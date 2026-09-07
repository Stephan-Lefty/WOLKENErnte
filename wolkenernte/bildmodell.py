"""Der Weg vom Bild zu den Ähnlichkeiten – das Modell selbst.

Dies ist die **optionale** Hälfte der Bilderkennung. Sie braucht
``onnxruntime`` und ``Pillow``; ohne die beiden gibt es die
Schlagwörter aus Datum und Dateiname, mehr nicht. Die Auswertung in
:mod:`wolkenernte.bilderkennung` kommt ohne alles aus und wird darum
getrennt gehalten.

**Nur der Bildteil läuft hier.** Ein CLIP-Modell besteht aus zwei
Hälften: Die eine wandelt Bilder in Zahlenreihen, die andere Sätze.
Beide zusammen wären 582 MB. Weil unsere Fragen aber feststehen –
sie stehen in :mod:`wolkenernte.begriffe` –, werden ihre Zahlenreihen
**einmal beim Bauen** gerechnet und liegen dem Programm als
dreihundert Kilobyte bei. Der Textteil wird auf dem Rechner des
Nutzers nie gebraucht.

Das ist auch der Grund, warum die Schlagwörter deutsch sein können,
ohne dass ein mehrsprachiges Modell nötig wäre: Die Frage ist
englisch, weil das Modell nur Englisch kann; der Name daneben ist
unserer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .bilderkennung import auswerten, fragen
from .modelle import BILDTEIL, ModellFehler, holen, vorhanden
from .schlagworte import Schlagwort

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

#: Die Bildgröße, die der Bildteil erwartet.
KANTE = 224

#: Womit die Farbwerte verrechnet werden.
#:
#: Diese sechs Zahlen stammen aus ``visual/preprocess_cfg.json`` des
#: Modells und sind **nicht** frei wählbar: Wer andere nimmt, füttert
#: das Modell mit Bildern, wie es sie nie gesehen hat. Es stürzt dabei
#: nicht ab, es antwortet nur Unsinn – der ärgerlichste Fehler von
#: allen.
MITTEL = (0.48145466, 0.4578275, 0.40821073)
STREUUNG = (0.26862954, 0.26130258, 0.27577711)

#: Wo die vorberechneten Zahlenreihen der Fragen liegen.
BEIGABE = Path(__file__).parent / "daten" / "begriffe.npz"


def verfuegbar() -> bool:
    """Ob die Bilderkennung überhaupt laufen kann.

    Prüft die Pakete und die Beigabe, **nicht** das 335-MB-Modell – das
    wird beim ersten Lauf geholt, und danach zu fragen wäre eine Frage
    zu früh.
    """
    try:
        import onnxruntime  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return BEIGABE.is_file()


def vorbereiten(bild: Path) -> Any:
    """Ein Bild in die Form bringen, die das Modell erwartet.

    Kürzeste Seite auf 224, dann aus der Mitte ausschneiden – so bleibt
    das Seitenverhältnis erhalten und der Bildinhalt wandert nicht in
    die Länge. Ein Hochformat verliert dabei oben und unten etwas; das
    ist der übliche Weg und das, worauf das Modell trainiert wurde.
    """
    import numpy as np
    from PIL import Image, ImageOps

    with Image.open(bild) as offen:
        # Wie im Fenster: Qt und Pillow drehen nicht von allein, und
        # ein liegendes Porträt erkennt kein Modell als Porträt.
        gerade = ImageOps.exif_transpose(offen)
        farbig = gerade.convert("RGB")

        breite, hoehe = farbig.size
        kleiner = min(breite, hoehe)
        neu = (max(KANTE, round(breite * KANTE / kleiner)),
               max(KANTE, round(hoehe * KANTE / kleiner)))
        verkleinert = farbig.resize(neu, Image.BICUBIC)

        links = (neu[0] - KANTE) // 2
        oben = (neu[1] - KANTE) // 2
        ausschnitt = verkleinert.crop((links, oben, links + KANTE, oben + KANTE))

    zahlen = np.asarray(ausschnitt, dtype=np.float32) / 255.0
    zahlen = (zahlen - np.array(MITTEL, dtype=np.float32)) / np.array(
        STREUUNG, dtype=np.float32)
    # Von Zeile-Spalte-Farbe auf Farbe-Zeile-Spalte, mit Stapel davor.
    return zahlen.transpose(2, 0, 1)[None, :, :, :]


class Bildmodell:
    """Der geladene Bildteil samt der vorberechneten Fragen.

    Das Laden dauert ein paar Sekunden und der Speicherbedarf liegt bei
    einigen hundert Megabyte – ein Bildmodell wird einmal aufgemacht
    und für den ganzen Durchlauf behalten, nicht je Bild.
    """

    def __init__(self, sitzung: Any, matrix: Any, reihen: list[str]) -> None:
        self.sitzung = sitzung
        self.matrix = matrix
        self.reihen = reihen

    @classmethod
    def laden(cls, fortschritt: "Callable[[int, int], None] | None" = None
              ) -> Bildmodell:
        """Modell und Beigabe öffnen, das Modell notfalls holen."""
        import numpy as np
        import onnxruntime as ort

        if not BEIGABE.is_file():
            raise ModellFehler(
                f"Die vorberechneten Begriffe fehlen ({BEIGABE}). "
                "Sie entstehen mit werkzeuge/begriffe_einbetten.py.")

        beigabe = np.load(BEIGABE, allow_pickle=False)
        reihen = [str(zeile) for zeile in beigabe["fragen"]]
        if reihen != fragen():
            raise ModellFehler(
                "Die vorberechneten Begriffe passen nicht zu "
                "wolkenernte/begriffe.py. Neu rechnen lassen mit "
                "werkzeuge/begriffe_einbetten.py.")

        datei = vorhanden(BILDTEIL) or holen(BILDTEIL, fortschritt)
        sitzung = ort.InferenceSession(
            str(datei), providers=["CPUExecutionProvider"])
        return cls(sitzung, beigabe["matrix"], reihen)

    def einbetten(self, bild: Path) -> Any:
        """Ein Bild in seine Zahlenreihe wandeln, auf Länge 1 gebracht.

        Auf Länge 1 gebracht, weil danach das Skalarprodukt zweier
        Reihen genau ihre Ähnlichkeit ist – kein Bruch, keine Wurzel,
        eine Multiplikation.
        """
        import numpy as np

        (reihe,) = self.sitzung.run(None, {"image": vorbereiten(bild)})
        vektor = reihe[0].astype(np.float32)
        return vektor / (np.linalg.norm(vektor) or 1.0)

    def aehnlichkeiten(self, bild: Path) -> dict[str, float]:
        """Zu jeder englischen Frage, wie gut sie zum Bild passt."""
        vektor = self.einbetten(bild)
        werte = self.matrix @ vektor
        return dict(zip(self.reihen, (float(wert) for wert in werte)))

    def schlagworte(self, bild: Path) -> list[Schlagwort]:
        """Die deutschen Schlagwörter zu einem Bild."""
        return auswerten(self.aehnlichkeiten(bild))

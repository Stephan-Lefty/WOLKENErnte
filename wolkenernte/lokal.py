"""Ein Ordner auf der Platte als Quelle – etwa ein früher ausgepackter Takeout.

Nach außen sieht er aus wie ein :class:`~wolkenernte.takeout.Archiv`:
dieselben ``eintrag()``, ``lesen()`` und dieselbe Aufzählung. Damit
nimmt die Übernahme ins Archiv beide Quellen entgegen, ohne sie
unterscheiden zu müssen.

**Ein Unterschied bleibt und ist wesentlich: die Prüfsumme.** Im ZIP
steht sie ohnehin drin, hier muss sie gerechnet werden – und das heißt,
jede Datei einmal vollständig zu lesen. Bei 37 GB sind das Minuten statt
Sekunden. Deshalb passiert das nicht beim Öffnen, sondern erst auf
Aufforderung über :meth:`Ordner.pruefsummen_rechnen`, und auch dort nur
für die Dateien, die überhaupt in Frage kommen: **Was eine Größe hat,
die sonst nirgends vorkommt, kann kein Doppelgänger sein.** An einem
echten Bestand fiel damit ein Drittel der Dateien weg, bevor auch nur
ein Byte gelesen wurde.

**Das Aufnahmedatum ist hier ein Problem.** Ein ausgepackter Takeout
enthält die Metadatendateien manchmal nicht mehr – in einem echten
Bestand hatten die Ordner ``Photos from 2019`` bis ``Photos from 2025``
**keine einzige**. Für diese Bilder wird das Datum in dieser Reihenfolge
gesucht: aus dem EXIF im Bild, sonst aus der Jahreszahl im Ordnernamen,
sonst gar nicht.
"""

from __future__ import annotations

import re
import zlib
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

from .takeout import Eintrag, TakeoutFehler

#: Endungen, die als Bild oder Video gelten.
MEDIEN = {
    ".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif", ".webp", ".avif",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".mpg", ".webm", ".m2ts",
}

#: Jahresordner eines Takeouts, in den Sprachen, die vorkommen.
#: Absichtlich großzügig: Eine nackte Jahreszahl reicht auch.
_JAHR = re.compile(
    r"(?:^|\b)(?:Fotos?\s+von|Photos?\s+from|Fotos?\s+del|Foto\s+da)?\s*"
    r"(19\d{2}|20\d{2})(?:$|\b)"
)

#: EXIF-Felder mit dem Aufnahmezeitpunkt, in der Reihenfolge ihrer Güte.
#: 36867 ist ``DateTimeOriginal`` – wann ausgelöst wurde. 306 ist
#: ``DateTime`` und kann auch der Zeitpunkt einer Bearbeitung sein.
_EXIF_ZEIT = (36867, 36868, 306)


class Ordner:
    """Ein Verzeichnisbaum voller Bilder."""

    def __init__(self, wurzel: Path) -> None:
        if not wurzel.is_dir():
            raise TakeoutFehler(f"{wurzel} ist kein Ordner.")
        self.wurzel = wurzel
        self._index: dict[str, Eintrag] = {}

        for pfad in sorted(wurzel.rglob("*")):
            if not pfad.is_file():
                continue
            try:
                groesse = pfad.stat().st_size
            except OSError:
                continue
            name = str(pfad.relative_to(wurzel))
            self._index[name] = Eintrag(
                pfad=name, quelle=pfad, groesse=groesse, pruefsumme=0
            )

    # -- Lesen, wie beim Takeout-Archiv ------------------------------------

    def __iter__(self) -> Iterator[Eintrag]:
        return iter(self._index.values())

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, pfad: str) -> bool:
        return pfad in self._index

    def eintrag(self, pfad: str) -> Eintrag | None:
        return self._index.get(pfad)

    def lesen(self, pfad: str) -> bytes:
        eintrag = self._index.get(pfad)
        if eintrag is None:
            raise TakeoutFehler(f"{pfad} liegt nicht in {self.wurzel}.")
        return eintrag.quelle.read_bytes()

    def medien(self) -> list[str]:
        """Nur die Bilder und Videos, ohne Metadaten und Beiwerk."""
        return [e.pfad for e in self._index.values()
                if e.quelle.suffix.lower() in MEDIEN]

    # -- Der teure Teil ----------------------------------------------------

    def pruefsummen_rechnen(
        self,
        *,
        nur_medien: bool = True,
        zusatzgroessen: set[int] | None = None,
        fortschritt: Callable[[int, int], None] | None = None,
    ) -> int:
        """Prüfsummen berechnen – aber nur, wo sie etwas nützen.

        Gerechnet wird für Dateien, deren Größe **mehr als einmal**
        vorkommt, und für solche, deren Größe in ``zusatzgroessen``
        steht – dort stehen die Größen einer zweiten Quelle, gegen die
        verglichen werden soll. Alles andere ist schon durch die Größe
        allein eindeutig.

        Gibt zurück, wie viele Dateien tatsächlich gelesen wurden.
        """
        kandidatenmenge = list(self._index.values())
        if nur_medien:
            kandidatenmenge = [e for e in kandidatenmenge
                               if e.quelle.suffix.lower() in MEDIEN]

        haeufigkeit: dict[int, int] = {}
        for eintrag in kandidatenmenge:
            haeufigkeit[eintrag.groesse] = haeufigkeit.get(eintrag.groesse, 0) + 1

        zusatz = zusatzgroessen or set()
        zu_rechnen = [e for e in kandidatenmenge
                      if haeufigkeit[e.groesse] > 1 or e.groesse in zusatz]

        for nummer, eintrag in enumerate(zu_rechnen, 1):
            if fortschritt:
                fortschritt(nummer, len(zu_rechnen))
            try:
                summe = 0
                with eintrag.quelle.open("rb") as datei:
                    while brocken := datei.read(1 << 20):
                        summe = zlib.crc32(brocken, summe)
            except OSError:
                continue
            self._index[eintrag.pfad] = Eintrag(
                pfad=eintrag.pfad, quelle=eintrag.quelle,
                groesse=eintrag.groesse, pruefsumme=summe,
            )
        return len(zu_rechnen)


def jahr_aus_ordner(pfad: str) -> int | None:
    """Die Jahreszahl aus einem Ordnernamen wie ``Fotos von 2023``.

    Von hinten gesucht: Der Ordner, in dem die Datei unmittelbar liegt,
    ist aussagekräftiger als ein Oberordner weiter oben.
    """
    teile = pfad.replace("\\", "/").split("/")[:-1]
    for teil in reversed(teile):
        treffer = _JAHR.search(teil)
        if treffer:
            jahr = int(treffer.group(1))
            if 1900 <= jahr <= 2100:
                return jahr
    return None


def exif_datum(rohdaten: bytes) -> datetime | None:
    """Den Aufnahmezeitpunkt aus dem Bild selbst lesen.

    Ohne Pillow gibt es hier nichts – dann bleibt die Jahreszahl aus dem
    Ordnernamen. Das Programm soll deswegen nicht abbrechen; ein Bild
    ohne Datum ist ärgerlich, ein Absturz ist schlimmer.

    Die Zeit im EXIF trägt **keine Zeitzone**, und sie ist die *Ortszeit
    der Kamera* – so steht es im Standard, und so stellt es jeder
    Mensch seine Kamera ein.
    """
    try:
        import io

        from PIL import Image
    except ImportError:
        return None

    try:
        with Image.open(io.BytesIO(rohdaten)) as bild:
            werte = bild.getexif()
            if not werte:
                return None
            for feld in _EXIF_ZEIT:
                roh = werte.get(feld)
                if isinstance(roh, str) and roh.strip():
                    zeit = _exif_zeit_lesen(roh)
                    if zeit:
                        return zeit
    except Exception:
        # Pillow wirft bei beschädigten Bildern die verschiedensten
        # Fehler. Für uns ist jeder davon gleichbedeutend mit
        # "kein Datum" - eine kaputte Datei darf den Lauf nicht stoppen.
        return None
    return None


def _exif_zeit_lesen(roh: str) -> datetime | None:
    """``"2023:07:15 12:00:00"`` in eine Zeit umsetzen.

    Kameras schreiben auch ``0000:00:00 00:00:00``, wenn die Uhr nie
    gestellt wurde – das ist kein Datum, sondern dessen Fehlen.

    **Ortszeit, nicht UTC.** Die erste Fassung setzte hier
    ``tzinfo=timezone.utc`` und begründete das damit, es mache nur um
    den Monatswechsel einen Unterschied. Das stimmt für die Einordnung
    in Ordner – aber der Zeitstempel wandert von hier aus in die Datei,
    und die Oberfläche rechnet ihn zurück in Ortszeit. Ein Foto von
    15:44 stand danach als »16:44« unter dem Bild, das ganze Jahr über,
    um genau den Abstand zu Greenwich. Aufgefallen ist es an einem
    Bildschirmfoto, auf dem Dateiname und angezeigte Uhrzeit
    nebeneinanderstanden und sich widersprachen.

    ``astimezone()`` ohne Argument liest eine zeitzonenlose Angabe als
    Ortszeit – genau die Annahme, die EXIF meint.
    """
    roh = roh.strip().replace("/", ":")
    if roh.startswith("0000"):
        return None
    for form in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(
                roh[:len(form) + 2].strip(), form).astimezone()
        except ValueError:
            continue
    return None

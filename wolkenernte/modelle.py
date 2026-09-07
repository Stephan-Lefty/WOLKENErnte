"""Das Bilderkennungsmodell holen und wiederfinden.

Ein CLIP-Bildencoder ist 335 MB groß. Das kann nicht ins Programmpaket:
PyPI lässt 100 MiB je Datei zu, und selbst mit Sondergenehmigung wäre
es unhöflich, jedem Nutzer ein Drittel Gigabyte aufzudrängen, der die
Bilderkennung gar nicht will. Also wird es **nachgeladen**, einmal je
Rechner, und liegt danach neben den anderen Daten des Programms.

So machen es alle vergleichbaren Programme – digiKam, InsightFace,
easyocr, spaCy. Zwei Dinge machen sie dabei schlecht, und die machen
wir anders:

**Die Prüfsumme wird geprüft.** easyocr führt für jedes Modell eine
MD5-Summe mit und ruft die Prüffunktion nie auf. Eine abgebrochene
Übertragung fällt dann erst auf, wenn das Modell Unsinn liefert.

**Es gibt keinen zweiten Griff ins Netz.** Wer ``huggingface_hub``
nutzt, sendet auch bei vollem Zwischenspeicher bei jedem Aufruf eine
Anfrage – für ein Programm, das offline arbeiten soll, ist das der
Knackpunkt. Hier reicht die Standardbibliothek: ``urllib`` holt, wenn
die Datei fehlt, und rührt das Netz sonst nicht an.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: Wie viel auf einmal gelesen wird.
BROCKEN = 1 << 20


class ModellFehler(Exception):
    """Das Modell fehlt, ließ sich nicht holen oder kam beschädigt an."""


@dataclass(frozen=True)
class Modell:
    """Eine nachzuladende Datei mit ihrer Prüfsumme.

    ``pruefsumme`` ist SHA-256 als Hexadezimaltext. Sie steht im Code,
    nicht in einer heruntergeladenen Beschreibungsdatei – sonst prüfte
    man die Datei gegen eine Angabe aus derselben Quelle, was nichts
    beweist.
    """

    name: str
    datei: str
    quelle: str
    pruefsumme: str
    groesse: int

    @property
    def megabyte(self) -> int:
        return round(self.groesse / (1 << 20))


#: Woher die Modelle kommen.
#:
#: Das immich-Projekt hält von OpenCLIP erzeugte ONNX-Ausfuhren bereit,
#: getrennt nach Bild- und Textteil. Getrennt ist genau das, was wir
#: brauchen: Der Textteil (242 MB) wird **einmal beim Bauen** gebraucht
#: und dem Nutzer nie zugemutet.
_HERKUNFT = "https://huggingface.co/immich-app/ViT-B-32__openai/resolve/main"

#: Der Bildteil – das einzige Modell, das auf dem Rechner des Nutzers
#: landet.
#:
#: **Warum ViT-B/32 und nicht etwas Kleineres?** MobileCLIP ist auf dem
#: Papier schneller, aber die Zahlen dazu stammen vom
#: Neuronenrechenwerk eines iPhones. Auf einem gewöhnlichen Rechner ist
#: MobileCLIP-S2 gemessen **1,5-mal langsamer** als ViT-B/32 – ein ViT
#: ist im Kern eine Kette großer Matrixmultiplikationen, und genau
#: darin ist die ONNX-Laufzeit auf der Hauptrecheneinheit stark.
BILDTEIL = Modell(
    name="CLIP ViT-B/32, Bildteil",
    datei="clip-vit-b-32-visual.onnx",
    quelle=f"{_HERKUNFT}/visual/model.onnx",
    pruefsumme="33a3df41ceef21acdf371af00f6dd0456ec1f9eba24d03a7720f9c3734e40859",
    groesse=351613724,
)

#: Der Textteil – nur für :mod:`werkzeuge.begriffe-einbetten`.
#:
#: Er rechnet die englischen Fragen aus :mod:`wolkenernte.begriffe`
#: einmal in Zahlenreihen um. Das Ergebnis ist ein paar hundert
#: Kilobyte groß und liegt dem Programm bei; dieses Modell braucht
#: niemand außer uns.
TEXTTEIL = Modell(
    name="CLIP ViT-B/32, Textteil",
    datei="clip-vit-b-32-textual.onnx",
    quelle=f"{_HERKUNFT}/textual/model.onnx",
    pruefsumme="b80cf0af751533a6712d92247f0ddc0c95208748bc59a1a27f33e67be6864e3b",
    groesse=254193396,
)


def ordner() -> Path:
    """Wo nachgeladene Modelle liegen.

    Die üblichen Orte je Betriebssystem. ``WOLKENERNTE_MODELLE``
    übersteuert das – für Systemverwalter, die einmal zentral
    ausliefern, und für Rechner ohne Netz.

    Bewusst **nicht** der Zwischenspeicher-Ordner: Der wird von
    Aufräumwerkzeugen und mancher Distribution geleert, und dann steht
    das Programm ohne Netz da. Ein Modell ist zwar wiederbeschaffbar,
    aber nur mit einer halben Stunde Leitung.
    """
    eigener = os.environ.get("WOLKENERNTE_MODELLE")
    if eigener:
        return Path(eigener).expanduser()
    if sys.platform == "win32":
        wurzel = Path(os.environ.get("LOCALAPPDATA")
                      or Path.home() / "AppData/Local")
        return wurzel / "WOLKENErnte/modelle"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/WOLKENErnte/modelle"
    wurzel = Path(os.environ.get("XDG_DATA_HOME")
                  or Path.home() / ".local/share")
    return wurzel / "WOLKENErnte/modelle"


def pfad(modell: Modell) -> Path:
    """Wo die Datei liegen würde – ob sie da ist, sagt das nicht."""
    return ordner() / modell.datei


def vorhanden(modell: Modell) -> Path | None:
    """Der Pfad, wenn die Datei da ist und die richtige Größe hat.

    Die Größe zu prüfen kostet nichts und fängt den häufigsten Fall:
    eine abgebrochene Übertragung. Die Prüfsumme wird beim Holen
    gerechnet, nicht bei jedem Start – dafür müsste jedes Mal ein
    Drittel Gigabyte durch die Hand gehen.
    """
    ziel = pfad(modell)
    if ziel.is_file() and ziel.stat().st_size == modell.groesse:
        return ziel
    return None


def pruefen(datei: Path, modell: Modell) -> str:
    """Die SHA-256-Summe einer Datei rechnen."""
    summe = hashlib.sha256()
    with datei.open("rb") as offen:
        while brocken := offen.read(BROCKEN):
            summe.update(brocken)
    return summe.hexdigest()


def holen(modell: Modell,
          fortschritt: Callable[[int, int], None] | None = None) -> Path:
    """Das Modell holen, prüfen und ablegen. Gibt den Pfad zurück.

    Ist es schon da, passiert nichts – kein Netzverkehr, keine Anfrage,
    ob es eine neuere Fassung gibt. Eine neuere Fassung bekäme einen
    anderen Dateinamen und eine andere Prüfsumme; hier ist keine
    Entscheidung zu treffen.

    Geschrieben wird zunächst nebenan unter ``.teil``. Erst wenn die
    Prüfsumme stimmt, wird umbenannt – ein Abbruch hinterlässt so nie
    eine Datei, die das Programm für vollständig hält.
    """
    schon_da = vorhanden(modell)
    if schon_da is not None:
        return schon_da

    ziel = pfad(modell)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    halb = ziel.with_suffix(ziel.suffix + ".teil")

    try:
        with urllib.request.urlopen(modell.quelle, timeout=60) as antwort:
            gesamt = int(antwort.headers.get("Content-Length") or modell.groesse)
            geladen = 0
            with halb.open("wb") as schreiben:
                while brocken := antwort.read(BROCKEN):
                    schreiben.write(brocken)
                    geladen += len(brocken)
                    if fortschritt:
                        fortschritt(geladen, gesamt)
    except (urllib.error.URLError, OSError) as fehler:
        halb.unlink(missing_ok=True)
        raise ModellFehler(
            f"{modell.name} ließ sich nicht holen: {fehler}\n"
            f"Von Hand: {modell.quelle}\n"
            f"Ablegen unter: {ziel}") from fehler

    gerechnet = pruefen(halb, modell)
    if gerechnet != modell.pruefsumme:
        halb.unlink(missing_ok=True)
        raise ModellFehler(
            f"{modell.name} kam beschädigt an.\n"
            f"  erwartet: {modell.pruefsumme}\n"
            f"  bekommen: {gerechnet}")

    halb.replace(ziel)
    return ziel

"""Was bei welchem Anbieter geht – und was nicht.

Diese Datei ist der ehrlichste Teil des Programms. Sie hält fest, was
ein Wolkenspeicher einer fremden Anwendung tatsächlich erlaubt, und sie
tut das **bevor** der Anwender seine Bilder auswählt und auf »Löschen«
drückt.

**Warum das eine eigene Datei ist und keine Fußnote in der Anleitung.**
Der Wunsch, aus dem dieses Programm entstand, lautete: alle Bilder aus
allen Wolken holen und dort löschen, was weg soll. Genau die drei
zuerst genannten Anbieter – Google Fotos, iCloud Fotos, Proton Fotos –
können das nicht, jeder aus einem anderen Grund. Ein Programm, das das
verschweigt und den Anwender erst nach dem Herunterladen von 40.000
Bildern auflaufen lässt, wäre schlimmer als eines, das es gar nicht
erst versucht.

Deshalb steht die Wahrheit hier im Code, nicht in der Doku: Die
Oberfläche fragt diese Tabelle, bevor sie einen Löschknopf anzeigt.
Einen Knopf, der nichts tut, gibt es nicht.

**Stand der Angaben: 2026-09-05.** Die Belege stehen in
``docs/anbieter.md``. Das ist kein Zierrat – diese Lage ändert sich,
und zwar schnell: Google hat die Fotos-Schnittstelle am 31.03.2025
abgeschaltet, rclone stuft sein Google-Fotos-Modul inzwischen als
veraltet ein. Wer hier etwas ändert, ändert bitte auch das Datum und
den Beleg.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Weg(Enum):
    """Worüber ein Anbieter angesprochen wird."""

    RCLONE = "rclone"
    """Über den mitgelieferten rclone-Dienst. Der Regelfall."""

    TAKEOUT = "takeout"
    """Nur über ein Archiv, das der Anwender selbst beim Anbieter
    anfordert. Kein laufender Zugriff, kein Löschen."""

    KEINER = "keiner"
    """Aus einem fremden Programm heraus überhaupt nicht erreichbar."""


@dataclass(frozen=True)
class Anbieter:
    """Ein Wolkenspeicher und das, was er zulässt.

    Die drei Fähigkeiten sind absichtlich einzeln aufgeführt und nicht
    zu einem »unterstützt ja/nein« zusammengefasst. Der interessante
    Fall ist gerade der dazwischen: iCloud Fotos lässt sich vollständig
    lesen und herunterladen, aber nicht anfassen.
    """

    kennung: str
    name: str
    weg: Weg

    auflisten: bool
    """Bestand sehen, ohne ihn herunterzuladen."""

    laden: bool
    """Originale herunterladen."""

    loeschen: bool
    """**In der Wolke** löschen. Nicht: die heruntergeladene Kopie."""

    hinweis: str
    """Was der Anwender wissen muss, bevor er sich darauf verlässt.
    Wird in der Oberfläche angezeigt, nicht nur protokolliert."""

    erprobt: bool = False
    """Ob es hier tatsächlich schon gelaufen ist. Was nur der
    Papierlage nach funktionieren müsste, wird nicht als erprobt
    ausgegeben – dieselbe Regel wie bei MailBurg und macOS."""

    @property
    def vollstaendig(self) -> bool:
        """Ob der ganze Ablauf – sehen, holen, aufräumen – hier trägt."""
        return self.auflisten and self.laden and self.loeschen


#: Die Anbieter, nach Brauchbarkeit sortiert.
#:
#: Zuerst die, bei denen der vollständige Ablauf funktioniert, danach
#: die Teilfälle. Diese Reihenfolge ist die der Oberfläche: Was ganz
#: funktioniert, steht oben.
ANBIETER: tuple[Anbieter, ...] = (
    # -- Vollständig: sehen, holen, aufräumen -----------------------------
    Anbieter(
        "nextcloud", "Nextcloud (WebDAV)", Weg.RCLONE,
        True, True, True,
        "Der unkomplizierteste Fall: eigener Server, offenes Protokoll, "
        "keine Zugangsbeschränkung durch Dritte.",
    ),
    Anbieter(
        "dropbox", "Dropbox", Weg.RCLONE,
        True, True, True,
        "Vollständig über die offizielle Schnittstelle.",
    ),
    Anbieter(
        "onedrive", "Microsoft OneDrive", Weg.RCLONE,
        True, True, True,
        "Vollständig über Microsoft Graph. Die Anmeldung läuft über "
        "OAuth2 – bei Microsoft kostenlos und ohne Prüfverfahren.",
    ),
    Anbieter(
        "drive", "Google Drive", Weg.RCLONE,
        True, True, True,
        "Vollständig – aber **nur Drive**. Was in Google Fotos liegt, "
        "ist seit 2019 in Drive nicht mehr sichtbar; dafür gilt der "
        "eigene Eintrag weiter unten.",
    ),
    Anbieter(
        "box", "Box", Weg.RCLONE,
        True, True, True,
        "Vollständig über die offizielle Schnittstelle.",
    ),
    Anbieter(
        "pcloud", "pCloud", Weg.RCLONE,
        True, True, True,
        "Vollständig über die offizielle Schnittstelle.",
    ),
    Anbieter(
        "icloud-drive", "iCloud Drive", Weg.RCLONE,
        True, True, True,
        "Apple bietet dafür keine Schnittstelle für fremde Programme an; "
        "rclone bildet den Weg über die Weboberfläche nach und stuft das "
        "selbst als erprobungsbedürftig ein. Die Anmeldung verlangt das "
        "echte Apple-Passwort – anwendungsspezifische Passwörter werden "
        "nicht angenommen – und muss etwa monatlich wiederholt werden.",
    ),
    Anbieter(
        "proton-drive", "Proton Drive", Weg.RCLONE,
        True, True, True,
        "Kein offenes Protokoll: rclone hat den Zugang nachgebaut, und "
        "Proton ändert die Verschlüsselung von Zeit zu Zeit. Rechnen Sie "
        "damit, dass das nach einer Aktualisierung vorübergehend stehen "
        "bleibt. Gilt nur für »Meine Dateien«, nicht für Proton Fotos.",
    ),

    # -- Teilfälle: nicht alles geht ---------------------------------------
    Anbieter(
        "icloud-fotos", "iCloud Fotos", Weg.RCLONE,
        True, True, False,
        "Sehen und Herunterladen ja, **Löschen nein** – der Zugang ist "
        "ausdrücklich nur lesend. Und: Mit eingeschaltetem erweitertem "
        "Datenschutz (Advanced Data Protection) geht gar nichts, weil "
        "dann auch der Zugriff über das Web gesperrt ist.",
    ),
    Anbieter(
        "google-fotos", "Google Fotos", Weg.TAKEOUT,
        False, False, False,
        "Seit dem 31.03.2025 sieht ein fremdes Programm nur noch die "
        "Bilder, die es selbst hochgeladen hat – Ihre eigene Mediathek "
        "ist unerreichbar. Eine Löschfunktion hat es dort nie gegeben. "
        "Der Weg führt über »Google Takeout«: Sie fordern das Archiv "
        "selbst an, WOLKENErnte wertet es aus. Aufgeräumt wird danach "
        "von Hand im Browser.",
    ),
    Anbieter(
        "proton-fotos", "Proton Fotos", Weg.KEINER,
        False, False, False,
        "Die von der Handy-App gesicherten Bilder liegen in einem "
        "eigenen Bereich, den fremde Programme nicht sehen. Es gibt "
        "dafür derzeit keinen Weg – auch keinen umständlichen.",
    ),
)

NACH_KENNUNG: dict[str, Anbieter] = {a.kennung: a for a in ANBIETER}


def vollstaendige() -> tuple[Anbieter, ...]:
    """Die Anbieter, bei denen der ganze Ablauf trägt."""
    return tuple(a for a in ANBIETER if a.vollstaendig)


def nur_lesend() -> tuple[Anbieter, ...]:
    """Anbieter, von denen geholt, bei denen aber nicht aufgeräumt
    werden kann. Der unangenehme Zwischenfall, den die Oberfläche
    ausdrücklich benennen muss."""
    return tuple(a for a in ANBIETER if a.laden and not a.loeschen)


def darf_loeschen(kennung: str) -> bool:
    """Ob für diesen Anbieter überhaupt ein Löschknopf gezeigt wird.

    Eine unbekannte Kennung gilt als »nein«. Das ist Absicht: Wer einen
    Anbieter hinzufügt und diese Tabelle vergisst, bekommt ein Programm,
    das zu wenig anbietet – nicht eines, das zu viel verspricht.
    """
    anbieter = NACH_KENNUNG.get(kennung)
    return anbieter is not None and anbieter.loeschen

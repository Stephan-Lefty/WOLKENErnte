"""Welche Metadatendatei gehört zu welchem Bild.

Das ist die eigentliche Fehlerquelle beim Takeout. Google legt neben
jedes Bild eine JSON mit Aufnahmedatum, Ort und Titel – aber der Name
dieser JSON folgt Regeln, die sich über die Jahre geändert haben und an
mehreren Stellen brechen.

**Warum das gefährlich ist und nicht bloß lästig.** Wer hier großzügig
rät, ordnet einem Bild die Angaben eines *anderen* zu. Im Werkzeug
GooglePhotosTakeoutHelper ist genau das passiert: Ortsangaben und
Aufnahmedaten fremder Fotos wanderten in die Bilder, mit Abweichungen
von hunderten Kilometern. Deshalb trägt jede Zuordnung hier eine
Sicherheitsangabe, und die Oberfläche zeigt bei einem unsicheren Treffer
**weder Datum noch Ort** – lieber keine Angabe als eine falsche.

**Die Regeln, so wie sie tatsächlich gelten** (Stand 2026-09-05, Belege
in ``docs/takeout.md``):

* Bis Ende 2024 hieß die Datei ``IMG_1234.jpg.json``, seither
  ``IMG_1234.jpg.supplemental-metadata.json``. Beide kommen vor.
* Der ganze JSON-Name darf **51 Zeichen** nicht überschreiten. Ist er
  länger, kürzt Google – und zwar irgendwo im Suffix, sodass Formen wie
  ``.supplemental-metadat.json``, ``.suppl.json`` oder ``.s.json``
  entstehen.
* Bei Namensgleichheit hängt Google eine Nummer an – aber **an eine
  andere Stelle als beim Bild**: Zu ``IMG_1234(1).jpg`` gehört
  ``IMG_1234.jpg(1).json``. Die Klammer steht vor der Endung.
* Bearbeitete Fassungen (``IMG_1234-bearbeitet.jpg``) haben **keine
  eigene** JSON; ihre Angaben stehen in der des Originals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Das lange Suffix, das Google seit Ende 2024 anhängt.
SUFFIX = "supplemental-metadata"

#: Höchstlänge des ganzen JSON-Dateinamens. Darüber kürzt Google.
#:
#: 51, nicht 46: 46 ist nur der Rest, der für den Namen bleibt, wenn
#: ``.json`` abgezogen ist. Wer 46 als Grenze nimmt, verfehlt jede
#: Kürzung um fünf Zeichen.
HOECHSTLAENGE = 51

#: Anhängsel bearbeiteter Fassungen. Die ersten sechs bleiben immer
#: englisch, die übrigen richten sich nach der Sprache des Kontos –
#: ``-bearbeitet`` ist die deutsche Form.
BEARBEITET = (
    "-effects", "-motion", "-animation", "-smile", "-collage", "-mix",
    "-edited", "-bearbeitet", "-edytowane", "-bewerkt", "-modificato",
    "-modifié", "-ha editado", "-editada", "-editado", "-editat",
    "-編集済み", "-编辑",
)

_KLAMMER = re.compile(r"\((\d+)\)")


@dataclass(frozen=True)
class Zuordnung:
    """Ein Bild und die Metadatendatei, die dazu gehört."""

    medium: str
    metadaten: str | None

    sicher: bool = True
    """Ob die Metadaten **dieses** Bild beschreiben.

    ``False`` heißt: Die Datei wurde über einen Umweg gefunden – etwa
    über die bearbeitete Fassung oder eine andere Dateiendung. Datum und
    Ort daraus sind für dieses Bild **nicht** verwendbar; Titel und
    Beschreibung meist schon.
    """

    weg: str = ""
    """Wie der Treffer zustande kam. Für Fehlersuche und Berichte."""


def _kuerzen(name: str) -> str:
    """Einen JSON-Namen auf Googles Höchstlänge stutzen."""
    if len(name) <= HOECHSTLAENGE:
        return name
    return name[: HOECHSTLAENGE - len(".json")] + ".json"


def _mit_nummer(name: str, nummer: str) -> str:
    """``IMG.jpg.json`` und ``1`` zu ``IMG.jpg(1).json``."""
    return name[: -len(".json")] + f"({nummer}).json"


def json_kandidaten(medienname: str) -> list[str]:
    """Alle JSON-Namen, die zu diesem Bild gehören könnten.

    Die Reihenfolge ist die Reihenfolge der Wahrscheinlichkeit: Der
    erste Treffer im Bestand gewinnt. Das ist zulässig, weil die alte
    und die neue Form für dieselbe Datei nie nebeneinander vorkommen.

    Die Nummer eines Duplikats wird dabei **an das Ende verschoben**:
    Zu ``IMG_1234(1).jpg`` sucht Google unter ``IMG_1234.jpg(1).json``.
    """
    kandidaten: list[str] = []

    treffer = list(_KLAMMER.finditer(medienname))
    nummer = treffer[-1].group(1) if treffer else None
    # Der Name ohne die Nummer - nur die letzte entfernen, sonst
    # zerlegt es Namen wie "Bild(3).(2)(3).jpg" falsch.
    ohne_nummer = (
        medienname[: treffer[-1].start()] + medienname[treffer[-1].end():]
        if treffer else medienname
    )

    for basis in ([ohne_nummer] if treffer else []) + [medienname]:
        # Das lange Suffix, von der vollen Länge abwärts gekürzt.
        for i in range(len(SUFFIX), 0, -1):
            voll = f"{basis}.{SUFFIX[:i]}.json"
            if len(voll) <= HOECHSTLAENGE:
                kandidaten.append(voll)
                if nummer:
                    kandidaten.append(_mit_nummer(voll, nummer))
                break
        else:
            # Selbst das kürzeste Suffix passt nicht mehr - dann kürzt
            # Google den Namen selbst.
            kandidaten.append(_kuerzen(f"{basis}.{SUFFIX}.json"))

        # Die alte Form ohne Suffix.
        alt = _kuerzen(f"{basis}.json")
        kandidaten.append(alt)
        if nummer:
            kandidaten.append(_mit_nummer(alt, nummer))

    # Reihenfolge erhalten, Wiederholungen entfernen.
    gesehen: set[str] = set()
    return [k for k in kandidaten if not (k in gesehen or gesehen.add(k))]


def ohne_bearbeitet(medienname: str) -> str | None:
    """Aus ``IMG-bearbeitet.jpg`` das ``IMG.jpg`` machen.

    Gibt ``None`` zurück, wenn kein Anhängsel gefunden wurde.

    Nur vollständige Anhängsel, keine abgeschnittenen: GPTH probiert
    auch Reste ab zwei Zeichen und schreibt damit eine echte Datei
    ``Foto-b.jpg`` zu ``Foto.jpg`` um. Für ein Programm, das den Bestand
    nur anzeigt, ist das zu übergriffig.
    """
    stamm, punkt, endung = medienname.rpartition(".")
    if not punkt:
        return None
    for anhang in BEARBEITET:
        # Eine Nummer darf dahinter stehen: "IMG-bearbeitet(1).jpg".
        muster = re.compile(re.escape(anhang) + r"(\(\d+\))?$", re.IGNORECASE)
        if muster.search(stamm):
            return muster.sub("", stamm) + punkt + endung
    return None


def zuordnen(medien: list[str], metadaten: set[str]) -> list[Zuordnung]:
    """Jedem Bild seine Metadatendatei zuweisen.

    ``medien`` und ``metadaten`` sind Pfade innerhalb des Archivs. Die
    Suche läuft je Verzeichnis: Google legt die JSON neben das Bild.

    Vorwärts gesucht, nicht rückwärts: Aus dem Bildnamen lassen sich die
    möglichen JSON-Namen berechnen, umgekehrt geht es nicht – ein
    gekürzter JSON-Name gibt den ursprünglichen Bildnamen nicht mehr her.
    Jeder Versuch ist ein Nachschlagen in einer Menge, also billig.
    """
    ergebnis: list[Zuordnung] = []

    for pfad in medien:
        ordner, _, name = pfad.rpartition("/")
        vorne = f"{ordner}/" if ordner else ""

        gefunden = None
        for kandidat in json_kandidaten(name):
            if vorne + kandidat in metadaten:
                gefunden = (vorne + kandidat, True, "direkt")
                break

        # Bearbeitete Fassungen haben keine eigene Datei - die Angaben
        # stehen bei der Ursprungsfassung. Titel und Beschreibung gelten
        # dort auch für die Bearbeitung, Datum und Ort nicht zwingend.
        if gefunden is None:
            urform = ohne_bearbeitet(name)
            if urform:
                for kandidat in json_kandidaten(urform):
                    if vorne + kandidat in metadaten:
                        gefunden = (vorne + kandidat, False, "bearbeitete Fassung")
                        break

        if gefunden is None:
            ergebnis.append(Zuordnung(pfad, None, False, "nichts gefunden"))
        else:
            ziel, sicher, weg = gefunden
            ergebnis.append(Zuordnung(pfad, ziel, sicher, weg))

    return ergebnis

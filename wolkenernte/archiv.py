"""Bilder aus einem Takeout in ein Archiv übernehmen.

Das Archiv liegt an einem Ort, den der Anwender bestimmt, und ist nach
Aufnahmedatum geordnet::

    <Archiv>/2023/2023-07/IMG_1234.jpg
    <Archiv>/ohne-datum/IMG_5678.jpg

**Warum nach Datum und nicht nach Alben.** Ein Bild kann in mehreren
Alben liegen, aber nur an einer Stelle auf der Platte. Nach Alben
geordnet müsste man es mehrfach ablegen – genau das, was das Programm
abschaffen soll. Das Datum ist eindeutig; die Albumzugehörigkeit gehört
in eine Datenbank, nicht in den Ordnernamen.

**Nichts wird überschrieben, und nichts wird zweimal geschrieben.** Ein
abgebrochener Durchlauf lässt sich einfach wiederholen: Was schon da ist
und die richtige Prüfsumme hat, wird übergangen.
"""

from __future__ import annotations

import os
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .metadaten import Angaben
from .takeout import Archiv as Takeout
from .zuordnung import Zuordnung

#: Ordner für Bilder, deren Aufnahmedatum unbekannt ist.
OHNE_DATUM = "ohne-datum"


@dataclass
class Bilanz:
    """Wie ein Durchlauf ausging."""

    uebernommen: int = 0
    uebergangen: int = 0
    """Schon vorhanden, mit passender Prüfsumme."""

    doppelt: int = 0
    """Inhaltsgleich zu etwas, das in diesem Lauf schon geschrieben wurde."""

    gescheitert: int = 0
    bytes_geschrieben: int = 0
    fehler: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        teile = [f"{self.uebernommen} übernommen"]
        if self.doppelt:
            teile.append(f"{self.doppelt} Doppelgänger übergangen")
        if self.uebergangen:
            teile.append(f"{self.uebergangen} bereits vorhanden")
        if self.gescheitert:
            teile.append(f"{self.gescheitert} fehlgeschlagen")
        teile.append(f"{self.bytes_geschrieben / 1e9:.2f} GB")
        return ", ".join(teile)


def _sicherer_name(name: str) -> str:
    """Einen Dateinamen entschärfen.

    Ein Name aus einem fremden Archiv ist eine Eingabe von außen. ``..``
    und Schrägstriche darin würden aus dem Archiv herausführen – die
    klassische Stelle für einen Pfaddurchbruch.
    """
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = name.replace("\x00", "")
    if name in ("", ".", ".."):
        return "unbenannt"
    return name


def zielordner(angaben: Angaben | None) -> str:
    """Wohin ein Bild gehört, gemessen an seinem Aufnahmedatum."""
    if angaben is None or angaben.aufgenommen is None:
        return OHNE_DATUM
    zeit = angaben.aufgenommen
    return f"{zeit.year:04d}/{zeit.year:04d}-{zeit.month:02d}"


def _freier_name(ordner: Path, name: str) -> Path:
    """Einen Namen finden, der noch nicht vergeben ist.

    Zwei verschiedene Bilder können denselben Namen tragen – etwa
    ``IMG_0001.jpg`` aus zwei Jahren, die im selben Monat gelandet sind.
    Dann wird angehängt statt überschrieben.
    """
    ziel = ordner / name
    if not ziel.exists():
        return ziel
    stamm, punkt, endung = name.rpartition(".")
    if not punkt:
        stamm, endung = name, ""
    for i in range(2, 10_000):
        kandidat = ordner / (f"{stamm}-{i}{punkt}{endung}" if punkt else f"{stamm}-{i}")
        if not kandidat.exists():
            return kandidat
    raise OSError(f"Kein freier Name für {name} in {ordner}")


def _pruefsumme(pfad: Path) -> int:
    """Die CRC-32 einer vorhandenen Datei – dieselbe Rechnung wie im ZIP."""
    summe = 0
    with pfad.open("rb") as datei:
        while brocken := datei.read(1 << 20):
            summe = zlib.crc32(brocken, summe)
    return summe


def uebernehmen(
    takeout: Takeout,
    zuordnungen: Iterable[Zuordnung],
    angaben_zu: Callable[[Zuordnung], Angaben | None],
    ziel: Path,
    *,
    fortschritt: Callable[[int, str], None] | None = None,
    gesehen: set[tuple[int, int]] | None = None,
) -> Bilanz:
    """Bilder aus dem Takeout ins Archiv schreiben.

    ``angaben_zu`` liefert zu einer Zuordnung die ausgewerteten
    Metadaten oder ``None``. Als Rückruf und nicht als fertige Liste,
    damit bei zehntausenden Bildern nicht alles gleichzeitig im
    Speicher steht.

    Doppelgänger werden an Größe und Prüfsumme erkannt und nur einmal
    geschrieben. Das ist bei einem Takeout kein Randfall: Jedes Bild,
    das in einem Album liegt, kommt dort ein zweites Mal vor.

    ``gesehen`` nimmt eine Menge entgegen, die über mehrere Aufrufe
    hinweg bestehen bleibt. Nur so lassen sich zwei Quellen nacheinander
    übernehmen, ohne dass die zweite die Doppelgänger der ersten noch
    einmal schreibt – und genau das ist der Regelfall, wenn ein alter
    ausgepackter Export und ein frischer nebeneinanderliegen.
    """
    bilanz = Bilanz()
    if gesehen is None:
        gesehen = set()

    for nummer, zuordnung in enumerate(zuordnungen, 1):
        eintrag = takeout.eintrag(zuordnung.medium)
        if eintrag is None:
            bilanz.gescheitert += 1
            bilanz.fehler.append(f"{zuordnung.medium}: nicht im Archiv")
            continue

        kennung = (eintrag.groesse, eintrag.pruefsumme)
        if kennung in gesehen:
            bilanz.doppelt += 1
            continue
        gesehen.add(kennung)

        angaben = angaben_zu(zuordnung)
        ordner = ziel / zielordner(angaben)
        name = _sicherer_name(eintrag.name)

        if fortschritt:
            fortschritt(nummer, name)

        try:
            ordner.mkdir(parents=True, exist_ok=True)

            # Schon da? Dann nur nachrechnen, nicht neu schreiben. So
            # lässt sich ein abgebrochener Lauf einfach wiederholen.
            vorhanden = ordner / name
            if vorhanden.exists() and vorhanden.stat().st_size == eintrag.groesse:
                if _pruefsumme(vorhanden) == eintrag.pruefsumme:
                    bilanz.uebergangen += 1
                    _zeit_setzen(vorhanden, angaben)
                    continue

            inhalt = takeout.lesen(zuordnung.medium)

            # **Vor dem Schreiben prüfen, nicht danach.** Eine Datei,
            # die schon auf der Platte liegt, hat der Anwender bereits
            # gesehen; ein Fehler fällt dann später auf oder nie.
            if zlib.crc32(inhalt) != eintrag.pruefsumme:
                bilanz.gescheitert += 1
                bilanz.fehler.append(f"{name}: Prüfsumme stimmt nicht")
                continue

            pfad = _freier_name(ordner, name)
            pfad.write_bytes(inhalt)
            _zeit_setzen(pfad, angaben)

            bilanz.uebernommen += 1
            bilanz.bytes_geschrieben += len(inhalt)

        except OSError as fehler:
            bilanz.gescheitert += 1
            bilanz.fehler.append(f"{name}: {fehler}")

    return bilanz


def _zeit_setzen(pfad: Path, angaben: Angaben | None) -> None:
    """Der Datei ihr Aufnahmedatum als Änderungszeit geben.

    Damit stimmt die Sortierung in jedem Dateimanager, ohne dass er
    unser Archiv kennen müsste. Schlägt es fehl – etwa auf einem
    Dateisystem, das keine Zeiten kennt –, ist das kein Grund, die
    Übernahme abzubrechen.
    """
    if angaben is None or angaben.aufgenommen is None:
        return
    try:
        zeit = angaben.aufgenommen.timestamp()
        os.utime(pfad, (zeit, zeit))
    except (OSError, OverflowError, ValueError):
        pass


def datum_aus(pfad: Path) -> datetime | None:
    """Das Aufnahmedatum, wie es im Archivpfad steht.

    Der Gegenweg zu :func:`zielordner` – für einen späteren Abgleich,
    der ohne Datenbank auskommen muss.
    """
    teile = pfad.parts
    for teil in reversed(teile):
        if len(teil) == 7 and teil[4] == "-":
            try:
                return datetime.strptime(teil, "%Y-%m")
            except ValueError:
                return None
    return None

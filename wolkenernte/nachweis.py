#!/usr/bin/env python3
"""Weist nach, dass jedes Bild aus den Quellen im Archiv angekommen ist.

    python3 werkzeuge/nachpruefen.py <Archiv> <Quelle> [<Quelle> ...]

**Vor jedem Löschen laufen lassen.** Die Bilanz der Übernahme sagt nur,
was das Programm zu tun *glaubte*. Dieses Werkzeug sieht nach, was
tatsächlich auf der Platte liegt – und zwar inhaltlich, über Größe und
Prüfsumme, nicht über Dateinamen. Ein Bild, das im Archiv anders heißt
oder in einem anderen Jahr liegt, gilt trotzdem als angekommen; nur
sein Inhalt zählt.

Das Werkzeug **ändert nichts**. Es liest und rechnet.
"""

from __future__ import annotations

import sys
import time
import zlib
from collections.abc import Callable
from pathlib import Path

from .archiv import medien as archiv_medien
from .lokal import MEDIEN, Ordner
from .takeout import Archiv as Takeout


def _ist_medium(name: str) -> bool:
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


def archiv_ist_leer(archiv: Path) -> bool:
    """Ob im Archiv überhaupt ein Bild liegt.

    Getrennt von :func:`archiv_kennungen`, seit die nur noch die
    passenden Größen rechnet: »Keine Größe passt« heißt bloß, dass
    diese Bilder noch nicht geerntet wurden – ein völlig normaler
    Befund. »Gar kein Bild im Archiv« heißt dagegen, dass jemand
    aufräumen will, bevor er geerntet hat, und das ist der
    gefährlichste denkbare Fall.
    """
    # **Der Zwischenspeicher zählt nicht mit.** In .wolkenernte/vorschau
    # liegen Tausende JPEG-Dateien; ein Archiv, in dem nur noch die
    # stehen, ist leer – und genau dann muss diese Funktion »ja« sagen,
    # weil unmittelbar danach in einer Cloud gelöscht wird.
    return not archiv_medien(archiv)


def _groesse(pfad: Path) -> int:
    try:
        return pfad.stat().st_size
    except OSError:
        return -1


def archiv_kennungen(
    archiv: Path,
    melden: Callable[[int, int], None] | None = None,
    *,
    nur_groessen: set[int] | None = None,
) -> set[tuple[int, int]]:
    """Größe und Prüfsumme jeder Datei im Archiv.

    **``nur_groessen`` ist der Unterschied zwischen Sekunden und
    Minuten.** Wer nachsehen will, ob 28 Bilder aus einer Cloud im
    Archiv liegen, muss nicht 15.662 Archivdateien durchrechnen – nur
    die, deren Größe überhaupt zu einer der 28 passt. Eine Datei
    anderer Größe kann keine von ihnen sein.

    Gemessen: über den ganzen Bestand 296 Sekunden, mit den 28 Größen
    weniger als eine. Und es wird dabei nichts weicher geprüft – die
    Prüfsumme wird nach wie vor gerechnet, nur eben nicht für Dateien,
    die als Antwort ohnehin ausscheiden.

    ``None`` heißt: alles rechnen. Das ist richtig für
    :func:`pruefen`, wo der vollständige Bestand gebraucht wird.

    **Ohne ``melden`` schweigt die Funktion.** Sie hat lange von sich
    aus ins Terminal geschrieben – für ein Werkzeug richtig, für die
    Fensteranwendung falsch: Dort sieht niemand ein Terminal, und die
    Meldungen landeten im Nichts, während der Anwender vor einem
    Fortschrittsbalken saß, der von alledem nichts wusste.
    """
    kennungen: set[tuple[int, int]] = set()
    # Ohne .wolkenernte: Ein Vorschaubild darf nicht als Nachweis
    # gelten, dass ein Bild im Archiv liegt – daran hängt das Löschen.
    dateien = archiv_medien(archiv)
    if nur_groessen is not None:
        # Ein stat() je Datei statt sie ganz zu lesen.
        dateien = [p for p in dateien
                   if _groesse(p) in nur_groessen]
    for nummer, pfad in enumerate(dateien, 1):
        if melden:
            melden(nummer, len(dateien))
        try:
            summe = 0
            with pfad.open("rb") as datei:
                while brocken := datei.read(1 << 20):
                    summe = zlib.crc32(brocken, summe)
            kennungen.add((pfad.stat().st_size, summe))
        except OSError:
            # Eine unlesbare Datei ist kein Grund abzubrechen - sie
            # zählt nur nicht als Nachweis, und das ist die sichere
            # Seite.
            continue
    return kennungen


def im_terminal(nummer: int, gesamt: int) -> None:
    """Fortschritt für die Kommandozeile – als ``melden`` zu übergeben."""
    if nummer % 1000 == 0 or nummer == gesamt:
        print(f"  Archiv {nummer}/{gesamt}", end="\r", flush=True)


def pruefen(archiv: Path, quellen: list[Path]) -> int:
    t0 = time.time()
    print(f"=== Archiv: {archiv} ===")
    vorhanden = archiv_kennungen(archiv, im_terminal)
    print(f"  {len(vorhanden)} verschiedene Inhalte im Archiv      ")

    fehlend: list[str] = []
    gesamt = 0

    for pfad in quellen:
        print(f"\n=== Quelle: {pfad.name} ===")
        if pfad.is_dir() and any(p.suffix.lower() == ".zip" for p in pfad.iterdir()):
            quelle = Takeout.aus_ordner(pfad)
            eintraege = [e for e in quelle if _ist_medium(e.name)]
            print(f"  {len(eintraege)} Mediendateien")
            for e in eintraege:
                gesamt += 1
                if (e.groesse, e.pruefsumme) not in vorhanden:
                    fehlend.append(f"{pfad.name}: {e.pfad}")
            quelle.schliessen()
        else:
            ordner = Ordner(pfad)
            # Alles rechnen, nicht nur Verdächtige: Hier geht es um den
            # Nachweis, nicht um Doppelgänger.
            eintraege = [e for e in ordner if _ist_medium(e.pfad)]
            print(f"  {len(eintraege)} Mediendateien, Prüfsummen werden gerechnet")
            for nummer, e in enumerate(eintraege, 1):
                if nummer % 1000 == 0:
                    print(f"  {nummer}/{len(eintraege)}", end="\r", flush=True)
                gesamt += 1
                try:
                    summe = 0
                    with e.quelle.open("rb") as datei:
                        while brocken := datei.read(1 << 20):
                            summe = zlib.crc32(brocken, summe)
                except OSError as fehler:
                    fehlend.append(f"{pfad.name}: {e.pfad} ({fehler})")
                    continue
                if (e.groesse, summe) not in vorhanden:
                    fehlend.append(f"{pfad.name}: {e.pfad}")
            print(f"  fertig                    ")

    print(f"\n=== Ergebnis nach {(time.time()-t0)/60:.1f} Minuten ===")
    print(f"  {gesamt} Dateien in den Quellen geprüft")
    if not fehlend:
        print("  **Jeder Inhalt ist im Archiv vorhanden.**")
        print("  Die Quellen können gelöscht werden.")
        return 0

    print(f"  **{len(fehlend)} Dateien fehlen im Archiv:**")
    for zeile in fehlend[:40]:
        print(f"    {zeile}")
    if len(fehlend) > 40:
        print(f"    ... und {len(fehlend) - 40} weitere")
    print("\n  Nichts löschen, bevor das geklärt ist.")
    return 1

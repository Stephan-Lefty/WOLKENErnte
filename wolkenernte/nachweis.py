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
from pathlib import Path

from .lokal import MEDIEN, Ordner
from .takeout import Archiv as Takeout


def _ist_medium(name: str) -> bool:
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


def archiv_kennungen(archiv: Path) -> set[tuple[int, int]]:
    """Größe und Prüfsumme jeder Datei im Archiv."""
    kennungen: set[tuple[int, int]] = set()
    dateien = [p for p in archiv.rglob("*") if p.is_file() and _ist_medium(p.name)]
    for nummer, pfad in enumerate(dateien, 1):
        if nummer % 1000 == 0:
            print(f"  Archiv {nummer}/{len(dateien)}", end="\r", flush=True)
        try:
            summe = 0
            with pfad.open("rb") as datei:
                while brocken := datei.read(1 << 20):
                    summe = zlib.crc32(brocken, summe)
            kennungen.add((pfad.stat().st_size, summe))
        except OSError as fehler:
            print(f"  ! {pfad.name}: {fehler}")
    print(f"  {len(dateien)} Dateien im Archiv, "
          f"{len(kennungen)} verschiedene Inhalte      ")
    return kennungen


def pruefen(archiv: Path, quellen: list[Path]) -> int:
    t0 = time.time()
    print(f"=== Archiv: {archiv} ===")
    vorhanden = archiv_kennungen(archiv)

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

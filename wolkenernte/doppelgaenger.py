"""Doppelgänger im Archiv finden – gleiche Bilder in verschiedenen Dateien.

Bytegleiche Kopien gibt es im Archiv keine mehr; die hat schon das
Ernten aussortiert. Was bleibt, ist der schwierigere Fall: **dasselbe
Foto in zwei Fassungen.** Einmal das Original von der Kamera, einmal die
Version, die durch einen Messenger gelaufen ist. Verschiedene Dateien,
verschiedene Größe, dasselbe Bild.

Der Fingerabdruck dafür steckt in :mod:`wolkenernte.aehnlich`, die
Aufbewahrung in :mod:`wolkenernte.bestand`. Hier wird beides verbunden:
einmal rechnen, dann nachschlagen. **Das Rechnen dauert Minuten, das
Nachschlagen Sekundenbruchteile** – deshalb wird es aufbewahrt und nicht
bei jedem Aufruf wiederholt.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .aehnlich import SCHWELLE, fingerabdruck, gruppen
from .bestand import ORT, Bestand


def rechnen(
    archiv: Path,
    *,
    fortschritt: Callable[[int, int], None] | None = None,
) -> int:
    """Fehlende Fingerabdrücke nachrechnen. Gibt zurück, wie viele.

    Videos bekommen keinen: Für ein Standbild daraus bräuchte es
    ffmpeg, und das ist noch nicht eingebaut. Sie werden mit dem Wert 0
    vermerkt, damit sie nicht bei jedem Lauf erneut versucht werden.
    """
    if not (archiv / ORT).exists():
        return 0

    gerechnet = 0
    with Bestand(archiv) as bestand:
        offen = bestand.ohne_fingerabdruck()
        for nummer, (kennung, pfad) in enumerate(offen, 1):
            if fortschritt:
                fortschritt(nummer, len(offen))
            wert = fingerabdruck(archiv / pfad)
            # 0 heißt hier: versucht, nichts dabei herausgekommen.
            # Ohne diesen Vermerk liefe jeder Aufruf erneut über
            # dieselben Videos und beschädigten Dateien.
            bestand.fingerabdruck_merken(kennung, wert if wert is not None else 0)
            gerechnet += 1
            if gerechnet % 500 == 0:
                bestand.sichern()
        bestand.sichern()
    return gerechnet


def finden(archiv: Path, *, schwelle: int = SCHWELLE) -> list[list[str]]:
    """Die Gruppen ähnlicher Bilder, größte zuerst."""
    if not (archiv / ORT).exists():
        return []
    with Bestand(archiv) as bestand:
        return gruppen(bestand.fingerabdruecke(), schwelle=schwelle)


def bericht(archiv: Path) -> int:
    """Der Befehl ``wolkenernte doppelt``."""
    if not (archiv / ORT).exists():
        print(f"Keine Datenbank in {archiv}.")
        print("Erst »wolkenernte erfassen« laufen lassen.")
        return 1

    with Bestand(archiv) as bestand:
        offen = len(bestand.ohne_fingerabdruck())

    if offen:
        print(f"{offen} Bilder haben noch keinen Fingerabdruck. Wird nachgeholt –")
        print("das dauert beim ersten Mal einige Minuten.")
        t0 = time.time()
        rechnen(archiv, fortschritt=lambda n, g: (
            print(f"  {n}/{g}", end="\r", flush=True) if n % 200 == 0 else None
        ))
        print(f"  fertig in {(time.time()-t0)/60:.1f} Minuten          ")

    t0 = time.time()
    treffer = finden(archiv)
    ueberzaehlig = sum(len(g) - 1 for g in treffer)

    print(f"\n{len(treffer)} Gruppen ähnlicher Bilder, "
          f"{ueberzaehlig} überzählige Fassungen "
          f"(gesucht in {time.time()-t0:.1f}s)\n")

    for gruppe in treffer[:20]:
        groessen = []
        for pfad in gruppe:
            datei = archiv / pfad
            groessen.append(datei.stat().st_size if datei.exists() else 0)
        print(f"  {len(gruppe)} Fassungen:")
        for pfad, groesse in sorted(zip(gruppe, groessen), key=lambda p: -p[1]):
            print(f"    {groesse/1e6:6.2f} MB  {pfad}")
        print()

    if len(treffer) > 20:
        print(f"  ... und {len(treffer) - 20} weitere Gruppen.")
    if treffer:
        print("Nichts wurde gelöscht. Die Oberfläche zeigt die Gruppen "
              "nebeneinander,\nsodass man vergleichen kann, bevor man "
              "sich entscheidet.")
    return 0

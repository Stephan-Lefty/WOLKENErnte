#!/usr/bin/env python3
"""Erzeugt aus den SVG-Quellen alle Programmsymbole.

    python3 werkzeuge/symbole.py

**Warum es drei Quellen gibt und nicht eine.** Ein Symbol, das bei 512
Pixeln gut aussieht, ist bei 16 Pixeln ein Fleck. Beim Verkleinern
verschwinden nicht alle Bestandteile gleichmäßig, sondern die feinsten
zuerst - und was übrig bleibt, ist dann kein reduziertes Bild, sondern
ein zerfallenes. Deshalb wird für die kleinen Größen nicht dasselbe
Bild kleiner gerechnet, sondern ein eigenes, ärmeres gezeichnet.

Ohne diese Datei wüsste in einem halben Jahr niemand mehr, dass
``icon-16.png`` nicht aus ``icon.svg`` stammt - und würde es beim
nächsten Mal versehentlich daraus neu erzeugen.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

#: Welche Quelle für welche Größe gilt.
#:
#: Die Grenzen sind erprobt, nicht geraten: Bei 48 Pixeln trägt das
#: volle Bild noch, bei 32 zerfällt der Filmstreifen zu einem grauen
#: Rechteck, und bei 16 frisst die Bildkachel die Wolke von innen auf.
QUELLEN: dict[str, tuple[int, ...]] = {
    "icon.svg": (48, 64, 128, 256, 512, 1024),
    "icon-klein.svg": (24, 32),
    "icon-winzig.svg": (16,),
}

#: Was in die .ico für Windows kommt.
ICO_GROESSEN = (16, 32, 48, 64, 128, 256)


def _werkzeug(name: str) -> str:
    pfad = shutil.which(name)
    if not pfad:
        sys.exit(f"{name} fehlt. Unter Manjaro: pacman -S librsvg imagemagick")
    return pfad


def erzeugen() -> list[Path]:
    """Alle PNG erzeugen. Gibt die geschriebenen Dateien zurück."""
    rsvg = _werkzeug("rsvg-convert")
    geschrieben: list[Path] = []

    for quelle, groessen in QUELLEN.items():
        pfad = ASSETS / quelle
        if not pfad.exists():
            sys.exit(f"{pfad} fehlt.")
        for groesse in groessen:
            ziel = ASSETS / f"icon-{groesse}.png"
            subprocess.run(
                [rsvg, "-w", str(groesse), "-h", str(groesse),
                 str(pfad), "-o", str(ziel)],
                check=True,
            )
            geschrieben.append(ziel)
            print(f"{ziel.name:<16} aus {quelle}")

    # icon.png ist die Fassung, die READMEs und Paketbauer erwarten.
    ziel = ASSETS / "icon.png"
    subprocess.run(
        [rsvg, "-w", "512", "-h", "512", str(ASSETS / "icon.svg"), "-o", str(ziel)],
        check=True,
    )
    geschrieben.append(ziel)
    print(f"{ziel.name:<16} aus icon.svg")
    return geschrieben


def ico_bauen() -> Path:
    """Die .ico für Windows aus den fertigen PNG zusammensetzen.

    Aus den PNG und nicht aus der SVG: Nur so landet für jede Größe die
    Fassung in der Datei, die für sie gezeichnet wurde. Ein ``magick
    icon.svg -define icon:auto-resize=...`` nähme für alle Größen die
    große Quelle - und genau das soll hier ja vermieden werden.
    """
    magick = _werkzeug("magick")
    ziel = ASSETS / "wolkenernte.ico"
    ziel.unlink(missing_ok=True)
    subprocess.run(
        [magick, *[str(ASSETS / f"icon-{g}.png") for g in ICO_GROESSEN], str(ziel)],
        check=True,
    )
    print(f"{ziel.name:<16} aus {', '.join(f'icon-{g}.png' for g in ICO_GROESSEN)}")
    return ziel


if __name__ == "__main__":
    erzeugen()
    ico_bauen()

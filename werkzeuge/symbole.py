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

#: Wohin die Fassungen kopiert werden, die das Programm selbst braucht.
#:
#: **Zwei Orte, ein Ursprung.** ``assets/`` bleibt die Vorlage für alles
#: außerhalb des Programms - Menüeintrag, Windows-Symboldatei, Bilder im
#: README. Aber ``assets/`` gehört nicht zum Python-Paket, und deshalb
#: stand ein installiertes WOLKENErnte ohne Symbol da, ohne dass
#: irgendwo etwas fehlschlug. Was das Fenster braucht, muss ins Paket.
IM_PAKET = Path(__file__).resolve().parent.parent / "wolkenernte/daten/symbole"

#: Welche Größen das Programm selbst braucht.
#:
#: Nicht alle: 512 und 1024 sind für Paketbauer und Bildschirmfotos da,
#: nicht für die Fensterleiste. Sie würden das Wheel nur aufblähen.
FUERS_PROGRAMM = (16, 24, 32, 48, 64, 128, 256)

#: Welche Quelle für welche Größe gilt.
#:
#: Die Grenzen sind erprobt, nicht geraten: Bei 48 Pixeln trägt das
#: volle Bild noch, bei 32 zerfällt der Filmstreifen zu einem grauen
#: Rechteck, und bei 16 frisst die Bildkachel die Wolke von innen auf.
#:
#: **Ab 48 Pixeln gilt das Original**, ``icon-quelle.png``. Es ist von
#: Hand entworfen und wird nur verkleinert, nicht nachgebaut. Ein
#: früherer Versuch, es als SVG nachzuzeichnen, geriet zu einer eigenen
#: Auslegung - andere Kachelgrößen, ein Gipfel statt zwei, sechs statt
#: acht Filmlöcher. Wer hier etwas ändern will, ändert bitte die
#: Bilddatei, nicht diesen Eintrag.
QUELLEN: dict[str, tuple[int, ...]] = {
    "icon-quelle.png": (48, 64, 128, 256, 512, 1024),
    "icon-klein.svg": (24, 32),
    "icon-winzig.svg": (16,),
}

#: Aus welcher Quelle ``icon.png`` entsteht - die Fassung, die READMEs
#: und Paketbauer erwarten.
HAUPTBILD = ("icon-quelle.png", 512)

#: Was in die .ico für Windows kommt.
ICO_GROESSEN = (16, 32, 48, 64, 128, 256)


def _werkzeug(name: str) -> str:
    pfad = shutil.which(name)
    if not pfad:
        sys.exit(f"{name} fehlt. Unter Manjaro: pacman -S librsvg imagemagick")
    return pfad


def _umrechnen(quelle: Path, groesse: int, ziel: Path) -> None:
    """Eine Quelle in einer Größe ablegen.

    SVG wird gerastert, PNG verkleinert. Beim Verkleinern ausdrücklich
    ``-filter Lanczos``: ImageMagick wählt sonst je nach Fassung einen
    anderen Filter, und dann sähe dasselbe Symbol auf zwei Rechnern
    unterschiedlich scharf aus.
    """
    if quelle.suffix.lower() == ".svg":
        subprocess.run(
            [_werkzeug("rsvg-convert"), "-w", str(groesse), "-h", str(groesse),
             str(quelle), "-o", str(ziel)],
            check=True,
        )
    else:
        subprocess.run(
            [_werkzeug("magick"), str(quelle), "-filter", "Lanczos",
             "-resize", f"{groesse}x{groesse}", "-strip", str(ziel)],
            check=True,
        )


def erzeugen() -> list[Path]:
    """Alle PNG erzeugen. Gibt die geschriebenen Dateien zurück."""
    geschrieben: list[Path] = []

    for quelle, groessen in QUELLEN.items():
        pfad = ASSETS / quelle
        if not pfad.exists():
            sys.exit(f"{pfad} fehlt.")
        for groesse in groessen:
            ziel = ASSETS / f"icon-{groesse}.png"
            _umrechnen(pfad, groesse, ziel)
            geschrieben.append(ziel)
            print(f"{ziel.name:<16} aus {quelle}")

    name, groesse = HAUPTBILD
    ziel = ASSETS / "icon.png"
    _umrechnen(ASSETS / name, groesse, ziel)
    geschrieben.append(ziel)
    print(f"{ziel.name:<16} aus {name}")
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


def ins_paket_kopieren() -> list[Path]:
    """Die Fassungen, die das Programm braucht, ins Paket legen.

    Kopieren statt verweisen: Ein Symlink überlebt weder das Bauen
    eines Wheels noch Windows.
    """
    IM_PAKET.mkdir(parents=True, exist_ok=True)
    kopiert: list[Path] = []
    for name in [f"icon-{g}.png" for g in FUERS_PROGRAMM] + ["wolkenernte.ico"]:
        quelle = ASSETS / name
        if not quelle.exists():
            sys.exit(f"{quelle} fehlt - erst erzeugen().")
        ziel = IM_PAKET / name
        shutil.copyfile(quelle, ziel)
        kopiert.append(ziel)
    print(f"{len(kopiert)} Dateien nach {IM_PAKET.name}/ kopiert")
    return kopiert


if __name__ == "__main__":
    erzeugen()
    ico_bauen()
    ins_paket_kopieren()

"""Die Fensteranwendung – WOLKENErnte ohne Browser.

Braucht **PySide6**, das rund hundert Megabyte wiegt und deshalb nicht
zum Kern gehört. Wer es nicht will, benutzt weiter die Weboberfläche:
Beide sitzen auf demselben Fundament, ``wolkenernte.bestandsliste``.

    wolkenernte fenster <Archiv>
"""

from __future__ import annotations

from pathlib import Path

FEHLT = (
    "PySide6 ist nicht installiert – ohne das gibt es kein Fenster.\n"
    "  Arch und Manjaro:  pacman -S pyside6\n"
    "  Debian und Ubuntu: apt install python3-pyside6.qtwidgets\n\n"
    "Die Weboberfläche läuft auch ohne:\n"
    "  wolkenernte oberflaeche <Archiv>"
)


def starten(archiv: Path) -> int:
    """Das Fenster öffnen, oder verständlich sagen, warum nicht."""
    try:
        from .hauptfenster import starten as fenster_starten
    except ImportError:
        print(FEHLT)
        return 1
    return fenster_starten(archiv)

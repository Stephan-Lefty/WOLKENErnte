"""Das Wenige, was sich das Programm zwischen zwei Aufrufen merkt.

Bisher genau eines: **welches Archiv zuletzt offen war.** Der
Menüeintrag im Anwendungsmenü übergibt keinen Pfad – er kann keinen
kennen –, und ein Programm, das beim Anklicken nach einem Ordner fragt,
den es beim letzten Mal schon kannte, ist lästig.

Abgelegt nach XDG-Konvention, also dort, wo Einstellungen unter Linux
hingehören: ``~/.config/wolkenernte/``. Als schlichte Textdatei, nicht
als JSON oder INI – bei einem einzigen Wert wäre alles andere Aufwand
ohne Gegenwert, und man kann sie mit jedem Editor reparieren.
"""

from __future__ import annotations

import os
from pathlib import Path


def ordner() -> Path:
    """Wo die Einstellungen liegen."""
    grund = os.environ.get("XDG_CONFIG_HOME")
    wurzel = Path(grund) if grund else Path.home() / ".config"
    return wurzel / "wolkenernte"


def _datei() -> Path:
    return ordner() / "zuletzt"


def letztes_archiv() -> Path | None:
    """Das zuletzt geöffnete Archiv – oder ``None``.

    Gibt auch dann ``None`` zurück, wenn der Pfad zwar vermerkt ist, es
    ihn aber nicht mehr gibt. Ein Verweis auf einen gelöschten Ordner
    ist keine brauchbare Vorgabe, sondern eine Fehlermeldung in spe.
    """
    try:
        text = _datei().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    pfad = Path(text).expanduser()
    return pfad if pfad.is_dir() else None


def archiv_merken(archiv: Path) -> None:
    """Den Pfad für das nächste Mal vermerken.

    Schlägt das fehl – etwa auf einem Nur-Lese-Dateisystem –, ist das
    kein Grund, irgendetwas abzubrechen. Dann fragt das Programm eben
    beim nächsten Mal wieder.
    """
    try:
        ordner().mkdir(parents=True, exist_ok=True)
        _datei().write_text(str(archiv.resolve()) + "\n", encoding="utf-8")
    except OSError:
        pass

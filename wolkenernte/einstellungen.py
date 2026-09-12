"""Das Wenige, was sich das Programm zwischen zwei Aufrufen merkt.

Zwei Pfade: **welches Archiv zuletzt offen war** und **wo die
Takeout-Dateien lagen**. Der Menüeintrag im Anwendungsmenü übergibt
keinen Pfad – er kann keinen kennen –, und ein Programm, das beim
Anklicken nach einem Ordner fragt, den es beim letzten Mal schon
kannte, ist lästig.

**Beim Takeout wiegt das mehr als Bequemlichkeit.** Ein Export liegt
selten unter ``~/Downloads``: Neun Gigabyte wandern auf die Platte, auf
der Platz ist, und die heißt dann ``/mnt/raid/…`` oder hängt an einem
USB-Anschluss. Wer sich dorthin jedes Mal neu durchklicken muss, sucht
beim zweiten Export länger als beim ersten.

Abgelegt nach XDG-Konvention, also dort, wo Einstellungen unter Linux
hingehören: ``~/.config/wolkenernte/``. Als schlichte Textdateien, eine
je Wert – bei so wenig wäre JSON oder INI Aufwand ohne Gegenwert, und
man kann sie mit jedem Editor reparieren.
"""

from __future__ import annotations

import os
from pathlib import Path


def ordner() -> Path:
    """Wo die Einstellungen liegen."""
    grund = os.environ.get("XDG_CONFIG_HOME")
    wurzel = Path(grund) if grund else Path.home() / ".config"
    return wurzel / "wolkenernte"


def _datei(name: str = "zuletzt") -> Path:
    return ordner() / name


def _gemerkt(name: str) -> Path | None:
    """Ein vermerkter Ordner – oder ``None``, wenn es ihn nicht gibt.

    Ein Verweis auf einen gelöschten Ordner ist keine brauchbare
    Vorgabe, sondern eine Fehlermeldung in spe. Das trifft besonders
    einen Wechseldatenträger: Wer den Export auf einem USB-Stick hatte,
    soll nicht dessen alten Pfad angeboten bekommen, sondern eine
    Auswahl, die es wirklich gibt.
    """
    try:
        text = _datei(name).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    pfad = Path(text).expanduser()
    return pfad if pfad.is_dir() else None


def _merken(name: str, pfad: Path) -> None:
    """Schlägt das fehl – etwa auf einem Nur-Lese-Dateisystem –, ist das
    kein Grund, irgendetwas abzubrechen. Dann fragt das Programm eben
    beim nächsten Mal wieder."""
    try:
        ordner().mkdir(parents=True, exist_ok=True)
        _datei(name).write_text(str(pfad.resolve()) + "\n", encoding="utf-8")
    except OSError:
        pass


def letztes_archiv() -> Path | None:
    """Das zuletzt geöffnete Archiv – oder ``None``."""
    return _gemerkt("zuletzt")


def archiv_merken(archiv: Path) -> None:
    """Den Pfad für das nächste Mal vermerken."""
    _merken("zuletzt", archiv)


def letzter_takeout_ordner() -> Path | None:
    """Wo zuletzt Takeout-Dateien lagen – oder ``None``."""
    return _gemerkt("takeout-ordner")


def takeout_ordner_merken(pfad: Path) -> None:
    """Den Ordner der Takeout-Dateien vermerken."""
    _merken("takeout-ordner", pfad)

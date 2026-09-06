#!/usr/bin/env python3
"""Spielt Qt die Videos eines Archivs wirklich ab?

    python3 werkzeuge/videoprobe.py <Archiv>

**Wozu.** Bevor eine Fensteranwendung auf ``QMediaPlayer`` gebaut wird,
muss feststehen, dass der die vorhandenen Videos auch darstellt. Qt
bringt seit Fassung 6.5 ein eigenes FFmpeg mit, und dessen Umfang ist
nicht dokumentiert: Es enthält nur, was unter einer freizügigen Lizenz
steht. Die H.264- und HEVC-*Dekoder* sind LGPL und sollten dabei sein –
sollten. Das ist Papierlage, und Papierlage hat sich in diesem Projekt
schon zweimal geirrt.

**Was hier geprüft wird, ist nicht »startet der Player«** – das tut er
immer. Geprüft wird, ob **tatsächlich ein Einzelbild ankommt**. Dafür
hängt sich die Probe an ``QVideoSink`` und wartet auf den ersten
Rückruf. Kommt keiner, ist das Format unbrauchbar, auch wenn nirgends
ein Fehler gemeldet wurde.

Läuft ohne Fenster, ist also für die Kommandozeile geeignet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Vor dem Qt-Import setzen, sonst wirken sie nicht.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")

VIDEOS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".m2ts", ".3gp"}

#: Wie lange auf das erste Bild gewartet wird.
FRIST_MS = 12_000


def codec(pfad: Path) -> str:
    """Der Videocodec einer Datei, über ffprobe."""
    try:
        ergebnis = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(pfad)],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    zeilen = ergebnis.stdout.strip().rstrip(",").splitlines()
    return zeilen[0].strip().rstrip(",") if zeilen else ""


def anspielen(pfad: Path, frist_ms: int = FRIST_MS) -> tuple[bool, str]:
    """Ein Video anspielen. Kam ein Bild an?"""
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    spieler = QMediaPlayer()
    senke = QVideoSink()
    spieler.setVideoSink(senke)

    stand = {"bild": False, "fehler": "", "groesse": ""}

    def bild_kam(rahmen) -> None:
        if rahmen.isValid() and not stand["bild"]:
            stand["bild"] = True
            stand["groesse"] = f"{rahmen.width()}x{rahmen.height()}"
            app.quit()

    def fehler(_, text) -> None:
        stand["fehler"] = text or "unbekannt"
        app.quit()

    senke.videoFrameChanged.connect(bild_kam)
    spieler.errorOccurred.connect(fehler)
    spieler.setSource(QUrl.fromLocalFile(str(pfad)))
    spieler.play()

    QTimer.singleShot(frist_ms, app.quit)
    app.exec()

    spieler.stop()
    spieler.setSource(QUrl())

    if stand["bild"]:
        return True, stand["groesse"]
    return False, stand["fehler"] or "kein Bild innerhalb der Frist"


def probe(archiv: Path, hoechstens: int = 8) -> int:
    if not archiv.is_dir():
        print(f"Kein Archiv: {archiv}")
        return 1

    try:
        import PySide6  # noqa: F401
    except ImportError:
        print("PySide6 fehlt – ohne das gibt es keine Fensteranwendung.")
        print("Unter Arch und Manjaro: pacman -S pyside6")
        return 1

    print(f"Archiv: {archiv}")
    print("Je Codec wird ein Beispiel angespielt.\n")

    beispiele: dict[str, Path] = {}
    for pfad in sorted(archiv.rglob("*")):
        if not pfad.is_file() or pfad.suffix.lower() not in VIDEOS:
            continue
        art = codec(pfad)
        if art and art not in beispiele:
            beispiele[art] = pfad
        if len(beispiele) >= hoechstens:
            break

    if not beispiele:
        print("Keine Videos gefunden.")
        return 0

    fehlgeschlagen = []
    for art, pfad in sorted(beispiele.items()):
        geklappt, hinweis = anspielen(pfad)
        print(f"  {art:8} {'ja  ' if geklappt else 'NEIN'}  {hinweis}")
        if not geklappt:
            fehlgeschlagen.append(art)

    print()
    if fehlgeschlagen:
        print(f"Qt spielt nicht ab: {', '.join(fehlgeschlagen)}")
        print("\nDann bräuchte die Fensteranwendung libmpv als Rückfall –")
        print("und zwar als LGPL-Bau, sonst steckt das Programm in der GPL.")
        return 1

    print("Qt spielt alle Formate dieses Archivs ab.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Aufruf: {sys.argv[0]} <Archiv>")
    raise SystemExit(probe(Path(sys.argv[1]).expanduser()))

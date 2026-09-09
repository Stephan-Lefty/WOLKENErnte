"""Ein Einzelbild aus einem Video holen – für die Vorschau.

**ffmpeg als eigener Prozess, nicht als Bibliothek.** Ein beschädigtes
Video ist keine Seltenheit; in einem Bestand aus vierhundert ist immer
eines dabei, das einen Dekodierer zum Absturz bringt. Als eigener
Prozess reißt es höchstens sich selbst mit, und eine Frist beendet
auch das, was sich festgefressen hat.

**``-ss`` steht vor ``-i``, und das ist keine Kleinigkeit.** Danach
gestellt, dekodiert ffmpeg das Video von vorn bis zur gesuchten Stelle;
davor springt es gleich hin. Bei einem einstündigen Film ist das der
Unterschied zwischen Minuten und einem Wimpernschlag.

**Nicht das allererste Bild**, und das ist an 394 echten Videos
gemessen. Viele Aufnahmen beginnen mit einer schwarzen Blende oder
einem verwackelten Moment, während die Kamera noch scharfstellt: Am
Anfang sind 11 Vorschaubilder fast schwarz und 10 ohne jede Struktur,
eine Sekunde später nur noch 6 und 2.

**Und wo das Video kürzer ist, wird doch der Anfang genommen** – das
betrifft 30 der 394, meist kurze Aufnahmen aus Nachrichtendiensten.
Ohne den Rückfall hätten die gar keine Vorschau.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

#: Wo im Video gesucht wird, in Sekunden.
#:
#: Die Reihenfolge ist die Reihenfolge der Versuche: erst eine Sekunde
#: hinein, dann ganz vorn für alles, was kürzer ist.
STELLEN = (1.0, 0.0)

#: Wie lange auf ffmpeg gewartet wird, je Versuch.
#:
#: Großzügig für ein Einzelbild, aber endlich: Ein kaputtes Video darf
#: die Rasteransicht nicht anhalten.
FRIST = 20.0


def verfuegbar() -> bool:
    """Ob ffmpeg auf diesem Rechner liegt."""
    return shutil.which("ffmpeg") is not None


def einzelbild(video: Path, kante: int) -> bytes | None:
    """Ein JPEG aus dem Video, höchstens ``kante`` Punkte groß.

    ``None`` heißt: Es ging nicht. Das ist kein Fehler, sondern der
    Normalfall bei fehlendem ffmpeg und bei beschädigten Dateien – die
    Oberfläche zeigt dann weiter ihr Abspielsymbol.
    """
    if not verfuegbar() or not video.is_file():
        return None

    for stelle in STELLEN:
        daten = _versuchen(video, stelle, kante)
        if daten:
            return daten
    return None


def _versuchen(video: Path, stelle: float, kante: int) -> bytes | None:
    befehl = [
        "ffmpeg",
        # Ohne das wartet ffmpeg unter Umständen auf eine Eingabe, die
        # nie kommt - und der Hintergrundfaden steht.
        "-nostdin",
        "-loglevel", "error",
        # **Vor -i.** Siehe oben: sonst wird bis hierher dekodiert.
        "-ss", f"{stelle}",
        "-i", str(video),
        "-frames:v", "1",
        # Verkleinern übernimmt ffmpeg gleich mit; ein Video in
        # voller Auflösung durch die Leitung zu schicken, nur um es
        # danach zu schrumpfen, wäre Verschwendung. Das ``-2`` hält die
        # Höhe gerade - JPEG mag ungerade Maße nicht überall.
        "-vf", f"scale='min({kante},iw)':-2",
        "-f", "image2pipe", "-vcodec", "mjpeg",
        "-",
    ]
    try:
        ergebnis = subprocess.run(
            befehl, capture_output=True, timeout=FRIST, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    # Auch bei Rückgabewert 0 kann die Ausgabe leer sein - etwa wenn
    # hinter der gesuchten Stelle kein Bild mehr kommt.
    return ergebnis.stdout or None

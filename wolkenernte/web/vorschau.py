"""Vorschaubilder erzeugen und aufbewahren.

**Warum überhaupt.** Das Archiv wiegt 29 GB. Ein Raster mit zweihundert
Bildern würde ohne Verkleinerung ein halbes Gigabyte durch die Leitung
schicken, und der Browser müsste jedes davon voll dekodieren, um es
briefmarkengroß anzuzeigen.

**Warum in einem eigenen Ordner und nicht neben den Bildern.** Das
Archiv soll nur enthalten, was der Anwender selbst hineingetan hat. Wer
später hineinsieht, soll Fotos finden und keine Verwaltungsdateien.

Ohne Pillow gibt es keine Vorschau. Dann liefert die Oberfläche das
Original aus – langsamer, aber sie bleibt benutzbar. Ein Bildbetrachter,
der ohne Zusatzpaket gar nicht startet, wäre die schlechtere Lösung.

**Videos gehen denselben Weg**, nur holt bei ihnen ffmpeg das Bild aus
der Datei statt Pillow (:mod:`wolkenernte.video`). Für alles danach –
Zwischenspeicher, Dateiname, Rückgabewert – ist kein Unterschied mehr,
und beide Oberflächen bekommen die Vorschau geschenkt.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..bestandsliste import VIDEOS

#: Kantenlänge der Vorschaubilder. 400 statt 200: Auf einem Bildschirm
#: mit doppelter Punktdichte sind 200 Punkte bereits 400 Bildpunkte, und
#: verwaschene Vorschaubilder sehen nach kaputt aus.
KANTE = 400

#: Wo die Vorschaubilder liegen, relativ zum Archiv.
ORT = ".wolkenernte/vorschau"


def verfuegbar() -> bool:
    """Ob Vorschaubilder erzeugt werden können."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


def _ziel(archiv: Path, pfad: str) -> Path:
    """Wohin das Vorschaubild gehört.

    Der Name ist ein Streuwert des Archivpfads, keine Nachbildung der
    Ordnerstruktur: Umlaute, Leerzeichen und Emoji in Albumnamen machen
    sonst Ärger, und zwei Ordnerbäume auseinanderzuhalten ist mühsamer
    als ein flacher Ordner mit eindeutigen Namen.

    Zwei Ebenen Unterordner, damit nicht fünfzehntausend Dateien in
    einem Verzeichnis liegen – das bringt manche Dateisysteme und die
    meisten Dateimanager ins Schwitzen.
    """
    fingerabdruck = hashlib.sha256(pfad.encode("utf-8")).hexdigest()
    return archiv / ORT / fingerabdruck[:2] / f"{fingerabdruck}.jpg"


def hole(archiv: Path, pfad: str) -> bytes | None:
    """Das Vorschaubild zu einem Archivbild oder Video – erzeugt es notfalls.

    Gibt ``None`` zurück, wenn keines erzeugt werden kann. Das ist kein
    Fehler, sondern der Normalfall bei fehlendem Pillow, fehlendem
    ffmpeg und beschädigten Dateien – die Oberfläche zeigt dann ihr
    Abspiel- beziehungsweise Platzhaltersymbol.
    """
    ziel = _ziel(archiv, pfad)
    if ziel.exists():
        try:
            gemerkt = ziel.read_bytes()
        except OSError:
            gemerkt = None
        # Eine leere Datei heißt: schon versucht, ging nicht. Ohne diese
        # Notiz liefe die Oberfläche bei jedem Aufbau des Rasters wieder
        # in dieselbe ffmpeg-Frist - bei einem beschädigten Video wären
        # das zwanzig Sekunden Stillstand, jedes Mal aufs Neue.
        if gemerkt is not None:
            return gemerkt or None

    quelle = archiv / pfad
    if not quelle.is_file():
        return None

    if quelle.suffix.lower() in VIDEOS:
        return _aus_video(quelle, ziel)
    return _aus_bild(quelle, ziel)


def _aus_video(quelle: Path, ziel: Path) -> bytes | None:
    """Ein Einzelbild aus dem Video, notfalls ein Fehlschlag mit Gedächtnis."""
    from .. import video

    daten = video.einzelbild(quelle, KANTE)
    if daten:
        _merken(ziel, daten)
        return daten
    # Nur wenn ffmpeg **da** ist, war es ein echter Fehlschlag. Fehlt es
    # bloß, darf das nicht auf Dauer festgeschrieben werden - sonst
    # bliebe das Video auch nach der Installation ohne Vorschau.
    if video.verfuegbar():
        _merken(ziel, b"")
    return None


def _aus_bild(quelle: Path, ziel: Path) -> bytes | None:
    """Das verkleinerte Foto – der Weg über Pillow."""
    try:
        import io

        from PIL import Image, ImageOps
    except ImportError:
        return None

    try:
        with Image.open(quelle) as bild:
            # draft() lässt den JPEG-Dekodierer gleich verkleinert
            # arbeiten, statt das volle Bild aufzubauen und danach zu
            # schrumpfen. Bei großen Aufnahmen ist das der Unterschied
            # zwischen flüssig und zäh.
            bild.draft("RGB", (KANTE * 2, KANTE * 2))
            bild = ImageOps.exif_transpose(bild)
            bild.thumbnail((KANTE, KANTE), Image.Resampling.LANCZOS)
            if bild.mode not in ("RGB", "L"):
                bild = bild.convert("RGB")

            puffer = io.BytesIO()
            bild.save(puffer, "JPEG", quality=82, optimize=True)
            daten = puffer.getvalue()
    except Exception:
        # Pillow wirft bei beschädigten Bildern die verschiedensten
        # Fehler. Für die Oberfläche ist jeder davon dasselbe: kein
        # Vorschaubild. Ein kaputtes Foto darf die Ansicht nicht
        # abbrechen - in einem Bestand von fünfzehntausend ist immer
        # eines dabei.
        return None

    _merken(ziel, daten)
    return daten


def _merken(ziel: Path, daten: bytes) -> None:
    """In den Zwischenspeicher legen – ein Fehlschlag ist keiner."""
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(daten)
    except OSError:
        pass  # Ohne Zwischenspeicher ist es langsamer, aber es geht.

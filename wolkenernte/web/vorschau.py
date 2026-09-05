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
"""

from __future__ import annotations

import hashlib
from pathlib import Path

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
    """Das Vorschaubild zu einem Archivbild – erzeugt es notfalls.

    Gibt ``None`` zurück, wenn keines erzeugt werden kann. Das ist kein
    Fehler: Videos haben hier noch keines, und ohne Pillow gibt es gar
    keine.
    """
    ziel = _ziel(archiv, pfad)
    if ziel.exists():
        try:
            return ziel.read_bytes()
        except OSError:
            pass

    quelle = archiv / pfad
    if not quelle.is_file():
        return None

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

    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(daten)
    except OSError:
        pass  # Ohne Zwischenspeicher ist es langsamer, aber es geht.
    return daten

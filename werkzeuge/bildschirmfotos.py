#!/usr/bin/env python3
"""Die Bildschirmfotos für README und Anleitungen erzeugen.

    python3 werkzeuge/bildschirmfotos.py

**Warum ein erfundenes Archiv und nicht das echte.** Ein Bildschirmfoto
aus dem eigenen Bestand zeigt Urlaubsziele, Wohnorte, Gesichter und
Albumnamen – im Kleinformat kaum lesbar, in der Bilddatei aber
vollständig vorhanden. Ein öffentliches Repository ist der falsche Ort
dafür. Hier entsteht deshalb ein Archiv aus **gerechneten** Bildern:
Farbverläufe, eine Sonne, ein paar Hügelketten. Von Weitem sieht es aus
wie Fotos, aus der Nähe ist es Arithmetik.

**Und es läuft durch das echte Programm.** Die Bilder werden geerntet,
erfasst und verschlagwortet wie jeder andere Bestand auch. Was auf dem
Bildschirmfoto steht – Jahreszahlen, Albumnamen, Anzahlen, Schlagwörter
–, hat WOLKENErnte selbst ausgerechnet. Ein nachgestelltes Bild wäre
schneller gemacht und wäre eine Behauptung.

Verschlagwortet wird ``--ohne-bilderkennung``: Jahreszeit, Tageszeit
und Bildformat stimmen auch bei gerechneten Bildern, das Modell dagegen
sähe hier Dinge, die niemand hineingelegt hat.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

ZIEL = WURZEL / "docs" / "bilder"

#: Wohin das erfundene Archiv kommt. Nicht ins Repository – es wiegt
#: ein paar Megabyte und ist in einer Minute neu gerechnet.
WERKSTATT = Path(os.environ.get("TMPDIR", "/tmp")) / "wolkenernte-schaufenster"

#: Die Alben. **Platzhalter, mit Absicht farblos gewählt** – die
#: ursprünglichen Namen aus dem echten Bestand verrieten Wohnort und
#: Urlaubsziel.
ALBEN = ("Nordsee 2023", "Bergtour 2024", "Mein Viertel")


# -- Die Bilder --------------------------------------------------------------

#: Fünf Stimmungen, jede mit Himmelsfarben oben und unten, einer
#: Sonnenfarbe und der Farbe der vordersten Hügelkette.
STIMMUNGEN = (
    ("morgen", (28, 42, 88), (247, 183, 140), (255, 236, 190), (18, 24, 40)),
    ("mittag", (58, 122, 206), (183, 219, 246), (255, 252, 235), (34, 58, 46)),
    ("abend", (46, 30, 74), (233, 118, 74), (255, 208, 128), (22, 16, 30)),
    ("nebel", (150, 158, 168), (214, 218, 222), (232, 234, 236), (72, 78, 84)),
    ("winter", (96, 122, 158), (222, 232, 242), (250, 250, 252), (58, 66, 78)),
)


def _mischen(a, b, anteil: float):
    return tuple(round(x + (y - x) * anteil) for x, y in zip(a, b))


def _landschaft(breite: int, hoehe: int, samen: int):
    """Ein Bild rechnen, das aus der Ferne wie eine Aufnahme aussieht.

    Kein Rauschen, keine Textur – für eine 180 Pixel breite Kachel
    zählt nur die Silhouette. Wer das Bild groß ansieht, soll sofort
    erkennen, dass hier nichts Echtes steht.
    """
    from PIL import Image, ImageDraw, ImageFilter

    wuerfel = random.Random(samen)
    _, oben, unten, sonne, berg = STIMMUNGEN[samen % len(STIMMUNGEN)]

    bild = Image.new("RGB", (breite, hoehe))
    zeichner = ImageDraw.Draw(bild)

    horizont = int(hoehe * wuerfel.uniform(0.55, 0.72))
    for y in range(hoehe):
        anteil = min(1.0, y / max(1, horizont))
        zeichner.line([(0, y), (breite, y)], fill=_mischen(oben, unten, anteil))

    # Die Sonne steht nie in der Mitte - das sieht gestellt aus.
    sx = int(breite * wuerfel.choice((0.22, 0.28, 0.72, 0.78)))
    sy = int(horizont * wuerfel.uniform(0.35, 0.7))
    r = int(min(breite, hoehe) * 0.055)
    zeichner.ellipse([sx - r, sy - r, sx + r, sy + r], fill=sonne)

    # Drei Ketten, von hinten nach vorn dunkler: So entsteht Tiefe
    # ohne ein einziges echtes Pixel.
    for kette in range(3):
        tiefe = (kette + 1) / 3
        farbe = _mischen(_mischen(unten, berg, 0.45), berg, tiefe)
        basis = horizont + int((hoehe - horizont) * kette * 0.28)
        hoehen = wuerfel.uniform(0.05, 0.13) * hoehe
        welle = wuerfel.uniform(0.7, 2.1)
        versatz = wuerfel.uniform(0, 6.28)
        kanten = [(0, hoehe)]
        for x in range(0, breite + 8, 8):
            t = x / breite * welle * 6.28 + versatz
            y = basis - hoehen * (math.sin(t) + 0.5 * math.sin(t * 2.3))
            kanten.append((x, y))
        kanten.append((breite, hoehe))
        zeichner.polygon(kanten, fill=farbe)

    return bild.filter(ImageFilter.GaussianBlur(0.6))


def _exif(wann: datetime):
    """Das Aufnahmedatum ins Bild schreiben, wie eine Kamera es täte.

    **Ohne das landet alles in ``ohne-datum``.** WOLKENErnte liest das
    Datum aus den Metadaten oder aus EXIF, nie aus dem Zeitstempel der
    Datei – der sagt, wann kopiert wurde, nicht wann ausgelöst. Der
    erste Anlauf zu diesen Bildschirmfotos setzte nur ``utime``, und
    31 von 45 Bildern hatten anschließend kein Datum.
    """
    from PIL import Image

    werte = Image.Exif()
    werte[306] = wann.strftime("%Y:%m:%d %H:%M:%S")          # DateTime
    werte[271], werte[272] = "WOLKENErnte", "Schaufenster"   # Make, Model
    werte.get_ifd(0x8769)[36867] = wann.strftime("%Y:%m:%d %H:%M:%S")
    return werte


def _quelle_bauen(quelle: Path) -> int:
    """Die erfundenen Aufnahmen in Ordner legen, wie sie ein Mensch hat.

    Der Ordnername wird beim Erfassen zum Album – deshalb liegen die
    Bilder in Alben und nicht alle in einem Topf.
    """
    from PIL import Image  # noqa: F401  (Fehlt Pillow, bricht es hier)

    wuerfel = random.Random(20260909)
    # Über sieben Jahre verteilt, damit die Jahresauswahl etwas zu
    # zeigen hat, und mit Schwerpunkt auf den letzten - so sieht ein
    # gewachsener Bestand aus.
    aufnahmen: list[tuple[Path, datetime, int, int]] = []
    nummer = 0
    for jahr, wieviel in ((2019, 3), (2020, 4), (2021, 5), (2022, 6),
                          (2023, 8), (2024, 9), (2025, 7)):
        for _ in range(wieviel):
            nummer += 1
            ordner = quelle / wuerfel.choice(ALBEN + (".", ".", "."))
            monat = wuerfel.randint(1, 12)
            tag = wuerfel.randint(1, 28)
            stunde = wuerfel.randint(6, 21)
            wann = datetime(jahr, monat, tag, stunde, wuerfel.randint(0, 59))
            hochkant = wuerfel.random() < 0.3
            masse = (1200, 1600) if hochkant else (1600, 1200)
            name = f"IMG_{wann:%Y%m%d}_{wann:%H%M%S}.jpg"
            ordner.mkdir(parents=True, exist_ok=True)
            aufnahmen.append((ordner / name, wann, *masse))

    for pfad, wann, breite, hoehe in aufnahmen:
        _landschaft(breite, hoehe, samen=hash(pfad.name) % 9973).save(
            pfad, quality=88, exif=_exif(wann))
        stempel = wann.timestamp()
        os.utime(pfad, (stempel, stempel))

    # Aus den jüngsten Zeitpunkten: Das Raster zeigt Neues zuerst, und
    # ein Abspielzeichen ganz unten sähe auf keinem Bildschirmfoto
    # jemand.
    _videos_bauen([(p.parent, w) for p, w, _, _ in
                   aufnahmen[-3:] + aufnahmen[-9:-7]])
    return len(aufnahmen)


def _videos_bauen(momente) -> None:
    """Ein paar Videos dazu – sonst fehlt das Abspielzeichen im Raster.

    **Mit einer Metadatendatei daneben, anders als bei den Bildern.**
    Ein Video trägt sein Aufnahmedatum in einem Feld, das WOLKENErnte
    nicht liest – EXIF gibt es dort nicht. Aus einem bloßen Ordner
    geerntet landete jedes Video in ``ohne-datum``. Google legt neben
    Videos ohnehin dieselbe JSON wie neben Bilder; genau die steht hier.

    **Jedes Video bekommt ein eigenes Standbild**, keins der schon
    vorhandenen. Sonst stünden im Raster Zwillingspaare – dasselbe Bild
    zweimal, einmal mit und einmal ohne Abspielzeichen –, und das sähe
    nach einem Fehler aus, obwohl keiner vorliegt.

    Ohne ffmpeg wird das übersprungen: Der Rest der Bildschirmfotos
    steht auch ohne, und ein Abbruch dafür wäre unverhältnismäßig.
    """
    if not shutil.which("ffmpeg"):
        print("  ffmpeg fehlt – die Bildschirmfotos zeigen keine Videos.")
        return
    for nummer, (ordner, wann) in enumerate(momente):
        ziel = ordner / f"VID_{wann:%Y%m%d}_{wann:%H%M%S}.mp4"
        standbild = ordner / f".standbild-{nummer}.jpg"
        _landschaft(1280, 960, samen=7000 + nummer * 137).save(
            standbild, quality=88)
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
             "-loop", "1", "-i", str(standbild), "-t", "3", "-r", "12",
             "-pix_fmt", "yuv420p", "-vf", "scale=960:-2", str(ziel)],
            check=True)
        standbild.unlink()
        stempel = wann.timestamp()
        ziel.with_name(ziel.name + ".supplemental-metadata.json").write_text(
            json.dumps({"title": ziel.name,
                        "photoTakenTime": {"timestamp": str(int(stempel))}}),
            "utf-8")
        os.utime(ziel, (stempel, stempel))


def _laufen(*teile: str) -> None:
    print("  $ wolkenernte", " ".join(teile[:2]))
    subprocess.run([sys.executable, "-m", "wolkenernte", *teile],
                   cwd=WURZEL, check=True, capture_output=True)


def archiv_bauen() -> Path:
    """Quelle erzeugen und durch ernten, erfassen, verschlagworten schicken."""
    if WERKSTATT.exists():
        shutil.rmtree(WERKSTATT)
    quelle = WERKSTATT / "Quelle"
    archiv = WERKSTATT / "Archiv"
    quelle.mkdir(parents=True)
    archiv.mkdir(parents=True)

    print("Erfundene Aufnahmen rechnen …")
    anzahl = _quelle_bauen(quelle)
    print(f"  {anzahl} Bilder")

    print("Durch das Programm schicken …")
    _laufen("ernten", str(archiv), str(quelle))
    _laufen("erfassen", str(archiv), str(quelle))
    _laufen("verschlagworten", "--ohne-bilderkennung", str(archiv))
    return archiv


# -- Das Fenster -------------------------------------------------------------

def _warten(app, sekunden: float) -> None:
    """Die Vorschaubilder kommen aus einem Nebenläufer – auf sie warten.

    Ohne das steht auf dem Bildschirmfoto ein Raster aus grauen
    Platzhaltern: Das Modell liefert absichtlich sofort etwas und
    tauscht es später aus.
    """
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        app.processEvents()
        time.sleep(0.02)


def fensterfotos(archiv: Path) -> None:
    from PySide6.QtCore import QDate
    from PySide6.QtWidgets import QApplication

    from wolkenernte.fenster.hauptfenster import Hauptfenster

    app = QApplication.instance() or QApplication([])
    fenster = Hauptfenster(archiv)
    fenster.resize(1180, 760)
    fenster.show()
    _warten(app, 6)

    fenster.grab().save(str(ZIEL / "fenster-raster.png"))
    print("  fenster-raster.png")

    # Der Zeitraum, eingeschaltet und gesetzt - das ist die Neuerung
    # aus 0.4.1 und auf einem Bild sonst nicht zu sehen.
    fenster.zeitraum_an.setChecked(True)
    fenster.von_feld.setDate(QDate(2023, 6, 1))
    fenster.bis_feld.setDate(QDate(2024, 8, 31))
    _warten(app, 4)
    fenster.grab().save(str(ZIEL / "fenster-zeitraum.png"))
    print("  fenster-zeitraum.png")

    fenster.zeitraum_an.setChecked(False)
    _warten(app, 2)

    # Die Einzelansicht - dasselbe Fenster, andere Ebene. **Kein
    # Video:** Die Wiedergabe zeichnet ohne Bildschirm nichts, und
    # herausgekommen ist beim ersten Versuch eine leere graue Fläche
    # mit einer korrekten Kopfzeile darüber.
    zeile = next(i for i, b in enumerate(fenster.modell.bilder)
                 if not b.ist_video)
    stelle = fenster.modell.index(zeile, 0)
    fenster.raster.setCurrentIndex(stelle)
    fenster._oeffnen(stelle)
    _warten(app, 3)
    fenster.grab().save(str(ZIEL / "fenster-einzelansicht.png"))
    print("  fenster-einzelansicht.png")

    fenster.close()


# -- Der Browser -------------------------------------------------------------

#: Welche Seite der Weboberfläche unter welchem Namen abgelichtet wird.
SEITEN = (
    ("browser-uebersicht.png", ""),
    ("browser-zeitraum.png", "raster?von=2023-06-01&bis=2024-08-31"),
)


def browserfotos(archiv: Path) -> None:
    """Die Weboberfläche, aufgenommen aus einem echten Browser.

    Gezeichnet wird sie von Chromium (über QtWebEngine) – also von
    derselben Sorte Programm, die auch der Anwender benutzt. Ein
    nachgebauter HTML-Betrachter zeigte etwas anderes als die
    Wirklichkeit.
    """
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        print("  QtWebEngine fehlt – keine Bilder der Weboberfläche.")
        return

    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QApplication

    from wolkenernte.web.dienst import Behandler, Dienst, freier_port

    port = freier_port()
    dienst = Dienst(("127.0.0.1", port), Behandler, archiv)
    threading.Thread(target=dienst.serve_forever, daemon=True).start()

    app = QApplication.instance() or QApplication([])
    sicht = QWebEngineView()
    sicht.resize(1180, 900)
    sicht.show()
    try:
        for name, weg in SEITEN:
            sicht.load(QUrl(f"http://127.0.0.1:{port}/{weg}"))
            # Reichlich: Die Vorschaubilder holt der Browser einzeln
            # nach, und ein halb geladenes Raster wäre kein Beleg.
            _warten(app, 12)
            sicht.grab().save(str(ZIEL / name))
            print(f"  {name}")
    finally:
        sicht.close()
        dienst.shutdown()
        dienst.server_close()


def main() -> int:
    ZIEL.mkdir(parents=True, exist_ok=True)
    archiv = archiv_bauen()
    print(f"Bildschirmfotos nach {ZIEL} …")
    fensterfotos(archiv)
    browserfotos(archiv)
    print("\nFertig. Das erfundene Archiv liegt unter")
    print(f"  {WERKSTATT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

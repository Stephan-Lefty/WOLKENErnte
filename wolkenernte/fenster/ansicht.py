"""Ein einzelnes Bild oder Video groß ansehen.

Bilder zeigt Qt selbst. Videos übernimmt ``QMediaPlayer`` – **das ist
geprüft**, nicht angenommen: ``werkzeuge/videoprobe.py`` hat an einem
echten Bestand nachgewiesen, dass H.264, HEVC und VP9 tatsächlich
Einzelbilder liefern. Deshalb braucht es hier weder libmpv noch VLC.

**HEIC kann Qt nicht** – außerhalb von macOS bringt es kein
HEIF-Modul mit. Dafür wird das Vorschaubild gezeigt, das Pillow ohnehin
erzeugt hat. Lieber ein verkleinertes Bild als eine leere Fläche.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImageReader, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..bestandsliste import Bild, wann
from ..farben import BLAU_LEUCHT, GRAU_MITTE, GRAU_NACHT, WEISS
from ..web import vorschau

#: Was Qt ohne Zusatzmodul darstellen kann.
IN_QT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

VIDEO_HINWEIS = (
    "Für die Wiedergabe fehlt QtMultimedia.\n"
    "Unter Arch und Manjaro: pacman -S pyside6"
)


def _laden(pfad: Path) -> QPixmap:
    """Ein Bild laden – und dabei die Aufnahmerichtung beachten.

    **``QPixmap.load()`` allein genügt nicht.** Es ignoriert das
    EXIF-Feld für die Ausrichtung, und hochkant gehaltene Aufnahmen
    liegen dann auf der Seite. Im Raster fällt das nicht auf, weil die
    Vorschaubilder von Pillow kommen, das von sich aus dreht – die
    Einzelansicht zeigte dasselbe Bild danach um 90 Grad gekippt.

    ``QImageReader`` kann es, aber nur auf ausdrückliche Ansage.
    """
    leser = QImageReader(str(pfad))
    leser.setAutoTransform(True)
    abbild = leser.read()
    return QPixmap.fromImage(abbild) if not abbild.isNull() else QPixmap()


class Einzelansicht(QWidget):
    """Ein Bild oder Video, bildschirmfüllend.

    Mit den Pfeiltasten geht es weiter, mit Escape zurück – das ist der
    eigentliche Gewinn gegenüber der Weboberfläche.
    """

    def __init__(self, archiv: Path) -> None:
        super().__init__()
        self.archiv = archiv
        self._spieler = None
        self._videoflaeche = None

        self.setStyleSheet(f"background: {GRAU_NACHT};")

        self.anzeige = QLabel()
        self.anzeige.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.anzeige.setSizePolicy(QSizePolicy.Policy.Ignored,
                                   QSizePolicy.Policy.Ignored)
        self.anzeige.setStyleSheet(f"color: {GRAU_MITTE};")

        self.angaben = QLabel()
        self.angaben.setStyleSheet(
            f"color: {WEISS}; padding: .5rem 1rem; font-size: 11pt;"
        )
        self.angaben.setWordWrap(True)

        zurueck = QPushButton("← Zurück (Esc)")
        zurueck.setStyleSheet(
            f"color: {BLAU_LEUCHT}; background: transparent; border: 0;"
            f" padding: .5rem 1rem; text-align: left;"
        )
        zurueck.clicked.connect(self.zurueck_gewuenscht)
        self.zurueck_knopf = zurueck

        kopf = QHBoxLayout()
        kopf.addWidget(zurueck)
        kopf.addWidget(self.angaben, 1)

        aufbau = QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addLayout(kopf)
        aufbau.addWidget(self.anzeige, 1)

        self._bild: QPixmap | None = None
        self._aktuell: Bild | None = None

    # -- Anzeigen ----------------------------------------------------------

    def zeigen(self, bild: Bild) -> None:
        self._aktuell = bild
        self._beenden()

        teile = [bild.name, wann(bild), f"{bild.groesse / 1e6:.1f} MB"]
        if bild.schlagworte:
            teile.append("· " + ", ".join(bild.schlagworte))
        if bild.alben:
            teile.append("· " + ", ".join(bild.alben))
        if bild.ort:
            teile.append(f"· {bild.ort[0]:.4f}, {bild.ort[1]:.4f}")
        self.angaben.setText("   ".join(teile))

        if bild.ist_video:
            self._video_zeigen(bild)
        else:
            self._bild_zeigen(bild)

    def _bild_zeigen(self, bild: Bild) -> None:
        self.anzeige.show()
        pfad = self.archiv / bild.pfad

        geladen = QPixmap()
        if bild.endung in IN_QT:
            geladen = _laden(pfad)

        if geladen.isNull():
            # HEIC und Verwandte: das Vorschaubild nehmen, das Pillow
            # erzeugt hat. Kleiner, aber sichtbar.
            daten = vorschau.hole(self.archiv, bild.pfad)
            if daten:
                geladen.loadFromData(daten)

        if geladen.isNull():
            self._bild = None
            self.anzeige.setText(f"{bild.name}\nlässt sich nicht anzeigen.")
            return

        self._bild = geladen
        self._einpassen()

    def _einpassen(self) -> None:
        if self._bild is None:
            return
        self.anzeige.setPixmap(self._bild.scaled(
            self.anzeige.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _video_zeigen(self, bild: Bild) -> None:
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
        except ImportError:
            self._bild = None
            self.anzeige.setText(VIDEO_HINWEIS)
            self.anzeige.show()
            return

        if self._videoflaeche is None:
            self._videoflaeche = QVideoWidget()
            self.layout().addWidget(self._videoflaeche, 1)
            self._spieler = QMediaPlayer()
            self._ton = QAudioOutput()
            self._spieler.setAudioOutput(self._ton)
            self._spieler.setVideoOutput(self._videoflaeche)

        self.anzeige.hide()
        self._videoflaeche.show()
        self._spieler.setSource(QUrl.fromLocalFile(str(self.archiv / bild.pfad)))
        self._spieler.play()

    def _beenden(self) -> None:
        """Die Wiedergabe anhalten und die Videofläche verstecken.

        **Wichtig beim Weiterblättern.** Ohne das läuft der Ton des
        vorigen Videos weiter, während schon das nächste Bild zu sehen
        ist.
        """
        if self._spieler is not None:
            self._spieler.stop()
            self._spieler.setSource(QUrl())
        if self._videoflaeche is not None:
            self._videoflaeche.hide()
        self.anzeige.show()
        self.anzeige.clear()

    # -- Bedienung ---------------------------------------------------------

    def zurueck_gewuenscht(self) -> None:
        """Wird vom Hauptfenster überschrieben."""

    def weiter_gewuenscht(self, richtung: int) -> None:
        """Wird vom Hauptfenster überschrieben."""

    def keyPressEvent(self, ereignis: QKeyEvent) -> None:  # noqa: N802
        taste = ereignis.key()
        if taste == Qt.Key.Key_Escape:
            self._beenden()
            self.zurueck_gewuenscht()
        elif taste in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Space):
            self.weiter_gewuenscht(1)
        elif taste in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_Backspace):
            self.weiter_gewuenscht(-1)
        else:
            super().keyPressEvent(ereignis)

    def resizeEvent(self, ereignis) -> None:  # noqa: N802
        super().resizeEvent(ereignis)
        self._einpassen()

    def aufraeumen(self) -> None:
        self._beenden()

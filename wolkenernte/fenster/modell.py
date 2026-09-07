"""Die Bilder für die Rasteransicht – und wie sie dorthin kommen.

**Der ganze Kniff steckt darin, nichts im Voraus zu tun.** Bei 14.770
Bildern wäre es aussichtslos, beim Öffnen alle Vorschaubilder zu laden:
Das dauert Minuten und belegt Gigabyte. Qt fragt eine Listenansicht
ohnehin nur nach dem, was gerade zu sehen ist – rund fünfzig Kacheln.
Dieses Modell antwortet deshalb sofort mit einem Platzhalter und lässt
das richtige Bild im Hintergrund nachladen.

**Vorschaubilder werden nicht im Anzeigefaden erzeugt.** Ein einziges
großes JPEG zu verkleinern dauert je nach Größe hundert Millisekunden;
in der Oberfläche wäre das ein Ruckeln bei jedem Bildlauf. Die Arbeit
geht deshalb in einen ``QThreadPool``, und wenn ein Bild fertig ist,
meldet sich das Modell bei der Ansicht.

**Was schon auf der Platte liegt, wird sofort genommen.** Der
Zwischenspeicher aus der Weboberfläche wird mitbenutzt – wer sein
Archiv dort schon einmal durchgesehen hat, sieht hier keine
Platzhalter.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from ..bestandsliste import Bild
from ..farben import BLAU, GRAU_KOHLE, GRAU_MITTE
from ..web import vorschau

#: Kantenlänge einer Kachel in der Rasteransicht.
KACHEL = 180


class _Bote(QObject):
    """Trägt das Ergebnis aus dem Arbeitsfaden zurück.

    ``QRunnable`` ist kein ``QObject`` und kann selbst keine Signale
    senden – deshalb dieser Umweg.
    """

    fertig = Signal(int, QPixmap)


class _Auftrag(QRunnable):
    """Ein Vorschaubild erzeugen, außerhalb des Anzeigefadens."""

    def __init__(self, archiv: Path, pfad: str, zeile: int, bote: _Bote) -> None:
        super().__init__()
        self.archiv = archiv
        self.pfad = pfad
        self.zeile = zeile
        self.bote = bote

    def run(self) -> None:
        daten = vorschau.hole(self.archiv, self.pfad)
        bild = QPixmap()
        if daten:
            bild.loadFromData(daten)
        # Auch ein leeres Bild melden: Sonst versucht das Modell es bei
        # jedem Bildlauf erneut und quält sich an derselben kaputten
        # Datei ab.
        self.bote.fertig.emit(self.zeile, bild)


def _quadratisch(bild: QPixmap) -> QPixmap:
    """Auf Kachelgröße bringen und mittig zuschneiden.

    **Skalieren allein genügt nicht.** ``KeepAspectRatioByExpanding``
    macht das Bild mindestens so groß wie verlangt, schneidet aber
    nichts ab – ein Hochformat bleibt hochkant. Im Raster ergibt das
    unterschiedlich hohe Kacheln und damit Lücken, obwohl
    ``setUniformItemSizes`` gesetzt ist.

    Zugeschnitten wird zur Mitte hin. Bei Fotos steht das Wesentliche
    selten am Rand, und ein gleichmäßiges Raster liest sich ruhiger als
    eines, in dem jede Zeile anders aussieht.
    """
    gross = bild.scaled(
        QSize(KACHEL, KACHEL),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    links = max(0, (gross.width() - KACHEL) // 2)
    oben = max(0, (gross.height() - KACHEL) // 2)
    return gross.copy(links, oben, KACHEL, KACHEL)


def _platzhalter(ist_video: bool) -> QPixmap:
    """Was zu sehen ist, solange das Vorschaubild fehlt."""
    bild = QPixmap(KACHEL, KACHEL)
    bild.fill(QColor(GRAU_KOHLE))
    maler = QPainter(bild)
    maler.setPen(QColor(BLAU if ist_video else GRAU_MITTE))
    schrift = maler.font()
    schrift.setPointSize(28)
    maler.setFont(schrift)
    maler.drawText(bild.rect(), Qt.AlignmentFlag.AlignCenter,
                   "▶" if ist_video else "…")
    maler.end()
    return bild


class Bildmodell(QAbstractListModel):
    """Die Bilder einer Auswahl, für eine Listenansicht.

    Die Ansicht fragt nur, was sie anzeigt. Alles andere bleibt
    ungetan – das ist der Unterschied zwischen flüssig und unbenutzbar.
    """

    def __init__(self, archiv: Path, bilder: list[Bild]) -> None:
        super().__init__()
        self.archiv = archiv
        self.bilder = bilder
        self._vorschau: dict[int, QPixmap] = {}
        self._laufend: set[int] = set()

        self._bote = _Bote()
        self._bote.fertig.connect(self._angekommen)

        self._pool = QThreadPool()
        # Nicht alle Kerne: Der Anzeigefaden braucht auch einen, sonst
        # hakt die Oberfläche genau dann, wenn viel nachzuladen ist.
        self._pool.setMaxThreadCount(max(1, QThreadPool.globalInstance()
                                         .maxThreadCount() - 1))

        self._leer = _platzhalter(False)
        self._leer_video = _platzhalter(True)

    # -- Was Qt von einem Modell erwartet -----------------------------------

    def rowCount(self, eltern: QModelIndex | None = None) -> int:  # noqa: N802
        return 0 if (eltern and eltern.isValid()) else len(self.bilder)

    def data(self, index: QModelIndex, rolle: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.bilder):
            return None
        bild = self.bilder[index.row()]

        if rolle == Qt.ItemDataRole.DecorationRole:
            return QIcon(self._bild_holen(index.row(), bild))
        if rolle == Qt.ItemDataRole.ToolTipRole:
            zeit = (bild.zeit.strftime("%d.%m.%Y um %H:%M")
                    if bild.datum_bekannt else "ohne Datum")
            teile = [bild.name, zeit, f"{bild.groesse / 1e6:.1f} MB"]
            if bild.alben:
                teile.append("Alben: " + ", ".join(bild.alben))
            if bild.ort:
                teile.append(f"Ort: {bild.ort[0]:.4f}, {bild.ort[1]:.4f}")
            return "\n".join(teile)
        if rolle == Qt.ItemDataRole.UserRole:
            return bild
        return None

    def _bild_holen(self, zeile: int, bild: Bild) -> QPixmap:
        fertig = self._vorschau.get(zeile)
        if fertig is not None:
            return fertig

        if zeile not in self._laufend:
            self._laufend.add(zeile)
            self._pool.start(_Auftrag(self.archiv, bild.pfad, zeile, self._bote))

        return self._leer_video if bild.ist_video else self._leer

    def _angekommen(self, zeile: int, bild: QPixmap) -> None:
        self._laufend.discard(zeile)
        if bild.isNull():
            # Kein Vorschaubild - Platzhalter behalten, aber vermerken,
            # damit nicht immer wieder gerechnet wird.
            eintrag = self.bilder[zeile] if zeile < len(self.bilder) else None
            self._vorschau[zeile] = (
                self._leer_video if eintrag and eintrag.ist_video else self._leer
            )
        else:
            self._vorschau[zeile] = _quadratisch(bild)
        stelle = self.index(zeile, 0)
        self.dataChanged.emit(stelle, stelle,
                              [Qt.ItemDataRole.DecorationRole])

    # -- Wechseln der Auswahl ----------------------------------------------

    def zeigen(self, bilder: list[Bild]) -> None:
        """Eine andere Auswahl anzeigen.

        Der Zwischenspeicher wird geleert, weil er nach Zeilennummern
        geht – die stimmen für die neue Auswahl nicht mehr. Die
        Vorschaubilder auf der Platte bleiben natürlich, das erneute
        Laden ist deshalb billig.
        """
        self.beginResetModel()
        self.bilder = bilder
        self._vorschau.clear()
        self._laufend.clear()
        self.endResetModel()

    def bild_bei(self, index: QModelIndex) -> Bild | None:
        if not index.isValid() or not 0 <= index.row() < len(self.bilder):
            return None
        return self.bilder[index.row()]

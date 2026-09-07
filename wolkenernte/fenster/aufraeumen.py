"""In der Wolke aufräumen – mit den Bildern vor Augen.

**Das ist der einzige Schritt ohne Rückweg**, und deshalb sieht er
anders aus als alle anderen: Erst wird geprüft, dann wird *gezeigt*,
was verschwinden würde, und erst danach darf gelöscht werden.

Warum überhaupt Bilder und nicht bloß eine Liste von Dateinamen? Weil
eine Liste aus vierhundert Zeilen ``IMG_20240816_172342.jpg`` niemand
liest. Vor Bildern erkennt man dagegen sofort, wenn etwas dabei ist,
das man behalten wollte – und **genau dafür gibt es diesen Zwischen-
schritt.** Die Dateien liegen beim Prüfen ohnehin schon auf der Platte;
das Vorschaubild kostet nichts extra.

Die Prüfung selbst steht in :mod:`wolkenernte.aufraeumen`. Hier wird
nichts entschieden, was dort nicht schon feststeht: Was nicht
nachweislich im Archiv liegt, lässt sich hier gar nicht erst
ankreuzen.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QRunnable,
    Qt,
    QThread,
    QThreadPool,
    Signal,
)
from PySide6.QtGui import QColor, QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..aufraeumen import AufraeumFehler, Urteil, durchgehen
from ..farben import GRAU_KOHLE, GRAU_MITTE, ROT, ROT_HELL, WEISS
from .modell import KACHEL, _platzhalter, _quadratisch


# ---------------------------------------------------------------------------
# Prüfen


class Pruefung(QObject):
    """Der Prüflauf, außerhalb des Fensterfadens.

    Er lädt jede Datei herunter und rechnet ihre Prüfsumme – bei einem
    Fotoarchiv einmal die ganze Leitung. Im Anzeigefaden stünde das
    Fenster derweil still.
    """

    schritt = Signal(int, int, str)
    fertig = Signal(object)
    misslungen = Signal(str)

    def __init__(self, archiv: Path, wolke) -> None:
        super().__init__()
        self.archiv = archiv
        self.wolke = wolke
        self.abbrechen = False

    def laufen(self) -> None:
        def melden(nummer: int, gesamt: int, pfad: str) -> None:
            if self.abbrechen:
                raise KeyboardInterrupt
            self.schritt.emit(nummer, gesamt, pfad)

        try:
            # **wirklich=False, immer.** Dieser Lauf prüft nur; gelöscht
            # wird erst, nachdem jemand die Bilder gesehen hat.
            bilanz = durchgehen(self.archiv, self.wolke, wirklich=False,
                                fortschritt=melden)
        except KeyboardInterrupt:
            self.misslungen.emit("Abgebrochen. Es wurde nichts gelöscht.")
            return
        except AufraeumFehler as fehler:
            self.misslungen.emit(str(fehler))
            return
        except Exception as fehler:  # noqa: BLE001
            self.misslungen.emit(str(fehler))
            return
        self.fertig.emit(bilanz)


# ---------------------------------------------------------------------------
# Zeigen


class _Bote(QObject):
    fertig = Signal(int, QPixmap)


class _Auftrag(QRunnable):
    """Ein Vorschaubild aus der schon heruntergeladenen Datei."""

    def __init__(self, datei: Path, zeile: int, bote: _Bote) -> None:
        super().__init__()
        self.datei = datei
        self.zeile = zeile
        self.bote = bote

    def run(self) -> None:
        leser = QImageReader(str(self.datei))
        # Wie in der Einzelansicht: Ohne das liegen hochkant gehaltene
        # Aufnahmen auf der Seite.
        leser.setAutoTransform(True)
        abbild = leser.read()
        bild = QPixmap.fromImage(abbild) if not abbild.isNull() else QPixmap()
        self.bote.fertig.emit(self.zeile, bild)


class Urteilsmodell(QAbstractListModel):
    """Die geprüften Dateien, zum Ankreuzen.

    **Nur das Nachgewiesene lässt sich ankreuzen.** Was nicht im Archiv
    liegt, bekommt gar kein Kästchen – ein abgeblendetes Häkchen, das
    sich nicht setzen lässt, ist eine Einladung zum Herumklicken; hier
    soll erkennbar sein, dass die Entscheidung schon gefallen ist.
    """

    def __init__(self, urteile: list[Urteil]) -> None:
        super().__init__()
        self.urteile = urteile
        self.gewaehlt = {i for i, u in enumerate(urteile) if u.gesichert}
        self._vorschau: dict[int, QPixmap] = {}
        self._laufend: set[int] = set()

        self._bote = _Bote()
        self._bote.fertig.connect(self._angekommen)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(
            max(1, QThreadPool.globalInstance().maxThreadCount() - 1))
        self._leer = _platzhalter(False)

    def rowCount(self, eltern: QModelIndex | None = None) -> int:  # noqa: N802
        return 0 if (eltern and eltern.isValid()) else len(self.urteile)

    def data(self, index: QModelIndex, rolle: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.urteile):
            return None
        zeile = index.row()
        urteil = self.urteile[zeile]

        if rolle == Qt.ItemDataRole.DisplayRole:
            # **Der Name gehört sichtbar darunter.** Ohne ihn sieht man
            # zwar die Bilder, aber nicht, welche stehenbleiben - und
            # ein fehlendes Kästchen am linken Rand ist zu wenig
            # Unterschied für eine Entscheidung, die endgültig ist.
            name = urteil.pfad.rsplit("/", 1)[-1]
            kurz = name if len(name) <= 22 else name[:10] + "…" + name[-11:]
            return kurz if urteil.gesichert else f"bleibt · {kurz}"
        if rolle == Qt.ItemDataRole.ForegroundRole and not urteil.gesichert:
            return QColor(ROT_HELL)
        if rolle == Qt.ItemDataRole.DecorationRole:
            return QIcon(self._bild_holen(zeile, urteil))
        if rolle == Qt.ItemDataRole.CheckStateRole and urteil.gesichert:
            return (Qt.CheckState.Checked if zeile in self.gewaehlt
                    else Qt.CheckState.Unchecked)
        if rolle == Qt.ItemDataRole.ToolTipRole:
            teile = [urteil.pfad, f"{urteil.groesse / 1e6:.1f} MB"]
            teile.append("liegt im Archiv – darf weg" if urteil.gesichert
                         else f"bleibt: {urteil.grund}")
            return "\n".join(teile)
        if rolle == Qt.ItemDataRole.UserRole:
            return urteil
        return None

    def setData(self, index: QModelIndex, wert,  # noqa: N802
                rolle: int = Qt.ItemDataRole.EditRole) -> bool:
        if rolle != Qt.ItemDataRole.CheckStateRole or not index.isValid():
            return False
        zeile = index.row()
        if not self.urteile[zeile].gesichert:
            return False
        if Qt.CheckState(wert) == Qt.CheckState.Checked:
            self.gewaehlt.add(zeile)
        else:
            self.gewaehlt.discard(zeile)
        self.dataChanged.emit(index, index, [rolle])
        return True

    def flags(self, index: QModelIndex):
        grund = super().flags(index)
        if index.isValid() and self.urteile[index.row()].gesichert:
            return grund | Qt.ItemFlag.ItemIsUserCheckable
        return grund

    # -- Vorschaubilder ----------------------------------------------------

    def _bild_holen(self, zeile: int, urteil: Urteil) -> QPixmap:
        fertig = self._vorschau.get(zeile)
        if fertig is not None:
            return fertig
        if urteil.ablage is not None and zeile not in self._laufend:
            self._laufend.add(zeile)
            self._pool.start(_Auftrag(urteil.ablage, zeile, self._bote))
        return self._leer

    def _angekommen(self, zeile: int, bild: QPixmap) -> None:
        self._vorschau[zeile] = (_quadratisch(bild) if not bild.isNull()
                                 else self._leer)
        self._laufend.discard(zeile)
        stelle = self.index(zeile, 0)
        self.dataChanged.emit(stelle, stelle,
                              [Qt.ItemDataRole.DecorationRole])

    def alle_waehlen(self, ja: bool) -> None:
        self.gewaehlt = ({i for i, u in enumerate(self.urteile) if u.gesichert}
                         if ja else set())
        self.dataChanged.emit(
            self.index(0, 0), self.index(max(0, len(self.urteile) - 1), 0),
            [Qt.ItemDataRole.CheckStateRole])

    def ausgewaehlte(self) -> list[Urteil]:
        return [self.urteile[i] for i in sorted(self.gewaehlt)]


# ---------------------------------------------------------------------------
# Der Dialog


class AufraeumenDialog(QDialog):
    """Prüfen, ansehen, entscheiden – in dieser Reihenfolge."""

    def __init__(self, dienst, wolke, archiv: Path,
                 eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.dienst = dienst
        self.wolke = wolke
        self.archiv = archiv
        self.geloescht = 0

        self.setWindowTitle(f"Aufräumen in {wolke.wurzel}")
        self.resize(940, 700)

        self.kopf = QLabel(
            f"Jede Datei aus {wolke.wurzel} wird geholt und mit dem Archiv "
            f"verglichen.\nGelöscht wird nichts, bevor Sie es gesehen haben.")
        self.kopf.setWordWrap(True)

        self.balken = QProgressBar()
        self.balken.setRange(0, 0)
        self.stand = QLabel("Prüfsummen des Archivs werden gerechnet …")
        self.stand.setStyleSheet(f"color: {GRAU_MITTE};")

        self.raster = QListView()
        self.raster.setViewMode(QListView.ViewMode.IconMode)
        self.raster.setIconSize(self.raster.iconSize().__class__(KACHEL, KACHEL))
        self.raster.setGridSize(self.raster.gridSize().__class__(
            KACHEL + 12, KACHEL + 30))
        self.raster.setResizeMode(QListView.ResizeMode.Adjust)
        self.raster.setSpacing(4)
        self.raster.setUniformItemSizes(True)
        self.raster.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.raster.hide()

        self.alle = QCheckBox("Alle nachgewiesenen auswählen")
        self.alle.setChecked(True)
        self.alle.hide()
        self.alle.toggled.connect(self._alle_umschalten)

        self.knoepfe = QDialogButtonBox()
        self.loeschen = QPushButton("Endgültig löschen")
        self.loeschen.setEnabled(False)
        self.loeschen.setStyleSheet(
            f"QPushButton {{ background: {ROT}; color: {WEISS}; border: 0; }}"
            f"QPushButton:disabled {{ background: {GRAU_KOHLE};"
            f" color: {GRAU_MITTE}; }}")
        # **Nicht der voreingestellte Knopf.** Wer aus Gewohnheit die
        # Eingabetaste drückt, soll nichts löschen.
        self.loeschen.setAutoDefault(False)
        self.loeschen.clicked.connect(self._loeschen)
        self.knoepfe.addButton(self.loeschen,
                               QDialogButtonBox.ButtonRole.DestructiveRole)
        self.abbrechen = self.knoepfe.addButton(
            "Abbrechen", QDialogButtonBox.ButtonRole.RejectRole)
        self.abbrechen.setDefault(True)
        self.knoepfe.rejected.connect(self._abbrechen)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.kopf)
        aufbau.addWidget(self.balken)
        aufbau.addWidget(self.stand)
        aufbau.addWidget(self.raster, 1)
        unten = QHBoxLayout()
        unten.addWidget(self.alle)
        unten.addStretch(1)
        aufbau.addLayout(unten)
        aufbau.addWidget(self.knoepfe)

        self.modell: Urteilsmodell | None = None
        self.faden = QThread(self)
        self.pruefung = Pruefung(archiv, wolke)
        self.pruefung.moveToThread(self.faden)
        self.faden.started.connect(self.pruefung.laufen)
        self.pruefung.schritt.connect(self._schritt)
        self.pruefung.fertig.connect(self._geprueft)
        self.pruefung.misslungen.connect(self._misslungen)
        self.faden.start()

    # -- Prüfen ------------------------------------------------------------

    def _schritt(self, nummer: int, gesamt: int, pfad: str) -> None:
        if self.balken.maximum() != gesamt:
            self.balken.setRange(0, gesamt)
        self.balken.setValue(nummer)
        self.stand.setText(f"Geprüft: {nummer} von {gesamt}   ·   {pfad[-52:]}")

    def _geprueft(self, bilanz) -> None:
        self._faden_beenden()
        self.bilanz = bilanz
        self.balken.hide()

        self.modell = Urteilsmodell(bilanz.urteile)
        self.modell.dataChanged.connect(self._zahl_auffrischen)
        self.raster.setModel(self.modell)
        self.raster.show()
        self.alle.show()

        self.kopf.setText(
            f"<b>{bilanz.gesichert}</b> von {bilanz.gesehen} Dateien liegen "
            f"nachweislich im Archiv und dürfen weg. "
            f"<span style='color:{ROT_HELL}'>{bilanz.fehlt} bleiben stehen</span>"
            f" – sie sind dort nicht angekommen."
            + (f"  {bilanz.gescheitert} ließen sich nicht lesen."
               if bilanz.gescheitert else ""))
        self._zahl_auffrischen()

    def _misslungen(self, text: str) -> None:
        self._faden_beenden()
        QMessageBox.warning(self, "WOLKENErnte", text)
        self.reject()

    def _faden_beenden(self) -> None:
        self.faden.quit()
        self.faden.wait(5000)

    # -- Entscheiden -------------------------------------------------------

    def _alle_umschalten(self, ja: bool) -> None:
        if self.modell is not None:
            self.modell.alle_waehlen(ja)

    def _zahl_auffrischen(self, *_) -> None:
        if self.modell is None:
            return
        wieviele = len(self.modell.gewaehlt)
        self.loeschen.setText(
            f"Endgültig löschen ({wieviele})" if wieviele
            else "Endgültig löschen")
        self.loeschen.setEnabled(bool(wieviele))
        self.stand.setText(
            f"{wieviele} ausgewählt   ·   "
            f"{sum(u.groesse for u in self.modell.ausgewaehlte()) / 1e9:.2f} GB")

    def _loeschen(self) -> None:
        from ..rclone import RcloneFehler
        from ..takeout import TakeoutFehler

        gewaehlt = self.modell.ausgewaehlte() if self.modell else []
        if not gewaehlt:
            return

        gb = sum(u.groesse for u in gewaehlt) / 1e9
        antwort = QMessageBox.warning(
            self, "Endgültig löschen",
            f"{len(gewaehlt)} Dateien ({gb:.2f} GB) werden in "
            f"{self.wolke.wurzel} gelöscht.\n\n"
            "Das lässt sich nicht rückgängig machen – je nach Anbieter "
            "landen sie im Papierkorb der Cloud, verlassen kann man sich "
            "darauf nicht.\n\nIm Archiv bleiben sie.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if antwort != QMessageBox.StandardButton.Yes:
            return

        fehler: list[str] = []
        for urteil in gewaehlt:
            try:
                self.wolke.loeschen(urteil.pfad)
            except (RcloneFehler, TakeoutFehler) as schaden:
                fehler.append(f"{urteil.pfad}: {schaden}")
            else:
                urteil.geloescht = True
                self.geloescht += 1

        text = (f"{self.geloescht} Dateien gelöscht.\n\n"
                f"Im Archiv liegen sie weiter.")
        if fehler:
            text += (f"\n\n{len(fehler)} ließen sich nicht löschen:\n"
                     + "\n".join(fehler[:5]))
        QMessageBox.information(self, "WOLKENErnte", text)
        self.accept()

    def _abbrechen(self) -> None:
        self.pruefung.abbrechen = True
        self.reject()

    def closeEvent(self, ereignis) -> None:  # noqa: N802
        """Nicht mitten in der Prüfung verschwinden.

        Gelöscht wird dabei nichts – die Prüfung läuft ausdrücklich mit
        ``wirklich=False``. Aber ein herrenloser Faden, der weiter
        Gigabyte herunterlädt, wäre trotzdem unschön.
        """
        self.pruefung.abbrechen = True
        self._faden_beenden()
        super().closeEvent(ereignis)

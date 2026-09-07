"""Das Hauptfenster: Raster, Filter, Suche.

Aufgebaut wie die Weboberfläche und auf demselben Fundament – beide
fragen :class:`wolkenernte.bestandsliste.Bestandsliste`. Was hier
anders ist, ist die Bedienung: Tastatur statt Mausklicks, und die
Einzelansicht ist keine neue Seite, sondern eine zweite Ebene im selben
Fenster.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QWidget,
)

from .. import __version__
from ..bestandsliste import Bestandsliste
from ..farben import (
    BLAU,
    GRAU_DUNKEL,
    GRAU_HELL,
    GRAU_KOHLE,
    GRAU_NACHT,
    WEISS,
)
from .ansicht import Einzelansicht
from .modell import KACHEL, Bildmodell

STIL = f"""
QMainWindow, QWidget {{ background: {GRAU_NACHT}; color: {GRAU_HELL}; }}
QToolBar {{ background: {GRAU_KOHLE}; border: 0; padding: 4px; spacing: 6px; }}
QLineEdit, QComboBox {{
    background: {GRAU_NACHT}; color: {GRAU_HELL};
    border: 1px solid {GRAU_DUNKEL}; border-radius: 4px; padding: 4px 8px;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {BLAU}; }}
QListView {{ background: {GRAU_NACHT}; border: 0; }}
QListView::item:selected {{ background: {BLAU}; color: {WEISS}; }}
QStatusBar {{ background: {GRAU_KOHLE}; color: {GRAU_HELL}; }}
"""


class Hauptfenster(QMainWindow):
    def __init__(self, archiv: Path) -> None:
        super().__init__()
        self.archiv = archiv
        self.liste = Bestandsliste(archiv)

        self.setWindowTitle(f"WOLKENErnte {__version__} – {archiv.name}")
        self.resize(1200, 800)
        self.setStyleSheet(STIL)

        symbol = Path(__file__).resolve().parent.parent.parent / "assets/icon-256.png"
        if symbol.exists():
            self.setWindowIcon(QIcon(str(symbol)))

        self._raster_bauen()
        self._leiste_bauen()

        self.ansicht = Einzelansicht(archiv)
        self.ansicht.zurueck_gewuenscht = self._zum_raster
        self.ansicht.weiter_gewuenscht = self._blaettern

        self.ebenen = QStackedWidget()
        self.ebenen.addWidget(self.raster)
        self.ebenen.addWidget(self.ansicht)
        self.setCentralWidget(self.ebenen)

        self.setStatusBar(QStatusBar())
        self._auswahl_anwenden()

    # -- Aufbau ------------------------------------------------------------

    def _raster_bauen(self) -> None:
        self.modell = Bildmodell(self.archiv, [])
        self.raster = QListView()
        self.raster.setModel(self.modell)
        self.raster.setViewMode(QListView.ViewMode.IconMode)
        self.raster.setIconSize(self.raster.iconSize().__class__(KACHEL, KACHEL))
        self.raster.setGridSize(self.raster.gridSize().__class__(
            KACHEL + 12, KACHEL + 12))
        self.raster.setResizeMode(QListView.ResizeMode.Adjust)
        self.raster.setSpacing(4)
        self.raster.setUniformItemSizes(True)
        self.raster.setSelectionMode(
            QListView.SelectionMode.ExtendedSelection)
        # **Bildlauf in Pixeln, nicht in Zeilen.** Sonst springt die
        # Ansicht bei jedem Raddrehen um eine ganze Kachelreihe.
        self.raster.setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel)
        self.raster.doubleClicked.connect(self._oeffnen)
        self.raster.activated.connect(self._oeffnen)

    def _leiste_bauen(self) -> None:
        leiste = QToolBar()
        leiste.setMovable(False)
        self.addToolBar(leiste)

        self.jahrwahl = QComboBox()
        self.jahrwahl.addItem("Alle Jahre", None)
        for jahr, anzahl in self.liste.jahre():
            self.jahrwahl.addItem(f"{jahr}  ({anzahl})", jahr)
        if self.liste.ohne_datum:
            self.jahrwahl.addItem(
                f"ohne Datum  ({len(self.liste.ohne_datum)})", "ohne")
        self.jahrwahl.currentIndexChanged.connect(self._auswahl_anwenden)
        leiste.addWidget(QLabel("  Jahr "))
        leiste.addWidget(self.jahrwahl)

        self.albumwahl = QComboBox()
        self.albumwahl.addItem("Alle Alben", None)
        for name, anzahl in self.liste.alben():
            self.albumwahl.addItem(f"{name}  ({anzahl})", name)
        self.albumwahl.currentIndexChanged.connect(self._auswahl_anwenden)
        leiste.addWidget(QLabel("  Album "))
        leiste.addWidget(self.albumwahl)

        # Der Kasten erscheint nur, wenn es Schlagwörter gibt. Eine
        # immer leere Auswahlliste sähe nach einem Defekt aus – dabei
        # fehlt nur ein Durchlauf, den niemand angestoßen hat.
        self.schlagwortwahl = QComboBox()
        self.schlagwortwahl.addItem("Alle Schlagwörter", None)
        vergebene = self.liste.schlagworte()
        for name, anzahl in vergebene:
            self.schlagwortwahl.addItem(f"{name}  ({anzahl})", name)
        self.schlagwortwahl.currentIndexChanged.connect(self._auswahl_anwenden)
        if vergebene:
            leiste.addWidget(QLabel("  Schlagwort "))
            leiste.addWidget(self.schlagwortwahl)

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText(
            "Suchen in Namen, Titeln, Alben, Schlagwörtern und Datum …  "
            "(Strg+F)")
        self.suchfeld.setClearButtonEnabled(True)
        # Erst beim Eingabeende suchen, nicht bei jedem Tastendruck:
        # Ein Durchlauf über 14.770 Einträge bei jedem Buchstaben
        # machte das Tippen zäh.
        self.suchfeld.editingFinished.connect(self._auswahl_anwenden)
        self.suchfeld.returnPressed.connect(self._auswahl_anwenden)
        leiste.addWidget(QLabel("  "))
        leiste.addWidget(self.suchfeld)

        suchen = QAction("Suchen", self)
        suchen.setShortcut(QKeySequence.StandardKey.Find)
        suchen.triggered.connect(self.suchfeld.setFocus)
        self.addAction(suchen)

    # -- Auswahl -----------------------------------------------------------

    def _auswahl_anwenden(self) -> None:
        wort = self.suchfeld.text().strip()
        if wort:
            bilder = self.liste.suchen(wort)
        else:
            jahr = self.jahrwahl.currentData()
            bilder = self.liste.auswahl(
                jahr=jahr if isinstance(jahr, int) else None,
                album=self.albumwahl.currentData(),
                schlagwort=self.schlagwortwahl.currentData(),
                nur_ohne_datum=(jahr == "ohne"),
            )

        self.modell.zeigen(bilder)
        gb = sum(b.groesse for b in bilder) / 1e9
        self.statusBar().showMessage(
            f"{len(bilder):n} von {len(self.liste.bilder):n} Dateien"
            f"   ·   {gb:.1f} GB"
        )

    # -- Einzelansicht -----------------------------------------------------

    def _oeffnen(self, index) -> None:
        bild = self.modell.bild_bei(index)
        if bild is None:
            return
        self._stelle = index.row()
        self.ansicht.zeigen(bild)
        self.ebenen.setCurrentWidget(self.ansicht)
        self.ansicht.setFocus()

    def _blaettern(self, richtung: int) -> None:
        neu = self._stelle + richtung
        if not 0 <= neu < len(self.modell.bilder):
            return
        self._stelle = neu
        self.ansicht.zeigen(self.modell.bilder[neu])

    def _zum_raster(self) -> None:
        self.ebenen.setCurrentWidget(self.raster)
        stelle = self.modell.index(self._stelle, 0)
        self.raster.setCurrentIndex(stelle)
        self.raster.scrollTo(stelle)
        self.raster.setFocus()

    def closeEvent(self, ereignis) -> None:  # noqa: N802
        self.ansicht.aufraeumen()
        super().closeEvent(ereignis)


def archiv_erfragen(app) -> Path | None:
    """Nach dem Archivordner fragen – im Dialog, nicht im Terminal.

    **Nötig, weil der Menüeintrag keinen Pfad kennen kann.** Vorher gab
    das Programm an dieser Stelle eine Textmeldung aus und beendete
    sich; aus dem Anwendungsmenü gestartet sah das aus, als sei nichts
    passiert. Wer auf ein Programm klickt, soll gefragt werden.
    """
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    QMessageBox.information(
        None, "WOLKENErnte",
        "Noch kein Archiv bekannt.\n\n"
        "Bitte den Ordner auswählen, in dem Ihre Bilder liegen –\n"
        "oder einen leeren Ordner, in den geerntet werden soll.\n\n"
        "Beim nächsten Mal merkt sich WOLKENErnte ihn.",
    )
    gewaehlt = QFileDialog.getExistingDirectory(
        None, "Archivordner auswählen", str(Path.home()),
    )
    return Path(gewaehlt) if gewaehlt else None


def starten(archiv: Path | None) -> int:
    """Das Fenster öffnen und laufen lassen."""
    import sys

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication(sys.argv)

    if archiv is None or not archiv.is_dir():
        archiv = archiv_erfragen(app)
        if archiv is None:
            return 1
        from ..einstellungen import archiv_merken
        archiv_merken(archiv)
    app.setApplicationName("WOLKENErnte")
    app.setApplicationDisplayName("WOLKENErnte")

    fenster = Hauptfenster(archiv)
    if not fenster.liste.bilder:
        # Auch das gehört in einen Dialog: Aus dem Menü gestartet sieht
        # eine Textmeldung im Nichts aus wie ein abgestürztes Programm.
        QMessageBox.information(
            None, "WOLKENErnte",
            f"In {archiv} liegen keine Bilder.\n\n"
            "Erst ernten – auf der Kommandozeile:\n"
            f"    wolkenernte ernten \"{archiv}\" <Quelle>",
        )
        return 1

    fenster.show()
    return app.exec()

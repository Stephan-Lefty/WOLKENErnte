"""Das Hauptfenster: Raster, Filter, Suche.

Aufgebaut wie die Weboberfläche und auf demselben Fundament – beide
fragen :class:`wolkenernte.bestandsliste.Bestandsliste`. Was hier
anders ist, ist die Bedienung: Tastatur statt Mausklicks, und die
Einzelansicht ist keine neue Seite, sondern eine zweite Ebene im selben
Fenster.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence, QTextCharFormat
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QWidget,
)

from .. import __version__, symbole
from ..bestandsliste import Bestandsliste, umfang
from ..farben import (
    BLAU,
    GRAU_DUNKEL,
    GRAU_HELL,
    GRAU_KOHLE,
    GRAU_MITTE,
    GRAU_NACHT,
    ROT_HELL,
    WEISS,
)
from .ansicht import Einzelansicht
from .modell import KACHEL, Bildmodell

STIL = f"""
QMainWindow, QWidget {{ background: {GRAU_NACHT}; color: {GRAU_HELL}; }}
QToolBar {{ background: {GRAU_KOHLE}; border: 0; padding: 4px; spacing: 6px; }}
QLineEdit, QComboBox, QDateEdit {{
    background: {GRAU_NACHT}; color: {GRAU_HELL};
    border: 1px solid {GRAU_DUNKEL}; border-radius: 4px; padding: 4px 8px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border-color: {BLAU}; }}
QDateEdit:disabled {{ color: {GRAU_MITTE}; }}
/* Das Kalenderblatt selbst erbt den dunklen Grund nicht von allein -
   ohne diese Zeilen klappt ein weisses Blatt aus einem dunklen
   Fenster. */
QCalendarWidget QWidget {{ background: {GRAU_KOHLE}; color: {GRAU_HELL}; }}
QCalendarWidget QAbstractItemView {{
    background: {GRAU_NACHT}; color: {GRAU_HELL};
    selection-background-color: {BLAU}; selection-color: {WEISS};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {GRAU_MITTE}; }}
QListView {{ background: {GRAU_NACHT}; border: 0; }}
QListView::item:selected {{ background: {BLAU}; color: {WEISS}; }}
QStatusBar {{ background: {GRAU_KOHLE}; color: {GRAU_HELL}; }}
QMenuBar, QMenu {{ background: {GRAU_KOHLE}; color: {GRAU_HELL}; }}
QMenuBar::item:selected, QMenu::item:selected {{
    background: {BLAU}; color: {WEISS};
}}
QMenu::item:disabled {{ color: {GRAU_MITTE}; }}
QTreeWidget {{
    background: {GRAU_NACHT}; color: {GRAU_HELL};
    border: 1px solid {GRAU_DUNKEL};
}}
QTreeWidget::item:selected {{ background: {BLAU}; color: {WEISS}; }}
QHeaderView::section {{
    background: {GRAU_KOHLE}; color: {GRAU_HELL};
    border: 0; padding: 4px;
}}
QPushButton {{
    background: {GRAU_KOHLE}; color: {GRAU_HELL};
    border: 1px solid {GRAU_DUNKEL}; border-radius: 4px; padding: 5px 14px;
}}
QPushButton:hover {{ border-color: {BLAU}; }}
QPushButton:default {{ background: {BLAU}; color: {WEISS}; border: 0; }}
QPushButton:disabled {{ color: {GRAU_MITTE}; }}
QProgressBar {{
    background: {GRAU_KOHLE}; color: {GRAU_HELL};
    border: 0; border-radius: 4px; text-align: center;
}}
QProgressBar::chunk {{ background: {BLAU}; border-radius: 4px; }}
"""


def _wochenende_faerben(kalender) -> None:
    """Samstag und Sonntag in ``ROT_HELL`` statt in Qts reinem Rot.

    **Über die Textformate, nicht über das Stilblatt** – Qt setzt die
    Wochenendfarbe im Code, und keine CSS-Regel kommt dagegen an.

    Das Rot muss weichen, weil es auf dem dunklen Grund nur einen
    Kontrast von 3,81 erreicht; für Text verlangt WCAG 4,5. ``ROT_HELL``
    steht in der Palette genau dafür (»dasselbe auf dunklem Grund«) und
    kommt auf 7,07. Die Unterscheidung selbst bleibt: In einem
    Fotoarchiv ist das Wochenende die halbe Suche.
    """
    fett = QTextCharFormat()
    fett.setForeground(QColor(ROT_HELL))
    for tag in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
        kalender.setWeekdayTextFormat(tag, fett)


def _benennen(teil, name: str) -> None:
    """Einem Bedienteil ohne sichtbare Aufschrift einen Namen geben.

    **Eine Aufschrift wegzunehmen heißt nicht, die Auskunft
    wegzunehmen.** Wer nicht hinsieht, hört sonst dreimal
    »Kombinationsfeld« hintereinander und muss aus dem Inhalt raten,
    welches davon die Alben sind. `accessibleName` ist das, was
    Vorlesesoftware liest; `toolTip` das, was beim Verweilen mit der
    Maus erscheint.
    """
    teil.setAccessibleName(name)
    teil.setToolTip(name)


class Hauptfenster(QMainWindow):
    def __init__(self, archiv: Path) -> None:
        super().__init__()
        self.archiv = archiv
        self._rclone = None
        self.liste = Bestandsliste(archiv)

        self.setWindowTitle(f"WOLKENErnte {__version__} – {archiv.name}")
        self.resize(1200, 800)

        self.setWindowIcon(symbole.qt_symbol())

        self._raster_bauen()
        self._leiste_bauen()
        self._menue_bauen()

        self.ansicht = Einzelansicht(archiv)
        self.ansicht.zurueck_gewuenscht = self._zum_raster
        self.ansicht.weiter_gewuenscht = self._blaettern
        self.ansicht.menue_gewuenscht = self._menue_einzeln

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
        self.raster.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.raster.customContextMenuRequested.connect(self._menue_zeigen)

    def _leiste_bauen(self) -> None:
        """Jahr, Album, Schlagwort, Suche – in einer Zeile.

        **Ohne Aufschriften davor.** Der erste Eintrag jedes Kastens
        sagt bereits, worum es geht: »Alle Jahre«, »Alle Alben«, »Alle
        Schlagwörter«. Ein »Jahr« daneben wiederholt das nur und nimmt
        dem Suchfeld die Breite, die dessen Platzhalter braucht – der
        war abgeschnitten.

        **Stattdessen ein Name für die Vorlesesoftware.** Eine
        Aufschrift wegzunehmen heißt nicht, die Auskunft wegzunehmen:
        `setAccessibleName` sagt Orca und den Werkzeugen der
        Arbeitsumgebung weiterhin, welcher Kasten das ist – sonst hörte
        jemand, der nicht hinsieht, dreimal »Kombinationsfeld« und
        müsste den Inhalt raten. Und `setToolTip` gibt sie dem zurück,
        der mit der Maus darüber verweilt.
        """
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
        _benennen(self.jahrwahl, "Jahr")
        leiste.addWidget(QLabel("  "))
        leiste.addWidget(self.jahrwahl)

        self.albumwahl = QComboBox()
        self.albumwahl.addItem("Alle Alben", None)
        for name, anzahl in self.liste.alben():
            self.albumwahl.addItem(f"{name}  ({anzahl})", name)
        self.albumwahl.currentIndexChanged.connect(self._auswahl_anwenden)
        _benennen(self.albumwahl, "Album")
        leiste.addWidget(QLabel("  "))
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
        _benennen(self.schlagwortwahl, "Schlagwort")
        if vergebene:
            leiste.addWidget(QLabel("  "))
            leiste.addWidget(self.schlagwortwahl)

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText(
            "Suchen in Namen, Titeln, Alben, Schlagwörtern und Datum …  "
            "(Strg+F)")
        self.suchfeld.setClearButtonEnabled(True)
        # Ein Platzhalter ist keine Aufschrift: Er verschwindet beim
        # ersten Buchstaben, und nicht jede Vorlesesoftware liest ihn.
        self.suchfeld.setAccessibleName("Suchen")
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

        self._zeitleiste_bauen()

    def _zeitleiste_bauen(self) -> None:
        """Zwei Kalender: alles, was zwischen zwei Tagen entstanden ist.

        **Eine eigene Zeile.** Die erste ist mit Jahr, Album, Schlagwort
        und Suchfeld schon voll; zwei Datumsfelder dazwischen drückten
        das Suchfeld auf Fingerbreite.

        **Und ein Haken davor, kein bloßes Feldpaar.** Ohne ihn müsste
        beim Start irgendein Zeitraum voreingestellt sein, und der
        filterte sofort – die 317 Bilder ohne Aufnahmedatum wären
        wortlos verschwunden, weil sie in keinem Zeitraum liegen. Der
        Haken setzt sich von selbst, sobald jemand ein Datum ändert:
        Datum wählen und nichts passiert, wäre die schlechtere Antwort.
        """
        self.addToolBarBreak()
        leiste = QToolBar()
        leiste.setMovable(False)
        self.addToolBar(leiste)

        self.zeitraum_an = QCheckBox("Zeitraum")
        self.zeitraum_an.toggled.connect(self._zeitraum_umschalten)
        leiste.addWidget(QLabel("  "))
        leiste.addWidget(self.zeitraum_an)

        erste, letzte = self._spanne()
        self.von_feld, self.bis_feld = QDateEdit(), QDateEdit()
        # Die Aufschriften »von« und »bis« stehen daneben, aber Qt
        # verbindet einen QLabel nicht von selbst mit dem Feld danach –
        # eine Vorlesesoftware hörte zweimal dasselbe leere »Datum«.
        _benennen(self.von_feld, "Zeitraum von")
        _benennen(self.bis_feld, "Zeitraum bis")
        for feld, tag in ((self.von_feld, erste), (self.bis_feld, letzte)):
            feld.setCalendarPopup(True)
            feld.setDisplayFormat("dd.MM.yyyy")
            # Die Grenzen sind die des Bestands: Ein Kalender, in dem
            # man ins Jahr 1752 blaettern kann, obwohl das aelteste Bild
            # von 2011 ist, hilft niemandem.
            feld.setDateRange(erste, letzte)
            feld.setDate(tag)
            feld.setEnabled(False)
            _wochenende_faerben(feld.calendarWidget())
            feld.dateChanged.connect(self._zeitraum_geaendert)

        leiste.addWidget(QLabel(" von "))
        leiste.addWidget(self.von_feld)
        leiste.addWidget(QLabel(" bis "))
        leiste.addWidget(self.bis_feld)

        self.zeit_zuruecksetzen = QPushButton("Ganzer Bestand")
        self.zeit_zuruecksetzen.setEnabled(False)
        self.zeit_zuruecksetzen.clicked.connect(self._zeitraum_zuruecksetzen)
        leiste.addWidget(self.zeit_zuruecksetzen)

        self.zeit_hinweis = QLabel("")
        self.zeit_hinweis.setStyleSheet(f"color: {GRAU_MITTE};")
        leiste.addWidget(QLabel("  "))
        leiste.addWidget(self.zeit_hinweis)

    def _spanne(self) -> tuple[QDate, QDate]:
        """Der älteste und der jüngste Aufnahmetag im Archiv.

        Bilder ohne bekanntes Datum tragen den Zeitstempel der
        Übernahme – die zählen hier nicht mit, sonst reichte die Spanne
        immer bis heute. Ist das Archiv leer, bleibt ein weites Fenster
        stehen, damit die Felder überhaupt bedienbar sind.
        """
        tage = [b.zeit.date() for b in self.liste.bilder if b.datum_bekannt]
        if not tage:
            return QDate(1990, 1, 1), QDate.currentDate()
        return QDate(min(tage)), QDate(max(tage))

    def _zeitraum_umschalten(self, an: bool) -> None:
        for teil in (self.von_feld, self.bis_feld, self.zeit_zuruecksetzen):
            teil.setEnabled(an)
        self._auswahl_anwenden()

    def _zeitraum_geaendert(self) -> None:
        if not self.zeitraum_an.isChecked():
            # Von selbst einschalten, ohne diesen Aufruf zu verdoppeln:
            # ``setChecked`` löst ``_zeitraum_umschalten`` aus, und das
            # wendet die Auswahl schon an.
            self.zeitraum_an.setChecked(True)
            return
        self._auswahl_anwenden()

    def _zeitraum_zuruecksetzen(self) -> None:
        self._spanne_setzen()
        # Ohne das Stummschalten schaltete ``setDate`` den Haken gleich
        # wieder ein, den die letzte Zeile ausschaltet.
        self.zeitraum_an.setChecked(False)

    def _spanne_setzen(self) -> None:
        """Die Felder auf den ganzen Bestand stellen.

        Auch nach dem Ernten nötig: Neue Bilder verschieben den
        jüngsten Tag, und ein Kalender, der davor endet, ließe sich
        nicht auf sie einstellen.
        """
        erste, letzte = self._spanne()
        for feld, tag in ((self.von_feld, erste), (self.bis_feld, letzte)):
            gesperrt = feld.blockSignals(True)
            feld.setDateRange(erste, letzte)
            feld.setDate(tag)
            feld.blockSignals(gesperrt)

    # -- Wolken ------------------------------------------------------------

    def _menue_bauen(self) -> None:
        """Die Menüleiste – bisher gab es keine.

        Das Ernten aus einem Cloudspeicher gehört nicht in die
        Werkzeugleiste neben die Filter: Es ist kein Blick auf den
        Bestand, sondern ein Eingriff.

        **In der Oberfläche heißt es »Cloudspeicher«, im Code
        »Wolke«.** Das ist kein Versehen: Der Quelltext ist durchgehend
        deutsch benannt – ``wolke.py``, ``aufraeumen.py`` –, aber im
        Menü sucht niemand nach einer Wolke. Dort steht das Wort, das
        auf den Netzseiten der Anbieter steht.
        """
        menue = self.menuBar().addMenu("&Cloudspeicher")

        eintrag = menue.addAction("Bei einer Cloud anmelden …")
        eintrag.triggered.connect(self._zugang_anlegen)

        self.holen_menue = menue.addMenu("Bilder holen aus")
        self.holen_menue.aboutToShow.connect(self._zugaenge_auffrischen)

        # **Der Takeout steht hier oben, nicht unter den Zugängen.**
        # Er braucht keinen: Google Fotos ist für fremde Programme
        # verschlossen, und der Export ist der einzige Weg an den
        # eigenen Bestand. Ein Anwender, der »Google« sucht, sucht ihn
        # unter »Bilder holen aus« - und findet dort sonst nichts.
        eintrag = menue.addAction("Google-Takeout einlesen (ZIP-Dateien) …")
        eintrag.triggered.connect(self._takeout_einlesen)

        menue.addSeparator()
        self.aufraeum_menue = menue.addMenu("In der Cloud aufräumen")
        self.aufraeum_menue.aboutToShow.connect(self._zugaenge_auffrischen)

        menue.addSeparator()
        eintrag = menue.addAction("Zugänge auffrischen")
        eintrag.triggered.connect(self._zugaenge_auffrischen)

    def _dienst(self):
        """Den rclone-Dienst starten, wenn er gebraucht wird.

        **Nicht beim Programmstart.** Wer nur seine Bilder durchsehen
        will, soll rclone nicht laufen haben müssen – und wer es gar
        nicht installiert hat, soll trotzdem ein Fenster bekommen.
        """
        if getattr(self, "_rclone", None) is not None:
            return self._rclone
        from ..rclone import Dienst, RcloneFehler
        from ..zugang import konfiguration

        pfad = konfiguration()
        pfad.parent.mkdir(parents=True, exist_ok=True)
        if not pfad.exists():
            pfad.touch(mode=0o600)
        pfad.chmod(0o600)
        try:
            self._rclone = Dienst.starten(pfad)
        except RcloneFehler as fehler:
            QMessageBox.warning(self, "WOLKENErnte", str(fehler))
            return None
        return self._rclone

    def _zugang_anlegen(self) -> None:
        """Anbieter wählen, anmelden, gleich hineinsehen."""
        from .anmelden import anmelden

        dienst = self._dienst()
        if dienst is None:
            return
        name = anmelden(dienst, self)
        if not name:
            return
        self.statusBar().showMessage(
            f"Zugang »{name}« angelegt und erprobt", 6000)
        self._zugaenge_auffrischen()
        self._durchsehen(name)

    def _zugaenge_auffrischen(self) -> None:
        from ..anbieter import NACH_KENNUNG, darf_loeschen

        self.holen_menue.clear()
        self.aufraeum_menue.clear()
        dienst = self._dienst()
        if dienst is None:
            return
        namen = dienst.remotes()
        if not namen:
            for wo in (self.holen_menue, self.aufraeum_menue):
                eintrag = wo.addAction("Noch kein Zugang angemeldet")
                eintrag.setEnabled(False)
            return

        for name in namen:
            art = dienst.art(name)
            anbieter = NACH_KENNUNG.get(art)
            beschriftung = (f"{name}  ({anbieter.name})" if anbieter
                            else f"{name}  (unbekannte Art)")

            eintrag = self.holen_menue.addAction(beschriftung)
            eintrag.triggered.connect(
                lambda _=False, n=name: self._durchsehen(n))

            # **Kein Löscheintrag, wo nicht gelöscht werden kann.**
            # Dieselbe Regel wie überall: einen Knopf, der nichts tut,
            # soll es nicht geben. Statt ihn wegzulassen, steht hier
            # der Grund - sonst sucht jemand einen Eintrag, den es nie
            # gab.
            eintrag = self.aufraeum_menue.addAction(beschriftung)
            if darf_loeschen(art):
                eintrag.triggered.connect(
                    lambda _=False, n=name: self._aufraeumen(n))
            else:
                eintrag.setEnabled(False)
                eintrag.setText(f"{beschriftung} – dort nur lesbar")

    def _takeout_einlesen(self) -> None:
        """Google-Takeout: auswählen, prüfen, holen – und dann fragen.

        **Das Löschen der ZIP-Dateien hängt an vier Bedingungen**,
        dieselbe Strenge wie beim Aufräumen in der Wolke: Der Lauf ist
        durchgelaufen; `erfassen` ist mitgelaufen, sonst wären Orte,
        Titel und Alben mit den ZIPs weg; **jedes einzelne** Bild ist im
        Archiv nachgewiesen, mit für diesen Lauf gerechneten
        Prüfsummen; und der Anwender bestätigt es, nachdem er die Zahlen
        gesehen hat. Fehlt eine, bleiben die ZIPs liegen.
        """
        from .takeout import TakeoutLauf, TakeoutWaehlen

        dialog = TakeoutWaehlen(self.archiv, self)
        if not dialog.exec() or not dialog.ausgewaehlt:
            return

        lauf = TakeoutLauf(self.archiv, dialog.ausgewaehlt, self)
        if not lauf.exec() or lauf.ergebnis is None:
            return
        bilanz, nachweis = lauf.ergebnis
        self._neu_einlesen()

        if not nachweis.vollstaendig:
            QMessageBox.warning(
                self, "WOLKENErnte",
                f"Geholt:\n\n{bilanz}\n\n"
                f"**{len(nachweis.fehlend)} von {nachweis.geprueft} Dateien "
                f"sind im Archiv nicht wiederzufinden.** Die ZIP-Dateien "
                f"bleiben liegen – nichts löschen, bevor das geklärt ist.")
            return

        text = (f"Geholt:\n\n{bilanz}\n\n"
                f"Nachgewiesen: alle {nachweis.geprueft} Dateien des "
                f"Exports liegen im Archiv.")
        if not dialog.loeschen_gewuenscht:
            QMessageBox.information(self, "WOLKENErnte", text)
            return

        self._takeout_loeschen(dialog.ausgewaehlt, text)

    def _takeout_loeschen(self, teile, was_geschah: str) -> None:
        """Die ZIP-Dateien wegräumen – nach einer letzten Rückfrage.

        Die Rückfrage nennt Zahl und Umfang und hat **»Behalten« als
        Vorgabe**. Ein Dialog, bei dem die Eingabetaste löscht, ist
        keine Rückfrage.
        """
        from ..bestandsliste import umfang

        gesamt = sum(p.stat().st_size for p in teile if p.exists())
        frage = QMessageBox(self)
        frage.setWindowTitle("WOLKENErnte")
        frage.setIcon(QMessageBox.Icon.Warning)
        frage.setText(f"{was_geschah}\n\n"
                      f"{len(teile)} ZIP-Datei(en) mit {umfang(gesamt)} "
                      f"jetzt löschen?")
        frage.setInformativeText(
            "Danach ist das Archiv die einzige Kopie dieser Bilder.\n"
            + "\n".join(f"  {p.name}" for p in teile))
        behalten = frage.addButton("Behalten", QMessageBox.ButtonRole.RejectRole)
        frage.addButton("Löschen", QMessageBox.ButtonRole.DestructiveRole)
        frage.setDefaultButton(behalten)
        frage.exec()
        if frage.clickedButton() is behalten:
            return

        geloescht, misslungen = 0, []
        for pfad in teile:
            try:
                pfad.unlink()
                geloescht += 1
            except OSError as fehler:
                misslungen.append(f"{pfad.name}: {fehler}")

        meldung = f"{geloescht} ZIP-Datei(en) gelöscht, {umfang(gesamt)} frei."
        if misslungen:
            meldung += "\n\nNicht gelöscht:\n" + "\n".join(misslungen)
        QMessageBox.information(self, "WOLKENErnte", meldung)

    def _durchsehen(self, zugang: str) -> None:
        from .wolken import Ernter, WolkeDurchsehen

        dienst = self._dienst()
        if dienst is None:
            return
        dialog = WolkeDurchsehen(dienst, zugang, self)
        if not dialog.exec() or not dialog.gewaehlt:
            return

        lauf = Ernter(dienst, dialog.gewaehlt, self.archiv, self,
                      mit_unterordnern=dialog.mit_unterordnern_gewaehlt)
        if not lauf.exec() or lauf.bilanz is None:
            return

        bilanz = lauf.bilanz
        QMessageBox.information(
            self, "WOLKENErnte",
            f"Aus {dialog.gewaehlt} geholt:\n\n{bilanz}\n\n"
            "Die Bilder liegen jetzt im Archiv. Was in der Cloud bleibt "
            "und was weg darf, entscheidet ein eigener Schritt – dort "
            "wird erst nachgewiesen, dass jede Datei angekommen ist.")
        self._neu_einlesen()

    def _aufraeumen(self, zugang: str) -> None:
        """Prüfen, zeigen, dann erst löschen."""
        from ..aufraeumen import AufraeumFehler, erlaubnis_pruefen
        from ..wolke import Wolke
        from .aufraeumen import AufraeumenDialog
        from .wolken import WolkeDurchsehen

        dienst = self._dienst()
        if dienst is None:
            return
        try:
            erlaubnis_pruefen(dienst, zugang)
        except AufraeumFehler as fehler:
            QMessageBox.warning(self, "WOLKENErnte", str(fehler))
            return

        wahl = WolkeDurchsehen(dienst, zugang, self)
        wahl.setWindowTitle(f"Aufräumen in {zugang}: – Ordner wählen")
        wahl.holen.setText("Diesen Ordner prüfen")
        if not wahl.exec() or not wahl.gewaehlt:
            return

        name, _, unterordner = wahl.gewaehlt.partition(":")
        with Wolke(dienst, name, unterordner,
                   mit_unterordnern=wahl.mit_unterordnern_gewaehlt) as wolke:
            if not wolke.medien():
                darunter = ("" if wahl.mit_unterordnern_gewaehlt else
                            "\n\nIn den Unterordnern wurde nicht gesucht – "
                            "dafür »Unterordner mitnehmen« ankreuzen.")
                QMessageBox.information(
                    self, "WOLKENErnte",
                    f"In {wolke.wurzel} liegen keine Bilder oder Videos."
                    + darunter)
                return
            dialog = AufraeumenDialog(dienst, wolke, self.archiv, self)
            dialog.exec()
            if dialog.geloescht:
                self.statusBar().showMessage(
                    f"{dialog.geloescht} Dateien in {wolke.wurzel} gelöscht",
                    8000)

    def _neu_einlesen(self) -> None:
        """Das Archiv noch einmal einlesen, nach dem Ernten."""
        self.liste = Bestandsliste(self.archiv)
        if not self.zeitraum_an.isChecked():
            # Nur wenn kein Zeitraum gilt. Sonst risse das Einlesen dem
            # Anwender die Grenzen weg, die er gerade eingestellt hat.
            self._spanne_setzen()
        self._auswahl_anwenden()

    # -- Auswahl -----------------------------------------------------------

    def _zeit_hinweis_setzen(self, von, bis) -> None:
        """Sagen, warum nichts kommt – statt eine leere Fläche zu zeigen.

        Zwei Fälle liefern zuverlässig null Treffer, und beide sehen wie
        ein leeres Archiv aus, wenn niemand sie benennt: vertauschte
        Grenzen, und »ohne Datum« zusammen mit einem Zeitraum – Bilder
        ohne Aufnahmedatum liegen in keinem.
        """
        if von and bis and von > bis:
            self.zeit_hinweis.setText(
                "Das Bis-Datum liegt vor dem Von-Datum.")
        elif von and self.jahrwahl.currentData() == "ohne":
            self.zeit_hinweis.setText(
                "»ohne Datum« und ein Zeitraum schließen einander aus.")
        else:
            self.zeit_hinweis.setText("")

    def _zeitgrenzen(self) -> tuple[object, object]:
        """Was der Zeitraumfilter gerade vorgibt – oder zweimal ``None``."""
        if not self.zeitraum_an.isChecked():
            return None, None
        return self.von_feld.date().toPython(), self.bis_feld.date().toPython()

    def _auswahl_anwenden(self) -> None:
        von, bis = self._zeitgrenzen()
        wort = self.suchfeld.text().strip()
        if wort:
            bilder = self.liste.suchen(wort)
            # Der Zeitraum gilt **auch für die Suche**. »Alle Bilder
            # aus dem Urlaub, aber nur die aus 2023« ist genau die
            # Frage, für die es beides zusammen braucht.
            if von or bis:
                bilder = [b for b in bilder if b.datum_bekannt
                          and von <= b.zeit.date() <= bis]
        else:
            jahr = self.jahrwahl.currentData()
            bilder = self.liste.auswahl(
                jahr=jahr if isinstance(jahr, int) else None,
                album=self.albumwahl.currentData(),
                schlagwort=self.schlagwortwahl.currentData(),
                von=von, bis=bis,
                nur_ohne_datum=(jahr == "ohne"),
            )

        self._zeit_hinweis_setzen(von, bis)
        self.modell.zeigen(bilder)
        self.statusBar().showMessage(
            f"{len(bilder):n} von {len(self.liste.bilder):n} Dateien"
            f"   ·   {umfang(sum(b.groesse for b in bilder))}"
        )

    # -- Weiterreichen -----------------------------------------------------

    def _menue_zeigen(self, stelle) -> None:
        """Das Menü zur rechten Maustaste.

        **Es gilt für die ganze Auswahl, nicht nur für das Bild unter
        dem Zeiger.** Wer zwanzig Bilder markiert und dann rechts
        klickt, meint die zwanzig. Angeklickt wird aber trotzdem
        vorgewählt – sonst öffnete ein Rechtsklick ins Leere die zuletzt
        markierten Bilder, und das überrascht.
        """
        unter_dem_zeiger = self.raster.indexAt(stelle)
        if not unter_dem_zeiger.isValid():
            return
        if unter_dem_zeiger not in self.raster.selectedIndexes():
            self.raster.setCurrentIndex(unter_dem_zeiger)

        bilder = [self.modell.bild_bei(i)
                  for i in self.raster.selectedIndexes()]
        bilder = [b for b in bilder if b is not None]
        if not bilder:
            return

        menue = QMenu(self)
        menue.addAction(
            "Ansehen" if len(bilder) == 1 else f"{len(bilder)} ansehen",
            lambda: self._oeffnen(self.raster.currentIndex()))
        menue.addSeparator()
        self._bearbeiten_eintragen(menue, bilder)
        menue.exec(self.raster.viewport().mapToGlobal(stelle))

    def _bearbeiten_eintragen(self, menue, bilder: list) -> None:
        """Die Einträge zum Weiterreichen an andere Programme.

        Wird auch von der Einzelansicht benutzt – dieselbe Liste, damit
        beide Wege dasselbe anbieten.
        """
        from .. import bearbeiten

        pfade = [self.archiv / b.pfad for b in bilder]
        wieviele = "" if len(pfade) == 1 else f" ({len(pfade)})"

        for programm in bearbeiten.vorhandene():
            eintrag = menue.addAction(f"Mit {programm.name} bearbeiten{wieviele}")
            if programm.wofuer:
                eintrag.setToolTip(programm.wofuer)
            eintrag.triggered.connect(
                lambda _=False, p=programm: self._weiterreichen(
                    pfade, lambda pfad: bearbeiten.oeffnen_mit(pfad, p)))

        eintrag = menue.addAction(f"Mit anderem Programm öffnen …{wieviele}")
        eintrag.triggered.connect(
            lambda: self._weiterreichen(pfade, bearbeiten.auswahl_anbieten))

        menue.addSeparator()
        eintrag = menue.addAction("Im Dateimanager zeigen")
        # Nur das erste: Zwanzig Dateimanagerfenster will niemand.
        eintrag.triggered.connect(
            lambda: self._weiterreichen(pfade[:1], bearbeiten.im_dateimanager))

    def _menue_einzeln(self, stelle, bild) -> None:
        """Dasselbe Menü in der Einzelansicht, für dieses eine Bild."""
        menue = QMenu(self)
        self._bearbeiten_eintragen(menue, [bild])
        menue.exec(stelle)

    def _weiterreichen(self, pfade: list[Path], was) -> None:
        """Ein anderes Programm aufrufen und Fehler sichtbar machen.

        Ohne diesen Dialog bliebe ein misslungener Start völlig stumm –
        der Anwender klickt, und nichts geschieht.
        """
        from ..bearbeiten import BearbeitenFehler

        for pfad in pfade:
            try:
                was(pfad)
            except BearbeitenFehler as fehler:
                QMessageBox.warning(self, "WOLKENErnte", str(fehler))
                return
        self.statusBar().showMessage(
            f"{len(pfade)} an ein anderes Programm übergeben", 4000)

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
        # rclone läuft als eigener Prozess weiter, wenn niemand ihn
        # beendet - und hält dabei die Zugangsdaten im Speicher.
        if getattr(self, "_rclone", None) is not None:
            self._rclone.beenden()
            self._rclone = None
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

    # **Vor dem ersten Fenster.** Das Symbol der Anwendung entscheidet,
    # was in der Fensterleiste und im Umschalter steht - und wenn schon
    # ein Dialog offen war, ändert Qt es dort nicht mehr nachträglich.
    app.setWindowIcon(symbole.qt_symbol())
    # Damit die Arbeitsumgebung das Fenster dem Menüeintrag zuordnet.
    # Ohne das zeigt GNOME ein Zahnrad statt des Symbols, obwohl die
    # .desktop-Datei richtig liegt.
    app.setDesktopFileName("wolkenernte")

    if archiv is None or not archiv.is_dir():
        archiv = archiv_erfragen(app)
        if archiv is None:
            return 1
        from ..einstellungen import archiv_merken
        archiv_merken(archiv)
    app.setApplicationName("WOLKENErnte")
    app.setApplicationDisplayName("WOLKENErnte")
    # **An die Anwendung, nicht ans Fenster.** Dialoge sind eigene
    # Fenster; am Hauptfenster gesetzt, blieben sie im hellen
    # Systemstil und sähen aus wie aus einem anderen Programm.
    app.setStyleSheet(STIL)

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

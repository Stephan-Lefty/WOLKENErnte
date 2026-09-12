"""Einen Google-Takeout im Fenster einlesen – prüfen, holen, aufräumen.

**Warum das im Fenster stehen muss.** Google Fotos ist für fremde
Programme verschlossen; der Takeout ist der *einzige* Weg an den
eigenen Bestand. Solange er nur auf der Kommandozeile ging, war der
wichtigste Anbieter derjenige, für den das Fenster nichts anzubieten
hatte.

Drei Dinge macht dieser Dialog, und die Reihenfolge ist nicht
verhandelbar:

1. **Erst nachsehen, dann anfassen.** Ein ZIP führt zu jeder Datei
   Größe und CRC-32 in seinem Inhaltsverzeichnis, das Archiv hat
   dieselben Angaben in seiner Datenbank. Am echten Export gemessen:
   neun Gigabyte, fünf Teilarchive, Antwort in **0,2 Sekunden** – 5.910
   der 5.939 Bilder lagen schon da, 29 waren neu. Niemand soll einen
   Lauf starten müssen, dessen Ergebnis er nicht vorher kennt.

2. **Holen, erfassen, prüfen** – alle drei, nicht nur das Holen. Orte,
   Titel und Albumzugehörigkeiten stehen **ausschließlich** in den
   JSON-Dateien des Takeouts. Wer holt und die ZIPs dann wegwirft, hat
   die Bilder und sonst nichts.

3. **Und erst danach darf gelöscht werden.** Vier Bedingungen, alle
   vier müssen gelten – dieselbe Strenge wie beim Aufräumen in der
   Wolke, weil es denselben Weg ohne Rückfahrt ist.

**Ausgewählt werden Exporte, nicht einzelne Teildateien.** Das ist
Absicht und die wichtigste Entscheidung hier: Google zerlegt den Export
ohne Rücksicht auf Zusammengehöriges – ein Bild liegt in ``-001.zip``,
seine Metadaten in ``-002.zip``. Wer drei von fünf Teilen anhakt,
verliert an jeder Nahtstelle Datum und Ort und merkt es nicht, weil die
Bilder ja da sind. Die Teile stehen darum unter ihrem Export, sichtbar,
aber nicht einzeln abwählbar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..bestandsliste import umfang
from ..farben import GRAU_MITTE, ROT_HELL
from ..takeout import Archiv as Takeout
from ..takeout import TakeoutFehler, exporte_im_ordner
from ..vorpruefung import in_worten, voransehen


def _einblenden(teil, name: str) -> None:
    teil.setAccessibleName(name)
    teil.setToolTip(name)


class TakeoutWaehlen(QDialog):
    """Ordner aussuchen, Exporte anhaken, Vorschau lesen, losschicken."""

    def __init__(self, archiv: Path, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.archiv = archiv
        self.ausgewaehlt: list[Path] = []
        self.loeschen_gewuenscht = False

        self.setWindowTitle("Google-Takeout einlesen")
        self.setMinimumSize(680, 520)

        self.ordner = Path.home() / "Downloads"

        self.ordnerzeile = QLabel()
        self.ordnerzeile.setWordWrap(True)
        durchsuchen = QPushButton("Ordner wählen …")
        durchsuchen.clicked.connect(self._ordner_waehlen)
        oben = QHBoxLayout()
        oben.addWidget(self.ordnerzeile, 1)
        oben.addWidget(durchsuchen)

        self.baum = QTreeWidget()
        self.baum.setHeaderLabels(["Export", "Teile", "Größe"])
        self.baum.setColumnWidth(0, 380)
        self.baum.itemChanged.connect(self._angehakt)
        _einblenden(self.baum, "Gefundene Takeout-Exporte")

        self.vorschau = QLabel()
        self.vorschau.setWordWrap(True)
        self.vorschau.setStyleSheet(
            f"padding: .6em; border-left: 3px solid {GRAU_MITTE};")

        self.loeschen = QCheckBox(
            "Die ZIP-Dateien nach dem Einlesen löschen")
        self.loeschen.setToolTip(
            "Gelöscht wird erst, wenn jedes einzelne Bild im Archiv "
            "nachgewiesen ist – und Sie es dann noch einmal bestätigen.")

        self.knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.knoepfe.button(
            QDialogButtonBox.StandardButton.Ok).setText("Einlesen")
        self.knoepfe.accepted.connect(self._weiter)
        self.knoepfe.rejected.connect(self.reject)

        aufbau = QVBoxLayout(self)
        aufbau.addLayout(oben)
        aufbau.addWidget(self.baum, 1)
        aufbau.addWidget(self.vorschau)
        aufbau.addWidget(self.loeschen)
        aufbau.addWidget(self.knoepfe)

        self._ordner_lesen()

    # -- Ordner und Baum ---------------------------------------------------

    def _ordner_waehlen(self) -> None:
        gewaehlt = QFileDialog.getExistingDirectory(
            self, "Ordner mit den Takeout-Dateien", str(self.ordner))
        if gewaehlt:
            self.ordner = Path(gewaehlt)
            self._ordner_lesen()

    def _ordner_lesen(self) -> None:
        """Die ZIPs des Ordners nach Export gruppiert anzeigen.

        **Nicht alle ZIPs als einen Export.** Im Download-Ordner liegt
        neben dem Takeout auch anderes – beim Entwickler ein
        Faktura-Programm und ein Spielstand. Alle zusammen zu lesen
        ergäbe eine Zählung, die niemand nachvollziehen kann.
        """
        self.ordnerzeile.setText(f"<b>Ordner:</b> {self.ordner}")
        self.baum.clear()
        try:
            gruppen = exporte_im_ordner(self.ordner)
        except TakeoutFehler as fehler:
            self.vorschau.setText(str(fehler))
            return

        if not gruppen:
            self.vorschau.setText(
                "In diesem Ordner liegt keine ZIP-Datei. "
                "Google legt den Takeout als »takeout-…-001.zip« ab.")
            self._knopf_setzen(False)
            return

        for stamm, teile in gruppen.items():
            zeile = QTreeWidgetItem(self.baum, [
                stamm,
                str(len(teile)),
                umfang(sum(p.stat().st_size for p in teile)),
            ])
            zeile.setData(0, Qt.ItemDataRole.UserRole, teile)
            zeile.setFlags(zeile.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            zeile.setCheckState(0, Qt.CheckState.Unchecked)
            # Die Teile darunter: sichtbar, damit man sieht, was
            # mitkommt - aber nicht einzeln abwählbar. Wer drei von
            # fünf Teilen nimmt, verliert die Metadaten an den
            # Nahtstellen und merkt es nicht.
            for teil in teile:
                QTreeWidgetItem(zeile, [teil.name, "",
                                        umfang(teil.stat().st_size)])
            zeile.setExpanded(len(gruppen) == 1)

        self.vorschau.setText(
            f"{len(gruppen)} Export(e) gefunden. Haken Sie an, was "
            f"eingelesen werden soll.")
        self._knopf_setzen(False)

    def _knopf_setzen(self, an: bool) -> None:
        self.knoepfe.button(
            QDialogButtonBox.StandardButton.Ok).setEnabled(an)

    # -- Vorschau ----------------------------------------------------------

    def _angehakt(self, zeile: QTreeWidgetItem, spalte: int) -> None:
        if spalte != 0 or zeile.parent() is not None:
            return
        self._vorschau_auffrischen()

    def _teile_der_auswahl(self) -> list[Path]:
        teile: list[Path] = []
        for nummer in range(self.baum.topLevelItemCount()):
            zeile = self.baum.topLevelItem(nummer)
            if zeile.checkState(0) == Qt.CheckState.Checked:
                teile.extend(zeile.data(0, Qt.ItemDataRole.UserRole))
        return teile

    def _vorschau_auffrischen(self) -> None:
        """Die Vorschau rechnen – sie ist schnell genug für sofort.

        Gemessen an neun Gigabyte in fünf Teilarchiven: 0,2 Sekunden.
        Deshalb kein Faden und kein Fortschrittsbalken; beides wäre
        hier mehr Gerüst als Nutzen.
        """
        teile = self._teile_der_auswahl()
        if not teile:
            self.vorschau.setText("Nichts angehakt.")
            self._knopf_setzen(False)
            return

        try:
            with Takeout(teile) as quelle:
                ergebnis = voransehen(self.archiv, quelle)
        except TakeoutFehler as fehler:
            self.vorschau.setText(f"<span style='color:{ROT_HELL}'>"
                                  f"{fehler}</span>")
            self._knopf_setzen(False)
            return

        self.vorschau.setText("<br>".join(
            f"• {zeile}" for zeile in in_worten(ergebnis)))
        self._knopf_setzen(True)
        self.knoepfe.button(QDialogButtonBox.StandardButton.Ok).setText(
            f"{ergebnis.neu:n} holen" if ergebnis.neu else "Einlesen")

    # -- Abschicken --------------------------------------------------------

    def _weiter(self) -> None:
        self.ausgewaehlt = self._teile_der_auswahl()
        self.loeschen_gewuenscht = self.loeschen.isChecked()
        if not self.ausgewaehlt:
            return
        self.accept()


class TakeoutArbeit(QObject):
    """Holen, erfassen, prüfen – und nichts davon im Fensterfaden.

    Die drei Schritte laufen als einer durch, weil sie zusammengehören:
    Zwischen Holen und Erfassen abzubrechen hinterlässt Bilder ohne
    ihre Orte und Alben, und niemand sieht, dass etwas fehlt.
    """

    schritt = Signal(str, int, int)
    fertig = Signal(object)
    misslungen = Signal(str)

    def __init__(self, archiv: Path, teile: list[Path]) -> None:
        super().__init__()
        self.archiv = archiv
        self.teile = teile
        self.abbrechen = False

    def laufen(self) -> None:
        from ..erfassung import erfassen
        from ..ernten import ernten
        from ..nachweis import archiv_kennungen, nachweis_fuehren

        try:
            # **Der erste Teil genügt als Angabe** – `aus_datei` holt
            # die Geschwister selbst dazu, und `ernten` geht denselben
            # Weg wie auf der Kommandozeile.
            erstes = self.teile[0]

            self.schritt.emit("Bilder holen", 0, 0)
            bilanz = ernten(self.archiv, [erstes])
            if self.abbrechen:
                self.misslungen.emit("Abgebrochen – nichts gelöscht.")
                return

            self.schritt.emit("Orte, Titel und Alben erfassen", 0, 0)
            erfassen(self.archiv, [erstes])

            # Der Nachweis rechnet die Prüfsummen des Archivs **für
            # diesen Lauf**, nicht aus der Datenbank. Die Vorschau
            # durfte der Datenbank glauben, weil sie nur eine Zahl
            # anzeigt; hier hängt ein Löschen daran.
            self.schritt.emit("Nachweisen, dass alles angekommen ist", 0, 0)
            vorhanden = archiv_kennungen(
                self.archiv,
                lambda n, g: self.schritt.emit("Archiv durchsehen", n, g))
            with Takeout(self.teile) as quelle:
                nachweis = nachweis_fuehren(self.archiv, quelle, erstes.name,
                                            vorhanden=vorhanden)
        except Exception as fehler:  # noqa: BLE001
            self.misslungen.emit(str(fehler))
            return

        self.fertig.emit((bilanz, nachweis))


class TakeoutLauf(QDialog):
    """Der Fortschritt der drei Schritte."""

    def __init__(self, archiv: Path, teile: list[Path],
                 eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Google-Takeout einlesen")
        self.setMinimumWidth(580)
        self.ergebnis = None

        self.was = QLabel(f"{len(teile)} Teilarchiv(e)\nnach {archiv}")
        self.was.setWordWrap(True)
        self.phase = QLabel("Wird vorbereitet …")
        self.balken = QProgressBar()
        self.balken.setRange(0, 0)
        self.zeile = QLabel("")
        self.zeile.setStyleSheet(f"color: {GRAU_MITTE};")

        self.knopf = QPushButton("Abbrechen")
        self.knopf.clicked.connect(self._abbrechen)
        unten = QHBoxLayout()
        unten.addStretch(1)
        unten.addWidget(self.knopf)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.was)
        aufbau.addWidget(self.phase)
        aufbau.addWidget(self.balken)
        aufbau.addWidget(self.zeile)
        aufbau.addLayout(unten)

        self.faden = QThread(self)
        self.arbeit = TakeoutArbeit(archiv, teile)
        self.arbeit.moveToThread(self.faden)
        self.faden.started.connect(self.arbeit.laufen)
        self.arbeit.schritt.connect(self._schritt)
        self.arbeit.fertig.connect(self._fertig)
        self.arbeit.misslungen.connect(self._misslungen)
        self.faden.start()

    def _schritt(self, was: str, nummer: int, gesamt: int) -> None:
        self.phase.setText(was)
        if gesamt:
            if self.balken.maximum() != gesamt:
                self.balken.setRange(0, gesamt)
            self.balken.setValue(nummer)
            self.zeile.setText(f"{nummer:n} von {gesamt:n}")
        else:
            self.balken.setRange(0, 0)
            self.zeile.setText("")

    def _abbrechen(self) -> None:
        self.arbeit.abbrechen = True
        self.knopf.setEnabled(False)
        self.phase.setText("Wird angehalten …")

    def _fertig(self, ergebnis) -> None:
        self.ergebnis = ergebnis
        self._aufraeumen()
        self.accept()

    def _misslungen(self, text: str) -> None:
        self._aufraeumen()
        QMessageBox.warning(self, "WOLKENErnte", text)
        self.reject()

    def _aufraeumen(self) -> None:
        self.faden.quit()
        self.faden.wait(10000)

    def closeEvent(self, ereignis) -> None:  # noqa: N802
        self.arbeit.abbrechen = True
        self._aufraeumen()
        super().closeEvent(ereignis)

"""Die Sicherung im Fenster – ein Menüpunkt, sonst nichts.

**Optional heißt hier wirklich optional.** Kein Vorschlag beim Start,
keine Erinnerung nach dem Ernten, kein Hinweis im Hauptfenster. Wer
diesen Menüpunkt nicht anklickt, merkt nicht, dass es ihn gibt.

Der Dialog macht drei Dinge, und alle drei vor dem Kopieren: Er sagt,
wie viel zu tun wäre, ob der Platz reicht, und ob Ziel und Archiv auf
derselben Platte liegen. Das Letzte wird **nicht verboten** – eine
Kopie an der falschen Stelle ist besser als gar keine –, aber es wird
gesagt.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..einstellungen import letzte_sicherung, sicherung_merken
from ..farben import GRAU_MITTE, ROT_HELL
from ..sicherung import (
    SicherungFehler,
    in_worten,
    nachpruefen,
    sichern,
    voransehen,
)


class SicherungWaehlen(QDialog):
    """Ziel aussuchen, Vorschau lesen, sichern."""

    def __init__(self, archiv: Path, eltern: QWidget | None = None, *,
                 ziel: Path | None = None) -> None:
        super().__init__(eltern)
        self.archiv = archiv
        self.gewaehlt: Path | None = None

        self.setWindowTitle("Archiv sichern")
        self.setMinimumWidth(640)

        # ``ziel`` gibt es für die Tests – sonst läse der Aufbau den
        # gemerkten Ordner des Anwenders und durchsuchte ihn.
        self.ziel = ziel or letzte_sicherung()

        self.pfadfeld = QLineEdit(str(self.ziel) if self.ziel else "")
        self.pfadfeld.setPlaceholderText(
            "Ordner für die Sicherung – am besten auf einer anderen Platte")
        self.pfadfeld.setAccessibleName("Ordner für die Sicherung")
        self.pfadfeld.editingFinished.connect(self._vorschau_auffrischen)

        waehlen = QPushButton("Ordner …")
        waehlen.clicked.connect(self._ordner_waehlen)

        oben = QHBoxLayout()
        oben.addWidget(QLabel("Sicherung nach:"))
        oben.addWidget(self.pfadfeld, 1)
        oben.addWidget(waehlen)

        self.was = QLabel(f"<b>Archiv:</b> {archiv}")
        self.was.setWordWrap(True)
        self.was.setStyleSheet(f"color: {GRAU_MITTE};")

        self.vorschau = QLabel("Bitte einen Ordner wählen.")
        self.vorschau.setWordWrap(True)
        self.vorschau.setStyleSheet(
            f"padding: .6em; border-left: 3px solid {GRAU_MITTE};")

        self.knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.knoepfe.button(
            QDialogButtonBox.StandardButton.Ok).setText("Sichern")
        self.knoepfe.button(
            QDialogButtonBox.StandardButton.Cancel).setText("Schließen")
        self.knoepfe.accepted.connect(self._weiter)
        self.knoepfe.rejected.connect(self.reject)

        aufbau = QVBoxLayout(self)
        aufbau.addLayout(oben)
        aufbau.addWidget(self.was)
        aufbau.addWidget(self.vorschau)
        aufbau.addWidget(self.knoepfe)

        self._vorschau_auffrischen()

    def _ordner_waehlen(self) -> None:
        anfang = str(self.ziel) if self.ziel else str(Path.home())
        gewaehlt = QFileDialog.getExistingDirectory(
            self, "Ordner für die Sicherung", anfang)
        if gewaehlt:
            self.pfadfeld.setText(gewaehlt)
            self._vorschau_auffrischen()

    def _knopf(self, an: bool) -> None:
        self.knoepfe.button(
            QDialogButtonBox.StandardButton.Ok).setEnabled(an)

    def _vorschau_auffrischen(self) -> None:
        text = self.pfadfeld.text().strip()
        if not text:
            self.vorschau.setText("Bitte einen Ordner wählen.")
            self._knopf(False)
            return

        self.ziel = Path(text).expanduser()
        try:
            ergebnis = voransehen(self.archiv, self.ziel)
        except SicherungFehler as fehler:
            self.vorschau.setText(
                f"<span style='color:{ROT_HELL}'>"
                f"{str(fehler).replace(chr(10), '<br>')}</span>")
            self._knopf(False)
            return

        zeilen = [z.replace("**", "") for z in in_worten(ergebnis)]
        self.vorschau.setText("<br>".join(f"• {z}" for z in zeilen))
        self._knopf(ergebnis.reicht_der_platz)

    def _weiter(self) -> None:
        if self.ziel is None:
            return
        self.gewaehlt = self.ziel
        sicherung_merken(self.ziel)
        self.accept()


class SicherungArbeit(QObject):
    """Kopieren und nachprüfen, außerhalb des Fensterfadens."""

    schritt = Signal(int, int, str)
    fertig = Signal(object, object)
    misslungen = Signal(str)

    def __init__(self, archiv: Path, ziel: Path) -> None:
        super().__init__()
        self.archiv = archiv
        self.ziel = ziel
        self.abbrechen = False

    def laufen(self) -> None:
        try:
            bilanz = sichern(
                self.archiv, self.ziel,
                melden=lambda n, g, name: self.schritt.emit(n, g, name),
                abbrechen=lambda: self.abbrechen)
            # **Nach dem Kopieren nachsehen.** Dass alle Dateien da
            # sind, merkt man später auch; dass ihre Zeitstempel fehlen,
            # erst, wenn man die Sicherung braucht.
            abweichungen = [] if bilanz.abgebrochen else nachpruefen(
                self.archiv, self.ziel)
        except Exception as fehler:      # noqa: BLE001
            self.misslungen.emit(str(fehler))
            return
        self.fertig.emit(bilanz, abweichungen)


class SicherungLauf(QDialog):
    """Der Fortschritt beim Kopieren."""

    def __init__(self, archiv: Path, ziel: Path,
                 eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Archiv sichern")
        self.setMinimumWidth(580)
        self.ergebnis = None

        self.was = QLabel(f"nach {ziel}")
        self.was.setWordWrap(True)
        self.balken = QProgressBar()
        self.balken.setRange(0, 0)
        self.zeile = QLabel("Wird durchgesehen …")
        self.zeile.setStyleSheet(f"color: {GRAU_MITTE};")

        self.knopf = QPushButton("Abbrechen")
        self.knopf.clicked.connect(self._abbrechen)
        unten = QHBoxLayout()
        unten.addStretch(1)
        unten.addWidget(self.knopf)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.was)
        aufbau.addWidget(self.balken)
        aufbau.addWidget(self.zeile)
        aufbau.addLayout(unten)

        self.faden = QThread(self)
        self.arbeit = SicherungArbeit(archiv, ziel)
        self.arbeit.moveToThread(self.faden)
        self.faden.started.connect(self.arbeit.laufen)
        self.arbeit.schritt.connect(self._schritt)
        self.arbeit.fertig.connect(self._fertig)
        self.arbeit.misslungen.connect(self._misslungen)
        self.faden.start()

    def _schritt(self, nummer: int, gesamt: int, name: str) -> None:
        if self.balken.maximum() != gesamt:
            self.balken.setRange(0, gesamt)
        self.balken.setValue(nummer)
        self.zeile.setText(f"{nummer:n} von {gesamt:n}   ·   {name[-52:]}")

    def _abbrechen(self) -> None:
        """**Zwischen zwei Dateien**, nie mitten in einer – sonst läge
        im Ziel eine halbe."""
        self.arbeit.abbrechen = True
        self.knopf.setEnabled(False)
        self.zeile.setText(
            "Wird angehalten – die laufende Datei noch zu Ende.")

    def _fertig(self, bilanz, abweichungen) -> None:
        self.ergebnis = (bilanz, abweichungen)
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
        """Nicht verschwinden, solange kopiert wird – derselbe Grund wie
        beim Takeout-Lauf: Der Faden gehört diesem Fenster."""
        if self.faden.isRunning():
            self._abbrechen()
            ereignis.ignore()
            return
        self._aufraeumen()
        super().closeEvent(ereignis)

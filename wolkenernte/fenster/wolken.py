"""Wolkenzugänge im Fenster: anmelden, durchsehen, holen.

**Das ist der Teil, für den es das Programm gibt.** Bis hierher ging
das alles nur auf der Kommandozeile – und ein Programm, das man erst
im Terminal einrichten muss, hat den Zweck verfehlt.

Drei Schritte, drei Dialoge:

1. :class:`ZugangAnlegen` – Adresse, Benutzer, App-Passwort. Die
   Verbindung wird **sofort erprobt**; ohne einen sichtbaren Beweis,
   dass sie steht, wird nichts gespeichert.
2. :class:`WolkeDurchsehen` – der Ordnerbaum der Wolke, mit der Zahl
   der Bilder darin. Erst hier entscheidet der Anwender, was er
   überhaupt holen will.
3. :class:`Ernter` – der Lauf selbst, im Hintergrund, mit Fortschritt
   und Abbruch.

**Was hier nicht steht, ist das Löschen.** Das gehört in
:mod:`wolkenernte.aufraeumen` und braucht einen eigenen Weg, weil es
sich nicht rückgängig machen lässt.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..anbieter import NACH_KENNUNG
from ..farben import BLAU, GRAU_HELL, GRAU_MITTE
from ..lokal import MEDIEN

#: Wie viele Einträge ein Ordner haben darf, bevor gewarnt wird.
#:
#: Nicht technisch begründet, sondern menschlich: Wer versehentlich die
#: Wurzel seiner Wolke erwischt, soll das merken, bevor Stunden
#: Leitung durchlaufen.
VIEL = 5000


def _ist_medium(name: str) -> bool:
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


# ---------------------------------------------------------------------------
# Schritt 1: anmelden


class ZugangAnlegen(QDialog):
    """Eine Nextcloud anmelden – Adresse, Benutzer, App-Passwort.

    **Es wird erst gespeichert, wenn die Verbindung nachweislich
    steht.** Ein Zugang, der nur auf dem Papier existiert, führt sonst
    später zu einer Fehlermeldung an einer Stelle, wo niemand mehr an
    die Anmeldung denkt.
    """

    def __init__(self, dienst, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.dienst = dienst
        self.angelegt: str | None = None

        self.setWindowTitle("Nextcloud anmelden")
        self.setMinimumWidth(520)

        self.name = QLineEdit("meinewolke")
        self.adresse = QLineEdit()
        self.adresse.setPlaceholderText("https://wolke.example")
        self.benutzer = QLineEdit()
        self.kennwort = QLineEdit()
        self.kennwort.setEchoMode(QLineEdit.EchoMode.Password)
        self.kennwort.setPlaceholderText("App-Passwort")

        felder = QFormLayout()
        felder.addRow("Name für diesen Zugang", self.name)
        felder.addRow("Adresse", self.adresse)
        felder.addRow("Benutzername", self.benutzer)
        felder.addRow("App-Passwort", self.kennwort)

        # Der wichtigste Satz des ganzen Dialogs. Bei eingeschalteter
        # Zwei-Faktor-Anmeldung nimmt Nextcloud das Kontokennwort über
        # WebDAV gar nicht an - und wer das nicht weiß, probiert es
        # dreimal und hält das Programm für kaputt.
        hinweis = QLabel(
            "<b>Bitte ein App-Passwort verwenden, nicht das Kontokennwort.</b>"
            "<br>In Nextcloud unter <i>Einstellungen → Sicherheit → "
            "App-Passwort erstellen</i>."
            "<br>Bei Zwei-Faktor-Anmeldung nimmt Nextcloud das "
            "Kontokennwort über WebDAV ohnehin nicht an – und ein "
            "App-Passwort lässt sich einzeln zurückziehen, ohne alles "
            "andere zu ändern.")
        hinweis.setWordWrap(True)
        hinweis.setStyleSheet(f"color: {GRAU_MITTE}; padding: .5rem 0;")

        self.meldung = QLabel()
        self.meldung.setWordWrap(True)

        self.knoepfe = QDialogButtonBox()
        self.pruefen = self.knoepfe.addButton(
            "Verbinden und prüfen", QDialogButtonBox.ButtonRole.AcceptRole)
        # **»Cancel« von Hand übersetzen.** Qt beschriftet seine
        # Standardknöpfe englisch, solange keine deutschen
        # Qt-Übersetzungen installiert sind - und ein englisches Wort
        # mitten im deutschen Dialog sieht nach Halbfertigem aus.
        self.knoepfe.addButton("Abbrechen",
                               QDialogButtonBox.ButtonRole.RejectRole)
        self.pruefen.clicked.connect(self._pruefen)
        self.knoepfe.rejected.connect(self.reject)

        aufbau = QVBoxLayout(self)
        aufbau.addLayout(felder)
        aufbau.addWidget(hinweis)
        aufbau.addWidget(self.meldung)
        aufbau.addWidget(self.knoepfe)

    def _pruefen(self) -> None:
        from ..einrichten import nextcloud
        from ..rclone import RcloneFehler

        name = self.name.text().strip()
        adresse = self.adresse.text().strip()
        benutzer = self.benutzer.text().strip()
        kennwort = self.kennwort.text()

        fehlt = [was for was, wert in (
            ("ein Name", name), ("die Adresse", adresse),
            ("der Benutzername", benutzer), ("das App-Passwort", kennwort),
        ) if not wert]
        if fehlt:
            self._sagen(f"Es fehlt noch {' und '.join(fehlt)}.", schlecht=True)
            return

        self.pruefen.setEnabled(False)
        self._sagen("Verbindung wird erprobt …")
        try:
            nextcloud(self.dienst, name, adresse, benutzer, kennwort)
            self.dienst.auflisten(f"{name}:", nur_dateien=False)
        except RcloneFehler as fehler:
            self._sagen(
                f"Die Verbindung steht nicht.\n\n{fehler}\n\n"
                "Die häufigsten Ursachen: das Kontokennwort statt eines "
                "App-Passworts, oder die Adresse zeigt nicht auf die "
                "Wurzel der Nextcloud.", schlecht=True)
            self.pruefen.setEnabled(True)
            return

        self.angelegt = name
        self.accept()

    def _sagen(self, text: str, *, schlecht: bool = False) -> None:
        farbe = "#e06c75" if schlecht else BLAU
        self.meldung.setStyleSheet(f"color: {farbe}; padding: .5rem 0;")
        self.meldung.setText(text)


# ---------------------------------------------------------------------------
# Schritt 2: durchsehen


class WolkeDurchsehen(QDialog):
    """Der Ordnerbaum einer Wolke, zum Aussuchen.

    **Nachgeladen wird erst beim Aufklappen.** Ein Fotoarchiv hat
    hunderte Ordner; sie alle vorab zu holen hieße, minutenlang vor
    einem leeren Fenster zu sitzen. Und die Zahl der Bilder steht erst
    daneben, wenn jemand hingesehen hat – sie kostet einen eigenen
    Aufruf je Ordner.
    """

    def __init__(self, dienst, zugang: str, eltern: QWidget | None = None
                 ) -> None:
        super().__init__(eltern)
        self.dienst = dienst
        # ``zugang`` ist der Name – darf aber auch schon einen Pfad
        # tragen (``meinewolke:Fotos``). Beides ohne Umstände zu
        # nehmen, spart eine Fehlerquelle: Ein erster Anlauf hängte
        # stur einen Doppelpunkt an und suchte dann nach
        # ``meinewolke:Fotos:``.
        self.mit_unterordnern_gewaehlt = True
        self.zugang, _, self.wurzelpfad = zugang.partition(":")
        # Nur hinten kürzen: Ein führender Schrägstrich gehört bei
        # manchen Backends zum Pfad. Dieselbe Falle wie in wolke.py –
        # dort suchte ein abgeschnittener Schrägstrich nach
        # ``tmp/…`` statt ``/tmp/…``.
        self.wurzelpfad = self.wurzelpfad.rstrip("/")
        self.gewaehlt: str | None = None

        anbieter = NACH_KENNUNG.get(dienst.art(self.zugang))
        wer = anbieter.name if anbieter else "unbekannter Anbieter"
        self.setWindowTitle(f"{self.zugang}: – {wer}")
        self.resize(640, 560)

        self.baum = QTreeWidget()
        self.baum.setHeaderLabels(["Ordner", "Bilder"])
        self.baum.setColumnWidth(0, 420)
        self.baum.itemExpanded.connect(self._aufklappen)
        self.baum.currentItemChanged.connect(self._auswahl_geaendert)

        wurzel = QTreeWidgetItem(
            self.baum, [f"{self.zugang}:{self.wurzelpfad}", ""])
        wurzel.setData(0, Qt.ItemDataRole.UserRole, self.wurzelpfad)
        wurzel.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        self.baum.addTopLevelItem(wurzel)
        wurzel.setExpanded(True)

        self.mit_unterordnern = QCheckBox("Unterordner mitnehmen")
        self.mit_unterordnern.setChecked(True)
        self.mit_unterordnern.setToolTip(
            "Aus: nur die Dateien, die unmittelbar in diesem Ordner "
            "liegen.\nEin: auch alles in den Ordnern darunter.")

        self.meldung = QLabel()
        self.meldung.setWordWrap(True)
        self.meldung.setStyleSheet(f"color: {GRAU_MITTE};")

        self.knoepfe = QDialogButtonBox()
        self.holen = self.knoepfe.addButton(
            "Diesen Ordner holen", QDialogButtonBox.ButtonRole.AcceptRole)
        self.knoepfe.addButton("Abbrechen",
                               QDialogButtonBox.ButtonRole.RejectRole)
        self.holen.clicked.connect(self._holen)
        self.knoepfe.rejected.connect(self.reject)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.baum, 1)
        aufbau.addWidget(self.mit_unterordnern)
        aufbau.addWidget(self.meldung)
        aufbau.addWidget(self.knoepfe)

        self._aufklappen(wurzel)

    # -- Baum --------------------------------------------------------------

    def _aufklappen(self, knoten: QTreeWidgetItem) -> None:
        """Die Unterordner eines Knotens holen – einmal."""
        from ..rclone import RcloneFehler

        if knoten.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        knoten.setData(0, Qt.ItemDataRole.UserRole + 1, True)

        pfad = knoten.data(0, Qt.ItemDataRole.UserRole) or ""
        wo = f"{self.zugang}:{pfad}"
        try:
            eintraege = self.dienst.auflisten(wo, nur_dateien=False)
        except RcloneFehler as fehler:
            self.meldung.setText(f"{wo} ließ sich nicht lesen: {fehler}")
            return

        bilder = sum(1 for e in eintraege
                     if not e.get("IsDir") and _ist_medium(e.get("Name") or ""))
        knoten.setText(1, str(bilder) if bilder else "")

        for eintrag in sorted(eintraege, key=lambda e: (e.get("Name") or "").lower()):
            if not eintrag.get("IsDir"):
                continue
            name = eintrag.get("Name") or ""
            kind = QTreeWidgetItem(knoten, [name, ""])
            kind.setData(0, Qt.ItemDataRole.UserRole,
                         f"{pfad}/{name}" if pfad else name)
            # Ohne diesen Pfeil sähe jeder Ordner leer aus, bis ihn
            # jemand doppelt anklickt - und niemand klickt auf etwas,
            # das erkennbar nichts enthält.
            kind.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

    def _auswahl_geaendert(self, jetzt, _vorher=None) -> None:
        if jetzt is None:
            return
        pfad = jetzt.data(0, Qt.ItemDataRole.UserRole) or ""
        ziel = f"{self.zugang}:{pfad}" if pfad else f"{self.zugang}:"
        self.meldung.setText(f"Holen aus  {ziel}")

    # -- Entscheidung ------------------------------------------------------

    def _holen(self) -> None:
        knoten = self.baum.currentItem()
        if knoten is None:
            self.meldung.setText("Erst einen Ordner auswählen.")
            return
        pfad = knoten.data(0, Qt.ItemDataRole.UserRole) or ""

        if self.mit_unterordnern.isChecked() and not pfad:
            antwort = QMessageBox.question(
                self, "WOLKENErnte",
                f"Die ganze Cloud »{self.zugang}:« mit allen Unterordnern?\n\n"
                "Das kann sehr lange dauern und viel Platz brauchen. "
                "Meistens ist ein einzelner Fotoordner gemeint.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if antwort != QMessageBox.StandardButton.Yes:
                return

        self.gewaehlt = f"{self.zugang}:{pfad}" if pfad else f"{self.zugang}:"
        self.mit_unterordnern_gewaehlt = self.mit_unterordnern.isChecked()
        self.accept()


# ---------------------------------------------------------------------------
# Schritt 3: holen


class Arbeit(QObject):
    """Der Erntelauf, außerhalb des Fensterfadens.

    **Qt darf nur aus seinem eigenen Faden bedient werden.** Deshalb
    meldet diese Klasse nichts selbst an, sondern schickt Signale; das
    Fenster hört zu und zeichnet.
    """

    schritt = Signal(int, int, str)
    fertig = Signal(object)
    misslungen = Signal(str)

    def __init__(self, dienst, quelle: str, ziel: Path, *,
                 mit_unterordnern: bool = True) -> None:
        super().__init__()
        self.dienst = dienst
        self.quelle = quelle
        self.ziel = ziel
        self.mit_unterordnern = mit_unterordnern
        self.abbrechen = False

    def laufen(self) -> None:
        from ..archiv import uebernehmen
        from ..ernten import angaben_ermitteln, quelle_oeffnen
        from ..zuordnung import zuordnen

        try:
            quelle, _art = quelle_oeffnen(
                self.quelle, self.dienst,
                mit_unterordnern=self.mit_unterordnern)
        except Exception as fehler:  # noqa: BLE001
            self.misslungen.emit(str(fehler))
            return

        try:
            medien, jsons = [], set()
            for eintrag in quelle:
                name = eintrag.pfad.rsplit("/", 1)[-1]
                if name.lower().endswith(".json"):
                    jsons.add(eintrag.pfad)
                elif _ist_medium(name):
                    medien.append(eintrag.pfad)

            zuordnungen = zuordnen(medien, jsons)
            gesamt = len(zuordnungen)
            if not gesamt:
                self.misslungen.emit(
                    f"In {self.quelle} liegen keine Bilder oder Videos.")
                return

            def melden(nummer: int, name: str) -> None:
                if self.abbrechen:
                    # Kein eigener Abbruchweg in uebernehmen(): Eine
                    # Ausnahme ist hier das ehrlichste Mittel, und sie
                    # lässt kein halb geschriebenes Bild zurück.
                    raise KeyboardInterrupt
                self.schritt.emit(nummer, gesamt, name)

            bilanz = uebernehmen(
                quelle, zuordnungen,
                lambda z: angaben_ermitteln(quelle, z),
                self.ziel, fortschritt=melden,
            )
        except KeyboardInterrupt:
            self.misslungen.emit("Abgebrochen. Was schon geholt wurde, bleibt.")
            return
        except Exception as fehler:  # noqa: BLE001
            self.misslungen.emit(str(fehler))
            return
        finally:
            if hasattr(quelle, "schliessen"):
                quelle.schliessen()

        self.fertig.emit(bilanz)


class Ernter(QDialog):
    """Der Fortschritt beim Holen – und der Abbruch."""

    def __init__(self, dienst, quelle: str, ziel: Path,
                 eltern: QWidget | None = None, *,
                 mit_unterordnern: bool = True) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Aus der Cloud holen")
        self.setMinimumWidth(560)
        self.bilanz = None

        self.was = QLabel(f"Aus {quelle}\nnach {ziel}")
        self.was.setWordWrap(True)
        self.balken = QProgressBar()
        self.balken.setRange(0, 0)      # unbestimmt, bis die Zahl steht
        self.datei = QLabel("Verzeichnis wird gelesen …")
        self.datei.setStyleSheet(f"color: {GRAU_MITTE};")

        self.knopf = QPushButton("Abbrechen")
        self.knopf.clicked.connect(self._abbrechen)
        unten = QHBoxLayout()
        unten.addStretch(1)
        unten.addWidget(self.knopf)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.was)
        aufbau.addWidget(self.balken)
        aufbau.addWidget(self.datei)
        aufbau.addLayout(unten)

        self.faden = QThread(self)
        self.arbeit = Arbeit(dienst, quelle, ziel,
                             mit_unterordnern=mit_unterordnern)
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
        self.datei.setText(f"{nummer} von {gesamt}   ·   {name[-58:]}")

    def _abbrechen(self) -> None:
        self.arbeit.abbrechen = True
        self.knopf.setEnabled(False)
        self.datei.setText("Wird angehalten – die laufende Datei noch zu Ende …")

    def _fertig(self, bilanz) -> None:
        self.bilanz = bilanz
        self._aufraeumen()
        self.accept()

    def _misslungen(self, text: str) -> None:
        self._aufraeumen()
        QMessageBox.warning(self, "WOLKENErnte", text)
        self.reject()

    def _aufraeumen(self) -> None:
        self.faden.quit()
        self.faden.wait(5000)

    def closeEvent(self, ereignis) -> None:  # noqa: N802
        """Nicht mitten im Schreiben verschwinden.

        Das Fenster zu schließen heißt hier: abbrechen und warten.
        Sonst schriebe ein herrenloser Faden weiter in ein Archiv,
        das niemand mehr beobachtet.
        """
        self.arbeit.abbrechen = True
        self._aufraeumen()
        super().closeEvent(ereignis)

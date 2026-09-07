"""In einer Wolke anmelden – für jeden Anbieter, nicht nur Nextcloud.

Das Programm hieß von Anfang an »aus **allen** Cloudspeichern«, aber
anmelden ließ sich im Fenster nur eine Nextcloud; für alles andere
musste man ins Terminal. Das ist hier behoben.

**Die Anbietertabelle entscheidet, was angeboten wird.** Wo
:mod:`wolkenernte.anbieter` sagt, dass ein Zugang gar nicht möglich ist
– Google Fotos, iCloud Fotos –, steht der Grund im Dialog, statt dass
jemand einen Eintrag sucht, den es nie gab. Und die Fähigkeiten stehen
daneben, **bevor** sich jemand darauf verlässt: sehen, holen, löschen.

**Die Rückfragen kommen von rclone, nicht von uns.** Jeder Anbieter
will etwas anderes wissen – Dropbox eine Browser-Anmeldung, pCloud die
Regionsangabe, Proton ein Zwei-Faktor-Kennwort. :func:`Frageblatt`
zeigt, wonach gerade gefragt wird, samt rclones eigenem Hilfetext. So
gibt es nichts, was wir je Anbieter nachpflegen müssten.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..anbieter import ANBIETER, Anbieter, Weg
from ..einrichten import Abbruch, Frage, einrichten
from ..farben import GRAU_MITTE, GRUEN_HELL, ROT_HELL


def _fähigkeiten(anbieter: Anbieter) -> str:
    kann = [was for was, ja in (("sehen", anbieter.auflisten),
                                ("holen", anbieter.laden),
                                ("löschen", anbieter.loeschen)) if ja]
    return ", ".join(kann) if kann else "nichts davon"


class AnbieterWaehlen(QDialog):
    """Bei wem soll angemeldet werden?

    **Auch die, bei denen es nicht geht, stehen in der Liste** – mit
    dem Grund daneben. Wer Google Fotos sucht und es nirgends findet,
    hält das Programm für unfertig; wer liest, dass Google seit 2019
    keine Schnittstelle mehr dafür anbietet, weiß Bescheid.
    """

    def __init__(self, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.gewaehlt: Anbieter | None = None

        self.setWindowTitle("Bei einer Cloud anmelden")
        self.resize(640, 560)

        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        for anbieter in ANBIETER:
            eintrag = QListWidgetItem(
                f"{anbieter.name}\n     kann: {_fähigkeiten(anbieter)}")
            eintrag.setData(Qt.ItemDataRole.UserRole, anbieter)
            if anbieter.weg is not Weg.RCLONE:
                eintrag.setFlags(Qt.ItemFlag.NoItemFlags)
                # **Den Hinweis nicht kürzen.** Ein erster Anlauf schnitt
                # am ersten Punkt ab und machte aus »Seit dem 31. März
                # 2019 …« ein »Seit dem 31.«. Der ganze Text steht
                # ohnehin unter der Liste, sobald jemand hinsieht.
                eintrag.setText(
                    f"{anbieter.name}  – hier nicht anmeldbar\n"
                    f"     kein Zugang möglich, Grund siehe unten")
            self.liste.addItem(eintrag)
        self.liste.currentItemChanged.connect(self._gewaehlt)
        self.liste.itemDoubleClicked.connect(lambda _: self._weiter())

        self.hinweis = QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setMinimumHeight(90)
        self.hinweis.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.hinweis.setStyleSheet(f"color: {GRAU_MITTE};")

        self.knoepfe = QDialogButtonBox()
        self.weiter = self.knoepfe.addButton(
            "Weiter", QDialogButtonBox.ButtonRole.AcceptRole)
        self.weiter.setEnabled(False)
        self.knoepfe.addButton("Abbrechen",
                               QDialogButtonBox.ButtonRole.RejectRole)
        self.weiter.clicked.connect(self._weiter)
        self.knoepfe.rejected.connect(self.reject)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(QLabel("Bei welchem Anbieter liegen die Bilder?"))
        aufbau.addWidget(self.liste, 1)
        aufbau.addWidget(self.hinweis)
        aufbau.addWidget(self.knoepfe)

    def _gewaehlt(self, jetzt, _vorher=None) -> None:
        if jetzt is None:
            return
        anbieter = jetzt.data(Qt.ItemDataRole.UserRole)
        if anbieter is None:
            return
        moeglich = anbieter.weg is Weg.RCLONE
        self.weiter.setEnabled(moeglich)
        farbe = GRUEN_HELL if anbieter.vollstaendig else ROT_HELL
        erprobt = ("erprobt" if anbieter.erprobt
                   else "eingebaut, aber hier noch nicht erprobt")
        self.hinweis.setText(
            f"<b style='color:{farbe}'>{anbieter.name}</b> – "
            f"kann {_fähigkeiten(anbieter)} · {erprobt}<br>{anbieter.hinweis}")

    def _weiter(self) -> None:
        eintrag = self.liste.currentItem()
        if eintrag is None:
            return
        anbieter = eintrag.data(Qt.ItemDataRole.UserRole)
        if anbieter is None or anbieter.weg is not Weg.RCLONE:
            return
        self.gewaehlt = anbieter
        self.accept()


class Frageblatt(QDialog):
    """Eine einzelne Rückfrage von rclone.

    Die Art der Frage bestimmt das Eingabefeld: eine Liste, wo rclone
    nur bestimmte Werte zulässt, ein Häkchen bei ja/nein, ein
    verdecktes Feld bei Kennwörtern.
    """

    def __init__(self, frage: Frage, anbieter: Anbieter,
                 eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.frage = frage
        self.setWindowTitle(f"{anbieter.name} einrichten")
        self.setMinimumWidth(560)

        aufbau = QVBoxLayout(self)

        if frage.fehler:
            schlecht = QLabel(frage.fehler)
            schlecht.setWordWrap(True)
            schlecht.setStyleSheet(f"color: {ROT_HELL};")
            aufbau.addWidget(schlecht)

        titel = QLabel(f"<b>{frage.name}</b>"
                       + ("  (nötig)" if frage.pflicht else ""))
        aufbau.addWidget(titel)

        if frage.hilfe:
            # rclones eigener Hilfetext. Ihn zu übersetzen hieße, ihn
            # bei jeder rclone-Fassung nachzupflegen - und falsch zu
            # übersetzen, wo wir den Anbieter gar nicht kennen.
            hilfe = QLabel(frage.hilfe)
            hilfe.setWordWrap(True)
            hilfe.setStyleSheet(f"color: {GRAU_MITTE};")
            aufbau.addWidget(hilfe)

        self.feld = self._feld_bauen(frage)
        aufbau.addWidget(self.feld)

        knoepfe = QDialogButtonBox()
        gut = knoepfe.addButton("Weiter", QDialogButtonBox.ButtonRole.AcceptRole)
        knoepfe.addButton("Abbrechen", QDialogButtonBox.ButtonRole.RejectRole)
        gut.clicked.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

    def _feld_bauen(self, frage: Frage) -> QWidget:
        if frage.art == "bool":
            kasten = QCheckBox("ja")
            kasten.setChecked(frage.vorgabe.lower() in ("true", "1", "yes"))
            return kasten
        if frage.auswahl:
            liste = QComboBox()
            liste.setEditable(not frage.nur_auswahl)
            liste.addItems(frage.auswahl)
            if frage.vorgabe in frage.auswahl:
                liste.setCurrentText(frage.vorgabe)
            return liste
        feld = QLineEdit(frage.vorgabe)
        if frage.geheim:
            feld.setEchoMode(QLineEdit.EchoMode.Password)
            feld.setText("")
        return feld

    def antwort(self) -> str:
        if isinstance(self.feld, QCheckBox):
            return "true" if self.feld.isChecked() else "false"
        if isinstance(self.feld, QComboBox):
            return self.feld.currentText()
        return self.feld.text()


def anmelden(dienst, eltern: QWidget | None = None) -> str | None:
    """Der ganze Weg: Anbieter wählen, Namen geben, Rückfragen beantworten.

    Gibt den Namen des angelegten Zugangs zurück – oder ``None``, wenn
    abgebrochen wurde oder nichts zustande kam.
    """
    from ..rclone import RcloneFehler

    wahl = AnbieterWaehlen(eltern)
    if not wahl.exec() or wahl.gewaehlt is None:
        return None
    anbieter = wahl.gewaehlt

    # Nextcloud hat ein eigenes Blatt: Adresse, Benutzer und Kennwort
    # auf einmal, statt drei Rückfragen nacheinander - und mit dem
    # Hinweis aufs App-Passwort, den rclone nicht kennt.
    if anbieter.kennung == "nextcloud":
        from .wolken import ZugangAnlegen

        dialog = ZugangAnlegen(dienst, eltern)
        return dialog.angelegt if dialog.exec() else None

    vorhandene = {n.rstrip(":") for n in dienst.remotes()}
    name = _namen_finden(anbieter.kennung, vorhandene)

    def fragen(frage: Frage) -> str | None:
        blatt = Frageblatt(frage, anbieter, eltern)
        return blatt.antwort() if blatt.exec() else None

    try:
        einrichten(dienst, name, anbieter.kennung, fragen=fragen)
    except Abbruch:
        # Der halbfertige Eintrag darf nicht stehenbleiben: Er sähe im
        # Menü aus wie ein Zugang und wäre keiner.
        _wegwerfen(dienst, name)
        return None
    except RcloneFehler as fehler:
        _wegwerfen(dienst, name)
        QMessageBox.warning(
            eltern, "WOLKENErnte",
            f"{anbieter.name} ließ sich nicht einrichten.\n\n{fehler}")
        return None

    # **Erst der Beweis, dann der Eintrag** – wie bei Nextcloud.
    try:
        dienst.auflisten(f"{name}:", nur_dateien=False)
    except RcloneFehler as fehler:
        _wegwerfen(dienst, name)
        QMessageBox.warning(
            eltern, "WOLKENErnte",
            f"Der Zugang wurde angelegt, aber {anbieter.name} antwortet "
            f"nicht:\n\n{fehler}\n\nEr wurde wieder entfernt.")
        return None
    return name


def _namen_finden(kennung: str, vorhandene: set[str]) -> str:
    """Einen freien Namen für den Zugang.

    Der Anwender muss sich keinen ausdenken – er sieht ihn ohnehin nur
    im Menü, und zwei gleich benannte Zugänge überschrieben einander.
    """
    if kennung not in vorhandene:
        return kennung
    for nummer in range(2, 100):
        name = f"{kennung}{nummer}"
        if name not in vorhandene:
            return name
    return f"{kennung}-neu"


def _wegwerfen(dienst, name: str) -> None:
    """Einen halbfertigen Zugang wieder entfernen."""
    from ..rclone import RcloneFehler

    try:
        dienst.rufen("config/delete", {"name": name})
    except RcloneFehler:
        pass

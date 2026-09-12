"""Die Hilfe im Fenster – wie man an seine Google-Bilder kommt.

**Warum das eine eigene Seite braucht.** Google Fotos ist für fremde
Programme seit dem 31.03.2025 verschlossen; der Export ist der einzige
Weg an den eigenen Bestand. WOLKENErnte kann ihn einlesen, aber
*anfordern* muss ihn der Anwender selbst – und dieser Teil findet in
einem Browser statt, den dieses Programm nicht steuert und nicht
steuern soll.

**Was hier nicht steht, und aus welchem Grund.** Keine nachgemalten
Klickwege durch Googles Netzseiten: »Auf ›Weiter‹ klicken, dann unten
links auf ›Export erstellen‹« ist genau die Sorte Anleitung, die nach
dem nächsten Umbau der Seite falsch ist – und eine falsche Anleitung
kostet mehr Zeit als keine. Beschrieben wird deshalb das **Ziel** jedes
Schrittes, und verlinkt wird Googles eigene Hilfe, die sich mit der
Seite ändert.

Die Angaben zu Ablauf, Anzahl der Downloads und Teilgrößen stehen mit
Belegen in ``docs/takeout.md``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..farben import BLAU_LEUCHT, GRAU_MITTE

#: Wo man den Export anfordert.
TAKEOUT = "https://takeout.google.com/"

#: Googles eigene Hilfe dazu. **Verlinkt statt nachgeschrieben:** Sie
#: ändert sich mit der Seite, eine abgetippte Anleitung nicht.
GOOGLE_HILFE = "https://support.google.com/accounts/answer/3024190?hl=de"

PROJEKT = "https://github.com/Stephan-Lefty/WOLKENErnte"


TAKEOUT_HILFE = f"""
<h2>Google-Bilder holen – in vier Schritten</h2>

<p><b>Warum überhaupt so umständlich?</b> Google Fotos ist für fremde
Programme seit dem 31.&nbsp;März 2025 verschlossen. Ein Programm sieht dort
nur noch die Bilder, die es selbst hochgeladen hat – Ihre eigene Mediathek
ist unerreichbar, und eine Löschfunktion hat es dort nie gegeben. Der
einzige Weg an Ihre Bilder führt über ein Archiv, das Sie bei Google
selbst anfordern.</p>

<h3>1. Den Export anfordern</h3>
<p>Auf <a href="{TAKEOUT}">takeout.google.com</a> anmelden. Dort wählen Sie
aus, <i>was</i> exportiert werden soll. Drei Dinge sind wichtig:</p>
<ul>
<li><b>Nur „Google Fotos“ auswählen</b>, sonst nichts. Voreingestellt ist
    meist <i>alles</i> – dann kommen Mails, Kalender und Karten mit, das
    Archiv wird ein Vielfaches größer, und Sie warten Tage darauf.</li>
<li><b>Als Dateityp ZIP</b>, nicht TGZ. <b>WOLKENErnte liest nur ZIP</b> –
    ein TGZ-Archiv müssten Sie erst auspacken, und bei hunderten
    Gigabyte heißt das, denselben Bestand zweimal auf der Platte zu
    haben. Ein ZIP führt außerdem ein Inhaltsverzeichnis mit, und nur
    dadurch lässt sich vor dem Einlesen sagen, was dabei herauskommt.</li>
<li><b>Teilgröße 10 GB oder 50 GB.</b> Wählbar sind 1, 2, 4, 10 und 50.
    Kleine Teile bedeuten mehr Dateien zum Herunterladen und mehr
    Gelegenheiten, eine davon zu vergessen – und ein fehlendes Teil
    kostet Aufnahmedaten, nicht nur Bilder.</li>
</ul>
<p>Die genauen Beschriftungen auf der Seite ändert Google regelmäßig.
Der jeweils aktuelle Weg steht in
<a href="{GOOGLE_HILFE}">Googles eigener Hilfe</a>.</p>

<h3>2. Warten</h3>
<p>Google rechnet das Archiv im Hintergrund zusammen und schickt eine
E-Mail, wenn es bereitliegt. Bei einer großen Mediathek dauert das
<b>Stunden bis Tage</b>. Sie müssen nichts offen lassen.</p>

<h3>3. Herunterladen – und zwar <i>alle</i> Teile</h3>
<p>Drei Dinge, die man wissen muss, bevor man anfängt:</p>
<ul>
<li>Das Archiv <b>läuft nach etwa sieben Tagen ab</b>.</li>
<li>Es lässt sich <b>fünfmal</b> herunterladen, danach nicht mehr.</li>
<li><b>Jedes Teil zählt.</b> Google zerlegt den Export ohne Rücksicht
    darauf, was zusammengehört: Ein Bild liegt in <code>…-001.zip</code>,
    seine Aufnahmedaten in <code>…-002.zip</code>. Fehlt ein Teil, sind
    die Bilder der Nachbarteile zwar da, aber ohne Datum und Ort – und
    das fällt nicht auf, weil ja Bilder da sind.</li>
</ul>
<p>Legen Sie alle Teile in <b>denselben Ordner</b>. Wohin, ist
gleichgültig – auf die Platte mit Platz. Neun Gigabyte passen selten
in den Download-Ordner.</p>
<p><b>Auspacken müssen Sie nichts.</b> WOLKENErnte liest die ZIP-Dateien,
wie sie sind. Auspacken hieße, denselben Bestand zweimal auf der Platte
zu haben – ausgerechnet dann, wenn der Platz knapp ist.</p>

<h3>4. In WOLKENErnte einlesen</h3>
<p>Menü <b>Cloudspeicher → Google-Takeout einlesen (ZIP-Dateien)</b>.</p>
<ul>
<li><b>Ordner angeben.</b> Pfad einfügen, „Ordner …“ zum Aussuchen, oder
    „ZIP-Dateien …“ – letzteres zeigt auch angesteckte Platten und
    Netzlaufwerke.</li>
<li><b>Den Export anhaken.</b> Die einzelnen Teile stehen aufklappbar
    darunter; angehakt wird immer der ganze Export. Fremde ZIP-Dateien im
    selben Ordner bleiben getrennt.</li>
<li><b>Die Vorschau lesen.</b> Sie steht sofort da und sagt, wie viele
    Bilder schon im Archiv liegen und wie viele hinzukämen. Der Knopf
    heißt danach zum Beispiel „29 holen“ – Sie wissen vorher, was
    passiert.</li>
</ul>
<p>Der Lauf macht vier Schritte: holen, Orte und Alben erfassen,
nachweisen, Schlagwörter vergeben. Das <b>Erfassen</b> ist keine Kür –
Orte, Titel und Albumzugehörigkeiten stehen ausschließlich in den
Metadatendateien des Exports. Wer die Bilder holt und die ZIP-Dateien
dann wegwirft, hat die Bilder und sonst nichts.</p>

<h3>Und die ZIP-Dateien danach?</h3>
<p>Der Haken „Die ZIP-Dateien nach dem Einlesen löschen“ räumt sie weg –
aber nur, wenn <b>alle vier</b> Bedingungen gelten: Der Lauf ist
durchgelaufen; die Angaben sind erfasst; <b>jedes einzelne</b> Bild ist
im Archiv nachgewiesen, mit Prüfsummen, die für diesen Lauf gerechnet
wurden; und Sie bestätigen es danach noch einmal. Fehlt eine, bleiben die
Dateien liegen.</p>
<p><b>Der Haken ist nicht voreingestellt</b>, und beim ersten Mal würden
wir ihn weglassen. Bedenken Sie außerdem: Danach ist Ihr Archiv die
einzige Kopie dieser Bilder. Die ZIP-Dateien waren nie eine Sicherung –
aber eine Sicherung sollte es geben.</p>

<h3>Aufräumen bei Google</h3>
<p>Das muss von Hand im Browser geschehen. Google Fotos hat für fremde
Programme nie eine Löschfunktion gehabt, und WOLKENErnte steuert keinen
Browser: Das saß auf undokumentierten internen Schnittstellen, bricht
ohne Vorwarnung, und bei Apple verstößt es ausdrücklich gegen die
Nutzungsbedingungen. Ein Knopf, der nichts Verlässliches tut, soll es
hier nicht geben.</p>
"""


UEBER = f"""
<h2>WOLKENErnte {__version__}</h2>
<p>Bilder und Videos aus den Wolken holen – und dort aufräumen.</p>
<p><b>Läuft nur auf diesem Rechner.</b> Es gibt keinen Dienst im Netz,
kein Konto und keine Zählung. Der einzige Netzaufruf, den das Programm
von sich aus an einen fremden Server richtet, ist
<code>wolkenernte neuigkeiten</code> – und der geschieht nur, wenn Sie
ihn verlangen.</p>
<p><b>Ihre Bilder bleiben gewöhnliche Dateien.</b> Kein eigenes Format,
keine Verschlüsselung, kein Verzeichnisdienst. Wer WOLKENErnte in zehn
Jahren nicht mehr hat, öffnet den Ordner mit jedem beliebigen
Programm.</p>
<p>Quelltext, Änderungsprotokoll und Anleitungen:<br>
<a href="{PROJEKT}">{PROJEKT}</a></p>
<p>Lizenz: MIT.</p>
"""


class Hilfeseite(QDialog):
    """Ein Hilfetext, den man lesen und daneben weiterarbeiten kann.

    **Nicht modal.** Eine Anleitung, die das Fenster blockiert, ist beim
    zweiten Schritt schon weggeklickt – und wer sie braucht, braucht sie
    *während* er den Dialog bedient.

    Verweise öffnen den Browser des Systems, nicht einen eingebauten:
    Dieses Programm soll kein Browser werden.
    """

    def __init__(self, titel: str, inhalt: str,
                 eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle(titel)
        self.setMinimumSize(640, 560)
        self.setModal(False)

        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(False)
        self.text.setOpenLinks(False)
        self.text.anchorClicked.connect(QDesktopServices.openUrl)
        self.text.setHtml(inhalt)
        self.text.setStyleSheet(
            f"QTextBrowser {{ border: 0; }} a {{ color: {BLAU_LEUCHT}; }}")
        self.text.setAccessibleName(titel)

        knoepfe = QDialogButtonBox()
        self.oeffnen = QPushButton("takeout.google.com öffnen")
        self.oeffnen.clicked.connect(
            lambda: QDesktopServices.openUrl(TAKEOUT))
        knoepfe.addButton(self.oeffnen, QDialogButtonBox.ButtonRole.ActionRole)
        schliessen = knoepfe.addButton(
            "Schließen", QDialogButtonBox.ButtonRole.AcceptRole)
        schliessen.clicked.connect(self.close)

        aufbau = QVBoxLayout(self)
        aufbau.addWidget(self.text, 1)
        aufbau.addWidget(knoepfe)

    def ohne_takeout_knopf(self) -> Hilfeseite:
        """Den Knopf zu Google weglassen – für »Über WOLKENErnte«."""
        self.oeffnen.setVisible(False)
        return self


def takeout_hilfe(eltern: QWidget | None = None) -> Hilfeseite:
    return Hilfeseite("Google-Bilder holen", TAKEOUT_HILFE, eltern)


def ueber(eltern: QWidget | None = None) -> Hilfeseite:
    return Hilfeseite(f"Über WOLKENErnte {__version__}",
                      UEBER, eltern).ohne_takeout_knopf()

"""Die Hilfe im Fenster.

**Warum eine Anleitung getestet wird.** Nicht die Formulierungen – die
darf jeder ändern. Getestet wird, dass sie **da ist**, dass ihre
Verweise stimmen und dass sie nicht behauptet, was das Programm nicht
kann. Ein Hilfetext, der auf einen Menüpunkt zeigt, den es nicht mehr
gibt, ist schlimmer als keiner: Er kostet erst Zeit und dann Vertrauen.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    QT = True
except ImportError:  # pragma: no cover
    QT = False


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DieTakeoutAnleitung(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from wolkenernte.fenster.hilfe import takeout_hilfe

        self.seite = takeout_hilfe()
        self.text = self.seite.text.toPlainText()

    def test_sie_nennt_den_menueweg_zum_einlesen(self) -> None:
        """**Der Kern der Anleitung.** Wer den Export geladen hat, muss
        wissen, wo er ihn einwirft – und dieser Weg muss zu dem passen,
        was im Menü wirklich steht."""
        self.assertIn("Cloudspeicher", self.text)
        self.assertIn("Google-Takeout einlesen", self.text)

    def test_der_menueweg_stimmt_mit_dem_menue_ueberein(self) -> None:
        """Ein Hilfetext, der auf einen Eintrag zeigt, den es nicht
        gibt, kostet erst Zeit und dann Vertrauen. Dieser Test fällt
        um, wenn jemand den Menüpunkt umbenennt."""
        from wolkenernte.fenster.hauptfenster import Hauptfenster

        tmp = Path(tempfile.mkdtemp())
        (tmp / "2024").mkdir()
        fenster = Hauptfenster(tmp)
        try:
            eintraege = []
            for menue in fenster.menuBar().actions():
                eintraege.append(menue.text().replace("&", ""))
                if menue.menu():
                    eintraege += [a.text() for a in menue.menu().actions()]
        finally:
            fenster.ansicht.aufraeumen()
            fenster.close()

        self.assertIn("Cloudspeicher", eintraege)
        self.assertTrue(
            any("Google-Takeout einlesen" in e for e in eintraege),
            f"Menüeintrag fehlt, gefunden: {eintraege}")

    def test_die_drei_fallen_beim_anfordern_stehen_drin(self) -> None:
        """Nur Fotos, ZIP statt TGZ, große Teile. Wer eines davon
        falsch wählt, wartet Tage auf ein unbrauchbares Archiv."""
        for stichwort in ("Google Fotos", "ZIP", "TGZ", "Teilgröße"):
            with self.subTest(stichwort):
                self.assertIn(stichwort, self.text)

    def test_sie_sagt_dass_nur_zip_geht(self) -> None:
        """**Nicht verharmlosen.** Ein erster Entwurf schrieb, das
        Programm lese »beides nicht gleich gut« – es liest TGZ gar
        nicht. Wer danach TGZ wählt, wartet Tage auf ein Archiv, das
        WOLKENErnte nicht öffnen kann."""
        self.assertIn("liest nur ZIP", self.text)

    def test_die_belegten_zahlen_stehen_drin(self) -> None:
        """Ablauf nach sieben Tagen und fünf Downloads – beides steht
        mit Beleg in docs/takeout.md. Wer das nicht weiß, lädt drei
        Teile und kommt eine Woche später nicht mehr an den Rest."""
        self.assertIn("sieben Tagen", self.text)
        self.assertIn("fünfmal", self.text)

    def test_sie_warnt_vor_dem_fehlenden_teil(self) -> None:
        """Der teuerste Fehler überhaupt: Bilder da, Datum und Ort weg
        – und es fällt nicht auf."""
        self.assertIn("Fehlt ein Teil", self.text)

    def test_sie_sagt_dass_nichts_ausgepackt_werden_muss(self) -> None:
        self.assertIn("Auspacken", self.text)

    def test_sie_verspricht_kein_loeschen_bei_google(self) -> None:
        """**Keine Zusage, die das Programm nicht hält.** Google Fotos
        hat für fremde Programme nie eine Löschfunktion gehabt."""
        self.assertIn("von Hand im Browser", self.text)

    def test_verweise_gehen_nach_draussen_und_nicht_ins_fenster(self) -> None:
        """Dieses Programm soll kein Browser werden – und ein Verweis,
        der im Hilfefenster aufgeht, lässt den Leser dort stranden."""
        self.assertFalse(self.seite.text.openLinks())

    def test_die_adressen_sind_die_erwarteten(self) -> None:
        from wolkenernte.fenster.hilfe import GOOGLE_HILFE, TAKEOUT

        html = self.seite.text.toHtml()
        self.assertIn("takeout.google.com", TAKEOUT)
        self.assertIn("support.google.com", GOOGLE_HILFE)
        self.assertIn("takeout.google.com", html)

    def test_kein_nachgemalter_klickweg(self) -> None:
        """**Absichtlich nicht drin.** »Auf ›Weiter‹ klicken, dann unten
        links auf ›Export erstellen‹« ist nach dem nächsten Umbau von
        Googles Seite falsch. Beschrieben wird das Ziel jedes Schrittes,
        verlinkt wird Googles eigene Hilfe."""
        for erfunden in ("Weiter“ klicken", "Export erstellen",
                         "Nächster Schritt"):
            with self.subTest(erfunden):
                self.assertNotIn(erfunden, self.text)

    def test_die_seite_blockiert_das_fenster_nicht(self) -> None:
        """Wer die Anleitung braucht, braucht sie *während* er den
        Dialog bedient."""
        self.assertFalse(self.seite.isModal())


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DieUeberSeite(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from wolkenernte.fenster.hilfe import ueber

        self.seite = ueber()

    def test_sie_nennt_die_fassung(self) -> None:
        from wolkenernte import __version__

        self.assertIn(__version__, self.seite.text.toPlainText())
        self.assertIn(__version__, self.seite.windowTitle())

    def test_ohne_knopf_zu_google(self) -> None:
        """Auf einer Seite über das Programm hat ein Knopf, der
        Googles Netzseite öffnet, nichts zu suchen.

        **Nicht ``isVisible()`` fragen.** Ein Widget in einem Fenster,
        das nie gezeigt wurde, ist *immer* unsichtbar – der erste
        Anlauf dieses Tests war grün, auch als der Knopf noch da war.
        Die Gegenprobe hat es aufgedeckt. ``isVisibleTo`` fragt, ob er
        sichtbar *wäre*, wenn man das Fenster zeigte, und das ist die
        Frage.
        """
        self.assertFalse(self.seite.oeffnen.isVisibleTo(self.seite))

    def test_die_anleitung_hat_den_knopf_dagegen_schon(self) -> None:
        """Die Gegenrichtung – sonst prüfte das obige nur, dass
        ``isVisibleTo`` irgendwas zurückgibt."""
        from wolkenernte.fenster.hilfe import takeout_hilfe

        seite = takeout_hilfe()
        self.assertTrue(seite.oeffnen.isVisibleTo(seite))

    def test_sie_sagt_dass_nichts_nach_hause_telefoniert(self) -> None:
        text = self.seite.text.toPlainText()
        self.assertIn("nur auf diesem Rechner", text)
        self.assertIn("neuigkeiten", text)


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DieSeiteBleibtOffen(unittest.TestCase):
    """**Ein nicht modaler Dialog braucht einen Verweis aus Python.**

    Ohne ihn sammelt der Speicherverwalter ihn ein, sobald die Methode
    endet – das Fenster erscheint und verschwindet im selben
    Augenblick. Das sieht nach einem Fehler in Qt aus und ist eine
    fehlende Variable.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_das_fenster_haelt_die_seite_fest(self) -> None:
        from wolkenernte.fenster.hauptfenster import Hauptfenster

        tmp = Path(tempfile.mkdtemp())
        (tmp / "2024").mkdir()
        fenster = Hauptfenster(tmp)
        try:
            fenster._takeout_hilfe_zeigen()
            self.assertEqual(len(fenster._hilfeseiten), 1)
            fenster._ueber_zeigen()
            self.assertEqual(len(fenster._hilfeseiten), 2)
            # Geschlossene Seiten werden wieder losgelassen, sonst
            # sammelt sich bei jedem Aufruf eine mehr an.
            fenster._hilfeseiten[0].close()
            fenster._hilfeseiten[0].reject()
            self.assertLessEqual(len(fenster._hilfeseiten), 1)
        finally:
            fenster.ansicht.aufraeumen()
            fenster.close()


if __name__ == "__main__":
    unittest.main()

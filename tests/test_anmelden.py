"""In einer Wolke anmelden – für jeden Anbieter, nicht nur Nextcloud.

Das Programm hieß von Anfang an »aus **allen** Cloudspeichern«, aber
anmelden ließ sich im Fenster nur eine Nextcloud. Diese Tests halten
fest, dass die Auswahl aus der Anbietertabelle kommt und dass kein
halbfertiger Zugang stehenbleibt.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte.anbieter import ANBIETER, NACH_KENNUNG, Weg
from wolkenernte.einrichten import Frage
from wolkenernte.rclone import Dienst, fassung, finden

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt
PYSIDE = importlib.util.find_spec("PySide6") is not None

if PYSIDE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(PYSIDE, "PySide6 fehlt")
class DieAnbieterauswahl(unittest.TestCase):
    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        from wolkenernte.fenster.anmelden import AnbieterWaehlen

        self.app = QApplication.instance() or QApplication([])
        self.dialog = AnbieterWaehlen()

    def tearDown(self) -> None:
        self.dialog = None

    def test_jeder_anbieter_steht_drin(self) -> None:
        """Auch die, bei denen es nicht geht – wer Google Fotos sucht
        und nichts findet, hält das Programm für unfertig."""
        self.assertEqual(self.dialog.liste.count(), len(ANBIETER))

    def test_was_nicht_geht_ist_nicht_waehlbar(self) -> None:
        from PySide6.QtCore import Qt

        for zeile in range(self.dialog.liste.count()):
            eintrag = self.dialog.liste.item(zeile)
            anbieter = ANBIETER[zeile]
            with self.subTest(anbieter.name):
                waehlbar = bool(eintrag.flags() & Qt.ItemFlag.ItemIsEnabled)
                self.assertEqual(waehlbar, anbieter.weg is Weg.RCLONE)

    def test_der_grund_steht_daneben(self) -> None:
        """Bei Google Fotos gibt es keinen Zugang – und der Text sagt
        warum, statt den Eintrag wegzulassen."""
        zeile = [a.kennung for a in ANBIETER].index("google-fotos")
        self.assertIn("nicht anmeldbar", self.dialog.liste.item(zeile).text())

    def test_der_hinweis_wird_nicht_zerschnitten(self) -> None:
        """Ein erster Anlauf kürzte am ersten Punkt und machte aus
        »Seit dem 31. März 2019 …« ein »Seit dem 31.«."""
        self.dialog.liste.setCurrentRow(
            [a.kennung for a in ANBIETER].index("google-fotos"))
        voller = NACH_KENNUNG["google-fotos"].hinweis
        self.assertIn(voller, self.dialog.hinweis.text())

    def test_weiter_bleibt_gesperrt_bis_etwas_gewaehlt_ist(self) -> None:
        self.assertFalse(self.dialog.weiter.isEnabled())

    def test_die_faehigkeiten_stehen_am_eintrag(self) -> None:
        """Sehen, holen, löschen – **bevor** sich jemand darauf
        verlässt."""
        zeile = [a.kennung for a in ANBIETER].index("nextcloud")
        text = self.dialog.liste.item(zeile).text()
        for was in ("sehen", "holen", "löschen"):
            with self.subTest(was):
                self.assertIn(was, text)

    def test_eine_wahl_schaltet_weiter_frei(self) -> None:
        zeile = [a.kennung for a in ANBIETER].index("nextcloud")
        self.dialog.liste.setCurrentRow(zeile)
        self.assertTrue(self.dialog.weiter.isEnabled())
        self.dialog._weiter()
        self.assertEqual(self.dialog.gewaehlt.kennung, "nextcloud")

    def test_ein_gesperrter_eintrag_kommt_nicht_durch(self) -> None:
        zeile = [a.kennung for a in ANBIETER].index("google-fotos")
        self.dialog.liste.setCurrentRow(zeile)
        self.dialog._weiter()
        self.assertIsNone(self.dialog.gewaehlt)


@unittest.skipUnless(PYSIDE, "PySide6 fehlt")
class DasFrageblatt(unittest.TestCase):
    """Die Rückfragen kommen von rclone – jede Art braucht ihr Feld."""

    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.blaetter = []

    def _blatt(self, frage: Frage):
        from wolkenernte.fenster.anmelden import Frageblatt

        blatt = Frageblatt(frage, NACH_KENNUNG["dropbox"])
        self.blaetter.append(blatt)
        return blatt

    def test_ein_kennwort_steht_nicht_im_klartext(self) -> None:
        from PySide6.QtWidgets import QLineEdit

        blatt = self._blatt(Frage(name="pass", geheim=True, vorgabe="alt"))
        self.assertEqual(blatt.feld.echoMode(), QLineEdit.EchoMode.Password)
        # Die Vorgabe wird nicht übernommen: Ein vorausgefülltes
        # Kennwortfeld verleitet dazu, es stehen zu lassen.
        self.assertEqual(blatt.feld.text(), "")

    def test_ja_nein_wird_zum_haekchen(self) -> None:
        from PySide6.QtWidgets import QCheckBox

        blatt = self._blatt(Frage(name="alles", art="bool", vorgabe="true"))
        self.assertIsInstance(blatt.feld, QCheckBox)
        self.assertEqual(blatt.antwort(), "true")

    def test_eine_auswahl_wird_zur_liste(self) -> None:
        from PySide6.QtWidgets import QComboBox

        blatt = self._blatt(Frage(name="region", auswahl=["eu", "us"],
                                  nur_auswahl=True, vorgabe="us"))
        self.assertIsInstance(blatt.feld, QComboBox)
        self.assertFalse(blatt.feld.isEditable())
        self.assertEqual(blatt.antwort(), "us")

    def test_eine_offene_auswahl_bleibt_beschreibbar(self) -> None:
        blatt = self._blatt(Frage(name="url", auswahl=["https://a"],
                                  nur_auswahl=False))
        self.assertTrue(blatt.feld.isEditable())

    def test_rclones_hilfetext_wird_gezeigt(self) -> None:
        """Ihn zu übersetzen hieße, ihn bei jeder rclone-Fassung
        nachzupflegen – und falsch zu übersetzen, wo wir den Anbieter
        gar nicht kennen."""
        from PySide6.QtWidgets import QLabel

        blatt = self._blatt(Frage(name="x", hilfe="Choose your region"))
        texte = " ".join(k.text() for k in blatt.findChildren(QLabel))
        self.assertIn("Choose your region", texte)

    def test_ein_fehler_vom_letzten_versuch_steht_oben(self) -> None:
        from PySide6.QtWidgets import QLabel

        blatt = self._blatt(Frage(name="x", fehler="falsches Kennwort"))
        texte = " ".join(k.text() for k in blatt.findChildren(QLabel))
        self.assertIn("falsches Kennwort", texte)


class FreieNamen(unittest.TestCase):
    def test_der_erste_heisst_wie_der_anbieter(self) -> None:
        from wolkenernte.fenster.anmelden import _namen_finden

        self.assertEqual(_namen_finden("dropbox", set()), "dropbox")

    def test_der_zweite_bekommt_eine_zahl(self) -> None:
        """Zwei gleich benannte Zugänge überschrieben einander."""
        from wolkenernte.fenster.anmelden import _namen_finden

        self.assertEqual(_namen_finden("dropbox", {"dropbox"}), "dropbox2")
        self.assertEqual(
            _namen_finden("dropbox", {"dropbox", "dropbox2"}), "dropbox3")


@unittest.skipUnless(PYSIDE and ECHTES_RCLONE, "PySide6 oder rclone fehlt")
class KeinHalbfertigerZugang(unittest.TestCase):
    """Ein abgebrochener Zugang darf nicht stehenbleiben.

    Er sähe im Menü aus wie ein Zugang und wäre keiner – und beim
    Anklicken käme eine Fehlermeldung an einer Stelle, wo niemand mehr
    an die Anmeldung denkt.
    """

    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.dienst = Dienst.starten(self.tmp / "konf.conf")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_wegwerfen_raeumt_auf(self) -> None:
        from wolkenernte.einrichten import einrichten
        from wolkenernte.fenster.anmelden import _wegwerfen

        # rclone gibt die Namen je nach Fassung mit oder ohne
        # Doppelpunkt zurück - hier zählt nur, ob der Zugang da ist.
        def namen() -> set[str]:
            return {n.rstrip(":") for n in self.dienst.remotes()}

        einrichten(self.dienst, "wegdamit", "local")
        self.assertIn("wegdamit", namen())
        _wegwerfen(self.dienst, "wegdamit")
        self.assertNotIn("wegdamit", namen())

    def test_wegwerfen_stoert_sich_nicht_an_nichts(self) -> None:
        from wolkenernte.fenster.anmelden import _wegwerfen

        _wegwerfen(self.dienst, "gabesnie")

    def test_ein_abbruch_hinterlaesst_nichts(self) -> None:
        from wolkenernte.fenster import anmelden as modul

        vorher = {n.rstrip(":") for n in self.dienst.remotes()}
        with mock.patch.object(modul, "AnbieterWaehlen") as auswahl:
            auswahl.return_value.exec.return_value = True
            auswahl.return_value.gewaehlt = NACH_KENNUNG["dropbox"]
            with mock.patch.object(modul, "Frageblatt") as blatt:
                # Der Anwender bricht bei der ersten Rückfrage ab.
                blatt.return_value.exec.return_value = False
                name = modul.anmelden(self.dienst)

        self.assertIsNone(name)
        self.assertEqual({n.rstrip(":") for n in self.dienst.remotes()},
                         vorher)


if __name__ == "__main__":
    unittest.main()

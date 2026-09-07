"""Aufräumen im Fenster – prüfen, zeigen, dann erst löschen.

**Der einzige Schritt ohne Rückweg.** Diese Tests halten fest, dass die
Oberfläche nichts durchlässt, was der Prüflauf nicht schon erlaubt hat:
Was nicht nachweislich im Archiv liegt, lässt sich hier gar nicht erst
ankreuzen.

Gegen das echte rclone, mit einem alias-Zugang auf einen Probenordner.
Gelöscht wird wirklich – nur eben unter ``/tmp``.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import unittest
import zlib
from pathlib import Path

from wolkenernte.aufraeumen import Urteil, durchgehen
from wolkenernte.einrichten import einrichten
from wolkenernte.rclone import Dienst, fassung, finden
from wolkenernte.wolke import Wolke

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt
PYSIDE = importlib.util.find_spec("PySide6") is not None
PILLOW = importlib.util.find_spec("PIL") is not None

if PYSIDE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(PYSIDE, "PySide6 fehlt")
class DasUrteilsmodell(unittest.TestCase):
    """Die Liste zum Ankreuzen – ohne Wolke, ohne rclone.

    Sie bekommt fertige Urteile; woher die kommen, ist ihr gleich.
    """

    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        from wolkenernte.fenster.aufraeumen import Urteilsmodell

        self.app = QApplication.instance() or QApplication([])
        self.urteile = [
            Urteil("a.jpg", 100, True),
            Urteil("b.jpg", 200, True),
            Urteil("c.jpg", 300, False, grund="liegt so nicht im Archiv"),
        ]
        self.modell = Urteilsmodell(self.urteile)

    def test_nur_das_nachgewiesene_ist_vorgewaehlt(self) -> None:
        self.assertEqual(self.modell.gewaehlt, {0, 1})

    def test_das_ungesicherte_laesst_sich_nicht_ankreuzen(self) -> None:
        """Ein abgeblendetes Häkchen wäre eine Einladung zum
        Herumklicken; hier soll erkennbar sein, dass die Entscheidung
        schon gefallen ist."""
        from PySide6.QtCore import Qt

        flaggen = self.modell.flags(self.modell.index(2, 0))
        self.assertFalse(flaggen & Qt.ItemFlag.ItemIsUserCheckable)
        self.assertIsNone(
            self.modell.data(self.modell.index(2, 0),
                             Qt.ItemDataRole.CheckStateRole))

    def test_ein_haekchen_laesst_sich_wegnehmen(self) -> None:
        from PySide6.QtCore import Qt

        self.modell.setData(self.modell.index(0, 0),
                            Qt.CheckState.Unchecked.value,
                            Qt.ItemDataRole.CheckStateRole)
        self.assertEqual(self.modell.gewaehlt, {1})

    def test_das_ungesicherte_bleibt_auch_auf_zuruf_draussen(self) -> None:
        """Der eigentliche Schutz: Auch wer die Methode direkt ruft,
        bekommt es nicht angekreuzt."""
        from PySide6.QtCore import Qt

        erfolg = self.modell.setData(self.modell.index(2, 0),
                                     Qt.CheckState.Checked.value,
                                     Qt.ItemDataRole.CheckStateRole)
        self.assertFalse(erfolg)
        self.assertNotIn(2, self.modell.gewaehlt)

    def test_alle_abwaehlen_und_wieder_zurueck(self) -> None:
        self.modell.alle_waehlen(False)
        self.assertEqual(self.modell.gewaehlt, set())
        self.modell.alle_waehlen(True)
        self.assertEqual(self.modell.gewaehlt, {0, 1})

    def test_alle_waehlen_nimmt_das_ungesicherte_nie_mit(self) -> None:
        self.modell.alle_waehlen(True)
        self.assertNotIn(2, self.modell.gewaehlt)

    def test_die_ausgewaehlten_kommen_in_der_reihenfolge(self) -> None:
        self.assertEqual([u.pfad for u in self.modell.ausgewaehlte()],
                         ["a.jpg", "b.jpg"])

    def test_der_tooltip_nennt_den_grund(self) -> None:
        from PySide6.QtCore import Qt

        text = self.modell.data(self.modell.index(2, 0),
                                Qt.ItemDataRole.ToolTipRole)
        self.assertIn("bleibt", text)
        self.assertIn("nicht im Archiv", text)


@unittest.skipUnless(PYSIDE and ECHTES_RCLONE and PILLOW,
                     "PySide6, rclone oder Pillow fehlt")
class DerGanzeDialog(unittest.TestCase):
    def setUp(self) -> None:
        from PIL import Image
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")

        self.inhalt = self.tmp / "wolke"
        self.inhalt.mkdir()
        self.archiv = self.tmp / "archiv" / "2024" / "2024-05"
        self.archiv.mkdir(parents=True)

        # Zwei Bilder liegen im Archiv, eines nicht.
        for nummer, name in enumerate(("IMG_1.jpg", "IMG_2.jpg", "IMG_3.jpg")):
            Image.new("RGB", (60, 40), (30 * nummer, 90, 140)).save(
                self.inhalt / name)
            if nummer < 2:
                shutil.copyfile(self.inhalt / name,
                                self.archiv / f"anders-{nummer}.jpg")

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "alias",
                   angaben={"remote": str(self.inhalt)})
        self.wolke = Wolke(self.dienst, "probe", "")
        self.dialoge = []

    def tearDown(self) -> None:
        self.dialoge.clear()
        self.wolke.schliessen()
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _dialog(self):
        from wolkenernte.fenster.aufraeumen import AufraeumenDialog

        dialog = AufraeumenDialog(self.dienst, self.wolke,
                                  self.tmp / "archiv")
        self.dialoge.append(dialog)
        # Der Prüflauf steckt in einem eigenen Faden; ihn hier zu Ende
        # laufen zu lassen ist verlässlicher als auf Signale zu warten.
        dialog.pruefung.abbrechen = False
        dialog._faden_beenden()
        bilanz = durchgehen(self.tmp / "archiv", self.wolke, wirklich=False)
        dialog._geprueft(bilanz)
        return dialog

    def test_zwei_duerfen_weg_eines_bleibt(self) -> None:
        dialog = self._dialog()
        self.assertEqual(len(dialog.modell.gewaehlt), 2)
        self.assertEqual(len(dialog.modell.urteile), 3)

    def test_der_kopf_sagt_beide_zahlen(self) -> None:
        dialog = self._dialog()
        self.assertIn("2", dialog.kopf.text())
        self.assertIn("bleiben stehen", dialog.kopf.text())

    def test_der_loeschknopf_zaehlt_mit(self) -> None:
        dialog = self._dialog()
        self.assertIn("(2)", dialog.loeschen.text())
        dialog.modell.alle_waehlen(False)
        dialog._zahl_auffrischen()
        self.assertFalse(dialog.loeschen.isEnabled())

    def test_das_vorschaubild_kommt_aus_der_geholten_datei(self) -> None:
        """Zum Prüfen wird ohnehin jede Datei heruntergeladen – daraus
        ein Vorschaubild zu machen, kostet nichts extra."""
        dialog = self._dialog()
        for urteil in dialog.modell.urteile:
            with self.subTest(urteil.pfad):
                self.assertIsNotNone(urteil.ablage)
                self.assertTrue(urteil.ablage.is_file())

    def test_geloescht_wird_nur_das_angekreuzte(self) -> None:
        from unittest import mock

        from PySide6.QtWidgets import QMessageBox

        dialog = self._dialog()
        with mock.patch.object(QMessageBox, "warning",
                               return_value=QMessageBox.StandardButton.Yes), \
                mock.patch.object(QMessageBox, "information"):
            dialog._loeschen()

        self.assertEqual(dialog.geloescht, 2)
        self.assertFalse((self.inhalt / "IMG_1.jpg").exists())
        self.assertFalse((self.inhalt / "IMG_2.jpg").exists())
        self.assertTrue((self.inhalt / "IMG_3.jpg").exists())

    def test_ohne_bestaetigung_verschwindet_nichts(self) -> None:
        from unittest import mock

        from PySide6.QtWidgets import QMessageBox

        dialog = self._dialog()
        with mock.patch.object(QMessageBox, "warning",
                               return_value=QMessageBox.StandardButton.Cancel):
            dialog._loeschen()

        self.assertEqual(dialog.geloescht, 0)
        for name in ("IMG_1.jpg", "IMG_2.jpg", "IMG_3.jpg"):
            with self.subTest(name):
                self.assertTrue((self.inhalt / name).exists())

    def test_ohne_auswahl_passiert_nichts(self) -> None:
        from unittest import mock

        from PySide6.QtWidgets import QMessageBox

        dialog = self._dialog()
        dialog.modell.alle_waehlen(False)
        with mock.patch.object(QMessageBox, "warning") as gefragt:
            dialog._loeschen()
        self.assertFalse(gefragt.called)


if __name__ == "__main__":
    unittest.main()

"""Den Google-Takeout im Fenster einlesen.

Läuft ohne Bildschirm über ``QT_QPA_PLATFORM=offscreen``. Ohne PySide6
wird übersprungen.

**Der gefährlichste Weg im ganzen Programm führt hier durch.** Am Ende
dieses Dialogs dürfen neun Gigabyte Quelldateien gelöscht werden. Fällt
irgendwo dazwischen ein Schritt aus, ist der Verlust nicht
wiederherstellbar – und niemand sieht es, weil die *Bilder* ja da sind.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    QT = True
except ImportError:  # pragma: no cover
    QT = False

try:
    from PIL import Image
    PILLOW = True
except ImportError:  # pragma: no cover
    PILLOW = False


def _jpeg(farbe: tuple[int, int, int]) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (80, 60), farbe).save(puffer, format="JPEG")
    return puffer.getvalue()


def _json(name: str) -> bytes:
    return json.dumps({
        "title": name,
        "photoTakenTime": {"timestamp": "1721053800"},
        "geoData": {"latitude": 53.55, "longitude": 8.58},
    }).encode()


@unittest.skipUnless(QT and PILLOW, "PySide6 oder Pillow fehlt")
class DerLaufMachtAlleDreiSchritte(unittest.TestCase):
    """**Holen, erfassen, prüfen – und keiner davon ist Kür.**

    Orte, Titel und Albumzugehörigkeiten stehen *ausschließlich* in den
    JSON-Dateien des Takeouts. Wer nur holt und die ZIPs dann wegwirft,
    hat die Bilder und sonst nichts – und merkt es Monate später, wenn
    er ein Album sucht.

    Dieser Test fällt um, sobald jemand `erfassen` aus dem Lauf
    herausnimmt oder die Reihenfolge vertauscht.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "Archiv"
        self.archiv.mkdir()
        self.quelle = self.tmp / "Downloads"
        self.quelle.mkdir()

        # Zwei Teile, und die Metadaten liegen im zweiten - die
        # Nahtstelle, an der ein Import ohne gemeinsamen Namensraum
        # Datum und Ort verliert.
        self.erstes = self.quelle / "takeout-20260912T1-1-001.zip"
        with zipfile.ZipFile(self.erstes, "w") as z:
            z.writestr("Takeout/Google Fotos/Nordsee 2023/IMG_1.jpg",
                       _jpeg((10, 20, 30)))
        self.zweites = self.quelle / "takeout-20260912T1-1-002.zip"
        with zipfile.ZipFile(self.zweites, "w") as z:
            z.writestr(
                "Takeout/Google Fotos/Nordsee 2023/"
                "IMG_1.jpg.supplemental-metadata.json", _json("IMG_1.jpg"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _laufen(self):
        from wolkenernte.fenster.takeout import TakeoutArbeit

        arbeit = TakeoutArbeit(self.archiv, [self.erstes, self.zweites])
        ergebnis = {}
        arbeit.fertig.connect(lambda e: ergebnis.update(werte=e))
        arbeit.misslungen.connect(lambda t: ergebnis.update(fehler=t))
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            arbeit.laufen()
        self.assertNotIn("fehler", ergebnis, ergebnis.get("fehler"))
        return ergebnis["werte"]

    def test_das_bild_liegt_hinterher_im_archiv(self) -> None:
        self._laufen()
        bilder = [p for p in self.archiv.rglob("*.jpg")
                  if ".wolkenernte" not in p.parts]
        self.assertEqual(len(bilder), 1)

    def test_das_album_ist_erfasst(self) -> None:
        """**Der Kern.** Ohne `erfassen` im Lauf wäre die Tabelle leer
        – und nach dem Löschen der ZIPs für immer."""
        self._laufen()
        from wolkenernte.bestand import ORT

        db = sqlite3.connect(self.archiv / ORT)
        alben = [z[0] for z in db.execute("SELECT name FROM album")]
        db.close()
        self.assertEqual(alben, ["Nordsee 2023"])

    def test_der_ort_aus_der_json_ist_erfasst(self) -> None:
        """Die JSON lag im *zweiten* Teilarchiv."""
        self._laufen()
        from wolkenernte.bestand import ORT

        db = sqlite3.connect(self.archiv / ORT)
        breite = db.execute(
            "SELECT breite FROM bild WHERE breite IS NOT NULL").fetchone()
        db.close()
        assert breite is not None
        self.assertAlmostEqual(breite[0], 53.55, places=2)

    def test_der_nachweis_ist_vollstaendig(self) -> None:
        """Erst das erlaubt das Löschen der ZIP-Dateien."""
        _bilanz, nachweis = self._laufen()
        self.assertTrue(nachweis.vollstaendig)
        self.assertEqual(nachweis.geprueft, 1)
        self.assertEqual(nachweis.fehlend, [])

    def test_ein_fehlendes_bild_verhindert_den_nachweis(self) -> None:
        """**Die Notbremse.** Verschwindet zwischen Holen und Prüfen
        etwas aus dem Archiv, darf keine Quelle weg."""
        _bilanz, nachweis = self._laufen()
        self.assertTrue(nachweis.vollstaendig)

        for pfad in self.archiv.rglob("*.jpg"):
            if ".wolkenernte" not in pfad.parts:
                pfad.unlink()

        from wolkenernte.nachweis import nachweis_fuehren
        from wolkenernte.takeout import Archiv as Takeout

        with Takeout([self.erstes, self.zweites]) as quelle:
            zweiter = nachweis_fuehren(self.archiv, quelle, "probe")
        self.assertFalse(zweiter.vollstaendig)
        self.assertEqual(len(zweiter.fehlend), 1)

    def test_abbrechen_nach_dem_holen_laesst_nichts_loeschen(self) -> None:
        """**Der Abbruch greift zwischen den Schritten**, denn `ernten`
        kennt keinen. Wichtig ist nur: Danach darf keine Quelle weg.
        Die Bilder liegen dann im Archiv, aber ohne Orte und Alben –
        und die stehen ausschließlich in den ZIP-Dateien.
        """
        from wolkenernte.fenster.takeout import TakeoutArbeit

        arbeit = TakeoutArbeit(self.archiv, [self.erstes, self.zweites])
        arbeit.abbrechen = True
        gemeldet = {}
        arbeit.fertig.connect(lambda e: gemeldet.update(werte=e))
        arbeit.misslungen.connect(lambda t: gemeldet.update(fehler=t))

        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            arbeit.laufen()

        self.assertIn("fehler", gemeldet)
        self.assertIn("nichts gelöscht", gemeldet["fehler"])
        self.assertNotIn("werte", gemeldet)
        self.assertTrue(self.erstes.exists())
        self.assertTrue(self.zweites.exists())

    def test_die_zip_dateien_bleiben_liegen(self) -> None:
        """Der Lauf selbst löscht **nichts**. Das ist ein eigener
        Schritt mit eigener Rückfrage."""
        self._laufen()
        self.assertTrue(self.erstes.exists())
        self.assertTrue(self.zweites.exists())


@unittest.skipUnless(QT and PILLOW, "PySide6 oder Pillow fehlt")
class DieAuswahl(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "Archiv"
        self.archiv.mkdir()
        self.quelle = self.tmp / "Downloads"
        self.quelle.mkdir()
        for name in ("takeout-A-1-001.zip", "takeout-A-1-002.zip"):
            with zipfile.ZipFile(self.quelle / name, "w") as z:
                z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg",
                           _jpeg((10, 20, 30)))
        with zipfile.ZipFile(self.quelle / "fremdes-programm.zip", "w") as z:
            z.writestr("liesmich.txt", b"kein Takeout")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _dialog(self):
        from wolkenernte.fenster.takeout import TakeoutWaehlen

        # **Den Ordner mitgeben, nicht nachträglich setzen.** Sonst
        # durchsucht der Aufbau den gemerkten Ordner des Anwenders –
        # und der Test hängt daran, was auf diesem Rechner steht.
        return TakeoutWaehlen(self.archiv, ordner=self.quelle)

    def test_fremde_zips_bilden_einen_eigenen_eintrag(self) -> None:
        """**Im Download-Ordner liegt nicht nur der Takeout.** Alles
        zusammen als einen Export zu lesen ergäbe eine Zählung, die
        niemand nachvollziehen kann."""
        dialog = self._dialog()
        namen = {dialog.baum.topLevelItem(i).text(0)
                 for i in range(dialog.baum.topLevelItemCount())}
        self.assertEqual(namen, {"takeout-A-1", "fremdes-programm"})

    def test_die_teile_stehen_unter_ihrem_export(self) -> None:
        dialog = self._dialog()
        zeile = next(dialog.baum.topLevelItem(i)
                     for i in range(dialog.baum.topLevelItemCount())
                     if dialog.baum.topLevelItem(i).text(0) == "takeout-A-1")
        self.assertEqual(zeile.childCount(), 2)

    def test_ohne_haken_kein_knopf(self) -> None:
        from PySide6.QtWidgets import QDialogButtonBox

        dialog = self._dialog()
        knopf = dialog.knoepfe.button(QDialogButtonBox.StandardButton.Ok)
        self.assertFalse(knopf.isEnabled())

    def test_mit_haken_kommt_die_vorschau(self) -> None:
        from PySide6.QtWidgets import QDialogButtonBox

        dialog = self._dialog()
        for i in range(dialog.baum.topLevelItemCount()):
            zeile = dialog.baum.topLevelItem(i)
            if zeile.text(0) == "takeout-A-1":
                zeile.setCheckState(0, Qt.CheckState.Checked)
        self.assertIn("Bilder und Videos", dialog.vorschau.text())
        self.assertTrue(
            dialog.knoepfe.button(
                QDialogButtonBox.StandardButton.Ok).isEnabled())

    def test_die_knoepfe_sind_deutsch(self) -> None:
        """Qt übersetzt seine Standardknöpfe nur mit geladenem
        QTranslator – sonst steht »Cancel« mitten im deutschen Dialog."""
        from PySide6.QtWidgets import QDialogButtonBox

        dialog = self._dialog()
        self.assertEqual(
            dialog.knoepfe.button(
                QDialogButtonBox.StandardButton.Cancel).text(), "Abbrechen")

    def test_loeschen_ist_nicht_voreingestellt(self) -> None:
        """Ein Haken, der beim Öffnen schon sitzt, ist keine
        Entscheidung des Anwenders.

        **Und eine PySide-Falle nebenbei:** ``self._dialog().loeschen``
        in einem Ausdruck reicht nicht – der Dialog wird noch in
        derselben Zeile eingesammelt und nimmt sein C++-Gegenstück
        mitsamt aller Kinder mit. Der Fehler lautet dann
        »Internal C++ object already deleted« und sieht nach einem
        Programmfehler aus.
        """
        dialog = self._dialog()
        self.assertFalse(dialog.loeschen.isChecked())

    def test_ein_eingetippter_pfad_wird_uebernommen(self) -> None:
        """**Der schnellste Weg zum richtigen Laufwerk** ist oft, den
        Pfad aus dem Dateimanager einzufügen. Vorher gab es nur einen
        Ordnerwähler, der in ``~/Downloads`` startete."""
        anderswo = self.tmp / "Platte"
        anderswo.mkdir()
        with zipfile.ZipFile(anderswo / "takeout-B-1-001.zip", "w") as z:
            z.writestr("Takeout/Google Fotos/2024/IMG_9.jpg", _jpeg((9, 9, 9)))

        dialog = self._dialog()
        dialog.pfadfeld.setText(str(anderswo))
        dialog._pfad_eingetippt()
        self.assertEqual(dialog.ordner, anderswo)
        namen = {dialog.baum.topLevelItem(i).text(0)
                 for i in range(dialog.baum.topLevelItemCount())}
        self.assertEqual(namen, {"takeout-B-1"})

    def test_ein_falscher_pfad_wird_gesagt(self) -> None:
        """Stillschweigend auf den alten zurückzufallen wäre schlimmer:
        Dann sucht jemand den Fehler im Export."""
        dialog = self._dialog()
        dialog.pfadfeld.setText(str(self.tmp / "gibtsnicht"))
        dialog._pfad_eingetippt()
        self.assertIn("gibt es nicht", dialog.vorschau.text())
        self.assertEqual(dialog.ordner, self.quelle)

    def test_ein_angeklicktes_teil_hakt_den_ganzen_export_an(self) -> None:
        """**Die wichtigste Regel dieses Dialogs.** Im Dateiwähler
        klickt man Dateien an – gemeint ist aber der Export. Wer nur
        ``-002.zip`` erwischt, bekommt beide Teile, denn sonst fehlten
        an der Nahtstelle die Metadaten.
        """
        dialog = self._dialog()
        from wolkenernte.takeout import stamm

        dialog._anhaken({stamm(self.quelle / "takeout-A-1-002.zip")})
        dialog._weiter()
        self.assertEqual([p.name for p in dialog.ausgewaehlt],
                         ["takeout-A-1-001.zip", "takeout-A-1-002.zip"])

    def test_die_teile_eines_exports_kommen_zusammen_heraus(self) -> None:
        dialog = self._dialog()
        for i in range(dialog.baum.topLevelItemCount()):
            zeile = dialog.baum.topLevelItem(i)
            if zeile.text(0) == "takeout-A-1":
                zeile.setCheckState(0, Qt.CheckState.Checked)
        dialog._weiter()
        self.assertEqual([p.name for p in dialog.ausgewaehlt],
                         ["takeout-A-1-001.zip", "takeout-A-1-002.zip"])


if __name__ == "__main__":
    unittest.main()

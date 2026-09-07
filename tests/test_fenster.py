"""Die Fensteranwendung.

Läuft ohne Bildschirm über ``QT_QPA_PLATFORM=offscreen`` – so lassen
sich die Tests auch in der CI ausführen, wo es keine Anzeige gibt. Ohne
PySide6 werden sie übersprungen; es ist eine Kür-Abhängigkeit.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    QT = True
except ImportError:
    QT = False

from wolkenernte.bestandsliste import Bild


def _archiv() -> Path:
    """Ein kleines Archiv, so aufgebaut wie ein echtes.

    **Die Dateizeit wird gesetzt**, nicht dem Zufall überlassen: Im
    echten Archiv trägt jede Datei ihr Aufnahmedatum, weil das Ernten
    es dorthin schreibt. Ein Testarchiv mit dem heutigen Datum bildet
    das nicht ab – und ein Test, der auf »2023« prüft, scheitert dann
    am Testaufbau statt am Programm.
    """
    tmp = Path(tempfile.mkdtemp())
    ordner = tmp / "2023" / "2023-07"
    ordner.mkdir(parents=True)
    try:
        from PIL import Image
        # Hochkant, damit sich das Zuschneiden auf Quadrate prüfen lässt.
        Image.new("RGB", (60, 120), (30, 90, 200)).save(ordner / "IMG_1.jpg")
        Image.new("RGB", (120, 60), (200, 90, 30)).save(ordner / "IMG_2.jpg")
    except ImportError:
        (ordner / "IMG_1.jpg").write_bytes(b"kein echtes Bild")
        (ordner / "IMG_2.jpg").write_bytes(b"auch nicht")
    (ordner / "VID_1.mp4").write_bytes(b"kein echtes Video")

    # 15. Juli 2023, wie es nach dem Ernten aussähe.
    zeit = datetime(2023, 7, 15, 12, 0).timestamp()
    for datei in ordner.iterdir():
        os.utime(datei, (zeit, zeit))
    return tmp


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DasBildmodell(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from wolkenernte.bestandsliste import Bestandsliste
        from wolkenernte.fenster.modell import Bildmodell

        self.archiv = _archiv()
        self.liste = Bestandsliste(self.archiv)
        self.modell = Bildmodell(self.archiv, self.liste.bilder)

    def test_zaehlt_die_bilder(self) -> None:
        self.assertEqual(self.modell.rowCount(), 3)

    def test_liefert_sofort_etwas(self) -> None:
        """Die Ansicht darf nicht warten, bis ein Vorschaubild fertig
        ist – sonst hakt der Bildlauf bei jedem neuen Bild."""
        from PySide6.QtCore import Qt

        stelle = self.modell.index(0, 0)
        symbol = self.modell.data(stelle, Qt.ItemDataRole.DecorationRole)
        self.assertIsNotNone(symbol)

    def test_hinweistext_nennt_das_wesentliche(self) -> None:
        """Nicht auf eine bestimmte Stelle festnageln.

        Alle Testdateien entstehen im selben Augenblick; die Liste
        sortiert nach Zeit, und bei gleicher Zeit ist die Reihenfolge
        beliebig. Ein erster Anlauf prüfte Stelle 0 auf »IMG_« und fand
        dort das Video.
        """
        from PySide6.QtCore import Qt

        for zeile in range(self.modell.rowCount()):
            text = self.modell.data(self.modell.index(zeile, 0),
                                    Qt.ItemDataRole.ToolTipRole)
            with self.subTest(zeile):
                self.assertIn("MB", text)
                self.assertIn("2023", text)
                self.assertTrue(text.split("\n")[0].endswith(
                    (".jpg", ".mp4")), text)

    def test_ausserhalb_gibt_nichts(self) -> None:
        self.assertIsNone(self.modell.bild_bei(self.modell.index(99, 0)))

    def test_auswahl_wechseln(self) -> None:
        self.modell.zeigen([])
        self.assertEqual(self.modell.rowCount(), 0)
        self.modell.zeigen(self.liste.bilder)
        self.assertEqual(self.modell.rowCount(), 3)


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DieKachelnSindQuadratisch(unittest.TestCase):
    """Sonst reißt das Raster Lücken.

    ``KeepAspectRatioByExpanding`` macht das Bild mindestens so groß wie
    verlangt, schneidet aber nichts ab – ein Hochformat blieb hochkant,
    und jede Zeile sah anders aus.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_hochformat_wird_quadratisch(self) -> None:
        from PySide6.QtGui import QPixmap

        from wolkenernte.fenster.modell import KACHEL, _quadratisch

        hoch = QPixmap(60, 200)
        hoch.fill()
        ergebnis = _quadratisch(hoch)
        self.assertEqual((ergebnis.width(), ergebnis.height()), (KACHEL, KACHEL))

    def test_querformat_wird_quadratisch(self) -> None:
        from PySide6.QtGui import QPixmap

        from wolkenernte.fenster.modell import KACHEL, _quadratisch

        quer = QPixmap(400, 100)
        quer.fill()
        ergebnis = _quadratisch(quer)
        self.assertEqual((ergebnis.width(), ergebnis.height()), (KACHEL, KACHEL))


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DasHauptfenster(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from wolkenernte.fenster.hauptfenster import Hauptfenster

        self.archiv = _archiv()
        self.fenster = Hauptfenster(self.archiv)

    def tearDown(self) -> None:
        self.fenster.ansicht.aufraeumen()
        self.fenster.close()

    def test_zeigt_alle_bilder(self) -> None:
        self.assertEqual(self.fenster.modell.rowCount(), 3)

    def test_statusleiste_nennt_die_zahl(self) -> None:
        self.assertIn("3", self.fenster.statusBar().currentMessage())

    def test_nach_jahr_filtern(self) -> None:
        self.fenster.jahrwahl.setCurrentIndex(1)  # 2023
        self.assertEqual(self.fenster.modell.rowCount(), 3)

    def test_suche_grenzt_ein(self) -> None:
        self.fenster.suchfeld.setText("VID")
        self.fenster._auswahl_anwenden()
        self.assertEqual(self.fenster.modell.rowCount(), 1)

    def test_suche_ohne_treffer(self) -> None:
        self.fenster.suchfeld.setText("gibtsnichtimarchiv")
        self.fenster._auswahl_anwenden()
        self.assertEqual(self.fenster.modell.rowCount(), 0)

    def test_einzelansicht_und_zurueck(self) -> None:
        self.fenster._oeffnen(self.fenster.modell.index(0, 0))
        self.assertIs(self.fenster.ebenen.currentWidget(), self.fenster.ansicht)
        self.fenster._zum_raster()
        self.assertIs(self.fenster.ebenen.currentWidget(), self.fenster.raster)

    def test_blaettern_bleibt_im_bestand(self) -> None:
        """Am Anfang und Ende darf nichts überlaufen."""
        self.fenster._oeffnen(self.fenster.modell.index(0, 0))
        self.fenster._blaettern(-1)
        self.assertEqual(self.fenster._stelle, 0)
        self.fenster._stelle = self.fenster.modell.rowCount() - 1
        self.fenster._blaettern(1)
        self.assertEqual(self.fenster._stelle,
                         self.fenster.modell.rowCount() - 1)


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DieEinzelansicht(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dreht_nach_aufnahmerichtung(self) -> None:
        """Qt ignoriert das EXIF-Feld, wenn man es nicht ausdrücklich
        darum bittet – hochkant gehaltene Aufnahmen lagen sonst auf der
        Seite, obwohl das Raster sie richtig zeigte."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow fehlt")

        from wolkenernte.fenster.ansicht import _laden

        tmp = Path(tempfile.mkdtemp())
        pfad = tmp / "gedreht.jpg"
        bild = Image.new("RGB", (200, 100), (10, 20, 30))
        # EXIF-Ausrichtung 6: um 90 Grad gedreht aufgenommen.
        exif = bild.getexif()
        exif[274] = 6
        bild.save(pfad, exif=exif)

        geladen = _laden(pfad)
        self.assertFalse(geladen.isNull())
        # Nach der Drehung ist aus quer hoch geworden.
        self.assertGreater(geladen.height(), geladen.width())

    def test_unbekanntes_format_stuerzt_nicht_ab(self) -> None:
        from wolkenernte.fenster.ansicht import Einzelansicht

        tmp = Path(tempfile.mkdtemp())
        (tmp / "x.xyz").write_bytes(b"nichts")
        ansicht = Einzelansicht(tmp)
        ansicht.zeigen(Bild(pfad="x.xyz", groesse=6, zeit=datetime.now()))
        self.assertIn("nicht anzeigen", ansicht.anzeige.text())


if __name__ == "__main__":
    unittest.main()

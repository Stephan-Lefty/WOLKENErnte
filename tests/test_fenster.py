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


def _archiv_ueber_jahre() -> Path:
    """Ein Archiv mit Streuung – und einem Bild ohne Aufnahmedatum.

    Das letzte ist der Fall, der beim Zeitraum leicht verlorengeht: Es
    liegt in keinem, und beim Start darf es trotzdem nicht fehlen.
    """
    tmp = Path(tempfile.mkdtemp())
    tage = {
        "2021/2021-03/a.jpg": datetime(2021, 3, 10, 9, 0),
        "2023/2023-07/b.jpg": datetime(2023, 7, 15, 12, 0),
        "2023/2023-12/c.mp4": datetime(2023, 12, 31, 23, 59),
        "2024/2024-01/d.jpg": datetime(2024, 1, 1, 0, 30),
    }
    for name, wann in tage.items():
        ziel = tmp / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(b"inhalt")
        os.utime(ziel, (wann.timestamp(), wann.timestamp()))
    ohne = tmp / "ohne-datum" / "e.jpg"
    ohne.parent.mkdir(parents=True)
    ohne.write_bytes(b"inhalt")
    return tmp


@unittest.skipUnless(QT, "PySide6 nicht vorhanden")
class DerZeitraum(unittest.TestCase):
    """»Alles, was zwischen … und … entstanden ist.«"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from wolkenernte.fenster.hauptfenster import Hauptfenster

        self.archiv = _archiv_ueber_jahre()
        self.fenster = Hauptfenster(self.archiv)

    def tearDown(self) -> None:
        self.fenster.ansicht.aufraeumen()
        self.fenster.close()

    def _stellen(self, von: datetime, bis: datetime) -> None:
        from PySide6.QtCore import QDate

        self.fenster.von_feld.setDate(QDate(von.year, von.month, von.day))
        self.fenster.bis_feld.setDate(QDate(bis.year, bis.month, bis.day))

    def test_beim_start_filtert_nichts(self) -> None:
        """**Die Falle.** Wären die Felder von Anfang an scharf, fehlte
        das Bild ohne Aufnahmedatum wortlos – es liegt in keinem
        Zeitraum, und niemand hätte danach gefragt."""
        self.assertFalse(self.fenster.zeitraum_an.isChecked())
        self.assertEqual(self.fenster.modell.rowCount(), 5)

    def test_die_felder_sind_erst_aus(self) -> None:
        self.assertFalse(self.fenster.von_feld.isEnabled())
        self.assertFalse(self.fenster.bis_feld.isEnabled())

    def test_ein_datum_schaltet_von_selbst_ein(self) -> None:
        """Sonst wählt man einen Tag und es passiert nichts."""
        self._stellen(datetime(2023, 1, 1), datetime(2023, 12, 31))
        self.assertTrue(self.fenster.zeitraum_an.isChecked())
        self.assertTrue(self.fenster.von_feld.isEnabled())

    def test_grenzt_auf_den_zeitraum_ein(self) -> None:
        self._stellen(datetime(2023, 1, 1), datetime(2023, 12, 31))
        self.assertEqual(self.fenster.modell.rowCount(), 2)

    def test_der_letzte_tag_gehoert_dazu(self) -> None:
        """``c.mp4`` liegt am 31.12.2023 um 23:59."""
        self._stellen(datetime(2023, 12, 31), datetime(2023, 12, 31))
        self.assertEqual(self.fenster.modell.rowCount(), 1)

    def test_bilder_und_videos_gleichermassen(self) -> None:
        self._stellen(datetime(2023, 12, 1), datetime(2024, 1, 31))
        namen = sorted(b.name for b in self.fenster.modell.bilder)
        self.assertEqual(namen, ["c.mp4", "d.jpg"])

    def test_ohne_datum_faellt_heraus(self) -> None:
        """Der Haken muss hier **von Hand** gesetzt werden.

        Die Felder stehen schon auf der vollen Spanne, und ein
        ``setDate`` auf denselben Wert sendet kein Signal – das
        Selbsteinschalten kann also gar nicht greifen. Genau darum ist
        die volle Spanne der einzige Zeitraum, den man nur über den
        Haken bekommt.
        """
        self.fenster.zeitraum_an.setChecked(True)
        self.assertEqual(self.fenster.modell.rowCount(), 4)

    def test_der_kalender_endet_am_bestand(self) -> None:
        """In ein Jahr blättern zu können, in dem es kein Bild gibt,
        hilft niemandem."""
        self.assertEqual(self.fenster.von_feld.minimumDate().year(), 2021)
        self.assertEqual(self.fenster.bis_feld.maximumDate().year(), 2024)

    def test_zuruecksetzen_gibt_alles_zurueck(self) -> None:
        self._stellen(datetime(2023, 1, 1), datetime(2023, 12, 31))
        self.fenster._zeitraum_zuruecksetzen()
        self.assertFalse(self.fenster.zeitraum_an.isChecked())
        self.assertEqual(self.fenster.modell.rowCount(), 5)

    def test_haken_wieder_weg_zeigt_wieder_alles(self) -> None:
        self._stellen(datetime(2023, 1, 1), datetime(2023, 12, 31))
        self.fenster.zeitraum_an.setChecked(False)
        self.assertEqual(self.fenster.modell.rowCount(), 5)

    def test_zusammen_mit_der_suche(self) -> None:
        """»Alles zum Suchwort, aber nur aus dem Zeitraum.«"""
        self._stellen(datetime(2023, 1, 1), datetime(2023, 12, 31))
        self.fenster.suchfeld.setText("jpg")
        self.fenster._auswahl_anwenden()
        namen = [b.name for b in self.fenster.modell.bilder]
        self.assertEqual(namen, ["b.jpg"])

    def test_vertauschte_grenzen_werden_gesagt(self) -> None:
        """Null Treffer sehen aus wie ein leeres Archiv, wenn niemand
        den Grund nennt."""
        self._stellen(datetime(2024, 1, 1), datetime(2021, 1, 1))
        self.assertEqual(self.fenster.modell.rowCount(), 0)
        self.assertIn("Bis-Datum", self.fenster.zeit_hinweis.text())

    def test_ohne_datum_und_zeitraum_wird_gesagt(self) -> None:
        self.fenster.zeitraum_an.setChecked(True)
        stelle = self.fenster.jahrwahl.findData("ohne")
        self.fenster.jahrwahl.setCurrentIndex(stelle)
        self.assertEqual(self.fenster.modell.rowCount(), 0)
        self.assertIn("schließen einander aus",
                      self.fenster.zeit_hinweis.text())

    def test_ohne_zeitraum_kein_hinweis(self) -> None:
        self.assertEqual(self.fenster.zeit_hinweis.text(), "")

    def test_das_wochenende_ist_lesbar(self) -> None:
        """Qts Wochenendrot erreicht auf dem dunklen Grund nur 3,81 –
        für Text verlangt WCAG 4,5. Und weil Qt die Farbe im Code setzt,
        kommt keine Regel im Stilblatt dagegen an; wer sie dort sucht,
        hält das Problem für gelöst."""
        from PySide6.QtCore import Qt

        from wolkenernte import farben

        kalender = self.fenster.von_feld.calendarWidget()
        for tag in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            farbe = kalender.weekdayTextFormat(tag).foreground().color()
            with self.subTest(tag):
                self.assertEqual(farbe.name(), farben.ROT_HELL)
                self.assertGreaterEqual(
                    farben.kontrast(farbe.name(), farben.GRAU_NACHT), 4.5)


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

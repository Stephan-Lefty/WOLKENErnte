"""Die HTML-Seiten der Weboberfläche.

**Warum es diese Datei gibt.** Beim Umzug der Bestandsliste aus ``web/``
eine Ebene höher fiel eine Eigenschaft weg, die ``seiten.py`` noch
benutzte – und alle 239 Tests blieben grün, weil die Einzelansicht
nirgends aufgerufen wurde. Aufgefallen wäre es erst beim Anzeigen eines
HEIC-Bildes.

Diese Tests rufen jede Seite einmal auf. Sie prüfen nicht, wie sie
aussieht, sondern dass sie überhaupt entsteht.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wolkenernte.bestandsliste import Bestandsliste, Bild
from wolkenernte.web import seiten


def _bild(pfad: str, **werte) -> Bild:
    werte.setdefault("groesse", 1234)
    werte.setdefault("zeit", datetime(2023, 7, 15, 12, 0))
    return Bild(pfad=pfad, **werte)


class DieSeitenEntstehen(unittest.TestCase):
    """Jede Seite einmal aufrufen – das fängt fehlende Namen ab."""

    def setUp(self) -> None:
        self.archiv = Path(tempfile.mkdtemp())
        (self.archiv / "2023" / "2023-07").mkdir(parents=True)
        (self.archiv / "2023/2023-07/IMG_1.jpg").write_bytes(b"bild")
        (self.archiv / "2023/2023-07/VID_1.mp4").write_bytes(b"video")
        (self.archiv / "2023/2023-07/IMG_2.heic").write_bytes(b"heic")
        self.liste = Bestandsliste(self.archiv)

    def test_uebersicht(self) -> None:
        html = seiten.uebersicht(self.liste)
        self.assertIn("<!doctype html>", html)
        self.assertIn("WOLKENErnte", html)

    def test_raster(self) -> None:
        html = seiten.raster(self.liste, self.liste.bilder, seite=1,
                             je_seite=120, jahr=None, album=None, zusatz="")
        self.assertIn("kachel", html)

    def test_suche_mit_treffern(self) -> None:
        html = seiten.suche(self.liste, "IMG", self.liste.suchen("IMG"))
        self.assertIn("Treffer", html)

    def test_suche_ohne_treffer(self) -> None:
        html = seiten.suche(self.liste, "gibtsnicht", [])
        self.assertIn("Nichts gefunden", html)

    def test_suche_ohne_wort(self) -> None:
        self.assertIn("Suchbegriff", seiten.suche(self.liste, "", []))

    def test_einzelansicht_bild(self) -> None:
        bild = self.liste.bei("2023/2023-07/IMG_1.jpg")
        assert bild is not None
        html = seiten.einzeln(self.liste, bild)
        self.assertIn("<img", html)

    def test_einzelansicht_video(self) -> None:
        bild = self.liste.bei("2023/2023-07/VID_1.mp4")
        assert bild is not None
        html = seiten.einzeln(self.liste, bild)
        self.assertIn("<video", html)

    def test_einzelansicht_heic_zeigt_die_vorschau(self) -> None:
        """Genau der Fall, der beim Umbau kaputtging.

        HEIC kann kein Browser darstellen – dort muss das Vorschaubild
        stehen, nicht die Originaldatei.
        """
        bild = self.liste.bei("2023/2023-07/IMG_2.heic")
        assert bild is not None
        html = seiten.einzeln(self.liste, bild)
        self.assertIn("/vorschau?p=", html)
        self.assertNotIn("/datei?p=2023%2F2023-07%2FIMG_2.heic\" alt", html)

    def test_doppelt_noch_nicht_gerechnet(self) -> None:
        html = seiten.doppelt(self.liste, [], fertig=False)
        self.assertIn("gerechnet", html)

    def test_doppelt_ohne_treffer(self) -> None:
        html = seiten.doppelt(self.liste, [], fertig=True)
        self.assertIn("Keine Doppelgänger", html)

    def test_doppelt_mit_gruppen(self) -> None:
        gruppe = [_bild("a/1.jpg"), _bild("a/2.jpg")]
        html = seiten.doppelt(self.liste, [(gruppe, "dieselbe Aufnahme")],
                              fertig=True)
        self.assertIn("dieselbe Aufnahme", html)


class WasDerBrowserKann(unittest.TestCase):
    def test_gewoehnliche_bilder(self) -> None:
        for endung in (".jpg", ".png", ".gif", ".webp"):
            with self.subTest(endung):
                self.assertTrue(seiten.im_browser(_bild(f"x{endung}")))

    def test_heic_nicht(self) -> None:
        """Deshalb wird dort das Vorschaubild gezeigt."""
        self.assertFalse(seiten.im_browser(_bild("x.heic")))

    def test_videos(self) -> None:
        self.assertTrue(seiten.im_browser(_bild("x.mp4", ist_video=True)))
        self.assertFalse(seiten.im_browser(_bild("x.mkv", ist_video=True)))


class DieZahlenformatierung(unittest.TestCase):
    def test_tausenderpunkte(self) -> None:
        self.assertEqual(seiten.zahl(14770), "14.770")

    def test_kleine_zahlen(self) -> None:
        self.assertEqual(seiten.zahl(7), "7")

    def test_der_viewport_bleibt_heil(self) -> None:
        """Hier lief einmal ein ``replace(",", ".")`` über die ganze
        Seite und machte aus ``width=device-width,initial-scale=1`` einen
        Punkt statt eines Kommas."""
        archiv = Path(tempfile.mkdtemp())
        html = seiten.uebersicht(Bestandsliste(archiv))
        self.assertIn("width=device-width,initial-scale=1", html)


if __name__ == "__main__":
    unittest.main()

"""Schlagwörter in der Bestandsliste und in beiden Oberflächen.

Der Unterbau steht in ``bestandsliste.py`` – **einmal**, nicht je
Oberfläche. Wer das trennt, lässt die beiden auseinanderlaufen; genau
das ist beim Umzug der Bestandsliste schon einmal passiert und blieb
grün getestet.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from wolkenernte.bestand import Bestand
from wolkenernte.bestandsliste import Bestandsliste, Bild, wann
from wolkenernte.web import seiten

MEZ = timezone(timedelta(hours=1))


def _bild(pfad: str, **werte) -> Bild:
    werte.setdefault("groesse", 1234)
    werte.setdefault("zeit", datetime(2023, 7, 15, 12, 0))
    return Bild(pfad=pfad, **werte)


class WannEinBildEntstand(unittest.TestCase):
    """Drei Fälle, drei Antworten – alles andere wäre eine Behauptung."""

    def test_ohne_datum(self) -> None:
        self.assertEqual(wann(_bild("x.jpg", datum_bekannt=False)),
                         "ohne Datum")

    def test_mit_uhrzeit(self) -> None:
        self.assertEqual(wann(_bild("x.jpg")), "15.07.2023 um 12:00")

    def test_nur_datum(self) -> None:
        """1.465 von 14.476 Bildern tragen keine Uhrzeit. »01:00« unter
        ein solches Bild zu schreiben behauptet etwas, das nirgends
        steht."""
        nur_datum = _bild("x.jpg", zeit=datetime(2023, 7, 15, 1, 0,
                                                 tzinfo=MEZ))
        self.assertFalse(nur_datum.uhrzeit_bekannt)
        self.assertEqual(wann(nur_datum), "15.07.2023")


class DieListeLiestSieAus(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "archiv"
        (self.archiv / "2023/2023-07").mkdir(parents=True)
        for name in ("IMG_1.jpg", "IMG_2.jpg", "VID_1.mp4"):
            (self.archiv / "2023/2023-07" / name).write_bytes(b"x" * 40)

        with Bestand(self.archiv) as bestand:
            eins = bestand.bild_merken(40, 1, pfad="2023/2023-07/IMG_1.jpg")
            zwei = bestand.bild_merken(40, 2, pfad="2023/2023-07/IMG_2.jpg")
            bestand.schlagwoerter_ersetzen(eins, "bild",
                                           [("Strand", 0.9), ("Meer", 0.6)])
            bestand.schlagwoerter_ersetzen(eins, "zeit", [("Sommer", 1.0)])
            bestand.schlagwoerter_ersetzen(zwei, "zeit", [("Sommer", 1.0)])
            bestand.sichern()
        self.liste = Bestandsliste(self.archiv)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _bei(self, name: str) -> Bild:
        bild = self.liste.bei(f"2023/2023-07/{name}")
        assert bild is not None
        return bild

    def test_sie_stehen_am_bild(self) -> None:
        self.assertEqual(set(self._bei("IMG_1.jpg").schlagworte),
                         {"Strand", "Meer", "Sommer"})

    def test_erkanntes_steht_vorn(self) -> None:
        """Was im Bild erkannt wurde, sagt mehr als die Jahreszeit –
        und in einer Kachelbeschriftung ist nur für die ersten Platz."""
        self.assertEqual(self._bei("IMG_1.jpg").schlagworte[0], "Strand")
        self.assertEqual(self._bei("IMG_1.jpg").schlagworte[-1], "Sommer")

    def test_ohne_schlagwoerter_bleibt_die_liste_leer(self) -> None:
        self.assertEqual(self._bei("VID_1.mp4").schlagworte, [])

    def test_haeufigkeiten(self) -> None:
        self.assertEqual(self.liste.schlagworte()[0], ("Sommer", 2))

    def test_filtern(self) -> None:
        treffer = self.liste.auswahl(schlagwort="Strand")
        self.assertEqual([b.name for b in treffer], ["IMG_1.jpg"])

    def test_unbekanntes_schlagwort_findet_nichts(self) -> None:
        self.assertEqual(self.liste.auswahl(schlagwort="Nordpol"), [])

    def test_suchen_findet_ueber_schlagwoerter(self) -> None:
        """Der eigentliche Zweck der ganzen Übung."""
        self.assertEqual([b.name for b in self.liste.suchen("strand")],
                         ["IMG_1.jpg"])

    def test_mehrere_woerter_muessen_alle_passen(self) -> None:
        self.assertEqual(len(self.liste.suchen("strand sommer")), 1)
        self.assertEqual(len(self.liste.suchen("strand winter")), 0)

    # -- Weboberfläche -----------------------------------------------------

    def test_die_leiste_zeigt_sie(self) -> None:
        html = seiten.raster(self.liste, self.liste.bilder, seite=1,
                             je_seite=120, jahr=None, album=None, zusatz="")
        self.assertIn("schlagwort=Strand", html)

    def test_die_einzelseite_zeigt_sie(self) -> None:
        html = seiten.einzeln(self.liste, self._bei("IMG_1.jpg"))
        self.assertIn("Schlagwörter", html)
        self.assertIn("Strand", html)

    def test_das_gefilterte_raster_entsteht(self) -> None:
        treffer = self.liste.auswahl(schlagwort="Strand")
        html = seiten.raster(self.liste, treffer, seite=1, je_seite=120,
                             jahr=None, album=None, zusatz="",
                             schlagwort="Strand")
        self.assertIn("Strand", html)
        self.assertIn("<!doctype html>", html)

    def test_ohne_schlagwoerter_keine_leiste(self) -> None:
        """Eine immer leere Leiste sähe nach einem Defekt aus – dabei
        fehlt nur ein Durchlauf, den niemand angestoßen hat."""
        leer = Path(tempfile.mkdtemp())
        try:
            (leer / "2023").mkdir()
            (leer / "2023/a.jpg").write_bytes(b"x")
            html = seiten.raster(Bestandsliste(leer), [], seite=1,
                                 je_seite=120, jahr=None, album=None,
                                 zusatz="")
            self.assertNotIn("schlagwort=", html)
        finally:
            shutil.rmtree(leer, ignore_errors=True)


@unittest.skipUnless(
    __import__("importlib").util.find_spec("PySide6"), "PySide6 fehlt")
class DasFensterZeigtSie(unittest.TestCase):
    def test_der_kasten_erscheint_nur_mit_schlagwoertern(self) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from wolkenernte.fenster.hauptfenster import Hauptfenster

        app = QApplication.instance() or QApplication([])
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "2023").mkdir()
            (tmp / "2023/a.jpg").write_bytes(b"x")
            fenster = Hauptfenster(tmp)
            # Der Kasten steht immer im Objekt, aber nicht in der Leiste.
            self.assertIsNone(fenster.schlagwortwahl.currentData())
            fenster.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        del app


if __name__ == "__main__":
    unittest.main()

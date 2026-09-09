"""Bilder und Videos zwischen zwei Daten finden.

Zwei Dinge lassen sich hier leicht falsch machen, und beide fallen im
Alltag nur als »das eine Bild fehlt« auf:

**Der Bis-Tag muss dazugehören.** ``bild.zeit`` trägt eine Uhrzeit; ein
Vergleich gegen den Zeitpunkt statt gegen den Tag wirft den gesamten
letzten Tag heraus.

**Eine unvollständige Angabe meint einen Zeitraum.** ``2024`` als
Untergrenze ist der 1. Januar, dasselbe ``2024`` als Obergrenze der
31. Dezember – nicht ebenfalls der 1. Januar.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from wolkenernte.bestandsliste import (
    VIDEOS,
    Bestandsliste,
    Bild,
    zeitraum_lesen,
)


class EinDatumLesen(unittest.TestCase):
    def test_deutsch_mit_punkten(self) -> None:
        self.assertEqual(zeitraum_lesen("31.12.2024"), date(2024, 12, 31))
        self.assertEqual(zeitraum_lesen("1.6.2024"), date(2024, 6, 1))

    def test_nach_iso(self) -> None:
        self.assertEqual(zeitraum_lesen("2024-12-31"), date(2024, 12, 31))
        self.assertEqual(zeitraum_lesen("2024-6-1"), date(2024, 6, 1))

    def test_leerzeichen_stoeren_nicht(self) -> None:
        self.assertEqual(zeitraum_lesen("  31.12.2024 "), date(2024, 12, 31))

    def test_leer_heisst_keine_grenze(self) -> None:
        self.assertIsNone(zeitraum_lesen(""))
        self.assertIsNone(zeitraum_lesen("   "))
        self.assertIsNone(zeitraum_lesen("", ende=True))


class UnvollstaendigMeintEinenZeitraum(unittest.TestCase):
    """**Der Kern der Sache.** Dieselbe Eingabe, zwei Ergebnisse."""

    def test_ein_jahr(self) -> None:
        self.assertEqual(zeitraum_lesen("2024"), date(2024, 1, 1))
        self.assertEqual(zeitraum_lesen("2024", ende=True), date(2024, 12, 31))

    def test_ein_monat(self) -> None:
        self.assertEqual(zeitraum_lesen("06.2024"), date(2024, 6, 1))
        self.assertEqual(zeitraum_lesen("06.2024", ende=True),
                         date(2024, 6, 30))
        self.assertEqual(zeitraum_lesen("2024-06", ende=True),
                         date(2024, 6, 30))

    def test_der_februar_wird_gerechnet_nicht_geraten(self) -> None:
        """28 oder 29 – ein fest eingetragener Wert läge alle vier Jahre
        daneben, und zwar genau am 29. Februar."""
        self.assertEqual(zeitraum_lesen("02.2024", ende=True),
                         date(2024, 2, 29))
        self.assertEqual(zeitraum_lesen("02.2023", ende=True),
                         date(2023, 2, 28))
        self.assertEqual(zeitraum_lesen("02.2100", ende=True),
                         date(2100, 2, 28))


class WasNichtGelesenWerdenKann(unittest.TestCase):
    """Wirft, statt die Grenze stillschweigend fallen zu lassen.

    Sonst zeigte die Oberfläche den ganzen Bestand, und niemand wüsste,
    dass der Zeitraum nie gegolten hat.
    """

    def test_kein_datum(self) -> None:
        for unsinn in ("gestern", "vorletzte Woche", "12/31/2024", "31-12-2024"):
            with self.subTest(unsinn), self.assertRaises(ValueError):
                zeitraum_lesen(unsinn)

    def test_zweistellige_jahreszahl_wird_abgelehnt(self) -> None:
        """``06.24`` wäre nicht von »Juni 2024« zu unterscheiden."""
        with self.assertRaises(ValueError):
            zeitraum_lesen("01.06.24")

    def test_den_tag_gibt_es_nicht(self) -> None:
        for unmoeglich in ("31.02.2024", "30.02.2024", "2023-02-29"):
            with self.subTest(unmoeglich), self.assertRaises(ValueError):
                zeitraum_lesen(unmoeglich)

    def test_den_monat_gibt_es_nicht(self) -> None:
        for unmoeglich in ("01.13.2024", "13.2024", "2024-00"):
            with self.subTest(unmoeglich), self.assertRaises(ValueError):
                zeitraum_lesen(unmoeglich)

    def test_die_meldung_nennt_das_erwartete(self) -> None:
        with self.assertRaises(ValueError) as fehler:
            zeitraum_lesen("gestern")
        self.assertIn("31.12.2024", str(fehler.exception))


def _bild(pfad: str, zeit: datetime, *, bekannt: bool = True) -> Bild:
    # ``ist_video`` setzt sonst der Scanner anhand der Endung; wer es
    # hier vergisst, bekommt einen Test, der still das Falsche prüft.
    return Bild(pfad=pfad, groesse=1000, zeit=zeit, datum_bekannt=bekannt,
                ist_video=Path(pfad).suffix.lower() in VIDEOS)


class Bestandsprobe(unittest.TestCase):
    """Ein kleiner Bestand, dessen Daten genau um die Grenzen liegen."""

    def setUp(self) -> None:
        self.archiv = Path(tempfile.mkdtemp())
        self.liste = Bestandsliste.__new__(Bestandsliste)
        self.liste.archiv = self.archiv
        self.liste.bilder = [
            _bild("a.jpg", datetime(2024, 5, 31, 23, 59)),
            _bild("b.jpg", datetime(2024, 6, 1, 0, 0)),
            _bild("c.mp4", datetime(2024, 6, 15, 12, 0)),
            _bild("d.jpg", datetime(2024, 6, 30, 23, 59)),
            _bild("e.jpg", datetime(2024, 7, 1, 0, 1)),
            _bild("ohne.jpg", datetime(2026, 9, 9, 8, 0), bekannt=False),
        ]

    def _namen(self, **grenzen) -> list[str]:
        return [b.pfad for b in self.liste.auswahl(**grenzen)]


class DerFilter(Bestandsprobe):
    def test_der_letzte_tag_gehoert_dazu(self) -> None:
        """**Die Falle.** ``d.jpg`` liegt am 30. Juni um 23:59 – gegen
        den Zeitpunkt verglichen fiele es heraus, gegen den Tag nicht.
        """
        self.assertIn("d.jpg", self._namen(von=date(2024, 6, 1),
                                           bis=date(2024, 6, 30)))

    def test_der_erste_tag_auch(self) -> None:
        self.assertIn("b.jpg", self._namen(von=date(2024, 6, 1),
                                           bis=date(2024, 6, 30)))

    def test_und_die_nachbarn_nicht(self) -> None:
        drin = self._namen(von=date(2024, 6, 1), bis=date(2024, 6, 30))
        self.assertEqual(drin, ["b.jpg", "c.mp4", "d.jpg"])

    def test_bilder_und_videos_gleichermassen(self) -> None:
        """Gefragt war nach beidem – der Filter kennt den Unterschied
        gar nicht, und dieser Test hält das fest."""
        self.assertIn("c.mp4", self._namen(von=date(2024, 6, 1),
                                           bis=date(2024, 6, 30)))

    def test_nur_eine_grenze(self) -> None:
        self.assertEqual(self._namen(von=date(2024, 7, 1)), ["e.jpg"])
        self.assertEqual(self._namen(bis=date(2024, 5, 31)), ["a.jpg"])

    def test_ohne_bekanntes_datum_faellt_heraus(self) -> None:
        """Deren Zeitstempel ist der Zeitpunkt der Übernahme. Sie in
        einen Zeitraum zu rechnen hieße, eine Zahl als Aufnahmedatum
        auszugeben, die keines ist."""
        alle = self._namen(von=date(2000, 1, 1), bis=date(2030, 12, 31))
        self.assertNotIn("ohne.jpg", alle)
        self.assertEqual(len(alle), 5)

    def test_vertauschte_grenzen_finden_nichts(self) -> None:
        self.assertEqual(self._namen(von=date(2024, 7, 1),
                                     bis=date(2024, 6, 1)), [])

    def test_ohne_grenzen_bleibt_alles(self) -> None:
        self.assertEqual(len(self.liste.auswahl()), 6)

    def test_zusammen_mit_einem_anderen_filter(self) -> None:
        self.assertEqual(
            self._namen(von=date(2024, 6, 1), bis=date(2024, 6, 30),
                        nur_videos=True), ["c.mp4"])


class VomTextBisZumTreffer(Bestandsprobe):
    """Der ganze Weg, wie ihn die Oberfläche geht."""

    def test_ein_jahr_findet_das_ganze_jahr(self) -> None:
        alle = self._namen(von=zeitraum_lesen("2024"),
                           bis=zeitraum_lesen("2024", ende=True))
        self.assertEqual(len(alle), 5)

    def test_ein_monat_findet_den_ganzen_monat(self) -> None:
        self.assertEqual(
            self._namen(von=zeitraum_lesen("06.2024"),
                        bis=zeitraum_lesen("06.2024", ende=True)),
            ["b.jpg", "c.mp4", "d.jpg"])


if __name__ == "__main__":
    unittest.main()

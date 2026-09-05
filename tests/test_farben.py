"""Kontraste. Für ein Programm, das Bilder zeigt, keine Nebensache.

Die Werte stammen aus WCAG 2.1: 4,5 für Fließtext, 3,0 für große
Schrift und Bedienelemente.
"""

from __future__ import annotations

import unittest

from wolkenernte import farben


class DieFarbenSindGueltig(unittest.TestCase):
    def test_alle_farben_sind_sechsstellige_hexwerte(self) -> None:
        for name in dir(farben):
            wert = getattr(farben, name)
            if name.isupper() and isinstance(wert, str):
                with self.subTest(name):
                    self.assertRegex(wert, r"^#[0-9a-f]{6}$")


class DieKontrasteReichen(unittest.TestCase):
    def test_fliesstext_auf_hellem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.GRAU, farben.GRAU_PAPIER), 4.5
        )

    def test_leiser_text_auf_hellem_grund(self) -> None:
        """GRAU_MITTE taugt hier nicht – es erreicht auf GRAU_PAPIER nur
        2,48. Genau deshalb gibt es GRAU_LEISE."""
        self.assertGreaterEqual(
            farben.kontrast(farben.GRAU_LEISE, farben.GRAU_PAPIER), 4.5
        )
        self.assertLess(
            farben.kontrast(farben.GRAU_MITTE, farben.GRAU_PAPIER), 4.5
        )

    def test_ueberschriften_auf_hellem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.GRAU_DUNKEL, farben.GRAU_PAPIER), 4.5
        )

    def test_text_auf_dunklem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.GRAU_HELL, farben.GRAU_NACHT), 4.5
        )

    def test_leiser_text_auf_dunklem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.GRAU_MITTE, farben.GRAU_NACHT), 4.5
        )

    def test_verweise_auf_dunklem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.BLAU_LEUCHT, farben.GRAU_NACHT), 4.5
        )

    def test_weiss_auf_der_leitfarbe(self) -> None:
        """Die Schrift auf blauen Knöpfen."""
        self.assertGreaterEqual(farben.kontrast(farben.WEISS, farben.BLAU), 4.5)

    def test_weiss_auf_beiden_enden_des_icon_verlaufs(self) -> None:
        """Das Programmsymbol ist weiß auf dem Verlauf. Am hellen oberen
        Ende ist der Kontrast am knappsten – dort steht die Wolke."""
        for farbe in farben.ICON_VERLAUF:
            with self.subTest(farbe):
                self.assertGreaterEqual(farben.kontrast(farben.WEISS, farbe), 3.0)

    def test_fehlerrot_auf_hellem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.ROT, farben.GRAU_PAPIER), 4.5
        )

    def test_fehlerrot_auf_dunklem_grund(self) -> None:
        self.assertGreaterEqual(
            farben.kontrast(farben.ROT_HELL, farben.GRAU_NACHT), 4.5
        )


class DieRechnungStimmt(unittest.TestCase):
    def test_gleiche_farben_haben_kontrast_eins(self) -> None:
        self.assertAlmostEqual(farben.kontrast("#1668e3", "#1668e3"), 1.0)

    def test_schwarz_auf_weiss_ist_das_hoechste(self) -> None:
        self.assertAlmostEqual(farben.kontrast("#000000", "#ffffff"), 21.0, places=1)

    def test_die_reihenfolge_ist_gleichgueltig(self) -> None:
        self.assertAlmostEqual(
            farben.kontrast(farben.WEISS, farben.BLAU),
            farben.kontrast(farben.BLAU, farben.WEISS),
        )


if __name__ == "__main__":
    unittest.main()

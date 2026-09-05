"""Dieselbe Aufnahme von bloß ähnlichen Bildern unterscheiden."""

from __future__ import annotations

import unittest

from wolkenernte.doppelgaenger import einstufen, namensstamm


class DerNamensstamm(unittest.TestCase):
    def test_klammerzusatz_faellt_weg(self) -> None:
        self.assertEqual(namensstamm("IMG_20210110_113920(1).jpg"),
                         namensstamm("IMG_20210110_113920.jpg"))

    def test_bearbeitungsanhaengsel_fallen_weg(self) -> None:
        self.assertEqual(namensstamm("IMG_20220711_210932-EFFECTS-bearbeitet.jpg"),
                         namensstamm("IMG_20220711_210932.jpg"))

    def test_tilde_nummer_faellt_weg(self) -> None:
        self.assertEqual(namensstamm("IMG_20260403_081244079_HDR~2.jpg"),
                         namensstamm("IMG_20260403_081244079_HDR.jpg"))

    def test_zeitstempel_bleiben_erhalten(self) -> None:
        """Der Fehler, der beinahe alles zunichtegemacht hätte.

        Ein erster Regex entfernte ``_\\d+`` mit beliebig vielen
        Ziffern. Aus ``IMG_20210110_113920(1).jpg`` wurde damit der
        Stamm ``img`` – und jedes Kamerabild hätte denselben gehabt.
        Die ganze Einstufung wäre wertlos gewesen.
        """
        self.assertEqual(namensstamm("IMG_20210110_113920.jpg"),
                         "img_20210110_113920")
        self.assertNotEqual(namensstamm("IMG_20210110_113920.jpg"),
                            namensstamm("IMG_20220505_101010.jpg"))

    def test_verschiedene_seriennummern_bleiben_verschieden(self) -> None:
        self.assertNotEqual(namensstamm("DSC02565.JPG"),
                            namensstamm("DSC02566.JPG"))

    def test_ordner_stoert_nicht(self) -> None:
        self.assertEqual(namensstamm("2023/2023-07/IMG_1234.jpg"),
                         namensstamm("ohne-datum/IMG_1234.jpg"))

    def test_grossschreibung_egal(self) -> None:
        self.assertEqual(namensstamm("DSC_1234.JPG"), namensstamm("dsc_1234.jpg"))


class DieEinstufung(unittest.TestCase):
    def test_gleicher_stamm_heisst_dieselbe_aufnahme(self) -> None:
        self.assertEqual(
            einstufen(["a/IMG_20210110_113920.jpg",
                       "a/IMG_20210110_113920(1).jpg"]),
            "dieselbe Aufnahme",
        )

    def test_serienaufnahme_ist_nur_aehnlich(self) -> None:
        """Fünfmal dasselbe Motiv im Sekundenabstand sieht für den
        Fingerabdruck gleich aus – es sind aber fünf Augenblicke."""
        self.assertEqual(
            einstufen(["DSC02565.JPG", "DSC02566.JPG", "DSC02567.JPG"]),
            "ähnlich",
        )

    def test_einzelnes_bild(self) -> None:
        self.assertEqual(einstufen(["a.jpg"]), "dieselbe Aufnahme")

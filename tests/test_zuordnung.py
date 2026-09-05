"""Bild und Metadatendatei zusammenbringen – ohne falsche Paare.

Die Beispiele stammen aus den Regeln, die GooglePhotosTakeoutHelper und
immich-go aus echten Archiven abgeleitet haben. Belege in
``docs/takeout.md``.
"""

from __future__ import annotations

import unittest

from wolkenernte.zuordnung import (
    HOECHSTLAENGE,
    json_kandidaten,
    ohne_bearbeitet,
    zuordnen,
)


class DieKandidaten(unittest.TestCase):
    def test_neue_form_kommt_zuerst(self) -> None:
        """Seit Ende 2024 die Regel – also der erste Versuch."""
        self.assertEqual(
            json_kandidaten("IMG_1234.jpg")[0],
            "IMG_1234.jpg.supplemental-metadata.json",
        )

    def test_alte_form_ist_dabei(self) -> None:
        self.assertIn("IMG_1234.jpg.json", json_kandidaten("IMG_1234.jpg"))

    def test_kein_kandidat_ist_zu_lang(self) -> None:
        """Googles Grenze gilt für jeden erzeugten Namen."""
        for name in ("IMG_1234.jpg", "a" * 30 + ".jpg", "b" * 60 + ".jpg"):
            for kandidat in json_kandidaten(name):
                with self.subTest(kandidat):
                    self.assertLessEqual(len(kandidat), HOECHSTLAENGE)

    def test_langer_name_bekommt_ein_gekuerztes_suffix(self) -> None:
        """Bei einem langen Bildnamen bleibt vom Suffix nur ein Rest.

        Für ``Ein ziemlich langer Dateiname 2024.jpg`` passt das volle
        ``.supplemental-metadata.json`` nicht mehr in 51 Zeichen; übrig
        bleibt ``.supplem.json``. Genau so kürzt Google auch.
        """
        kandidaten = json_kandidaten("Ein ziemlich langer Dateiname 2024.jpg")
        gekuerzt = [k for k in kandidaten if ".suppl" in k]
        self.assertTrue(gekuerzt, kandidaten)
        # Gekürzt heißt: kürzer als das volle Suffix, aber noch erkennbar.
        for kandidat in gekuerzt:
            with self.subTest(kandidat):
                self.assertNotIn("supplemental-metadata", kandidat)
                self.assertLessEqual(len(kandidat), HOECHSTLAENGE)
                # Was übrig bleibt, muss ein Anfang des vollen Suffixes sein.
                rest = kandidat.split(".")[-2]
                self.assertTrue("supplemental-metadata".startswith(rest), rest)

    def test_sehr_langer_name_wird_gestutzt(self) -> None:
        kandidaten = json_kandidaten("x" * 80 + ".jpg")
        self.assertTrue(all(len(k) <= HOECHSTLAENGE for k in kandidaten))
        self.assertTrue(any(k.endswith(".json") for k in kandidaten))

    def test_keine_wiederholungen(self) -> None:
        kandidaten = json_kandidaten("IMG_1234.jpg")
        self.assertEqual(len(kandidaten), len(set(kandidaten)))


class DieKlammerFalle(unittest.TestCase):
    """Beim Bild steht die Nummer vor der Endung, bei der JSON dahinter.

    Zu ``IMG_1234(1).jpg`` gehört ``IMG_1234.jpg(1).json``. Wer das
    übersieht, findet für jedes Duplikat keine Metadaten.
    """

    def test_nummer_wandert_hinter_die_endung(self) -> None:
        self.assertIn("IMG_1234.jpg(1).json", json_kandidaten("IMG_1234(1).jpg"))

    def test_auch_die_form_mit_nummer_am_ende(self) -> None:
        self.assertIn(
            "IMG_1234.jpg.supplemental-metadata(1).json",
            json_kandidaten("IMG_1234(1).jpg"),
        )

    def test_nur_die_letzte_klammer_wandert(self) -> None:
        """``Bild(3).(2)(3).jpg`` darf nicht zerlegt werden."""
        kandidaten = json_kandidaten("Bild(3).(2)(3).jpg")
        self.assertTrue(any(k.endswith("(3).json") for k in kandidaten), kandidaten)

    def test_ohne_klammer_keine_verrenkung(self) -> None:
        for kandidat in json_kandidaten("IMG_1234.jpg"):
            self.assertNotIn("(", kandidat)


class BearbeiteteFassungen(unittest.TestCase):
    def test_deutsches_anhaengsel(self) -> None:
        self.assertEqual(ohne_bearbeitet("IMG_1234-bearbeitet.jpg"), "IMG_1234.jpg")

    def test_englisches_anhaengsel(self) -> None:
        self.assertEqual(ohne_bearbeitet("IMG_1234-edited.jpg"), "IMG_1234.jpg")

    def test_immer_englische_anhaengsel(self) -> None:
        """``-effects`` und Verwandte bleiben englisch, auch auf Deutsch."""
        self.assertEqual(ohne_bearbeitet("IMG_1234-effects.jpg"), "IMG_1234.jpg")

    def test_mit_nummer_dahinter(self) -> None:
        self.assertEqual(ohne_bearbeitet("IMG-bearbeitet(1).jpg"), "IMG.jpg")

    def test_gewoehnlicher_name_bleibt_unangetastet(self) -> None:
        self.assertIsNone(ohne_bearbeitet("IMG_1234.jpg"))

    def test_abgeschnittene_reste_werden_nicht_geraten(self) -> None:
        """``Foto-b.jpg`` ist eine echte Datei, keine bearbeitete Fassung.

        GPTH probiert Reste ab zwei Zeichen und schreibt sie um. Für ein
        Programm, das den Bestand nur anzeigt, ist das zu übergriffig.
        """
        self.assertIsNone(ohne_bearbeitet("Foto-b.jpg"))
        self.assertIsNone(ohne_bearbeitet("Foto-bear.jpg"))


class DieZuordnung(unittest.TestCase):
    def test_einfacher_fall(self) -> None:
        z = zuordnen(
            ["Takeout/Fotos/IMG_1.jpg"],
            {"Takeout/Fotos/IMG_1.jpg.supplemental-metadata.json"},
        )[0]
        self.assertEqual(z.metadaten, "Takeout/Fotos/IMG_1.jpg.supplemental-metadata.json")
        self.assertTrue(z.sicher)

    def test_alte_form(self) -> None:
        z = zuordnen(["a/IMG_1.jpg"], {"a/IMG_1.jpg.json"})[0]
        self.assertEqual(z.metadaten, "a/IMG_1.jpg.json")
        self.assertTrue(z.sicher)

    def test_duplikat_mit_verschobener_klammer(self) -> None:
        z = zuordnen(["a/IMG_1(1).jpg"], {"a/IMG_1.jpg(1).json"})[0]
        self.assertEqual(z.metadaten, "a/IMG_1.jpg(1).json")
        self.assertTrue(z.sicher)

    def test_bearbeitete_fassung_gilt_als_unsicher(self) -> None:
        """Der wichtigste Test dieser Datei.

        Die Metadaten des Originals beschreiben nicht zwingend die
        bearbeitete Fassung. Titel ja, Aufnahmedatum und Ort nicht - und
        genau daran sind andere Werkzeuge gescheitert, mit Ortsangaben
        hunderte Kilometer daneben.
        """
        z = zuordnen(["a/IMG_1-bearbeitet.jpg"], {"a/IMG_1.jpg.json"})[0]
        self.assertEqual(z.metadaten, "a/IMG_1.jpg.json")
        self.assertFalse(z.sicher)

    def test_nichts_gefunden_ist_auch_unsicher(self) -> None:
        z = zuordnen(["a/IMG_1.jpg"], set())[0]
        self.assertIsNone(z.metadaten)
        self.assertFalse(z.sicher)

    def test_nur_im_selben_ordner(self) -> None:
        """Eine gleichnamige JSON in einem anderen Album gehört nicht dazu."""
        z = zuordnen(["a/IMG_1.jpg"], {"b/IMG_1.jpg.json"})[0]
        self.assertIsNone(z.metadaten)

    def test_ohne_ordner(self) -> None:
        z = zuordnen(["IMG_1.jpg"], {"IMG_1.jpg.json"})[0]
        self.assertEqual(z.metadaten, "IMG_1.jpg.json")

    def test_jedes_bild_bekommt_genau_einen_eintrag(self) -> None:
        medien = ["a/1.jpg", "a/2.jpg", "a/3.jpg"]
        self.assertEqual(len(zuordnen(medien, {"a/2.jpg.json"})), 3)


if __name__ == "__main__":
    unittest.main()

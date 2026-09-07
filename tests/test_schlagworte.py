"""Schlagwörter ohne Bilderkennung."""

from __future__ import annotations

import unittest
from datetime import datetime

from wolkenernte.schlagworte import (
    HOECHSTENS,
    Schlagwort,
    aus_angaben,
    begrenzen,
    form,
    herkunft,
    jahreszeit,
    tageszeit,
)


class DieJahreszeit(unittest.TestCase):
    def test_die_vier(self) -> None:
        for monat, erwartet in [(1, "Winter"), (4, "Frühling"),
                                (7, "Sommer"), (10, "Herbst")]:
            with self.subTest(monat):
                self.assertEqual(jahreszeit(datetime(2024, monat, 15)), erwartet)

    def test_dezember_ist_winter(self) -> None:
        """Meteorologisch, nicht astronomisch – niemand sucht Fotos vom
        20. Dezember im Herbst."""
        self.assertEqual(jahreszeit(datetime(2024, 12, 1)), "Winter")


class DieTageszeit(unittest.TestCase):
    def test_nacht(self) -> None:
        self.assertEqual(tageszeit(datetime(2024, 6, 1, 23)), "Nachtaufnahme")
        self.assertEqual(tageszeit(datetime(2024, 6, 1, 3)), "Nachtaufnahme")

    def test_frueh_und_abends(self) -> None:
        self.assertEqual(tageszeit(datetime(2024, 6, 1, 6)), "Frühmorgens")
        self.assertEqual(tageszeit(datetime(2024, 6, 1, 21)), "Abends")

    def test_der_tag_bekommt_nichts(self) -> None:
        """»Nachmittag« an ein Foto zu hängen, sagt nichts."""
        for stunde in (9, 12, 15, 18):
            with self.subTest(stunde):
                self.assertIsNone(tageszeit(datetime(2024, 6, 1, stunde)))


class DieForm(unittest.TestCase):
    def test_panorama(self) -> None:
        self.assertEqual(form(6000, 2000), "Panorama")

    def test_hochformat(self) -> None:
        self.assertEqual(form(1080, 1920), "Hochformat")

    def test_quadratisch(self) -> None:
        self.assertEqual(form(1000, 1000), "Quadratisch")

    def test_gewoehnliches_querformat_bekommt_nichts(self) -> None:
        """Sonst trügen zehntausend Bilder dasselbe Wort."""
        self.assertIsNone(form(4000, 3000))
        self.assertIsNone(form(1920, 1080))

    def test_ohne_masse(self) -> None:
        self.assertIsNone(form(0, 0))


class DieHerkunft(unittest.TestCase):
    def test_bildschirmfoto(self) -> None:
        self.assertEqual(
            herkunft("Screenshot_2024-05-13-17-47-44.png"), "Bildschirmfoto")

    def test_messenger(self) -> None:
        self.assertEqual(herkunft("IMG-20240708-WA0006.jpg"), "Messenger")

    def test_bearbeitet(self) -> None:
        self.assertEqual(
            herkunft("IMG_20240816_172342-bearbeitet.jpg"), "Bearbeitet")

    def test_drohne(self) -> None:
        self.assertEqual(
            herkunft("dji_fly_20241227_165330_photo.jpg"), "Drohne")

    def test_kamera(self) -> None:
        self.assertEqual(herkunft("DSCF5198.JPG"), "Kamera")

    def test_bildschirmfoto_schlaegt_messenger(self) -> None:
        """Ein Bildschirmfoto, das über WhatsApp kam, ist zuerst ein
        Bildschirmfoto."""
        self.assertEqual(
            herkunft("Screenshot-WA0001.jpg"), "Bildschirmfoto")

    def test_unbekannter_name(self) -> None:
        self.assertIsNone(herkunft("urlaub.jpg"))


class AusDenAngaben(unittest.TestCase):
    def test_jahreszeit_und_herkunft(self) -> None:
        woerter = aus_angaben(
            name="IMG-20240708-WA0006.jpg",
            zeit=datetime(2024, 7, 8, 14),
        )
        namen = {w.name for w in woerter}
        self.assertIn("Sommer", namen)
        self.assertIn("Messenger", namen)

    def test_ohne_bekanntes_datum_keine_jahreszeit(self) -> None:
        """Bei undatierten Bildern ist der Zeitstempel der Zeitpunkt der
        Übernahme – daraus eine Jahreszeit abzuleiten wäre erfunden."""
        woerter = aus_angaben(name="x.jpg", zeit=datetime(2026, 9, 7),
                              datum_bekannt=False)
        self.assertNotIn("Herbst", {w.name for w in woerter})

    def test_video(self) -> None:
        woerter = aus_angaben(name="VID_1.mp4", ist_video=True)
        self.assertIn("Video", {w.name for w in woerter})

    def test_panorama_aus_den_massen(self) -> None:
        woerter = aus_angaben(name="x.jpg", groesse_bild=(8000, 2000))
        self.assertIn("Panorama", {w.name for w in woerter})


class DieBegrenzung(unittest.TestCase):
    def test_hoechstens_fuenf(self) -> None:
        viele = [Schlagwort(f"Wort{i}", "bild", 0.9) for i in range(12)]
        self.assertEqual(len(begrenzen(viele)), HOECHSTENS)

    def test_erkanntes_hat_vorrang(self) -> None:
        """Was im Bild zu sehen ist, beschreibt es besser als die
        Jahreszeit – und die lässt sich aus dem Datum nachrechnen, das
        ohnehin danebensteht."""
        gemischt = [
            Schlagwort("Winter", "zeit"),
            Schlagwort("Hochformat", "form"),
            Schlagwort("Berge", "bild", 0.8),
            Schlagwort("Schnee", "bild", 0.7),
            Schlagwort("Kamera", "herkunft"),
            Schlagwort("Abends", "zeit"),
        ]
        namen = [w.name for w in begrenzen(gemischt)]
        self.assertEqual(namen[:2], ["Berge", "Schnee"])
        self.assertNotIn("Abends", namen)

    def test_sicherere_zuerst(self) -> None:
        woerter = [
            Schlagwort("unsicher", "bild", 0.3),
            Schlagwort("sicher", "bild", 0.95),
        ]
        self.assertEqual(begrenzen(woerter)[0].name, "sicher")

    def test_doppelte_namen_nur_einmal(self) -> None:
        woerter = [
            Schlagwort("Winter", "zeit"),
            Schlagwort("Winter", "bild", 0.9),
        ]
        self.assertEqual(len(begrenzen(woerter)), 1)

    def test_leere_liste(self) -> None:
        self.assertEqual(begrenzen([]), [])


if __name__ == "__main__":
    unittest.main()


class KameraUndHandyBleibenGetrennt(unittest.TestCase):
    """Ein Schlagwort, das die Hälfte des Bestands trifft, hilft nicht.

    Ein erster Anlauf warf Kamera- und Handydateinamen zusammen und
    hängte »Kamera« an 8.589 von 14.767 Bildern. Wer seine Kamerabilder
    sucht, meint gerade nicht die Handyfotos.
    """

    def test_kameranamen(self) -> None:
        for name in ("DSCF5198.JPG", "DSC02566.JPG", "_MG_0624.JPG",
                     "STR06530.JPG"):
            with self.subTest(name):
                self.assertEqual(herkunft(name), "Kamera")

    def test_handynamen(self) -> None:
        for name in ("IMG_20240816_172342.jpg", "VID_20241201_121937.mp4",
                     "PXL_20230405_090123740.jpg"):
            with self.subTest(name):
                self.assertEqual(herkunft(name), "Handy")

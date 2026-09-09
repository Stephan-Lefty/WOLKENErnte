"""Schlagwörter ohne Bilderkennung."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from wolkenernte.schlagworte import (
    HOECHSTENS,
    Schlagwort,
    aus_angaben,
    begrenzen,
    form,
    herkunft,
    jahreszeit,
    ostersonntag,
    nach_dem_kalender,
    nach_der_uhr,
    tageszeit,
    uhrzeit_ist_geraten,
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


class OhneUhrzeitKeineTageszeit(unittest.TestCase):
    """Manche Aufnahmen tragen nur ein Datum.

    Google schreibt dann Mitternacht UTC in die Metadaten, und daraus
    wird beim Ernten der Dateizeitstempel. Am echten Bestand sind das
    1.465 von 14.476 Bildern – die Stunde 1 trägt 1.488 Aufnahmen, die
    Stunden 2 bis 5 zusammen nur 39. Ohne diese Prüfung bekäme jedes
    zehnte Bild »Nachtaufnahme«, und ausgerechnet die Bilder, von denen
    man am wenigsten weiß.
    """

    def test_mitternacht_utc_gilt_als_geraten(self) -> None:
        self.assertTrue(uhrzeit_ist_geraten(
            datetime(2021, 6, 1, tzinfo=timezone.utc)))

    def test_daraus_folgt_keine_tageszeit(self) -> None:
        self.assertIsNone(tageszeit(datetime(2021, 6, 1, tzinfo=timezone.utc)))

    def test_das_datum_bleibt_gueltig(self) -> None:
        """Nur die Uhrzeit fehlt – der Monat steht fest, und damit die
        Jahreszeit."""
        woerter = aus_angaben(name="x.jpg",
                              zeit=datetime(2021, 6, 1, tzinfo=timezone.utc))
        namen = {w.name for w in woerter}
        self.assertIn("Sommer", namen)
        self.assertNotIn("Nachtaufnahme", namen)

    def test_eine_sekunde_daneben_zaehlt_als_echt(self) -> None:
        """Ein Foto, das *wirklich* auf die Sekunde genau um
        Mitternacht UTC entstand, verliert sein Schlagwort. Das ist
        eines von 86.400."""
        knapp = datetime(2021, 6, 1, 0, 0, 1, tzinfo=timezone.utc)
        self.assertFalse(uhrzeit_ist_geraten(knapp))
        self.assertEqual(tageszeit(knapp), "Nachtaufnahme")

    def test_andere_zeitzone_bleibt_unberuehrt(self) -> None:
        """Geprüft wird gegen UTC, nicht gegen die Ortszeit – sonst
        träfe es je nach Zeitzone andere Bilder."""
        mez = timezone(timedelta(hours=1))
        self.assertFalse(uhrzeit_ist_geraten(
            datetime(2021, 12, 1, 0, 0, tzinfo=mez)))
        self.assertTrue(uhrzeit_ist_geraten(
            datetime(2021, 12, 1, 1, 0, tzinfo=mez)))


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


class WasDieUhrBesserWeiss(unittest.TestCase):
    """Auf- und Untergang sehen auf dem Bild gleich aus.

    Gemessen liegen die beiden Begriffe bei 0,975 auseinander – das
    Modell kann sie nicht unterscheiden, und ein Mensch könnte es am
    Bild allein auch nicht. Die Aufnahmezeit kann es.
    """

    def _wort(self, stunde: int, **rest) -> str:
        gefunden = nach_der_uhr(
            [Schlagwort("Sonnenuntergang", "bild", 0.8)],
            datetime(2024, 6, 1, stunde), **rest)
        return gefunden[0].name

    def test_morgens_wird_es_zum_aufgang(self) -> None:
        self.assertEqual(self._wort(6), "Sonnenaufgang")

    def test_abends_bleibt_es_der_untergang(self) -> None:
        self.assertEqual(self._wort(20), "Sonnenuntergang")

    def test_ohne_datum_bleibt_alles(self) -> None:
        """Lieber das häufigere Wort als ein geratenes."""
        self.assertEqual(self._wort(6, datum_bekannt=False),
                         "Sonnenuntergang")

    def test_ohne_uhrzeit_bleibt_alles(self) -> None:
        gefunden = nach_der_uhr(
            [Schlagwort("Sonnenuntergang", "bild", 0.8)],
            datetime(2024, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(gefunden[0].name, "Sonnenuntergang")

    def test_die_sicherheit_bleibt_erhalten(self) -> None:
        gefunden = nach_der_uhr(
            [Schlagwort("Sonnenuntergang", "bild", 0.83)],
            datetime(2024, 6, 1, 6))
        self.assertAlmostEqual(gefunden[0].sicherheit, 0.83)
        self.assertEqual(gefunden[0].quelle, "bild")

    def test_andere_woerter_bleiben_unberuehrt(self) -> None:
        gefunden = nach_der_uhr(
            [Schlagwort("Berge", "bild", 0.9), Schlagwort("Winter", "zeit")],
            datetime(2024, 6, 1, 6))
        self.assertEqual([w.name for w in gefunden], ["Berge", "Winter"])

    def test_ohne_zeit_kein_absturz(self) -> None:
        self.assertEqual(nach_der_uhr([], None), [])


class WasDerKalenderBesserWeiss(unittest.TestCase):
    """Ein Anlass, der zur falschen Jahreszeit auftaucht, ist keiner.

    Am echten Bestand gegen die Aufnahmedaten gehalten: »Weihnachten«
    trifft im Dezember 6,3-mal so oft wie blind geraten – das Wort
    trägt. »Ostern« trifft im April zwar 3,5-mal so oft, aber **71 %
    seiner Treffer lagen außerhalb von März und April**, und der
    zweitstärkste Monat war der Mai. Das Modell findet
    Frühlingsblumen und nennt sie Ostern.
    """

    def _bleibt(self, wort: str, wann: datetime, **rest) -> bool:
        return bool(nach_dem_kalender([Schlagwort(wort, "bild", 0.8)],
                                      wann, **rest))

    def test_ostern_zur_osterzeit(self) -> None:
        # Ostersonntag 2024 war der 31. März.
        self.assertTrue(self._bleibt("Ostern", datetime(2024, 3, 31)))
        self.assertTrue(self._bleibt("Ostern", datetime(2024, 4, 1)))

    def test_ostern_im_mai_faellt_weg(self) -> None:
        """Der zweitstärkste Monat des Wortes – und der falscheste."""
        self.assertFalse(self._bleibt("Ostern", datetime(2024, 5, 15)))

    def test_ostern_wandert_mit(self) -> None:
        """2024 war Ostern am 31. März, 2025 erst am 20. April. Ein
        festes Fenster »März und April« träfe beides zu grob."""
        self.assertTrue(self._bleibt("Ostern", datetime(2025, 4, 20)))
        self.assertFalse(self._bleibt("Ostern", datetime(2025, 3, 1)))

    def test_die_karwoche_gehoert_dazu(self) -> None:
        self.assertTrue(self._bleibt("Ostern", datetime(2024, 3, 25)))

    def test_weihnachten_im_dezember(self) -> None:
        self.assertTrue(self._bleibt("Weihnachten", datetime(2024, 12, 24)))

    def test_weihnachten_bis_dreikoenig(self) -> None:
        """Der Baum steht in vielen Wohnungen bis zum 6. Januar."""
        self.assertTrue(self._bleibt("Weihnachten", datetime(2025, 1, 6)))
        self.assertFalse(self._bleibt("Weihnachten", datetime(2025, 1, 7)))

    def test_weihnachten_im_juli_faellt_weg(self) -> None:
        self.assertFalse(self._bleibt("Weihnachten", datetime(2024, 7, 1)))

    def test_ohne_datum_bleibt_alles(self) -> None:
        """Bei 291 Bildern im Bestand ist der Zeitstempel der Zeitpunkt
        der Übernahme – daraus einen Anlass abzusprechen wäre
        erfunden."""
        self.assertTrue(self._bleibt("Ostern", datetime(2024, 8, 1),
                                     datum_bekannt=False))
        self.assertTrue(nach_dem_kalender(
            [Schlagwort("Ostern", "bild", 0.8)], None))

    def test_andere_woerter_bleiben_unberuehrt(self) -> None:
        gefunden = nach_dem_kalender(
            [Schlagwort("Berge", "bild", 0.9), Schlagwort("Sommer", "zeit")],
            datetime(2024, 7, 1))
        self.assertEqual([w.name for w in gefunden], ["Berge", "Sommer"])

    def test_es_wird_nur_weggenommen_nie_hinzugefuegt(self) -> None:
        """Dass ein Bild am 24. Dezember entstand, macht es noch nicht
        zu einem Weihnachtsbild."""
        gefunden = nach_dem_kalender([Schlagwort("Berge", "bild", 0.9)],
                                     datetime(2024, 12, 24))
        self.assertEqual([w.name for w in gefunden], ["Berge"])


class DerOstersonntag(unittest.TestCase):
    """Gegen den Kirchenkalender geprüft, nicht aus dem Gedächtnis.

    Ostern ist der erste Sonntag nach dem ersten Frühlingsvollmond und
    wandert deshalb zwischen dem 22. März und dem 25. April.
    """

    def test_bekannte_jahre(self) -> None:
        for jahr, erwartet in [(2000, "2000-04-23"), (2024, "2024-03-31"),
                               (2025, "2025-04-20"), (2026, "2026-04-05"),
                               (2027, "2027-03-28"), (2038, "2038-04-25")]:
            with self.subTest(jahr):
                self.assertEqual(ostersonntag(jahr).isoformat(), erwartet)

    def test_es_ist_immer_ein_sonntag(self) -> None:
        for jahr in range(1990, 2060):
            with self.subTest(jahr):
                self.assertEqual(ostersonntag(jahr).weekday(), 6)

    def test_immer_zwischen_dem_22_maerz_und_dem_25_april(self) -> None:
        for jahr in range(1990, 2060):
            tag = ostersonntag(jahr)
            with self.subTest(jahr):
                self.assertGreaterEqual((tag.month, tag.day), (3, 22))
                self.assertLessEqual((tag.month, tag.day), (4, 25))


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


class KameraUndHandyBleibenGetrennt(unittest.TestCase):
    """Ein Schlagwort, das die Hälfte des Bestands trifft, hilft nicht.

    Ein erster Anlauf warf Kamera- und Handydateinamen zusammen und
    hängte »Kamera« an 8.589 von 14.767 Bildern. Wer seine Kamerabilder
    sucht, meint gerade nicht die Handyfotos.
    """

    def test_kameranamen(self) -> None:
        for name in ("DSCF5198.JPG", "DSC02566.JPG", "_MG_0624.JPG",
                     "STR06530.JPG", "P1010101.JPG"):
            with self.subTest(name):
                self.assertEqual(herkunft(name), "Kamera")

    def test_umbenanntes_kamerabild(self) -> None:
        """Wer ein Bild umbenennt, hängt meist vorn etwas an – der
        Gerätename bleibt darin stehen."""
        self.assertEqual(herkunft("Urlaub-2023-DSCF5186 1.jpg"), "Kamera")

    def test_handynamen(self) -> None:
        for name in ("IMG_20240816_172342.jpg", "VID_20241201_121937.mp4",
                     "PXL_20230405_090123740.jpg", "MOV_20191208_1511234.mp4",
                     "1000016856.jpg"):
            with self.subTest(name):
                self.assertEqual(herkunft(name), "Handy")


class DieZiffernGehoerenZumMuster(unittest.TestCase):
    """Ein Muster ohne Ziffern trifft menschliche Dateinamen.

    Ein erster Anlauf suchte in der Handyliste bloß nach ``"20"`` – das
    steht in jeder Jahreszahl und in fast jeder UUID. 1.587 Bilder
    bekamen »Handy«, die keins waren.
    """

    def test_jahreszahl_im_namen_ist_kein_handy(self) -> None:
        for name in ("Kürbistag 2020  346.jpg", "Beanie_Shooting_2020 286.jpg",
                     "c282061f-76cd-40b3-8bf6-d17e16072fdd.jpg",
                     "komoot_1342055587.mp4"):
            with self.subTest(name):
                self.assertIsNone(herkunft(name))

    def test_die_drohne_behaelt_ihr_wort(self) -> None:
        """``dji_fly_20241227_…`` trägt selbst eine Zeitangabe im Namen.

        Verlangt das Drohnenmuster eine Ziffer direkt nach ``dji_``,
        greift es nicht – und das Handymuster erbt 479 Drohnenfotos.
        """
        self.assertEqual(
            herkunft("dji_fly_20241227_165330_photo.jpg"), "Drohne")


if __name__ == "__main__":
    unittest.main()

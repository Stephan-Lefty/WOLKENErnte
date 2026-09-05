"""Einen Ordner auf der Platte als Quelle lesen."""

from __future__ import annotations

import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from wolkenernte.lokal import (
    Ordner,
    _exif_zeit_lesen,
    exif_datum,
    jahr_aus_ordner,
)
from wolkenernte.takeout import TakeoutFehler


class DasJahrAusDemOrdnernamen(unittest.TestCase):
    def test_deutsch(self) -> None:
        self.assertEqual(jahr_aus_ordner("Fotos von 2023/IMG.jpg"), 2023)

    def test_englisch(self) -> None:
        self.assertEqual(jahr_aus_ordner("Photos from 2019/IMG.jpg"), 2019)

    def test_nackte_jahreszahl(self) -> None:
        self.assertEqual(jahr_aus_ordner("2021/IMG.jpg"), 2021)

    def test_der_naechste_ordner_gewinnt(self) -> None:
        """Der Ordner, in dem die Datei liegt, ist aussagekräftiger als
        ein Oberordner weiter oben."""
        self.assertEqual(jahr_aus_ordner("Fotos von 2019/Fotos von 2023/x.jpg"), 2023)

    def test_albumname_ohne_jahr(self) -> None:
        self.assertIsNone(jahr_aus_ordner("Urlaub Nordsee/IMG.jpg"))

    def test_unsinnige_zahl(self) -> None:
        self.assertIsNone(jahr_aus_ordner("Album 12/IMG.jpg"))

    def test_ohne_ordner(self) -> None:
        self.assertIsNone(jahr_aus_ordner("IMG.jpg"))

    def test_jahr_im_albumnamen(self) -> None:
        self.assertEqual(jahr_aus_ordner("Nordsee 2023/IMG.jpg"), 2023)


class DieExifZeit(unittest.TestCase):
    def test_uebliche_schreibweise(self) -> None:
        zeit = _exif_zeit_lesen("2023:07:15 12:30:45")
        assert zeit is not None
        self.assertEqual((zeit.year, zeit.month, zeit.day), (2023, 7, 15))
        self.assertEqual(zeit.tzinfo, timezone.utc)

    def test_ungestellte_uhr(self) -> None:
        """``0000:00:00`` heißt: Die Kamera kannte das Datum nicht."""
        self.assertIsNone(_exif_zeit_lesen("0000:00:00 00:00:00"))

    def test_leer(self) -> None:
        self.assertIsNone(_exif_zeit_lesen("   "))

    def test_unsinn(self) -> None:
        self.assertIsNone(_exif_zeit_lesen("neulich"))

    def test_kaputtes_bild_wirft_nicht(self) -> None:
        """Eine beschädigte Datei darf den ganzen Lauf nicht stoppen."""
        self.assertIsNone(exif_datum(b"das ist kein Bild"))

    def test_leere_datei(self) -> None:
        self.assertIsNone(exif_datum(b""))


class DerOrdnerAlsQuelle(unittest.TestCase):
    def setUp(self) -> None:
        self.wurzel = Path(tempfile.mkdtemp())
        (self.wurzel / "Fotos von 2023").mkdir()
        (self.wurzel / "Fotos von 2023/IMG_1.jpg").write_bytes(b"eins")
        (self.wurzel / "Fotos von 2023/IMG_2.jpg").write_bytes(b"zwei")
        (self.wurzel / "Album").mkdir()
        # Dieselbe Datei ein zweites Mal, wie es Alben tun.
        (self.wurzel / "Album/IMG_1.jpg").write_bytes(b"eins")
        (self.wurzel / "Album/notiz.txt").write_bytes(b"kein Bild")

    def test_findet_alle_dateien(self) -> None:
        self.assertEqual(len(Ordner(self.wurzel)), 4)

    def test_medien_lassen_beiwerk_aus(self) -> None:
        self.assertEqual(len(Ordner(self.wurzel).medien()), 3)

    def test_lesen(self) -> None:
        o = Ordner(self.wurzel)
        self.assertEqual(o.lesen("Fotos von 2023/IMG_1.jpg"), b"eins")

    def test_unbekannter_pfad(self) -> None:
        with self.assertRaises(TakeoutFehler):
            Ordner(self.wurzel).lesen("gibtsnicht.jpg")

    def test_kein_ordner(self) -> None:
        with self.assertRaises(TakeoutFehler):
            Ordner(self.wurzel / "weg")

    def test_pruefsummen_sind_anfangs_leer(self) -> None:
        """Sie zu rechnen heißt, jede Datei zu lesen – das passiert
        nicht ungefragt beim Öffnen."""
        o = Ordner(self.wurzel)
        self.assertTrue(all(e.pruefsumme == 0 for e in o))

    def test_nur_gleich_grosse_werden_gerechnet(self) -> None:
        """Was eine Größe hat, die sonst nirgends vorkommt, kann kein
        Doppelgänger sein. An einem echten Bestand fiel damit ein
        Drittel weg, bevor ein Byte gelesen wurde."""
        o = Ordner(self.wurzel)
        # "eins" und "eins" sind gleich lang, "zwei" ebenfalls (4 Bytes),
        # also werden hier alle drei Bilder gerechnet.
        gerechnet = o.pruefsummen_rechnen()
        self.assertEqual(gerechnet, 3)

    def test_eindeutige_groesse_wird_uebergangen(self) -> None:
        (self.wurzel / "Fotos von 2023/IMG_3.jpg").write_bytes(b"deutlich laenger")
        o = Ordner(self.wurzel)
        gerechnet = o.pruefsummen_rechnen()
        self.assertEqual(gerechnet, 3)  # die vierte Datei fällt heraus

    def test_zusatzgroessen_holen_dateien_zurueck(self) -> None:
        """Für den Abgleich mit einer zweiten Quelle muss auch gerechnet
        werden, wo die Größe lokal nur einmal vorkommt."""
        (self.wurzel / "Fotos von 2023/IMG_3.jpg").write_bytes(b"deutlich laenger")
        o = Ordner(self.wurzel)
        gerechnet = o.pruefsummen_rechnen(zusatzgroessen={len(b"deutlich laenger")})
        self.assertEqual(gerechnet, 4)

    def test_doppelgaenger_bekommen_dieselbe_pruefsumme(self) -> None:
        o = Ordner(self.wurzel)
        o.pruefsummen_rechnen()
        a = o.eintrag("Fotos von 2023/IMG_1.jpg")
        b = o.eintrag("Album/IMG_1.jpg")
        assert a is not None and b is not None
        self.assertEqual((a.groesse, a.pruefsumme), (b.groesse, b.pruefsumme))


if __name__ == "__main__":
    unittest.main()

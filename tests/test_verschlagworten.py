"""Der Durchlauf, der die Schlagwörter in die Datenbank schreibt.

**Ohne Modell.** Geprüft wird die Buchführung – wer drankommt, wer
übersprungen wird, was beim zweiten Lauf passiert –, nicht die
Bilderkennung; die hat ihre eigenen Tests.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wolkenernte.bestand import STUFEN, Bestand
from wolkenernte.schlagworte import HOECHSTENS, Schlagwort
from wolkenernte.verschlagworten import (
    QUELLEN,
    _bildangaben,
    fuer_ein_bild,
    verschlagworten,
)

try:
    from PIL import Image
    PILLOW = True
except ImportError:  # pragma: no cover
    PILLOW = False


def _bild(ziel: Path, breite: int = 40, hoehe: int = 30) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if PILLOW:
        Image.new("RGB", (breite, hoehe), (90, 120, 60)).save(ziel)
    else:  # pragma: no cover
        ziel.write_bytes(b"\xff\xd8\xff\xdb" + b"x" * 200)


class EinArchivMitDatenbank(unittest.TestCase):
    """Ein kleines Archiv, dessen Datenbank die Bilder schon kennt."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "archiv"
        self.namen = [
            "2021/2021-01/IMG_20210110_113920.jpg",     # Handy, Winter
            "2021/2021-07/DSCF5198.JPG",                # Kamera, Sommer
            "2021/2021-07/Screenshot_20210704.png",     # Bildschirmfoto
            "2022/2022-04/urlaub.jpg",                  # nichts am Namen
        ]
        for name in self.namen:
            _bild(self.archiv / name)
        # Ein Bild im Hochformat, damit die Bildform greift. Nicht
        # 30x60: Genau 0,5 gilt schon als Hochpanorama.
        _bild(self.archiv / "2022/2022-04/hoch.jpg", 30, 50)
        self.namen.append("2022/2022-04/hoch.jpg")

        # Die Dateizeit trägt im echten Archiv das Aufnahmedatum.
        wann = datetime(2021, 1, 10, 14, 30).timestamp()
        for name in self.namen:
            os.utime(self.archiv / name, (wann, wann))

        with Bestand(self.archiv) as bestand:
            for nummer, name in enumerate(self.namen, 1):
                bestand.bild_merken(1000 + nummer, nummer, pfad=name)
            bestand.sichern()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- Der Durchlauf -----------------------------------------------------

    def test_alle_kommen_dran(self) -> None:
        bilanz = verschlagworten(self.archiv, mit_bilderkennung=False)
        self.assertEqual(bilanz.gesehen, len(self.namen))
        self.assertEqual(bilanz.gescheitert, 0)

    def test_die_woerter_stehen_in_der_datenbank(self) -> None:
        verschlagworten(self.archiv, mit_bilderkennung=False)
        with Bestand(self.archiv) as bestand:
            kennungen = bestand.kennungen_nach_pfad()
            woerter = bestand.schlagwoerter(
                kennungen["2021/2021-01/IMG_20210110_113920.jpg"])
            namen = {name for name, _, _ in woerter}
        self.assertIn("Handy", namen)
        self.assertIn("Winter", namen)

    def test_die_herkunft_wird_mitgeschrieben(self) -> None:
        """Nur so lässt sich später eine Hälfte wiederholen, ohne die
        andere mitzureißen."""
        verschlagworten(self.archiv, mit_bilderkennung=False)
        with Bestand(self.archiv) as bestand:
            kennungen = bestand.kennungen_nach_pfad()
            woerter = bestand.schlagwoerter(
                kennungen["2021/2021-01/IMG_20210110_113920.jpg"])
        quellen = {quelle for _, quelle, _ in woerter}
        self.assertIn("herkunft", quellen)
        self.assertIn("zeit", quellen)
        self.assertTrue(quellen <= set(QUELLEN))

    def test_hoechstens_fuenf_je_bild(self) -> None:
        verschlagworten(self.archiv, mit_bilderkennung=False)
        with Bestand(self.archiv) as bestand:
            for kennung in bestand.kennungen_nach_pfad().values():
                with self.subTest(kennung):
                    self.assertLessEqual(
                        len(bestand.schlagwoerter(kennung)), HOECHSTENS)

    # -- Zweiter Lauf ------------------------------------------------------

    def test_der_zweite_lauf_ueberspringt(self) -> None:
        verschlagworten(self.archiv, mit_bilderkennung=False)
        zweitens = verschlagworten(self.archiv, mit_bilderkennung=False)
        self.assertEqual(zweitens.gesehen, 0)
        self.assertEqual(zweitens.uebersprungen, len(self.namen))

    def test_mit_alle_kommen_alle_wieder_dran(self) -> None:
        verschlagworten(self.archiv, mit_bilderkennung=False)
        zweitens = verschlagworten(self.archiv, mit_bilderkennung=False,
                                   nur_fehlende=False)
        self.assertEqual(zweitens.gesehen, len(self.namen))

    def test_ein_wortloses_bild_gilt_trotzdem_als_erledigt(self) -> None:
        """»Hat kein Wort« ist nicht dasselbe wie »war noch nie dran«.

        Ohne diese Unterscheidung liefe die halbe Stunde Bilderkennung
        bei jedem Lauf wieder über dieselben Bilder.
        """
        leer = self.archiv / "2022/2022-04/leer.jpg"
        _bild(leer, 40, 30)          # Querformat, kein sprechender Name
        os.utime(leer, (datetime(2021, 1, 10).timestamp(),) * 2)
        with Bestand(self.archiv) as bestand:
            bestand.bild_merken(9999, 9999, pfad="2022/2022-04/leer.jpg")
            bestand.sichern()

        verschlagworten(self.archiv, mit_bilderkennung=False)
        with Bestand(self.archiv) as bestand:
            kennung = bestand.kennungen_nach_pfad()["2022/2022-04/leer.jpg"]
            self.assertIn(kennung, bestand.schon_verschlagwortet("abgeleitet"))

    def test_der_lauf_ohne_modell_blockiert_den_mit_modell_nicht(self) -> None:
        """Wer erst die billige Hälfte laufen lässt und später die
        Bilderkennung, soll dabei nichts verlieren."""
        verschlagworten(self.archiv, mit_bilderkennung=False)
        with Bestand(self.archiv) as bestand:
            offen = set(bestand.kennungen_nach_pfad().values()) - \
                bestand.schon_verschlagwortet("bild")
        self.assertEqual(len(offen), len(self.namen))

    # -- Einzelne Bilder ---------------------------------------------------

    def test_ein_video_bekommt_sein_wort(self) -> None:
        from wolkenernte.bestandsliste import Bild

        video = Bild(pfad="a/VID_20210110_113920.mp4", groesse=10,
                     zeit=datetime(2021, 7, 1, 14), ist_video=True)
        namen = {w.name for w in fuer_ein_bild(video, self.archiv)}
        self.assertIn("Video", namen)
        self.assertIn("Sommer", namen)

    @unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
    def test_die_bildform_kommt_aus_der_datei(self) -> None:
        from wolkenernte.bestandsliste import Bild

        hoch = Bild(pfad="2022/2022-04/hoch.jpg", groesse=10,
                    zeit=datetime(2021, 7, 1, 14))
        namen = {w.name for w in fuer_ein_bild(hoch, self.archiv)}
        self.assertIn("Hochformat", namen)

    def test_eine_kaputte_datei_reisst_nichts_mit(self) -> None:
        kaputt = self.archiv / "2022/2022-04/kaputt.jpg"
        kaputt.write_bytes(b"das ist kein Bild")
        with Bestand(self.archiv) as bestand:
            bestand.bild_merken(5555, 5555, pfad="2022/2022-04/kaputt.jpg")
            bestand.sichern()
        bilanz = verschlagworten(self.archiv, mit_bilderkennung=False)
        # Pillow scheitert lautlos und liefert keine Maße - das ist kein
        # Fehler, das Bild bekommt nur kein Formwort.
        self.assertEqual(bilanz.gescheitert, 0)
        self.assertEqual(bilanz.gesehen, len(self.namen) + 1)


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class SchwarzweissWirdGerechnet(unittest.TestCase):
    """Die Farbsättigung sagt es genau, das Modell riet.

    An 400 echten Bildern gemessen tragen die schwarzweißen nicht
    *wenig* Farbe, sondern **gar keine** – 28 Bilder mit einer
    Sättigung von exakt 0, und ihre Dateinamen sagen unabhängig davon
    dasselbe: ``bw``, ``SW``, ``schwarzweiss``. Das Modell hängte
    »Schwarzweiß« dagegen an 11 % aller Bilder, darunter lauter
    farbige.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pruefen(self, bild: "Image.Image") -> bool:
        ziel = self.tmp / "probe.png"      # PNG: keine Kompressionsartefakte
        bild.save(ziel)
        return _bildangaben(ziel)[1]

    def test_grau_ist_farblos(self) -> None:
        grau = Image.new("RGB", (80, 80))
        for x in range(80):
            for y in range(80):
                wert = (x + y) * 255 // 158
                grau.putpixel((x, y), (wert, wert, wert))
        self.assertTrue(self._pruefen(grau))

    def test_farbe_ist_farbe(self) -> None:
        self.assertFalse(self._pruefen(Image.new("RGB", (80, 80), (200, 60, 40))))

    def test_ein_einzelnes_buntes_pixel_entscheidet_nicht(self) -> None:
        """Ein eingestempeltes Datum in Rot, ein Rest vom Rand des
        Scanners, ein Artefakt der Kompression – das darf ein
        Schwarzweißbild nicht farbig machen."""
        fast = Image.new("RGB", (80, 80), (128, 128, 128))
        fast.putpixel((0, 0), (255, 0, 0))
        self.assertTrue(self._pruefen(fast))

    def test_ein_ganzer_farbiger_streifen_entscheidet_doch(self) -> None:
        """Mehr als jedes zwanzigste Pixel – dann ist es kein
        Ausreißer mehr."""
        gemischt = Image.new("RGB", (80, 80), (128, 128, 128))
        for x in range(80):
            for y in range(10):
                gemischt.putpixel((x, y), (255, 0, 0))
        self.assertFalse(self._pruefen(gemischt))

    def test_das_wort_landet_am_bild(self) -> None:
        from wolkenernte.bestandsliste import Bild

        grau = Image.new("RGB", (60, 40), (100, 100, 100))
        (self.tmp / "a").mkdir()
        grau.save(self.tmp / "a/grau.png")
        eintrag = Bild(pfad="a/grau.png", groesse=10,
                       zeit=datetime(2021, 7, 1, 14))
        namen = {w.name for w in fuer_ein_bild(eintrag, self.tmp)}
        self.assertIn("Schwarzweiß", namen)

    def test_ein_video_wird_gar_nicht_erst_geoeffnet(self) -> None:
        from wolkenernte.bestandsliste import Bild

        video = Bild(pfad="gibtsnicht.mp4", groesse=10,
                     zeit=datetime(2021, 7, 1, 14), ist_video=True)
        namen = {w.name for w in fuer_ein_bild(video, self.tmp)}
        self.assertNotIn("Schwarzweiß", namen)


class DieStufen(unittest.TestCase):
    def test_von_wenig_nach_viel(self) -> None:
        self.assertEqual(STUFEN, ("", "abgeleitet", "bild"))

    def test_bild_schliesst_abgeleitet_ein(self) -> None:
        """Ein Lauf ohne Modell lässt die Bilder in Ruhe, die schon
        durch die Bilderkennung gelaufen sind."""
        self.assertGreater(STUFEN.index("bild"), STUFEN.index("abgeleitet"))


class DieBilanz(unittest.TestCase):
    def test_sagt_was_passiert_ist(self) -> None:
        from wolkenernte.verschlagworten import Bilanz

        text = str(Bilanz(gesehen=10, verschlagwortet=9, ohne=1,
                          aus_dem_bild=7, gescheitert=0))
        self.assertIn("9 verschlagwortet", text)
        self.assertIn("7 davon mit Bilderkennung", text)

    def test_schweigt_ueber_das_was_nicht_war(self) -> None:
        from wolkenernte.verschlagworten import Bilanz

        self.assertNotIn("gescheitert", str(Bilanz(verschlagwortet=3)))


class DerVorrangImDurchlauf(unittest.TestCase):
    def test_erkanntes_verdraengt_abgeleitetes(self) -> None:
        """Sechs Wörter, fünf Plätze – die aus dem Bild bleiben."""
        from wolkenernte.schlagworte import begrenzen

        gemischt = [
            Schlagwort("Winter", "zeit"), Schlagwort("Abends", "zeit"),
            Schlagwort("Handy", "herkunft"), Schlagwort("Hochformat", "form"),
            Schlagwort("Berge", "bild", 0.9), Schlagwort("Schnee", "bild", 0.8),
        ]
        namen = [w.name for w in begrenzen(gemischt)]
        self.assertEqual(namen[:2], ["Berge", "Schnee"])
        self.assertEqual(len(namen), HOECHSTENS)


if __name__ == "__main__":
    unittest.main()

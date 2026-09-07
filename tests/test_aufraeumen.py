"""In der Wolke löschen – der einzige Schritt ohne Rückweg.

Die Tests laufen gegen das **echte rclone** mit dem ``local``-Backend:
Es wird tatsächlich gelöscht, nur eben in einem Ordner unter ``/tmp``.
Ein nachgebauter Dienst könnte hier nichts beweisen – gerade beim
Löschen zählt, dass der Weg bis zum Ende trägt.

Ohne rclone werden sie übersprungen.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
import zlib
from pathlib import Path

from wolkenernte.anbieter import darf_loeschen
from wolkenernte.aufraeumen import (
    AufraeumFehler,
    durchgehen,
    erlaubnis_pruefen,
)
from wolkenernte.einrichten import einrichten
from wolkenernte.rclone import Dienst, fassung, finden
from wolkenernte.takeout import TakeoutFehler
from wolkenernte.wolke import Wolke

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt


def _kennung(daten: bytes) -> tuple[int, int]:
    return len(daten), zlib.crc32(daten)


class DieErlaubnisWirdVorherGeholt(unittest.TestCase):
    """Vier Bedingungen, alle vier müssen gelten – die erste ist der
    Anbieter."""

    def test_nextcloud_darf(self) -> None:
        self.assertTrue(darf_loeschen("nextcloud"))

    def test_google_fotos_darf_nicht(self) -> None:
        """Genau der Anbieter, den Stephan zuerst genannt hat – und der
        es nicht kann."""
        self.assertFalse(darf_loeschen("google-fotos"))

    def test_unbekanntes_darf_nicht(self) -> None:
        self.assertFalse(darf_loeschen("irgendwas"))


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class DieArtStehtInDerKonfiguration(unittest.TestCase):
    """Der Name eines Zugangs sagt nichts über den Anbieter.

    Daran hing ein Fehler: ``darf_loeschen()`` bekam den *Namen*
    übergeben, fand ihn in keiner Tabelle und antwortete »nein«. Sicher,
    aber unbrauchbar – es hätte sich nie irgendwo etwas aufräumen
    lassen.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.dienst = Dienst.starten(self.tmp / "konf.conf")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_die_art_kommt_von_rclone(self) -> None:
        einrichten(self.dienst, "heisst-ganz-anders", "local")
        self.assertEqual(self.dienst.art("heisst-ganz-anders"), "local")

    def test_nextcloud_wird_als_solche_erkannt(self) -> None:
        """rclone kennt nur »webdav«; erst ``vendor`` macht daraus eine
        Nextcloud – und genau die steht in unserer Tabelle."""
        einrichten(self.dienst, "wolke", "webdav", angaben={
            "url": "https://example.invalid/remote.php/dav/files/anna",
            "vendor": "nextcloud", "user": "anna", "pass": "geheim",
        })
        self.assertEqual(self.dienst.art("wolke"), "nextcloud")
        self.assertTrue(darf_loeschen(self.dienst.art("wolke")))

    def test_der_doppelpunkt_stoert_nicht(self) -> None:
        einrichten(self.dienst, "probe", "local")
        self.assertEqual(self.dienst.art("probe:"), "local")

    def test_ein_unbekannter_zugang(self) -> None:
        self.assertEqual(self.dienst.art("gibtsnicht"), "")

    def test_erlaubnis_pruefen_nennt_den_grund(self) -> None:
        with self.assertRaises(AufraeumFehler) as fehler:
            erlaubnis_pruefen(self.dienst, "gibtsnicht")
        self.assertIn("kennt rclone nicht", str(fehler.exception))

    def test_local_darf_nicht_aufgeraeumt_werden(self) -> None:
        """``local`` steht in keiner Anbietertabelle – und ein
        Programm, das den eigenen Rechner leert, war nie gemeint."""
        einrichten(self.dienst, "platte", "local")
        with self.assertRaises(AufraeumFehler):
            erlaubnis_pruefen(self.dienst, "platte")


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class DerDurchgang(unittest.TestCase):
    """Es wird wirklich gelöscht – in einem Ordner unter ``/tmp``."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")

        self.wolkenordner = self.tmp / "wolke"
        self.wolkenordner.mkdir()
        self.inhalte = {
            "IMG_1.jpg": b"das erste Bild",
            "IMG_2.jpg": b"das zweite Bild",
            "IMG_3.jpg": b"das dritte, noch nicht geerntet",
        }
        for name, daten in self.inhalte.items():
            (self.wolkenordner / name).write_bytes(daten)
        (self.wolkenordner / "notiz.txt").write_bytes(b"kein Bild")

        # Das Archiv enthält die ersten beiden - unter anderen Namen,
        # denn beim Übernehmen wird umbenannt.
        self.archiv = self.tmp / "archiv" / "2024" / "2024-05"
        self.archiv.mkdir(parents=True)
        (self.archiv / "anders-benannt.jpg").write_bytes(self.inhalte["IMG_1.jpg"])
        (self.archiv / "auch-anders.jpg").write_bytes(self.inhalte["IMG_2.jpg"])

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")
        self.wolke = Wolke(self.dienst, "probe", str(self.wolkenordner))

    def tearDown(self) -> None:
        self.wolke.schliessen()
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    @property
    def _kennungen(self) -> set[tuple[int, int]]:
        return {_kennung(self.inhalte["IMG_1.jpg"]),
                _kennung(self.inhalte["IMG_2.jpg"])}

    # -- Der Probelauf -----------------------------------------------------

    def test_ohne_wirklich_bleibt_alles_stehen(self) -> None:
        """Der Normalfall, und der, mit dem jeder anfangen sollte."""
        bilanz = durchgehen(self.tmp / "archiv", self.wolke,
                            kennungen=self._kennungen)
        self.assertEqual(bilanz.gesichert, 2)
        self.assertEqual(bilanz.fehlt, 1)
        self.assertEqual(bilanz.geloescht, 0)
        for name in self.inhalte:
            with self.subTest(name):
                self.assertTrue((self.wolkenordner / name).exists())

    def test_beiwerk_wird_gar_nicht_erst_angesehen(self) -> None:
        """Nur Bilder und Videos – eine Textdatei ist nicht unsere."""
        bilanz = durchgehen(self.tmp / "archiv", self.wolke,
                            kennungen=self._kennungen)
        self.assertEqual(bilanz.gesehen, 3)
        self.assertTrue((self.wolkenordner / "notiz.txt").exists())

    # -- Der Ernstfall -----------------------------------------------------

    def test_nur_das_nachgewiesene_verschwindet(self) -> None:
        bilanz = durchgehen(self.tmp / "archiv", self.wolke, wirklich=True,
                            kennungen=self._kennungen)
        self.assertEqual(bilanz.geloescht, 2)
        self.assertFalse((self.wolkenordner / "IMG_1.jpg").exists())
        self.assertFalse((self.wolkenordner / "IMG_2.jpg").exists())
        self.assertTrue((self.wolkenordner / "IMG_3.jpg").exists())

    def test_der_name_beweist_nichts(self) -> None:
        """Ein Bild gleichen Namens, aber anderen Inhalts bleibt
        stehen. Bilder werden beim Übernehmen umbenannt; nur Größe und
        Prüfsumme zählen.
        """
        (self.wolkenordner / "anders-benannt.jpg").write_bytes(b"ganz anderer Inhalt")
        wolke = Wolke(self.dienst, "probe", str(self.wolkenordner))
        try:
            durchgehen(self.tmp / "archiv", wolke, wirklich=True,
                       kennungen=self._kennungen)
        finally:
            wolke.schliessen()
        self.assertTrue((self.wolkenordner / "anders-benannt.jpg").exists())

    def test_gleiche_groesse_reicht_nicht(self) -> None:
        """Zwei verschiedene Bilder können gleich groß sein. Ohne die
        Prüfsumme flöge das falsche heraus."""
        daten = self.inhalte["IMG_1.jpg"]
        gleich_lang = bytes(len(daten))
        self.assertEqual(len(gleich_lang), len(daten))
        (self.wolkenordner / "IMG_4.jpg").write_bytes(gleich_lang)
        wolke = Wolke(self.dienst, "probe", str(self.wolkenordner))
        try:
            durchgehen(self.tmp / "archiv", wolke, wirklich=True,
                       kennungen=self._kennungen)
        finally:
            wolke.schliessen()
        self.assertTrue((self.wolkenordner / "IMG_4.jpg").exists())

    def test_das_verzeichnis_wird_nachgefuehrt(self) -> None:
        """Sonst zeigte ein zweiter Durchgang Dateien, die es nicht
        mehr gibt."""
        durchgehen(self.tmp / "archiv", self.wolke, wirklich=True,
                   kennungen=self._kennungen)
        self.assertNotIn("IMG_1.jpg", self.wolke)
        zweitens = durchgehen(self.tmp / "archiv", self.wolke,
                              kennungen=self._kennungen)
        self.assertEqual(zweitens.gesehen, 1)

    def test_die_bilanz_zaehlt_das_freie(self) -> None:
        bilanz = durchgehen(self.tmp / "archiv", self.wolke, wirklich=True,
                            kennungen=self._kennungen)
        erwartet = len(self.inhalte["IMG_1.jpg"]) + len(self.inhalte["IMG_2.jpg"])
        self.assertEqual(bilanz.bytes_frei, erwartet)

    # -- Was nicht passieren darf ------------------------------------------

    def test_ein_leeres_archiv_bricht_ab(self) -> None:
        """Der gefährlichste denkbare Fall: Wer zuerst aufräumt und
        dann erntet, hätte sonst alles verloren."""
        leer = self.tmp / "leeres-archiv"
        leer.mkdir()
        with self.assertRaises(AufraeumFehler) as fehler:
            durchgehen(leer, self.wolke, wirklich=True)
        self.assertIn("kein einziges Bild", str(fehler.exception))
        for name in self.inhalte:
            with self.subTest(name):
                self.assertTrue((self.wolkenordner / name).exists())

    def test_eine_unbekannte_datei_laesst_sich_nicht_loeschen(self) -> None:
        with self.assertRaises(TakeoutFehler):
            self.wolke.loeschen("gibtsnicht.jpg")

    def test_der_fortschritt_wird_gemeldet(self) -> None:
        gesehen: list[tuple[int, int, str]] = []
        durchgehen(self.tmp / "archiv", self.wolke,
                   kennungen=self._kennungen,
                   fortschritt=lambda n, g, p: gesehen.append((n, g, p)))
        self.assertEqual(len(gesehen), 3)
        self.assertEqual(gesehen[-1][0], 3)

    def test_jedes_urteil_wird_festgehalten(self) -> None:
        """Damit die Oberfläche zeigen kann, was warum stehenbleibt."""
        bilanz = durchgehen(self.tmp / "archiv", self.wolke,
                            kennungen=self._kennungen)
        offen = [u for u in bilanz.urteile if not u.gesichert]
        self.assertEqual([u.pfad for u in offen], ["IMG_3.jpg"])
        self.assertTrue(offen[0].grund)


if __name__ == "__main__":
    unittest.main()

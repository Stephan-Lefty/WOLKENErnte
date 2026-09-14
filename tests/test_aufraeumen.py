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

    def test_nur_vorschaubilder_ist_auch_leer(self) -> None:
        """**Die Notbremse darf nicht auf den eigenen Zwischenspeicher
        hereinfallen.**

        In ``.wolkenernte/vorschau/`` liegen JPEG-Dateien, und für ein
        ``rglob("*")`` sehen die aus wie Fotos. Ein Archiv, aus dem die
        Bilder verschwunden sind und in dem nur noch der
        Zwischenspeicher steht, gälte damit als gefüllt – und in der
        Cloud würde gelöscht. Der Zwischenspeicher ist jederzeit neu zu
        rechnen; er ist kein Bestand.
        """
        leer = self.tmp / "nur-zwischenspeicher"
        (leer / ".wolkenernte" / "vorschau" / "ab").mkdir(parents=True)
        (leer / ".wolkenernte" / "vorschau" / "ab" / "abcd.jpg").write_bytes(
            b"sieht aus wie ein Bild")
        with self.assertRaises(AufraeumFehler) as fehler:
            durchgehen(leer, self.wolke, wirklich=True)
        self.assertIn("kein einziges Bild", str(fehler.exception))
        for name in self.inhalte:
            with self.subTest(name):
                self.assertTrue((self.wolkenordner / name).exists())

    def test_noch_nichts_geerntet_ist_kein_fehler(self) -> None:
        """**Nur Auskunft, kein Abbruch.**

        Ein Ordner, dessen Bilder noch gar nicht geerntet wurden, ist
        ein völlig normaler Befund: nichts gesichert, alles bleibt
        stehen. Ein erster Anlauf machte daraus einen Fehler, weil er
        »keine passende Größe gefunden« mit »Archiv leer«
        verwechselte.
        """
        anderes = self.tmp / "anderes-archiv" / "2024"
        anderes.mkdir(parents=True)
        (anderes / "fremd.jpg").write_bytes(b"etwas ganz anderes")

        bilanz = durchgehen(self.tmp / "anderes-archiv", self.wolke)
        self.assertEqual(bilanz.gesichert, 0)
        self.assertEqual(bilanz.fehlt, 3)
        for name in self.inhalte:
            with self.subTest(name):
                self.assertTrue((self.wolkenordner / name).exists())

    def test_die_vorbereitung_wird_gemeldet(self) -> None:
        """Ohne diese Meldung sah es aus wie ein Absturz: Bei 15.662
        Bildern rechnete das Programm fünf Minuten ohne Lebenszeichen."""
        gesehen: list[tuple[int, int]] = []
        durchgehen(self.tmp / "archiv", self.wolke,
                   vorbereitung=lambda n, g: gesehen.append((n, g)))
        self.assertTrue(gesehen)

    def test_nur_die_passenden_groessen_werden_gerechnet(self) -> None:
        """Der Unterschied zwischen Sekunden und Minuten.

        Eine Archivdatei anderer Größe kann keine der Clouddateien
        sein; sie zu lesen wäre reine Zeitverschwendung.
        """
        # Ein großes Bild ins Archiv, das es drüben nicht gibt.
        (self.tmp / "archiv" / "2024" / "2024-05" / "riesig.jpg").write_bytes(
            b"x" * 5000)
        gesehen: list[tuple[int, int]] = []
        durchgehen(self.tmp / "archiv", self.wolke,
                   vorbereitung=lambda n, g: gesehen.append((n, g)))
        # Zwei Archivdateien passen der Größe nach, die dritte nicht.
        self.assertEqual(gesehen[-1][1], 2)

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


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class DieLeerenOrdner(unittest.TestCase):
    """Was nach dem Löschen an leeren Ordnern zurückbleibt.

    **Der Anlass, am echten Bestand:** Nach dem ersten scharfen Lauf
    waren die elf Bilder aus ``GuideOS:Photos/TEST`` weg – der Ordner
    stand leer da. Dateien löschte das Programm, Ordner nie.

    Gelöscht wird nur mit ``--leere-ordner``, denn Ordner sind eine
    andere Art von Löschen: In einem kann liegen, was WOLKENErnte
    absichtlich nie anfasst – Schriftstücke, Musik, Sonstiges.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.wolkenordner = self.tmp / "wolke" / "TEST"
        (self.wolkenordner / "Screenshot").mkdir(parents=True)
        (self.wolkenordner / "Papiere").mkdir(parents=True)

        self.bild = b"ein Bild, das auch im Archiv liegt"
        (self.wolkenordner / "Screenshot" / "IMG_1.jpg").write_bytes(self.bild)
        (self.wolkenordner / "Papiere" / "rechnung.pdf").write_bytes(
            b"%PDF-1.4 kein Bild")

        self.archiv = self.tmp / "archiv" / "2024"
        self.archiv.mkdir(parents=True)
        (self.archiv / "anders.jpg").write_bytes(self.bild)

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _laufen(self, **werte):
        with Wolke(self.dienst, "probe", str(self.wolkenordner)) as wolke:
            return durchgehen(self.tmp / "archiv", wolke, **werte)

    def test_ohne_schalter_bleiben_die_ordner_stehen(self) -> None:
        """Der Zustand, der die Frage ausgelöst hat."""
        self._laufen(wirklich=True)
        self.assertTrue((self.wolkenordner / "Screenshot").is_dir())

    def test_mit_schalter_geht_der_leere_ordner_weg(self) -> None:
        bilanz = self._laufen(wirklich=True, leere_ordner=True)
        self.assertFalse((self.wolkenordner / "Screenshot").exists())
        self.assertGreaterEqual(bilanz.ordner_weg, 1)

    def test_ein_ordner_mit_einem_schriftstueck_bleibt(self) -> None:
        """**Die eigentliche Sicherung.** In ``Papiere`` liegt ein PDF,
        das WOLKENErnte nie anfasst. rclone lehnt ``rmdir`` auf einen
        nicht leeren Ordner ab – deshalb kann er gar nicht
        verschwinden, ohne dass das Programm selbst zählen müsste."""
        self._laufen(wirklich=True, leere_ordner=True)
        self.assertTrue((self.wolkenordner / "Papiere" / "rechnung.pdf").is_file())
        self.assertTrue((self.wolkenordner / "Papiere").is_dir())

    def test_und_deshalb_bleibt_auch_die_wurzel(self) -> None:
        """Solange ein Kind steht, kann der Elternordner nicht weg."""
        self._laufen(wirklich=True, leere_ordner=True)
        self.assertTrue(self.wolkenordner.is_dir())

    def test_ein_ganz_leerer_baum_verschwindet_samt_wurzel(self) -> None:
        """**Der Fall aus der Wirklichkeit.**

        Wer schon einmal ohne den Schalter aufgeräumt hat, steht vor
        leeren Ordnern – und dann gibt es **keine Datei mehr**, aus
        deren Pfad sich ein Ordnername ableiten ließe. Genau so war es
        am echten Bestand: elf Bilder gelöscht, der TEST-Ordner leer
        und trotzdem da.

        Ein erster Anlauf leitete die Ordnerliste aus den Dateipfaden
        ab und fand deshalb nichts zu tun – lautlos. Jetzt wird rclone
        selbst nach den Ordnern gefragt.
        """
        (self.wolkenordner / "Papiere" / "rechnung.pdf").unlink()
        (self.wolkenordner / "Screenshot" / "IMG_1.jpg").unlink()
        # Ab hier steht genau das da, was Stephan vor sich hatte: ein
        # Baum aus leeren Ordnern, kein einziges Bild mehr.

        bilanz = self._laufen(wirklich=True, leere_ordner=True)
        self.assertEqual(bilanz.gesehen, 0)
        self.assertFalse(self.wolkenordner.exists(),
                         "der leere Baum muss samt Wurzel verschwinden")
        self.assertGreaterEqual(bilanz.ordner_weg, 3)

    def test_ohne_wirklich_wird_kein_ordner_angefasst(self) -> None:
        """Der Probelauf bleibt ein Probelauf."""
        self._laufen(leere_ordner=True)
        self.assertTrue((self.wolkenordner / "Screenshot").is_dir())

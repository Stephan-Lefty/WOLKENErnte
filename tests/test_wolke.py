"""Eine Wolke als Quelle.

Die Tests laufen gegen das **echte rclone** mit dem ``local``-Backend.
Das braucht keine Zugangsdaten, geht aber denselben Weg wie jede echte
Wolke: über den Dienst, über ``operations/list`` und
``operations/copyfile``. Damit lässt sich der ganze Ablauf durchspielen,
statt ihn zu behaupten.

Ohne rclone werden sie übersprungen.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from wolkenernte.archiv import uebernehmen
from wolkenernte.einrichten import einrichten
from wolkenernte.ernten import ist_wolke, quelle_oeffnen
from wolkenernte.metadaten import Angaben
from wolkenernte.rclone import Dienst, fassung, finden
from wolkenernte.takeout import TakeoutFehler
from wolkenernte.wolke import Wolke
from wolkenernte.zuordnung import zuordnen

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt

MAI = Angaben(aufgenommen=datetime(2024, 5, 1, tzinfo=timezone.utc))


class WolkeOderPfad(unittest.TestCase):
    """rclones Schreibweise: ``zugang:pfad``.

    Ein Doppelpunkt vor dem ersten Schrägstrich – so unterscheidet
    rclone es selbst.
    """

    def test_zugang_ohne_pfad(self) -> None:
        self.assertTrue(ist_wolke("meinewolke:"))

    def test_zugang_mit_pfad(self) -> None:
        self.assertTrue(ist_wolke("meinewolke:Fotos/2024"))

    def test_gewoehnlicher_pfad(self) -> None:
        self.assertFalse(ist_wolke("/mnt/raid/Bilder"))
        self.assertFalse(ist_wolke("~/Downloads"))
        self.assertFalse(ist_wolke("takeout-probe"))

    def test_windows_laufwerk_ist_keine_wolke(self) -> None:
        """Ein Laufwerksbuchstabe hat nur ein Zeichen, ein Zugangsname
        mehr."""
        self.assertFalse(ist_wolke("C:"))
        self.assertFalse(ist_wolke("D:/Bilder"))

    def test_doppelpunkt_erst_nach_dem_schraegstrich(self) -> None:
        """``bilder/2024:05`` ist ein Ordner, kein Zugang."""
        self.assertFalse(ist_wolke("bilder/2024:05"))


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class DieWolkeAlsQuelle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.inhalt = self.tmp / "wolke"
        (self.inhalt / "Fotos").mkdir(parents=True)
        for i in (1, 2, 3):
            (self.inhalt / "Fotos" / f"IMG_{i}.jpg").write_bytes(
                f"bild-{i}".encode())
        (self.inhalt / "Fotos" / "notiz.txt").write_bytes(b"kein Bild")

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")
        self.wolke = Wolke(self.dienst, "probe", str(self.inhalt))

    def tearDown(self) -> None:
        self.wolke.schliessen()
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_listet_rekursiv_auf(self) -> None:
        """Ein Aufruf für den ganzen Bestand, nicht einer je Ordner –
        über eine Leitung ist das der Unterschied zwischen Sekunden und
        Minuten."""
        self.assertEqual(len(self.wolke), 4)
        self.assertIn("Fotos/IMG_1.jpg", self.wolke)

    def test_medien_ohne_beiwerk(self) -> None:
        self.assertEqual(sorted(self.wolke.medien()),
                         ["Fotos/IMG_1.jpg", "Fotos/IMG_2.jpg",
                          "Fotos/IMG_3.jpg"])

    def test_groessen_stimmen(self) -> None:
        eintrag = self.wolke.eintrag("Fotos/IMG_1.jpg")
        assert eintrag is not None
        self.assertEqual(eintrag.groesse, len(b"bild-1"))

    def test_lesen_holt_den_inhalt(self) -> None:
        self.assertEqual(self.wolke.lesen("Fotos/IMG_2.jpg"), b"bild-2")

    def test_zweimal_lesen_holt_nur_einmal(self) -> None:
        erst = self.wolke.holen("Fotos/IMG_1.jpg")
        nochmal = self.wolke.holen("Fotos/IMG_1.jpg")
        self.assertEqual(erst, nochmal)

    def test_unbekannte_datei(self) -> None:
        with self.assertRaises(TakeoutFehler):
            self.wolke.lesen("gibtsnicht.jpg")

    def test_fuehrender_schraegstrich_bleibt(self) -> None:
        """Beim ``local``-Backend ist der Pfad absolut. Wer den ersten
        Schrägstrich wegschneidet, sucht ``tmp/…`` statt ``/tmp/…`` –
        rclone antwortet dann mit »directory not found«."""
        self.assertTrue(self.wolke.wurzel.startswith("probe:/"))

    def test_aufraeumen_loescht_die_ablage(self) -> None:
        self.wolke.holen("Fotos/IMG_1.jpg")
        ablage = self.wolke._ablage
        self.assertTrue(ablage.exists())
        self.wolke.schliessen()
        self.assertFalse(ablage.exists())

    def test_der_dienst_laeuft_weiter(self) -> None:
        """Eine Quelle beendet nicht den Dienst – der gehört dem
        Aufrufer und bedient womöglich weitere Zugänge."""
        self.wolke.schliessen()
        self.assertEqual(self.dienst.rufen("rc/noop", {"a": 1}), {"a": 1})


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class NurDieserOrdner(unittest.TestCase):
    """»Unterordner mitnehmen« muss auch etwas bewirken.

    **Der Haken stand in der Oberfläche und tat nichts.** ``_auflisten``
    hatte ``recurse`` fest auf ``True``; wer in einem Ordner aufräumen
    wollte, bekam alles darunter mit vorgelegt. In einer Cloud liegen
    aber nicht nur Bilder, und wer *einen* Ordner meint, meint nicht
    die zwanzig darunter.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.inhalt = self.tmp / "wolke"
        (self.inhalt / "Fotos" / "2024").mkdir(parents=True)
        (self.inhalt / "Fotos" / "oben.jpg").write_bytes(b"oben")
        (self.inhalt / "Fotos" / "2024" / "unten.jpg").write_bytes(b"unten")

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")
        self.wo = str(self.inhalt / "Fotos")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_mit_unterordnern_kommt_alles(self) -> None:
        with Wolke(self.dienst, "probe", self.wo) as wolke:
            self.assertEqual(sorted(wolke.medien()),
                             ["2024/unten.jpg", "oben.jpg"])

    def test_ohne_unterordner_nur_diese_ebene(self) -> None:
        with Wolke(self.dienst, "probe", self.wo,
                   mit_unterordnern=False) as wolke:
            self.assertEqual(wolke.medien(), ["oben.jpg"])

    def test_die_angabe_steht_am_objekt(self) -> None:
        """Die Oberfläche liest sie ab, um zu sagen, was geprüft wird."""
        with Wolke(self.dienst, "probe", self.wo,
                   mit_unterordnern=False) as wolke:
            self.assertFalse(wolke.mit_unterordnern)

    def test_quelle_oeffnen_reicht_sie_durch(self) -> None:
        quelle, _ = quelle_oeffnen(f"probe:{self.wo}", self.dienst,
                                   mit_unterordnern=False)
        try:
            self.assertEqual(quelle.medien(), ["oben.jpg"])
        finally:
            quelle.schliessen()


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class DerGanzeWeg(unittest.TestCase):
    """Aus der Wolke ins Archiv – das, wofür es das Programm gibt."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.inhalt = self.tmp / "wolke"
        self.inhalt.mkdir()
        for i in (1, 2, 3):
            (self.inhalt / f"IMG_{i}.jpg").write_bytes(f"bild-{i}".encode())
        # Derselbe Inhalt ein zweites Mal, unter anderem Namen.
        (self.inhalt / "kopie.jpg").write_bytes(b"bild-1")
        self.ziel = self.tmp / "archiv"

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ernten(self):
        with Wolke(self.dienst, "probe", str(self.inhalt)) as wolke:
            return uebernehmen(
                wolke, zuordnen(wolke.medien(), set()),
                lambda z: MAI, self.ziel,
            )

    def test_bilder_kommen_im_archiv_an(self) -> None:
        self._ernten()
        self.assertTrue((self.ziel / "2024/2024-05/IMG_1.jpg").exists())
        self.assertEqual((self.ziel / "2024/2024-05/IMG_2.jpg").read_bytes(),
                         b"bild-2")

    def test_doppelgaenger_wird_uebergangen(self) -> None:
        bilanz = self._ernten()
        self.assertEqual(bilanz.uebernommen, 3)
        self.assertEqual(bilanz.doppelt, 1)

    def test_zweiter_lauf_schreibt_nichts_neu(self) -> None:
        self._ernten()
        bilanz = self._ernten()
        self.assertEqual(bilanz.uebernommen, 0)

    def test_quelle_oeffnen_erkennt_die_wolke(self) -> None:
        quelle, art = quelle_oeffnen(f"probe:{self.inhalt}", self.dienst)
        try:
            self.assertEqual(art, "Wolkenzugang")
            self.assertEqual(len(quelle), 4)
        finally:
            quelle.schliessen()

    def test_ohne_dienst_keine_wolke(self) -> None:
        """Eine verständliche Meldung, kein Absturz."""
        with self.assertRaises(TakeoutFehler) as fehler:
            quelle_oeffnen("irgendeine:wolke", None)
        self.assertIn("rclone läuft nicht", str(fehler.exception))


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class OhnePruefsummenVomAnbieter(unittest.TestCase):
    """Nextcloud führt über WebDAV keine Hashes.

    Dann steht in ``pruefsumme`` eine 0 – **unbekannt**, nicht »null«.
    Ohne diese Unterscheidung gälten alle gleich großen Dateien als
    dasselbe Bild und flögen reihenweise als Doppelgänger heraus.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.ziel = self.tmp / "archiv"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gleich_grosse_bilder_bleiben_verschieden(self) -> None:
        from wolkenernte.takeout import Eintrag

        class OhneHashes:
            """Eine Quelle, die keine Prüfsummen kennt."""

            def __init__(self) -> None:
                self.inhalte = {"a.jpg": b"AAAA", "b.jpg": b"BBBB",
                                "c.jpg": b"AAAA"}

            def eintrag(self, pfad):
                if pfad not in self.inhalte:
                    return None
                return Eintrag(pfad=pfad, quelle=Path(pfad),
                               groesse=4, pruefsumme=0)

            def lesen(self, pfad):
                return self.inhalte[pfad]

        quelle = OhneHashes()
        bilanz = uebernehmen(
            quelle, zuordnen(list(quelle.inhalte), set()),
            lambda z: MAI, self.ziel,
        )
        # a und b sind verschieden, c ist die Kopie von a.
        self.assertEqual(bilanz.uebernommen, 2)
        self.assertEqual(bilanz.doppelt, 1)
        self.assertEqual(bilanz.gescheitert, 0)


if __name__ == "__main__":
    unittest.main()

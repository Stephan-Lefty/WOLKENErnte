"""Die Datenbank neben dem Archiv."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from wolkenernte.bestand import ORT, Bestand

JULI = datetime(2023, 7, 15, 12, 0, tzinfo=timezone.utc)


class DieDatenbank(unittest.TestCase):
    def setUp(self) -> None:
        self.archiv = Path(tempfile.mkdtemp())
        self.b = Bestand(self.archiv)

    def tearDown(self) -> None:
        self.b.schliessen()

    def test_wird_neben_dem_archiv_angelegt(self) -> None:
        self.assertTrue((self.archiv / ORT).exists())

    def test_bild_anlegen_und_wiederfinden(self) -> None:
        kennung = self.b.bild_merken(100, 42, pfad="2023/2023-07/x.jpg",
                                     aufgenommen=JULI, ort=(52.5, 13.4))
        self.assertGreater(kennung, 0)
        z = self.b.zahlen()
        self.assertEqual((z.bilder, z.mit_datum, z.mit_ort), (1, 1, 1))

    def test_derselbe_inhalt_zweimal_ergibt_ein_bild(self) -> None:
        """Verknüpft wird über Größe und Prüfsumme, nicht über den Namen –
        ein Bild kann im Archiv umbenannt worden sein."""
        a = self.b.bild_merken(100, 42, pfad="a.jpg")
        b = self.b.bild_merken(100, 42, pfad="b.jpg")
        self.assertEqual(a, b)
        self.assertEqual(self.b.zahlen().bilder, 1)

    def test_verschiedene_pruefsummen_sind_verschiedene_bilder(self) -> None:
        self.b.bild_merken(100, 42)
        self.b.bild_merken(100, 43)
        self.assertEqual(self.b.zahlen().bilder, 2)


class ErgaenzenStattUeberschreiben(unittest.TestCase):
    """Dasselbe Bild kommt aus mehreren Quellen.

    Mal ist der Ort dabei, mal nur der Titel. Ein zweiter Fund darf eine
    vorhandene Angabe nicht durch eine leere ersetzen – sonst hängt es
    vom Zufall der Reihenfolge ab, was am Ende in der Datenbank steht.
    """

    def setUp(self) -> None:
        self.b = Bestand(Path(tempfile.mkdtemp()))

    def tearDown(self) -> None:
        self.b.schliessen()

    def test_ort_bleibt_erhalten(self) -> None:
        self.b.bild_merken(100, 42, ort=(52.5, 13.4))
        self.b.bild_merken(100, 42)  # zweite Quelle, ohne Ort
        self.assertEqual(self.b.zahlen().mit_ort, 1)

    def test_ort_wird_nachgetragen(self) -> None:
        self.b.bild_merken(100, 42)
        self.b.bild_merken(100, 42, ort=(52.5, 13.4))
        self.assertEqual(self.b.zahlen().mit_ort, 1)

    def test_datum_bleibt_erhalten(self) -> None:
        self.b.bild_merken(100, 42, aufgenommen=JULI)
        self.b.bild_merken(100, 42)
        self.assertEqual(self.b.zahlen().mit_datum, 1)

    def test_titel_wird_nicht_geleert(self) -> None:
        self.b.bild_merken(100, 42, titel="Sonnenuntergang")
        self.b.bild_merken(100, 42, titel="")
        zeile = self.b.db.execute("SELECT titel FROM bild").fetchone()
        self.assertEqual(zeile[0], "Sonnenuntergang")

    def test_favorit_bleibt_gesetzt(self) -> None:
        self.b.bild_merken(100, 42, favorit=True)
        self.b.bild_merken(100, 42, favorit=False)
        self.assertEqual(self.b.zahlen().favoriten, 1)

    def test_pfad_wird_nachgetragen(self) -> None:
        self.b.bild_merken(100, 42)
        self.b.bild_merken(100, 42, pfad="2023/x.jpg")
        zeile = self.b.db.execute("SELECT pfad FROM bild").fetchone()
        self.assertEqual(zeile[0], "2023/x.jpg")


class AlbenUndFundorte(unittest.TestCase):
    def setUp(self) -> None:
        self.b = Bestand(Path(tempfile.mkdtemp()))

    def tearDown(self) -> None:
        self.b.schliessen()

    def test_ein_bild_in_mehreren_alben(self) -> None:
        """Der eigentliche Grund für diese Tabelle.

        Im Archiv liegt das Bild einmal, nach Datum einsortiert. Dass es
        zu drei Alben gehört, ergibt sich nur noch aus der Datenbank.
        """
        kennung = self.b.bild_merken(100, 42)
        for name in ("Nordsee 2023", "Mein Viertel", "Foto-Contest"):
            self.b.album_zuordnen(kennung, name)
        self.assertEqual(self.b.zahlen().alben, 3)
        self.assertEqual({n for n, _ in self.b.alben()},
                         {"Nordsee 2023", "Mein Viertel", "Foto-Contest"})

    def test_alben_zaehlen_ihre_bilder(self) -> None:
        for summe in (1, 2, 3):
            kennung = self.b.bild_merken(100, summe)
            self.b.album_zuordnen(kennung, "Urlaub")
        self.assertEqual(self.b.alben()[0], ("Urlaub", 3))

    def test_dieselbe_zuordnung_zweimal(self) -> None:
        kennung = self.b.bild_merken(100, 42)
        self.b.album_zuordnen(kennung, "Urlaub")
        self.b.album_zuordnen(kennung, "Urlaub")
        self.assertEqual(self.b.alben()[0], ("Urlaub", 1))

    def test_fundorte_werden_gesammelt(self) -> None:
        """Auch für Kopien, die nicht übernommen wurden – sonst wäre
        nicht nachvollziehbar, woher die Albumzugehörigkeit stammt."""
        kennung = self.b.bild_merken(100, 42)
        self.b.fundort_merken(kennung, "takeout", "Takeout/2023/x.jpg")
        self.b.fundort_merken(kennung, "takeout", "Takeout/Urlaub/x.jpg")
        self.assertEqual(self.b.zahlen().fundorte, 2)


class Albumerkennung(unittest.TestCase):
    """Jahresordner sind keine Alben, Googles Fächer auch nicht."""

    def setUp(self) -> None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    def test_jahresordner_ist_kein_album(self) -> None:
        from wolkenernte.erfassung import albumname
        self.assertIsNone(albumname("Fotos von 2023/IMG.jpg"))
        self.assertIsNone(albumname("Photos from 2019/IMG.jpg"))

    def test_googles_faecher_sind_keine_alben(self) -> None:
        from wolkenernte.erfassung import albumname
        for ordner in ("Archiv", "Papierkorb", "Failed Videos", "Takeout"):
            with self.subTest(ordner):
                self.assertIsNone(albumname(f"{ordner}/IMG.jpg"))

    def test_echtes_album(self) -> None:
        from wolkenernte.erfassung import albumname
        self.assertEqual(albumname("Mein Viertel/IMG.jpg"), "Mein Viertel")

    def test_album_mit_jahreszahl_bleibt_album(self) -> None:
        """»Nordsee 2023« enthält eine Jahreszahl, ist aber ein Album."""
        from wolkenernte.erfassung import albumname
        self.assertEqual(albumname("Nordsee 2023/IMG.jpg"), "Nordsee 2023")


if __name__ == "__main__":
    unittest.main()

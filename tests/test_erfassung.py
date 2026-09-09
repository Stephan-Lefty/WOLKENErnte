"""Woher ein Bild kam – auch aus einer Cloud.

**Darum gibt es diese Datei.** ``erfassen`` nahm nur Ordner entgegen;
für einen Cloudzugang gab es keinen Weg, Orte, Titel, Alben und
Fundorte in die Datenbank zu schreiben. Am echten Bestand sah man es:
Die Fundorttabelle kannte zwei Herkünfte, beide von der Platte – von
der Nextcloud stand dort nichts, obwohl Bilder von dort kamen.

**Bei einer Cloud wiegt das schwerer als bei einem Ordner auf der
Platte.** Nach dem Aufräumen ist die Cloud leer. Was hier nicht
festgehalten wurde, ist dann endgültig weg – anders als bei einem
Takeout-Archiv, das man noch einmal auspacken kann.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
import zlib
from pathlib import Path

from wolkenernte.bestand import Bestand
from wolkenernte.einrichten import einrichten
from wolkenernte.erfassung import albumname, archiv_lesen, erfassen, quellenname
from wolkenernte.rclone import Dienst, fassung, finden

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt

try:
    from PIL import Image
    PILLOW = True
except ImportError:  # pragma: no cover
    PILLOW = False


def _jpeg(farbe: tuple[int, int, int]) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (80, 60), farbe).save(puffer, format="JPEG")
    return puffer.getvalue()


class DerNameEinerQuelle(unittest.TestCase):
    """Er landet in der Datenbank und muss unterscheidbar bleiben."""

    def test_ein_ordner_heisst_wie_sein_ordner(self) -> None:
        self.assertEqual(quellenname(Path("/wo/auch/immer/Google Fotos")),
                         "Google Fotos")

    def test_eine_cloud_traegt_den_pfad_mit(self) -> None:
        """Wer aus zwei Ordnern derselben Cloud erntet, soll später
        noch sehen, aus welchem."""
        self.assertEqual(quellenname("meinewolke:Fotos"), "meinewolke:Fotos")
        self.assertNotEqual(quellenname("meinewolke:Fotos"),
                            quellenname("meinewolke:Bilder"))

    def test_der_zugangsname_darf_nicht_wegfallen(self) -> None:
        """**Der Fall, der eine erste Gegenprobe durchrutschen ließ.**

        ``Path("meinewolke:Fotos").name`` ergibt zufällig dasselbe wie
        die richtige Antwort – es steckt kein Schrägstrich darin. Erst
        bei einem Unterordner zeigt sich der Unterschied: Dort bliebe
        nur »2024« übrig, und aus welcher Cloud es kam, wäre für immer
        verloren.
        """
        self.assertEqual(quellenname("meinewolke:Fotos/2024"),
                         "meinewolke:Fotos/2024")

    def test_zwei_clouds_mit_gleichem_unterordner(self) -> None:
        """Zwei Anbieter, beide mit einem Ordner »Fotos/2024« – ohne
        den Zugangsnamen wären sie nicht auseinanderzuhalten."""
        self.assertNotEqual(quellenname("meinewolke:Fotos/2024"),
                            quellenname("Dropbox:Fotos/2024"))

    def test_die_ganze_cloud_ohne_pfad(self) -> None:
        self.assertEqual(quellenname("meinewolke:"), "meinewolke:")


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class DasArchivWirdGelesen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "2024").mkdir()
        (self.tmp / "2024" / "eins.jpg").write_bytes(_jpeg((10, 20, 30)))
        (self.tmp / "2024" / "zwei.jpg").write_bytes(_jpeg((200, 60, 40)))
        (self.tmp / "2024" / "notiz.txt").write_bytes(b"kein Bild")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_jedes_bild_mit_seinem_pfad(self) -> None:
        bekannt = archiv_lesen(self.tmp)
        self.assertEqual(sorted(bekannt.values()),
                         ["2024/eins.jpg", "2024/zwei.jpg"])

    def test_beiwerk_bleibt_draussen(self) -> None:
        self.assertEqual(len(archiv_lesen(self.tmp)), 2)

    def test_nur_die_passenden_groessen(self) -> None:
        """Über ein gewachsenes Archiv der Unterschied zwischen
        Sekunden und Minuten."""
        eine = (self.tmp / "2024" / "eins.jpg").stat().st_size
        bekannt = archiv_lesen(self.tmp, nur_groessen={eine})
        self.assertEqual(list(bekannt.values()), ["2024/eins.jpg"])

    def test_der_fortschritt_wird_gemeldet(self) -> None:
        gesehen: list[tuple[int, int]] = []
        archiv_lesen(self.tmp, lambda n, g: gesehen.append((n, g)))
        self.assertEqual(gesehen[-1], (2, 2))

    def test_der_zwischenspeicher_zaehlt_nicht_mit(self) -> None:
        """**Am echten Bestand passiert, 2026-09-09.**

        In ``.wolkenernte/vorschau/`` liegen Tausende JPEG-Dateien, und
        für ein ``rglob("*")`` sehen die aus wie Fotos. `erfassen` legte
        für 1.470 Vorschaubilder eine Datenbankzeile an. Kein Datenverlust
        – aber die Datenbank behauptete danach 16.294 Bilder, wo 14.821
        liegen, und dieselbe Verwechslung entscheidet an anderer Stelle
        darüber, ob in einer Cloud gelöscht werden darf.
        """
        vorschau = self.tmp / ".wolkenernte" / "vorschau" / "ab"
        vorschau.mkdir(parents=True)
        (vorschau / "abcdef.jpg").write_bytes(_jpeg((7, 7, 7)))
        self.assertEqual(sorted(archiv_lesen(self.tmp).values()),
                         ["2024/eins.jpg", "2024/zwei.jpg"])


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class DasArchivAlsEigeneQuelle(unittest.TestCase):
    """`erfassen` ohne Quelle – für von Hand hineingelegte Bilder.

    **Der Anlass:** Nach der Zeitreparatur am echten Bestand fielen 51
    Dateien auf, zu denen es gar keine Datenbankzeile gab. Ohne Zeile
    bekommt ein Bild kein Schlagwort und keinen Titel; die Oberfläche
    zeigt es zwar, weil das Dateisystem die Wahrheit ist, aber die
    Datenbank kennt es nicht.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        # **Jedes Bild eine eigene Farbe.** Der erste Anlauf leitete sie
        # aus der Namenslänge ab – und »eins.jpg«, »zwei.jpg« und
        # »drei.jpg« sind alle acht Zeichen lang. Die drei Dateien waren
        # byteidentisch, das Archiv kannte sie als *ein* Bild, und der
        # Test schlug fehl, ohne dass am Programm etwas falsch war.
        for nummer, (ordner, name) in enumerate((
                ("2024/2024-03", "eins.jpg"),
                ("2024/2024-03", "zwei.jpg"),
                ("ohne-datum", "drei.jpg"))):
            ziel = self.tmp / ordner
            ziel.mkdir(parents=True, exist_ok=True)
            (ziel / name).write_bytes(_jpeg((20 + nummer * 70, 60, 40)))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_jede_datei_bekommt_eine_zeile(self) -> None:
        erfassen(self.tmp, [])
        with Bestand(self.tmp) as bestand:
            pfade = {z[0] for z in bestand.db.execute("SELECT pfad FROM bild")}
        self.assertEqual(pfade, {"2024/2024-03/eins.jpg",
                                 "2024/2024-03/zwei.jpg",
                                 "ohne-datum/drei.jpg"})

    def test_ohne_datum_wird_kein_album(self) -> None:
        """**Der Fehler, der das fast unbrauchbar gemacht hätte.**

        ``albumname()`` nimmt den letzten Ordner vor der Datei. Bei
        einer echten Quelle ist das ein Albumname; im Archiv heißt der
        Ordner für Bilder ohne Aufnahmedatum ``ohne-datum`` – und der
        wäre als Album durchgegangen, mit dreihundert Bildern darin.
        Die Jahresordner fängt die Jahresprüfung ab, dieser trägt keine
        Jahreszahl und rutschte durch.
        """
        self.assertIsNone(albumname("ohne-datum/IMG_1.jpg"))
        erfassen(self.tmp, [])
        with Bestand(self.tmp) as bestand:
            self.assertEqual(bestand.alben(), [])

    def test_jahresordner_bleiben_auch_kein_album(self) -> None:
        self.assertIsNone(albumname("2024/2024-03/eins.jpg"))
        self.assertIsNone(albumname("2024/eins.jpg"))

    def test_ein_zweiter_lauf_legt_nichts_doppelt_an(self) -> None:
        erfassen(self.tmp, [])
        erfassen(self.tmp, [])
        with Bestand(self.tmp) as bestand:
            anzahl = bestand.db.execute(
                "SELECT COUNT(*) FROM bild").fetchone()[0]
        self.assertEqual(anzahl, 3)

    def test_ohne_quelle_kein_fundort(self) -> None:
        """Ein Fundort sagt, *wo das Bild ursprünglich lag*. Das Archiv
        als eigenen Fundort einzutragen wäre eine Selbstverständlichkeit
        in vierzehntausend Zeilen."""
        erfassen(self.tmp, [])
        with Bestand(self.tmp) as bestand:
            self.assertEqual(
                bestand.db.execute(
                    "SELECT COUNT(*) FROM fundort").fetchone()[0], 0)

    def test_vorhandene_angaben_bleiben_stehen(self) -> None:
        """**Die eigentliche Gefahr.** Orte, Titel und Alben stehen nur
        hier; ein Lauf ohne Quelle darf sie nicht durch Leeres
        ersetzen."""
        datei = self.tmp / "2024/2024-03/eins.jpg"
        groesse = datei.stat().st_size
        summe = zlib.crc32(datei.read_bytes())
        with Bestand(self.tmp) as bestand:
            kennung = bestand.bild_merken(
                groesse, summe, pfad="2024/2024-03/eins.jpg",
                titel="Der Steg", ort=(53.5, 8.1), favorit=True)
            bestand.album_zuordnen(kennung, "Nordsee 2023")
            bestand.sichern()

        erfassen(self.tmp, [])

        with Bestand(self.tmp) as bestand:
            titel, breite, favorit = bestand.db.execute(
                "SELECT titel, breite, favorit FROM bild WHERE pfad = ?",
                ("2024/2024-03/eins.jpg",)).fetchone()
            self.assertEqual((titel, breite, favorit), ("Der Steg", 53.5, 1))
            self.assertEqual(bestand.alben(), [("Nordsee 2023", 1)])


@unittest.skipUnless(PILLOW and ECHTES_RCLONE, "Pillow oder rclone fehlt")
class EineCloudAlsQuelle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")

        self.inhalt = self.tmp / "wolke"
        (self.inhalt / "Urlaub").mkdir(parents=True)
        self.bilder = {"a.jpg": _jpeg((10, 20, 30)),
                       "Urlaub/b.jpg": _jpeg((200, 60, 40))}
        for name, daten in self.bilder.items():
            (self.inhalt / name).write_bytes(daten)

        # Dieselben Inhalte liegen schon im Archiv, anders benannt.
        self.archiv = self.tmp / "archiv"
        (self.archiv / "2024" / "2024-05").mkdir(parents=True)
        for nummer, daten in enumerate(self.bilder.values()):
            (self.archiv / "2024" / "2024-05" / f"anders-{nummer}.jpg"
             ).write_bytes(daten)

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "alias",
                   angaben={"remote": str(self.inhalt)})

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _erfassen(self, quelle: str) -> None:
        import contextlib

        with contextlib.redirect_stdout(io.StringIO()):
            erfassen(self.archiv, [quelle], self.dienst)

    def test_die_herkunft_steht_in_der_datenbank(self) -> None:
        self._erfassen("probe:")
        with Bestand(self.archiv) as bestand:
            quellen = {q for q, in bestand.db.execute(
                "SELECT DISTINCT quelle FROM fundort")}
        self.assertEqual(quellen, {"probe:"})

    def test_der_pfad_in_der_cloud_wird_festgehalten(self) -> None:
        """Nach dem Aufräumen ist er das Einzige, was von dort übrig
        bleibt."""
        self._erfassen("probe:")
        with Bestand(self.archiv) as bestand:
            pfade = {p for p, in bestand.db.execute(
                "SELECT pfad FROM fundort")}
        self.assertEqual(pfade, {"a.jpg", "Urlaub/b.jpg"})

    def test_zwei_ordner_derselben_cloud_bleiben_unterscheidbar(self) -> None:
        self._erfassen("probe:Urlaub")
        with Bestand(self.archiv) as bestand:
            quellen = {q for q, in bestand.db.execute(
                "SELECT DISTINCT quelle FROM fundort")}
        self.assertEqual(quellen, {"probe:Urlaub"})

    def test_die_bilder_werden_dem_archiv_zugeordnet(self) -> None:
        """Über Größe und Prüfsumme, nicht über den Namen – im Archiv
        heißen sie anders."""
        self._erfassen("probe:")
        with Bestand(self.archiv) as bestand:
            pfade = {p for p, in bestand.db.execute(
                "SELECT pfad FROM bild WHERE pfad IS NOT NULL")}
        self.assertTrue(all(p.startswith("2024/") for p in pfade), pfade)


if __name__ == "__main__":
    unittest.main()

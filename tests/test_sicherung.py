"""Das Archiv auf eine zweite Platte kopieren.

**Der Punkt, um den sich alles dreht, sind die Zeitstempel.** Das
Aufnahmedatum jedes Bildes steckt in der Änderungszeit der Datei; die
Jahresordner sind nur eine Beigabe. Eine Sicherung ohne Zeitstempel ist
vollständig und trotzdem wertlos: Nach dem Zurückholen trägt jedes Bild
das Datum der Wiederherstellung, und die ganze Ordnung ist weg. Nichts
schlägt fehl dabei, nichts warnt – deshalb steht das hier an erster
Stelle.

Am echten Bestand am 2026-09-14 gemacht: 16.371 Dateien, 31,2 GB, und
alle 14.853 Zeitstempel danach einzeln nachgeprüft.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wolkenernte.sicherung import (
    SicherungFehler,
    in_worten,
    nachpruefen,
    sichern,
    voransehen,
)

#: Ein Aufnahmedatum, das weit genug zurückliegt, um von »jetzt«
#: unterscheidbar zu sein.
AUFGENOMMEN = datetime(2019, 7, 15, 14, 30).timestamp()


def _archiv(wurzel: Path) -> Path:
    """Ein kleines Archiv, so aufgebaut wie ein echtes."""
    archiv = wurzel / "Archiv"
    (archiv / "2019" / "2019-07").mkdir(parents=True)
    (archiv / "ohne-datum").mkdir(parents=True)
    (archiv / ".wolkenernte").mkdir(parents=True)

    (archiv / "2019/2019-07/IMG_1.jpg").write_bytes(b"erstes Bild")
    (archiv / "2019/2019-07/IMG_2.jpg").write_bytes(b"zweites Bild")
    (archiv / "ohne-datum/IMG_3.jpg").write_bytes(b"drittes")
    # Die Datenbank: Orte, Titel und Alben stehen nur hier.
    (archiv / ".wolkenernte/bestand.db").write_bytes(b"SQLite format 3\x00")

    for pfad in archiv.rglob("*"):
        if pfad.is_file():
            os.utime(pfad, (AUFGENOMMEN, AUFGENOMMEN))
    return archiv


class EineSicherungAnlegen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = _archiv(self.tmp)
        self.ziel = self.tmp / "Sicherung"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_alle_dateien_kommen_an(self) -> None:
        bilanz = sichern(self.archiv, self.ziel)
        self.assertEqual(bilanz.kopiert, 4)
        self.assertTrue(bilanz.geglueckt)
        self.assertEqual(
            sorted(p.name for p in self.ziel.rglob("*") if p.is_file()),
            ["IMG_1.jpg", "IMG_2.jpg", "IMG_3.jpg", "bestand.db"])

    def test_die_zeitstempel_ueberleben(self) -> None:
        """**Der wichtigste Test dieser Datei.**

        `shutil.copy` statt `copy2` wäre hier grün in jeder anderen
        Hinsicht: alle Dateien da, alle Bytes gleich – und jedes Bild
        mit dem heutigen Datum. Die Jahresordnung wäre zerstört, ohne
        dass irgendetwas fehlschlägt.
        """
        sichern(self.archiv, self.ziel)
        for pfad in self.archiv.rglob("*"):
            if not pfad.is_file():
                continue
            kopie = self.ziel / pfad.relative_to(self.archiv)
            with self.subTest(str(pfad.relative_to(self.archiv))):
                self.assertAlmostEqual(
                    kopie.stat().st_mtime, AUFGENOMMEN, delta=1)

    def test_nachpruefen_findet_nichts_zu_meckern(self) -> None:
        sichern(self.archiv, self.ziel)
        self.assertEqual(nachpruefen(self.archiv, self.ziel), [])

    def test_die_datenbank_kommt_mit(self) -> None:
        """**Ohne sie wäre es die halbe Sicherung.** Orte, Titel und
        Alben stehen nur dort – nach einem Aufräumen in der Wolke gibt
        es sie sonst nirgends mehr."""
        sichern(self.archiv, self.ziel)
        self.assertTrue((self.ziel / ".wolkenernte/bestand.db").is_file())

    def test_ein_zweiter_lauf_kopiert_nichts_mehr(self) -> None:
        sichern(self.archiv, self.ziel)
        bilanz = sichern(self.archiv, self.ziel)
        self.assertEqual(bilanz.kopiert, 0)
        self.assertEqual(bilanz.uebersprungen, 4)

    def test_ein_geaendertes_bild_wird_erneuert(self) -> None:
        sichern(self.archiv, self.ziel)
        datei = self.archiv / "2019/2019-07/IMG_1.jpg"
        datei.write_bytes(b"anderer Inhalt, andere Laenge")
        bilanz = sichern(self.archiv, self.ziel)
        self.assertEqual(bilanz.kopiert, 1)
        self.assertEqual(
            (self.ziel / "2019/2019-07/IMG_1.jpg").read_bytes(),
            b"anderer Inhalt, andere Laenge")

    def test_es_wird_nichts_geloescht(self) -> None:
        """**Absichtlich ohne `--delete`.** Wer im Archiv versehentlich
        etwas löscht, findet es in der Sicherung wieder. Der Preis ist,
        dass die Sicherung wächst – das ist die richtige Richtung für
        einen Irrtum."""
        sichern(self.archiv, self.ziel)
        (self.archiv / "2019/2019-07/IMG_2.jpg").unlink()
        sichern(self.archiv, self.ziel)
        self.assertTrue((self.ziel / "2019/2019-07/IMG_2.jpg").is_file())


class DieVorschau(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = _archiv(self.tmp)
        self.ziel = self.tmp / "Sicherung"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_beim_ersten_mal_ist_alles_neu(self) -> None:
        schau = voransehen(self.archiv, self.ziel)
        self.assertEqual(schau.dateien, 4)
        self.assertEqual(schau.neu, 4)
        self.assertEqual(schau.unveraendert, 0)
        self.assertFalse(schau.ziel_vorhanden)

    def test_danach_ist_nichts_mehr_zu_tun(self) -> None:
        sichern(self.archiv, self.ziel)
        schau = voransehen(self.archiv, self.ziel)
        self.assertEqual(schau.zu_tun, 0)
        self.assertEqual(schau.unveraendert, 4)
        self.assertIn("neuesten Stand", " ".join(in_worten(schau)))

    def test_sie_zaehlt_nur_das_zu_uebertragende(self) -> None:
        sichern(self.archiv, self.ziel)
        (self.archiv / "2019/2019-07/IMG_1.jpg").write_bytes(b"neu und anders")
        schau = voransehen(self.archiv, self.ziel)
        self.assertEqual(schau.geaendert, 1)
        self.assertEqual(schau.bytes_zu_kopieren, len(b"neu und anders"))

    def test_dieselbe_platte_wird_gesagt(self) -> None:
        """**Nicht verboten, aber gesagt.** Eine Kopie auf derselben
        Platte schützt gegen versehentliches Löschen, nicht gegen den
        Ausfall der Platte."""
        schau = voransehen(self.archiv, self.ziel)
        self.assertTrue(schau.gleiche_platte)
        self.assertIn("demselben Datenträger", " ".join(in_worten(schau)))


class WasNichtGehenDarf(unittest.TestCase):
    """Drei Ziele, die die Sicherung in sich selbst laufen ließen."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = _archiv(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ziel_gleich_archiv(self) -> None:
        with self.assertRaises(SicherungFehler):
            voransehen(self.archiv, self.archiv)

    def test_ziel_im_archiv(self) -> None:
        """**Die Falle ohne Boden.** Jede kopierte Datei taucht beim
        Durchgehen wieder auf und wird erneut kopiert – das hört erst
        auf, wenn die Platte voll ist."""
        with self.assertRaises(SicherungFehler) as gefangen:
            voransehen(self.archiv, self.archiv / "Sicherung")
        self.assertIn("endlos", str(gefangen.exception))

    def test_archiv_im_ziel(self) -> None:
        with self.assertRaises(SicherungFehler):
            voransehen(self.archiv, self.archiv.parent)

    def test_auch_ueber_einen_umweg(self) -> None:
        """``..`` und Symlinks kämen an einem naiven Vergleich vorbei –
        deshalb wird vorher aufgelöst."""
        umweg = self.archiv / "2019" / ".." / "Sicherung"
        with self.assertRaises(SicherungFehler):
            voransehen(self.archiv, umweg)

    def test_sichern_prueft_ebenfalls(self) -> None:
        """Nicht nur die Vorschau – wer `sichern` direkt ruft, darf
        nicht in die Falle laufen."""
        with self.assertRaises(SicherungFehler):
            sichern(self.archiv, self.archiv / "Sicherung")


class DerAbbruch(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = _archiv(self.tmp)
        self.ziel = self.tmp / "Sicherung"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_abbrechen_haelt_zwischen_zwei_dateien(self) -> None:
        """Nie mitten in einer – sonst läge im Ziel eine halbe."""
        gesehen = []

        def abbrechen() -> bool:
            return len(gesehen) >= 2

        bilanz = sichern(self.archiv, self.ziel,
                         melden=lambda n, g, name: gesehen.append(name),
                         abbrechen=abbrechen)
        self.assertTrue(bilanz.abgebrochen)
        self.assertFalse(bilanz.geglueckt)
        # Was kopiert wurde, ist vollständig kopiert.
        for pfad in self.ziel.rglob("*"):
            if pfad.is_file():
                quelle = self.archiv / pfad.relative_to(self.ziel)
                self.assertEqual(pfad.stat().st_size, quelle.stat().st_size)

    def test_ein_erneuter_lauf_macht_weiter(self) -> None:
        sichern(self.archiv, self.ziel, abbrechen=lambda: True)
        bilanz = sichern(self.archiv, self.ziel)
        self.assertTrue(bilanz.geglueckt)
        self.assertEqual(nachpruefen(self.archiv, self.ziel), [])


if __name__ == "__main__":
    unittest.main()

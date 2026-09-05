"""Bilder ins Archiv übernehmen – ohne Verlust und ohne Doppelgänger."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from wolkenernte.archiv import (
    OHNE_DATUM,
    datum_aus,
    uebernehmen,
    zielordner,
)
from wolkenernte.metadaten import Angaben
from wolkenernte.takeout import Archiv as Takeout
from wolkenernte.zuordnung import Zuordnung

JULI = Angaben(aufgenommen=datetime(2023, 7, 15, 12, 0, tzinfo=timezone.utc))


class DerZielordner(unittest.TestCase):
    def test_nach_jahr_und_monat(self) -> None:
        self.assertEqual(zielordner(JULI), "2023/2023-07")

    def test_ohne_datum(self) -> None:
        self.assertEqual(zielordner(Angaben()), OHNE_DATUM)
        self.assertEqual(zielordner(None), OHNE_DATUM)

    def test_monat_ist_zweistellig(self) -> None:
        januar = Angaben(aufgenommen=datetime(2023, 1, 5, tzinfo=timezone.utc))
        self.assertEqual(zielordner(januar), "2023/2023-01")

    def test_hin_und_zurueck(self) -> None:
        pfad = Path(zielordner(JULI)) / "x.jpg"
        zurueck = datum_aus(pfad)
        assert zurueck is not None
        self.assertEqual((zurueck.year, zurueck.month), (2023, 7))

    def test_ohne_datum_ergibt_nichts(self) -> None:
        self.assertIsNone(datum_aus(Path(OHNE_DATUM) / "x.jpg"))


class DieUebernahme(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.ziel = self.tmp / "archiv"
        self.zip = self.tmp / "takeout-001.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("Takeout/Google Fotos/2023/IMG_1.jpg", b"bild-eins")
            z.writestr("Takeout/Google Fotos/2023/IMG_2.jpg", b"bild-zwei")
            # Dieselbe Datei noch einmal, in einem Album.
            z.writestr("Takeout/Google Fotos/Urlaub/IMG_1.jpg", b"bild-eins")

    def _lauf(self, angaben: Angaben | None = JULI) -> tuple:
        pfade = [
            "Takeout/Google Fotos/2023/IMG_1.jpg",
            "Takeout/Google Fotos/2023/IMG_2.jpg",
            "Takeout/Google Fotos/Urlaub/IMG_1.jpg",
        ]
        with Takeout([self.zip]) as t:
            return uebernehmen(
                t, [Zuordnung(p, None) for p in pfade],
                lambda _: angaben, self.ziel,
            ), None

    def test_bilder_landen_im_datumsordner(self) -> None:
        self._lauf()
        self.assertTrue((self.ziel / "2023/2023-07/IMG_1.jpg").exists())
        self.assertTrue((self.ziel / "2023/2023-07/IMG_2.jpg").exists())

    def test_inhalt_bleibt_unveraendert(self) -> None:
        self._lauf()
        self.assertEqual(
            (self.ziel / "2023/2023-07/IMG_1.jpg").read_bytes(), b"bild-eins"
        )

    def test_doppelgaenger_wird_nur_einmal_geschrieben(self) -> None:
        """Das Album enthält dieselbe Datei ein zweites Mal.

        Bei einem echten Takeout sind das gut zwölf Prozent des
        Bestands – erkannt an Größe und Prüfsumme, ohne die Datei
        zweimal zu entpacken.
        """
        bilanz, _ = self._lauf()
        self.assertEqual(bilanz.uebernommen, 2)
        self.assertEqual(bilanz.doppelt, 1)

    def test_ohne_datum_eigener_ordner(self) -> None:
        self._lauf(Angaben())
        self.assertTrue((self.ziel / OHNE_DATUM / "IMG_1.jpg").exists())

    def test_aufnahmezeit_wird_auf_die_datei_geschrieben(self) -> None:
        """Damit die Sortierung in jedem Dateimanager stimmt."""
        self._lauf()
        pfad = self.ziel / "2023/2023-07/IMG_1.jpg"
        self.assertEqual(
            datetime.fromtimestamp(pfad.stat().st_mtime, tz=timezone.utc).date(),
            datetime(2023, 7, 15, tzinfo=timezone.utc).date(),
        )

    def test_zweiter_lauf_schreibt_nichts_neu(self) -> None:
        """Ein abgebrochener Durchlauf muss sich wiederholen lassen."""
        self._lauf()
        bilanz, _ = self._lauf()
        self.assertEqual(bilanz.uebernommen, 0)
        self.assertEqual(bilanz.uebergangen, 2)

    def test_bilanz_zaehlt_die_bytes(self) -> None:
        bilanz, _ = self._lauf()
        self.assertEqual(bilanz.bytes_geschrieben, len(b"bild-eins") + len(b"bild-zwei"))


class Namenskonflikte(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.ziel = self.tmp / "archiv"
        self.zip = self.tmp / "t.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            # Gleicher Name, verschiedener Inhalt, verschiedene Ordner.
            z.writestr("a/IMG_1.jpg", b"eins")
            z.writestr("b/IMG_1.jpg", b"zwei-anders")

    def test_beide_bleiben_erhalten(self) -> None:
        """Zwei verschiedene Bilder mit demselben Namen dürfen sich
        nicht gegenseitig überschreiben."""
        with Takeout([self.zip]) as t:
            bilanz = uebernehmen(
                t, [Zuordnung("a/IMG_1.jpg", None), Zuordnung("b/IMG_1.jpg", None)],
                lambda _: JULI, self.ziel,
            )
        self.assertEqual(bilanz.uebernommen, 2)
        ordner = self.ziel / "2023/2023-07"
        self.assertEqual(len(list(ordner.iterdir())), 2)
        inhalte = {p.read_bytes() for p in ordner.iterdir()}
        self.assertEqual(inhalte, {b"eins", b"zwei-anders"})


class Sicherheit(unittest.TestCase):
    def test_pfaddurchbruch_wird_entschaerft(self) -> None:
        """Ein Name aus einem fremden Archiv ist eine Eingabe von außen.

        ``../../../etc/x`` darf nicht aus dem Archiv herausführen.
        """
        tmp = Path(tempfile.mkdtemp())
        ziel = tmp / "archiv"
        pfad = tmp / "t.zip"
        with zipfile.ZipFile(pfad, "w") as z:
            z.writestr("../../../boesartig.jpg", b"x")

        with Takeout([pfad]) as t:
            eintraege = [e.pfad for e in t]
            uebernehmen(t, [Zuordnung(p, None) for p in eintraege],
                        lambda _: JULI, ziel)

        geschrieben = list(ziel.rglob("*.jpg"))
        self.assertEqual(len(geschrieben), 1)
        # Die Datei muss unterhalb des Archivs liegen, nicht daneben.
        self.assertTrue(geschrieben[0].resolve().is_relative_to(ziel.resolve()))
        self.assertFalse((tmp.parent / "boesartig.jpg").exists())


if __name__ == "__main__":
    unittest.main()

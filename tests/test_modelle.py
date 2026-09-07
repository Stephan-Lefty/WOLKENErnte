"""Das Modell holen, prüfen und wiederfinden.

Kein Test hier lädt 335 MB. Geprüft wird die Mechanik – Ablageort,
Prüfsumme, Abbruchverhalten – an winzigen Dateien über ``file://``.

**Warum kein eigener Webdienst?** Ein erster Anlauf startete einen
kleinen HTTP-Server im selben Prozess. Er lief für sich allein
tadellos und riss den **gesamten Testlauf** mit einem Speicherauszug
ab, sobald zuvor die Fenstertests gelaufen waren – Qt und ein
Serverfaden im selben Prozess vertragen sich nicht. ``urllib`` behandelt
``file://`` über denselben Weg wie ``http://``: dieselbe Antwort,
dieselbe ``Content-Length``, dieselben Fehler. Es wird also nichts
weniger geprüft, nur ohne Faden und ohne Netzanschluss.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from wolkenernte.modelle import (
    BILDTEIL,
    TEXTTEIL,
    Modell,
    ModellFehler,
    holen,
    ordner,
    pfad,
    pruefen,
    vorhanden,
)

INHALT = b"nicht wirklich ein Modell, aber gross genug" * 40
SUMME = hashlib.sha256(INHALT).hexdigest()


class DerAblageort(unittest.TestCase):
    def setUp(self) -> None:
        self.vorher = os.environ.pop("WOLKENERNTE_MODELLE", None)

    def tearDown(self) -> None:
        if self.vorher is not None:
            os.environ["WOLKENERNTE_MODELLE"] = self.vorher
        else:
            os.environ.pop("WOLKENERNTE_MODELLE", None)

    def test_uebersteuerbar(self) -> None:
        """Für Systemverwalter, die einmal zentral ausliefern, und für
        Rechner ohne Netz."""
        os.environ["WOLKENERNTE_MODELLE"] = "/anderswo/modelle"
        self.assertEqual(ordner(), Path("/anderswo/modelle"))

    def test_liegt_unter_dem_programmnamen(self) -> None:
        self.assertIn("WOLKENErnte", str(ordner()))

    @unittest.skipIf(sys.platform in ("win32", "darwin"), "nur unter Linux")
    def test_xdg_wird_beachtet(self) -> None:
        vorher = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = "/eigene/daten"
        try:
            self.assertEqual(ordner(), Path("/eigene/daten/WOLKENErnte/modelle"))
        finally:
            if vorher is None:
                os.environ.pop("XDG_DATA_HOME")
            else:
                os.environ["XDG_DATA_HOME"] = vorher

    def test_nicht_der_zwischenspeicher(self) -> None:
        """Der wird von Aufräumwerkzeugen geleert – und dann steht das
        Programm ohne Netz da."""
        self.assertNotIn("/.cache/", str(ordner()))


class DieAngabenZuDenModellen(unittest.TestCase):
    def test_pruefsummen_sind_vollstaendig(self) -> None:
        for modell in (BILDTEIL, TEXTTEIL):
            with self.subTest(modell.name):
                self.assertEqual(len(modell.pruefsumme), 64)
                self.assertGreater(modell.groesse, 0)

    def test_verschiedene_dateinamen(self) -> None:
        self.assertNotEqual(BILDTEIL.datei, TEXTTEIL.datei)

    def test_megabyte(self) -> None:
        self.assertEqual(BILDTEIL.megabyte, 335)


class DasHolen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.ferne = self.tmp / "ferne" / "modell.bin"
        self.ferne.parent.mkdir()
        self.ferne.write_bytes(INHALT)

        self.vorher = os.environ.get("WOLKENERNTE_MODELLE")
        os.environ["WOLKENERNTE_MODELLE"] = str(self.tmp / "ablage")
        self.modell = Modell(
            name="Probe", datei="modell.bin",
            quelle=self.ferne.as_uri(),
            pruefsumme=SUMME, groesse=len(INHALT))

    def tearDown(self) -> None:
        if self.vorher is None:
            os.environ.pop("WOLKENERNTE_MODELLE", None)
        else:
            os.environ["WOLKENERNTE_MODELLE"] = self.vorher
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_kommt_an(self) -> None:
        datei = holen(self.modell)
        self.assertEqual(datei.read_bytes(), INHALT)

    def test_fortschritt_wird_gemeldet(self) -> None:
        gesehen: list[tuple[int, int]] = []
        holen(self.modell, lambda a, b: gesehen.append((a, b)))
        self.assertTrue(gesehen)
        self.assertEqual(gesehen[-1][0], len(INHALT))

    def test_zweimal_holen_geht_nicht_ins_netz(self) -> None:
        """Kein zweiter Griff, auch nicht die Frage nach einer neueren
        Fassung – für ein Programm, das offline arbeitet, ist das der
        Knackpunkt. Nachgewiesen, indem die Quelle verschwindet."""
        holen(self.modell)
        self.ferne.unlink()
        self.assertEqual(holen(self.modell).read_bytes(), INHALT)

    def test_falsche_pruefsumme_wird_bemerkt(self) -> None:
        """easyocr führt für jedes Modell eine Prüfsumme mit und ruft
        die Prüffunktion nie auf. Eine abgebrochene Übertragung fällt
        dann erst auf, wenn das Modell Unsinn liefert."""
        falsch = Modell(name="Probe", datei="modell.bin",
                        quelle=self.modell.quelle, pruefsumme="0" * 64,
                        groesse=len(INHALT))
        with self.assertRaises(ModellFehler):
            holen(falsch)

    def test_nach_dem_fehlschlag_liegt_nichts_halbes_da(self) -> None:
        """Geschrieben wird nebenan unter ``.teil``; erst wenn die
        Prüfsumme stimmt, wird umbenannt. Sonst hielte das Programm
        einen Abbruch für eine vollständige Datei."""
        falsch = Modell(name="Probe", datei="modell.bin",
                        quelle=self.modell.quelle, pruefsumme="0" * 64,
                        groesse=len(INHALT))
        with self.assertRaises(ModellFehler):
            holen(falsch)
        self.assertIsNone(vorhanden(falsch))
        self.assertFalse(list((self.tmp / "ablage").glob("*.teil")))

    def test_ohne_netz_eine_verstaendliche_meldung(self) -> None:
        self.ferne.unlink()
        with self.assertRaises(ModellFehler) as fehler:
            holen(self.modell)
        # Der Nutzer soll sich selbst helfen können.
        self.assertIn(self.modell.quelle, str(fehler.exception))

    def test_halbe_datei_gilt_nicht_als_vorhanden(self) -> None:
        """Der häufigste Fall überhaupt: die abgebrochene Übertragung.
        Die Größe zu prüfen kostet nichts."""
        ziel = pfad(self.modell)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(INHALT[:20])
        self.assertIsNone(vorhanden(self.modell))

    def test_pruefsumme_rechnen(self) -> None:
        datei = holen(self.modell)
        self.assertEqual(pruefen(datei, self.modell), SUMME)


if __name__ == "__main__":
    unittest.main()

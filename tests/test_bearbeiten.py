"""Ein Bild an ein anderes Programm weiterreichen.

Gestartet wird hier nichts – kein Test soll GIMP öffnen. Geprüft wird,
**welcher Befehl zusammengebaut** würde und dass nur angeboten wird,
was wirklich da ist.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte import bearbeiten
from wolkenernte.bearbeiten import (
    MACOS,
    UNIX,
    BearbeitenFehler,
    Programm,
    auswahl_anbieten,
    im_dateimanager,
    oeffnen_mit,
    vorhandene,
)


class DieListe(unittest.TestCase):
    def test_nur_was_wirklich_da_ist(self) -> None:
        """Ein Menüeintrag, der beim Anklicken nichts tut, ist schlimmer
        als keiner – dieselbe Regel wie bei ``darf_loeschen()``."""
        for programm in vorhandene():
            with self.subTest(programm.name):
                if sys.platform == "darwin":
                    self.assertTrue(
                        Path(f"/Applications/{programm.befehl}.app").exists()
                        or Path(f"/System/Applications/{programm.befehl}.app"
                                ).exists())
                else:
                    self.assertIsNotNone(shutil.which(programm.befehl))

    def test_bearbeiter_stehen_vor_betrachtern(self) -> None:
        """Wer »bearbeiten« anklickt, meint GIMP, nicht den
        Bildbetrachter."""
        namen = [p.befehl for p in UNIX]
        self.assertLess(namen.index("gimp"), namen.index("gwenview"))

    def test_die_namen_sind_eindeutig(self) -> None:
        for liste in (UNIX, MACOS):
            with self.subTest(len(liste)):
                namen = [p.name for p in liste]
                self.assertEqual(sorted(namen), sorted(set(namen)))

    def test_unter_windows_gibt_es_keine_liste(self) -> None:
        """Dort führt der Weg über den Dialog des Systems – eine
        geratene Liste wäre schlimmer als gar keine."""
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(vorhandene(), [])


class WasAufgerufenWird(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.bild = self.tmp / "IMG_1.jpg"
        self.bild.write_bytes(b"bild")

    def _gerufen(self, was, *args, plattform="linux") -> list[str]:
        with mock.patch.object(sys, "platform", plattform), \
                mock.patch.object(bearbeiten, "_starten") as start:
            was(*args)
        self.assertTrue(start.called)
        return start.call_args[0][0]

    def test_das_bild_kommt_mit(self) -> None:
        befehl = self._gerufen(oeffnen_mit, self.bild, Programm("GIMP", "gimp"))
        self.assertEqual(befehl, ["gimp", str(self.bild)])

    def test_unter_macos_ueber_open(self) -> None:
        """Dort liegen Programme nicht im Suchpfad."""
        befehl = self._gerufen(oeffnen_mit, self.bild, Programm("GIMP", "GIMP"),
                               plattform="darwin")
        self.assertEqual(befehl, ["open", "-a", "GIMP", str(self.bild)])

    def test_der_auswahldialog_unter_windows(self) -> None:
        befehl = self._gerufen(auswahl_anbieten, self.bild, plattform="win32")
        self.assertIn("OpenAs_RunDLL", " ".join(befehl))

    def test_der_dateimanager_waehlt_die_datei_aus(self) -> None:
        """Nicht bloß den Ordner öffnen: Bei vierzehntausend Bildern in
        Monatsordnern hilft es wenig, irgendwo im richtigen Ordner zu
        landen."""
        befehl = self._gerufen(im_dateimanager, self.bild, plattform="win32")
        self.assertEqual(befehl, ["explorer.exe", f"/select,{self.bild}"])

    def test_der_dateimanager_unter_macos(self) -> None:
        befehl = self._gerufen(im_dateimanager, self.bild, plattform="darwin")
        self.assertEqual(befehl, ["open", "-R", str(self.bild)])

    @unittest.skipUnless(shutil.which("dbus-send"), "dbus-send fehlt")
    def test_der_dateimanager_unter_linux(self) -> None:
        befehl = self._gerufen(im_dateimanager, self.bild)
        self.assertIn("org.freedesktop.FileManager1.ShowItems", befehl)
        self.assertIn(f"array:string:{self.bild.as_uri()}", befehl)


class WennEtwasFehlt(unittest.TestCase):
    def test_ein_verschwundenes_bild(self) -> None:
        """Zwischen Anzeigen und Anklicken kann eine Datei wegkommen –
        etwa weil nebenher aufgeräumt wurde."""
        weg = Path(tempfile.mkdtemp()) / "weg.jpg"
        for was in (lambda: oeffnen_mit(weg, Programm("GIMP", "gimp")),
                    lambda: auswahl_anbieten(weg),
                    lambda: im_dateimanager(weg)):
            with self.subTest(was), self.assertRaises(BearbeitenFehler):
                was()

    def test_ein_programm_das_es_nicht_gibt(self) -> None:
        bild = Path(tempfile.mkdtemp()) / "a.jpg"
        bild.write_bytes(b"x")
        with self.assertRaises(BearbeitenFehler):
            oeffnen_mit(bild, Programm("Nix", "gibtsganzsicherhtnicht"))


class WieGestartetWird(unittest.TestCase):
    def test_es_wird_nicht_gewartet(self) -> None:
        """WOLKENErnte darf nicht stehenbleiben, solange GIMP offen
        ist."""
        with mock.patch("subprocess.Popen") as popen:
            bearbeiten._starten(["echo", "hallo"])
        self.assertTrue(popen.called)

    @unittest.skipIf(sys.platform == "win32", "gilt nur für Unix")
    def test_eine_eigene_sitzung(self) -> None:
        """Sonst stürbe der Bildbearbeiter mit WOLKENErnte – und ein
        Bearbeitungsstand mit ihm."""
        with mock.patch("subprocess.Popen") as popen:
            bearbeiten._starten(["echo", "hallo"])
        self.assertTrue(popen.call_args.kwargs["start_new_session"])


if __name__ == "__main__":
    unittest.main()

"""rclone finden, starten und ansprechen.

Gegen den Nachbau in ``fake_rclone.py``, nicht gegen das echte
Programm: Die Tests sollen überall laufen, auch ohne installiertes
rclone, und sie sollen Fälle prüfen, die sich mit dem Original nur
umständlich herstellen lassen.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte.rclone import (
    MINDESTFASSUNG,
    Dienst,
    Fassung,
    RcloneFehler,
    fassung,
    finden,
)

NACHBAU = Path(__file__).resolve().parent / "fake_rclone.py"


def _huelle(ordner: Path, *, umgebung: str = "") -> Path:
    """Ein Startskript, das sich wie rclone verhält.

    **Die Pfade gehören in Anführungszeichen.** Ohne sie scheitert alles,
    sobald ein Verzeichnis im Weg ein Leerzeichen enthält – und genau das
    ist hier der Fall. Die Fehlermeldung lautete dann »meldet keine
    Fassungsnummer« und wies auf das Programm statt auf den Test.
    """
    pfad = ordner / "rclone"
    pfad.write_text(
        f'#!/bin/sh\n{umgebung}exec "{sys.executable}" "{NACHBAU}" "$@"\n'
    )
    pfad.chmod(pfad.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return pfad


class DieFassung(unittest.TestCase):
    def test_vergleich(self) -> None:
        self.assertTrue(Fassung(1, 75, 0) >= MINDESTFASSUNG)
        self.assertTrue(Fassung(1, 76, 0) >= MINDESTFASSUNG)
        self.assertTrue(Fassung(2, 0, 0) >= MINDESTFASSUNG)
        self.assertFalse(Fassung(1, 74, 9) >= MINDESTFASSUNG)
        self.assertFalse(Fassung(1, 69, 0) >= MINDESTFASSUNG)

    def test_lesbar(self) -> None:
        self.assertEqual(str(Fassung(1, 75, 0)), "1.75.0")

    def test_wird_ausgelesen(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.assertEqual(str(fassung(_huelle(tmp))), "1.75.0")

    def test_zu_alte_fassung_wird_erkannt(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        huelle = _huelle(tmp, umgebung="FAKE_RCLONE_VERSION=1.69.0\nexport FAKE_RCLONE_VERSION\n")
        gefunden = fassung(huelle)
        assert gefunden is not None
        self.assertFalse(gefunden.genuegt)

    def test_kein_programm(self) -> None:
        self.assertIsNone(fassung(Path("/gibt/es/nicht")))


class DasFinden(unittest.TestCase):
    def test_nimmt_was_im_pfad_liegt(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _huelle(tmp)
        with mock.patch.dict(os.environ, {"PATH": str(tmp)}):
            gefunden = finden()
        self.assertIsNotNone(gefunden)
        self.assertEqual(gefunden.name, "rclone")

    def test_nichts_da(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ, {"PATH": str(tmp)}):
            self.assertIsNone(finden())


class DerDienst(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.programm = _huelle(self.tmp)

    def test_startet_und_antwortet(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            self.assertGreater(dienst.port, 0)
            self.assertEqual(dienst.rufen("rc/noop", {"x": 1}), {"x": 1})

    def test_hoert_nur_auf_localhost(self) -> None:
        """Der Dienst gibt Zugriff auf alle Zugangsdaten – er darf das
        Gerät nicht verlassen."""
        import socket
        with Dienst.starten(programm=self.programm) as dienst:
            fremd = socket.socket()
            fremd.settimeout(1)
            with self.assertRaises((ConnectionRefusedError, OSError)):
                # Die Adresse des Rechners im Netz, nicht die Rückschleife.
                fremd.connect((socket.gethostbyname(socket.gethostname()),
                               dienst.port))
            fremd.close()

    def test_ohne_anmeldung_geht_nichts(self) -> None:
        """Der wichtigste Test dieser Datei.

        Wer die Schnittstelle unangemeldet erreicht, kann über
        ``core/command`` beliebige Befehle ausführen und über
        ``config/dump`` sämtliche Zugangsdaten auslesen.
        """
        import urllib.error
        import urllib.request

        with Dienst.starten(programm=self.programm) as dienst:
            anfrage = urllib.request.Request(
                f"http://127.0.0.1:{dienst.port}/config/listremotes",
                data=b"{}", method="POST",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as fehler:
                urllib.request.urlopen(anfrage, timeout=5)
            self.assertEqual(fehler.exception.code, 401)

    def test_kennwort_steht_nicht_in_der_kommandozeile(self) -> None:
        """Unter Linux kann jeder Benutzer ``/proc/<pid>/cmdline``
        fremder Prozesse lesen. Zugangsdaten gehören in die Umgebung."""
        with Dienst.starten(programm=self.programm) as dienst:
            kennwort = dienst._kopf
            befehl = Path(f"/proc/{dienst.prozess.pid}/cmdline")
            if not befehl.exists():
                self.skipTest("kein /proc auf diesem System")
            zeile = befehl.read_bytes().decode(errors="replace")
            self.assertNotIn("--rc-pass", zeile)
            self.assertNotIn("--rc-user", zeile)
            self.assertNotIn(kennwort, zeile)

    def test_niemals_ohne_anmeldung_starten(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            befehl = Path(f"/proc/{dienst.prozess.pid}/cmdline")
            if not befehl.exists():
                self.skipTest("kein /proc auf diesem System")
            self.assertNotIn("--rc-no-auth",
                             befehl.read_bytes().decode(errors="replace"))

    def test_remotes_auflisten(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            self.assertEqual(dienst.remotes(), ["probe:", "zweite:"])

    def test_ordner_auflisten(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            eintraege = dienst.auflisten("probe:Fotos/2024")
        self.assertEqual([e["Name"] for e in eintraege], ["IMG_1.jpg", "IMG_2.jpg"])

    def test_unbekannter_endpunkt_meldet_sich(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            with self.assertRaises(RcloneFehler):
                dienst.rufen("gibt/es/nicht")

    def test_prozess_endet_mit_dem_block(self) -> None:
        with Dienst.starten(programm=self.programm) as dienst:
            prozess = dienst.prozess
            self.assertIsNone(prozess.poll())
        self.assertIsNotNone(prozess.poll())


class WennEtwasFehlt(unittest.TestCase):
    def test_ohne_rclone_eine_verstaendliche_meldung(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ, {"PATH": str(tmp)}):
            with self.assertRaises(RcloneFehler) as fehler:
                Dienst.starten()
        self.assertIn("nicht installiert", str(fehler.exception))
        # Die Meldung soll sagen, was zu tun ist.
        self.assertIn("pacman", str(fehler.exception))

    def test_zu_alte_fassung_wird_abgewiesen(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        huelle = _huelle(
            tmp, umgebung="FAKE_RCLONE_VERSION=1.69.0\nexport FAKE_RCLONE_VERSION\n"
        )
        with self.assertRaises(RcloneFehler) as fehler:
            Dienst.starten(programm=huelle)
        self.assertIn("zu alt", str(fehler.exception))
        self.assertIn("1.75.0", str(fehler.exception))

    def test_sofortiges_ende_wird_erkannt(self) -> None:
        """Wenn rclone sich gleich beendet, soll nicht bis zur Frist
        gewartet werden – die Ausgabe sagt meist, woran es lag."""
        tmp = Path(tempfile.mkdtemp())
        huelle = _huelle(
            tmp, umgebung="FAKE_RCLONE_STIRBT=1\nexport FAKE_RCLONE_STIRBT\n"
        )
        with self.assertRaises(RcloneFehler) as fehler:
            Dienst.starten(programm=huelle, frist=10)
        self.assertIn("beendet", str(fehler.exception))


if __name__ == "__main__":
    unittest.main()

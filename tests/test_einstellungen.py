"""Das Wenige, was sich das Programm zwischen zwei Aufrufen merkt."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte import einstellungen


class DasZuletztBenutzteArchiv(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": str(self.tmp / "config")}
        )
        self.patch.start()
        self.archiv = self.tmp / "archiv"
        self.archiv.mkdir()

    def tearDown(self) -> None:
        self.patch.stop()

    def test_ohne_vermerk_nichts(self) -> None:
        self.assertIsNone(einstellungen.letztes_archiv())

    def test_merken_und_wiederfinden(self) -> None:
        einstellungen.archiv_merken(self.archiv)
        self.assertEqual(einstellungen.letztes_archiv(), self.archiv.resolve())

    def test_folgt_der_xdg_konvention(self) -> None:
        einstellungen.archiv_merken(self.archiv)
        self.assertTrue((self.tmp / "config/wolkenernte/zuletzt").exists())

    def test_geloeschter_ordner_gilt_nicht(self) -> None:
        """Ein Verweis auf einen Ordner, den es nicht mehr gibt, ist
        keine brauchbare Vorgabe, sondern eine Fehlermeldung in spe."""
        einstellungen.archiv_merken(self.archiv)
        self.archiv.rmdir()
        self.assertIsNone(einstellungen.letztes_archiv())

    def test_leere_datei(self) -> None:
        ordner = self.tmp / "config/wolkenernte"
        ordner.mkdir(parents=True)
        (ordner / "zuletzt").write_text("   \n")
        self.assertIsNone(einstellungen.letztes_archiv())

    def test_zweites_merken_ersetzt_das_erste(self) -> None:
        zweites = self.tmp / "zweites"
        zweites.mkdir()
        einstellungen.archiv_merken(self.archiv)
        einstellungen.archiv_merken(zweites)
        self.assertEqual(einstellungen.letztes_archiv(), zweites.resolve())

"""Dateigrößen in Worten.

Aufgefallen ist das an einem Bildschirmfoto: Ein frisch geerntetes
Archiv aus 45 Bildern stand in der Statuszeile als »0.0 GB« da. Nichts
schlug fehl, nichts war falsch gerechnet – die Einheit war nur um drei
Größenordnungen daneben, und ausgerechnet beim ersten Blick auf ein
neues Archiv.
"""

from __future__ import annotations

import unittest

from wolkenernte.bestandsliste import umfang


class DieEinheitPasstSichAn(unittest.TestCase):
    def test_ein_grosses_archiv_in_gigabyte(self) -> None:
        self.assertEqual(umfang(29_400_000_000), "29.4 GB")

    def test_ein_kleines_archiv_ist_nicht_null(self) -> None:
        """Der eigentliche Fehler: 5,2 Millionen Byte sind nicht nichts."""
        self.assertEqual(umfang(5_200_000), "5 MB")
        self.assertNotIn("0.0", umfang(5_200_000))

    def test_eine_einzelne_datei_in_kilobyte(self) -> None:
        self.assertEqual(umfang(184_000), "184 kB")

    def test_ein_leeres_archiv(self) -> None:
        self.assertEqual(umfang(0), "0 kB")

    def test_die_grenzen_selbst(self) -> None:
        self.assertEqual(umfang(999_999), "1000 kB")
        self.assertEqual(umfang(1_000_000), "1 MB")
        self.assertEqual(umfang(1_000_000_000), "1.0 GB")


class BeideOberflaechenBenutzenEs(unittest.TestCase):
    """Sonst driften sie auseinander – dieselbe Lehre wie bei
    ``bestandsliste`` überhaupt: Was zwei Teile brauchen, gehört
    keinem von beiden."""

    def test_im_html_steht_keine_null_gigabyte(self) -> None:
        import tempfile
        from pathlib import Path

        from wolkenernte.bestandsliste import Bestandsliste
        from wolkenernte.web import seiten

        ordner = Path(tempfile.mkdtemp())
        (ordner / "a.jpg").write_bytes(b"x" * 3_000_000)
        liste = Bestandsliste(ordner)
        html = seiten.uebersicht(liste)
        self.assertIn("3 MB", html)
        self.assertNotIn("0.0 GB", html)


if __name__ == "__main__":
    unittest.main()

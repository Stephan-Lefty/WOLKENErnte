"""Mehrere Wolken nebeneinander – ohne dass eine die andere frisst.

**Der Fehler, um den es geht.** ``config/create`` ersetzt bei rclone
einen gleichnamigen Zugang **wortlos**. Der Anmeldedialog schlug aber
immer denselben Namen vor: »meinewolke«. Wer eine zweite Nextcloud
anlegte und den Vorschlag stehen ließ, verlor damit die erste – Adresse,
Benutzername und App-Passwort, ohne eine einzige Meldung. Am echten
rclone nachgemessen: Nach dem zweiten Anlegen stand ein Zugang in der
Liste, mit den Daten des zweiten.

Aufgefallen ist es an der Bitte »WOLKENErnte sollte sich die Zugangsdaten
merken« – das tat es längst, nur überschrieb es sie.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from wolkenernte.einrichten import (
    NameVergeben,
    freier_name,
    nextcloud,
    vergeben,
)
from wolkenernte.rclone import Dienst, fassung, finden

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class ZweiNextcloudsNebeneinander(unittest.TestCase):
    """Gegen das echte rclone – das stille Überschreiben ist dessen
    Verhalten, und nur dort zeigt es sich."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.konf = self.tmp / "rclone.conf"
        self.dienst = Dienst.starten(self.konf)

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _erste(self) -> None:
        nextcloud(self.dienst, "meinewolke", "https://wolke-a.invalid",
                  "anna", "geheim-A")

    def test_der_erste_vorschlag_ist_meinewolke(self) -> None:
        self.assertEqual(freier_name(self.dienst), "meinewolke")

    def test_danach_wird_ein_freier_name_vorgeschlagen(self) -> None:
        """**Der Kern.** Vorher stand hier fest »meinewolke«, und wer
        den Vorschlag stehen ließ, überschrieb die erste Wolke."""
        self._erste()
        self.assertEqual(freier_name(self.dienst), "meinewolke-2")

    def test_und_weiter_hoch(self) -> None:
        self._erste()
        nextcloud(self.dienst, "meinewolke-2", "https://wolke-b.invalid",
                  "bert", "geheim-B")
        self.assertEqual(freier_name(self.dienst), "meinewolke-3")

    def test_ein_belegter_name_wird_abgelehnt(self) -> None:
        self._erste()
        with self.assertRaises(NameVergeben) as gefangen:
            nextcloud(self.dienst, "meinewolke", "https://wolke-b.invalid",
                      "bert", "geheim-B")
        self.assertIn("gibt es schon", str(gefangen.exception))

    def test_der_erste_zugang_bleibt_dabei_unversehrt(self) -> None:
        """Nicht nur »es wirft« – die Daten müssen auch noch da sein."""
        self._erste()
        with self.assertRaises(NameVergeben):
            nextcloud(self.dienst, "meinewolke", "https://wolke-b.invalid",
                      "bert", "geheim-B")
        werte = self.dienst.rufen("config/dump")["meinewolke"]
        self.assertIn("wolke-a.invalid", werte["url"])
        self.assertEqual(werte["user"], "anna")

    def test_zwei_wolken_stehen_nebeneinander(self) -> None:
        self._erste()
        nextcloud(self.dienst, freier_name(self.dienst),
                  "https://wolke-b.invalid", "bert", "geheim-B")
        namen = sorted(self.dienst.remotes())
        self.assertEqual(namen, ["meinewolke", "meinewolke-2"])

        gedumpt = self.dienst.rufen("config/dump")
        self.assertIn("wolke-a.invalid", gedumpt["meinewolke"]["url"])
        self.assertIn("wolke-b.invalid", gedumpt["meinewolke-2"]["url"])
        self.assertEqual(gedumpt["meinewolke"]["user"], "anna")
        self.assertEqual(gedumpt["meinewolke-2"]["user"], "bert")

    def test_ausdruecklich_ersetzen_geht_weiterhin(self) -> None:
        """**Kein Verbot, nur keine Überraschung.** Wer sein
        App-Passwort erneuert hat, will genau überschreiben."""
        self._erste()
        nextcloud(self.dienst, "meinewolke", "https://wolke-a.invalid",
                  "anna", "neues-geheimnis", ersetzen=True)
        self.assertEqual(self.dienst.remotes(), ["meinewolke"])
        self.assertEqual(
            self.dienst.rufen("config/dump")["meinewolke"]["user"], "anna")

    def test_vergeben_sagt_die_wahrheit(self) -> None:
        self.assertFalse(vergeben(self.dienst, "meinewolke"))
        self._erste()
        self.assertTrue(vergeben(self.dienst, "meinewolke"))
        self.assertFalse(vergeben(self.dienst, "meinewolke-2"))

    def test_die_zugangsdaten_ueberleben_einen_neustart(self) -> None:
        """**Das war die eigentliche Bitte.** Ein Zugang muss den
        nächsten Programmstart überstehen – er steht in der Datei, nicht
        im Arbeitsspeicher."""
        self._erste()
        nextcloud(self.dienst, "meinewolke-2", "https://wolke-b.invalid",
                  "bert", "geheim-B")
        self.dienst.beenden()

        with Dienst.starten(self.konf) as neuer:
            self.assertEqual(sorted(neuer.remotes()),
                             ["meinewolke", "meinewolke-2"])
            werte = neuer.rufen("config/dump")
            self.assertEqual(werte["meinewolke"]["user"], "anna")
            self.assertEqual(werte["meinewolke-2"]["user"], "bert")
        self.dienst = Dienst.starten(self.konf)      # für tearDown


if __name__ == "__main__":
    unittest.main()

"""Die Kommandozeile – kommen die Schalter auch an?

**Darum gibt es diese Datei.** Ein Schalter ``--ohne-unterordner`` war
angelegt, in der Hilfe beschrieben und wurde beim Aufruf **nicht
weitergereicht**: Der Aufruf von ``bericht()`` blieb unverändert, weil
eine Textersetzung ins Leere lief und niemand nachsah. Getestet war die
Funktion dahinter, getestet war der Schalter im Zerleger – nur der
Draht zwischen beiden nicht.

Aufgefallen ist es erst an einer echten Cloud: Der Lauf meldete »mit
allen Unterordnern«, obwohl das Gegenteil verlangt war.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from wolkenernte.__main__ import main


class DerSchalterKommtAn(unittest.TestCase):
    """Für jeden Schalter: Was der Aufrufer bekommt, nicht was er heißt."""

    def _aufraeumen(self, *zusatz: str) -> dict:
        with mock.patch("wolkenernte.aufraeumen.bericht",
                        return_value=0) as gerufen:
            main(["aufraeumen", "/irgendwo", "wolke:Fotos", *zusatz])
        self.assertTrue(gerufen.called, "bericht() wurde gar nicht gerufen")
        return gerufen.call_args.kwargs

    def test_ohne_unterordner_kommt_an(self) -> None:
        self.assertFalse(self._aufraeumen("--ohne-unterordner")
                         ["mit_unterordnern"])

    def test_ohne_den_schalter_wird_alles_genommen(self) -> None:
        self.assertTrue(self._aufraeumen()["mit_unterordnern"])

    def test_wirklich_kommt_an(self) -> None:
        self.assertTrue(self._aufraeumen("--wirklich")["wirklich"])

    def test_ohne_wirklich_wird_nur_gezaehlt(self) -> None:
        """Der Normalfall – und der, mit dem jeder anfangen sollte."""
        self.assertFalse(self._aufraeumen()["wirklich"])

    def test_beide_schalter_zusammen(self) -> None:
        werte = self._aufraeumen("--wirklich", "--ohne-unterordner")
        self.assertTrue(werte["wirklich"])
        self.assertFalse(werte["mit_unterordnern"])

    def test_das_archiv_kommt_als_pfad(self) -> None:
        with mock.patch("wolkenernte.aufraeumen.bericht",
                        return_value=0) as gerufen:
            main(["aufraeumen", "/irgendwo", "wolke:Fotos"])
        archiv, zugang = gerufen.call_args.args
        self.assertIsInstance(archiv, Path)
        self.assertEqual(zugang, "wolke:Fotos")


class DieSchalterBeimVerschlagworten(unittest.TestCase):
    def _verschlagworten(self, *zusatz: str) -> dict:
        with mock.patch("wolkenernte.verschlagworten.bericht",
                        return_value=0) as gerufen:
            main(["verschlagworten", "/irgendwo", *zusatz])
        self.assertTrue(gerufen.called)
        return gerufen.call_args.kwargs

    def test_ohne_bilderkennung(self) -> None:
        self.assertFalse(
            self._verschlagworten("--ohne-bilderkennung")["mit_bilderkennung"])

    def test_alle(self) -> None:
        self.assertFalse(self._verschlagworten("--alle")["nur_fehlende"])

    def test_die_vorgaben(self) -> None:
        werte = self._verschlagworten()
        self.assertTrue(werte["mit_bilderkennung"])
        self.assertTrue(werte["nur_fehlende"])


if __name__ == "__main__":
    unittest.main()

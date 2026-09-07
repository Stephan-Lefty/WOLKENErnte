"""Das Programmsymbol – und dass es beim Installieren mitkommt.

**Darum gibt es diese Datei.** Die Bilder lagen unter ``assets/`` neben
dem Quelltext, und das Fenster suchte sie über ``__file__`` drei Ebenen
höher. Aus dem Arbeitsverzeichnis heraus ging das gut; installiert
nicht, denn ``assets/`` gehört nicht zum Paket. Wer WOLKENErnte über
pip installierte, bekam ein Fenster ohne Symbol – **und keine
Fehlermeldung**, weil der Pfad nur geprüft und still übergangen wurde.

Genau das prüfen diese Tests: nicht, ob das Bild schön ist, sondern ob
es dort liegt, wo das installierte Programm es sucht.
"""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from wolkenernte import symbole

WURZEL = Path(__file__).resolve().parent.parent


class DieSymboleLiegenImPaket(unittest.TestCase):
    def test_der_ordner_ist_teil_des_pakets(self) -> None:
        """Unterhalb von ``wolkenernte/``, nicht daneben."""
        self.assertIn("wolkenernte", symbole.ORDNER.parts)
        self.assertTrue(symbole.ORDNER.is_dir())

    def test_jede_angekuendigte_groesse_ist_da(self) -> None:
        for groesse in symbole.GROESSEN:
            with self.subTest(groesse):
                self.assertIsNotNone(symbole.datei(groesse))

    def test_die_paketdaten_nehmen_sie_mit(self) -> None:
        """Ohne diesen Eintrag landen die Bilder in keinem Wheel – und
        genau das war der Fehler."""
        angaben = tomllib.loads(
            (WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
        muster = angaben["tool"]["setuptools"]["package-data"]["wolkenernte"]
        self.assertTrue(
            any("symbole" in m for m in muster),
            f"kein Muster für die Symbole in {muster}")

    def test_alle_gibt_die_vorhandenen(self) -> None:
        self.assertEqual(len(symbole.alle()), len(symbole.GROESSEN))

    def test_eine_unbekannte_groesse_gibt_nichts(self) -> None:
        """``None`` statt eines Pfades, der ins Leere zeigt."""
        self.assertIsNone(symbole.datei(999))


@unittest.skipUnless(
    __import__("importlib").util.find_spec("PySide6"), "PySide6 fehlt")
class DasQtSymbol(unittest.TestCase):
    def test_es_traegt_alle_groessen(self) -> None:
        """Wer nur eine Größe mitgibt, überlässt das Verkleinern Qt –
        und aus der 256er wird in 16 Pixeln ein grauer Fleck."""
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        symbol = symbole.qt_symbol()
        self.assertFalse(symbol.isNull())
        vorhanden = {g.width() for g in symbol.availableSizes()}
        for groesse in symbole.GROESSEN:
            with self.subTest(groesse):
                self.assertIn(groesse, vorhanden)
        del app


class DieVorlageBleibtWoSieWar(unittest.TestCase):
    def test_assets_ist_weiterhin_die_quelle(self) -> None:
        """``assets/`` bleibt die Vorlage für alles außerhalb des
        Programms: Menüeintrag, Windows-Symboldatei, Bilder im README.
        Die Fassungen im Paket sind Kopien davon, keine zweite
        Wahrheit."""
        self.assertTrue((WURZEL / "assets/icon-quelle.png").is_file())

    def test_paket_und_vorlage_stimmen_ueberein(self) -> None:
        """Sonst zeigte das Fenster ein anderes Symbol als der
        Menüeintrag."""
        for groesse in symbole.GROESSEN:
            vorlage = WURZEL / f"assets/icon-{groesse}.png"
            if not vorlage.is_file():
                continue
            with self.subTest(groesse):
                self.assertEqual(vorlage.read_bytes(),
                                 symbole.datei(groesse).read_bytes())


if __name__ == "__main__":
    unittest.main()

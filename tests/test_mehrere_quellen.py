"""Dasselbe Bild aus mehreren Clouds – es darf nur einmal ankommen.

**Darum gibt es diese Datei.** Innerhalb *eines* Laufs erkannte
``uebernehmen()`` Doppelgänger an Größe und Prüfsumme; jeder neue
Aufruf begann aber mit einer leeren Menge. Der zweite Schutz – »liegt
schon unter diesem Namen« – greift nur bei **gleichem Dateinamen**.

Genau das ist der Regelfall bei mehreren Clouds: ``Coast.jpg`` in der
einen, ``IMG_0001.jpg`` in der anderen, derselbe Inhalt. Beide landeten
im Archiv, und niemand merkte es – die Bilanz meldete brav »1
übernommen«.

Aufgefallen ist es an der Frage, wie Bilder aus mehreren Cloudsystemen
eigentlich zusammengeführt werden.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from wolkenernte.archiv import uebernehmen
from wolkenernte.lokal import Ordner
from wolkenernte.metadaten import Angaben
from wolkenernte.nachweis import archiv_kennungen
from wolkenernte.zuordnung import zuordnen

try:
    from PIL import Image
    PILLOW = True
except ImportError:  # pragma: no cover
    PILLOW = False

MAI = Angaben(aufgenommen=datetime(2024, 5, 1, tzinfo=timezone.utc))


def _jpeg(farbe: tuple[int, int, int]) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (80, 60), farbe).save(puffer, format="JPEG")
    return puffer.getvalue()


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class ZweiCloudsEinBild(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "archiv"

        dasselbe = _jpeg((40, 120, 200))
        (self.tmp / "wolke-a").mkdir()
        (self.tmp / "wolke-a" / "Coast.jpg").write_bytes(dasselbe)
        (self.tmp / "wolke-b").mkdir()
        # Derselbe Inhalt, anderer Name - der Regelfall bei zwei Clouds.
        (self.tmp / "wolke-b" / "IMG_0001.jpg").write_bytes(dasselbe)
        (self.tmp / "wolke-b" / "extra.jpg").write_bytes(_jpeg((200, 60, 40)))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _lauf(self, wolke: str):
        """Ein Erntelauf, wie ``ernten()`` ihn macht."""
        quelle = Ordner(self.tmp / wolke)
        quelle.pruefsummen_rechnen()
        groessen = {e.groesse for e in quelle}
        # **Was schon im Archiv liegt, gilt als gesehen.** Genau die
        # Zeile, die gefehlt hat.
        gesehen = (archiv_kennungen(self.archiv, nur_groessen=groessen)
                   if self.archiv.is_dir() else set())
        return uebernehmen(quelle, zuordnen(quelle.medien(), set()),
                           lambda z: MAI, self.archiv, gesehen=gesehen)

    def _dateien(self) -> list[str]:
        return sorted(p.name for p in self.archiv.rglob("*") if p.is_file())

    def test_der_zweite_lauf_erkennt_es_wieder(self) -> None:
        self._lauf("wolke-a")
        bilanz = self._lauf("wolke-b")
        self.assertEqual(bilanz.doppelt, 1)
        self.assertEqual(bilanz.uebernommen, 1)

    def test_es_liegt_nur_einmal_da(self) -> None:
        self._lauf("wolke-a")
        self._lauf("wolke-b")
        self.assertEqual(self._dateien(), ["Coast.jpg", "extra.jpg"])

    def test_der_name_aus_der_ersten_quelle_bleibt(self) -> None:
        """Wer zuerst kommt, gibt den Namen – deshalb gehört die Quelle
        mit den besseren Metadaten nach vorn."""
        self._lauf("wolke-b")
        self._lauf("wolke-a")
        self.assertIn("IMG_0001.jpg", self._dateien())
        self.assertNotIn("Coast.jpg", self._dateien())

    def test_neues_kommt_trotzdem_an(self) -> None:
        """Der Schutz darf nicht dazu führen, dass gar nichts mehr
        ankommt."""
        self._lauf("wolke-a")
        self._lauf("wolke-b")
        self.assertIn("extra.jpg", self._dateien())

    def test_derselbe_lauf_zweimal_aendert_nichts(self) -> None:
        self._lauf("wolke-a")
        vorher = self._dateien()
        bilanz = self._lauf("wolke-a")
        self.assertEqual(self._dateien(), vorher)
        self.assertEqual(bilanz.uebernommen, 0)

    def test_ohne_vorbelegung_kaeme_es_doppelt(self) -> None:
        """Die Gegenprobe im Test selbst: ohne die vorbelegte Menge
        landet derselbe Inhalt zweimal im Archiv."""
        for wolke in ("wolke-a", "wolke-b"):
            quelle = Ordner(self.tmp / wolke)
            quelle.pruefsummen_rechnen()
            uebernehmen(quelle, zuordnen(quelle.medien(), set()),
                        lambda z: MAI, self.archiv)
        self.assertEqual(self._dateien(),
                         ["Coast.jpg", "IMG_0001.jpg", "extra.jpg"])


if __name__ == "__main__":
    unittest.main()

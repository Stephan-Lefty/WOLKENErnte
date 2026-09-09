"""Vorschaubilder – für Fotos wie für Videos derselbe Weg.

Der interessante Teil ist der **Fehlschlag mit Gedächtnis**: Ein
beschädigtes Video darf nicht bei jedem Aufbau des Rasters erneut
zwanzig Sekunden lang versucht werden. Ein fehlendes ffmpeg dagegen
darf gerade *nicht* festgeschrieben werden, sonst bliebe das Video auch
nach dem Nachinstallieren ohne Bild.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte import video
from wolkenernte.web import vorschau

HAT_FFMPEG = shutil.which("ffmpeg") is not None

try:
    from PIL import Image
    HAT_PILLOW = True
except ImportError:
    HAT_PILLOW = False


class VorschauProbe(unittest.TestCase):
    def setUp(self) -> None:
        self.archiv = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.archiv, ignore_errors=True)

    def _video(self, name: str, sekunden: float = 2) -> str:
        ziel = self.archiv / name
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i",
             f"testsrc=size=640x480:rate=25:duration={sekunden}",
             "-pix_fmt", "yuv420p", str(ziel)],
            check=True, capture_output=True)
        return name


@unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
class VideosBekommenEineVorschau(VorschauProbe):
    def test_ein_bild_kommt_heraus(self) -> None:
        pfad = self._video("film.mp4")
        daten = vorschau.hole(self.archiv, pfad)
        self.assertIsNotNone(daten)
        self.assertEqual(daten[:2], b"\xff\xd8")

    def test_es_landet_im_zwischenspeicher(self) -> None:
        pfad = self._video("film.mp4")
        daten = vorschau.hole(self.archiv, pfad)
        gemerkt = vorschau._ziel(self.archiv, pfad)
        self.assertTrue(gemerkt.is_file())
        self.assertEqual(gemerkt.read_bytes(), daten)

    def test_beim_zweiten_mal_laeuft_ffmpeg_nicht_noch_einmal(self) -> None:
        pfad = self._video("film.mp4")
        vorschau.hole(self.archiv, pfad)
        with mock.patch.object(video, "einzelbild") as nie:
            self.assertIsNotNone(vorschau.hole(self.archiv, pfad))
        nie.assert_not_called()

    def test_endung_entscheidet_ohne_ruecksicht_auf_gross_und_klein(self) -> None:
        """``.MP4`` kommt von Kameras genauso oft wie ``.mp4``."""
        pfad = self._video("FILM.MP4")
        with mock.patch.object(video, "einzelbild",
                               return_value=b"\xff\xd8x") as gerufen:
            vorschau.hole(self.archiv, pfad)
        gerufen.assert_called_once()


class EinFehlschlagMitGedaechtnis(VorschauProbe):
    def _kaputt(self) -> str:
        (self.archiv / "kaputt.mp4").write_bytes(b"kein Video" * 100)
        return "kaputt.mp4"

    @unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
    def test_kaputtes_video_gibt_nichts_zurueck(self) -> None:
        self.assertIsNone(vorschau.hole(self.archiv, self._kaputt()))

    @unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
    def test_und_wird_nicht_wieder_versucht(self) -> None:
        """Sonst kostet jedes Blättern durch das Raster erneut die volle
        Frist – bei einer kaputten Datei zwanzig Sekunden Stillstand."""
        pfad = self._kaputt()
        vorschau.hole(self.archiv, pfad)
        with mock.patch.object(video, "einzelbild") as nie:
            self.assertIsNone(vorschau.hole(self.archiv, pfad))
        nie.assert_not_called()

    @unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
    def test_gegenprobe_ohne_die_notiz_liefe_es_wieder(self) -> None:
        """Nimmt man die leere Datei weg, versucht es die Oberfläche
        beim nächsten Mal von vorn – genau das soll verhindert werden."""
        pfad = self._kaputt()
        vorschau.hole(self.archiv, pfad)
        vorschau._ziel(self.archiv, pfad).unlink()
        with mock.patch.object(video, "einzelbild",
                               return_value=None) as doch:
            vorschau.hole(self.archiv, pfad)
        doch.assert_called_once()

    def test_fehlendes_ffmpeg_wird_nicht_festgeschrieben(self) -> None:
        """**Der Unterschied, auf den es ankommt.** Wer ffmpeg erst
        nachinstalliert, soll seine Videos danach sehen – und nicht
        gegen eine Notiz laufen, die aus der Zeit davor stammt.
        """
        pfad = self._kaputt()
        with mock.patch.object(video, "verfuegbar", return_value=False):
            self.assertIsNone(vorschau.hole(self.archiv, pfad))
        self.assertFalse(vorschau._ziel(self.archiv, pfad).exists())


@unittest.skipUnless(HAT_PILLOW, "Pillow fehlt")
class FotosGehenWeiterIhrenWeg(VorschauProbe):
    def _foto(self, name: str = "bild.jpg") -> str:
        Image.new("RGB", (1200, 800), (30, 90, 150)).save(self.archiv / name)
        return name

    def test_verkleinert_auf_die_kante(self) -> None:
        import io
        daten = vorschau.hole(self.archiv, self._foto())
        self.assertIsNotNone(daten)
        self.assertEqual(max(Image.open(io.BytesIO(daten)).size),
                         vorschau.KANTE)

    def test_ffmpeg_wird_fuer_fotos_nicht_bemueht(self) -> None:
        with mock.patch.object(video, "einzelbild") as nie:
            vorschau.hole(self.archiv, self._foto())
        nie.assert_not_called()

    def test_was_es_nicht_gibt_gibt_nichts(self) -> None:
        self.assertIsNone(vorschau.hole(self.archiv, "gibtsnicht.jpg"))


if __name__ == "__main__":
    unittest.main()

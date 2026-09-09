"""Ein Einzelbild aus einem Video – und was passiert, wenn keines kommt.

Die Testvideos werden von ffmpeg selbst erzeugt. Das kostet eine halbe
Sekunde und ist die einzige ehrliche Möglichkeit: Ein eingecheckter
Schnipsel wäre eine Datei, die niemand mehr versteht, und ein
nachgebauter Container prüfte den Nachbau statt ffmpeg.

Ohne ffmpeg werden die Tests übersprungen – wie die Fenstertests ohne
PySide6.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolkenernte import video

HAT_FFMPEG = shutil.which("ffmpeg") is not None


def _testvideo(ziel: Path, sekunden: float, breite: int = 640,
               hoehe: int = 480) -> Path:
    """Ein buntes Testbild als Video."""
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i",
         f"testsrc=size={breite}x{hoehe}:rate=25:duration={sekunden}",
         "-pix_fmt", "yuv420p", str(ziel)],
        check=True, capture_output=True)
    return ziel


@unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
class AusEchtenVideos(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.ordner, ignore_errors=True)

    def test_ein_jpeg_in_der_richtigen_groesse(self) -> None:
        datei = _testvideo(self.ordner / "film.mp4", 3)
        daten = video.einzelbild(datei, 400)
        self.assertIsNotNone(daten)
        # Die zwei Bytes, an denen man ein JPEG erkennt.
        self.assertEqual(daten[:2], b"\xff\xd8")
        from PIL import Image
        import io
        breite, hoehe = Image.open(io.BytesIO(daten)).size
        self.assertEqual(breite, 400)
        self.assertLessEqual(hoehe, 400)

    def test_kleines_video_wird_nicht_aufgeblasen(self) -> None:
        """``min(kante, iw)`` – ein 200 Punkte breites Video bleibt so.

        Hochskalieren macht nichts besser, kostet aber Platz und
        Rechenzeit und sieht matschig aus.
        """
        datei = _testvideo(self.ordner / "klein.mp4", 2, breite=200, hoehe=150)
        daten = video.einzelbild(datei, 400)
        from PIL import Image
        import io
        self.assertEqual(Image.open(io.BytesIO(daten)).size[0], 200)

    def test_kurzes_video_faellt_auf_den_anfang_zurueck(self) -> None:
        """Kürzer als eine Sekunde – trotzdem eine Vorschau.

        Am echten Bestand betrifft das 30 von 394 Videos. Ohne den
        Rückfall auf ``0.0`` blieben die ohne Bild; die Gegenprobe
        darunter zeigt genau das.
        """
        datei = _testvideo(self.ordner / "kurz.mp4", 0.3)
        self.assertIsNotNone(video.einzelbild(datei, 400))

    def test_gegenprobe_ohne_rueckfall_bliebe_es_leer(self) -> None:
        datei = _testvideo(self.ordner / "kurz.mp4", 0.3)
        with mock.patch.object(video, "STELLEN", (1.0,)):
            self.assertIsNone(video.einzelbild(datei, 400))


class WennEsSchiefgeht(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.ordner, ignore_errors=True)

    @unittest.skipUnless(HAT_FFMPEG, "ffmpeg fehlt")
    def test_kaputte_datei_liefert_nichts(self) -> None:
        """Und wirft nicht – in vierhundert Videos ist immer eines dabei."""
        datei = self.ordner / "kaputt.mp4"
        datei.write_bytes(b"das ist kein Video, sondern Text" * 100)
        self.assertIsNone(video.einzelbild(datei, 400))

    def test_datei_gibt_es_gar_nicht(self) -> None:
        self.assertIsNone(video.einzelbild(self.ordner / "weg.mp4", 400))

    def test_ohne_ffmpeg_gibt_es_nichts(self) -> None:
        datei = self.ordner / "film.mp4"
        datei.write_bytes(b"egal")
        with mock.patch.object(shutil, "which", return_value=None):
            self.assertIsNone(video.einzelbild(datei, 400))

    def test_eine_frist_beendet_das_haengen(self) -> None:
        """Ein festgefressenes ffmpeg darf die Oberfläche nicht anhalten."""
        datei = self.ordner / "film.mp4"
        datei.write_bytes(b"egal")
        with mock.patch.object(shutil, "which", return_value="/usr/bin/ffmpeg"), \
                mock.patch.object(
                    video.subprocess, "run",
                    side_effect=subprocess.TimeoutExpired("ffmpeg", 20)):
            self.assertIsNone(video.einzelbild(datei, 400))


class DerBefehl(unittest.TestCase):
    """Geprüft wird, **was bei ffmpeg ankommt** – nicht, wie es heißt.

    Dieselbe Lehre wie in ``test_kommandozeile.py``: Fünf Fehler an der
    echten Nextcloud hatten dieselbe Form – etwas war angelegt,
    beschrieben und kam nirgends an.
    """

    def _befehl(self, stelle: float = 1.0, kante: int = 400) -> list[str]:
        gefangen = []

        def merken(befehl, **rest):
            gefangen.append(befehl)
            return mock.Mock(stdout=b"")

        with mock.patch.object(video.subprocess, "run", side_effect=merken):
            video._versuchen(Path("/pfad/film.mp4"), stelle, kante)
        return gefangen[0]

    def test_ss_steht_vor_i(self) -> None:
        """**Der Kern der Sache.** Hinter ``-i`` gestellt, dekodiert
        ffmpeg das Video von vorn bis zur gesuchten Stelle; davor
        springt es hin. Bei einem langen Film ist das der Unterschied
        zwischen Minuten und einem Wimpernschlag – und im Code stehen
        die beiden nur zwei Zeilen auseinander, also leicht vertauscht.
        """
        befehl = self._befehl()
        self.assertLess(befehl.index("-ss"), befehl.index("-i"))

    def test_die_stelle_kommt_an(self) -> None:
        befehl = self._befehl(stelle=2.5)
        self.assertEqual(befehl[befehl.index("-ss") + 1], "2.5")

    def test_die_kante_kommt_an(self) -> None:
        befehl = self._befehl(kante=180)
        self.assertIn("scale='min(180,iw)':-2", befehl)

    def test_nur_ein_einziges_bild(self) -> None:
        befehl = self._befehl()
        self.assertEqual(befehl[befehl.index("-frames:v") + 1], "1")

    def test_ffmpeg_wartet_auf_keine_eingabe(self) -> None:
        """Ohne ``-nostdin`` steht sonst der Hintergrundfaden."""
        self.assertIn("-nostdin", self._befehl())

    def test_leere_ausgabe_gilt_als_fehlschlag(self) -> None:
        """Auch mit Rückgabewert 0 kann nichts herauskommen."""
        with mock.patch.object(video.subprocess, "run",
                               return_value=mock.Mock(stdout=b"")):
            self.assertIsNone(
                video._versuchen(Path("/pfad/film.mp4"), 1.0, 400))


if __name__ == "__main__":
    unittest.main()

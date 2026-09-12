"""Was ein Import brächte – bevor man ihn anstößt.

**Der Anlass, gemessen am echten Bestand am 2026-09-12:** Ein neuer
Takeout mit 6.587 Bildern, davon 5.939 verschiedene – und 5.910 lagen
schon im Archiv. Neu waren **29**. Wer das nicht vorher sieht, startet
einen Lauf über neun Gigabyte, ohne zu wissen, dass dabei 724 MB
herauskommen.

Zwei Zahlen, die den Entwurf entschieden und die hier festgenagelt
werden, weil man sie sonst beim nächsten Umbau verliert: Das
Inhaltsverzeichnis der fünf Teilarchive war in **0,1 s** gelesen, die
Archivseite über die Datenbank in **0,2 s** – über die Dateien
gerechnet dauerte dasselbe **130 s** bei identischem Ergebnis.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from wolkenernte.takeout import Archiv, exporte_im_ordner
from wolkenernte.vorpruefung import (
    in_worten,
    kennungen_aus_datenbank,
    voransehen,
)

try:
    from PIL import Image
    PILLOW = True
except ImportError:  # pragma: no cover
    PILLOW = False


def _jpeg(farbe: tuple[int, int, int]) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (80, 60), farbe).save(puffer, format="JPEG")
    return puffer.getvalue()


def _einlesen(archiv: Path, quelle: Path) -> None:
    """Ernten **und** erfassen – der dokumentierte Ablauf.

    **Der erste Anlauf dieser Tests rief nur `ernten`**, und vier
    Tests fielen um: `ernten` schreibt keine Datenbankzeile, das tut
    erst `erfassen`. Der Fehler saß im Testaufbau – und deckte
    gleichzeitig eine echte Lücke in der Vorschau auf, die nun
    `nicht_erfasst` meldet.
    """
    import contextlib

    from wolkenernte.erfassung import erfassen
    from wolkenernte.ernten import ernten

    with contextlib.redirect_stdout(io.StringIO()):
        ernten(archiv, [quelle])
        erfassen(archiv, [quelle])


def _json(name: str) -> bytes:
    return json.dumps({"title": name,
                       "photoTakenTime": {"timestamp": "1721053800"}}).encode()


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class EinLeeresArchiv(unittest.TestCase):
    """Ohne Datenbank ist alles neu – und das ist keine Schätzung."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "Archiv"
        self.archiv.mkdir()
        self.zip = self.tmp / "takeout-001.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg", _jpeg((10, 20, 30)))
            z.writestr("Takeout/Google Fotos/2024/IMG_2.jpg", _jpeg((200, 60, 40)))
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg.json", _json("IMG_1.jpg"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_alles_ist_neu(self) -> None:
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.medien, 2)
        self.assertEqual(ergebnis.neu, 2)
        self.assertEqual(ergebnis.schon_da, 0)

    def test_die_json_zaehlt_nicht_als_bild(self) -> None:
        """Sonst stimmt jede Zahl um die Metadatendateien daneben."""
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.medien, 2)

    def test_es_wird_gesagt_dass_nie_geerntet_wurde(self) -> None:
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertFalse(ergebnis.datenbank_gefragt)
        self.assertIn("noch nie geerntet", " ".join(in_worten(ergebnis)))


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class NachEinemErstenLauf(unittest.TestCase):
    """Der Normalfall: Ein zweiter Export mit wenig Neuem."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "Archiv"
        self.archiv.mkdir()

        self.alt = _jpeg((10, 20, 30))
        self.auch_alt = _jpeg((200, 60, 40))
        self.neu = _jpeg((40, 160, 80))

        erster = self.tmp / "takeout-alt-001.zip"
        with zipfile.ZipFile(erster, "w") as z:
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg", self.alt)
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg.json", _json("IMG_1.jpg"))
            z.writestr("Takeout/Google Fotos/2024/IMG_2.jpg", self.auch_alt)
            z.writestr("Takeout/Google Fotos/2024/IMG_2.jpg.json", _json("IMG_2.jpg"))
        _einlesen(self.archiv, erster)

        # Der zweite Export enthält dieselben zwei und ein drittes Bild -
        # und das dritte liegt zusätzlich in einem Album, wie Google es
        # tut: derselbe Inhalt an zwei Pfaden.
        self.zweiter = self.tmp / "takeout-neu-001.zip"
        with zipfile.ZipFile(self.zweiter, "w") as z:
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg", self.alt)
            z.writestr("Takeout/Google Fotos/2024/IMG_2.jpg", self.auch_alt)
            z.writestr("Takeout/Google Fotos/2024/IMG_3.jpg", self.neu)
            z.writestr("Takeout/Google Fotos/Nordsee/IMG_3.jpg", self.neu)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nur_das_dritte_ist_neu(self) -> None:
        with Archiv.aus_datei(self.zweiter) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.medien, 4)
        self.assertEqual(ergebnis.verschiedene, 3)
        self.assertEqual(ergebnis.schon_da, 2)
        self.assertEqual(ergebnis.neu, 1)

    def test_das_doppelte_im_export_wird_benannt(self) -> None:
        """**Google legt jedes Bild in einem Album ein zweites Mal ab.**
        Ohne diese Zeile wundert sich jeder über die Differenz."""
        with Archiv.aus_datei(self.zweiter) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.doppelt_in_der_quelle, 1)
        self.assertIn("doppelt", " ".join(in_worten(ergebnis)))

    def test_der_umfang_zaehlt_das_doppelte_nicht_mit(self) -> None:
        """Sonst verspricht die Vorschau doppelt so viel Zuwachs."""
        with Archiv.aus_datei(self.zweiter) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.bytes_neu, len(self.neu))

    def test_ein_zweiter_lauf_bringt_nichts_mehr(self) -> None:
        _einlesen(self.archiv, self.zweiter)
        with Archiv.aus_datei(self.zweiter) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.neu, 0)
        self.assertFalse(ergebnis.lohnt_sich)
        self.assertIn("Nichts Neues", " ".join(in_worten(ergebnis)))

    def test_beispiele_nennen_nur_dateinamen(self) -> None:
        """**Kein Ordner, kein Albumname.** »Nordsee 2023« verrät ein
        Urlaubsziel, und diese Liste landet in Bildschirmfotos."""
        with Archiv.aus_datei(self.zweiter) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.beispiele, ["IMG_3.jpg"])
        for name in ergebnis.beispiele:
            self.assertNotIn("/", name)


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
class DieDatenbankWirdGegengeprueft(unittest.TestCase):
    """Eine Zeile, deren Datei nicht mehr passt, darf nicht zählen.

    Sonst hieße es »liegt schon im Archiv«, das Bild würde nicht geholt
    – und niemand merkte es. Ein `stat()` je Zeile kostet nichts und
    fängt alles außer einer Änderung bei gleicher Größe.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.archiv = self.tmp / "Archiv"
        self.archiv.mkdir()
        self.bild = _jpeg((10, 20, 30))
        self.zip = self.tmp / "takeout-001.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("Takeout/Google Fotos/2024/IMG_1.jpg", self.bild)
        _einlesen(self.archiv, self.zip)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _die_eine_datei(self) -> Path:
        return next(p for p in self.archiv.rglob("*.jpg")
                    if ".wolkenernte" not in p.parts)

    def test_vorher_gilt_es_als_vorhanden(self) -> None:
        with Archiv.aus_datei(self.zip) as quelle:
            self.assertEqual(voransehen(self.archiv, quelle).schon_da, 1)

    def test_verschwundene_datei_zaehlt_nicht(self) -> None:
        self._die_eine_datei().unlink()
        stand = kennungen_aus_datenbank(self.archiv)
        self.assertEqual(len(stand.kennungen), 0)
        self.assertEqual(stand.verwaiste_zeilen, 1)
        self.assertEqual(stand.brauchbare_zeilen, 0)
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.neu, 1)
        self.assertEqual(ergebnis.schon_da, 0)

    def test_andere_groesse_zaehlt_nicht(self) -> None:
        self._die_eine_datei().write_bytes(self.bild + b"noch etwas")
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertEqual(ergebnis.neu, 1)

    def test_der_hinweis_steht_in_den_worten(self) -> None:
        self._die_eine_datei().unlink()
        with Archiv.aus_datei(self.zip) as quelle:
            ergebnis = voransehen(self.archiv, quelle)
        self.assertIn("passen nicht mehr", " ".join(in_worten(ergebnis)))


class ExporteImOrdner(unittest.TestCase):
    """**Im Download-Ordner liegt nicht nur der Takeout.**

    Beim Entwickler lagen neben den fünf Teilen eines Exports ein
    Faktura-Programm und ein Spielstand, beide als ZIP. Alle zusammen
    als einen Export zu lesen ergäbe eine Zählung, die niemand
    nachvollziehen kann – und schlimmer, fremde Grafiken wanderten ins
    Fotoarchiv.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("takeout-20260912T165849Z-1-001.zip",
                     "takeout-20260912T165849Z-1-002.zip",
                     "takeout-20260912T165849Z-1-005.zip",
                     "SRFakturaImport_v1.14.1.zip",
                     "Trans To Vostok.zip"):
            with zipfile.ZipFile(self.tmp / name, "w") as z:
                z.writestr("leer.txt", b"")
        (self.tmp / "notiz.txt").write_bytes(b"keine ZIP")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_drei_gruppen(self) -> None:
        gruppen = exporte_im_ordner(self.tmp)
        self.assertEqual(len(gruppen), 3)

    def test_die_fuenf_teile_bleiben_zusammen(self) -> None:
        gruppen = exporte_im_ordner(self.tmp)
        self.assertEqual(len(gruppen["takeout-20260912T165849Z-1"]), 3)

    def test_das_fremde_bleibt_getrennt(self) -> None:
        gruppen = exporte_im_ordner(self.tmp)
        self.assertIn("SRFakturaImport_v1.14.1", gruppen)
        self.assertIn("Trans To Vostok", gruppen)

    def test_was_keine_zip_ist_kommt_nicht_vor(self) -> None:
        self.assertNotIn("notiz", exporte_im_ordner(self.tmp))

    def test_nach_namen_sortiert(self) -> None:
        """``-002`` vor ``-005``, damit Meldungen lesbar bleiben."""
        teile = exporte_im_ordner(self.tmp)["takeout-20260912T165849Z-1"]
        self.assertEqual([p.name[-7:] for p in teile],
                         ["001.zip", "002.zip", "005.zip"])


if __name__ == "__main__":
    unittest.main()

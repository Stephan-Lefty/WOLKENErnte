"""Die EXIF-Uhrzeit in einem bestehenden Archiv nachrechnen.

**Das Testarchiv wird kaputtgemacht wie die alte Fassung es tat** –
Zeitstempel aus ``naive.replace(tzinfo=utc).timestamp()`` –, statt einen
festen Zahlenwert hinzuschreiben. Ein hingeschriebener Wert wäre nur
auf dem Rechner richtig, auf dem er entstand; die Verschiebung ist ja
gerade der Abstand zur Ortszeit, und der ist woanders anders.

Läuft die Testmaschine auf UTC, gibt es nichts zu reparieren. Diese
Tests werden dann übersprungen – sie prüften sonst nur, dass eine
Nulloperation nichts tut.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from wolkenernte import uhrzeit
from wolkenernte.uhrzeit import Befund, durchsehen, wanduhr

try:
    from PIL import Image
    PILLOW = True
except ImportError:
    PILLOW = False


def _versetzt() -> bool:
    """Ob dieser Rechner überhaupt einen Abstand zu Greenwich hat."""
    wand = datetime(2023, 7, 15, 12, 30, 45)
    return wand.replace(tzinfo=timezone.utc).timestamp() != wand.astimezone().timestamp()


def _falscher_stempel(wand: datetime) -> float:
    """Was die alte Fassung aus dieser EXIF-Zeit gemacht hätte."""
    return wand.replace(tzinfo=timezone.utc).timestamp()


def _richtiger_stempel(wand: datetime) -> float:
    return wand.astimezone().timestamp()


def _bild(pfad: Path, wand: datetime | None, *, stempel: float) -> None:
    """Ein Bild anlegen, wahlweise mit EXIF-Zeit, und die Dateizeit setzen."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bild = Image.new("RGB", (12, 8), (40, 90, 160))
    if wand is None:
        bild.save(pfad, quality=70)
    else:
        werte = Image.Exif()
        werte[306] = wand.strftime("%Y:%m:%d %H:%M:%S")           # DateTime
        werte[271], werte[272] = "WOLKENErnte", "Probe"           # Make, Model
        werte.get_ifd(0x8769)[36867] = werte[306]                 # Original
        bild.save(pfad, quality=70, exif=werte)
    os.utime(pfad, (stempel, stempel))


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
@unittest.skipUnless(_versetzt(), "Rechner steht auf UTC – kein Abstand")
class Archivprobe(unittest.TestCase):
    """Ein Archiv, in dem alle vier Fälle vorkommen."""

    def setUp(self) -> None:
        self.archiv = Path(tempfile.mkdtemp())

        # 1. Betroffen: Zeitstempel aus der alten Rechnung.
        self.krumm = datetime(2023, 7, 15, 12, 30, 45)
        _bild(self.archiv / "2023/2023-07/IMG_1.jpg", self.krumm,
              stempel=_falscher_stempel(self.krumm))

        # 2. Schon richtig - etwa nach einem Lauf mit 0.4.3.
        self.gerade = datetime(2023, 8, 2, 9, 0, 0)
        _bild(self.archiv / "2023/2023-08/IMG_2.jpg", self.gerade,
              stempel=_richtiger_stempel(self.gerade))

        # 3. Datum aus einer Takeout-JSON: EXIF sagt etwas anderes als
        #    der Zeitstempel, und der Zeitstempel gilt.
        _bild(self.archiv / "2023/2023-08/IMG_3.jpg",
              datetime(2023, 8, 2, 9, 0, 0),
              stempel=datetime(2019, 5, 5, 8, 0).astimezone().timestamp())

        # 4. Gar kein EXIF.
        _bild(self.archiv / "2023/2023-08/IMG_4.jpg", None,
              stempel=_falscher_stempel(datetime(2023, 8, 3, 10, 0)))

    def _namen(self, befunde: list[Befund]) -> list[str]:
        return sorted(b.relativ.rsplit("/", 1)[-1] for b in befunde)


class DerFingerabdruck(Archivprobe):
    def test_nur_die_betroffene_datei(self) -> None:
        """**Der Kern.** Drei von vier Bildern werden nicht angefasst –
        und zwar aus drei verschiedenen Gründen."""
        self.assertEqual(self._namen(durchsehen(self.archiv)), ["IMG_1.jpg"])

    def test_die_uhrzeit_kommt_richtig_heraus(self) -> None:
        fund = durchsehen(self.archiv)[0]
        self.assertEqual(
            datetime.fromtimestamp(fund.neu).strftime("%d.%m.%Y %H:%M"),
            "15.07.2023 12:30")

    def test_die_wanduhr_kommt_ohne_zeitzone(self) -> None:
        gelesen = wanduhr(self.archiv / "2023/2023-07/IMG_1.jpg")
        self.assertEqual(gelesen, self.krumm)
        self.assertIsNone(gelesen.tzinfo)

    def test_ohne_datum_bleibt_draussen(self) -> None:
        """Dort steht der Zeitpunkt der Übernahme, nicht der Aufnahme –
        auch wenn im Bild zufällig noch ein EXIF-Datum steckt."""
        ordner = self.archiv / "ohne-datum"
        ordner.mkdir()
        _bild(ordner / "IMG_9.jpg", self.krumm,
              stempel=_falscher_stempel(self.krumm))
        self.assertEqual(self._namen(durchsehen(self.archiv)), ["IMG_1.jpg"])


class DasRichtigstellen(Archivprobe):
    def test_der_zeitstempel_steht_danach_richtig(self) -> None:
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        datei = self.archiv / "2023/2023-07/IMG_1.jpg"
        self.assertEqual(
            datetime.fromtimestamp(datei.stat().st_mtime).strftime("%H:%M"),
            "12:30")

    def test_ein_zweiter_lauf_findet_nichts_mehr(self) -> None:
        """Der Lauf muss wiederholbar sein – wer unsicher ist, ob er
        ihn schon hatte, soll ihn gefahrlos noch einmal starten
        können."""
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        self.assertEqual(durchsehen(self.archiv), [])

    def test_die_anderen_drei_sind_unberuehrt(self) -> None:
        vorher = {p.name: p.stat().st_mtime
                  for p in self.archiv.rglob("*.jpg") if p.name != "IMG_1.jpg"}
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        nachher = {p.name: p.stat().st_mtime
                   for p in self.archiv.rglob("*.jpg") if p.name != "IMG_1.jpg"}
        self.assertEqual(vorher, nachher)

    def test_es_wird_protokolliert(self) -> None:
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        zeilen = (self.archiv / uhrzeit.PROTOKOLL).read_text(
            "utf-8").splitlines()
        self.assertEqual(len(zeilen), 1)
        eintrag = json.loads(zeilen[0])
        self.assertEqual(eintrag["pfad"], "2023/2023-07/IMG_1.jpg")
        self.assertIn("lauf", eintrag)


@unittest.skipUnless(PILLOW, "Pillow nicht vorhanden")
@unittest.skipUnless(_versetzt(), "Rechner steht auf UTC – kein Abstand")
class DerOrdnerBleibt(unittest.TestCase):
    """**Die Annahme, die beim Bauen fast eine Umzugsmechanik gekostet
    hätte.**

    Der Verdacht war: Eine Aufnahme vom 1. Januar 00:30, um eine Stunde
    zurückgerechnet, gehört ins Vorjahr – die Datei müsste also
    umziehen. Sie muss nicht. ``archiv.zielordner()`` nimmt ``.year``
    und ``.month`` des Zeitobjekts, und die zeigen die Wanduhr, ganz
    gleich welche Zeitzone daranhängt. Mit dem falschen Zeitstempel
    landete die Aufnahme deshalb im *richtigen* Januarordner.

    Dieser Test nagelt das fest. Fällt er um, ist die Reparatur
    unvollständig – dann bleiben Dateien im falschen Ordner zurück.
    """

    def test_der_januarfall(self) -> None:
        from wolkenernte import archiv as archivmodul
        from wolkenernte.metadaten import Angaben

        wand = datetime(2024, 1, 1, 0, 30, 0)
        beim_ernten = archivmodul.zielordner(
            Angaben(aufgenommen=wand.replace(tzinfo=timezone.utc)))
        richtig = datetime.fromtimestamp(wand.astimezone().timestamp())
        self.assertEqual(beim_ernten,
                         f"{richtig.year:04d}/{richtig.year:04d}-"
                         f"{richtig.month:02d}")

    def test_die_datei_bleibt_liegen(self) -> None:
        archiv = Path(tempfile.mkdtemp())
        wand = datetime(2024, 1, 1, 0, 30, 0)
        datei = archiv / "2024/2024-01/IMG_1.jpg"
        _bild(datei, wand, stempel=_falscher_stempel(wand))

        uhrzeit.richtigstellen(archiv, durchsehen(archiv))

        self.assertTrue(datei.exists())
        self.assertEqual(
            datetime.fromtimestamp(datei.stat().st_mtime).strftime(
                "%d.%m.%Y %H:%M"),
            "01.01.2024 00:30")


class DerRueckweg(Archivprobe):
    """Ein Lauf, der sich nicht aufheben lässt, ist ein Sprung ohne Netz."""

    def test_alles_steht_wieder_wie_vorher(self) -> None:
        datei = self.archiv / "2023/2023-07/IMG_1.jpg"
        vorher = datei.stat().st_mtime
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        self.assertNotEqual(datei.stat().st_mtime, vorher)

        geschafft, fehler = uhrzeit.zurueck(self.archiv)
        self.assertEqual((geschafft, fehler), (1, []))
        self.assertAlmostEqual(datei.stat().st_mtime, vorher, places=3)

    def test_das_protokoll_ist_danach_leer(self) -> None:
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))
        uhrzeit.zurueck(self.archiv)
        self.assertFalse((self.archiv / uhrzeit.PROTOKOLL).exists())

    def test_ohne_protokoll_passiert_nichts(self) -> None:
        self.assertEqual(uhrzeit.zurueck(self.archiv), (0, []))

    def test_nur_der_letzte_lauf_wird_aufgehoben(self) -> None:
        """Zwei Läufe im Protokoll, einer davon aufgehoben – der ältere
        muss stehen bleiben, sonst nähme ``--zurueck`` beim zweiten
        Aufruf stillschweigend mehr mit als beim ersten."""
        uhrzeit._protokoll_schreiben(
            self.archiv, "2020-01-01T00:00:00+01:00",
            [{"pfad": "2023/2023-08/IMG_2.jpg", "alt": 1.0, "neu": 2.0}])
        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))

        uhrzeit.zurueck(self.archiv)

        rest = uhrzeit._protokoll_lesen(self.archiv)
        self.assertEqual([e["lauf"] for e in rest],
                         ["2020-01-01T00:00:00+01:00"])


class DieDatenbankWirdMitgefuehrt(Archivprobe):
    """Bleibt sie stehen, während Dateien wandern, hängen Titel und
    Alben plötzlich am falschen Bild."""

    def _bestand(self):
        from wolkenernte.bestand import Bestand
        return Bestand(self.archiv)

    def test_das_aufnahmedatum_wird_nachgezogen(self) -> None:
        with self._bestand() as bestand:
            bestand.bild_merken(
                1, 1, pfad="2023/2023-07/IMG_1.jpg",
                aufgenommen=self.krumm.replace(tzinfo=timezone.utc))
            bestand.sichern()

        uhrzeit.richtigstellen(self.archiv, durchsehen(self.archiv))

        with self._bestand() as bestand:
            zeile = bestand.db.execute(
                "SELECT aufgenommen FROM bild WHERE pfad = ?",
                ("2023/2023-07/IMG_1.jpg",)).fetchone()
        gespeichert = datetime.fromisoformat(zeile[0])
        self.assertEqual(
            gespeichert.astimezone().strftime("%d.%m.%Y %H:%M"),
            "15.07.2023 12:30")


class DerBefehlIstAngeschlossen(unittest.TestCase):
    """Dass ein Unterbefehl im Zerleger steht, heißt nicht, dass er
    ankommt – dieselbe Lehre wie bei ``--ohne-unterordner``."""

    def test_die_schalter_kommen_an(self) -> None:
        from unittest import mock

        from wolkenernte.__main__ import main

        with mock.patch("wolkenernte.uhrzeit.bericht",
                        return_value=0) as gerufen:
            main(["uhrzeit", "/tmp/irgendwo", "--wirklich"])
        _, benannt = gerufen.call_args
        self.assertTrue(benannt["wirklich"])
        self.assertFalse(benannt["rueckgaengig"])

    def test_zurueck_kommt_an(self) -> None:
        from unittest import mock

        from wolkenernte.__main__ import main

        with mock.patch("wolkenernte.uhrzeit.bericht",
                        return_value=0) as gerufen:
            main(["uhrzeit", "/tmp/irgendwo", "--zurueck"])
        _, benannt = gerufen.call_args
        self.assertTrue(benannt["rueckgaengig"])
        self.assertFalse(benannt["wirklich"])

    def test_ohne_schalter_wird_nichts_geaendert(self) -> None:
        """Der Probelauf ist die Voreinstellung – wie beim Aufräumen."""
        from unittest import mock

        from wolkenernte.__main__ import main

        with mock.patch("wolkenernte.uhrzeit.bericht",
                        return_value=0) as gerufen:
            main(["uhrzeit", "/tmp/irgendwo"])
        _, benannt = gerufen.call_args
        self.assertFalse(benannt["wirklich"])


if __name__ == "__main__":
    unittest.main()

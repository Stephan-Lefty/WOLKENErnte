"""Takeout-Archive lesen, ohne sie auszupacken.

Die Testarchive werden hier erzeugt, nicht mitgeliefert: Ein echtes
Takeout enthält private Fotos, und die haben in einem Repository nichts
zu suchen – auch nicht als Beispiel.
"""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from wolkenernte.takeout import Archiv, TakeoutFehler


def _zip_bauen(pfad: Path, dateien: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(pfad, "w") as datei:
        for name, inhalt in dateien.items():
            datei.writestr(name, inhalt)
    return pfad


class MitEinemTeilarchiv(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Path(tempfile.mkdtemp())
        _zip_bauen(
            self.ordner / "takeout-001.zip",
            {
                "Takeout/Google Fotos/2024/IMG_0001.jpg": b"bild-eins",
                "Takeout/Google Fotos/2024/IMG_0001.jpg.json": b'{"title": "eins"}',
            },
        )

    def test_findet_alle_dateien(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertEqual(len(archiv), 2)

    def test_liest_inhalt(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            inhalt = archiv.lesen("Takeout/Google Fotos/2024/IMG_0001.jpg")
            self.assertEqual(inhalt, b"bild-eins")

    def test_verzeichnisse_zaehlen_nicht_mit(self) -> None:
        """Ordnereinträge sind keine Dateien und dürfen die Zählung
        nicht verfälschen – sonst meldet das Programm mehr Bilder, als
        es gibt."""
        _zip_bauen(
            self.ordner / "takeout-002.zip",
            {"Takeout/Google Fotos/Leer/": b""},
        )
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertEqual(len(archiv), 2)

    def test_unbekannter_pfad_meldet_sich(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            with self.assertRaises(TakeoutFehler):
                archiv.lesen("gibtsnicht.jpg")

    def test_eintrag_kennt_name_und_ordner(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            eintrag = archiv.eintrag("Takeout/Google Fotos/2024/IMG_0001.jpg")
            assert eintrag is not None
            self.assertEqual(eintrag.name, "IMG_0001.jpg")
            self.assertEqual(eintrag.ordner, "Takeout/Google Fotos/2024")
            self.assertEqual(eintrag.groesse, len(b"bild-eins"))


class UeberTeilarchiveHinweg(unittest.TestCase):
    """Der eigentliche Grund für dieses Modul.

    Google zerlegt den Export ohne Rücksicht auf Zusammengehöriges. Ein
    Bild im einen Teil, seine Metadaten im nächsten – wer die Teile
    einzeln betrachtet, verliert an jeder Nahtstelle Aufnahmedatum und
    Ortsangabe und merkt es nicht, weil die Bilder ja da sind.
    """

    def setUp(self) -> None:
        self.ordner = Path(tempfile.mkdtemp())
        _zip_bauen(
            self.ordner / "takeout-001.zip",
            {"Takeout/Google Fotos/2024/IMG_0001.jpg": b"bild"},
        )
        _zip_bauen(
            self.ordner / "takeout-002.zip",
            {"Takeout/Google Fotos/2024/IMG_0001.jpg.json": b'{"title": "eins"}'},
        )

    def test_bild_und_metadaten_finden_zusammen(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertIn("Takeout/Google Fotos/2024/IMG_0001.jpg", archiv)
            self.assertIn("Takeout/Google Fotos/2024/IMG_0001.jpg.json", archiv)
            self.assertEqual(len(archiv), 2)

    def test_lesen_greift_ins_richtige_teilarchiv(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertEqual(
                archiv.lesen("Takeout/Google Fotos/2024/IMG_0001.jpg.json"),
                b'{"title": "eins"}',
            )

    def test_eintrag_weiss_aus_welchem_teil_er_stammt(self) -> None:
        """Ohne diese Angabe sucht man bei zwanzig ZIP-Dateien lange."""
        with Archiv.aus_ordner(self.ordner) as archiv:
            eintrag = archiv.eintrag("Takeout/Google Fotos/2024/IMG_0001.jpg.json")
            assert eintrag is not None
            self.assertEqual(eintrag.quelle.name, "takeout-002.zip")

    def test_teile_werden_nach_namen_sortiert(self) -> None:
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertEqual(
                [p.name for p in archiv.teile()],
                ["takeout-001.zip", "takeout-002.zip"],
            )


class WennEtwasNichtStimmt(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Path(tempfile.mkdtemp())

    def test_ordner_ohne_zip(self) -> None:
        with self.assertRaises(TakeoutFehler):
            Archiv.aus_ordner(self.ordner)

    def test_ordner_gibt_es_nicht(self) -> None:
        with self.assertRaises(TakeoutFehler):
            Archiv.aus_ordner(self.ordner / "weg")

    def test_leere_liste(self) -> None:
        with self.assertRaises(TakeoutFehler):
            Archiv([])

    def test_beschaedigtes_zip_nennt_die_datei(self) -> None:
        """Die Meldung muss sagen, *welche* Datei kaputt ist – bei
        zwanzig Teilarchiven ist alles andere wertlos."""
        kaputt = self.ordner / "takeout-001.zip"
        kaputt.write_bytes(b"das ist kein ZIP")
        with self.assertRaises(TakeoutFehler) as fehler:
            Archiv.aus_ordner(self.ordner)
        self.assertIn("takeout-001.zip", str(fehler.exception))

    def test_doppelte_pfade_werden_gemeldet(self) -> None:
        """Zwei Exporte durcheinandergeworfen. Nicht stillschweigend
        übergehen, sonst stimmen die Zählungen nicht."""
        _zip_bauen(self.ordner / "a.zip", {"Takeout/x.jpg": b"eins"})
        _zip_bauen(self.ordner / "b.zip", {"Takeout/x.jpg": b"zwei"})
        with Archiv.aus_ordner(self.ordner) as archiv:
            self.assertEqual(archiv.doppelte, ["Takeout/x.jpg"])
            self.assertEqual(len(archiv), 1)


class GrosseArchive(unittest.TestCase):
    """ZIP64 – und das ist bei Takeout kein Sonderfall, sondern die Regel.

    Ein Teilarchiv über vier Gigabyte wird im 64-Bit-Format geschrieben,
    und Google liefert genau solche. Hier wird ZIP64 nicht über die
    Dateigröße erzwungen, sondern über die Zahl der Einträge – über
    65535 verlangen denselben Endsatz, kosten aber keine vier Gigabyte
    Plattenplatz.

    Nebenbei ist das die Größenordnung eines echten Bestands: 35.000
    Fotos ergeben mit ihren Metadaten 70.000 Einträge.
    """

    ANZAHL = 70_000

    @classmethod
    def setUpClass(cls) -> None:
        cls.ordner = Path(tempfile.mkdtemp())
        cls.datei = cls.ordner / "takeout-20260905T084500Z-001.zip"
        with zipfile.ZipFile(cls.datei, "w", allowZip64=True) as z:
            for i in range(cls.ANZAHL):
                z.writestr(f"Takeout/Google Fotos/2024/IMG_{i:05d}.jpg", b"x" * 20)

    def test_ist_wirklich_zip64(self) -> None:
        """Sonst prüft der Rest dieser Klasse nichts.

        Ein früherer Versuch nahm ``force_zip64`` beim Schreiben einer
        einzelnen kleinen Datei – das setzt nur den lokalen Kopf, das
        Inhaltsverzeichnis blieb 32-bittig, und der Test war wertlos.
        ``PK\\x06\\x06`` ist der ZIP64-Endsatz; steht er nicht drin, ist
        es kein ZIP64.
        """
        self.assertIn(b"PK\x06\x06", self.datei.read_bytes())

    def test_alle_eintraege_werden_gefunden(self) -> None:
        with Archiv([self.datei]) as archiv:
            self.assertEqual(len(archiv), self.ANZAHL)

    def test_der_letzte_eintrag_ist_lesbar(self) -> None:
        """Wahlfreier Zugriff über das Inhaltsverzeichnis – nicht
        sequentielles Durchlaufen. Bei einem Archiv über vier Gigabyte
        ist das der Unterschied zwischen Augenblick und Minuten."""
        letzter = f"Takeout/Google Fotos/2024/IMG_{self.ANZAHL - 1:05d}.jpg"
        with Archiv([self.datei]) as archiv:
            self.assertEqual(archiv.lesen(letzter), b"x" * 20)


class DasArchivWirdWiederGeschlossen(unittest.TestCase):
    def test_nach_dem_block_sind_die_dateien_zu(self) -> None:
        ordner = Path(tempfile.mkdtemp())
        _zip_bauen(ordner / "takeout-001.zip", {"Takeout/x.jpg": b"bild"})
        with Archiv.aus_ordner(ordner) as archiv:
            self.assertEqual(len(archiv.teile()), 1)
        self.assertEqual(archiv.teile(), [])


if __name__ == "__main__":
    unittest.main()

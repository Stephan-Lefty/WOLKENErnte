"""Ähnliche Bilder finden – auch bei verschiedenen Dateien."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wolkenernte.aehnlich import SCHWELLE, abstand, fingerabdruck, gruppen

try:
    from PIL import Image
    PILLOW = True
except ImportError:
    PILLOW = False


#: Zwei Fingerabdrücke mit echter Struktur: acht verschiedene Zeilen.
#:
#: Hier standen einmal ``0x0F0F...`` und ``0x3333...`` – Werte mit acht
#: **gleichen** Zeilen. Seit die Suche solche als nichtssagend verwirft,
#: prüften die Tests damit nichts mehr.
MUSTER_A = 0x0F1E2D3C4B5A6978
MUSTER_B = 0xC3A5961E7834D20F


def _bild(pfad: Path, muster, groesse=(120, 120), qualitaet=95) -> Path:
    """Ein Testbild aus einer Funktion (u, v) -> Helligkeit.

    **u und v laufen von 0 bis 1**, nicht über Bildpunkte. Das ist
    wesentlich: Ein Muster wie ``(x * 3) % 256`` sieht bei 400 und bei
    100 Punkten Kantenlänge völlig verschieden aus, weil sich die
    Periodenlänge mitverschiebt. Ein erster Anlauf hat genau daran
    geglaubt, der Fingerabdruck sei nicht skalierungsfest - dabei waren
    es die Testbilder, die beim Verkleinern zu etwas anderem wurden.
    """
    bild = Image.new("L", groesse)
    breite, hoehe = groesse
    bild.putdata([muster(x / breite, y / hoehe)
                  for y in range(hoehe) for x in range(breite)])
    bild.save(pfad, quality=qualitaet)
    return pfad


def _schachbrett(u: float, v: float) -> int:
    """Vier mal vier Felder – grobe Struktur, die jedes Verkleinern übersteht."""
    return 235 if (int(u * 4) + int(v * 4)) % 2 else 30


def _streifen(u: float, v: float) -> int:
    """Waagerechte Bänder – deutlich anders als das Schachbrett."""
    return 235 if int(v * 6) % 2 else 30


class DerAbstand(unittest.TestCase):
    def test_gleiche_haben_abstand_null(self) -> None:
        self.assertEqual(abstand(0b1010, 0b1010), 0)

    def test_ein_bit_unterschied(self) -> None:
        self.assertEqual(abstand(0b1010, 0b1011), 1)

    def test_alle_bit_verschieden(self) -> None:
        self.assertEqual(abstand(0, (1 << 64) - 1), 64)


@unittest.skipUnless(PILLOW, "Pillow fehlt")
class DerFingerabdruck(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_hat_64_bit(self) -> None:
        pfad = _bild(self.tmp / "a.png", _schachbrett)
        wert = fingerabdruck(pfad)
        assert wert is not None
        self.assertLess(wert, 1 << 64)

    def test_dasselbe_bild_ergibt_denselben_wert(self) -> None:
        a = fingerabdruck(_bild(self.tmp / "a.png", _schachbrett))
        b = fingerabdruck(_bild(self.tmp / "b.png", _schachbrett))
        self.assertEqual(a, b)

    def test_ueberlebt_verkleinern(self) -> None:
        """Der eigentliche Zweck: dasselbe Bild in anderer Größe."""
        gross = fingerabdruck(_bild(self.tmp / "g.png", _schachbrett, (400, 400)))
        klein = fingerabdruck(_bild(self.tmp / "k.png", _schachbrett, (100, 100)))
        assert gross is not None and klein is not None
        self.assertLessEqual(abstand(gross, klein), SCHWELLE)

    def test_ueberlebt_starke_kompression(self) -> None:
        """Dasselbe Foto, von einem Messenger neu komprimiert."""
        gut = fingerabdruck(_bild(self.tmp / "gut.jpg", _schachbrett, qualitaet=95))
        schlecht = fingerabdruck(_bild(self.tmp / "sch.jpg", _schachbrett,
                                       qualitaet=25))
        assert gut is not None and schlecht is not None
        self.assertLessEqual(abstand(gut, schlecht), SCHWELLE)

    def test_verschiedene_bilder_sind_verschieden(self) -> None:
        a = fingerabdruck(_bild(self.tmp / "a.png", _schachbrett))
        b = fingerabdruck(_bild(self.tmp / "b.png", _streifen))
        assert a is not None and b is not None
        self.assertGreater(abstand(a, b), SCHWELLE)

    def test_kaputte_datei_wirft_nicht(self) -> None:
        pfad = self.tmp / "kaputt.jpg"
        pfad.write_bytes(b"das ist kein Bild")
        self.assertIsNone(fingerabdruck(pfad))

    def test_datei_gibt_es_nicht(self) -> None:
        self.assertIsNone(fingerabdruck(self.tmp / "weg.jpg"))


class DieGruppen(unittest.TestCase):
    def test_gleiche_werte_kommen_zusammen(self) -> None:
        ergebnis = gruppen([("a", MUSTER_A), ("b", MUSTER_A),
                            ("c", MUSTER_B)])
        self.assertEqual(len(ergebnis), 1)
        self.assertEqual(set(ergebnis[0]), {"a", "b"})

    def test_ein_bit_unterschied_reicht_noch(self) -> None:
        ergebnis = gruppen([("a", MUSTER_A),
                            ("b", MUSTER_A ^ 1)])
        self.assertEqual(len(ergebnis), 1)

    def test_zu_weit_auseinander_bleibt_getrennt(self) -> None:
        self.assertEqual(gruppen([("a", MUSTER_A),
                                  ("b", MUSTER_B)]), [])

    def test_einzelgaenger_kommen_nicht_vor(self) -> None:
        """Gezählt werden unterschiedliche *Bit*, nicht Zahlengröße.

        Hier stand einmal ``1`` gegen ``1 << 40`` - das sind zwei Bit
        Unterschied und damit ähnlich, obwohl die Zahlen weit
        auseinanderliegen."""
        self.assertEqual(gruppen([("a", MUSTER_A),
                                  ("b", MUSTER_B)]), [])

    def test_ketten_werden_zusammengefasst(self) -> None:
        """a ähnelt b, b ähnelt c – dann gehören alle drei zusammen."""
        ergebnis = gruppen([("a", MUSTER_A ^ 0x0F),
                            ("b", MUSTER_A ^ 0x0E),
                            ("c", MUSTER_A ^ 0x0C)])
        self.assertEqual(len(ergebnis), 1)
        self.assertEqual(set(ergebnis[0]), {"a", "b", "c"})

    def test_groesste_gruppe_zuerst(self) -> None:
        ergebnis = gruppen([
            ("a", MUSTER_A), ("b", MUSTER_A),
            ("c", MUSTER_A),
            ("x", MUSTER_B), ("y", MUSTER_B),
        ])
        self.assertEqual(len(ergebnis[0]), 3)
        self.assertEqual(len(ergebnis[1]), 2)

    def test_leere_eingabe(self) -> None:
        self.assertEqual(gruppen([]), [])

    def test_grosse_menge_bleibt_schnell(self) -> None:
        """Ohne Vorfilter wären das 500.000 Paarvergleiche.

        Der Test prüft nicht die Zeit, sondern dass der Vorfilter das
        Ergebnis nicht verfälscht: Die zehn eingestreuten Paare müssen
        alle gefunden werden.

        Die Zählung beginnt bei 1, nicht bei 0 – bei 0 wäre der
        Fingerabdruck ebenfalls 0, und den wirft die Strukturprüfung
        zu Recht heraus. Ein erster Anlauf zählte ab 0 und fand deshalb
        neun statt zehn Gruppen.
        """
        eintraege = [(f"f{i}", (i * 2_654_435_761) % (1 << 64))
                     for i in range(1, 1001)]
        for i in range(10):
            eintraege.append((f"kopie{i}", eintraege[i][1]))
        ergebnis = gruppen(eintraege)
        self.assertGreaterEqual(len(ergebnis), 10)

    def test_strukturlose_bilder_bleiben_draussen(self) -> None:
        """Eine weiße Wand und ein schwarzes Videobild ergeben beide
        lauter Nullen – sie sind sich nicht »ähnlich«, sie sagen nur
        nichts aus. Ohne diese Grenze bildeten sie eine Riesengruppe."""
        self.assertEqual(gruppen([("weiss", 0), ("schwarz", 0),
                                  ("leer", 0)]), [])
        self.assertEqual(gruppen([("voll", (1 << 64) - 1),
                                  ("auch", (1 << 64) - 1)]), [])


class NichtssagendeFingerabdruecke(unittest.TestCase):
    """Ein Fingerabdruck kann viele Bit haben und trotzdem nichts sagen.

    Der Fall aus einem echten Bestand: Zwei Aufnahmen mit schlichtem
    Hell-Dunkel-Verlauf ergaben beide ``00001111``, achtmal
    untereinander – 32 gesetzte Bit, aber keine senkrechte Struktur.
    Die Bilder stammten aus verschiedenen Jahren und zeigten
    Verschiedenes; die Suche spannte sie trotzdem zusammen.
    """

    def test_einfarbig_ist_nichtssagend(self) -> None:
        from wolkenernte.aehnlich import aussagekraeftig
        self.assertFalse(aussagekraeftig(0))
        self.assertFalse(aussagekraeftig((1 << 64) - 1))

    def test_lauter_gleiche_zeilen_sind_nichtssagend(self) -> None:
        from wolkenernte.aehnlich import aussagekraeftig
        # 0b00001111, achtmal untereinander.
        self.assertFalse(aussagekraeftig(0x0F0F0F0F0F0F0F0F))

    def test_zwei_verschiedene_zeilen_reichen_nicht(self) -> None:
        from wolkenernte.aehnlich import aussagekraeftig
        self.assertFalse(aussagekraeftig(0x0F0FF0F00F0FF0F0))

    def test_echte_struktur_zaehlt(self) -> None:
        from wolkenernte.aehnlich import aussagekraeftig
        self.assertTrue(aussagekraeftig(MUSTER_A))

    def test_gleichfoermige_bilder_bilden_keine_gruppe(self) -> None:
        """Der Fall aus dem echten Bestand: zwei Verläufe, kein Motiv."""
        self.assertEqual(gruppen([("a", 0x0F0F0F0F0F0F0F0F),
                                  ("b", 0x0F0F0F0F0F0F0F0E)]), [])


if __name__ == "__main__":
    unittest.main()

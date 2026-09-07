"""Der selbstgebaute Zerleger.

Er läuft nur beim Bauen, aber ein Fehler darin wäre trotzdem teuer: Die
Zahlenreihen, die er erzeugt, wandern ins Repository und werden nie
wieder nachgerechnet. Zerlegt er falsch, zeigen die Schlagwörter für
immer daneben – ohne dass irgendwo eine Fehlermeldung erschiene.

Die Zerlegungen unten stammen aus einem Abgleich mit dem echten
Zerleger von Hugging Face: 455 Sätze, null Abweichungen. Sie stehen
hier fest, damit der Abgleich nicht bei jedem Testlauf ein
Rust-Paket braucht.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from werkzeuge.clip_zerleger import ANFANG, ENDE, WOERTER, Zerleger, saeubern

#: Wo der Zerleger liegt, wenn das Modell schon geholt wurde.
ECHTER = Path.home() / ".local/share/WOLKENErnte/modelle/tokenizer.json"

#: Nachgerechnet gegen ``tokenizers.Tokenizer``.
BEKANNT = {
    "a photo of a cat.":
        [49406, 320, 1125, 539, 320, 2368, 269, 49407],
    "a photo of a beach.":
        [49406, 320, 1125, 539, 320, 2117, 269, 49407],
    "a photo of sand and sea at the shore.":
        [49406, 320, 1125, 539, 5094, 537, 2102, 536, 518, 5928, 269, 49407],
    "a photo of knitting or sewing.":
        [49406, 320, 1125, 539, 18863, 541, 15974, 269, 49407],
    "the sun setting over the horizon":
        [49406, 518, 2176, 5264, 962, 518, 11920, 49407],
    # Der Apostroph: *don't* darf nicht als *don* und *t* zerfallen.
    "don't stop":
        [49406, 847, 713, 1691, 49407],
    # Die Ziffer steht für sich, 273 ist die 2.
    "a photo of 2 dogs.":
        [49406, 320, 1125, 539, 273, 3255, 269, 49407],
}


class DieZerlegungInWoerter(unittest.TestCase):
    """Der Ausdruck, an dem ein erster Anlauf danebenlag.

    Er verschluckte **jedes Satzzeichen**: Die Wörter waren alle
    richtig, nur der Schlusspunkt fehlte – und damit hätte das Modell
    andere Sätze gesehen als im Training. Aufgefallen ist es nur, weil
    gegen den echten Zerleger geprüft wurde.
    """

    def test_satzzeichen_bleiben(self) -> None:
        self.assertEqual(WOERTER.findall("a cat."), ["a", "cat", "."])

    def test_ziffern_einzeln(self) -> None:
        """``\\p{N}`` steht für **eine** Ziffer, nicht für eine Zahl."""
        self.assertEqual(WOERTER.findall("2024"), ["2", "0", "2", "4"])

    def test_apostroph_bleibt_am_wort(self) -> None:
        self.assertEqual(WOERTER.findall("don't"), ["don", "'t"])

    def test_unterstrich_gilt_als_satzzeichen(self) -> None:
        """``\\w`` schließt ihn ein, ``\\p{L}`` und ``\\p{N}`` nicht –
        er muss darum ausdrücklich zu den Satzzeichen."""
        self.assertEqual(WOERTER.findall("a_b"), ["a", "_", "b"])


class DasSaeubern(unittest.TestCase):
    def test_kleinschreibung(self) -> None:
        self.assertEqual(saeubern("A Photo"), "a photo")

    def test_leerraum_wird_zusammengezogen(self) -> None:
        self.assertEqual(saeubern("  a\n\tphoto  "), "a photo")

    def test_html_wird_aufgeloest(self) -> None:
        self.assertEqual(saeubern("caf&eacute;"), "café")


@unittest.skipUnless(ECHTER.is_file(), "tokenizer.json nicht vorhanden")
class DerZerlegerAmEchtenWortschatz(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.zerleger = Zerleger.aus_datei(ECHTER)

    def test_bekannte_zerlegungen(self) -> None:
        for satz, erwartet in BEKANNT.items():
            with self.subTest(satz):
                self.assertEqual(self.zerleger.zahlen(satz), erwartet)

    def test_anfang_und_ende(self) -> None:
        zahlen = self.zerleger.zahlen("a cat")
        self.assertEqual(zahlen[0], self.zerleger.wortschatz[ANFANG])
        self.assertEqual(zahlen[-1], self.zerleger.wortschatz[ENDE])

    def test_alle_fragen_passen_in_siebenundsiebzig(self) -> None:
        """Was länger wäre, würde abgeschnitten – lautlos."""
        from wolkenernte.bilderkennung import fragen
        from wolkenernte.begriffe import VORLAGEN

        for vorlage in VORLAGEN:
            for frage in fragen():
                satz = vorlage.format(frage)
                with self.subTest(satz):
                    self.assertLessEqual(len(self.zerleger.zahlen(satz)), 77)

    def test_leerer_satz(self) -> None:
        self.assertEqual(len(self.zerleger.zahlen("")), 2)


class DerAufbauAusDerDatei(unittest.TestCase):
    def test_verschmelzungen_als_text_oder_paar(self) -> None:
        """Ältere und neuere ``tokenizer.json`` schreiben die
        Verschmelzungen verschieden: als ``"a b"`` oder als
        ``["a", "b"]``. Beides muss gehen."""
        for merges in ([["a", "b</w>"]], ["a b</w>"]):
            with self.subTest(merges=merges):
                with tempfile.TemporaryDirectory() as ordner:
                    datei = Path(ordner) / "t.json"
                    datei.write_text(json.dumps({"model": {
                        "vocab": {ANFANG: 0, ENDE: 1, "a": 2, "b</w>": 3,
                                  "ab</w>": 4},
                        "merges": merges}}), encoding="utf-8")
                    zerleger = Zerleger.aus_datei(datei)
                    self.assertEqual(zerleger.zahlen("ab"), [0, 4, 1])


if __name__ == "__main__":
    unittest.main()

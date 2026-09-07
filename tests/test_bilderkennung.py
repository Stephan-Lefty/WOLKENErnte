"""Aus Ähnlichkeiten werden deutsche Schlagwörter.

Diese Tests brauchen **kein Modell**. Sie füttern die Auswertung mit
ausgedachten Ähnlichkeiten und prüfen, was dabei herauskommt – genau
die Rechnung, die zwischen dem Modell und der Datenbank steht.
"""

from __future__ import annotations

import unittest

from wolkenernte.begriffe import GRUPPEN, VORLAGEN, alle_begriffe, namen
from wolkenernte.bilderkennung import anteile, auswerten, fragen, je_begriff
from wolkenernte.schlagworte import HOECHSTENS, begrenzen


#: Womit ein solches Modell tatsächlich antwortet.
#:
#: **Nicht mit 0 und 1.** Ein CLIP-artiges Modell gibt für *jede* Frage
#: eine Ähnlichkeit um 0,2 zurück, auch für die abwegigste; der Sieger
#: liegt um Hundertstel vorn, nicht um Zehntel. Ein erster Anlauf
#: prüfte mit einem Vorsprung von 0,16 – damit wäre jede Schwelle
#: erfüllt gewesen, und die Tests hätten nichts nachgewiesen.
GRUNDRAUSCHEN = 0.22
DEUTLICH = 0.03    # so viel Vorsprung reicht: das Modell ist sich sicher
KNAPP = 0.008      # so viel nicht: das könnte Zufall sein


def _flau(wert: float = GRUNDRAUSCHEN) -> dict[str, float]:
    """Alle Fragen gleich lau – kein Bild, auf dem etwas zu sehen ist."""
    return {frage: wert for frage in fragen()}


def _mit(**vorspruenge: float) -> dict[str, float]:
    """Ein Feld aus Grundrauschen, in dem einzelne Begriffe vorn liegen.

    Die Schlüssel sind deutsche Begriffsnamen, die Werte der
    **Vorsprung** vor dem Grundrauschen – nicht die Ähnlichkeit selbst.
    So steht in jedem Test, worum es geht: wie deutlich sich das Modell
    festlegt.
    """
    werte = _flau()
    for gruppe in GRUPPEN:
        for begriff in gruppe.begriffe:
            if begriff.name in vorspruenge:
                for frage in begriff.fragen:
                    werte[frage] = GRUNDRAUSCHEN + vorspruenge[begriff.name]
    return werte


class DieBegriffsliste(unittest.TestCase):
    def test_jeder_begriff_hat_fragen(self) -> None:
        for gruppe in GRUPPEN:
            for begriff in gruppe.begriffe:
                with self.subTest(begriff.name):
                    self.assertTrue(begriff.fragen)

    def test_namen_sind_eindeutig(self) -> None:
        """Zweimal derselbe Name in zwei Gruppen hieße: ein Bild kann
        dasselbe Wort doppelt bekommen."""
        alle = [b.name for g in GRUPPEN for b in g.begriffe]
        self.assertEqual(sorted(alle), sorted(set(alle)))

    def test_fragen_sind_eindeutig(self) -> None:
        """Die Fragen sind die Schlüssel der Auswertung. Eine doppelte
        Frage stünde für zwei Begriffe und wäre nicht mehr zuzuordnen."""
        alle = [f for _, _, f in alle_begriffe()]
        self.assertEqual(sorted(alle), sorted(set(alle)))

    def test_deutsche_namen(self) -> None:
        """Stichprobe: Die Ausgabe ist deutsch, die Frage englisch."""
        self.assertIn("Sonnenuntergang", namen())
        self.assertIn("Nahaufnahme", namen())
        self.assertIn("a sunset", fragen())

    def test_vorlagen_haben_eine_stelle(self) -> None:
        for vorlage in VORLAGEN:
            with self.subTest(vorlage):
                self.assertIn("{}", vorlage)

    def test_reihenfolge_haelt_zusammen(self) -> None:
        """``fragen()`` und ``alle_begriffe()`` müssen Zeile für Zeile
        dasselbe sagen – die vorberechneten Zahlen liegen in dieser
        Ordnung."""
        self.assertEqual(fragen(), [f for _, _, f in alle_begriffe()])


class DieUmrechnung(unittest.TestCase):
    def test_anteile_ergeben_eins(self) -> None:
        werte = {"a": 0.30, "b": 0.22, "c": 0.19}
        self.assertAlmostEqual(sum(anteile(werte)), 1.0)

    def test_der_groesste_gewinnt(self) -> None:
        gerechnet = anteile({"a": 0.19, "b": 0.31, "c": 0.20})
        self.assertEqual(max(range(3), key=lambda i: gerechnet[i]), 1)

    def test_kein_ueberlauf(self) -> None:
        """Bei einer Skala von 100 wäre ``exp()`` ohne Abzug des
        Größten sicher übergelaufen."""
        self.assertAlmostEqual(sum(anteile({"a": 4.0, "b": 0.1})), 1.0)

    def test_leere_gruppe(self) -> None:
        self.assertEqual(anteile({}), [])

    def test_mittelwert_ueber_die_fragen(self) -> None:
        gruppe = GRUPPEN[0]
        begriff = gruppe.begriffe[0]
        werte = _flau()
        werte[begriff.fragen[0]] = GRUNDRAUSCHEN + 0.06
        gemittelt = je_begriff(gruppe, werte)
        erwartet = GRUNDRAUSCHEN + 0.06 / len(begriff.fragen)
        self.assertAlmostEqual(gemittelt[begriff.name], erwartet)


class DieAuswertung(unittest.TestCase):
    def test_ein_deutlicher_treffer(self) -> None:
        woerter = auswerten(_mit(Strand=DEUTLICH))
        self.assertIn("Strand", [w.name for w in woerter])

    def test_alles_flau_gibt_nichts(self) -> None:
        """Ein Bild, auf dem nichts Bestimmtes zu erkennen ist, bekommt
        lieber gar kein Wort als ein geratenes."""
        self.assertEqual(auswerten(_flau()), [])

    def test_knapper_vorsprung_reicht_nicht(self) -> None:
        """Der eigentliche Zweck der Schwelle.

        Acht Tausendstel Vorsprung vor vierundzwanzig Mitbewerbern ist
        kein Befund, sondern Rauschen. Ohne diesen Test wäre nie
        aufgefallen, ob die Schwellen überhaupt etwas bewirken – ein
        erster Anlauf prüfte mit einem so großen Vorsprung, dass jede
        Schwelle erfüllt gewesen wäre.
        """
        woerter = auswerten(_mit(Strand=KNAPP))
        self.assertNotIn("Strand", [w.name for w in woerter])

    def test_hoechstens_eins_je_gruppe(self) -> None:
        """Sonst fräßen fünf Verwandte alle fünf Plätze: *Strand, Meer,
        Küste, Sand, Urlaub* beschreibt ein Bild nicht fünfmal besser
        als *Strand*."""
        woerter = auswerten(_mit(Strand=0.05, Meer=0.045, See=0.04))
        aus_dem_ort = [w for w in woerter if w.name in ("Strand", "Meer", "See")]
        self.assertEqual(len(aus_dem_ort), 1)

    def test_motive_duerfen_zu_zweit(self) -> None:
        """Ein Bild kann ein Kind *und* einen Hund zeigen – anders als
        beim Ort schließen sich diese Antworten nicht aus."""
        woerter = auswerten(_mit(Kind=0.05, Hund=0.048))
        namen_der = [w.name for w in woerter]
        self.assertIn("Kind", namen_der)
        self.assertIn("Hund", namen_der)

    def test_verschiedene_gruppen_nebeneinander(self) -> None:
        woerter = auswerten(
            _mit(Strand=DEUTLICH, Kind=DEUTLICH, Sonnenuntergang=DEUTLICH))
        gefunden = {w.name for w in woerter}
        self.assertIn("Strand", gefunden)
        self.assertIn("Kind", gefunden)
        self.assertIn("Sonnenuntergang", gefunden)

    def test_die_quelle_heisst_bild(self) -> None:
        """Nur so lässt sich die Bilderkennung später wiederholen, ohne
        die abgeleiteten Schlagwörter mitzureißen."""
        woerter = auswerten(_mit(Strand=DEUTLICH))
        self.assertTrue(all(w.quelle == "bild" for w in woerter))

    def test_sicherheit_ist_der_anteil(self) -> None:
        woerter = auswerten(_mit(Strand=DEUTLICH))
        strand = next(w for w in woerter if w.name == "Strand")
        self.assertGreater(strand.sicherheit, 0.22)
        self.assertLessEqual(strand.sicherheit, 1.0)

    def test_fehlende_fragen_stuerzen_nicht_ab(self) -> None:
        """Eine unvollständige Zahlenreihe – etwa aus einer älteren
        Fassung – darf keinen Absturz geben."""
        werte = _mit(Strand=DEUTLICH)
        for frage in list(werte)[:20]:
            del werte[frage]
        auswerten(werte)

    def test_nie_mehr_als_fuenf(self) -> None:
        """Auch wenn jede Gruppe etwas findet, bleiben es fünf."""
        viele = auswerten(_mit(
            Strand=0.05, Kind=0.05, Hund=0.048, Hochzeit=0.06,
            Sonnenuntergang=0.06, Nahaufnahme=0.06))
        self.assertLessEqual(len(begrenzen(viele)), HOECHSTENS)


if __name__ == "__main__":
    unittest.main()

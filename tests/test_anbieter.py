"""Die Anbietertabelle darf nicht mehr versprechen, als sie hält."""

from __future__ import annotations

import unittest

from wolkenernte.anbieter import (
    ANBIETER,
    NACH_KENNUNG,
    Weg,
    darf_loeschen,
    nur_lesend,
    vollstaendige,
)


class TabelleIstSchluessig(unittest.TestCase):
    def test_kennungen_sind_eindeutig(self) -> None:
        kennungen = [a.kennung for a in ANBIETER]
        self.assertEqual(len(kennungen), len(set(kennungen)))

    def test_jeder_anbieter_hat_einen_hinweis(self) -> None:
        for a in ANBIETER:
            with self.subTest(a.kennung):
                self.assertTrue(a.hinweis.strip(), "Hinweistext fehlt")

    def test_wer_nicht_auflisten_kann_kann_auch_nicht_laden(self) -> None:
        """Rückwärts geht es nicht: Was man nicht sieht, holt man nicht."""
        for a in ANBIETER:
            with self.subTest(a.kennung):
                if not a.auflisten:
                    self.assertFalse(a.laden)

    def test_loeschen_setzt_auflisten_voraus(self) -> None:
        """Blind löschen gibt es nicht – erst sehen, dann entscheiden."""
        for a in ANBIETER:
            with self.subTest(a.kennung):
                if a.loeschen:
                    self.assertTrue(a.auflisten)

    def test_ohne_zugang_kann_nichts(self) -> None:
        for a in ANBIETER:
            with self.subTest(a.kennung):
                if a.weg is Weg.KEINER:
                    self.assertFalse(a.auflisten or a.laden or a.loeschen)

    def test_takeout_kann_nicht_loeschen(self) -> None:
        """Ein Archiv, das der Anwender selbst anfordert, ist eine
        Kopie. Daraus lässt sich beim Anbieter nichts entfernen."""
        for a in ANBIETER:
            with self.subTest(a.kennung):
                if a.weg is Weg.TAKEOUT:
                    self.assertFalse(a.loeschen)


class DieBekanntenGrenzen(unittest.TestCase):
    """Festgenagelt, damit es niemand aus Versehen »repariert«.

    Diese drei Fälle sind der Grund, warum es dieses Modul gibt. Wenn
    einer davon eines Tages wirklich möglich wird, soll der Test
    fehlschlagen und jemanden zwingen, den Beleg in ``docs/anbieter.md``
    nachzutragen – statt dass die Zusage stillschweigend hereinrutscht.
    """

    def test_google_fotos_ist_nicht_erreichbar(self) -> None:
        a = NACH_KENNUNG["google-fotos"]
        self.assertEqual(a.weg, Weg.TAKEOUT)
        self.assertFalse(a.loeschen)

    def test_icloud_fotos_ist_nur_lesbar(self) -> None:
        a = NACH_KENNUNG["icloud-fotos"]
        self.assertTrue(a.laden)
        self.assertFalse(a.loeschen)

    def test_proton_fotos_ist_gar_nicht_erreichbar(self) -> None:
        self.assertEqual(NACH_KENNUNG["proton-fotos"].weg, Weg.KEINER)


class DerLoeschknopf(unittest.TestCase):
    def test_unbekannter_anbieter_darf_nicht_loeschen(self) -> None:
        """Die vorsichtige Seite des Irrtums: Wer die Tabelle beim
        Hinzufügen vergisst, bekommt kein Löschen geschenkt."""
        self.assertFalse(darf_loeschen("gibtsnicht"))

    def test_bekannte_anbieter_stimmen_mit_der_tabelle_ueberein(self) -> None:
        for a in ANBIETER:
            with self.subTest(a.kennung):
                self.assertEqual(darf_loeschen(a.kennung), a.loeschen)


class DieAuswahlfunktionen(unittest.TestCase):
    def test_vollstaendige_koennen_wirklich_alles(self) -> None:
        for a in vollstaendige():
            self.assertTrue(a.auflisten and a.laden and a.loeschen)

    def test_es_gibt_ueberhaupt_vollstaendige(self) -> None:
        """Sonst wäre das ganze Programm sinnlos."""
        self.assertGreater(len(vollstaendige()), 0)

    def test_nur_lesend_holt_aber_raeumt_nicht_auf(self) -> None:
        for a in nur_lesend():
            self.assertTrue(a.laden)
            self.assertFalse(a.loeschen)

    def test_icloud_fotos_ist_der_bekannte_zwischenfall(self) -> None:
        self.assertIn(NACH_KENNUNG["icloud-fotos"], nur_lesend())


if __name__ == "__main__":
    unittest.main()

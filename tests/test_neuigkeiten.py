"""Nachsehen, ob es eine neuere Fassung gibt.

**Kein Test ruft GitHub tatsächlich an.** Ein Testlauf, der ohne Netz
durchfällt, prüft die Leitung und nicht das Programm – und in der CI
wäre er eine Wackelkontakt-Quelle. Die Antwort wird darum eingesetzt.

Zwei Dinge sind hier leicht falsch: der Vergleich zweier Fassungen (als
Text verglichen ist 0.10.0 kleiner als 0.4.1) und die Frage, was
passiert, wenn das Netz fehlt.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from wolkenernte import neuigkeiten
from wolkenernte.neuigkeiten import (
    NeuigkeitenFehler,
    ist_neuer,
    neueste,
    zerlegen,
)


def _antwort(**felder):
    """Eine GitHub-Antwort vortäuschen, wie ``urlopen`` sie liefert."""
    daten = {
        "tag_name": "v0.4.1",
        "html_url": "https://example.invalid/releases/v0.4.1",
        "published_at": "2026-09-09T09:35:45Z",
    }
    daten.update(felder)
    roh = json.dumps(daten).encode("utf-8")

    def oeffnen(anfrage, timeout=None):
        oeffnen.anfrage = anfrage
        oeffnen.frist = timeout
        return io.BytesIO(roh)

    return oeffnen


class EineFassungZerlegen(unittest.TestCase):
    def test_das_v_faellt_weg(self) -> None:
        self.assertEqual(zerlegen("v0.4.1"), (0, 4, 1))
        self.assertEqual(zerlegen("0.4.1"), (0, 4, 1))

    def test_leerzeichen_stoeren_nicht(self) -> None:
        self.assertEqual(zerlegen(" v1.2.3 "), (1, 2, 3))

    def test_ein_anhaengsel_wird_gekuerzt(self) -> None:
        self.assertEqual(zerlegen("1.0.0rc1"), (1, 0, 0))

    def test_unterschiedlich_viele_stellen(self) -> None:
        self.assertEqual(zerlegen("1.2"), (1, 2))
        self.assertEqual(zerlegen("1"), (1,))


class WelcheIstNeuer(unittest.TestCase):
    def test_der_gewoehnliche_fall(self) -> None:
        self.assertTrue(ist_neuer("0.4.1", "0.4.0"))
        self.assertTrue(ist_neuer("0.5.0", "0.4.9"))
        self.assertTrue(ist_neuer("1.0.0", "0.9.9"))

    def test_gleich_ist_nicht_neuer(self) -> None:
        self.assertFalse(ist_neuer("0.4.1", "0.4.1"))
        self.assertFalse(ist_neuer("v0.4.1", "0.4.1"))

    def test_aelter_ist_nicht_neuer(self) -> None:
        self.assertFalse(ist_neuer("0.3.0", "0.4.1"))

    def test_zehn_ist_groesser_als_vier(self) -> None:
        """**Die Falle.** Als Text verglichen stünde »1« vor »4«, und
        der Hinweis bliebe genau dann aus, wenn er am nötigsten ist."""
        self.assertTrue(ist_neuer("0.10.0", "0.4.1"))
        self.assertFalse(ist_neuer("0.4.1", "0.10.0"))
        self.assertTrue(ist_neuer("1.0.0", "0.99.0"))

    def test_mehr_stellen_bei_gleichem_anfang(self) -> None:
        self.assertTrue(ist_neuer("0.4.1", "0.4"))
        self.assertFalse(ist_neuer("0.4", "0.4.1"))


class DieAnfrage(unittest.TestCase):
    def test_liest_die_fassung_heraus(self) -> None:
        neu = neueste(oeffnen=_antwort())
        self.assertEqual(neu.fassung, "0.4.1")
        self.assertEqual(neu.erschienen, "2026-09-09")
        self.assertIn("releases", neu.adresse)

    def test_eine_kennung_muss_mit(self) -> None:
        """Ohne ``User-Agent`` weist GitHub die Anfrage ab – und der
        Fehler käme erst beim Anwender heraus, nie im Test."""
        oeffnen = _antwort()
        neueste(oeffnen=oeffnen)
        kopf = oeffnen.anfrage.headers
        self.assertIn("WOLKENErnte", kopf.get("User-agent", ""))

    def test_eine_frist_ist_gesetzt(self) -> None:
        """Sonst hängt der Befehl an einem stummen Server für immer."""
        oeffnen = _antwort()
        neueste(oeffnen=oeffnen)
        self.assertEqual(oeffnen.frist, neuigkeiten.FRIST)

    def test_es_wird_nur_gelesen(self) -> None:
        """Kein Rumpf, keine Angaben über das Archiv – GitHub sieht
        nichts als die Anfrage selbst."""
        oeffnen = _antwort()
        neueste(oeffnen=oeffnen)
        self.assertIsNone(oeffnen.anfrage.data)
        self.assertEqual(oeffnen.anfrage.get_method(), "GET")


class WennEsNichtGeht(unittest.TestCase):
    """Jeder Fall endet mit einem Satz, den man lesen kann – nicht mit
    einem Stapelabzug."""

    def _fehlschlag(self, ausloeser):
        def oeffnen(anfrage, timeout=None):
            raise ausloeser
        with self.assertRaises(NeuigkeitenFehler) as gefangen:
            neueste(oeffnen=oeffnen)
        return str(gefangen.exception)

    def test_kein_netz(self) -> None:
        text = self._fehlschlag(
            urllib.error.URLError("Name or service not known"))
        self.assertIn("Keine Verbindung", text)

    def test_github_antwortet_mit_einem_fehler(self) -> None:
        text = self._fehlschlag(urllib.error.HTTPError(
            neuigkeiten.ZIEL, 403, "rate limit", {}, None))
        self.assertIn("403", text)

    def test_die_antwort_ist_kein_json(self) -> None:
        def oeffnen(anfrage, timeout=None):
            return io.BytesIO(b"<html>Wartungsarbeiten</html>")
        with self.assertRaises(NeuigkeitenFehler):
            neueste(oeffnen=oeffnen)

    def test_es_gibt_noch_keine_veroeffentlichung(self) -> None:
        with self.assertRaises(NeuigkeitenFehler) as gefangen:
            neueste(oeffnen=_antwort(tag_name=None))
        self.assertIn("keine Fassung", str(gefangen.exception))


class DerBefehl(unittest.TestCase):
    """Die drei Rückgabewerte, an denen ein Skript sich orientieren kann."""

    def _laufen(self, **felder) -> tuple[int, str]:
        # Ersetzt wird ``urlopen``, nicht ``neueste`` – so läuft die
        # echte Funktion mit, und ein erster Anlauf, der ``neueste``
        # ersetzte, rief sich selbst.
        gedruckt: list[str] = []
        with mock.patch.object(neuigkeiten.urllib.request, "urlopen",
                               _antwort(**felder)), \
                mock.patch("builtins.print",
                           lambda *t, **r: gedruckt.append(" ".join(map(str, t)))):
            wert = neuigkeiten.bericht()
        return wert, "\n".join(gedruckt)

    def test_null_wenn_alles_aktuell_ist(self) -> None:
        wert, text = self._laufen(tag_name=f"v{neuigkeiten.__version__}")
        self.assertEqual(wert, 0)
        self.assertIn("aktuell", text)

    def test_zwei_wenn_es_etwas_neueres_gibt(self) -> None:
        wert, text = self._laufen(tag_name="v99.0.0")
        self.assertEqual(wert, 2)
        self.assertIn("99.0.0", text)
        self.assertIn("CHANGELOG", text)

    def test_null_auch_wenn_die_eigene_neuer_ist(self) -> None:
        """Wer aus dem Quelltext arbeitet, hat die Marke gesetzt und den
        Release noch nicht angelegt. »Aktuell« wäre nicht falsch, sagte
        aber nicht, was los ist."""
        wert, text = self._laufen(tag_name="v0.0.1")
        self.assertEqual(wert, 0)
        self.assertIn("neuer als die veröffentlichte", text)
        self.assertNotIn("Es gibt eine neuere Fassung", text)

    def test_eins_wenn_es_nicht_geht(self) -> None:
        gedruckt: list[str] = []

        def platzen():
            raise NeuigkeitenFehler("Keine Verbindung zu GitHub: nix")

        with mock.patch.object(neuigkeiten, "neueste", platzen), \
                mock.patch("builtins.print",
                           lambda *t, **r: gedruckt.append(" ".join(map(str, t)))):
            wert = neuigkeiten.bericht()
        self.assertEqual(wert, 1)
        self.assertIn("Keine Verbindung", "\n".join(gedruckt))

    def test_die_eigene_fassung_steht_immer_dabei(self) -> None:
        _, text = self._laufen()
        self.assertIn(neuigkeiten.__version__, text)


class DerBefehlIstAngeschlossen(unittest.TestCase):
    """Dass ein Unterbefehl im Zerleger steht, heißt nicht, dass er
    irgendwo ankommt – dieselbe Lehre wie bei ``--ohne-unterordner``."""

    def test_neuigkeiten_ruft_den_bericht(self) -> None:
        from wolkenernte.__main__ import main

        with mock.patch.object(neuigkeiten, "bericht",
                               return_value=0) as gerufen:
            self.assertEqual(main(["neuigkeiten"]), 0)
        gerufen.assert_called_once()

    def test_ohne_netz_kein_absturz(self) -> None:
        """Der Rückgabewert kommt bis nach draußen, statt dass eine
        Ausnahme durchschlägt."""
        from wolkenernte.__main__ import main

        def platzen(*a, **r):
            raise urllib.error.URLError("kein Netz")

        with mock.patch.object(neuigkeiten.urllib.request, "urlopen", platzen), \
                mock.patch("builtins.print"):
            self.assertEqual(main(["neuigkeiten"]), 1)


if __name__ == "__main__":
    unittest.main()

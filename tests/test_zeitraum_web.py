"""Der Zeitraum im Browser – vom Adresszusatz bis zur fertigen Seite.

**Warum diese Datei getrennt von ``test_zeitraum.py`` steht:** Dort
geht es um das Fundament, hier um den Weg dorthin. Genau dieser Weg hat
schon einmal Fehler getragen, die grün getestet waren – der Schalter
``--ohne-unterordner`` war angelegt, beschrieben und kam nirgends an.
Geprüft wird darum, **was beim Aufgerufenen ankommt**.

Der Behandler wird ohne Steckdose gebaut: ``_seite`` fängt das HTML ab,
statt es zu versenden. Ein echter Server würde den Testlauf mit einem
offenen Port belasten, und ein früherer Anlauf hat damit nach den
Qt-Tests den ganzen Lauf zum Absturz gebracht.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wolkenernte.bestandsliste import Bestandsliste, Bild
from wolkenernte.web import dienst, seiten


def _liste() -> Bestandsliste:
    liste = Bestandsliste.__new__(Bestandsliste)
    liste.archiv = Path(tempfile.mkdtemp())
    liste.bilder = [
        Bild(pfad="2023/a.jpg", groesse=1000, zeit=datetime(2023, 5, 1, 8, 0)),
        Bild(pfad="2024/b.jpg", groesse=1000, zeit=datetime(2024, 6, 15, 8, 0)),
        Bild(pfad="2024/c.mp4", groesse=1000, zeit=datetime(2024, 6, 30, 23, 59),
             ist_video=True),
        Bild(pfad="2025/d.jpg", groesse=1000, zeit=datetime(2025, 2, 2, 8, 0)),
    ]
    return liste


def _seite_holen(**parameter: str) -> str:
    """Eine Rasterseite bauen, wie sie ein Aufruf von ``/raster`` ergäbe."""
    behandler = object.__new__(dienst.Behandler)
    gefangen: list[str] = []
    behandler._seite = lambda html, code=200: gefangen.append(html)

    werte = {name: [wert] for name, wert in parameter.items()}

    def eins(name: str) -> str | None:
        return werte.get(name, [None])[0] or None

    behandler._raster(_liste(), werte, eins)
    return gefangen[0]


class DerZeitraumKommtAn(unittest.TestCase):
    def test_grenzt_ein(self) -> None:
        html = _seite_holen(von="2024-06-01", bis="2024-06-30")
        self.assertIn("2 Dateien", html)

    def test_der_letzte_tag_gehoert_dazu(self) -> None:
        """``c.mp4`` liegt am 30.06.2024 um 23:59."""
        self.assertIn("2024/c.mp4", _seite_holen(von="2024-06-30",
                                                 bis="2024-06-30"))

    def test_deutsche_schreibweise_geht_auch(self) -> None:
        """Für den, der es in die Adresszeile tippt – das Formular
        selbst schickt immer ISO."""
        self.assertIn("2 Dateien", _seite_holen(von="1.6.2024",
                                                bis="30.06.2024"))

    def test_ein_jahr_meint_das_ganze_jahr(self) -> None:
        self.assertIn("2 Dateien", _seite_holen(von="2024", bis="2024"))

    def test_die_ueberschrift_nennt_den_zeitraum(self) -> None:
        """Sonst sieht eine eingegrenzte Ansicht aus wie der ganze
        Bestand, nur mit weniger Bildern."""
        html = _seite_holen(von="2024-06-01", bis="2024-06-30")
        self.assertIn("01.06.2024 – 30.06.2024", html)

    def test_nur_eine_grenze_wird_auch_benannt(self) -> None:
        self.assertIn("ab 01.06.2024", _seite_holen(von="2024-06-01"))
        self.assertIn("bis 30.06.2024", _seite_holen(bis="2024-06-30"))


class WennDasDatumNichtZuLesenIst(unittest.TestCase):
    def test_es_wird_gesagt(self) -> None:
        """**Nicht stillschweigend übergehen.** Sonst zeigte die Seite
        den ganzen Bestand, und der Anwender hielte das für das
        Ergebnis seines Zeitraums."""
        html = _seite_holen(von="gestern")
        self.assertIn("kein Datum", html)

    def test_und_es_wird_nicht_gefiltert(self) -> None:
        self.assertIn("4 Dateien", _seite_holen(von="gestern"))

    def test_die_ueberschrift_behauptet_keinen_zeitraum(self) -> None:
        """Sonst stünde »ab gestern« über der Zahl des ganzen Bestands –
        ein sichtbarer Zustand, der dem tatsächlichen widerspricht."""
        self.assertNotIn("ab gestern", _seite_holen(von="gestern"))


class DasFormular(unittest.TestCase):
    def test_ein_kalender_kein_textfeld(self) -> None:
        """``type="date"`` bringt das Kalenderblatt des Browsers mit."""
        html = _seite_holen()
        self.assertIn('type="date" name="von"', html)
        self.assertIn('type="date" name="bis"', html)

    def test_der_wert_steht_in_iso_drin(self) -> None:
        """Das Feld nimmt nichts anderes an – wer ``01.06.2024`` in die
        Adresszeile tippt, sähe sonst ein leeres Feld, obwohl der
        Zeitraum gilt."""
        html = _seite_holen(von="01.06.2024")
        self.assertIn('name="von" value="2024-06-01"', html)

    def test_ein_jahr_wird_zum_ersten_januar(self) -> None:
        html = _seite_holen(von="2024", bis="2024")
        self.assertIn('name="von" value="2024-01-01"', html)
        self.assertIn('name="bis" value="2024-12-31"', html)

    def test_die_uebrigen_filter_bleiben_erhalten(self) -> None:
        """Wer im Jahr 2024 steht und einen Monat eingrenzt, will nicht
        plötzlich im ganzen Bestand stehen."""
        html = _seite_holen(jahr="2024", videos="1")
        self.assertIn('type="hidden" name="jahr" value="2024"', html)
        self.assertIn('type="hidden" name="videos" value="1"', html)

    def test_ohne_datum_wird_nicht_mitgenommen(self) -> None:
        """Bilder ohne Aufnahmedatum liegen in keinem Zeitraum – beides
        zusammen ergäbe immer null Treffer."""
        html = _seite_holen(ohnedatum="1")
        self.assertNotIn('name="ohnedatum"', html)

    def test_aufheben_erscheint_nur_wenn_etwas_gilt(self) -> None:
        self.assertNotIn("Zeitraum aufheben", _seite_holen())
        self.assertIn("Zeitraum aufheben", _seite_holen(von="2024"))


class BeimBlaettern(unittest.TestCase):
    """Der Zeitraum muss in die Seitenverweise – sonst steht man auf
    Seite 2 wieder im ganzen Bestand."""

    def test_die_verweise_tragen_den_zeitraum(self) -> None:
        liste = _liste()
        html = seiten.raster(
            liste, liste.bilder, seite=1, je_seite=2, jahr=None, album=None,
            zusatz="von=2024-06-01&bis=2024-06-30&", von="2024-06-01",
            bis="2024-06-30")
        self.assertIn("seite=2", html)
        for verweis in ("von=2024-06-01", "bis=2024-06-30"):
            with self.subTest(verweis):
                self.assertIn(verweis, html)

    def test_der_dienst_legt_ihn_dort_hinein(self) -> None:
        """Nicht der Text des Schalters wird geprüft, sondern was in
        der Adresse ankommt."""
        behandler = object.__new__(dienst.Behandler)
        gefangen: dict = {}
        behandler._seite = lambda html, code=200: None

        echt = seiten.raster

        def merken(*args, **rest):
            gefangen.update(rest)
            return echt(*args, **rest)

        seiten.raster = merken
        try:
            werte = {"von": ["2024-06-01"], "bis": ["2024-06-30"]}
            behandler._raster(_liste(), werte,
                              lambda n: werte.get(n, [None])[0] or None)
        finally:
            seiten.raster = echt

        self.assertIn("von=2024-06-01", gefangen["zusatz"])
        self.assertIn("bis=2024-06-30", gefangen["zusatz"])


if __name__ == "__main__":
    unittest.main()

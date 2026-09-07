"""Anmelden, durchsehen und holen – im Fenster.

**Bis hierher ging das alles nur auf der Kommandozeile.** Ein Programm,
das man erst im Terminal einrichten muss, hat seinen Zweck verfehlt;
diese Tests halten fest, dass der Weg durchs Fenster wirklich trägt.

Gegen das **echte rclone** mit dem ``local``-Backend: Es wird
tatsächlich aufgelistet und tatsächlich geerntet, nur eben aus einem
Ordner unter ``/tmp``. Für die Anmeldung selbst braucht es keine echte
Nextcloud – geprüft wird, dass ohne bewiesene Verbindung nichts
gespeichert wird.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from wolkenernte.einrichten import einrichten, nextcloud_adresse
from wolkenernte.rclone import Dienst, fassung, finden

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt
PYSIDE = importlib.util.find_spec("PySide6") is not None

if PYSIDE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class DieAdresseWirdZurechtgerueckt(unittest.TestCase):
    """Was der Anwender eintippt, ist selten das, was rclone braucht.

    Sie muss auf ``/remote.php/dav/files/BENUTZER/`` enden. Endet sie
    auf das ältere ``/remote.php/webdav/``, greift rclones Erkennung
    für stückweises Hochladen nicht – und Übertragungen scheitern erst
    später und ohne erkennbaren Zusammenhang.
    """

    def test_die_nackte_adresse(self) -> None:
        self.assertEqual(
            nextcloud_adresse("https://wolke.example", "anna"),
            "https://wolke.example/remote.php/dav/files/anna/")

    def test_mit_schraegstrich_am_ende(self) -> None:
        self.assertEqual(
            nextcloud_adresse("https://wolke.example/", "anna"),
            "https://wolke.example/remote.php/dav/files/anna/")

    def test_die_alte_webdav_form(self) -> None:
        self.assertEqual(
            nextcloud_adresse("https://wolke.example/remote.php/webdav", "anna"),
            "https://wolke.example/remote.php/dav/files/anna/")

    def test_eine_schon_vollstaendige_adresse(self) -> None:
        self.assertEqual(
            nextcloud_adresse(
                "https://wolke.example/remote.php/dav/files/anna/", "anna"),
            "https://wolke.example/remote.php/dav/files/anna/")


@unittest.skipUnless(PYSIDE and ECHTES_RCLONE, "PySide6 oder rclone fehlt")
class DieAnmeldung(unittest.TestCase):
    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        self.dialoge = []

    def tearDown(self) -> None:
        self.dialoge.clear()
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _dialog(self):
        """Der Dialog – und eine Fessel dafür.

        Ohne die eigene Liste sammelt Python ihn ein, sobald der Aufruf
        vorbei ist, und Qt meldet »Internal C++ object already
        deleted«.
        """
        from wolkenernte.fenster.wolken import ZugangAnlegen

        dialog = ZugangAnlegen(self.dienst)
        self.dialoge.append(dialog)
        return dialog

    def test_ohne_angaben_passiert_nichts(self) -> None:
        dialog = self._dialog()
        dialog.adresse.setText("")
        dialog.benutzer.setText("")
        dialog.kennwort.setText("")
        dialog._pruefen()
        self.assertIsNone(dialog.angelegt)
        self.assertIn("fehlt", dialog.meldung.text())

    def test_es_wird_gesagt_was_fehlt(self) -> None:
        dialog = self._dialog()
        dialog.adresse.setText("https://wolke.example")
        dialog.benutzer.setText("anna")
        dialog._pruefen()
        self.assertIn("App-Passwort", dialog.meldung.text())

    def test_das_kennwort_steht_nicht_im_klartext(self) -> None:
        from PySide6.QtWidgets import QLineEdit

        self.assertEqual(self._dialog().kennwort.echoMode(),
                         QLineEdit.EchoMode.Password)

    def test_eine_unerreichbare_wolke_wird_nicht_uebernommen(self) -> None:
        """**Erst der Beweis, dann der Eintrag.** Ein Zugang, der nur
        auf dem Papier existiert, führt später zu einer Fehlermeldung
        an einer Stelle, wo niemand mehr an die Anmeldung denkt.
        """
        dialog = self._dialog()
        dialog.name.setText("gibtsnicht")
        dialog.adresse.setText("https://wolke.invalid")
        dialog.benutzer.setText("anna")
        dialog.kennwort.setText("geheim")
        dialog._pruefen()
        self.assertIsNone(dialog.angelegt)
        self.assertIn("steht nicht", dialog.meldung.text())

    def test_der_hinweis_aufs_app_passwort_steht_da(self) -> None:
        """Der wichtigste Satz des Dialogs: Bei Zwei-Faktor nimmt
        Nextcloud das Kontokennwort über WebDAV gar nicht an."""
        dialog = self._dialog()
        texte = " ".join(
            k.text() for k in dialog.findChildren(type(dialog.meldung)))
        self.assertIn("App-Passwort", texte)
        self.assertIn("Kontokennwort", texte)


@unittest.skipUnless(PYSIDE and ECHTES_RCLONE, "PySide6 oder rclone fehlt")
class DasDurchsehen(unittest.TestCase):
    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")

        self.inhalt = self.tmp / "wolke"
        (self.inhalt / "Fotos" / "2024").mkdir(parents=True)
        (self.inhalt / "Dokumente").mkdir()
        for i in (1, 2, 3):
            (self.inhalt / "Fotos" / f"IMG_{i}.jpg").write_bytes(f"b{i}".encode())
        (self.inhalt / "Fotos" / "2024" / "IMG_9.jpg").write_bytes(b"neun")
        (self.inhalt / "Fotos" / "notiz.txt").write_bytes(b"kein Bild")

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        # **alias statt local.** Bei ``local`` wäre ``probe:`` die ganze
        # Platte, und der Baum begänne bei ``/``. Ein alias-Zugang zeigt
        # auf den Probenordner - damit ist ``probe:`` die Wurzel, genau
        # wie bei einer echten Wolke.
        einrichten(self.dienst, "probe", "alias",
                   angaben={"remote": str(self.inhalt)})
        self.dialoge = []

    def tearDown(self) -> None:
        self.dialoge.clear()
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _baum(self):
        """Der Dialog - und eine Fessel dafür.

        Ohne die eigene Liste sammelt Python ihn ein, sobald der Aufruf
        vorbei ist, und Qt meldet »Internal C++ object already
        deleted«.
        """
        from wolkenernte.fenster.wolken import WolkeDurchsehen

        dialog = WolkeDurchsehen(self.dienst, "probe")
        self.dialoge.append(dialog)
        return dialog

    def test_die_ordner_erscheinen(self) -> None:
        dialog = self._baum()
        wurzel = dialog.baum.topLevelItem(0)
        namen = {wurzel.child(i).text(0) for i in range(wurzel.childCount())}
        self.assertEqual(namen, {"Fotos", "Dokumente"})

    def test_nachgeladen_wird_erst_beim_aufklappen(self) -> None:
        """Ein Fotoarchiv hat hunderte Ordner; sie alle vorab zu holen
        hieße, minutenlang vor einem leeren Fenster zu sitzen."""
        dialog = self._baum()
        wurzel = dialog.baum.topLevelItem(0)
        fotos = next(wurzel.child(i) for i in range(wurzel.childCount())
                     if wurzel.child(i).text(0) == "Fotos")
        self.assertEqual(fotos.childCount(), 0)
        dialog._aufklappen(fotos)
        self.assertEqual(fotos.child(0).text(0), "2024")

    def test_die_zahl_der_bilder_steht_daneben(self) -> None:
        dialog = self._baum()
        wurzel = dialog.baum.topLevelItem(0)
        fotos = next(wurzel.child(i) for i in range(wurzel.childCount())
                     if wurzel.child(i).text(0) == "Fotos")
        dialog._aufklappen(fotos)
        # Drei Bilder, die Textdatei zählt nicht mit.
        self.assertEqual(fotos.text(1), "3")

    def test_zweimal_aufklappen_laedt_nicht_doppelt(self) -> None:
        dialog = self._baum()
        wurzel = dialog.baum.topLevelItem(0)
        vorher = wurzel.childCount()
        dialog._aufklappen(wurzel)
        self.assertEqual(wurzel.childCount(), vorher)

    def test_die_wahl_kommt_in_rclones_schreibweise_zurueck(self) -> None:
        dialog = self._baum()
        wurzel = dialog.baum.topLevelItem(0)
        fotos = next(wurzel.child(i) for i in range(wurzel.childCount())
                     if wurzel.child(i).text(0) == "Fotos")
        dialog.baum.setCurrentItem(fotos)
        dialog.mit_unterordnern.setChecked(False)
        dialog._holen()
        self.assertEqual(dialog.gewaehlt, "probe:Fotos")


@unittest.skipUnless(PYSIDE and ECHTES_RCLONE, "PySide6 oder rclone fehlt")
class DasHolen(unittest.TestCase):
    """Der Lauf selbst – im Hintergrundfaden, mit Signalen."""

    def setUp(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.app = QApplication.instance() or QApplication([])
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "konf.conf").write_text("")
        self.inhalt = self.tmp / "wolke"
        self.inhalt.mkdir()
        for i in (1, 2, 3):
            (self.inhalt / f"IMG_{i}.jpg").write_bytes(f"bild-{i}".encode())
        self.ziel = self.tmp / "archiv"

        self.dienst = Dienst.starten(self.tmp / "konf.conf")
        einrichten(self.dienst, "probe", "local")

    def tearDown(self) -> None:
        self.dienst.beenden()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _laufen(self, quelle: str):
        """Die Arbeit ohne Faden ausführen und die Signale einsammeln."""
        from wolkenernte.fenster.wolken import Arbeit

        arbeit = Arbeit(self.dienst, quelle, self.ziel)
        ergebnis: dict = {}
        arbeit.fertig.connect(lambda b: ergebnis.update(bilanz=b))
        arbeit.misslungen.connect(lambda t: ergebnis.update(fehler=t))
        arbeit.schritt.connect(
            lambda n, g, name: ergebnis.setdefault("schritte", []).append(n))
        arbeit.laufen()
        return arbeit, ergebnis

    def test_die_bilder_kommen_an(self) -> None:
        _, ergebnis = self._laufen(f"probe:{self.inhalt}")
        self.assertIn("bilanz", ergebnis)
        self.assertEqual(ergebnis["bilanz"].uebernommen, 3)
        self.assertTrue(list(self.ziel.rglob("IMG_1.jpg")))

    def test_der_fortschritt_wird_gemeldet(self) -> None:
        _, ergebnis = self._laufen(f"probe:{self.inhalt}")
        self.assertEqual(ergebnis["schritte"], [1, 2, 3])

    def test_ein_leerer_ordner_sagt_das(self) -> None:
        leer = self.tmp / "leer"
        leer.mkdir()
        _, ergebnis = self._laufen(f"probe:{leer}")
        self.assertIn("keine Bilder", ergebnis.get("fehler", ""))

    def test_abbrechen_laesst_das_schon_geholte_stehen(self) -> None:
        from wolkenernte.fenster.wolken import Arbeit

        arbeit = Arbeit(self.dienst, f"probe:{self.inhalt}", self.ziel)
        ergebnis: dict = {}
        arbeit.misslungen.connect(lambda t: ergebnis.update(fehler=t))
        # Nach dem ersten Bild abbrechen.
        arbeit.schritt.connect(
            lambda n, g, name: setattr(arbeit, "abbrechen", True))
        arbeit.laufen()
        self.assertIn("Abgebrochen", ergebnis.get("fehler", ""))
        self.assertTrue(list(self.ziel.rglob("*.jpg")))

    def test_ein_unbekannter_zugang_stuerzt_nicht_ab(self) -> None:
        _, ergebnis = self._laufen("gibtsnicht:irgendwo")
        self.assertIn("fehler", ergebnis)


if __name__ == "__main__":
    unittest.main()

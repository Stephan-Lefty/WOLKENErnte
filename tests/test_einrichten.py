"""Zugänge einrichten – und der ganze Weg gegen das echte rclone.

Die Klasse am Ende läuft nur, wenn rclone installiert ist. Sie benutzt
das ``local``-Backend: Das braucht keine Zugangsdaten, verhält sich für
die Schnittstelle aber wie jede Wolke. Damit lässt sich auflisten und
löschen wirklich durchspielen, statt es nur zu behaupten.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from wolkenernte.einrichten import (
    Abbruch,
    Frage,
    einrichten,
    nextcloud_adresse,
)
from wolkenernte.rclone import Dienst, RcloneFehler, fassung, finden

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt


class DieNextcloudAdresse(unittest.TestCase):
    """Sie muss auf ``/remote.php/dav/files/BENUTZER/`` enden.

    Endet sie auf das ältere ``/remote.php/webdav/``, greift rclones
    Erkennung für stückweises Hochladen nicht – und Übertragungen
    scheitern erst später, ohne erkennbaren Zusammenhang. rclones eigene
    Doku zeigt im Beispiel bis heute die alte Form.
    """

    ZIEL = "https://wolke.example/remote.php/dav/files/anna/"

    def test_blosse_adresse(self) -> None:
        self.assertEqual(nextcloud_adresse("https://wolke.example", "anna"),
                         self.ZIEL)

    def test_mit_schraegstrich_am_ende(self) -> None:
        self.assertEqual(nextcloud_adresse("https://wolke.example/", "anna"),
                         self.ZIEL)

    def test_alte_webdav_form_wird_ersetzt(self) -> None:
        self.assertEqual(
            nextcloud_adresse("https://wolke.example/remote.php/webdav/", "anna"),
            self.ZIEL,
        )

    def test_bereits_vollstaendig(self) -> None:
        self.assertEqual(nextcloud_adresse(self.ZIEL, "anna"), self.ZIEL)

    def test_falscher_benutzer_im_pfad_wird_ersetzt(self) -> None:
        """Wer die Adresse aus der Nextcloud-Oberfläche kopiert, hat dort
        womöglich einen anderen Benutzernamen stehen."""
        self.assertEqual(
            nextcloud_adresse(
                "https://wolke.example/remote.php/dav/files/berta/", "anna"),
            self.ZIEL,
        )

    def test_unterverzeichnis_bleibt(self) -> None:
        self.assertEqual(
            nextcloud_adresse("https://example.org/wolke", "anna"),
            "https://example.org/wolke/remote.php/dav/files/anna/",
        )


class DieFrage(unittest.TestCase):
    def test_aus_rclones_antwort(self) -> None:
        frage = Frage.aus_antwort({
            "Name": "user", "Help": "Benutzername.", "Required": True,
            "Type": "string", "Default": "",
        })
        self.assertEqual(frage.name, "user")
        self.assertTrue(frage.pflicht)
        self.assertFalse(frage.geheim)

    def test_kennwort_wird_erkannt(self) -> None:
        frage = Frage.aus_antwort({"Name": "pass", "IsPassword": True})
        self.assertTrue(frage.geheim)

    def test_auswahl_wird_uebernommen(self) -> None:
        frage = Frage.aus_antwort({
            "Name": "region", "Exclusive": True,
            "Examples": [{"Value": "global"}, {"Value": "us"}],
        })
        self.assertEqual(frage.auswahl, ["global", "us"])
        self.assertTrue(frage.nur_auswahl)

    def test_fehler_wird_durchgereicht(self) -> None:
        frage = Frage.aus_antwort({"Name": "code"}, "2FA codes can't be blank")
        self.assertIn("blank", frage.fehler)


class DasGespraech(unittest.TestCase):
    """Gegen einen nachgestellten Dienst, ohne rclone."""

    class FalscherDienst:
        def __init__(self, antworten: list[dict]) -> None:
            self.antworten = antworten
            self.aufrufe: list[dict] = []

        def rufen(self, weg: str, werte: dict | None = None, **_: object) -> dict:
            self.aufrufe.append(werte or {})
            return self.antworten.pop(0)

    def test_ohne_rueckfragen_ein_durchgang(self) -> None:
        dienst = self.FalscherDienst([{"State": "", "Option": None}])
        einrichten(dienst, "wolke", "webdav", angaben={"url": "https://x/"})
        self.assertEqual(len(dienst.aufrufe), 1)

    def test_angaben_werden_jedes_mal_mitgeschickt(self) -> None:
        """So steht es in rclones Doku zu ``--continue`` – und es ist die
        Sorte Fehler, die sich erst beim dritten Anbieter zeigt."""
        dienst = self.FalscherDienst([
            {"State": "*all-user", "Option": {"Name": "user"}},
            {"State": "", "Option": None},
        ])
        einrichten(dienst, "w", "webdav", angaben={"url": "https://x/"},
                   fragen=lambda f: "anna")
        for aufruf in dienst.aufrufe:
            self.assertEqual(aufruf["parameters"]["url"], "https://x/")

    def test_antwort_wandert_in_den_naechsten_aufruf(self) -> None:
        dienst = self.FalscherDienst([
            {"State": "*all-user", "Option": {"Name": "user"}},
            {"State": "", "Option": None},
        ])
        einrichten(dienst, "w", "webdav", fragen=lambda f: "anna")
        zweiter = dienst.aufrufe[1]["opt"]
        self.assertTrue(zweiter["continue"])
        self.assertEqual(zweiter["state"], "*all-user")
        self.assertEqual(zweiter["result"], "anna")

    def test_fehler_ohne_frage_wird_nicht_zum_absturz(self) -> None:
        """Der dritte Zustand, den rclones eigenes Beispielprogramm
        vergisst: iCloud antwortet so bei leerem 2FA-Code."""
        dienst = self.FalscherDienst([
            {"State": "2fa_do", "Option": None, "Error": "2FA codes can't be blank"},
            {"State": "", "Option": None},
        ])
        einrichten(dienst, "apfel", "iclouddrive", fragen=lambda f: "")
        self.assertEqual(dienst.aufrufe[1]["opt"]["state"], "2fa_do")
        self.assertEqual(dienst.aufrufe[1]["opt"]["result"], "")

    def test_abbruch_durch_den_anwender(self) -> None:
        dienst = self.FalscherDienst([
            {"State": "*all-user", "Option": {"Name": "user"}},
        ])
        with self.assertRaises(Abbruch):
            einrichten(dienst, "w", "webdav", fragen=lambda f: None)

    def test_frage_ohne_jemanden_der_antwortet(self) -> None:
        dienst = self.FalscherDienst([
            {"State": "*all-user", "Option": {"Name": "user"}},
        ])
        with self.assertRaises(RcloneFehler):
            einrichten(dienst, "w", "webdav")

    def test_endlosschleife_wird_abgebrochen(self) -> None:
        """Ein Anbieter, der immer dieselbe Frage stellt, darf das
        Programm nicht festhalten."""
        dienst = self.FalscherDienst(
            [{"State": "x", "Option": {"Name": "user"}}] * 20
        )
        with self.assertRaises(RcloneFehler) as fehler:
            einrichten(dienst, "w", "webdav", fragen=lambda f: "a", hoechstens=5)
        self.assertIn("keinem Ende", str(fehler.exception))

    def test_browser_wird_nicht_von_rclone_geoeffnet(self) -> None:
        dienst = self.FalscherDienst([{"State": "", "Option": None}])
        einrichten(dienst, "w", "dropbox")
        self.assertEqual(
            dienst.aufrufe[0]["parameters"]["config_auth_no_browser"], "true"
        )


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class GegenDasEchteRclone(unittest.TestCase):
    """Der ganze Weg mit dem ``local``-Backend.

    Keine Zugangsdaten nötig, aber für die Schnittstelle ist es ein
    Zugang wie jeder andere: auflisten, löschen, Zahlen abfragen.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.konf = self.tmp / "rclone.conf"
        self.konf.write_text("")
        self.ordner = self.tmp / "bilder"
        self.ordner.mkdir()
        for name in ("IMG_1.jpg", "IMG_2.jpg", "weg.jpg"):
            (self.ordner / name).write_bytes(name.encode())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zugang_anlegen(self) -> None:
        with Dienst.starten(self.konf) as dienst:
            einrichten(dienst, "probe", "local")
            self.assertIn("probe", dienst.remotes())
        self.assertIn("type = local", self.konf.read_text())

    def test_auflisten(self) -> None:
        with Dienst.starten(self.konf) as dienst:
            einrichten(dienst, "probe", "local")
            namen = {e["Name"] for e in dienst.auflisten(f"probe:{self.ordner}")}
        self.assertEqual(namen, {"IMG_1.jpg", "IMG_2.jpg", "weg.jpg"})

    def test_loeschen_entfernt_wirklich(self) -> None:
        with Dienst.starten(self.konf) as dienst:
            einrichten(dienst, "probe", "local")
            dienst.loeschen(f"probe:{self.ordner}/weg.jpg")
        self.assertFalse((self.ordner / "weg.jpg").exists())
        self.assertTrue((self.ordner / "IMG_1.jpg").exists())

    def test_zahlen_kommen_an(self) -> None:
        with Dienst.starten(self.konf) as dienst:
            self.assertIn("bytes", dienst.zahlen())


if __name__ == "__main__":
    unittest.main()

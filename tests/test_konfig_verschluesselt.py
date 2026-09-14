"""Ein verschlüsseltes rclone-Konfigurat.

**WOLKENErnte baut hier nichts.** rclone bringt die Verschlüsselung
selbst mit (`rclone config encryption set`); das Programm musste nur
aufhören, im Weg zu stehen. Bis 0.4.6 startete der Dienst mit
``--ask-password=false`` – nötig, weil ein Dienst kein Terminal hat –
und der erste Aufruf platzte dann mit »panic received«.

**Und was es nicht schützt, steht ausdrücklich dabei.** Aus einer
Rückmeldung von außen: *»Wenn jemand physischen Zugriff auf deinen PC
hat, kann er rclone ja so oder so direkt ausführen.«* Das stimmt. Es
geht um die **ruhende Platte** – ein gestohlenes Notebook, eine
ausgemusterte Festplatte, ein Sicherungsband –, und darum, dass ein
Zugangsschlüssel ein *fremdes* Konto öffnet, nicht nur die eigenen
Fotos.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from wolkenernte.rclone import (
    VERSCHLUESSELT,
    Dienst,
    RcloneFehler,
    fassung,
    finden,
    ist_verschluesselt,
)

_PROGRAMM = finden()
_FASSUNG = fassung(_PROGRAMM) if _PROGRAMM else None
ECHTES_RCLONE = _FASSUNG is not None and _FASSUNG.genuegt

KENNWORT = "probe-geheim-123"


class DieErkennung(unittest.TestCase):
    """An der ersten Zeile, ohne rclone zu starten."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_eine_gewoehnliche_konfiguration(self) -> None:
        pfad = self.tmp / "rclone.conf"
        pfad.write_text("[probe]\ntype = alias\nremote = /tmp\n", "utf-8")
        self.assertFalse(ist_verschluesselt(pfad))

    def test_eine_verschluesselte(self) -> None:
        pfad = self.tmp / "rclone.conf"
        pfad.write_text(f"{VERSCHLUESSELT}\n\nRCLONE_ENCRYPT_V0:\nabc\n",
                        "utf-8")
        self.assertTrue(ist_verschluesselt(pfad))

    def test_eine_datei_die_es_nicht_gibt(self) -> None:
        """Dann gibt es nichts zu entsperren – rclone legt beim ersten
        Zugang eine neue an."""
        self.assertFalse(ist_verschluesselt(self.tmp / "fehlt.conf"))

    def test_ein_ordner_statt_einer_datei(self) -> None:
        self.assertFalse(ist_verschluesselt(self.tmp))

    def test_eine_leere_datei(self) -> None:
        pfad = self.tmp / "leer.conf"
        pfad.touch()
        self.assertFalse(ist_verschluesselt(pfad))


@unittest.skipUnless(ECHTES_RCLONE, "rclone ab 1.75.0 nicht vorhanden")
class GegenEinEchtesRclone(unittest.TestCase):
    """**Gegen das echte rclone, nicht gegen eine Nachbildung.**

    Der Aufbau hängt an Einzelheiten, die sich nur am Original zeigen:
    wie die Datei anfängt, welche Umgebungsvariable rclone liest und
    wann ein falsches Kennwort auffällt. Ein nachgebautes rclone hätte
    all das nach meinen Annahmen getan.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.konf = self.tmp / "rclone.conf"
        subprocess.run(
            [str(_PROGRAMM), "--config", str(self.konf), "config", "create",
             "probe", "alias", f"remote={self.tmp}"],
            capture_output=True, check=True, timeout=60)
        self.assertFalse(ist_verschluesselt(self.konf))

        # rclone fragt zweimal - einmal setzen, einmal bestätigen.
        subprocess.run(
            [str(_PROGRAMM), "--config", str(self.konf),
             "config", "encryption", "set"],
            input=f"{KENNWORT}\n{KENNWORT}\n",
            capture_output=True, text=True, check=True, timeout=60)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rclone_schreibt_die_erwartete_erste_zeile(self) -> None:
        """Woran die Erkennung hängt. Ändert rclone diese Zeile, fällt
        es hier auf und nicht erst beim Anwender."""
        self.assertTrue(ist_verschluesselt(self.konf))
        self.assertEqual(
            self.konf.read_text("utf-8").splitlines()[0], VERSCHLUESSELT)

    def test_mit_kennwort_laeuft_der_dienst(self) -> None:
        with Dienst.starten(
            self.konf, kennwort_holen=lambda: KENNWORT
        ) as dienst:
            self.assertEqual(dienst.rufen("config/listremotes"),
                             {"remotes": ["probe"]})

    def test_ohne_frager_eine_verstaendliche_meldung(self) -> None:
        """Nicht »panic received« aus der Tiefe des ersten Aufrufs."""
        with self.assertRaises(RcloneFehler) as gefangen:
            Dienst.starten(self.konf)
        text = str(gefangen.exception)
        self.assertIn("verschlüsselt", text)
        self.assertNotIn("panic", text)

    def test_abgebrochen_heisst_abgebrochen(self) -> None:
        with self.assertRaises(RcloneFehler) as gefangen:
            Dienst.starten(self.konf, kennwort_holen=lambda: None)
        self.assertIn("Ohne das Kennwort", str(gefangen.exception))

    def test_ein_falsches_kennwort_faellt_beim_start_auf(self) -> None:
        """**Der Kern.** rclone merkt es erst beim ersten Zugriff: Der
        Dienst fährt hoch, wirkt gesund, und irgendwann später platzt
        ein beliebiger Aufruf mit »panic received«. Das liest sich wie
        ein Defekt des Programms."""
        with self.assertRaises(RcloneFehler) as gefangen:
            Dienst.starten(self.konf, kennwort_holen=lambda: "falsch")
        text = str(gefangen.exception)
        self.assertIn("stimmt nicht", text)
        self.assertNotIn("panic", text)

    def test_das_kennwort_steht_nicht_in_der_kommandozeile(self) -> None:
        """**Dieselbe Regel wie beim Kennwort der Schnittstelle.** Unter
        Linux kann jeder Benutzer die Kommandozeile fremder Prozesse in
        ``/proc`` lesen. Ein Kennwort als Argument wäre öffentlich.
        """
        with Dienst.starten(
            self.konf, kennwort_holen=lambda: KENNWORT
        ) as dienst:
            aufruf = Path(f"/proc/{dienst.prozess.pid}/cmdline")
            if not aufruf.exists():          # pragma: no cover
                self.skipTest("kein /proc auf diesem System")
            zeile = aufruf.read_bytes().replace(b"\0", b" ").decode(
                "utf-8", "replace")
        self.assertNotIn(KENNWORT, zeile)
        self.assertIn("--ask-password=false", zeile)

    def test_ein_unverschluesseltes_wird_nicht_gefragt(self) -> None:
        """Wer nichts verschlüsselt hat, soll nie einen Kennwortdialog
        sehen."""
        gefragt = []

        def holen():
            gefragt.append(1)
            return KENNWORT

        offen = self.tmp / "offen.conf"
        subprocess.run(
            [str(_PROGRAMM), "--config", str(offen), "config", "create",
             "zwei", "alias", f"remote={self.tmp}"],
            capture_output=True, check=True, timeout=60)
        with Dienst.starten(offen, kennwort_holen=holen):
            pass
        self.assertEqual(gefragt, [])

    def test_aus_der_umgebung_geht_auch(self) -> None:
        """Für Skripte und die CI: Steht ``RCLONE_CONFIG_PASS`` schon
        da, wird niemand gefragt."""
        gefragt = []
        alt = os.environ.get("RCLONE_CONFIG_PASS")
        os.environ["RCLONE_CONFIG_PASS"] = KENNWORT
        try:
            with Dienst.starten(
                self.konf, kennwort_holen=lambda: gefragt.append(1)
            ) as dienst:
                self.assertEqual(dienst.rufen("config/listremotes"),
                                 {"remotes": ["probe"]})
        finally:
            if alt is None:
                del os.environ["RCLONE_CONFIG_PASS"]
            else:
                os.environ["RCLONE_CONFIG_PASS"] = alt
        self.assertEqual(gefragt, [])


if __name__ == "__main__":
    unittest.main()

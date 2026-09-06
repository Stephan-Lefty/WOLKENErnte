"""rclone finden, starten und ansprechen.

rclone erledigt die Arbeit an den Wolkenspeichern: auflisten,
herunterladen, löschen. Es läuft als eigener Dienst (``rclone rcd``) und
wird über eine gewöhnliche HTTP-Schnittstelle angesprochen – dafür
genügen ``urllib`` und ``json`` aus der Standardbibliothek.

**Die Anmeldung an dieser Schnittstelle ist Pflicht, nicht Kür.** Aus
rclones eigener Dokumentation: *»Access to the rc API is equivalent to
shell access as the user running rclone.«* Wer sie erreicht, kann über
``core/command`` beliebige Befehle ausführen und über ``config/dump``
sämtliche Zugangsdaten auslesen. Deshalb:

* nur an ``127.0.0.1``, nie an ``0.0.0.0``,
* Benutzername und Kennwort bei jedem Start neu gewürfelt,
* beides über die **Prozessumgebung**, nicht über die Kommandozeile –
  Argumente sind unter Linux in ``/proc`` für jeden Benutzer lesbar,
* ``--rc-no-auth`` unter keinen Umständen.

**Mindestens rclone 1.75.0.** Erst dort gibt es ``config/oauthstatus``,
über das ein Programm die Anmelde-Adresse für den Browser erfährt –
vorher musste man sie aus dem Protokolltext fischen. Und erst dort ist
der Fehler behoben, bei dem iCloud einen korrekten 2FA-Code ablehnte.
"""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

#: Die kleinste Fassung, mit der WOLKENErnte arbeitet.
MINDESTFASSUNG = (1, 75, 0)

#: Wie lange auf den Start des Dienstes gewartet wird.
STARTFRIST = 20.0


class RcloneFehler(Exception):
    """rclone fehlt, ist zu alt, oder der Dienst antwortet nicht."""


@dataclass(frozen=True)
class Fassung:
    """Die Fassungsnummer von rclone."""

    haupt: int
    neben: int
    klein: int

    def __str__(self) -> str:
        return f"{self.haupt}.{self.neben}.{self.klein}"

    def __ge__(self, andere: tuple[int, int, int]) -> bool:  # type: ignore[override]
        return (self.haupt, self.neben, self.klein) >= andere

    @property
    def genuegt(self) -> bool:
        return self >= MINDESTFASSUNG


def finden() -> Path | None:
    """rclone auf dem Rechner suchen.

    Erst neben dem Programm – dort landet es, wenn WOLKENErnte es unter
    Windows mitbringt –, dann im Suchpfad des Systems. Die mitgelieferte
    Fassung hat Vorrang, weil sie zur geprüften Fassungsnummer passt.
    """
    beigelegt = Path(__file__).resolve().parent / "rclone"
    for kandidat in (beigelegt, beigelegt.with_suffix(".exe")):
        if kandidat.is_file() and os.access(kandidat, os.X_OK):
            return kandidat
    gefunden = shutil.which("rclone")
    return Path(gefunden) if gefunden else None


def fassung(programm: Path) -> Fassung | None:
    """Die Fassungsnummer ermitteln, oder ``None``."""
    try:
        ergebnis = subprocess.run(
            [str(programm), "version"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    treffer = re.search(r"rclone\s+v(\d+)\.(\d+)(?:\.(\d+))?", ergebnis.stdout)
    if not treffer:
        return None
    haupt, neben, klein = treffer.groups()
    return Fassung(int(haupt), int(neben), int(klein or 0))


def _freier_port() -> int:
    """Einen freien Port vom Betriebssystem erfragen.

    Kurzes Wettrennen: Zwischen Freigeben und rclones Binden könnte ein
    anderes Programm zugreifen. rclone selbst könnte mit ``--rc-addr
    127.0.0.1:0`` einen wählen, verrät ihn dann aber nur im
    Protokolltext – und den zu lesen ist die wackeligere Lösung.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Dienst:
    """Ein laufender ``rclone rcd``, den nur dieses Programm kennt.

    Als Kontextverwalter benutzen, damit der Kindprozess zuverlässig
    endet::

        with Dienst.starten(konfiguration) as dienst:
            dienst.rufen("config/listremotes")
    """

    def __init__(self, prozess: subprocess.Popen, port: int,
                 benutzer: str, kennwort: str) -> None:
        self.prozess = prozess
        self.port = port
        self._kopf = "Basic " + base64.b64encode(
            f"{benutzer}:{kennwort}".encode()
        ).decode()

    # -- Aufbau ------------------------------------------------------------

    @classmethod
    def starten(
        cls,
        konfiguration: Path | None = None,
        *,
        programm: Path | None = None,
        frist: float = STARTFRIST,
    ) -> Dienst:
        """Den Dienst hochfahren und warten, bis er antwortet."""
        programm = programm or finden()
        if programm is None:
            raise RcloneFehler(
                "rclone ist nicht installiert.\n"
                "Unter Arch und Manjaro: pacman -S rclone"
            )

        gefunden = fassung(programm)
        if gefunden is None:
            raise RcloneFehler(f"{programm} meldet keine Fassungsnummer.")
        if not gefunden.genuegt:
            noetig = ".".join(str(z) for z in MINDESTFASSUNG)
            raise RcloneFehler(
                f"rclone {gefunden} ist zu alt, nötig ist mindestens {noetig}.\n"
                "Erst dort lässt sich die Browser-Anmeldung steuern."
            )

        benutzer = "wolkenernte"
        kennwort = secrets.token_urlsafe(32)
        port = _freier_port()

        befehl = [
            str(programm), "rcd",
            "--rc-addr", f"127.0.0.1:{port}",
            # Ohne das wartet rclone auf ein Terminal, das ein Dienst
            # nicht hat, und hängt unsichtbar.
            "--ask-password=false",
        ]
        if konfiguration is not None:
            befehl += ["--config", str(konfiguration)]

        umgebung = dict(os.environ)
        # **Nicht als Argument.** Unter Linux kann jeder Benutzer die
        # Kommandozeile fremder Prozesse in /proc lesen.
        umgebung["RCLONE_RC_USER"] = benutzer
        umgebung["RCLONE_RC_PASS"] = kennwort

        try:
            prozess = subprocess.Popen(
                befehl, env=umgebung,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        except OSError as fehler:
            raise RcloneFehler(f"rclone ließ sich nicht starten: {fehler}")

        dienst = cls(prozess, port, benutzer, kennwort)
        dienst._warten(frist)
        return dienst

    def _warten(self, frist: float) -> None:
        """Warten, bis der Dienst antwortet."""
        ende = time.monotonic() + frist
        while time.monotonic() < ende:
            if self.prozess.poll() is not None:
                ausgabe = (self.prozess.stdout.read() if self.prozess.stdout
                           else "")
                self.beenden()
                raise RcloneFehler(
                    f"rclone hat sich sofort beendet:\n{ausgabe.strip()[:500]}"
                )
            try:
                self.rufen("rc/noop", frist=1.0)
                return
            except RcloneFehler:
                time.sleep(0.1)
        self.beenden()
        raise RcloneFehler(f"rclone antwortet nicht innerhalb von {frist:.0f}s.")

    # -- Sprechen ----------------------------------------------------------

    def rufen(self, weg: str, werte: dict | None = None, *,
              frist: float = 60.0) -> dict:
        """Einen Endpunkt aufrufen und die Antwort zurückgeben."""
        körper = json.dumps(werte or {}).encode()
        anfrage = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/{weg.lstrip('/')}",
            data=körper, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": self._kopf},
        )
        try:
            with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
                return json.loads(antwort.read() or b"{}")
        except urllib.error.HTTPError as fehler:
            roh = fehler.read()
            try:
                grund = json.loads(roh).get("error", "")
            except (json.JSONDecodeError, ValueError):
                grund = roh.decode(errors="replace")[:200]
            raise RcloneFehler(f"{weg}: {grund or fehler.reason}")
        except (urllib.error.URLError, TimeoutError, OSError) as fehler:
            raise RcloneFehler(f"{weg}: {fehler}")

    # -- Was WOLKENErnte davon braucht -------------------------------------

    def remotes(self) -> list[str]:
        """Die eingerichteten Zugänge."""
        antwort = self.rufen("config/listremotes")
        return list(antwort.get("remotes") or [])

    def auflisten(self, pfad: str, *, nur_dateien: bool = True) -> list[dict]:
        """Den Inhalt eines Ordners auflisten.

        ``pfad`` in rclones Schreibweise, etwa ``meinecloud:Fotos/2024``.
        """
        ordner, _, unterordner = pfad.partition(":")
        antwort = self.rufen("operations/list", {
            "fs": f"{ordner}:", "remote": unterordner,
            "opt": {"filesOnly": nur_dateien, "recurse": False},
        })
        return list(antwort.get("list") or [])

    def loeschen(self, pfad: str) -> None:
        """Eine einzelne Datei löschen.

        **Aufrufer müssen vorher ``anbieter.darf_loeschen()`` fragen.**
        Diese Klasse kennt die Grenzen der Anbieter nicht; sie führt aus,
        was ihr gesagt wird.
        """
        ordner, _, datei = pfad.partition(":")
        self.rufen("operations/deletefile", {"fs": f"{ordner}:", "remote": datei})

    def zahlen(self) -> dict:
        """Fortschritt und Durchsatz des laufenden Betriebs."""
        return self.rufen("core/stats")

    # -- Aufräumen ---------------------------------------------------------

    def beenden(self) -> None:
        if self.prozess.poll() is None:
            self.prozess.terminate()
            try:
                self.prozess.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.prozess.kill()
                self.prozess.wait(timeout=5)
        if self.prozess.stdout:
            self.prozess.stdout.close()

    def __enter__(self) -> Dienst:
        return self

    def __exit__(self, *_: object) -> None:
        self.beenden()


def bericht() -> int:
    """Der Befehl ``wolkenernte rclone`` – nachsehen, ob alles da ist."""
    programm = finden()
    if programm is None:
        print("rclone ist nicht installiert.")
        print("\nWOLKENErnte braucht es, um an die Wolkenspeicher zu kommen.")
        print("  Arch und Manjaro:  pacman -S rclone")
        print("  Debian und Ubuntu: apt install rclone")
        print("  sonst:             https://rclone.org/downloads/")
        return 1

    print(f"Gefunden: {programm}")
    gefunden = fassung(programm)
    if gefunden is None:
        print("  Fassung: nicht zu ermitteln")
        return 1

    noetig = ".".join(str(z) for z in MINDESTFASSUNG)
    print(f"  Fassung: {gefunden} (nötig: {noetig})")
    if not gefunden.genuegt:
        print("\nZu alt. Erst ab 1.75.0 lässt sich die Browser-Anmeldung")
        print("steuern, und erst dort nimmt iCloud den 2FA-Code an.")
        return 1

    try:
        with Dienst.starten() as dienst:
            print(f"  Dienst läuft auf 127.0.0.1:{dienst.port}")
            zugaenge = dienst.remotes()
            if zugaenge:
                print(f"\nEingerichtete Zugänge ({len(zugaenge)}):")
                for name in zugaenge:
                    print(f"  {name}")
            else:
                print("\nNoch keine Zugänge eingerichtet.")
    except RcloneFehler as fehler:
        print(f"\n{fehler}")
        return 1
    return 0

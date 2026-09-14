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

**Ein verschlüsseltes Konfigurat wird unterstützt, aber nicht von uns
gebaut.** rclone bringt das selbst mit (``rclone config encryption
set``); WOLKENErnte muss nur aufhören, im Weg zu stehen. Bis 0.4.6 tat
es genau das: Der Dienst startet mit ``--ask-password=false`` – ein
Dienst hat kein Terminal, an dem er fragen könnte –, und der erste
Aufruf platzte dann mit *»panic received: fatal error: unable to
decrypt configuration«*. Das Kennwort geht jetzt über
``RCLONE_CONFIG_PASS`` in die **Prozessumgebung**, aus demselben Grund
wie beim Kennwort der Schnittstelle: Die Kommandozeile ist in ``/proc``
mitlesbar.

**Was das schützt und was nicht.** Nicht gegen jemanden, der an Ihrem
angemeldeten Rechner sitzt – der kann rclone ohnehin selbst aufrufen,
und ein einmal entsperrter Dienst trägt das Kennwort in seiner
Umgebung. Es schützt die **ruhende Platte**: ein gestohlenes Notebook,
eine ausgemusterte Festplatte, ein Sicherungsband, ein
``~/.config``-Ordner, der versehentlich in einer Cloud landet. Dort ist
rclones ``obscure`` in einer Zeile rückgängig gemacht, eine
Verschlüsselung nicht. Und anders als die Fotos daneben öffnet ein
Zugangsschlüssel ein **fremdes Konto**.

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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: Die kleinste Fassung, mit der WOLKENErnte arbeitet.
MINDESTFASSUNG = (1, 75, 0)

#: Wie lange auf den Start des Dienstes gewartet wird.
STARTFRIST = 20.0

#: Womit ein verschlüsseltes Konfigurat anfängt.
#:
#: rclone schreibt diese Zeile selbst an den Anfang der Datei. Danach
#: folgt ``RCLONE_ENCRYPT_V0:`` und der Inhalt.
VERSCHLUESSELT = "# Encrypted rclone configuration File"


class RcloneFehler(Exception):
    """rclone fehlt, ist zu alt, oder der Dienst antwortet nicht."""


def ist_verschluesselt(konfiguration: Path) -> bool:
    """Ob die Zugangsdaten verschlüsselt abgelegt sind.

    **An der ersten Zeile erkannt, nicht über rclone.** Es gäbe
    ``rclone config encryption check``, aber das wäre ein Prozessstart
    für eine Frage, die in den ersten vierzig Bytes steht – und diese
    Frage wird bei jedem Start des Dienstes gestellt.

    Eine Datei, die es nicht gibt oder die sich nicht lesen lässt, gilt
    als unverschlüsselt: Dann gibt es nichts zu entsperren, und rclone
    legt beim ersten Zugang eine neue an.
    """
    try:
        with konfiguration.open("r", encoding="utf-8", errors="replace") as datei:
            return datei.readline().strip() == VERSCHLUESSELT
    except OSError:
        return False


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
        kennwort_holen: Callable[[], str | None] | None = None,
    ) -> Dienst:
        """Den Dienst hochfahren und warten, bis er antwortet.

        ``kennwort_holen`` wird **nur** gerufen, wenn das Konfigurat
        verschlüsselt ist – und dann höchstens einmal. Wer nur seine
        Bilder durchsieht, wird nie danach gefragt: Der Dienst startet
        ohnehin erst, wenn eine Wolke gebraucht wird.

        Gibt die Funktion ``None`` zurück (abgebrochen), bricht auch der
        Start ab. Ohne ``kennwort_holen`` kommt eine Meldung, die sagt,
        was zu tun ist – besser als rclones *»panic received«* aus der
        Tiefe des ersten Aufrufs.
        """
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

        # Ein verschlüsseltes Konfigurat braucht sein Kennwort, **bevor**
        # der Dienst startet. Sonst fährt er hoch, wirkt gesund, und
        # erst der erste Aufruf platzt mit einem »panic received« – eine
        # Meldung, die nach einem Defekt des Programms aussieht.
        if konfiguration is not None and ist_verschluesselt(konfiguration):
            if os.environ.get("RCLONE_CONFIG_PASS"):
                pass          # Schon in der Umgebung, etwa aus einem Skript
            elif kennwort_holen is None:
                raise RcloneFehler(
                    f"Die Zugangsdaten in {konfiguration} sind "
                    f"verschlüsselt.\n"
                    f"Setzen Sie RCLONE_CONFIG_PASS, oder nehmen Sie die "
                    f"Verschlüsselung\nmit »rclone --config "
                    f"{konfiguration} config encryption remove« heraus."
                )
            else:
                geheim = kennwort_holen()
                if not geheim:
                    raise RcloneFehler("Ohne das Kennwort geht es nicht.")
                umgebung["RCLONE_CONFIG_PASS"] = geheim

        try:
            prozess = subprocess.Popen(
                befehl, env=umgebung,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        except OSError as fehler:
            raise RcloneFehler(f"rclone ließ sich nicht starten: {fehler}")

        dienst = cls(prozess, port, benutzer, kennwort)
        dienst._warten(frist)
        if konfiguration is not None and ist_verschluesselt(konfiguration):
            dienst._kennwort_pruefen(konfiguration)
        return dienst

    def _kennwort_pruefen(self, konfiguration: Path) -> None:
        """Einmal anklopfen, solange die Meldung noch etwas wert ist.

        **Ein falsches Kennwort merkt rclone erst beim ersten Zugriff.**
        Der Dienst fährt hoch, wirkt gesund, und irgendwann später
        platzt ein beliebiger Aufruf mit *»panic received: fatal error:
        using RCLONE_CONFIG_PASS env password, unable to decrypt
        configuration«*. Das liest sich wie ein Defekt des Programms und
        steht an einer Stelle, an der niemand ans Kennwort denkt.

        Ein Aufruf von ``config/listremotes`` kostet nichts und
        verwandelt das in einen Satz, der sagt, was los ist.
        """
        try:
            self.rufen("config/listremotes")
        except RcloneFehler as fehler:
            if "decrypt" not in str(fehler):
                raise
            self.beenden()
            raise RcloneFehler(
                f"Das Kennwort für {konfiguration.name} stimmt nicht."
            ) from fehler

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

    def auflisten(self, pfad: str, *, nur_dateien: bool = True,
                  mit_unterordnern: bool = False) -> list[dict]:
        """Den Inhalt eines Ordners auflisten.

        ``pfad`` in rclones Schreibweise, etwa ``meinecloud:Fotos/2024``.

        **Der ganze Pfad gehört in ``fs``, nicht aufgeteilt.** Ein erster
        Anlauf trennte am Doppelpunkt und übergab den Rest als
        ``remote`` – rclone antwortete darauf mit »directory not
        found«, obwohl der Ordner existierte. ``remote`` ist relativ zu
        ``fs`` gedacht, nicht als zweite Hälfte davon.
        """
        antwort = self.rufen("operations/list", {
            "fs": pfad, "remote": "",
            "opt": {"filesOnly": nur_dateien, "recurse": mit_unterordnern},
        })
        return list(antwort.get("list") or [])

    def art(self, name: str) -> str:
        """Welcher Anbieter hinter einem Zugang steckt.

        **Der Name eines Zugangs sagt darüber nichts.** Wer seine
        Nextcloud »meinewolke« nennt, hat trotzdem eine Nextcloud – und
        genau daran hing ein Fehler: :func:`wolkenernte.anbieter.darf_loeschen`
        bekam den *Namen* übergeben, fand ihn in keiner Tabelle und
        antwortete »nein«. Sicher, aber unbrauchbar: Es hätte sich nie
        irgendwo etwas aufräumen lassen.

        Zurück kommt die Kennung aus :mod:`wolkenernte.anbieter`, also
        ``"nextcloud"`` und nicht ``"webdav"``. Leer, wenn der Zugang
        unbekannt ist.
        """
        try:
            angaben = self.rufen("config/get", {"name": name.rstrip(":")})
        except RcloneFehler:
            return ""
        art = str(angaben.get("type") or "")
        # Nextcloud ist ein WebDAV-Server unter vielen. rclone merkt
        # sich die Unterscheidung in »vendor«, und genau die ist für
        # uns der Unterschied zwischen einem erprobten Anbieter und
        # irgendeinem Server.
        if art == "webdav":
            return str(angaben.get("vendor") or "").lower() or "webdav"
        return art

    def loeschen(self, pfad: str) -> None:
        """Eine einzelne Datei löschen.

        **Aufrufer müssen vorher ``anbieter.darf_loeschen()`` fragen.**
        Diese Klasse kennt die Grenzen der Anbieter nicht; sie führt aus,
        was ihr gesagt wird.
        """
        ordner, _, datei = pfad.rpartition("/")
        if not ordner:
            ordner, _, datei = pfad.rpartition(":")
            ordner += ":"
        self.rufen("operations/deletefile", {"fs": ordner, "remote": datei})

    def ordner_loeschen(self, pfad: str) -> None:
        """Einen **leeren** Ordner entfernen.

        ``operations/rmdir`` weigert sich, wenn noch etwas darin liegt –
        »directory not empty«. Das ist hier kein Ärgernis, sondern die
        zweite Sicherung: Ein Ordner, in dem noch ein Schriftstück oder
        eine Musikdatei liegt, die WOLKENErnte absichtlich nicht
        anfasst, kann damit gar nicht verschwinden. Der Aufrufer muss
        nicht raten, ob er leer ist; rclone weiß es besser.
        """
        ordner, _, name = pfad.rpartition("/")
        if not ordner:
            ordner, _, name = pfad.rpartition(":")
            ordner += ":"
        self.rufen("operations/rmdir", {"fs": ordner, "remote": name})

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

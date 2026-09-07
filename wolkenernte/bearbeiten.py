"""Ein Bild an ein anderes Programm weiterreichen.

WOLKENErnte zeigt Bilder, es bearbeitet sie nicht – und soll es auch
nicht. Wer ein Foto begradigen oder aufhellen will, hat dafür ein
Programm, und meistens ein bestimmtes. Hier steht nur, wie man es
findet und aufruft.

**Es wird nur angeboten, was wirklich da ist.** Ein Menüeintrag, der
beim Anklicken nichts tut, ist schlimmer als keiner – dieselbe Regel
wie bei :func:`wolkenernte.anbieter.darf_loeschen`. Gesucht wird über
den Suchpfad, nicht geraten.

**Und WOLKENErnte wartet nicht.** Das andere Programm läuft
eigenständig weiter; wer GIMP schließt, schließt nicht WOLKENErnte, und
umgekehrt. Was dort gespeichert wird, sieht WOLKENErnte beim nächsten
Einlesen.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class BearbeitenFehler(Exception):
    """Das Programm ließ sich nicht starten."""


@dataclass(frozen=True)
class Programm:
    """Ein Bildbearbeitungsprogramm, das auf dem Rechner liegt."""

    name: str
    """So heißt es im Menü."""

    befehl: str
    """So heißt es auf der Platte."""

    wofuer: str = ""
    """Ein Halbsatz für den Tooltip – wozu es taugt."""


#: Was unter Linux und BSD in Frage kommt, in der Reihenfolge des Menüs.
#:
#: Erst die Bearbeiter, dann die Betrachter: Wer »bearbeiten« anklickt,
#: meint meistens GIMP, nicht den Bildbetrachter. Die Liste ist bewusst
#: kurz – jedes weitere Programm ist ein Eintrag, den niemand liest.
UNIX = (
    Programm("GIMP", "gimp", "malen, retuschieren, montieren"),
    Programm("Krita", "krita", "malen und zeichnen"),
    Programm("darktable", "darktable", "entwickeln, Belichtung, RAW"),
    Programm("RawTherapee", "rawtherapee", "entwickeln, RAW"),
    Programm("Inkscape", "inkscape", "nachzeichnen, Vektoren"),
    Programm("Photoflare", "photoflare", "schnelle Korrekturen"),
    Programm("Pinta", "pinta", "schnelle Korrekturen"),
    Programm("Showfoto", "showfoto", "aus digiKam"),
    Programm("Gwenview", "gwenview", "ansehen, gerade rücken"),
    Programm("Nomacs", "nomacs", "ansehen"),
)

#: Unter macOS liegen Programme nicht im Suchpfad.
#:
#: Sie werden über ``open -a`` mit ihrem Anzeigenamen aufgerufen; ob
#: eines da ist, sagt der Ordner ``/Applications``.
MACOS = (
    Programm("GIMP", "GIMP", "malen, retuschieren, montieren"),
    Programm("Krita", "Krita", "malen und zeichnen"),
    Programm("Affinity Photo", "Affinity Photo", ""),
    Programm("Pixelmator Pro", "Pixelmator Pro", ""),
    Programm("Vorschau", "Preview", "ansehen, zuschneiden"),
)


def vorhandene() -> list[Programm]:
    """Welche Bildbearbeitung auf diesem Rechner liegt.

    Unter Windows gibt es keine verlässliche Liste – dort führt der
    Weg über :func:`auswahl_anbieten`, den Dialog des Systems.
    """
    if sys.platform == "darwin":
        return [p for p in MACOS
                if Path(f"/Applications/{p.befehl}.app").exists()
                or Path(f"/System/Applications/{p.befehl}.app").exists()]
    if sys.platform == "win32":
        return []
    return [p for p in UNIX if shutil.which(p.befehl)]


def _starten(befehle: list[str]) -> None:
    """Ein Programm starten und **nicht** auf es warten.

    ``start_new_session`` hängt es von WOLKENErnte ab: Sonst stürbe der
    Bildbearbeiter mit, wenn WOLKENErnte endet – und ein
    Bearbeitungsstand mit ihm.
    """
    try:
        subprocess.Popen(
            befehle,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=(sys.platform != "win32"),
        )
    except (OSError, ValueError) as fehler:
        raise BearbeitenFehler(
            f"{befehle[0]} ließ sich nicht starten: {fehler}") from fehler


def oeffnen_mit(bild: Path, programm: Programm) -> None:
    """Ein Bild in einem bestimmten Programm öffnen."""
    if not bild.is_file():
        raise BearbeitenFehler(f"{bild.name} liegt nicht mehr dort.")
    if sys.platform == "darwin":
        _starten(["open", "-a", programm.befehl, str(bild)])
    else:
        _starten([programm.befehl, str(bild)])


def auswahl_anbieten(bild: Path) -> None:
    """Den »Öffnen mit«-Dialog des Betriebssystems zeigen.

    Der Ausweg für alles, was nicht in der Liste steht – und unter
    Windows der einzige Weg, weil es dort keine verlässliche Liste
    installierter Programme gibt.
    """
    if not bild.is_file():
        raise BearbeitenFehler(f"{bild.name} liegt nicht mehr dort.")
    if sys.platform == "win32":
        _starten(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", str(bild)])
    elif sys.platform == "darwin":
        _starten(["open", str(bild)])
    else:
        # mimeopen fragt nach, xdg-open nimmt kommentarlos die
        # Standardanwendung. Gefragt ist hier die Frage.
        if shutil.which("mimeopen"):
            _starten(["mimeopen", "-a", str(bild)])
        else:
            _starten(["xdg-open", str(bild)])


def im_dateimanager(bild: Path) -> None:
    """Den Ordner öffnen und das Bild darin auswählen.

    Nicht bloß den Ordner: Bei vierzehntausend Bildern in
    Monatsordnern hilft es wenig, irgendwo im richtigen Ordner zu
    landen.
    """
    if not bild.exists():
        raise BearbeitenFehler(f"{bild.name} liegt nicht mehr dort.")
    if sys.platform == "win32":
        _starten(["explorer.exe", f"/select,{bild}"])
    elif sys.platform == "darwin":
        _starten(["open", "-R", str(bild)])
    elif shutil.which("dbus-send"):
        # Der freedesktop-Weg: Er wählt die Datei aus, statt nur den
        # Ordner zu öffnen. Nautilus, Dolphin und Nemo können ihn.
        _starten([
            "dbus-send", "--session", "--print-reply",
            "--dest=org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1.ShowItems",
            f"array:string:{bild.as_uri()}", "string:",
        ])
    else:
        _starten(["xdg-open", str(bild.parent)])

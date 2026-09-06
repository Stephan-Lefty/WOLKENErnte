"""Zugänge einrichten und ansehen – von der Kommandozeile aus.

    wolkenernte zugang
    wolkenernte zugang nextcloud <Name> <Adresse> <Benutzer>

Die Zugangsdaten landen in ``~/.config/wolkenernte/rclone.conf`` –
**nicht** in der Konfiguration, die der Anwender vielleicht selbst für
rclone pflegt. Wer WOLKENErnte wieder loswird, nimmt diese eine Datei
mit; und was das Programm anlegt, kann es nicht versehentlich in
fremden Einstellungen anrichten.
"""

from __future__ import annotations

import getpass
from pathlib import Path

from .anbieter import NACH_KENNUNG
from .einrichten import Abbruch, Frage, einrichten, nextcloud
from .einstellungen import ordner as einstellungsordner
from .rclone import Dienst, RcloneFehler


def konfiguration() -> Path:
    """Wo WOLKENErnte die Zugangsdaten für rclone ablegt."""
    return einstellungsordner() / "rclone.conf"


def _antworten(frage: Frage) -> str | None:
    """Eine Rückfrage von rclone im Terminal stellen."""
    print()
    if frage.fehler:
        print(f"  ! {frage.fehler}")
    if frage.hilfe:
        for zeile in frage.hilfe.splitlines()[:6]:
            print(f"  {zeile}")
    if frage.auswahl:
        print(f"  Möglich: {', '.join(frage.auswahl)}")

    hinweis = f"  {frage.name}"
    if frage.vorgabe:
        hinweis += f" [{frage.vorgabe}]"
    hinweis += ": "

    try:
        eingabe = (getpass.getpass(hinweis) if frage.geheim
                   else input(hinweis)).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not eingabe and frage.vorgabe:
        return frage.vorgabe
    if not eingabe and frage.pflicht:
        print("  (Pflichtangabe)")
        return _antworten(frage)
    return eingabe


def zeigen() -> int:
    """Die eingerichteten Zugänge auflisten."""
    pfad = konfiguration()
    if not pfad.exists():
        print("Noch kein Zugang eingerichtet.\n")
        print("Nextcloud einrichten:")
        print("  wolkenernte zugang nextcloud meinewolke "
              "https://wolke.example anna")
        return 0

    try:
        with Dienst.starten(pfad) as dienst:
            namen = dienst.remotes()
            if not namen:
                print("Noch kein Zugang eingerichtet.")
                return 0
            print(f"Eingerichtete Zugänge ({len(namen)}):\n")
            for name in namen:
                kennung = name.rstrip(":")
                anbieter = NACH_KENNUNG.get(kennung)
                zusatz = ""
                if anbieter and not anbieter.loeschen:
                    zusatz = "  – dort kann nur gelesen werden"
                print(f"  {name}{zusatz}")
            print(f"\nAbgelegt in {pfad}")
    except RcloneFehler as fehler:
        print(fehler)
        return 1
    return 0


def nextcloud_anlegen(name: str, adresse: str, benutzer: str) -> int:
    """Einen Nextcloud-Zugang einrichten."""
    print(f"Nextcloud-Zugang »{name}« einrichten\n")
    print("**Bitte ein App-Passwort verwenden, nicht das Kontokennwort.**")
    print("Bei eingeschalteter Zwei-Faktor-Anmeldung nimmt Nextcloud das")
    print("Kontokennwort über WebDAV gar nicht an – und ein App-Passwort")
    print("lässt sich einzeln zurückziehen, ohne alles andere zu ändern.\n")

    try:
        kennwort = getpass.getpass("  App-Passwort: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAbgebrochen.")
        return 1
    if not kennwort:
        print("Ohne Kennwort geht es nicht.")
        return 1

    pfad = konfiguration()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    if not pfad.exists():
        pfad.touch(mode=0o600)
    # Die Datei enthält Zugangsdaten - niemand sonst hat darin zu lesen.
    pfad.chmod(0o600)

    try:
        with Dienst.starten(pfad) as dienst:
            nextcloud(dienst, name, adresse, benutzer, kennwort)
            print(f"\nAngelegt. Probe – der Inhalt von »{name}:«:\n")
            try:
                eintraege = dienst.auflisten(f"{name}:", nur_dateien=False)
            except RcloneFehler as fehler:
                print(f"  Die Verbindung steht nicht: {fehler}\n")
                print("  Häufigste Ursachen: falsches App-Passwort, oder die")
                print("  Adresse zeigt nicht auf die Nextcloud-Wurzel.")
                return 1
            for eintrag in eintraege[:15]:
                art = "/" if eintrag.get("IsDir") else " "
                print(f"  {art} {eintrag.get('Name')}")
            if len(eintraege) > 15:
                print(f"  … und {len(eintraege) - 15} weitere")
    except Abbruch:
        print("\nAbgebrochen.")
        return 1
    except RcloneFehler as fehler:
        print(f"\n{fehler}")
        return 1

    print(f"\nZugangsdaten in {pfad}")
    return 0


def anlegen(art: str, name: str) -> int:
    """Einen Zugang beliebiger Art einrichten, mit Rückfragen."""
    pfad = konfiguration()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    if not pfad.exists():
        pfad.touch(mode=0o600)
    pfad.chmod(0o600)

    print(f"Zugang »{name}« vom Typ »{art}« einrichten.")
    print("Leere Eingabe übernimmt die Vorgabe in eckigen Klammern.")

    try:
        with Dienst.starten(pfad) as dienst:
            einrichten(dienst, name, art, fragen=_antworten)
            print(f"\nAngelegt: {dienst.remotes()}")
    except Abbruch:
        print("\nAbgebrochen.")
        return 1
    except RcloneFehler as fehler:
        print(f"\n{fehler}")
        return 1
    return 0

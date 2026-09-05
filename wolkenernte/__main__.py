"""Der Einstieg von der Kommandozeile.

    wolkenernte anbieter
    wolkenernte ernten   <Archiv> <Quelle> [<Quelle> ...]
    wolkenernte erfassen <Archiv> <Quelle> [<Quelle> ...]
    wolkenernte pruefen  <Archiv> <Quelle> [<Quelle> ...]
    wolkenernte bestand  <Archiv>

**Die Reihenfolge ist keine Geschmackssache.** Erst ``ernten`` – die
Bilder ins Archiv. Dann ``erfassen`` – Orte, Titel und Alben in die
Datenbank, denn die stehen nur in den Quellen. Dann ``pruefen`` – der
Nachweis, dass wirklich alles angekommen ist. **Und erst danach darf
eine Quelle gelöscht werden**, von Hand und mit Bedacht.

Eine grafische Oberfläche gibt es noch nicht.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .anbieter import ANBIETER, Weg


def _ja_nein(wert: bool) -> str:
    return "ja " if wert else "nein"


def _umbrechen(text: str, breite: int) -> list[str]:
    """Fließtext auf Zeilenlänge umbrechen.

    Von Hand statt mit ``textwrap``: Der Hinweistext enthält Anführungs-
    zeichen und Halbgeviertstriche, und ``textwrap`` bricht davor
    gelegentlich unschön um.
    """
    zeilen: list[str] = []
    zeile = ""
    for wort in text.split():
        if zeile and len(zeile) + 1 + len(wort) > breite:
            zeilen.append(zeile)
            zeile = wort
        else:
            zeile = f"{zeile} {wort}".strip()
    if zeile:
        zeilen.append(zeile)
    return zeilen


def anbieter_zeigen() -> int:
    """Die Anbietertabelle ausgeben – ungeschönt."""
    print(f"WOLKENErnte {__version__} – was bei welchem Anbieter geht\n")

    breite = max(len(a.name) for a in ANBIETER)
    print(f"{'Anbieter':<{breite}}  sehen holen löschen")
    print("-" * (breite + 20))
    for a in ANBIETER:
        print(f"{a.name:<{breite}}  {_ja_nein(a.auflisten):<5} "
              f"{_ja_nein(a.laden):<5} {_ja_nein(a.loeschen)}")

    print("\nWas dabei zu beachten ist:\n")
    for a in ANBIETER:
        if a.weg is Weg.RCLONE and a.vollstaendig and not a.hinweis:
            continue
        print(f"  {a.name}")
        for zeile in _umbrechen(a.hinweis, 68):
            print(f"    {zeile}")
        print()
    return 0


def bestand_zeigen(archiv: Path) -> int:
    """Was in der Datenbank neben dem Archiv steht."""
    from .bestand import ORT, Bestand

    if not (archiv / ORT).exists():
        print(f"Keine Datenbank in {archiv}.")
        print("Erst »wolkenernte erfassen« laufen lassen.")
        return 1

    with Bestand(archiv) as bestand:
        zahlen = bestand.zahlen()
        print(f"Archiv: {archiv}\n")
        print(f"  Bilder und Videos : {zahlen.bilder:6}")
        print(f"  mit Aufnahmedatum : {zahlen.mit_datum:6}")
        print(f"  mit Ortsangabe    : {zahlen.mit_ort:6}")
        print(f"  als Favorit       : {zahlen.favoriten:6}")
        print(f"  Alben             : {zahlen.alben:6}")
        print(f"  Fundorte           : {zahlen.fundorte:6}")

        alben = bestand.alben()
        if alben:
            print("\n  Die größten Alben:")
            for name, anzahl in alben[:15]:
                print(f"    {anzahl:>5}  {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="wolkenernte",
        description="Bilder und Videos aus den Wolken holen und dort aufräumen.",
    )
    zerleger.add_argument(
        "--fassung", action="version", version=f"WOLKENErnte {__version__}"
    )
    unter = zerleger.add_subparsers(dest="befehl")

    unter.add_parser("anbieter", help="zeigen, was wo möglich ist")

    p = unter.add_parser("ernten", help="Bilder aus Quellen ins Archiv holen")
    p.add_argument("archiv", type=Path)
    p.add_argument("quelle", type=Path, nargs="+")

    p = unter.add_parser(
        "erfassen", help="Orte, Titel und Alben in die Datenbank schreiben"
    )
    p.add_argument("archiv", type=Path)
    p.add_argument("quelle", type=Path, nargs="+")

    p = unter.add_parser(
        "pruefen", help="nachweisen, dass alles im Archiv angekommen ist"
    )
    p.add_argument("archiv", type=Path)
    p.add_argument("quelle", type=Path, nargs="+")

    p = unter.add_parser("bestand", help="zeigen, was in der Datenbank steht")
    p.add_argument("archiv", type=Path)

    werte = zerleger.parse_args(argv)

    if werte.befehl in (None, "anbieter"):
        return anbieter_zeigen()

    archiv = werte.archiv.expanduser()

    if werte.befehl == "bestand":
        return bestand_zeigen(archiv)

    quellen = [q.expanduser() for q in werte.quelle]
    for quelle in quellen:
        if not quelle.exists():
            print(f"Quelle gibt es nicht: {quelle}")
            return 1

    if werte.befehl == "ernten":
        from .ernten import ernten
        return ernten(archiv, quellen)
    if werte.befehl == "erfassen":
        from .erfassung import erfassen
        return erfassen(archiv, quellen)
    if werte.befehl == "pruefen":
        from .nachweis import pruefen
        return pruefen(archiv, quellen)

    zerleger.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

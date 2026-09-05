"""Der Einstieg von der Kommandozeile.

Vorerst kann WOLKENErnte genau eines: Auskunft darüber geben, was bei
welchem Anbieter möglich ist. Das ist wenig – aber es ist der Teil, den
man zuerst braucht. Wer wissen will, ob sich der Aufwand lohnt, soll
das erfahren, bevor er ein Konto einrichtet.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .anbieter import ANBIETER, Weg


def _ja_nein(wert: bool) -> str:
    return "ja " if wert else "nein"


def anbieter_zeigen() -> None:
    """Die Anbietertabelle ausgeben – ungeschönt."""
    print(f"WOLKENErnte {__version__} – was bei welchem Anbieter geht\n")

    breite = max(len(a.name) for a in ANBIETER)
    print(f"{'Anbieter':<{breite}}  sehen holen löschen")
    print("-" * (breite + 20))
    for a in ANBIETER:
        print(
            f"{a.name:<{breite}}  "
            f"{_ja_nein(a.auflisten):<5} "
            f"{_ja_nein(a.laden):<5} "
            f"{_ja_nein(a.loeschen)}"
        )

    print("\nWas dabei zu beachten ist:\n")
    for a in ANBIETER:
        if a.weg is Weg.RCLONE and a.vollstaendig and not a.hinweis:
            continue
        print(f"  {a.name}")
        for zeile in _umbrechen(a.hinweis, 68):
            print(f"    {zeile}")
        print()


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


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="wolkenernte",
        description="Bilder und Videos aus den Wolken holen und dort aufräumen.",
    )
    zerleger.add_argument(
        "--fassung", action="version", version=f"WOLKENErnte {__version__}"
    )
    zerleger.add_argument(
        "befehl",
        nargs="?",
        default="anbieter",
        choices=["anbieter"],
        help="anbieter: zeigen, was wo möglich ist (Vorgabe)",
    )
    werte = zerleger.parse_args(argv)

    if werte.befehl == "anbieter":
        anbieter_zeigen()
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

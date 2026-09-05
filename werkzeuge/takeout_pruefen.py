#!/usr/bin/env python3
"""Sieht sich ein Takeout-Archiv an und berichtet, wie es aufgebaut ist.

    python3 werkzeuge/takeout_pruefen.py /pfad/zu/den/zips

**Wozu.** Googles Takeout ist nicht überall gleich: Die Ordner heißen je
nach Spracheinstellung des Kontos anders, die Metadatendateien wurden
zwischenzeitlich umbenannt, und lange Dateinamen werden gekürzt. Bevor
ein Leser darauf losgelassen wird, muss man wissen, womit man es zu tun
hat – und das steht in keiner Dokumentation, sondern nur im eigenen
Archiv.

**Was es nicht ausgibt: die Fotos und ihre Namen.** Albumnamen und
Dateinamen sind privat; »Hochzeit Rita 2019« gehört in keine
Fehlermeldung und in keinen Chatverlauf. Ausgegeben werden deshalb nur
Zahlen, Endungen und Namens*muster*. Wo ein Beispiel nötig ist, wird der
Name durch »x« ersetzt und nur seine Gestalt gezeigt.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wolkenernte.takeout import Archiv, TakeoutFehler  # noqa: E402

#: Endungen, die als Bild oder Video gelten.
MEDIEN = {
    ".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif", ".webp", ".avif",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".mpg", ".webm",
}


def _verhuellen(name: str) -> str:
    """Aus einem Namen seine Gestalt machen, ohne ihn zu verraten.

    Buchstaben werden zu ``x``, Ziffern zu ``0``. Aus ``Hochzeit_2019.jpg``
    wird ``xxxxxxxx_0000.jpg`` – man sieht Länge, Trennzeichen und
    Endung, aber nicht den Inhalt.
    """
    kopf, punkt, rest = name.partition(".")
    kopf = re.sub(r"[^\W\d_]", "x", kopf, flags=re.UNICODE)
    kopf = re.sub(r"\d", "0", kopf)
    return kopf + punkt + rest


def _json_muster(name: str) -> str:
    """Das Suffix einer Metadatendatei, ohne den Bildnamen davor.

    Aus ``IMG_1234.jpg.supplemental-metadata.json`` wird
    ``<name>.jpg.supplemental-metadata.json``. Genau diese Muster
    unterscheiden die Takeout-Jahrgänge voneinander.
    """
    teile = name.split(".")
    return "<name>." + ".".join(teile[1:]) if len(teile) > 1 else name


def bericht(ordner: Path) -> int:
    try:
        archiv = Archiv.aus_ordner(ordner)
    except TakeoutFehler as fehler:
        print(f"Fehler: {fehler}")
        return 1

    with archiv:
        print(f"Teilarchive:      {len(archiv.teile())}")
        print(f"Dateien gesamt:   {len(archiv)}")
        if archiv.doppelte:
            print(f"Doppelte Pfade:   {len(archiv.doppelte)}  (zwei Exporte gemischt?)")
        print()

        endungen: Counter[str] = Counter()
        oberste: Counter[str] = Counter()
        zweite: Counter[str] = Counter()
        json_muster: Counter[str] = Counter()
        medien: list[str] = []
        jsons: set[str] = set()
        laengen: Counter[int] = Counter()

        for eintrag in archiv:
            endung = ("." + eintrag.name.rsplit(".", 1)[-1].lower()
                      if "." in eintrag.name else "(ohne)")
            endungen[endung] += 1

            teile = eintrag.pfad.split("/")
            if teile:
                oberste[teile[0]] += 1
            if len(teile) > 1:
                zweite[f"{teile[0]}/{teile[1]}"] += 1

            if endung == ".json":
                json_muster[_json_muster(eintrag.name)] += 1
                jsons.add(eintrag.pfad)
            elif endung in MEDIEN:
                medien.append(eintrag.pfad)
                laengen[len(eintrag.name)] += 1

        print("Oberste Ebene (die Ordnernamen brauche ich wörtlich):")
        for name, anzahl in oberste.most_common(10):
            print(f"  {anzahl:>7}  {name!r}")
        print()

        print("Zweite Ebene:")
        for name, anzahl in zweite.most_common(12):
            print(f"  {anzahl:>7}  {name!r}")
        if len(zweite) > 12:
            print(f"  ... und {len(zweite) - 12} weitere")
        print()

        print("Dateiendungen:")
        for endung, anzahl in endungen.most_common(20):
            print(f"  {anzahl:>7}  {endung}")
        print()

        print("Muster der Metadatendateien – der wichtigste Punkt:")
        for muster, anzahl in json_muster.most_common(15):
            print(f"  {anzahl:>7}  {muster}")
        print()

        print(f"Medien: {len(medien)}   Metadatendateien: {len(jsons)}")
        if len(jsons) and len(medien):
            print(f"Verhältnis: {len(jsons) / len(medien):.2f} JSON je Mediendatei")
        print()

        # Die einfachste denkbare Zuordnung: Bildname + ".json". Was
        # dabei durchfällt, zeigt, wie viel Sonderbehandlung nötig wird.
        einfach = sum(1 for p in medien if p + ".json" in jsons)
        print("Wie weit trägt die einfachste Regel (Bildname + '.json')?")
        print(f"  {einfach} von {len(medien)} gefunden"
              f"  ({einfach / len(medien) * 100:.1f} %)" if medien else "  keine Medien")
        print()

        if laengen:
            print(f"Längste Mediendateinamen: {max(laengen)} Zeichen"
                  f"   (kürzester: {min(laengen)})")
            lang = [p for p in medien if len(p.rsplit('/', 1)[-1]) >= 40]
            if lang:
                print(f"  {len(lang)} Namen ab 40 Zeichen – dort kürzt Google.")
                print("  Gestalt der drei längsten (Buchstaben als x, Ziffern als 0):")
                for pfad in sorted(lang, key=lambda p: -len(p))[:3]:
                    name = pfad.rsplit("/", 1)[-1]
                    print(f"    {len(name):>3} Zeichen  {_verhuellen(name)}")
        print()

        # Klammerzusätze, die Google bei Namensgleichheit vergibt. Ob die
        # JSON dazu (1).json oder .json(1) heißt, ist eine der
        # klassischen Fallen.
        klammern = [p for p in medien if re.search(r"\(\d+\)\.", p)]
        print(f"Mediendateien mit Klammerzusatz wie '(1)': {len(klammern)}")
        for pfad in klammern[:3]:
            name = pfad.rsplit("/", 1)[-1]
            passend = [j.rsplit("/", 1)[-1] for j in jsons
                       if j.rsplit("/", 1)[-1].startswith(name.split("(")[0])]
            print(f"    {_verhuellen(name)}")
            for j in passend[:2]:
                print(f"      dazu gefunden: {_verhuellen(j)}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Aufruf: {sys.argv[0]} /pfad/zu/den/zips")
    raise SystemExit(bericht(Path(sys.argv[1]).expanduser()))

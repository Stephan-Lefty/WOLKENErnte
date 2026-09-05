"""Doppelgänger im Archiv finden – gleiche Bilder in verschiedenen Dateien.

Bytegleiche Kopien gibt es im Archiv keine mehr; die hat schon das
Ernten aussortiert. Was bleibt, ist der schwierigere Fall: **dasselbe
Foto in zwei Fassungen.** Einmal das Original von der Kamera, einmal die
Version, die durch einen Messenger gelaufen ist. Verschiedene Dateien,
verschiedene Größe, dasselbe Bild.

Der Fingerabdruck dafür steckt in :mod:`wolkenernte.aehnlich`, die
Aufbewahrung in :mod:`wolkenernte.bestand`. Hier wird beides verbunden:
einmal rechnen, dann nachschlagen. **Das Rechnen dauert Minuten, das
Nachschlagen Sekundenbruchteile** – deshalb wird es aufbewahrt und nicht
bei jedem Aufruf wiederholt.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path

from .aehnlich import SCHWELLE, fingerabdruck, gruppen
from .bestand import ORT, Bestand


def rechnen(
    archiv: Path,
    *,
    fortschritt: Callable[[int, int], None] | None = None,
) -> int:
    """Fehlende Fingerabdrücke nachrechnen. Gibt zurück, wie viele.

    Videos bekommen keinen: Für ein Standbild daraus bräuchte es
    ffmpeg, und das ist noch nicht eingebaut. Sie werden mit dem Wert 0
    vermerkt, damit sie nicht bei jedem Lauf erneut versucht werden.
    """
    if not (archiv / ORT).exists():
        return 0

    gerechnet = 0
    with Bestand(archiv) as bestand:
        offen = bestand.ohne_fingerabdruck()
        for nummer, (kennung, pfad) in enumerate(offen, 1):
            if fortschritt:
                fortschritt(nummer, len(offen))
            wert = fingerabdruck(archiv / pfad)
            # 0 heißt hier: versucht, nichts dabei herausgekommen.
            # Ohne diesen Vermerk liefe jeder Aufruf erneut über
            # dieselben Videos und beschädigten Dateien.
            bestand.fingerabdruck_merken(kennung, wert if wert is not None else 0)
            gerechnet += 1
            if gerechnet % 500 == 0:
                bestand.sichern()
        bestand.sichern()
    return gerechnet


#: Anhängsel, die Google und Bildbearbeitungen an den Namen hängen.
#:
#: **Absichtlich eng gefasst.** Ein erster Anlauf hatte ``_\d+`` und
#: ``-\d+`` mit beliebig vielen Ziffern darin. Damit wurde aus
#: ``IMG_20210110_113920(1).jpg`` der Stamm ``img`` – die Zeitstempel im
#: Namen fielen mit weg, und **jedes** Kamerabild hätte denselben Stamm
#: gehabt. Alles wäre »dieselbe Aufnahme« gewesen.
#:
#: Deshalb: Nummern nur in Klammern oder nach Tilde, angehängte Ziffern
#: höchstens zwei Stellen. Ein Zeitstempel hat sechs oder acht.
_ANHAENGSEL = re.compile(
    r"(\(\d{1,3}\)|~\d{1,2}|-\d{1,2}|-bearbeitet|-edited|-effects"
    r"|-collage|-animation|-motion|-smile|-mix|-pano|-bokeh)$",
    re.IGNORECASE,
)


def namensstamm(pfad: str) -> str:
    """Der Dateiname ohne Endung und ohne Anhängsel.

    ``IMG_20210110_113920(1).jpg`` und ``IMG_20210110_113920.jpg``
    ergeben beide ``img_20210110_113920``.
    """
    name = pfad.rsplit("/", 1)[-1]
    name = name.rsplit(".", 1)[0]
    vorher = None
    while vorher != name:
        vorher = name
        name = _ANHAENGSEL.sub("", name)
    return name.lower().strip(" _-")


def einstufen(gruppe: list[str]) -> str:
    """Wie sicher es sich um dieselbe Aufnahme handelt.

    **Ähnlich ist nicht dasselbe.** Eine Serienaufnahme – fünfmal
    dasselbe Motiv im Sekundenabstand – sieht für den Fingerabdruck
    gleich aus, zeigt aber fünf verschiedene Augenblicke. Ein Bild und
    seine kleingerechnete Fassung dagegen sind wirklich dasselbe.

    Unterscheiden lässt sich das am Dateinamen: Tragen alle Bilder
    denselben Stamm und unterscheiden sich nur durch ein Anhängsel wie
    ``(1)`` oder ``-bearbeitet``, ist es dieselbe Aufnahme. Sonst bleibt
    es bei »ähnlich«, und der Mensch entscheidet.
    """
    staemme = {namensstamm(p) for p in gruppe}
    if len(staemme) == 1:
        return "dieselbe Aufnahme"
    return "ähnlich"


def finden(
    archiv: Path, *, schwelle: int = SCHWELLE, nur_sichere: bool = False
) -> list[list[str]]:
    """Die Gruppen ähnlicher Bilder.

    Sortiert nach Verlässlichkeit: erst die Gruppen, in denen alle
    Bilder denselben Namensstamm tragen – das sind wirklich dieselben
    Aufnahmen –, danach die bloß ähnlichen. Innerhalb dessen die
    größten zuerst.
    """
    if not (archiv / ORT).exists():
        return []
    with Bestand(archiv) as bestand:
        alle = gruppen(bestand.fingerabdruecke(), schwelle=schwelle)
    if nur_sichere:
        alle = [g for g in alle if einstufen(g) == "dieselbe Aufnahme"]
    return sorted(alle, key=lambda g: (einstufen(g) != "dieselbe Aufnahme",
                                       -len(g)))


def bericht(archiv: Path) -> int:
    """Der Befehl ``wolkenernte doppelt``."""
    if not (archiv / ORT).exists():
        print(f"Keine Datenbank in {archiv}.")
        print("Erst »wolkenernte erfassen« laufen lassen.")
        return 1

    with Bestand(archiv) as bestand:
        offen = len(bestand.ohne_fingerabdruck())

    if offen:
        print(f"{offen} Bilder haben noch keinen Fingerabdruck. Wird nachgeholt –")
        print("das dauert beim ersten Mal einige Minuten.")
        t0 = time.time()
        rechnen(archiv, fortschritt=lambda n, g: (
            print(f"  {n}/{g}", end="\r", flush=True) if n % 200 == 0 else None
        ))
        print(f"  fertig in {(time.time()-t0)/60:.1f} Minuten          ")

    t0 = time.time()
    treffer = finden(archiv)
    ueberzaehlig = sum(len(g) - 1 for g in treffer)

    print(f"\n{len(treffer)} Gruppen ähnlicher Bilder, "
          f"{ueberzaehlig} überzählige Fassungen "
          f"(gesucht in {time.time()-t0:.1f}s)\n")

    sichere = [g for g in treffer if einstufen(g) == "dieselbe Aufnahme"]
    print(f"  davon {len(sichere)} Gruppen mit demselben Namensstamm – das "
          f"sind wirklich dieselben\n  Aufnahmen. Der Rest sieht nur "
          f"ähnlich aus, oft Serienbilder.\n")

    for gruppe in treffer[:20]:
        groessen = []
        for pfad in gruppe:
            datei = archiv / pfad
            groessen.append(datei.stat().st_size if datei.exists() else 0)
        print(f"  {len(gruppe)} Fassungen – {einstufen(gruppe)}:")
        for pfad, groesse in sorted(zip(gruppe, groessen), key=lambda p: -p[1]):
            print(f"    {groesse/1e6:6.2f} MB  {pfad}")
        print()

    if len(treffer) > 20:
        print(f"  ... und {len(treffer) - 20} weitere Gruppen.")
    if treffer:
        print("Nichts wurde gelöscht. Die Oberfläche zeigt die Gruppen "
              "nebeneinander,\nsodass man vergleichen kann, bevor man "
              "sich entscheidet.")
    return 0

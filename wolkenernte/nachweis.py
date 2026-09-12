#!/usr/bin/env python3
"""Weist nach, dass jedes Bild aus den Quellen im Archiv angekommen ist.

    python3 werkzeuge/nachpruefen.py <Archiv> <Quelle> [<Quelle> ...]

**Vor jedem Löschen laufen lassen.** Die Bilanz der Übernahme sagt nur,
was das Programm zu tun *glaubte*. Dieses Werkzeug sieht nach, was
tatsächlich auf der Platte liegt – und zwar inhaltlich, über Größe und
Prüfsumme, nicht über Dateinamen. Ein Bild, das im Archiv anders heißt
oder in einem anderen Jahr liegt, gilt trotzdem als angekommen; nur
sein Inhalt zählt.

Das Werkzeug **ändert nichts**. Es liest und rechnet.
"""

from __future__ import annotations

import sys
import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .archiv import medien as archiv_medien
from .lokal import MEDIEN, Ordner
from .takeout import Archiv as Takeout


def _ist_medium(name: str) -> bool:
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


def archiv_ist_leer(archiv: Path) -> bool:
    """Ob im Archiv überhaupt ein Bild liegt.

    Getrennt von :func:`archiv_kennungen`, seit die nur noch die
    passenden Größen rechnet: »Keine Größe passt« heißt bloß, dass
    diese Bilder noch nicht geerntet wurden – ein völlig normaler
    Befund. »Gar kein Bild im Archiv« heißt dagegen, dass jemand
    aufräumen will, bevor er geerntet hat, und das ist der
    gefährlichste denkbare Fall.
    """
    # **Der Zwischenspeicher zählt nicht mit.** In .wolkenernte/vorschau
    # liegen Tausende JPEG-Dateien; ein Archiv, in dem nur noch die
    # stehen, ist leer – und genau dann muss diese Funktion »ja« sagen,
    # weil unmittelbar danach in einer Cloud gelöscht wird.
    return not archiv_medien(archiv)


def _groesse(pfad: Path) -> int:
    try:
        return pfad.stat().st_size
    except OSError:
        return -1


def archiv_kennungen(
    archiv: Path,
    melden: Callable[[int, int], None] | None = None,
    *,
    nur_groessen: set[int] | None = None,
) -> set[tuple[int, int]]:
    """Größe und Prüfsumme jeder Datei im Archiv.

    **``nur_groessen`` ist der Unterschied zwischen Sekunden und
    Minuten.** Wer nachsehen will, ob 28 Bilder aus einer Cloud im
    Archiv liegen, muss nicht 15.662 Archivdateien durchrechnen – nur
    die, deren Größe überhaupt zu einer der 28 passt. Eine Datei
    anderer Größe kann keine von ihnen sein.

    Gemessen: über den ganzen Bestand 296 Sekunden, mit den 28 Größen
    weniger als eine. Und es wird dabei nichts weicher geprüft – die
    Prüfsumme wird nach wie vor gerechnet, nur eben nicht für Dateien,
    die als Antwort ohnehin ausscheiden.

    ``None`` heißt: alles rechnen. Das ist richtig für
    :func:`pruefen`, wo der vollständige Bestand gebraucht wird.

    **Ohne ``melden`` schweigt die Funktion.** Sie hat lange von sich
    aus ins Terminal geschrieben – für ein Werkzeug richtig, für die
    Fensteranwendung falsch: Dort sieht niemand ein Terminal, und die
    Meldungen landeten im Nichts, während der Anwender vor einem
    Fortschrittsbalken saß, der von alledem nichts wusste.
    """
    kennungen: set[tuple[int, int]] = set()
    # Ohne .wolkenernte: Ein Vorschaubild darf nicht als Nachweis
    # gelten, dass ein Bild im Archiv liegt – daran hängt das Löschen.
    dateien = archiv_medien(archiv)
    if nur_groessen is not None:
        # Ein stat() je Datei statt sie ganz zu lesen.
        dateien = [p for p in dateien
                   if _groesse(p) in nur_groessen]
    for nummer, pfad in enumerate(dateien, 1):
        if melden:
            melden(nummer, len(dateien))
        try:
            summe = 0
            with pfad.open("rb") as datei:
                while brocken := datei.read(1 << 20):
                    summe = zlib.crc32(brocken, summe)
            kennungen.add((pfad.stat().st_size, summe))
        except OSError:
            # Eine unlesbare Datei ist kein Grund abzubrechen - sie
            # zählt nur nicht als Nachweis, und das ist die sichere
            # Seite.
            continue
    return kennungen


def im_terminal(nummer: int, gesamt: int) -> None:
    """Fortschritt für die Kommandozeile – als ``melden`` zu übergeben."""
    if nummer % 1000 == 0 or nummer == gesamt:
        print(f"  Archiv {nummer}/{gesamt}", end="\r", flush=True)


def fuehrt_pruefsummen(quelle) -> bool:
    """Ob die Quelle Prüfsummen mitbringt, ohne dass man liest.

    Ein Takeout tut das – ein ZIP führt zu jeder Datei die CRC-32 in
    seinem Inhaltsverzeichnis. Ein ausgepackter Ordner tut es nicht.
    Erkannt an der Art der Quelle, **nicht** an einem Nullwert: Eine
    leere Datei hat die Prüfsumme Null und ist trotzdem bekannt.
    """
    return isinstance(quelle, Takeout)


@dataclass
class Nachweis:
    """Das Ergebnis einer Prüfung – ohne eine Zeile Ausgabe."""

    geprueft: int = 0
    fehlend: list[str] = field(default_factory=list)

    @property
    def vollstaendig(self) -> bool:
        """Ob **jeder** Inhalt der Quelle im Archiv wiedergefunden wurde.

        Nur dann darf die Quelle weg. Steht als Eigenschaft hier und
        nicht als ``not fehlend`` an drei Stellen in der Oberfläche:
        Eine Bedingung fürs Löschen gehört an genau eine Stelle.
        """
        return not self.fehlend


def nachweis_fuehren(archiv: Path, quelle, name: str = "",
                     melden: Callable[[int, int], None] | None = None,
                     *, vorhanden: set[tuple[int, int]] | None = None,
                     ) -> Nachweis:
    """Jede Mediendatei der Quelle im Archiv wiederfinden.

    **Die Prüfsummen werden für diesen Lauf gerechnet**, nicht der
    Datenbank geglaubt – anders als bei der Vorschau in
    :mod:`wolkenernte.vorpruefung`. Der Unterschied ist der Einsatz:
    Dort wird eine Zahl angezeigt, hier wird danach etwas gelöscht.

    Bei einem Takeout kostet das nichts, weil ein ZIP seine CRC-32 im
    Inhaltsverzeichnis führt. Bei einem Ordner auf der Platte wird jede
    Datei gelesen.
    """
    ergebnis = Nachweis()
    if vorhanden is None:
        vorhanden = archiv_kennungen(archiv, melden)

    # Ein ZIP führt seine CRC-32 im Inhaltsverzeichnis; ein Ordner auf
    # der Platte nicht, dort muss gelesen werden.
    selbst_rechnen = not fuehrt_pruefsummen(quelle)
    eintraege = [e for e in quelle if _ist_medium(e.pfad.rsplit("/", 1)[-1])]
    for nummer, eintrag in enumerate(eintraege, 1):
        if melden:
            melden(nummer, len(eintraege))
        ergebnis.geprueft += 1

        summe = eintrag.pruefsumme
        if selbst_rechnen:
            # **Nicht an ``pruefsumme == 0`` entscheiden.** Eine leere
            # Datei hat die CRC-32 Null, und ein ZIP führt sie
            # trotzdem. Wer daraus »unbekannt« schließt, liest das
            # ganze Teilarchiv durch, um die Prüfsumme einer nulllangen
            # Datei zu bilden. Ob eine Quelle Prüfsummen mitbringt,
            # hängt an ihrer Art, nicht an einem Wert.
            try:
                summe = 0
                with Path(eintrag.quelle).open("rb") as datei:
                    while brocken := datei.read(1 << 20):
                        summe = zlib.crc32(brocken, summe)
            except OSError as fehler:
                ergebnis.fehlend.append(
                    f"{name or archiv.name}: {eintrag.pfad} ({fehler})")
                continue

        if (eintrag.groesse, summe) not in vorhanden:
            ergebnis.fehlend.append(f"{name or archiv.name}: {eintrag.pfad}")
    return ergebnis


def _quelle_zum_pruefen(pfad: Path):
    """Ordner voller ZIPs, einzelne ZIP-Datei oder ausgepackter Ordner.

    Dieselben drei Fälle wie in :func:`wolkenernte.ernten.quelle_oeffnen`
    – ohne den Wolkenzugang, denn geprüft wird gegen etwas, das auf
    dieser Platte liegt.
    """
    if pfad.is_dir() and any(p.suffix.lower() == ".zip" for p in pfad.iterdir()):
        return Takeout.aus_ordner(pfad)
    if pfad.is_file() and pfad.suffix.lower() == ".zip":
        return Takeout.aus_datei(pfad)
    return Ordner(pfad)


def pruefen(archiv: Path, quellen: list[Path]) -> int:
    t0 = time.time()
    print(f"=== Archiv: {archiv} ===")
    vorhanden = archiv_kennungen(archiv, im_terminal)
    print(f"  {len(vorhanden)} verschiedene Inhalte im Archiv      ")

    fehlend: list[str] = []
    gesamt = 0

    for pfad in quellen:
        print(f"\n=== Quelle: {pfad.name} ===")
        # Dieselbe Funktion, die auch das Fenster benutzt. Zwei
        # Umsetzungen derselben Löschbedingung wären die eine, die
        # irgendwann auseinanderläuft - und zwar unbemerkt, weil beide
        # in ihrem eigenen Test grün bleiben.
        quelle = _quelle_zum_pruefen(pfad)
        eintraege = sum(1 for _ in quelle)
        print(f"  {eintraege} Einträge, Prüfsummen werden verglichen")
        ergebnis = nachweis_fuehren(archiv, quelle, pfad.name,
                                    vorhanden=vorhanden)
        gesamt += ergebnis.geprueft
        fehlend.extend(ergebnis.fehlend)
        if hasattr(quelle, "schliessen"):
            quelle.schliessen()
        print("  fertig                    ")

    print(f"\n=== Ergebnis nach {(time.time()-t0)/60:.1f} Minuten ===")
    print(f"  {gesamt} Dateien in den Quellen geprüft")
    if not fehlend:
        print("  **Jeder Inhalt ist im Archiv vorhanden.**")
        print("  Die Quellen können gelöscht werden.")
        return 0

    print(f"  **{len(fehlend)} Dateien fehlen im Archiv:**")
    for zeile in fehlend[:40]:
        print(f"    {zeile}")
    if len(fehlend) > 40:
        print(f"    ... und {len(fehlend) - 40} weitere")
    print("\n  Nichts löschen, bevor das geklärt ist.")
    return 1

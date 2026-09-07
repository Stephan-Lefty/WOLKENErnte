"""Den ganzen Bestand verschlagworten – der Weg in die Datenbank.

    wolkenernte verschlagworten <Archiv>

Hier treffen sich die beiden Hälften: die Schlagwörter aus Datum,
Dateiname und Bildmaßen (:mod:`wolkenernte.schlagworte`) und die aus
dem Bild selbst (:mod:`wolkenernte.bildmodell`). Zusammen dürfen es
höchstens fünf sein; welche fünf, entscheidet
:func:`wolkenernte.schlagworte.begrenzen`.

**Die erste Hälfte kostet nichts, die zweite eine halbe Stunde.** Ohne
``onnxruntime`` läuft nur die erste, und das Programm sagt das auch –
statt wortlos schlechtere Ergebnisse zu liefern.

**Beim zweiten Lauf nur, was noch keine hat.** Wer die Begriffsliste
ändert, will das Gegenteil; dafür gibt es ``--alle``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .bestand import Bestand
from .bestandsliste import Bestandsliste, Bild
from .schlagworte import Schlagwort, aus_angaben, begrenzen

#: Welche Herkünfte dieser Durchlauf schreibt.
#:
#: Beim Schreiben werden **alle** geleert, auch die, für die nichts
#: übrig blieb. Sonst bliebe ein Schlagwort aus einem früheren Lauf
#: stehen, das die Begrenzung diesmal aussortiert hat.
QUELLEN = ("zeit", "form", "herkunft", "bild")


@dataclass
class Bilanz:
    """Was der Durchlauf getan hat."""

    gesehen: int = 0
    verschlagwortet: int = 0
    ohne: int = 0
    uebersprungen: int = 0
    gescheitert: int = 0
    aus_dem_bild: int = 0
    sekunden: float = 0.0
    haeufigste: list[tuple[str, int]] = field(default_factory=list)

    def __str__(self) -> str:
        teile = [f"{self.verschlagwortet} verschlagwortet"]
        if self.aus_dem_bild:
            teile.append(f"{self.aus_dem_bild} davon mit Bilderkennung")
        if self.ohne:
            teile.append(f"{self.ohne} ohne jedes Wort")
        if self.uebersprungen:
            teile.append(f"{self.uebersprungen} übersprungen")
        if self.gescheitert:
            teile.append(f"{self.gescheitert} gescheitert")
        return ", ".join(teile)


def _bildmasse(pfad: Path) -> tuple[int, int] | None:
    """Breite und Höhe, ohne das Bild zu dekodieren.

    Pillow liest dafür nur den Dateikopf. Ohne Pillow entfällt das
    Schlagwort für die Bildform – kein Grund, den Lauf abzubrechen.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(pfad) as offen:
            return offen.size
    except (OSError, ValueError):
        return None


def fuer_ein_bild(bild: Bild, archiv: Path, modell: object | None = None
                  ) -> list[Schlagwort]:
    """Alle Schlagwörter eines Bildes, schon auf fünf gestutzt.

    ``modell`` ist ein :class:`wolkenernte.bildmodell.Bildmodell` oder
    ``None``. Videos bekommen auch mit Modell keine Schlagwörter aus
    dem Bild – ein Einzelbild daraus zu ziehen braucht ffmpeg und steht
    noch aus.
    """
    voll = archiv / bild.pfad
    gefunden = list(aus_angaben(
        name=bild.name,
        zeit=bild.zeit,
        datum_bekannt=bild.datum_bekannt,
        groesse_bild=None if bild.ist_video else _bildmasse(voll),
        ist_video=bild.ist_video,
    ))
    if modell is not None and not bild.ist_video:
        gefunden.extend(modell.schlagworte(voll))  # type: ignore[attr-defined]
    return begrenzen(gefunden)


def verschlagworten(
    archiv: Path,
    *,
    mit_bilderkennung: bool = True,
    nur_fehlende: bool = True,
    hoechstens: int | None = None,
    fortschritt: Callable[[int, int], None] | None = None,
) -> Bilanz:
    """Den Bestand durchgehen und die Schlagwörter schreiben."""
    begonnen = time.monotonic()
    bilanz = Bilanz()

    modell = None
    if mit_bilderkennung:
        from .bildmodell import Bildmodell

        modell = Bildmodell.laden()

    stufe = "bild" if modell is not None else "abgeleitet"

    liste = Bestandsliste(archiv)
    with Bestand(archiv) as bestand:
        kennungen = bestand.kennungen_nach_pfad()
        fertig = bestand.schon_verschlagwortet(stufe) if nur_fehlende else set()

        zu_tun = [b for b in liste.bilder
                  if b.pfad in kennungen and kennungen[b.pfad] not in fertig]
        bilanz.uebersprungen = len(liste.bilder) - len(zu_tun)
        if hoechstens is not None:
            zu_tun = zu_tun[:hoechstens]

        for nummer, bild in enumerate(zu_tun, 1):
            bilanz.gesehen += 1
            if fortschritt:
                fortschritt(nummer, len(zu_tun))
            try:
                woerter = fuer_ein_bild(bild, archiv, modell)
            except Exception:  # noqa: BLE001 - ein kaputtes Bild reißt nicht alles mit
                bilanz.gescheitert += 1
                continue

            bild_id = kennungen[bild.pfad]
            for quelle in QUELLEN:
                bestand.schlagwoerter_ersetzen(
                    bild_id, quelle,
                    [(w.name, w.sicherheit) for w in woerter
                     if w.quelle == quelle],
                )
            # Videos sehen auch mit Modell nur die billige Hälfte -
            # sonst gälten sie beim nächsten Lauf als erledigt und
            # kämen nie zu Schlagwörtern aus dem Bild, sobald ffmpeg
            # ein Einzelbild liefern kann.
            bestand.verschlagwortet_merken(
                bild_id, "abgeleitet" if bild.ist_video else stufe)
            if woerter:
                bilanz.verschlagwortet += 1
            else:
                bilanz.ohne += 1
            if any(w.quelle == "bild" for w in woerter):
                bilanz.aus_dem_bild += 1

            if nummer % 200 == 0:
                bestand.sichern()

        bestand.sichern()
        bilanz.haeufigste = bestand.haeufigste_schlagwoerter(20)

    bilanz.sekunden = time.monotonic() - begonnen
    return bilanz


def bericht(archiv: Path, *, mit_bilderkennung: bool = True,
            nur_fehlende: bool = True) -> int:
    """Der Durchlauf von der Kommandozeile aus."""
    from .bildmodell import verfuegbar

    if mit_bilderkennung and not verfuegbar():
        print("Die Bilderkennung fehlt – es gibt nur die Schlagwörter aus\n"
              "Datum, Dateiname und Bildmaßen.\n")
        print("Dafür fehlt ein Paket:")
        print("  Arch, Manjaro:  sudo pacman -S python-onnxruntime-cpu")
        print("  sonst:          pip install onnxruntime\n")
        mit_bilderkennung = False

    if mit_bilderkennung:
        from .modelle import BILDTEIL, vorhanden

        if vorhanden(BILDTEIL) is None:
            print(f"Das Modell fehlt und wird geholt: "
                  f"{BILDTEIL.megabyte} MB, einmalig.")

    def zeigen(nummer: int, gesamt: int) -> None:
        if nummer % 25 == 0 or nummer == gesamt:
            print(f"  {nummer}/{gesamt}", end="\r", flush=True)

    bilanz = verschlagworten(
        archiv, mit_bilderkennung=mit_bilderkennung,
        nur_fehlende=nur_fehlende, fortschritt=zeigen)

    minuten = bilanz.sekunden / 60
    print(f"\n{bilanz}")
    if bilanz.gesehen:
        print(f"{bilanz.gesehen / bilanz.sekunden:.1f} Bilder je Sekunde, "
              f"{minuten:.1f} Minuten insgesamt")
    print("\nDie häufigsten Schlagwörter:")
    for name, wie_oft in bilanz.haeufigste:
        print(f"  {wie_oft:>6}  {name}")
    return 0

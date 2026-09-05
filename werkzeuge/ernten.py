#!/usr/bin/env python3
"""Bilder aus Takeout-Archiven und Ordnern in ein Archiv übernehmen.

    python3 werkzeuge/ernten.py <Ziel> <Quelle> [<Quelle> ...]

Eine Quelle ist entweder ein Ordner mit Takeout-ZIP-Dateien oder ein
ausgepackter Bestand. Was das ist, erkennt das Werkzeug selbst.

**Die Reihenfolge der Quellen entscheidet.** Was zuerst kommt, gewinnt:
Der erste Fund eines Inhalts wird geschrieben, alle weiteren gelten als
Doppelgänger. Deshalb gehört die Quelle mit den besseren Metadaten nach
vorn.

Dieses Werkzeug ist der Vorläufer dessen, was später die Oberfläche tut.
Es **löscht nichts** – die Quellen bleiben unangetastet.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wolkenernte.archiv import uebernehmen  # noqa: E402
from wolkenernte.lokal import (  # noqa: E402
    MEDIEN,
    Ordner,
    exif_datum,
    jahr_aus_ordner,
)
from wolkenernte.metadaten import Angaben, MetadatenFehler, aus_json  # noqa: E402
from wolkenernte.takeout import Archiv as Takeout  # noqa: E402
from wolkenernte.zuordnung import Zuordnung, zuordnen  # noqa: E402


def quelle_oeffnen(pfad: Path):
    """Ein ZIP-Bestand oder ein ausgepackter Ordner – je nachdem."""
    if pfad.is_dir() and any(p.suffix.lower() == ".zip" for p in pfad.iterdir()):
        return Takeout.aus_ordner(pfad), "Takeout-Archive"
    return Ordner(pfad), "ausgepackter Ordner"


def angaben_ermitteln(quelle, zuordnung: Zuordnung) -> Angaben:
    """Datum und Ort eines Bildes, auf drei Wegen.

    1. Aus der Metadatendatei, wenn es eine gibt – die ist am
       verlässlichsten, weil Google beim Hochladen das EXIF beschneidet.
    2. Aus dem EXIF im Bild selbst.
    3. Aus der Jahreszahl im Ordnernamen. Grob, aber besser als nichts:
       Ein Bild aus »Photos from 2019« gehört ins Jahr 2019, auch wenn
       Monat und Tag unbekannt bleiben.
    """
    if zuordnung.metadaten:
        try:
            angaben = aus_json(quelle.lesen(zuordnung.metadaten),
                               sicher=zuordnung.sicher)
            if angaben.aufgenommen or not zuordnung.sicher:
                return angaben
        except (MetadatenFehler, Exception):
            angaben = Angaben()
    else:
        angaben = Angaben()

    eintrag = quelle.eintrag(zuordnung.medium)
    if eintrag is not None and eintrag.groesse < 80_000_000:
        try:
            zeit = exif_datum(quelle.lesen(zuordnung.medium))
        except Exception:
            zeit = None
        if zeit:
            return Angaben(titel=angaben.titel, beschreibung=angaben.beschreibung,
                           aufgenommen=zeit, favorit=angaben.favorit,
                           papierkorb=angaben.papierkorb,
                           archiviert=angaben.archiviert)

    jahr = jahr_aus_ordner(zuordnung.medium)
    if jahr:
        # Der 1. Januar als Platzhalter: Das Jahr stimmt, der Tag nicht.
        # Besser als "ohne-datum", denn die Jahresordnung trägt bereits.
        return Angaben(titel=angaben.titel, beschreibung=angaben.beschreibung,
                       aufgenommen=datetime(jahr, 1, 1, tzinfo=timezone.utc),
                       favorit=angaben.favorit, papierkorb=angaben.papierkorb,
                       archiviert=angaben.archiviert)
    return angaben


def ernten(ziel: Path, quellen: list[Path]) -> int:
    gesehen: set[tuple[int, int]] = set()
    gesamt_uebernommen = gesamt_doppelt = gesamt_bytes = 0
    t_start = time.time()

    # Für den Abgleich zwischen den Quellen: alle Größen, die irgendwo
    # vorkommen. Nur wo Größen zusammenfallen, muss gerechnet werden.
    alle_groessen: set[int] = set()
    geoeffnet = []
    for pfad in quellen:
        quelle, art = quelle_oeffnen(pfad)
        geoeffnet.append((pfad, quelle, art))
        for e in quelle:
            if e.quelle.suffix.lower() in MEDIEN or e.pfad.lower().endswith(
                tuple(MEDIEN)
            ):
                alle_groessen.add(e.groesse)

    for pfad, quelle, art in geoeffnet:
        print(f"\n=== {pfad.name}  ({art}) ===")

        if isinstance(quelle, Ordner):
            t0 = time.time()
            anzahl = quelle.pruefsummen_rechnen(
                zusatzgroessen=alle_groessen,
                fortschritt=lambda n, g: (
                    print(f"  Prüfsummen {n}/{g}", end="\r", flush=True)
                    if n % 500 == 0 else None
                ),
            )
            print(f"  Prüfsummen für {anzahl} Dateien in {time.time()-t0:.0f}s")

        medien, jsons = [], set()
        for e in quelle:
            name = e.pfad.rsplit("/", 1)[-1] if "/" in e.pfad else e.pfad
            endung = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if endung == ".json":
                jsons.add(e.pfad)
            elif endung in MEDIEN:
                medien.append(e.pfad)

        zuordnungen = zuordnen(medien, jsons)
        sicher = sum(1 for z in zuordnungen if z.sicher and z.metadaten)
        print(f"  {len(medien)} Medien, {len(jsons)} Metadatendateien, "
              f"{sicher} sicher zugeordnet")

        t0 = time.time()
        bilanz = uebernehmen(
            quelle, zuordnungen,
            lambda z: angaben_ermitteln(quelle, z),
            ziel, gesehen=gesehen,
            fortschritt=lambda n, name: (
                print(f"  {n}/{len(zuordnungen)}  {name[:50]:<50}",
                      end="\r", flush=True) if n % 100 == 0 else None
            ),
        )
        print(f"  {bilanz}                                        ")
        if bilanz.fehler:
            print(f"  Fehler ({len(bilanz.fehler)}):")
            for zeile in bilanz.fehler[:5]:
                print(f"    {zeile}")

        gesamt_uebernommen += bilanz.uebernommen
        gesamt_doppelt += bilanz.doppelt
        gesamt_bytes += bilanz.bytes_geschrieben
        if hasattr(quelle, "schliessen"):
            quelle.schliessen()

    print(f"\n=== Zusammen ===")
    print(f"  {gesamt_uebernommen} Bilder übernommen, "
          f"{gesamt_doppelt} Doppelgänger übergangen")
    print(f"  {gesamt_bytes/1e9:.2f} GB in {(time.time()-t_start)/60:.1f} Minuten")
    print(f"  Ziel: {ziel}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(f"Aufruf: {sys.argv[0]} <Ziel> <Quelle> [<Quelle> ...]")
    raise SystemExit(ernten(Path(sys.argv[1]).expanduser(),
                            [Path(p).expanduser() for p in sys.argv[2:]]))

#!/usr/bin/env python3
"""Schreibt alles, was nicht in die Bilddatei passt, in die Datenbank.

    python3 werkzeuge/erfassen.py <Archiv> <Quelle> [<Quelle> ...]

**Vor dem Löschen der Quellen laufen lassen.** Ortsangaben, Titel,
Beschreibungen, Favoriten und Albumzugehörigkeiten stehen ausschließlich
in den Metadatendateien des Takeouts beziehungsweise in dessen
Ordnernamen. Sind die Quellen weg, sind sie weg.

Das Werkzeug ändert an den Quellen nichts und an den Bildern im Archiv
auch nicht. Es legt nur ``<Archiv>/.wolkenernte/bestand.db`` an.
"""

from __future__ import annotations

import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wolkenernte.bestand import Bestand  # noqa: E402
from wolkenernte.lokal import MEDIEN, Ordner, jahr_aus_ordner  # noqa: E402
from wolkenernte.metadaten import MetadatenFehler, aus_json  # noqa: E402
from wolkenernte.takeout import Archiv as Takeout  # noqa: E402
from wolkenernte.zuordnung import zuordnen  # noqa: E402

#: Ordner, die kein Album sind, sondern Googles eigene Fächer.
KEIN_ALBUM = {
    "archiv", "archivieren", "archive", "papierkorb", "bin", "trash",
    "failed videos", "takeout", "google fotos", "google photos",
    "gesperrter ordner", "locked folder",
}


def albumname(pfad: str) -> str | None:
    """Der Albumname aus dem Pfad – oder ``None``, wenn es keiner ist.

    Ein Jahresordner ist kein Album, und Googles eigene Fächer sind es
    auch nicht. Alles andere ist eines: »Nordsee 2023«, »Mein Viertel«.
    """
    teile = [t for t in pfad.replace("\\", "/").split("/")[:-1] if t]
    if not teile:
        return None
    name = teile[-1]
    if name.lower() in KEIN_ALBUM:
        return None
    # Ein reiner Jahresordner - aber "Nordsee 2023" bleibt ein Album.
    if jahr_aus_ordner(pfad) is not None:
        rest = name
        for wort in ("Fotos von", "Photos from", "Fotos del", "Foto da"):
            rest = rest.replace(wort, "")
        if not rest.strip(" -_0123456789"):
            return None
    return name


def _ist_medium(name: str) -> bool:
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


def erfassen(archiv: Path, quellen: list[Path]) -> int:
    t0 = time.time()

    # Zuerst das Archiv: Dort steht, wo ein Bild heute liegt.
    print(f"=== Archiv: {archiv} ===")
    bekannt: dict[tuple[int, int], str] = {}
    dateien = [p for p in archiv.rglob("*")
               if p.is_file() and _ist_medium(p.name)]
    for nummer, pfad in enumerate(dateien, 1):
        if nummer % 2000 == 0:
            print(f"  {nummer}/{len(dateien)}", end="\r", flush=True)
        summe = 0
        with pfad.open("rb") as datei:
            while brocken := datei.read(1 << 20):
                summe = zlib.crc32(brocken, summe)
        bekannt[(pfad.stat().st_size, summe)] = str(pfad.relative_to(archiv))
    print(f"  {len(bekannt)} Bilder im Archiv                    ")

    with Bestand(archiv) as bestand:
        for (groesse, summe), pfad in bekannt.items():
            bestand.bild_merken(groesse, summe, pfad=pfad)
        bestand.sichern()

        for quellpfad in quellen:
            print(f"\n=== Quelle: {quellpfad.name} ===")
            if quellpfad.is_dir() and any(
                p.suffix.lower() == ".zip" for p in quellpfad.iterdir()
            ):
                quelle = Takeout.aus_ordner(quellpfad)
            else:
                quelle = Ordner(quellpfad)
                print("  Prüfsummen werden gerechnet")
                quelle.pruefsummen_rechnen(
                    zusatzgroessen={g for g, _ in bekannt},
                    fortschritt=lambda n, g: (
                        print(f"  {n}/{g}", end="\r", flush=True)
                        if n % 2000 == 0 else None
                    ),
                )

            medien, jsons = [], set()
            for e in quelle:
                name = e.pfad.rsplit("/", 1)[-1]
                if name.lower().endswith(".json"):
                    jsons.add(e.pfad)
                elif _ist_medium(name):
                    medien.append(e.pfad)

            mit_ort = mit_alben = 0
            for z in zuordnen(medien, jsons):
                eintrag = quelle.eintrag(z.medium)
                if eintrag is None or not eintrag.pruefsumme:
                    continue
                kennung = (eintrag.groesse, eintrag.pruefsumme)

                angaben = None
                if z.metadaten:
                    try:
                        angaben = aus_json(quelle.lesen(z.metadaten),
                                           sicher=z.sicher)
                    except (MetadatenFehler, OSError):
                        angaben = None

                bild_id = bestand.bild_merken(
                    *kennung,
                    pfad=bekannt.get(kennung),
                    aufgenommen=angaben.aufgenommen if angaben else None,
                    ort=angaben.ort if angaben else None,
                    titel=angaben.titel if angaben else "",
                    beschreibung=angaben.beschreibung if angaben else "",
                    favorit=bool(angaben and angaben.favorit),
                    papierkorb=bool(angaben and angaben.papierkorb),
                    archiviert=bool(angaben and angaben.archiviert),
                )
                if angaben and angaben.ort:
                    mit_ort += 1

                bestand.fundort_merken(bild_id, quellpfad.name, z.medium)
                name = albumname(z.medium)
                if name:
                    bestand.album_zuordnen(bild_id, name)
                    mit_alben += 1

            bestand.sichern()
            print(f"  {len(medien)} Bilder erfasst, {mit_ort} mit Ort, "
                  f"{mit_alben} Albumzuordnungen        ")
            if hasattr(quelle, "schliessen"):
                quelle.schliessen()

        print(f"\n=== Ergebnis nach {(time.time()-t0)/60:.1f} Minuten ===")
        print(f"  {bestand.zahlen()}")
        print("\n  Die größten Alben:")
        for name, anzahl in bestand.alben()[:12]:
            print(f"    {anzahl:>5}  {name}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(f"Aufruf: {sys.argv[0]} <Archiv> <Quelle> [<Quelle> ...]")
    raise SystemExit(erfassen(Path(sys.argv[1]).expanduser(),
                              [Path(p).expanduser() for p in sys.argv[2:]]))

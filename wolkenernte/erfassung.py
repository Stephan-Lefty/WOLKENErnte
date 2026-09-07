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
from collections.abc import Callable
from pathlib import Path

from .bestand import Bestand
from .ernten import ist_wolke, quelle_oeffnen
from .lokal import MEDIEN, jahr_aus_ordner
from .metadaten import MetadatenFehler, aus_json
from .zuordnung import zuordnen

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


def archiv_lesen(
    archiv: Path,
    melden: Callable[[int, int], None] | None = None,
    *,
    nur_groessen: set[int] | None = None,
) -> dict[tuple[int, int], str]:
    """Zu jedem Inhalt im Archiv der Pfad, unter dem er dort liegt.

    ``nur_groessen`` beschränkt auf die Größen, die in den Quellen
    überhaupt vorkommen – über ein gewachsenes Archiv ist das der
    Unterschied zwischen Sekunden und Minuten. Dieselbe Überlegung wie
    in :func:`wolkenernte.nachweis.archiv_kennungen`: Eine Datei
    anderer Größe kann keine der gesuchten sein.
    """
    bekannt: dict[tuple[int, int], str] = {}
    dateien = [p for p in archiv.rglob("*")
               if p.is_file() and _ist_medium(p.name)]
    if nur_groessen is not None:
        dateien = [p for p in dateien if _groesse(p) in nur_groessen]
    for nummer, pfad in enumerate(dateien, 1):
        if melden:
            melden(nummer, len(dateien))
        try:
            summe = 0
            with pfad.open("rb") as datei:
                while brocken := datei.read(1 << 20):
                    summe = zlib.crc32(brocken, summe)
            bekannt[(pfad.stat().st_size, summe)] = str(pfad.relative_to(archiv))
        except OSError:
            continue
    return bekannt


def _groesse(pfad: Path) -> int:
    try:
        return pfad.stat().st_size
    except OSError:
        return -1


def quellenname(angabe: str | Path) -> str:
    """Wie eine Quelle in der Datenbank heißt.

    Bei einem Ordner sein Name, bei einer Cloud der Zugang samt Pfad –
    ``GuideOS:Photos``. **Das muss unterscheidbar bleiben**: Wer aus
    zwei Clouds erntet, soll später noch sehen können, woher ein Bild
    kam. Nach dem Aufräumen ist die Cloud leer, und dann ist dieser
    Eintrag das Einzige, was davon übrig ist.
    """
    return str(angabe) if ist_wolke(str(angabe)) else Path(angabe).name


def erfassen(archiv: Path, quellen: list[str | Path], dienst=None) -> int:
    """Orte, Titel, Alben und Fundorte in die Datenbank schreiben.

    ``dienst`` ist ein laufender rclone-Dienst. Fehlt er und ist eine
    Cloud unter den Quellen, wird einer gestartet – wie in
    :func:`wolkenernte.ernten.ernten`. Wer nur aus Ordnern erfasst,
    soll rclone nicht installiert haben müssen.
    """
    eigener_dienst = None
    if dienst is None and any(ist_wolke(str(q)) for q in quellen):
        from .rclone import Dienst, RcloneFehler
        from .zugang import konfiguration
        try:
            dienst = eigener_dienst = Dienst.starten(konfiguration())
        except RcloneFehler as fehler:
            print(fehler)
            return 1
    try:
        return _erfassen(archiv, quellen, dienst)
    finally:
        if eigener_dienst is not None:
            eigener_dienst.beenden()


def _erfassen(archiv: Path, quellen: list[str | Path], dienst) -> int:
    t0 = time.time()

    # Zuerst das Archiv: Dort steht, wo ein Bild heute liegt.
    print(f"=== Archiv: {archiv} ===")
    bekannt = archiv_lesen(
        archiv,
        lambda n, g: (print(f"  {n}/{g}", end="\r", flush=True)
                      if n % 2000 == 0 else None))
    print(f"  {len(bekannt)} Bilder im Archiv                    ")

    with Bestand(archiv) as bestand:
        for (groesse, summe), pfad in bekannt.items():
            bestand.bild_merken(groesse, summe, pfad=pfad)
        bestand.sichern()

        for angabe in quellen:
            name_der_quelle = quellenname(angabe)
            print(f"\n=== Quelle: {name_der_quelle} ===")
            quelle, art = quelle_oeffnen(angabe, dienst)
            print(f"  {art}")
            if hasattr(quelle, "pruefsummen_rechnen"):
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

                bestand.fundort_merken(bild_id, name_der_quelle, z.medium)
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

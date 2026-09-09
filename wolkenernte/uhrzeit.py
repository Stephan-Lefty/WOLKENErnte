"""Die EXIF-Uhrzeit in einem bestehenden Archiv nachrechnen.

    wolkenernte uhrzeit ~/Bilder/Archiv               nur nachsehen
    wolkenernte uhrzeit ~/Bilder/Archiv --wirklich    und richtigstellen
    wolkenernte uhrzeit ~/Bilder/Archiv --zurueck     den letzten Lauf aufheben

**Was schiefging.** Bis 0.4.2 las WOLKENErnte die Aufnahmezeit aus dem
EXIF als UTC. EXIF trägt aber die *Ortszeit der Kamera*; so steht es im
Standard, und so stellt jeder Mensch seine Kamera. Der Zeitstempel, der
daraus in die Datei geschrieben wurde, liegt deshalb um den Abstand zu
Greenwich daneben – in Deutschland ein bis zwei Stunden, je nach
Sommerzeit. Ein Foto von 15:44 steht seither als »16:44« unter dem Bild.

**Warum ein eigener Befehl und nicht »einfach neu ernten«.** Das
Aufnahmedatum steht im Zeitstempel der Datei, und der wurde beim Ernten
gesetzt. Ein zweiter Lauf über dieselben Quellen würde ihn
richtigstellen – nur gibt es die Quellen oft nicht mehr. Das Archiv ist
bei den meisten inzwischen die einzige Kopie.

**Der Ordner ist nicht betroffen, nur die Uhrzeit.** Das war beim Bauen
die offene Frage, und sie ist nachgerechnet: ``archiv.zielordner()``
nimmt ``.year`` und ``.month`` des Zeitobjekts, und die zeigen die
Wanduhr – unabhängig davon, welche Zeitzone daranhängt. Eine Aufnahme
vom 1. Januar 00:30 landete deshalb auch mit dem falschen Zeitstempel
im richtigen Januarordner. Es wird also **nichts verschoben**; der
Befehl fasst ausschließlich Zeitstempel an.

**Woran eine betroffene Datei erkannt wird.** Nicht geraten, sondern
nachgerechnet: Aus dem EXIF *dieser Datei* wird ausgerechnet, was die
alte Fassung daraus gemacht hätte. Stimmt der Zeitstempel der Datei
damit auf die Sekunde überein, stammt er von der alten Rechnung und
wird ersetzt. Stimmt er nicht überein, bleibt die Datei unangetastet –
dann kam das Datum aus einer Takeout-JSON, oder jemand hat es von Hand
gesetzt, oder die Reparatur lief schon.

Daraus folgt zweierlei, und beides ist beabsichtigt: Der Lauf lässt
sich **beliebig oft wiederholen**, ohne beim zweiten Mal noch etwas zu
tun. Und auf einem Rechner, der auf UTC steht, tut er **gar nichts** –
dort hat der Fehler nie zugeschlagen.

**Die eine Lücke, ehrlich benannt.** Ein Foto, das in einer Zeitzone
*ohne* Abstand zu Greenwich entstand und dessen Datum aus einer
Takeout-JSON kam, trägt zufällig genau den Zeitstempel, den die alte
Rechnung ergeben hätte. Es wird dann mitverschoben, obwohl es richtig
stand. Deshalb schreibt der Lauf ein Protokoll und lässt sich mit
``--zurueck`` vollständig aufheben.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import lokal
from .bestandsliste import BILDER, OHNE_DATUM

#: Wo das Protokoll liegt, relativ zum Archiv.
PROTOKOLL = ".wolkenernte/uhrzeit-reparatur.jsonl"

#: Wie viel von einer Datei gelesen wird, um an das EXIF zu kommen.
#:
#: Ein APP1-Abschnitt darf laut JPEG-Norm höchstens 65.533 Byte lang
#: sein und steht am Anfang. Ein halbes Megabyte deckt das mit reichlich
#: Luft ab – und erspart es, für eine Uhrzeit 29 GB durch den
#: Arbeitsspeicher zu schieben. Findet sich darin nichts, wird die Datei
#: doch noch ganz gelesen; ein Bild stillschweigend zu übergehen wäre
#: die schlechtere Antwort.
KOPF = 512 * 1024

#: Wie weit Zeitstempel auseinanderliegen dürfen und noch als gleich
#: gelten. EXIF kennt nur ganze Sekunden; Dateisysteme rechnen feiner.
TOLERANZ = 1.0


@dataclass(frozen=True)
class Befund:
    """Eine Datei, deren Zeitstempel von der alten Rechnung stammt."""

    relativ: str
    """Pfad im Archiv, mit ``/`` getrennt."""

    alt: float
    """Der Zeitstempel, der jetzt an der Datei steht."""

    neu: float
    """Der Zeitstempel, der daran stehen sollte."""

    @property
    def verschiebung(self) -> float:
        return self.neu - self.alt


def wanduhr(datei: Path) -> datetime | None:
    """Die Uhrzeit, wie sie im Bild steht – ohne Zeitzone.

    Gelesen wird über :func:`lokal.exif_datum`, also über **denselben
    Weg wie beim Ernten**. Eine zweite, eigene EXIF-Auswertung hier
    hieße, dass die Reparatur etwas anderes sieht als der Fehler, den
    sie richtigstellen soll.

    ``exif_datum`` liefert die Ortszeit mit Zeitzone daran; ``replace``
    nimmt sie wieder ab, ohne am Zifferblatt zu drehen.
    """
    try:
        with datei.open("rb") as offen:
            anfang = offen.read(KOPF)
            zeit = lokal.exif_datum(anfang)
            if zeit is None and len(anfang) == KOPF:
                zeit = lokal.exif_datum(anfang + offen.read())
    except OSError:
        return None
    return zeit.replace(tzinfo=None) if zeit else None


def befund_fuer(archiv: Path, datei: Path) -> Befund | None:
    """Prüfen, ob diese Datei den Fingerabdruck des Fehlers trägt."""
    wand = wanduhr(datei)
    if wand is None:
        return None

    falsch = wand.replace(tzinfo=timezone.utc).timestamp()
    richtig = wand.astimezone().timestamp()
    if falsch == richtig:
        # Der Rechner steht auf UTC - hier gab es nie einen Unterschied.
        return None

    try:
        steht = datei.stat().st_mtime
    except OSError:
        return None
    if abs(steht - falsch) > TOLERANZ:
        return None

    return Befund(relativ=datei.relative_to(archiv).as_posix(),
                  alt=steht, neu=richtig)


def durchsehen(archiv: Path, *, melden=None) -> list[Befund]:
    """Das ganze Archiv ansehen und die betroffenen Dateien sammeln.

    Videos bleiben außen vor: Sie tragen kein EXIF, ihr Datum kam
    ausschließlich aus einer Metadatendatei und ist damit unberührt.
    Ebenso ``ohne-datum`` – dort steht der Zeitpunkt der Übernahme, und
    den korrigiert niemand.
    """
    befunde: list[Befund] = []
    gesehen = 0
    for datei in sorted(archiv.rglob("*")):
        if not datei.is_file() or datei.suffix.lower() not in BILDER:
            continue
        relativ = datei.relative_to(archiv)
        if relativ.parts[0] in (".wolkenernte", OHNE_DATUM):
            continue
        gesehen += 1
        if melden and gesehen % 500 == 0:
            melden(gesehen, len(befunde))
        treffer = befund_fuer(archiv, datei)
        if treffer is not None:
            befunde.append(treffer)
    if melden:
        melden(gesehen, len(befunde))
    return befunde


def _protokoll_schreiben(archiv: Path, lauf: str, zeilen: list[dict]) -> None:
    pfad = archiv / PROTOKOLL
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        for zeile in zeilen:
            datei.write(json.dumps({"lauf": lauf, **zeile},
                                   ensure_ascii=False) + "\n")


def _protokoll_lesen(archiv: Path) -> list[dict]:
    pfad = archiv / PROTOKOLL
    if not pfad.exists():
        return []
    eintraege = []
    for zeile in pfad.read_text("utf-8").splitlines():
        if zeile.strip():
            try:
                eintraege.append(json.loads(zeile))
            except ValueError:
                continue
    return eintraege


def _setzen(archiv: Path, paare: list[tuple[str, float]]
            ) -> tuple[int, list[str]]:
    """Zeitstempel setzen. Was scheitert, wird benannt, nicht verschwiegen."""
    geschafft, fehler = 0, []
    for relativ, stempel in paare:
        try:
            os.utime(archiv / relativ, (stempel, stempel))
        except OSError as ausnahme:
            fehler.append(f"{relativ}: {ausnahme}")
            continue
        geschafft += 1
    return geschafft, fehler


def richtigstellen(archiv: Path, befunde: list[Befund]
                   ) -> tuple[int, list[str]]:
    """Die Zeitstempel setzen und die Datenbank nachziehen."""
    lauf = datetime.now().astimezone().isoformat(timespec="seconds")
    gelungen = []
    geschafft, fehler = 0, []
    for fund in befunde:
        anzahl, schief = _setzen(archiv, [(fund.relativ, fund.neu)])
        geschafft += anzahl
        fehler.extend(schief)
        if anzahl:
            gelungen.append({"pfad": fund.relativ,
                             "alt": fund.alt, "neu": fund.neu})

    _datenbank_nachziehen(archiv, [(e["pfad"], e["neu"]) for e in gelungen])
    if gelungen:
        _protokoll_schreiben(archiv, lauf, gelungen)
    return geschafft, fehler


def _datenbank_nachziehen(archiv: Path, paare: list[tuple[str, float]]) -> None:
    """Das Aufnahmedatum in der Datenbank mitführen.

    Fehlt die Datenbank, ist das kein Fehler – sie ist eine Beigabe.
    Bliebe sie aber stehen, stünde in der Datei die richtige Zeit und in
    der Datenbank die falsche, und je nachdem, wer fragt, käme etwas
    anderes heraus.
    """
    from .bestand import ORT, Bestand

    if not paare or not (archiv / ORT).exists():
        return
    with Bestand(archiv) as bestand:
        for relativ, stempel in paare:
            bestand.zeit_richtigstellen(
                relativ, datetime.fromtimestamp(stempel).astimezone())
        bestand.sichern()


def zurueck(archiv: Path) -> tuple[int, list[str]]:
    """Den zuletzt protokollierten Lauf vollständig aufheben."""
    eintraege = _protokoll_lesen(archiv)
    if not eintraege:
        return 0, []

    letzter = eintraege[-1]["lauf"]
    bleiben = [e for e in eintraege if e["lauf"] != letzter]
    aufheben = [e for e in eintraege if e["lauf"] == letzter]

    geschafft, fehler = _setzen(
        archiv, [(e["pfad"], e["alt"]) for e in aufheben])
    _datenbank_nachziehen(archiv, [(e["pfad"], e["alt"]) for e in aufheben])

    pfad = archiv / PROTOKOLL
    if bleiben:
        pfad.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                                for e in bleiben), "utf-8")
    elif pfad.exists():
        pfad.unlink()
    return geschafft, fehler


def _stunden(sekunden: float) -> str:
    return f"{sekunden / 3600:+.0f} h"


def bericht(archiv: Path, *, wirklich: bool = False,
            rueckgaengig: bool = False) -> int:
    """Der Befehl von der Kommandozeile aus."""
    if not archiv.is_dir():
        print(f"Kein Archiv: {archiv}")
        return 1

    if rueckgaengig:
        geschafft, fehler = zurueck(archiv)
        if not geschafft and not fehler:
            print("Kein Lauf zum Aufheben – es gibt kein Protokoll.")
            return 1
        print(f"{geschafft} Dateien auf ihren alten Stand zurückgesetzt.")
        for zeile in fehler[:10]:
            print(f"  {zeile}")
        return 1 if fehler else 0

    print(f"Archiv: {archiv}")
    print("Wird durchgesehen – gelesen wird nur der Kopf jeder Datei.")

    def melden(gesehen: int, gefunden: int) -> None:
        print(f"\r  {gesehen} Bilder angesehen, {gefunden} betroffen",
              end="", flush=True)

    befunde = durchsehen(archiv, melden=melden)
    print()

    if not befunde:
        print("\nNichts zu tun. Entweder ist das Archiv schon in Ordnung,")
        print("oder die Aufnahmedaten stammen aus Metadatendateien und")
        print("waren nie betroffen.")
        return 0

    spanne = sorted({round(b.verschiebung) for b in befunde})
    print(f"\n{len(befunde)} Dateien tragen den Zeitstempel der alten "
          f"Rechnung.")
    print(f"  Verschiebung: {', '.join(_stunden(s) for s in spanne)}")
    print("  Der Ordner bleibt in jedem Fall derselbe.")

    print("\n  Beispiele:")
    for fund in befunde[:5]:
        alt = datetime.fromtimestamp(fund.alt).strftime("%d.%m.%Y %H:%M")
        neu = datetime.fromtimestamp(fund.neu).strftime("%d.%m.%Y %H:%M")
        print(f"    {fund.relativ}")
        print(f"      {alt}  ->  {neu}")

    if not wirklich:
        print("\nEs wurde nichts geändert. Zum Richtigstellen:")
        print(f"  wolkenernte uhrzeit {archiv} --wirklich")
        print("\nDer Lauf schreibt ein Protokoll und lässt sich mit")
        print("--zurueck vollständig aufheben.")
        return 0

    print()
    geschafft, fehler = richtigstellen(archiv, befunde)
    print(f"{geschafft} Dateien richtiggestellt.")
    if fehler:
        print(f"{len(fehler)} Fehlschläge:")
        for zeile in fehler[:10]:
            print(f"  {zeile}")
    print(f"\nProtokoll: {archiv / PROTOKOLL}")
    print(f"Aufheben:  wolkenernte uhrzeit {archiv} --zurueck")
    return 1 if fehler else 0

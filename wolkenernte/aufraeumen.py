"""In der Wolke löschen – aber nur, was nachweislich im Archiv liegt.

    wolkenernte aufraeumen <Archiv> <zugang:pfad>

Das ist der Schritt, für den es das Programm gibt, und der einzige, der
sich nicht rückgängig machen lässt. Deshalb steht hier mehr Vorsicht
als Code.

**Vier Bedingungen, alle vier müssen gelten.** Fällt eine aus, wird
nichts gelöscht:

1. Der Anbieter erlaubt es überhaupt –
   :func:`wolkenernte.anbieter.darf_loeschen`, gefragt mit der **Art**
   des Zugangs, nicht mit seinem Namen.
2. Die Datei liegt im Archiv, mit **derselben Größe und derselben
   Prüfsumme**. Nicht »ein Bild dieses Namens« – Bilder werden beim
   Übernehmen umbenannt, und ein Name beweist nichts.
3. Die Prüfsumme wurde **für diesen Lauf gerechnet**, nicht aus einer
   Datenbank geglaubt. Zwischen Ernten und Aufräumen kann in der Wolke
   etwas anderes an derselben Stelle liegen.
4. Der Anwender hat ``--wirklich`` gesagt. Ohne das wird gezählt und
   berichtet, sonst nichts.

**Warum das Herunterladen sein muss.** Nextcloud führt über WebDAV
keine Prüfsummen; rclone kann also keine liefern, ohne die Datei zu
lesen. Man könnte sich auf die Fundorte aus der Datenbank verlassen –
aber die sagen, was beim *Ernten* dort lag. Für ein Löschen ist das zu
wenig. Ein Durchlauf über ein Fotoarchiv kostet damit einmal die
Leitung; das ist der Preis dafür, dass nichts Falsches verschwindet.
"""

from __future__ import annotations

import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .anbieter import NACH_KENNUNG, darf_loeschen
from .lokal import MEDIEN
from .nachweis import archiv_ist_leer, archiv_kennungen
from .rclone import RcloneFehler
from .takeout import TakeoutFehler
from .wolke import Wolke


class AufraeumFehler(Exception):
    """Aufräumen war nicht möglich – und zwar aus einem nennbaren Grund."""


@dataclass
class Urteil:
    """Was mit einer Datei in der Wolke geschehen soll."""

    pfad: str
    groesse: int
    gesichert: bool
    """Ob genau dieser Inhalt im Archiv liegt."""

    geloescht: bool = False
    grund: str = ""

    ablage: Path | None = None
    """Wo die geholte Datei liegt, solange die Wolke offen ist.

    **Für die Oberfläche.** Zum Prüfen muss ohnehin jede Datei
    heruntergeladen werden; daraus ein Vorschaubild zu machen, kostet
    nichts extra – und ohne Bilder vor Augen liest niemand eine Liste
    aus vierhundert Dateinamen durch, bevor er sie löscht.

    Nach :meth:`wolkenernte.wolke.Wolke.schliessen` zeigt der Pfad ins
    Leere. Das ist in Ordnung: Danach gibt es auch nichts mehr zu
    entscheiden.
    """


@dataclass
class Bilanz:
    """Was der Lauf ergeben hat."""

    gesehen: int = 0
    gesichert: int = 0
    fehlt: int = 0
    gescheitert: int = 0
    geloescht: int = 0
    bytes_frei: int = 0
    sekunden: float = 0.0
    urteile: list[Urteil] = field(default_factory=list)

    def __str__(self) -> str:
        teile = [f"{self.gesehen} Dateien in der Wolke",
                 f"{self.gesichert} im Archiv nachgewiesen"]
        if self.fehlt:
            teile.append(f"{self.fehlt} fehlen dort noch")
        if self.gescheitert:
            teile.append(f"{self.gescheitert} nicht lesbar")
        if self.geloescht:
            teile.append(f"{self.geloescht} gelöscht "
                         f"({self.bytes_frei / 1e9:.2f} GB frei)")
        return ", ".join(teile)


def _pruefsumme(datei: Path) -> int:
    summe = 0
    with datei.open("rb") as offen:
        while brocken := offen.read(1 << 20):
            summe = zlib.crc32(brocken, summe)
    return summe


def erlaubnis_pruefen(dienst, zugang: str) -> str:
    """Die Kennung des Anbieters – oder ein Fehler mit Begründung.

    Getrennt vom eigentlichen Lauf, damit die Oberfläche schon vor dem
    ersten Klick weiß, ob sie einen Löschknopf zeigen darf.
    """
    art = dienst.art(zugang)
    if not art:
        raise AufraeumFehler(
            f"»{zugang}« kennt rclone nicht.\n"
            "Vorhandene Zugänge zeigt:  wolkenernte zugang")
    if not darf_loeschen(art):
        anbieter = NACH_KENNUNG.get(art)
        wer = anbieter.name if anbieter else art
        grund = anbieter.hinweis if anbieter else (
            "Dieser Anbieter steht nicht in der Tabelle in anbieter.py.")
        raise AufraeumFehler(
            f"Bei {wer} räumt WOLKENErnte nicht auf.\n\n{grund}")
    return art


def durchgehen(
    archiv: Path,
    wolke: Wolke,
    *,
    wirklich: bool = False,
    kennungen: set[tuple[int, int]] | None = None,
    fortschritt: Callable[[int, int, str], None] | None = None,
    vorbereitung: Callable[[int, int], None] | None = None,
) -> Bilanz:
    """Den Bestand einer Wolke gegen das Archiv halten.

    Ohne ``wirklich`` wird nur gezählt – der Normalfall, und der, mit
    dem jeder anfangen sollte.

    **Der Aufrufer hat vorher :func:`erlaubnis_pruefen` zu fragen.**
    Diese Funktion prüft es nicht noch einmal; sie bekommt eine
    :class:`~wolkenernte.wolke.Wolke` und weiß über den Anbieter
    dahinter nichts.
    """
    begonnen = time.monotonic()
    bilanz = Bilanz()

    medien = wolke.medien()
    if kennungen is None and archiv_ist_leer(archiv):
        raise AufraeumFehler(
            f"In {archiv} liegt kein einziges Bild.\n\n"
            "Erst ernten, dann aufräumen – nie umgekehrt.")
    if kennungen is None:
        # **Nur die Größen, die drüben vorkommen.** Eine Archivdatei
        # anderer Größe kann keine dieser Dateien sein; sie zu lesen
        # wäre reine Zeitverschwendung. Über einen Bestand aus 15.662
        # Bildern gemessen: 296 Sekunden gegen weniger als eine.
        groessen = {e.groesse for p in medien
                    if (e := wolke.eintrag(p)) is not None}
        if vorbereitung:
            vorbereitung(0, 0)
        kennungen = archiv_kennungen(archiv, vorbereitung,
                                     nur_groessen=groessen)

    for nummer, pfad in enumerate(medien, 1):
        eintrag = wolke.eintrag(pfad)
        if eintrag is None:
            continue
        bilanz.gesehen += 1
        if fortschritt:
            fortschritt(nummer, len(medien), pfad)

        try:
            datei = wolke.holen(pfad)
            summe = _pruefsumme(datei)
        except (TakeoutFehler, OSError) as fehler:
            bilanz.gescheitert += 1
            bilanz.urteile.append(
                Urteil(pfad, eintrag.groesse, False, grund=str(fehler)))
            continue

        # Die Größe kommt von der Platte, nicht aus dem Verzeichnis der
        # Wolke: Wenn die beiden auseinanderliegen, ist etwas faul, und
        # dann soll nichts gelöscht werden.
        groesse = datei.stat().st_size
        gesichert = (groesse, summe) in kennungen
        urteil = Urteil(pfad, groesse, gesichert, ablage=datei)

        if gesichert:
            bilanz.gesichert += 1
            if wirklich:
                try:
                    wolke.loeschen(pfad)
                except (RcloneFehler, TakeoutFehler) as fehler:
                    urteil.grund = str(fehler)
                    bilanz.gescheitert += 1
                else:
                    urteil.geloescht = True
                    bilanz.geloescht += 1
                    bilanz.bytes_frei += groesse
        else:
            bilanz.fehlt += 1
            urteil.grund = "liegt so nicht im Archiv"

        bilanz.urteile.append(urteil)

    bilanz.sekunden = time.monotonic() - begonnen
    return bilanz


def bericht(archiv: Path, zugang: str, *, wirklich: bool = False,
            mit_unterordnern: bool = True) -> int:
    """Das Aufräumen von der Kommandozeile aus."""
    from .ernten import ist_wolke
    from .rclone import Dienst
    from .zugang import konfiguration

    if not ist_wolke(zugang):
        print(f"»{zugang}« sieht nicht nach einem Wolkenzugang aus.\n"
              "Gemeint ist etwas wie:  meinewolke:Fotos")
        return 1
    if not archiv.is_dir():
        print(f"{archiv} gibt es nicht.")
        return 1

    name, _, unterordner = zugang.partition(":")
    try:
        dienst = Dienst.starten(konfiguration())
    except RcloneFehler as fehler:
        print(fehler)
        return 1

    try:
        try:
            art = erlaubnis_pruefen(dienst, name)
        except AufraeumFehler as fehler:
            print(fehler)
            return 1

        print(f"=== {zugang}  ({NACH_KENNUNG[art].name}) ===")
        print(f"Archiv: {archiv}\n")

        with Wolke(dienst, name, unterordner,
                   mit_unterordnern=mit_unterordnern) as wolke:
            wie_weit = ("mit allen Unterordnern" if mit_unterordnern
                        else "nur dieser Ordner, ohne Unterordner")
            print(f"\n{len(wolke)} Dateien in {wolke.wurzel} ({wie_weit}), "
                  f"{len(wolke.medien())} davon Bilder und Videos.")
            print("Alles andere - Schriftstücke, Musik, Sonstiges - "
                  "wird nicht angefasst.")
            if not wirklich:
                print("\n**Probelauf.** Es wird nichts gelöscht – dafür "
                      "später --wirklich anhängen.\n")
            try:
                bilanz = durchgehen(
                    archiv, wolke, wirklich=wirklich,
                    vorbereitung=lambda n, g: (
                        print(f"  Archiv {n}/{g}", end="\r", flush=True)
                        if g else print("Passende Dateien im Archiv werden "
                                        "gerechnet …")),
                    fortschritt=lambda n, g, p: (
                        print(f"  {n}/{g}  {p[-46:]:<48}", end="\r", flush=True)
                        if n % 10 == 0 or n == g else None),
                )
            except AufraeumFehler as fehler:
                print(fehler)
                return 1
    finally:
        dienst.beenden()

    print(f"\n{bilanz}")
    print(f"{bilanz.sekunden / 60:.1f} Minuten")

    fehlende = [u for u in bilanz.urteile if not u.gesichert]
    if fehlende:
        print(f"\nNicht im Archiv – diese bleiben stehen ({len(fehlende)}):")
        for urteil in fehlende[:15]:
            print(f"  {urteil.pfad[-60:]}  ({urteil.grund})")
        if len(fehlende) > 15:
            print(f"  … und {len(fehlende) - 15} weitere")
        print("\nErst ernten, dann noch einmal aufräumen:")
        print(f"  wolkenernte ernten \"{archiv}\" {zugang}")

    if not wirklich and bilanz.gesichert:
        print(f"\n{bilanz.gesichert} Dateien ließen sich löschen. "
              f"Dafür denselben Befehl mit --wirklich:")
        print(f"  wolkenernte aufraeumen \"{archiv}\" {zugang} --wirklich")
    return 0

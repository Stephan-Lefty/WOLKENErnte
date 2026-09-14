"""Das Archiv auf eine zweite Platte kopieren – wenn man will.

**Freiwillig, und zwar wirklich.** Kein Vorschlag beim Start, keine
Erinnerung, kein roter Punkt im Menü. Wer WOLKENErnte nur zum
Durchsehen benutzt, erfährt von diesem Teil nie etwas. Das Programm
verlangt keine Sicherung – es macht eine, wenn jemand darum bittet.

**Warum es das trotzdem gibt.** Nach dem Ernten aus einer Wolke und dem
Aufräumen dort ist das Archiv oft die *einzige* Kopie: Die Quelle ist
weg, und in `.wolkenernte/bestand.db` stehen Orte, Titel und Alben, die
es sonst nirgends mehr gibt. Zwei Handgriffe im Dateimanager täten es
auch – aber einer davon geht dabei fast immer schief, und deshalb steht
das hier.

**Der Handgriff, der schiefgeht: die Zeitstempel.** Das Aufnahmedatum
jedes Bildes steckt in der Änderungszeit der Datei; die Jahresordner
sind nur eine Beigabe. Wer mit einem Werkzeug kopiert, das Zeitstempel
nicht überträgt – und dazu gehört das Ziehen mit der Maus in manchen
Dateimanagern –, hat hinterher alle Bilder mit dem heutigen Datum. Die
Kopie ist vollständig, und die ganze Ordnung darin ist zerstört. Nichts
schlägt fehl, nichts warnt.

Deshalb `shutil.copy2` und deshalb die Prüfung danach.

**Kein rsync.** Es wäre naheliegend und kann alles, was hier nötig ist –
aber es ist ein Fremdprogramm, das unter Windows fehlt, und Kopieren
mit erhaltenem Zeitstempel kann Python selbst. Für ffmpeg und rclone
lohnt die Abhängigkeit, hierfür nicht.

**Und nichts wird gelöscht.** Was im Ziel liegt und in der Quelle nicht
mehr, bleibt stehen. Das lässt die Sicherung mit der Zeit wachsen – und
es ist die richtige Richtung für einen Irrtum: Wer im Archiv
versehentlich etwas löscht, findet es in der Sicherung wieder.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


class SicherungFehler(Exception):
    """Die Sicherung kann so nicht laufen."""


def _pruefen(archiv: Path, ziel: Path) -> tuple[Path, Path]:
    """Quelle und Ziel auflösen und die unmöglichen Fälle abfangen.

    **Ein Ziel *im* Archiv wäre eine Falle ohne Boden.** Die Sicherung
    liefe in sich selbst: Jede kopierte Datei taucht beim Durchgehen
    wieder auf, wird erneut kopiert, und das hört erst auf, wenn die
    Platte voll ist. Aufgelöst wird vorher (``resolve``), sonst käme ein
    Symlink oder ein ``..`` daran vorbei.
    """
    archiv = archiv.resolve()
    ziel = ziel.resolve()

    if ziel == archiv:
        raise SicherungFehler(
            "Ziel und Archiv sind derselbe Ordner.")
    if archiv in ziel.parents:
        raise SicherungFehler(
            f"Das Ziel liegt im Archiv selbst ({ziel}).\n"
            f"Die Sicherung würde sich endlos in sich selbst kopieren – "
            f"bitte einen Ordner außerhalb wählen.")
    if ziel in archiv.parents:
        raise SicherungFehler(
            f"Das Archiv liegt im Ziel ({ziel}). Bitte einen eigenen "
            f"Ordner für die Sicherung wählen.")
    return archiv, ziel


@dataclass
class Vorschau:
    """Was eine Sicherung täte – bevor sie etwas tut."""

    dateien: int = 0
    bytes_gesamt: int = 0

    neu: int = 0
    """Dateien, die im Ziel noch gar nicht liegen."""

    geaendert: int = 0
    """Dateien, die dort anders sind – andere Größe oder andere Zeit."""

    unveraendert: int = 0
    bytes_zu_kopieren: int = 0

    platz_frei: int = 0
    ziel_vorhanden: bool = False

    gleiche_platte: bool = False
    """Ob Quelle und Ziel auf demselben Datenträger liegen.

    **Das muss gesagt werden.** Eine Kopie auf derselben Platte schützt
    gegen versehentliches Löschen, gegen einen Tippfehler, gegen ein
    falsch geratenes Programm – aber nicht gegen den Ausfall der Platte,
    und genau davor fürchtet man sich. Verboten wird es nicht: Besser
    eine Kopie an der falschen Stelle als gar keine."""

    @property
    def reicht_der_platz(self) -> bool:
        # Ein Zehntel Luft: Dateisysteme brauchen Verwaltungsplatz, und
        # eine Sicherung, die bei 99 % abbricht, ist keine.
        return self.platz_frei > self.bytes_zu_kopieren * 1.1

    @property
    def zu_tun(self) -> int:
        return self.neu + self.geaendert


@dataclass
class Bilanz:
    """Wie eine Sicherung ausging."""

    kopiert: int = 0
    uebersprungen: int = 0
    bytes_kopiert: int = 0
    misslungen: list[str] = field(default_factory=list)
    abgebrochen: bool = False

    @property
    def geglueckt(self) -> bool:
        return not self.misslungen and not self.abgebrochen

    def __str__(self) -> str:
        from .bestandsliste import umfang

        teile = [f"{self.kopiert:n} Dateien kopiert "
                 f"({umfang(self.bytes_kopiert)})"]
        if self.uebersprungen:
            teile.append(f"{self.uebersprungen:n} waren schon aktuell")
        if self.misslungen:
            teile.append(f"{len(self.misslungen):n} misslungen")
        if self.abgebrochen:
            teile.append("abgebrochen")
        return ", ".join(teile)


def _alle_dateien(wurzel: Path) -> list[Path]:
    """Alles im Archiv – **auch** ``.wolkenernte``.

    Anders als bei :func:`wolkenernte.archiv.medien` gehört der eigene
    Ordner hier dazu: In ``bestand.db`` stehen Orte, Titel und Alben,
    und nach einem Aufräumen in der Wolke gibt es die sonst nirgends
    mehr. Eine Sicherung ohne sie wäre die halbe.
    """
    gefunden = []
    for pfad in wurzel.rglob("*"):
        if pfad.is_file() and not pfad.is_symlink():
            gefunden.append(pfad)
    return gefunden


def _gleich(quelle: Path, ziel: Path) -> bool:
    """Ob die Zieldatei schon dieselbe ist – Größe und Zeit.

    Wie rsync es ohne ``--checksum`` tut. Byteweise zu vergleichen
    hieße, bei jedem Auffrischen einunddreißig Gigabyte zu lesen, um
    fast immer »nichts zu tun« herauszubekommen.
    """
    try:
        a, b = quelle.stat(), ziel.stat()
    except OSError:
        return False
    return a.st_size == b.st_size and abs(a.st_mtime - b.st_mtime) <= 1


def voransehen(archiv: Path, ziel: Path) -> Vorschau:
    """Was eine Sicherung nach ``ziel`` kopieren würde.

    Wirft :class:`SicherungFehler`, wenn Ziel und Archiv ineinander
    liegen – **bevor** irgendjemand auf »Sichern« drückt.
    """
    archiv, ziel = _pruefen(archiv, ziel)
    ergebnis = Vorschau(ziel_vorhanden=ziel.is_dir())

    for pfad in _alle_dateien(archiv):
        ergebnis.dateien += 1
        groesse = pfad.stat().st_size
        ergebnis.bytes_gesamt += groesse

        gegenstueck = ziel / pfad.relative_to(archiv)
        if not gegenstueck.exists():
            ergebnis.neu += 1
            ergebnis.bytes_zu_kopieren += groesse
        elif _gleich(pfad, gegenstueck):
            ergebnis.unveraendert += 1
        else:
            ergebnis.geaendert += 1
            ergebnis.bytes_zu_kopieren += groesse

    # Der Platz am Ziel – oder am nächsten vorhandenen Elternordner,
    # denn das Ziel selbst gibt es beim ersten Mal noch nicht.
    messpunkt = ziel
    while not messpunkt.exists() and messpunkt != messpunkt.parent:
        messpunkt = messpunkt.parent
    try:
        ergebnis.platz_frei = shutil.disk_usage(messpunkt).free
        ergebnis.gleiche_platte = (
            archiv.stat().st_dev == messpunkt.stat().st_dev)
    except OSError:
        pass
    return ergebnis


def sichern(
    archiv: Path,
    ziel: Path,
    *,
    melden: Callable[[int, int, str], None] | None = None,
    abbrechen: Callable[[], bool] | None = None,
) -> Bilanz:
    """Das Archiv nach ``ziel`` kopieren.

    ``melden`` bekommt Nummer, Gesamtzahl und Dateinamen. ``abbrechen``
    wird vor jeder Datei gefragt; sagt es ``True``, hört die Sicherung
    **zwischen** zwei Dateien auf – nie mitten in einer, sonst läge dort
    eine halbe.
    """
    archiv, ziel = _pruefen(archiv, ziel)
    bilanz = Bilanz()
    dateien = _alle_dateien(archiv)
    ziel.mkdir(parents=True, exist_ok=True)

    for nummer, pfad in enumerate(dateien, 1):
        if abbrechen is not None and abbrechen():
            bilanz.abgebrochen = True
            break
        relativ = pfad.relative_to(archiv)
        if melden:
            melden(nummer, len(dateien), str(relativ))

        gegenstueck = ziel / relativ
        if gegenstueck.exists() and _gleich(pfad, gegenstueck):
            bilanz.uebersprungen += 1
            continue

        try:
            gegenstueck.parent.mkdir(parents=True, exist_ok=True)
            # **copy2, nicht copy.** Nur copy2 überträgt die
            # Änderungszeit, und darin steckt das Aufnahmedatum.
            shutil.copy2(pfad, gegenstueck)
            bilanz.kopiert += 1
            bilanz.bytes_kopiert += pfad.stat().st_size
        except OSError as fehler:
            bilanz.misslungen.append(f"{relativ}: {fehler}")
    return bilanz


def nachpruefen(archiv: Path, ziel: Path) -> list[str]:
    """Stichprobe nach der Sicherung – was nicht stimmt, kommt heraus.

    **Geprüft wird vor allem die Zeit.** Dass alle Dateien da sind,
    merkt man später auch; dass ihre Zeitstempel fehlen, merkt man erst,
    wenn man die Sicherung braucht – und dann steht das ganze Archiv
    unter dem Datum der Wiederherstellung.
    """
    abweichungen: list[str] = []
    for pfad in _alle_dateien(archiv):
        relativ = pfad.relative_to(archiv)
        gegenstueck = ziel / relativ
        try:
            a, b = pfad.stat(), gegenstueck.stat()
        except OSError:
            abweichungen.append(f"{relativ}: fehlt in der Sicherung")
            continue
        if a.st_size != b.st_size:
            abweichungen.append(f"{relativ}: andere Größe")
        elif abs(a.st_mtime - b.st_mtime) > 1:
            abweichungen.append(f"{relativ}: anderer Zeitstempel")
    return abweichungen


def in_worten(vorschau: Vorschau) -> list[str]:
    """Die Vorschau als Sätze – für Terminal und Fenster gleichermaßen."""
    from .bestandsliste import umfang

    zeilen = [f"{vorschau.dateien:n} Dateien im Archiv "
              f"({umfang(vorschau.bytes_gesamt)})"]

    if not vorschau.ziel_vorhanden:
        zeilen.append("Das Ziel wird neu angelegt – alles wird kopiert.")
    elif vorschau.zu_tun == 0:
        zeilen.append("Die Sicherung ist auf dem neuesten Stand – "
                      "es gibt nichts zu tun.")
    else:
        was = []
        if vorschau.neu:
            was.append(f"{vorschau.neu:n} neu")
        if vorschau.geaendert:
            was.append(f"{vorschau.geaendert:n} geändert")
        zeilen.append(f"{' und '.join(was)}, "
                      f"{umfang(vorschau.bytes_zu_kopieren)} zu übertragen")
        if vorschau.unveraendert:
            zeilen.append(f"{vorschau.unveraendert:n} sind schon aktuell "
                          f"und werden übersprungen")

    if not vorschau.reicht_der_platz:
        zeilen.append(
            f"**Der Platz reicht nicht**: {umfang(vorschau.platz_frei)} frei, "
            f"gebraucht werden {umfang(vorschau.bytes_zu_kopieren)}.")
    if vorschau.gleiche_platte:
        zeilen.append(
            "**Ziel und Archiv liegen auf demselben Datenträger.** Das "
            "schützt gegen versehentliches Löschen, aber nicht gegen einen "
            "Ausfall der Platte.")
    return zeilen


def bericht(archiv: Path, ziel: Path, *, wirklich: bool = False) -> int:
    """Der Befehl von der Kommandozeile aus.

    Ohne ``--wirklich`` wird nur gezeigt, was geschähe. Dieselbe
    Vorsicht wie beim Aufräumen in der Wolke: Wer kopiert, überschreibt
    im Ziel – und soll vorher gesehen haben, was.
    """
    if not archiv.is_dir():
        print(f"Kein Archiv: {archiv}")
        return 1

    print(f"Archiv:    {archiv}")
    print(f"Sicherung: {ziel}\n")
    vorschau = voransehen(archiv, ziel)
    for zeile in in_worten(vorschau):
        print(f"  {zeile.replace('**', '')}")

    if not vorschau.reicht_der_platz:
        return 1
    if not wirklich:
        if vorschau.zu_tun:
            print("\nProbelauf – es wurde nichts kopiert.")
            print("Mit »--wirklich« wird es ausgeführt.")
        return 0

    print()
    bilanz = sichern(
        archiv, ziel,
        melden=lambda n, g, name: (
            print(f"  {n}/{g}  {name[-50:]}", end="\r", flush=True)
            if n % 50 == 0 or n == g else None))
    print(f"\n{bilanz}")

    if not bilanz.geglueckt:
        for zeile in bilanz.misslungen[:10]:
            print(f"  ! {zeile}")
        return 1

    print("\nWird nachgeprüft …")
    abweichungen = nachpruefen(archiv, ziel)
    if abweichungen:
        print(f"  **{len(abweichungen)} Abweichungen:**")
        for zeile in abweichungen[:10]:
            print(f"    {zeile}")
        return 1
    print("  Jede Datei ist da, mit Größe und Zeitstempel.")
    return 0

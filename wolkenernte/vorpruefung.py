"""Was ein Import brächte – **bevor** man ihn anstößt.

»Ich habe einen neuen Takeout, aber seit dem letzten sind nur ein paar
Bilder dazugekommen« ist der Normalfall, nicht die Ausnahme. Ohne
Vorprüfung sieht man das erst hinterher: Der Lauf liest neun Gigabyte,
übergeht neunundneunzig Prozent davon als bytegleich und meldet am Ende
neunundzwanzig neue Bilder. Das ist nicht falsch, aber niemand traut
sich, einen Lauf zu starten, dessen Ergebnis er nicht abschätzen kann.

**Und es kostet fast nichts.** Beide Seiten kennen ihre Prüfsummen
schon:

* Ein ZIP führt zu jeder Datei Größe und **CRC-32** in seinem
  Inhaltsverzeichnis. Am echten Export gemessen: fünf Teilarchive, neun
  Gigabyte, Verzeichnis gelesen in **0,1 Sekunden** – ohne ein einziges
  entpacktes Byte.
* Das Archiv hat dieselben zwei Angaben in seiner Datenbank, denn
  genau darüber findet das Ernten seine Doppelgänger.

Die CRC-32 im ZIP ist **bitgleich** mit der, die WOLKENErnte selbst
rechnet – beide sind die gewöhnliche CRC-32, und `zlib.crc32` liefert
dieselbe Zahl wie `ZipInfo.CRC`. Nachgemessen, nicht angenommen.

**Warum die Datenbank und nicht die Dateien.** Der ehrliche Weg wäre,
die Prüfsummen des Archivs für diesen Lauf zu rechnen. Am echten
Bestand dauert das **130 Sekunden** – dreißig Gigabyte lesen –, und für
eine Vorschau, die sofort da sein soll, ist das zu lang. Über die
Datenbank sind es **0,2 Sekunden** bei genau demselben Ergebnis
(5.910 schon vorhanden, 29 neu; beide Wege gemessen am 2026-09-12).

Damit eine veraltete Zeile nicht zu einer falschen Auskunft führt, wird
jede mit einem `stat()` gegengeprüft: Eine Zeile, deren Datei
verschwunden ist oder eine andere Größe hat, zählt nicht mit. Das kostet
nichts und fängt alles außer einer Änderung, die die Größe unverändert
lässt.

**Das Ergebnis ist eine Vorschau, kein Beweis.** Der Lauf selbst prüft
weiter Byte für Byte, und er bleibt die Wahrheit. Hier wird niemandem
etwas gelöscht; im schlimmsten Fall steht eine Zahl um eins daneben.
Für die Bedingungen des *Löschens* gilt weiterhin das Gegenteil – dort
wird die Prüfsumme für jeden Lauf neu gerechnet und der Datenbank
ausdrücklich nicht geglaubt.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .lokal import MEDIEN


@dataclass
class Voransicht:
    """Was ein Import an diesem Archiv ändern würde."""

    medien: int = 0
    """Bilder und Videos in der Quelle, Doppelte mitgezählt."""

    verschiedene: int = 0
    """Wie viele davon verschiedene Inhalte sind.

    Google legt jedes Bild, das in einem Album steckt, ein zweites Mal
    ab – der Unterschied zu ``medien`` ist meist beträchtlich."""

    schon_da: int = 0
    neu: int = 0

    bytes_neu: int = 0
    """Wie viel das Archiv wachsen würde."""

    beispiele: list[str] = field(default_factory=list)
    """Ein paar Dateinamen der neuen Bilder – nur die Namen, ohne
    Ordner. Ein Albumname verrät Wohnort oder Urlaubsziel, und diese
    Liste landet in Bildschirmfotos und Fehlerberichten."""

    datenbank_gefragt: bool = True
    """Ob die schnelle Auskunft möglich war.

    ``False`` heißt: Es gibt keine Datenbank, also ist noch nie
    geerntet worden. Dann ist *alles* neu, und das ist keine Schätzung,
    sondern sicher."""

    verwaiste_zeilen: int = 0
    """Zeilen, deren Datei fehlt oder eine andere Größe hat.

    Sie werden übergangen. Die Zahl gehört trotzdem nach außen: Ist sie
    groß, stimmt etwas anderes nicht, und die Vorschau wäre die falsche
    Stelle, das zu verschweigen."""

    nicht_erfasst: int = 0
    """Dateien im Archiv, die die Datenbank nicht kennt.

    **Der Grund, warum diese Zahl nach außen muss:** `ernten` schreibt
    keine Datenbankzeile, das tut erst `erfassen`. Wer nur geerntet hat,
    bekäme sonst »alles neu« zu sehen. Die Vorschau irrt dann zur
    sicheren Seite – sie verspricht zu viel Zuwachs, statt ein Bild
    unterzuschlagen –, aber sagen muss sie es."""

    @property
    def doppelt_in_der_quelle(self) -> int:
        return self.medien - self.verschiedene

    @property
    def lohnt_sich(self) -> bool:
        return self.neu > 0


def _ist_medium(pfad: str) -> bool:
    name = pfad.rsplit("/", 1)[-1]
    return "." in name and "." + name.rsplit(".", 1)[-1].lower() in MEDIEN


@dataclass
class Datenbankstand:
    """Was die Datenbank über das Archiv weiß – und was ihr fehlt."""

    kennungen: set[tuple[int, int]] = field(default_factory=set)
    """Größe und Prüfsumme, für jede Zeile, deren Datei noch passt."""

    brauchbare_zeilen: int = 0
    """Wie viele Zeilen das waren. **Nicht** ``len(kennungen)``:
    Zwei Dateien mit demselben Inhalt teilen eine Kennung."""

    verwaiste_zeilen: int = 0
    """Zeilen, deren Datei fehlt oder eine andere Größe hat."""

    vorhanden: bool = False
    """Ob es überhaupt eine Datenbank gab."""


def kennungen_aus_datenbank(archiv: Path) -> Datenbankstand:
    """Größe und Prüfsumme jeder Archivdatei – aus der Datenbank.

    **Jede Zeile wird mit einem ``stat()`` gegengeprüft.** Eine Zeile,
    deren Datei verschwunden ist oder eine andere Größe hat, zählt
    nicht mit – sonst hieße es »liegt schon im Archiv«, das Bild würde
    nicht geholt, und niemand merkte es. Das kostet nichts und fängt
    alles außer einer Änderung, die die Größe unverändert lässt.
    """
    from .bestand import ORT as DB_ORT

    stand = Datenbankstand()
    ort = archiv / DB_ORT
    if not ort.exists():
        return stand

    try:
        db = sqlite3.connect(f"file:{ort}?mode=ro", uri=True)
    except sqlite3.Error:
        return stand
    stand.vorhanden = True

    try:
        for groesse, summe, pfad in db.execute(
            "SELECT groesse, pruefsumme, pfad FROM bild WHERE pfad IS NOT NULL"
        ):
            if groesse is None or summe is None:
                continue
            try:
                if (archiv / pfad).stat().st_size != groesse:
                    stand.verwaiste_zeilen += 1
                    continue
            except OSError:
                stand.verwaiste_zeilen += 1
                continue
            stand.kennungen.add((groesse, summe))
            stand.brauchbare_zeilen += 1
    except sqlite3.Error:
        pass
    finally:
        db.close()
    return stand


def voransehen(archiv: Path, quelle, *, hoechstens: int = 5) -> Voransicht:
    """Was ``quelle`` diesem Archiv brächte.

    ``quelle`` ist alles, was sich durchlaufen lässt und Einträge mit
    ``pfad``, ``groesse`` und ``pruefsumme`` liefert – ein
    :class:`wolkenernte.takeout.Archiv` also, oder ein
    :class:`wolkenernte.lokal.Ordner`.

    **Einträge ohne Prüfsumme zählen als neu.** Ohne sie lässt sich
    nichts vergleichen, und »vielleicht schon da« wäre die gefährliche
    Antwort: Sie führte dazu, dass ein Bild nicht geholt wird.
    """
    from .archiv import medien as archiv_medien

    stand = kennungen_aus_datenbank(archiv)
    bekannt = stand.kennungen

    # **Die Datei ist die Wahrheit, die Datenbank nur eine Beigabe.**
    # `ernten` allein schreibt keine Zeile – das tut erst `erfassen`.
    # Wer nur geerntet hat, hätte hier eine Vorschau bekommen, die
    # »alles neu« behauptet. Darum wird gezählt, wie viele Dateien im
    # Archiv die Datenbank gar nicht kennt, und das gesagt.
    im_archiv = len(archiv_medien(archiv))
    ergebnis = Voransicht(
        datenbank_gefragt=stand.vorhanden,
        verwaiste_zeilen=stand.verwaiste_zeilen,
        nicht_erfasst=max(0, im_archiv - stand.brauchbare_zeilen),
    )

    gesehen: set[tuple[int, int]] = set()
    for eintrag in quelle:
        if not _ist_medium(eintrag.pfad):
            continue
        ergebnis.medien += 1

        kennung = (eintrag.groesse, eintrag.pruefsumme)
        if not eintrag.pruefsumme:
            # Kein Vergleich möglich – also neu, und jedes Mal einzeln
            # gezählt, weil auch untereinander nichts entscheidbar ist.
            ergebnis.verschiedene += 1
            ergebnis.neu += 1
            ergebnis.bytes_neu += eintrag.groesse
            if len(ergebnis.beispiele) < hoechstens:
                ergebnis.beispiele.append(eintrag.pfad.rsplit("/", 1)[-1])
            continue

        if kennung in gesehen:
            continue          # Doppelt in der Quelle selbst
        gesehen.add(kennung)
        ergebnis.verschiedene += 1

        if kennung in bekannt:
            ergebnis.schon_da += 1
        else:
            ergebnis.neu += 1
            ergebnis.bytes_neu += eintrag.groesse
            if len(ergebnis.beispiele) < hoechstens:
                ergebnis.beispiele.append(eintrag.pfad.rsplit("/", 1)[-1])

    return ergebnis


def in_worten(ergebnis: Voransicht) -> list[str]:
    """Die Vorschau als Sätze – für Terminal und Fenster gleichermaßen.

    Steht hier und nicht in der Oberfläche, damit beide dasselbe sagen;
    dieselbe Überlegung wie bei :mod:`wolkenernte.bestandsliste`.
    """
    from .bestandsliste import umfang

    zeilen = [
        f"{ergebnis.medien:n} Bilder und Videos in der Quelle, "
        f"{ergebnis.verschiedene:n} davon verschieden"
    ]
    if ergebnis.doppelt_in_der_quelle:
        zeilen.append(
            f"{ergebnis.doppelt_in_der_quelle:n} liegen in der Quelle "
            f"doppelt – Google legt jedes Bild in einem Album zweimal ab")

    if not ergebnis.datenbank_gefragt:
        zeilen.append("In diesem Archiv wurde noch nie geerntet – "
                      "alles ist neu.")
    else:
        zeilen.append(f"{ergebnis.schon_da:n} liegen schon im Archiv und "
                      f"werden übergangen")

    if ergebnis.neu:
        zeilen.append(f"{ergebnis.neu:n} kämen hinzu "
                      f"({umfang(ergebnis.bytes_neu)})")
    else:
        zeilen.append("Nichts Neues dabei – der Lauf würde nichts ändern.")

    if ergebnis.verwaiste_zeilen:
        zeilen.append(
            f"Hinweis: {ergebnis.verwaiste_zeilen:n} Datenbankzeilen passen "
            f"nicht mehr zu ihrer Datei und wurden übergangen.")
    if ergebnis.nicht_erfasst:
        zeilen.append(
            f"Hinweis: {ergebnis.nicht_erfasst:n} Dateien im Archiv sind nicht "
            f"erfasst – die Vorschau kann sie nicht berücksichtigen und "
            f"verspricht darum eher zu viel. Der Lauf selbst übergeht sie "
            f"trotzdem; »erfassen« räumt das auf.")
    return zeilen

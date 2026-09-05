"""Bilder finden, die dasselbe zeigen – auch wenn die Dateien verschieden sind.

Bytegleiche Kopien findet schon die Prüfsumme. Der interessantere Fall
ist der andere: **dasselbe Foto, einmal über WhatsApp geschickt und
dabei neu komprimiert.** Zwei völlig verschiedene Dateien, dasselbe
Bild. Dafür braucht es einen Fingerabdruck, der den *Inhalt* beschreibt
und nicht die Bytes.

**Das Verfahren: Differenz-Hash.** Das Bild wird auf 9×8 Graustufen
verkleinert; für jedes Paar benachbarter Punkte wird notiert, ob der
linke heller ist als der rechte. Das ergibt 64 Bit. Zwei Bilder gelten
als ähnlich, wenn sich ihre Fingerabdrücke in wenigen Bit unterscheiden.

**Warum dieses und kein anderes.** Es kommt mit Pillow aus, das ohnehin
für die Vorschaubilder gebraucht wird – kein Fremdpaket, keine
Matrizenrechnung. Es übersteht Größenänderung, Kompression und
Helligkeitsanpassung, weil nur Nachbarschaftsverhältnisse zählen. Es
übersteht **nicht** Drehung und Spiegelung; das ist bewusst in Kauf
genommen, denn ein gedrehtes Bild ist meistens auch eine gewollte
Bearbeitung.

**Und die Suche: keine Paarvergleiche.** Bei 15.000 Bildern wären das
112 Millionen Vergleiche. Stattdessen wird der Fingerabdruck in vier
Blöcke zu 16 Bit zerlegt: Zwei Bilder, die sich in höchstens drei Bit
unterscheiden, müssen in mindestens einem Block **genau** übereinstimmen
– sonst wären es vier Unterschiede. Damit wird aus der Ähnlichkeitssuche
ein Nachschlagen in vier Wörterbüchern.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

#: Kantenlänge für den Fingerabdruck. 9 Spalten ergeben 8 Vergleiche
#: je Zeile, bei 8 Zeilen also 64 Bit.
BREITE, HOEHE = 9, 8

#: Ab wie vielen unterschiedlichen Bit zwei Bilder als verschieden
#: gelten. Bis 3 findet das Banding garantiert alles; darüber wird die
#: Suche unvollständig, aber schneller als jeder Paarvergleich.
SCHWELLE = 3

_BLOECKE = 4
_BLOCKBREITE = 16

#: Wie viele der 64 Bit mindestens gesetzt sein müssen, damit ein
#: Fingerabdruck etwas aussagt.
#:
#: **Ein strukturloses Bild ergibt lauter Nullen.** Eine weiße Wand, ein
#: schwarzes Videobild, eine leere Seite: Nirgends ist der linke Punkt
#: heller als der rechte, der Hash ist 0 – und zwar für alle solchen
#: Bilder derselbe. Ohne diese Grenze landeten sie in einer einzigen
#: riesigen Gruppe »ähnlicher« Bilder, die nichts miteinander zu tun
#: haben. Sechs Bit sind wenig verlangt; jedes Foto mit erkennbarem
#: Inhalt liegt weit darüber.
MINDESTSTRUKTUR = 6

#: Wie viele der acht Zeilen sich mindestens voneinander unterscheiden
#: müssen.
#:
#: **Die Bitzahl allein genügt nicht.** Ein Bild mit einem schlichten
#: Hell-Dunkel-Verlauf von links nach rechts ergibt in jeder Zeile
#: dasselbe Muster – etwa ``00001111`` achtmal untereinander. Das sind
#: 32 gesetzte Bit, die Mindestprüfung oben ist also zufrieden, und
#: trotzdem sagt der Fingerabdruck nichts über das Motiv: **Jedes**
#: Bild mit ähnlichem Verlauf bekommt denselben Wert.
#:
#: Bei einem echten Bestand hat genau das zwei Aufnahmen aus 2023 und
#: 2026 zusammengespannt, die nichts miteinander zu tun hatten. Drei
#: verschiedene Zeilen sind wenig verlangt und schließen nur die Fälle
#: aus, in denen sich das Bild senkrecht praktisch nicht ändert.
MINDESTZEILEN = 3


def fingerabdruck(pfad: Path) -> int | None:
    """Der Differenz-Hash eines Bildes, oder ``None``.

    ``None`` heißt: kein Bild, beschädigt, oder Pillow fehlt. Ein
    kaputtes Foto darf einen Durchlauf über zehntausende Dateien nicht
    abbrechen.
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        with Image.open(pfad) as bild:
            bild.draft("L", (BREITE * 4, HOEHE * 4))
            klein = bild.convert("L").resize((BREITE, HOEHE), Image.Resampling.LANCZOS)
            punkte = list(klein.getdata())
    except Exception:
        return None

    wert = 0
    for zeile in range(HOEHE):
        for spalte in range(BREITE - 1):
            links = punkte[zeile * BREITE + spalte]
            rechts = punkte[zeile * BREITE + spalte + 1]
            wert = (wert << 1) | (1 if links > rechts else 0)
    return wert


def aussagekraeftig(wert: int) -> bool:
    """Ob ein Fingerabdruck überhaupt etwas über das Motiv sagt.

    Zwei Prüfungen, und beide sind nötig: genug gesetzte **und** genug
    ungesetzte Bit (sonst ist das Bild einfarbig), und genug
    verschiedene **Zeilen** (sonst ändert sich das Bild senkrecht
    nicht).
    """
    if wert.bit_count() < MINDESTSTRUKTUR:
        return False
    if (~wert & ((1 << 64) - 1)).bit_count() < MINDESTSTRUKTUR:
        return False
    zeilen = {(wert >> (i * 8)) & 0xFF for i in range(HOEHE)}
    return len(zeilen) >= MINDESTZEILEN


def abstand(a: int, b: int) -> int:
    """In wie vielen Bit sich zwei Fingerabdrücke unterscheiden."""
    return (a ^ b).bit_count()


def gruppen(
    eintraege: Iterable[tuple[str, int]], *, schwelle: int = SCHWELLE
) -> list[list[str]]:
    """Ähnliche Bilder zu Gruppen zusammenfassen.

    ``eintraege`` sind Paare aus Pfad und Fingerabdruck. Zurück kommen
    Gruppen mit mindestens zwei Bildern, größte zuerst.

    Statt aller Paarvergleiche wird über vier 16-Bit-Blöcke vorgefiltert
    – siehe die Erklärung oben. Nur die wenigen Kandidaten, die sich
    einen Block teilen, werden wirklich verglichen.
    """
    # Nichtssagende Fingerabdrücke fliegen vorher heraus - weiße Wände,
    # schwarze Videobilder, schlichte Verläufe. Sonst bilden sie eine
    # einzige Riesengruppe aus Bildern, die nichts gemeinsam haben.
    eintraege = [(p, w) for p, w in eintraege if aussagekraeftig(w)]

    faecher: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(_BLOECKE)]
    for nummer, (_, wert) in enumerate(eintraege):
        for block in range(_BLOECKE):
            teil = (wert >> (block * _BLOCKBREITE)) & 0xFFFF
            faecher[block][teil].append(nummer)

    # Vereinigungsmenge über die Kandidatenpaare.
    eltern = list(range(len(eintraege)))

    def wurzel(i: int) -> int:
        while eltern[i] != i:
            eltern[i] = eltern[eltern[i]]
            i = eltern[i]
        return i

    def vereinen(a: int, b: int) -> None:
        wa, wb = wurzel(a), wurzel(b)
        if wa != wb:
            eltern[wb] = wa

    for fach in faecher:
        for nummern in fach.values():
            if len(nummern) < 2:
                continue
            # Ein Block, den sich sehr viele teilen, ist ein einfarbiger
            # Bereich - etwa lauter schwarze Videobilder. Solche Fächer
            # würden alles mit allem verbinden.
            if len(nummern) > 400:
                continue
            for i, links in enumerate(nummern):
                for rechts in nummern[i + 1:]:
                    if wurzel(links) == wurzel(rechts):
                        continue
                    if abstand(eintraege[links][1], eintraege[rechts][1]) <= schwelle:
                        vereinen(links, rechts)

    sammlung: dict[int, list[str]] = defaultdict(list)
    for nummer, (pfad, _) in enumerate(eintraege):
        sammlung[wurzel(nummer)].append(pfad)

    return sorted((g for g in sammlung.values() if len(g) > 1),
                  key=len, reverse=True)

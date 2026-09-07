"""Schlagwörter, die sich ohne Bilderkennung ergeben.

**Was hier steht, kostet nichts.** Kein Modell, keine Bibliothek, keine
Rechenzeit von Belang: Jahreszeit, Tageszeit, Bildformat und Herkunft
lassen sich aus dem ableiten, was ohnehin bekannt ist. Für einen
Bestand aus fünfzehntausend Bildern ist das in Sekunden erledigt.

Ersetzt das keine Bilderkennung? Nein – »Sommer« sagt nicht, dass ein
Schaf im Bild ist. Aber es beantwortet Fragen, die man tatsächlich
stellt: *die Winterbilder*, *die Nachtaufnahmen*, *die Bildschirmfotos*,
*die Panoramen*. Und es funktioniert für jedes Bild, auch für das, bei
dem ein Modell danebenliegt.

**Höchstens fünf Schlagwörter je Bild.** Wer zwanzig vergibt,
beschreibt nichts mehr, sondern verrauscht die Suche. Die Auswahl
trifft :func:`begrenzen` – dort steht auch, was Vorrang hat.
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass
from datetime import datetime, timezone

#: Wie viele Schlagwörter ein Bild höchstens trägt.
HOECHSTENS = 5

#: Welche Herkunft bei Platzmangel Vorrang hat.
#:
#: **Erkanntes zuerst, Abgeleitetes danach.** Was im Bild zu sehen ist,
#: beschreibt es besser als die Jahreszeit – und die Jahreszeit lässt
#: sich jederzeit aus dem Datum nachrechnen, das ohnehin danebensteht.
#: Ein erkanntes Schlagwort wäre dagegen verloren.
VORRANG = {"bild": 0, "herkunft": 1, "ort": 2, "form": 3, "zeit": 4}


@dataclass(frozen=True)
class Schlagwort:
    name: str
    quelle: str
    sicherheit: float = 1.0


def jahreszeit(zeit: datetime) -> str:
    """Meteorologische Jahreszeit – ganze Monate, keine Tagesgrenzen.

    Die astronomische Rechnung (21. März und so weiter) wäre genauer
    und für diesen Zweck schlechter: Niemand sucht Fotos »vom 20. Juni«
    im Frühling.
    """
    if zeit.month in (12, 1, 2):
        return "Winter"
    if zeit.month in (3, 4, 5):
        return "Frühling"
    if zeit.month in (6, 7, 8):
        return "Sommer"
    return "Herbst"


def uhrzeit_ist_geraten(zeit: datetime) -> bool:
    """Ob hinter dem Zeitstempel gar keine Uhrzeit steckt.

    **Manche Aufnahmen tragen nur ein Datum.** Google schreibt dann
    Mitternacht UTC in die Metadaten, und daraus wird beim Ernten der
    Dateizeitstempel. In Mitteleuropa liegt der dann auf ein oder zwei
    Uhr nachts.

    Am echten Bestand sind das **1.465 von 14.476 Bildern**: Die
    Stunde 1 trägt 1.488 Aufnahmen, die Stunden 2 bis 5 zusammen nur
    39. Ohne diese Prüfung bekäme jedes zehnte Bild »Nachtaufnahme« –
    und ausgerechnet die Bilder, von denen man am wenigsten weiß.
    »Nachtaufnahme« fiel damit von 2.004 auf 539.

    Ein Foto, das *wirklich* auf die Sekunde genau um Mitternacht UTC
    entstand, verliert dabei sein Schlagwort. Das ist eines von
    86.400.
    """
    genau = zeit.astimezone(timezone.utc)
    return (genau.hour, genau.minute, genau.second) == (0, 0, 0)


def tageszeit(zeit: datetime) -> str | None:
    """Grobe Tageszeit, oder ``None`` für die unauffälligen Stunden.

    Nur Nacht und Abend werden vergeben. »Nachmittag« an ein Foto zu
    hängen, sagt nichts – »Nachtaufnahme« dagegen ist eine Eigenschaft,
    nach der man sucht.

    Ohne Uhrzeit gibt es gar nichts: siehe
    :func:`uhrzeit_ist_geraten`.
    """
    if uhrzeit_ist_geraten(zeit):
        return None
    stunde = zeit.hour
    if stunde < 5 or stunde >= 22:
        return "Nachtaufnahme"
    if 5 <= stunde < 8:
        return "Frühmorgens"
    if 20 <= stunde < 22:
        return "Abends"
    return None


def form(breite: int, hoehe: int) -> str | None:
    """Das Seitenverhältnis, soweit es etwas aussagt.

    Ein gewöhnliches Querformat bekommt kein Schlagwort – das wären
    zehntausend Bilder mit demselben Wort.
    """
    if not breite or not hoehe:
        return None
    verhaeltnis = breite / hoehe
    if verhaeltnis >= 2.2:
        return "Panorama"
    if verhaeltnis <= 0.5:
        return "Hochpanorama"
    if verhaeltnis < 1:
        return "Hochformat"
    if 0.97 <= verhaeltnis <= 1.03:
        return "Quadratisch"
    return None


#: Woran sich die Herkunft eines Bildes am Dateinamen ablesen lässt.
#:
#: Nach dem ersten Treffer wird abgebrochen: Ein Bildschirmfoto, das
#: über WhatsApp kam, ist zuerst ein Bildschirmfoto.
#:
#: **Die Muster verlangen die Ziffern mit.** Geräte benennen ihre
#: Dateien nach festen Schemata – ``IMG_20240816_172342``,
#: ``DSCF5198``, ``1000016856`` –, und gerade die Zifferngruppe macht
#: den Unterschied zu einem Namen, den ein Mensch vergeben hat. Ein
#: erster Anlauf suchte bloß nach ``"20"`` und hängte »Handy« an
#: *Kids Kürbis Day 2020* und an jede zweite UUID: 1.587 Fehlgriffe.
#:
#: **Kamera und Handy bleiben getrennt.** Ein noch früherer Anlauf warf
#: beides in einen Topf und traf damit 8.589 von 14.767 Bildern. Ein
#: Schlagwort, das mehr als die Hälfte des Bestands trägt, hilft beim
#: Suchen nicht – und wer seine Kamerabilder sucht, meint gerade nicht
#: die Handyfotos.
HERKUNFT = tuple(
    (schlagwort, _re.compile(muster, _re.IGNORECASE))
    for schlagwort, muster in (
        ("Bildschirmfoto", r"screenshot|bildschirmfoto|screen[_-]\d{4}"),
        ("Bildschirmaufnahme", r"screenrecord|bildschirmaufnahme"),
        ("Messenger", r"-wa\d{4}|whatsapp|telegram|signal-\d|img-\d{8}"),
        ("Bearbeitet",
         r"-bearbeitet|-edited|-effects|-collage|photocollage|~\d\."),
        # Kein ``dji_\d``: die Bilder heißen ``dji_fly_20241227_…``, und
        # das Handymuster weiter unten hätte sie sonst alle geerbt.
        ("Drohne", r"\bdji[_-]|mavic|drone"),
        ("Kamera", r"dscf\d|_?dsc\d{4}|_mg_\d{4}|str\d{5}|\bp\d{7}"),
        ("Handy",
         r"\b(img|vid|mov|pxl|burst|panorama)[_-]\d"
         r"|\b1000\d{6}|\b\d{8}_\d{6}"),
    )
)


def herkunft(name: str) -> str | None:
    """Woher ein Bild stammt, soweit der Dateiname es verrät.

    Das ist keine Bilderkennung, sondern Namenskunde – aber sie trifft
    zuverlässig, weil Geräte und Programme ihre Dateien nach festen
    Mustern benennen.
    """
    for schlagwort, muster in HERKUNFT:
        if muster.search(name):
            return schlagwort
    return None


def aus_angaben(
    *,
    name: str = "",
    zeit: datetime | None = None,
    datum_bekannt: bool = True,
    groesse_bild: tuple[int, int] | None = None,
    ist_video: bool = False,
) -> list[Schlagwort]:
    """Alle Schlagwörter, die sich ohne Bilderkennung ergeben."""
    gefunden: list[Schlagwort] = []

    if ist_video:
        gefunden.append(Schlagwort("Video", "form"))

    if zeit is not None and datum_bekannt:
        gefunden.append(Schlagwort(jahreszeit(zeit), "zeit"))
        stunde = tageszeit(zeit)
        if stunde:
            gefunden.append(Schlagwort(stunde, "zeit"))

    if groesse_bild:
        gestalt = form(*groesse_bild)
        if gestalt:
            gefunden.append(Schlagwort(gestalt, "form"))

    woher = herkunft(name)
    if woher:
        gefunden.append(Schlagwort(woher, "herkunft"))

    return gefunden


#: Was das Modell nicht unterscheiden kann, die Uhr aber schon.
#:
#: Auf- und Untergang sehen auf dem Bild gleich aus – gemessen liegen
#: die beiden Begriffe bei 0,975 auseinander, also praktisch
#: aufeinander. Ein Mensch könnte es am Bild allein auch nicht sagen.
#: Deshalb fragt das Modell nur nach dem *Phänomen*, und die
#: Aufnahmezeit entscheidet über den Namen.
VOR = 11  # bis dahin morgens


def nach_der_uhr(woerter: list[Schlagwort], zeit: datetime | None,
                 datum_bekannt: bool = True) -> list[Schlagwort]:
    """Schlagwörter, die erst mit der Uhrzeit vollständig werden.

    Hier treffen sich die beiden Hälften: Was aus dem Bild kommt, wird
    von dem berichtigt, was ohnehin bekannt ist. Ohne verlässliche
    Uhrzeit bleibt alles, wie es war – lieber das häufigere Wort als
    ein geratenes.
    """
    if zeit is None or not datum_bekannt or uhrzeit_ist_geraten(zeit):
        return woerter
    if zeit.hour >= VOR:
        return woerter
    return [Schlagwort("Sonnenaufgang", w.quelle, w.sicherheit)
            if w.name == "Sonnenuntergang" else w
            for w in woerter]


def begrenzen(woerter: list[Schlagwort],
              hoechstens: int = HOECHSTENS) -> list[Schlagwort]:
    """Auf die aussagekräftigsten Schlagwörter eindampfen.

    Sortiert nach Herkunft (siehe :data:`VORRANG`) und innerhalb dessen
    nach Sicherheit. Doppelte Namen fliegen heraus – dasselbe Wort aus
    zwei Quellen bleibt ein Wort.
    """
    gesehen: set[str] = set()
    einmalig: list[Schlagwort] = []
    for wort in sorted(woerter,
                       key=lambda w: (VORRANG.get(w.quelle, 9), -w.sicherheit)):
        if wort.name in gesehen:
            continue
        gesehen.add(wort.name)
        einmalig.append(wort)
    return einmalig[:hoechstens]

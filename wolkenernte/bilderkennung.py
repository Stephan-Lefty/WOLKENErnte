"""Schlagwörter aus dem Bild selbst – die Auswertung.

Hier steht der Teil, der **kein Modell braucht**: Aus den Ähnlichkeiten,
die ein Bilderkennungsmodell für jede Frage aus
:mod:`wolkenernte.begriffe` liefert, werden deutsche Schlagwörter. Das
ist reines Rechnen mit ein paar hundert Zahlen, läuft ohne Fremdpakete
und lässt sich prüfen, ohne 335 MB Modell zu laden.

Der Weg vom Bild zu diesen Zahlen steht in
:mod:`wolkenernte.bildmodell` und ist optional – ohne ihn gibt es die
Schlagwörter aus Datum und Dateiname, mehr nicht.

**Warum überhaupt gerechnet und nicht einfach das höchste genommen?**
Ein Modell dieser Art gibt für jede Frage eine Ähnlichkeit zwischen
etwa 0,1 und 0,4 zurück – auch für Fragen, die überhaupt nicht passen.
Die nackte Zahl sagt darum wenig; erst der Vergleich mit den
Mitbewerbern derselben Gruppe sagt etwas. Genau das tut :func:`anteile`.
"""

from __future__ import annotations

import math

from .begriffe import GRUPPEN, Gruppe, alle_begriffe
from .schlagworte import Schlagwort

#: Womit die Ähnlichkeiten gestreckt werden, bevor verglichen wird.
#:
#: CLIP-artige Modelle bringen diesen Faktor selbst mit (er wird
#: mittrainiert und liegt bei 100). Ohne ihn liegen alle Ähnlichkeiten
#: so dicht beieinander, dass nach dem Vergleich jede Antwort ungefähr
#: gleich wahrscheinlich aussieht und keine Schwelle je erreicht wird.
LOGIT_SKALA = 100.0


def anteile(werte: dict[str, float]) -> list[float]:
    """Ähnlichkeiten in Anteile umrechnen, die zusammen 1 ergeben.

    Der übliche Weg (»Softmax«), aber mit dem Größten vorweg
    abgezogen: ``exp(40)`` allein ist schon eine Zahl mit 17 Stellen,
    und bei einer Skala von 100 wäre der Überlauf sicher.
    """
    if not werte:
        return []
    roh = [wert * LOGIT_SKALA for wert in werte.values()]
    groesster = max(roh)
    gestreckt = [math.exp(wert - groesster) for wert in roh]
    summe = sum(gestreckt)
    return [wert / summe for wert in gestreckt]


def je_begriff(gruppe: Gruppe, aehnlichkeiten: dict[str, float]
               ) -> dict[str, float]:
    """Die Ähnlichkeiten einer Gruppe je Begriff mitteln.

    Zu jedem Begriff gehören mehrere englische Formulierungen. Ihr
    Mittelwert ist deutlich verlässlicher als jede einzelne – ein
    unglücklich gewählter Satz zieht das Ergebnis dann nicht mehr
    allein.
    """
    gemittelt: dict[str, float] = {}
    for begriff in gruppe.begriffe:
        einzeln = [aehnlichkeiten[frage] for frage in begriff.fragen
                   if frage in aehnlichkeiten]
        if einzeln:
            gemittelt[begriff.name] = sum(einzeln) / len(einzeln)
    return gemittelt


def auswerten(aehnlichkeiten: dict[str, float]) -> list[Schlagwort]:
    """Aus den Ähnlichkeiten die Schlagwörter machen.

    ``aehnlichkeiten`` ist die Zuordnung *englische Frage → Ähnlichkeit*
    für alle Fragen aus :func:`wolkenernte.begriffe.alle_begriffe`.

    Jede Gruppe wird für sich ausgewertet und gibt höchstens ihre
    ``hoechstens`` besten Antworten ab, und auch die nur, wenn sie über
    der ``schwelle`` der Gruppe liegen. Eine Gruppe darf also leer
    ausgehen – ein Bild, auf dem nichts Bestimmtes zu erkennen ist,
    bekommt lieber gar kein Wort als ein geratenes.
    """
    gefunden: list[Schlagwort] = []
    for gruppe in GRUPPEN:
        gemittelt = je_begriff(gruppe, aehnlichkeiten)
        if not gemittelt:
            continue
        verteilung = dict(zip(gemittelt, anteile(gemittelt)))
        beste = sorted(verteilung.items(), key=lambda paar: -paar[1])
        for name, anteil in beste[:gruppe.hoechstens]:
            if anteil >= gruppe.schwelle:
                gefunden.append(Schlagwort(name, gruppe.quelle, anteil))
    return gefunden


def fragen() -> list[str]:
    """Alle englischen Fragen, in der festgelegten Reihenfolge.

    Die Reihenfolge ist verbindlich: Die mitgelieferten vorberechneten
    Zahlenreihen liegen genau so. Wer :mod:`wolkenernte.begriffe`
    ändert, muss sie neu rechnen lassen.
    """
    return [frage for _, _, frage in alle_begriffe()]

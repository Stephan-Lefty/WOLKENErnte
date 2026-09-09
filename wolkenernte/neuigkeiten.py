"""Nachsehen, ob es eine neuere Fassung gibt.

    wolkenernte neuigkeiten

**Das ist der einzige Netzaufruf, den WOLKENErnte von sich aus an einen
fremden Server richtet** – und er geschieht nur, wenn jemand ihn
ausdrücklich verlangt. Kein Aufruf beim Start, keiner im Hintergrund,
keiner nebenbei. Ein Bildarchiv, das ungefragt nach Hause telefoniert,
wäre das Gegenteil dessen, was dieses Programm sein soll; das Modell
für die Schlagwörter wird aus demselben Grund nur einmal geholt und
läuft danach offline.

**Warum es den Befehl trotzdem gibt.** Die Veröffentlichungen liegen
als Dateien auf GitHub. Wer WOLKENErnte selbst gebaut hat, erfährt von
einer neuen Fassung sonst gar nichts – und läuft womöglich monatelang
auf einem Stand, dessen Fehler längst behoben sind. Genau das ist
passiert: Zwei Veröffentlichungen kamen beim Entwickler selbst nie an.

Übertragen wird dabei nichts als die Anfrage. Kein Archivinhalt, keine
Kennung, keine Zählung – GitHub sieht eine IP-Adresse und den Namen des
Programms, wie bei jedem Aufruf der Seite im Browser auch.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import __version__

#: Wo die neueste Veröffentlichung steht.
ZIEL = ("https://api.github.com/repos/Stephan-Lefty/WOLKENErnte/"
        "releases/latest")

#: Wie lange auf eine Antwort gewartet wird.
#:
#: Kurz gehalten: Wer den Befehl aufruft, wartet davor. Zehn Sekunden
#: reichen für eine Antwort von wenigen Kilobyte; danach ist ohnehin
#: etwas anderes im Argen als die Fassung.
FRIST = 10.0

#: GitHub weist Anfragen ohne Programmkennung ab.
KENNUNG = f"WOLKENErnte/{__version__} (+https://github.com/Stephan-Lefty)"


class NeuigkeitenFehler(Exception):
    """Es ließ sich nicht nachsehen – mit einem Satz, der das erklärt."""


@dataclass(frozen=True)
class Neuigkeit:
    """Was auf der anderen Seite steht."""

    fassung: str
    adresse: str
    erschienen: str


def zerlegen(fassung: str) -> tuple[int, ...]:
    """»v0.4.1« wird zu ``(0, 4, 1)``.

    **Zahlen, nicht Zeichenketten.** Als Text verglichen wäre ``0.10.0``
    kleiner als ``0.4.1``, weil »1« vor »4« steht – und der Hinweis auf
    die neue Fassung bliebe genau dann aus, wenn er am nötigsten ist.

    Ein Anhängsel wie ``1.0.0rc1`` wird auf seine führenden Ziffern
    gekürzt. Das ist grob, aber für dieses Programm genau richtig: Es
    gibt keine Vorabfassungen, und eine vollständige Umsetzung von
    PEP 440 hieße, ein Fremdpaket dafür hereinzuholen.
    """
    ziffern = []
    for teil in fassung.strip().lstrip("vV").split("."):
        treffer = re.match(r"\d+", teil)
        if not treffer:
            break
        ziffern.append(int(treffer.group()))
    return tuple(ziffern)


def ist_neuer(dort: str, hier: str) -> bool:
    """Ob ``dort`` eine höhere Fassung ist als ``hier``."""
    return zerlegen(dort) > zerlegen(hier)


def neueste(*, oeffnen=None) -> Neuigkeit:
    """Die neueste Veröffentlichung erfragen.

    ``oeffnen`` gibt es nur für die Tests – kein Test darf GitHub
    tatsächlich anrufen. Ein Testlauf, der ohne Netz durchfällt, prüft
    die Leitung und nicht das Programm.
    """
    hole = oeffnen or urllib.request.urlopen
    anfrage = urllib.request.Request(
        ZIEL, headers={"User-Agent": KENNUNG,
                       "Accept": "application/vnd.github+json"})
    try:
        with hole(anfrage, timeout=FRIST) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        raise NeuigkeitenFehler(
            f"GitHub antwortet mit {fehler.code}. Wenn das anhält, steht "
            f"die neueste Fassung auf der Seite des Projekts.") from fehler
    except urllib.error.URLError as fehler:
        raise NeuigkeitenFehler(
            f"Keine Verbindung zu GitHub: {fehler.reason}") from fehler
    except (OSError, ValueError) as fehler:
        raise NeuigkeitenFehler(f"Die Antwort war nicht zu lesen: "
                                f"{fehler}") from fehler

    marke = daten.get("tag_name")
    if not marke:
        raise NeuigkeitenFehler("GitHub nennt keine Fassung.")
    return Neuigkeit(
        fassung=marke.lstrip("vV"),
        adresse=daten.get("html_url") or
        "https://github.com/Stephan-Lefty/WOLKENErnte/releases",
        erschienen=(daten.get("published_at") or "")[:10],
    )


def bericht() -> int:
    """Der Befehl von der Kommandozeile aus.

    Der Rückgabewert unterscheidet drei Dinge, damit ein Skript sie
    auseinanderhalten kann: 0 – aktuell, 1 – nachsehen ging nicht,
    2 – es gibt etwas Neueres.
    """
    print(f"Installiert:  {__version__}")
    try:
        neu = neueste()
    except NeuigkeitenFehler as fehler:
        print(f"\n{fehler}")
        return 1

    wann = f" (vom {neu.erschienen})" if neu.erschienen else ""
    print(f"Neueste:      {neu.fassung}{wann}")

    if not ist_neuer(neu.fassung, __version__):
        print("\nDie installierte Fassung ist aktuell.")
        return 0

    print(f"\nEs gibt eine neuere Fassung: {neu.fassung}")
    print(f"  {neu.adresse}")
    print("\nWas sich geändert hat, steht im Änderungsprotokoll:")
    print("  https://github.com/Stephan-Lefty/WOLKENErnte/blob/main/"
          "CHANGELOG.md")
    return 2

"""Was in einer Takeout-Metadatendatei steht – und was davon stimmt.

Google legt neben jedes Bild eine JSON mit Aufnahmedatum, Ort und Titel.
Diese Angaben sind wichtiger als die im Bild selbst: **Beim Hochladen
rechnet Google die Bilder um und verliert dabei regelmäßig Datum und
Ortsangabe.** Wer sich auf die EXIF-Daten im Bild verlässt, bekommt bei
einem großen Teil des Bestands gar nichts oder etwas Falsches. Genau
deshalb gibt es die ganze Familie von Takeout-Werkzeugen.

Drei Fallen stecken in dieser Datei:

**``formatted`` niemals auswerten.** Neben jedem Zeitstempel steht eine
lesbare Fassung – aber in der Sprache des Kontos und in wechselndem
Aufbau. Der Zeitstempel daneben ist eindeutig; der Text ist es nicht.

**Zwei Ortsangaben, und beide können Null sein.** ``geoDataExif`` gilt
vor ``geoData``. Stehen in beiden Nullen, ist **kein Ort bekannt** –
(0,0) liegt im Golf von Guinea und ist nie eine echte Aufnahme.

**``creationTime`` ist nicht die Aufnahmezeit**, sondern der Zeitpunkt
des Hochladens. Ein Bild von 1998, das 2015 eingescannt und hochgeladen
wurde, trägt dort 2015.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


class MetadatenFehler(Exception):
    """Die Datei ließ sich nicht lesen oder ist keine Bildbeschreibung."""


@dataclass(frozen=True)
class Angaben:
    """Was über ein Bild bekannt ist."""

    titel: str = ""
    """Der ursprüngliche Dateiname, ohne die Nummer eines Duplikats.
    Überlebt Googles Kürzung und ist damit der beste Weg zurück zum
    echten Namen."""

    beschreibung: str = ""

    aufgenommen: datetime | None = None
    """Wann das Bild entstand, in UTC. ``None``, wenn unbekannt **oder
    wenn die Zuordnung unsicher war** – siehe ``aus_json``."""

    hochgeladen: datetime | None = None
    """Wann es zu Google kam. Nicht mit der Aufnahmezeit verwechseln."""

    ort: tuple[float, float] | None = None
    """Breite und Länge, oder ``None``. Wie beim Datum gilt: Bei
    unsicherer Zuordnung bleibt das Feld leer."""

    favorit: bool = False
    papierkorb: bool = False
    archiviert: bool = False

    unvollstaendig: bool = False
    """Ob Datum und Ort absichtlich weggelassen wurden, weil die
    Metadaten möglicherweise zu einem anderen Bild gehören. Die
    Oberfläche soll das anzeigen können – »kein Datum« und »Datum
    verschwiegen« sind zwei verschiedene Aussagen."""


def _zeitstempel(zweig: object) -> datetime | None:
    """Aus ``{"timestamp": "1563379729", ...}`` eine Zeit machen.

    Nur ``timestamp`` wird gelesen, niemals ``formatted``. Google
    schreibt gelegentlich ``"0"`` oder einen leeren Text – beides heißt
    »unbekannt«, nicht »1. Januar 1970«.
    """
    if not isinstance(zweig, dict):
        return None
    roh = zweig.get("timestamp")
    if not isinstance(roh, str) or not roh or roh == "0":
        return None
    try:
        sekunden = int(roh)
    except ValueError:
        return None
    if sekunden <= 0:
        return None
    try:
        return datetime.fromtimestamp(sekunden, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _ort(daten: dict) -> tuple[float, float] | None:
    """Die Ortsangabe, mit ``geoDataExif`` vor ``geoData``.

    Der Nullpunkt gilt als »kein Ort«. Das ist keine Kleinigkeit: Ein
    erheblicher Teil der Takeout-Dateien trägt dort Nullen, obwohl
    Google den Ort kennt. Wer sie übernimmt, verteilt seinen halben
    Bestand auf eine Stelle im Golf von Guinea.
    """
    for feld in ("geoDataExif", "geoData"):
        zweig = daten.get(feld)
        if not isinstance(zweig, dict):
            continue
        breite, laenge = zweig.get("latitude"), zweig.get("longitude")
        if not isinstance(breite, (int, float)) or not isinstance(laenge, (int, float)):
            continue
        if breite == 0 and laenge == 0:
            continue
        return (float(breite), float(laenge))
    return None


def ist_album(daten: dict) -> bool:
    """Ob die Datei ein Album beschreibt statt eines Bildes.

    Albumdateien tragen einen Titel, aber keine Aufnahmezeit. Sie liegen
    in denselben Ordnern und würden sonst als Bildbeschreibungen gezählt.
    """
    return "photoTakenTime" not in daten and "title" in daten


def aus_json(rohdaten: bytes, *, sicher: bool = True) -> Angaben:
    """Eine Metadatendatei auswerten.

    ``sicher=False`` heißt: Die Datei wurde über einen Umweg gefunden
    und beschreibt möglicherweise ein **anderes** Bild. Dann werden
    Datum und Ort **nicht** übernommen – Titel und Beschreibung schon,
    denn die gelten auch für eine bearbeitete Fassung.

    Das ist die Lehre aus einem Fehler anderer Werkzeuge: Dort wanderten
    Ortsangaben fremder Fotos in die Bilder, mit Abweichungen von
    hunderten Kilometern. Lieber keine Angabe als eine falsche.
    """
    try:
        daten = json.loads(rohdaten)
    except (json.JSONDecodeError, UnicodeDecodeError) as fehler:
        raise MetadatenFehler(f"Keine lesbare JSON: {fehler}") from fehler

    if not isinstance(daten, dict):
        raise MetadatenFehler("JSON enthält kein Objekt.")

    # Albumdateien sind gelegentlich eingewickelt.
    if isinstance(daten.get("albumData"), dict):
        daten = daten["albumData"]

    titel = daten.get("title")
    beschreibung = daten.get("description")

    gemeinsam = {
        "titel": titel if isinstance(titel, str) else "",
        "beschreibung": beschreibung if isinstance(beschreibung, str) else "",
        "favorit": daten.get("favorited") is True,
        "papierkorb": daten.get("trashed") is True,
        "archiviert": daten.get("archived") is True,
    }

    if not sicher:
        return Angaben(**gemeinsam, unvollstaendig=True)

    return Angaben(
        **gemeinsam,
        aufgenommen=_zeitstempel(daten.get("photoTakenTime")),
        hochgeladen=_zeitstempel(daten.get("creationTime")),
        ort=_ort(daten),
    )

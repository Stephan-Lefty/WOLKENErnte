"""Die deutschen Schlagwörter, nach denen im Bild gesucht wird.

Ein Bilderkennungsmodell erfindet keine Begriffe – man gibt ihm eine
Liste vor, und es bewertet, wie gut jeder davon zum Bild passt. Diese
Liste steht hier. Sie ist das Herz der Bilderkennung: Ein Bild kann nur
Schlagwörter bekommen, die jemand vorher aufgeschrieben hat.

Drei Entscheidungen stecken darin, und alle drei sind es wert, erklärt
zu werden.

**Die Frage lautet englisch, die Antwort deutsch.** Das Modell versteht
nur Englisch – mehrsprachige Modelle gibt es, aber sie kosten zwischen
250 MB und 1,6 GB zusätzlich, nur für den Textteil, und antworten auf
Deutsch schlechter als auf Englisch. Das ist hier kein Verlust: Die
englischen Sätze werden **einmal beim Bauen** in Zahlenreihen
umgerechnet und liegen dem Programm fertig bei. Zur Laufzeit läuft nur
noch der Bildteil. Der deutsche Name daneben ist schlicht unserer – wir
schreiben ihn hin, wie er heißen soll, und niemand übersetzt etwas.

**Gruppen statt einer langen Liste.** Die Zahlen, die das Modell
liefert, lassen sich *innerhalb* einer Auswahl vergleichen, nicht über
das ganze Feld hinweg: »Strand« und »Küche« stehen nie zur selben Frage
an. Ohne Gruppen fräßen außerdem fünf Verwandte alle fünf Plätze –
*Strand, Meer, Küste, Sand, Urlaub* beschreibt ein Bild nicht fünfmal
besser als *Strand*. Je Gruppe wird darum höchstens ein Wort vergeben,
und die fünf Plätze verteilen sich auf verschiedene Arten von Aussage:
wo, was, wann, wie.

**Nur Wörter, nach denen jemand sucht.** Kein »Objekt«, kein
»Draußen«, keine Hunderassen. Die Frage ist nicht, was ein Modell
unterscheiden *kann*, sondern was jemand in fünfzehntausend Bildern
wiederfinden *will*.

Siehe auch :mod:`wolkenernte.schlagworte` – die Schlagwörter, die sich
schon aus Datum, Dateiname und Bildmaßen ergeben und kein Modell
brauchen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Wie der englische Suchsatz gebaut wird.
#:
#: Ein einzelner Satz trifft launisch; der Mittelwert über mehrere
#: Formulierungen ist deutlich stabiler. Das ist beim Bauen kostenlos –
#: gerechnet wird einmal, mitgeliefert wird nur das Ergebnis.
VORLAGEN = (
    "a photo of {}.",
    "a photo of {}, a personal snapshot.",
    "a picture showing {}.",
)


@dataclass(frozen=True)
class Begriff:
    """Ein deutsches Schlagwort und die englischen Sätze dazu.

    ``fragen`` sind mehrere Formulierungen desselben Gedankens. Sie
    werden gemittelt; wo ein einzelnes Wort mehrdeutig ist (*bar* ist
    ein Lokal und eine Maßeinheit), rückt eine zweite Formulierung es
    zurecht.
    """

    name: str
    fragen: tuple[str, ...]


@dataclass(frozen=True)
class Gruppe:
    """Eine Frage an das Bild und die Antworten, die zur Wahl stehen.

    ``schwelle`` ist der Anteil, den der Sieger unter den Antworten
    dieser Gruppe auf sich vereinen muss. Bei einer Gruppe mit zehn
    Antworten wäre reines Raten 0,1 – wer bei 0,35 abschneidet,
    verlangt also, dass das Modell sich deutlich festlegt.

    ``hoechstens`` erlaubt einer Gruppe mehr als ein Wort. Das ist die
    Ausnahme: Nur wo sich zwei Antworten wirklich nicht ausschließen
    (ein Bild kann Hund *und* Katze zeigen), ist es sinnvoll.
    """

    titel: str
    schwelle: float
    begriffe: tuple[Begriff, ...]
    hoechstens: int = 1
    quelle: str = field(default="bild")


def _b(name: str, *fragen: str) -> Begriff:
    return Begriff(name, fragen)


#: Wo das Bild entstanden ist.
#:
#: Die größte Gruppe, und die nützlichste: Nach dem Ort sucht man
#: zuerst. Drinnen und draußen stehen bewusst in derselben Gruppe – ein
#: Bild ist das eine oder das andere, nie beides.
ORT = Gruppe("Ort", 0.22, (
    _b("Strand", "a beach", "sand and sea at the shore"),
    _b("Meer", "the open sea", "waves on the ocean"),
    _b("See", "a lake", "a calm lake surrounded by land"),
    _b("Fluss", "a river", "a river flowing through a landscape"),
    _b("Wald", "a forest", "trees in a woodland"),
    _b("Berge", "mountains", "a mountain landscape"),
    _b("Wiese", "a meadow", "a green field of grass"),
    _b("Feld", "a farm field", "farmland and crops"),
    _b("Garten", "a garden", "a private garden with plants"),
    _b("Park", "a public park", "a park with lawns and paths"),
    _b("Stadt", "a city", "streets and buildings in a town"),
    _b("Dorf", "a village", "a small rural village"),
    _b("Innenraum", "the inside of a room", "an indoor room"),
    _b("Küche", "a kitchen", "the inside of a kitchen"),
    _b("Lokal", "the inside of a restaurant or cafe",
       "people sitting at tables in a cafe"),
    _b("Kirche", "a church", "the inside of a church"),
    _b("Museum", "a museum", "the inside of a museum or gallery"),
    _b("Bahnhof", "a railway station", "a train platform"),
    _b("Flughafen", "an airport", "an airport terminal"),
    _b("Hafen", "a harbour", "boats moored in a harbour"),
    _b("Schwimmbad", "a swimming pool", "people at a swimming pool"),
    _b("Baustelle", "a construction site", "building work in progress"),
    _b("Werkstatt", "a workshop", "a workbench with tools"),
    _b("Büro", "an office", "a desk in an office"),
    _b("Zuhause", "a living room at home", "the inside of a home"),
))

#: Was auf dem Bild die Hauptsache ist.
#:
#: ``hoechstens=2``: Anders als beim Ort schließen sich diese Antworten
#: nicht aus. Ein Bild kann ein Kind mit einem Hund zeigen, und beides
#: gehört daran.
MOTIV = Gruppe("Motiv", 0.18, (
    _b("Porträt", "a portrait of one person", "a close-up of a person's face"),
    _b("Gruppenbild", "a group of people posing together",
       "several people photographed together"),
    _b("Kind", "a child", "a small child"),
    _b("Hund", "a dog", "a pet dog"),
    _b("Katze", "a cat", "a pet cat"),
    _b("Pferd", "a horse", "horses in a field"),
    _b("Vogel", "a bird", "a bird outdoors"),
    _b("Schaf", "sheep", "sheep grazing"),
    _b("Tier", "an animal", "a wild animal"),
    _b("Blume", "a flower", "flowers in bloom"),
    _b("Baum", "a tree", "a single tree"),
    _b("Essen", "a plate of food", "a meal on a table"),
    _b("Kuchen", "a cake", "cake or pastry"),
    _b("Getränk", "a drink in a glass", "glasses with drinks"),
    _b("Auto", "a car", "a parked car"),
    _b("Fahrrad", "a bicycle", "a bike"),
    _b("Boot", "a boat", "a boat on the water"),
    _b("Zug", "a train", "a railway train"),
    _b("Flugzeug", "an aeroplane", "an aircraft"),
    _b("Gebäude", "a building", "the facade of a building"),
    _b("Brücke", "a bridge", "a bridge over water"),
    _b("Denkmal", "a monument", "a statue or memorial"),
    _b("Handarbeit", "knitting or sewing", "handmade textile craft"),
    _b("Werkzeug", "tools", "hand tools laid out"),
    _b("Buch", "a book", "an open book"),
    _b("Dokument", "a document or letter", "a printed page of text"),
    _b("Bildschirm", "a computer screen", "a screen showing an application"),
), hoechstens=2)

#: Wozu das Bild entstanden ist.
#:
#: Der Anlass ist das, was ein Bild in der Erinnerung festhält – »die
#: Hochzeit«, »der Geburtstag«. Die Schwelle liegt hoch: Ein falsch
#: geratener Anlass ärgert mehr als ein fehlender.
ANLASS = Gruppe("Anlass", 0.30, (
    _b("Feier", "a party", "people celebrating at a party"),
    _b("Geburtstag", "a birthday party", "a birthday cake with candles"),
    _b("Hochzeit", "a wedding", "a bride and groom"),
    _b("Weihnachten", "christmas", "a christmas tree with decorations"),
    _b("Ostern", "easter", "easter eggs and decorations"),
    _b("Konzert", "a concert", "musicians performing on a stage"),
    _b("Sport", "people playing sport", "a sports match"),
    _b("Wandern", "hiking", "people walking on a hiking trail"),
    _b("Markt", "a market", "market stalls with goods"),
    _b("Ausflug", "a day trip sightseeing", "tourists visiting a place"),
    _b("Umzug", "moving house", "cardboard moving boxes"),
))

#: Licht und Wetter.
#:
#: Kleine Gruppe, hohe Schwelle: Diese Wörter sind auffällig genau dann,
#: wenn sie zutreffen, und nichtssagend, wenn man sie großzügig
#: vergibt.
WETTER = Gruppe("Wetter", 0.32, (
    _b("Sonnenuntergang", "a sunset", "the sun setting over the horizon"),
    _b("Sonnenaufgang", "a sunrise", "the sun rising at dawn"),
    _b("Schnee", "snow", "a snow-covered landscape"),
    _b("Nebel", "fog", "a foggy misty landscape"),
    _b("Regen", "rain", "a rainy day with wet ground"),
    _b("Gewitter", "a thunderstorm", "dark storm clouds with lightning"),
    _b("Regenbogen", "a rainbow", "a rainbow in the sky"),
))

#: Wie aufgenommen wurde.
#:
#: Beschreibt nicht den Inhalt, sondern die Machart – und trennt damit
#: Bilder, die inhaltlich gleich aussehen: die Luftaufnahme vom Dorf,
#: die Nahaufnahme der Blume.
MACHART = Gruppe("Machart", 0.30, (
    _b("Nahaufnahme", "an extreme close-up photograph",
       "a macro photograph of a small subject"),
    _b("Luftaufnahme", "an aerial photograph from above",
       "a bird's eye view from a drone"),
    _b("Schwarzweiß", "a black and white photograph",
       "a monochrome photograph"),
    _b("Zeichnung", "a drawing or illustration",
       "a hand-drawn picture, not a photograph"),
    _b("Karte", "a map", "a printed map or plan"),
))

#: Alle Gruppen in der Reihenfolge, in der sie gefragt werden.
GRUPPEN = (ORT, MOTIV, ANLASS, WETTER, MACHART)


def alle_begriffe() -> list[tuple[str, str, str]]:
    """Jeden Begriff einmal, als ``(Gruppe, Name, Frage)``.

    Eine Zeile je englischem Satz – genau die Reihenfolge, in der das
    Werkzeug zum Vorberechnen die Zahlenreihen ablegt. Der Aufbau darf
    sich ändern; wer ihn ändert, muss die mitgelieferte Datei neu
    rechnen lassen, sonst zeigen die Zahlen auf die falschen Wörter.
    """
    zeilen: list[tuple[str, str, str]] = []
    for gruppe in GRUPPEN:
        for begriff in gruppe.begriffe:
            for frage in begriff.fragen:
                zeilen.append((gruppe.titel, begriff.name, frage))
    return zeilen


def namen() -> list[str]:
    """Alle deutschen Schlagwörter, ohne Wiederholung."""
    gesehen: list[str] = []
    for gruppe in GRUPPEN:
        for begriff in gruppe.begriffe:
            if begriff.name not in gesehen:
                gesehen.append(begriff.name)
    return gesehen

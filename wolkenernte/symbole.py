"""Das Programmsymbol finden – auch nach dem Installieren.

**Das ist der Grund, warum es dieses Modul gibt.** Die Bilder lagen
unter ``assets/`` neben dem Quelltext, und das Fenster suchte sie über
``__file__`` drei Ebenen höher. Aus dem Arbeitsverzeichnis heraus
funktionierte das; **installiert nicht**, denn ``assets/`` gehört nicht
zum Paket. Wer WOLKENErnte über pip installierte, bekam ein Fenster
ohne Symbol – und keine Fehlermeldung, weil der Pfad nur geprüft und
bei Nichtvorhandensein still übergangen wurde.

Jetzt liegen die Größen **im Paket**, unter ``daten/symbole/``.
``werkzeuge/symbole.py`` schreibt sie beim Erzeugen dorthin.
``assets/`` bleibt die Vorlage für alles, was außerhalb des Programms
gebraucht wird: Menüeintrag, Windows-Symboldatei, Fahnen im README.
"""

from __future__ import annotations

from pathlib import Path

#: Wo die mitgelieferten Größen liegen.
ORDNER = Path(__file__).resolve().parent / "daten/symbole"

#: Welche Größen mitgeliefert werden.
#:
#: Ab 48 Pixeln ist es die Vorlage selbst; darunter gibt es eigene,
#: ärmere Fassungen – dort überleben weder Perforation noch zwei
#: Berggipfel.
GROESSEN = (16, 24, 32, 48, 64, 128, 256)


def datei(groesse: int = 256) -> Path | None:
    """Das Symbol in dieser Größe, oder ``None``.

    ``None`` heißt: Das Paket wurde ohne die Symbole gebaut. Das ist
    kein Grund, das Fenster nicht zu öffnen – nur ein hässlicheres
    Fenster.
    """
    pfad = ORDNER / f"icon-{groesse}.png"
    return pfad if pfad.is_file() else None


def alle() -> list[Path]:
    """Alle vorhandenen Größen, kleinste zuerst."""
    return [p for p in (datei(g) for g in GROESSEN) if p is not None]


def qt_symbol():
    """Ein ``QIcon`` mit **allen** Größen.

    Qt sucht sich daraus die passende: die 16er für die Fensterleiste,
    die 256er für den Anwendungsumschalter. Wer nur eine Größe
    mitgibt, überlässt das Verkleinern Qt – und aus der 256er wird
    dabei ein grauer Fleck, weil in 16 Pixeln weder Perforation noch
    Berggipfel Platz haben.
    """
    from PySide6.QtGui import QIcon

    symbol = QIcon()
    for pfad in alle():
        symbol.addFile(str(pfad))
    return symbol

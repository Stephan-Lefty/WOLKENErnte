"""Die Datenbank neben dem Archiv – alles, was nicht in die Datei passt.

Ein Bild trägt sein Aufnahmedatum im Dateizeitstempel und in der
Ordnerstruktur. **Alles andere ginge verloren, sobald die Quellen
gelöscht werden**, denn es steht nur in den Metadatendateien des
Takeouts: Ortsangaben, Titel, Beschreibungen, Favoriten – und die
Albumzugehörigkeit, die sich überhaupt nur aus den Ordnernamen der
Quelle ergibt.

Besonders die Ortsangaben sind unersetzlich: **Google entfernt sie beim
Hochladen aus dem Bild.** Sie stehen ausschließlich in der JSON daneben.
Wer die Quelle löscht, ohne sie zu sichern, verliert sie endgültig.

**Verknüpft wird über Größe und Prüfsumme, nicht über den Dateinamen.**
Ein Bild kann im Archiv umbenannt worden sein, weil sein Name schon
belegt war; sein Inhalt ändert sich dadurch nicht. Damit übersteht die
Datenbank auch ein späteres Umsortieren des Archivs.

**Und sie erfasst alle Fundorte, nicht nur den übernommenen.** Ein Bild,
das im Jahresordner *und* in drei Alben lag, wurde nur einmal kopiert –
aber es gehört trotzdem zu drei Alben.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: Wo die Datenbank liegt, relativ zum Archiv.
ORT = ".wolkenernte/bestand.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bild (
    id           INTEGER PRIMARY KEY,
    groesse      INTEGER NOT NULL,
    pruefsumme   INTEGER NOT NULL,
    pfad         TEXT,
    aufgenommen  TEXT,
    breite       REAL,
    laenge       REAL,
    titel        TEXT NOT NULL DEFAULT '',
    beschreibung TEXT NOT NULL DEFAULT '',
    favorit      INTEGER NOT NULL DEFAULT 0,
    papierkorb   INTEGER NOT NULL DEFAULT 0,
    archiviert   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (groesse, pruefsumme)
);

CREATE TABLE IF NOT EXISTS album (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bild_album (
    bild_id  INTEGER NOT NULL REFERENCES bild(id) ON DELETE CASCADE,
    album_id INTEGER NOT NULL REFERENCES album(id) ON DELETE CASCADE,
    PRIMARY KEY (bild_id, album_id)
);

CREATE TABLE IF NOT EXISTS fundort (
    bild_id INTEGER NOT NULL REFERENCES bild(id) ON DELETE CASCADE,
    quelle  TEXT NOT NULL,
    pfad    TEXT NOT NULL,
    PRIMARY KEY (bild_id, quelle, pfad)
);

CREATE INDEX IF NOT EXISTS bild_zeit ON bild(aufgenommen);
CREATE INDEX IF NOT EXISTS bild_ort  ON bild(breite, laenge);
"""


@dataclass
class Zahlen:
    """Was in der Datenbank steht."""

    bilder: int = 0
    mit_datum: int = 0
    mit_ort: int = 0
    favoriten: int = 0
    alben: int = 0
    fundorte: int = 0

    def __str__(self) -> str:
        return (f"{self.bilder} Bilder, {self.mit_datum} mit Datum, "
                f"{self.mit_ort} mit Ort, {self.alben} Alben, "
                f"{self.fundorte} Fundorte")


class Bestand:
    """Die Datenbank zu einem Archiv."""

    def __init__(self, archiv: Path) -> None:
        self.archiv = archiv
        pfad = archiv / ORT
        pfad.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(pfad)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.commit()

    # -- Schreiben ---------------------------------------------------------

    def bild_merken(
        self,
        groesse: int,
        pruefsumme: int,
        *,
        pfad: str | None = None,
        aufgenommen: datetime | None = None,
        ort: tuple[float, float] | None = None,
        titel: str = "",
        beschreibung: str = "",
        favorit: bool = False,
        papierkorb: bool = False,
        archiviert: bool = False,
    ) -> int:
        """Ein Bild anlegen oder ergänzen. Gibt seine Kennung zurück.

        **Ergänzen, nicht überschreiben.** Dasselbe Bild kommt aus
        mehreren Quellen, und mal ist der Ort dabei, mal nur der Titel.
        Ein zweiter Fund darf eine vorhandene Angabe nicht durch eine
        leere ersetzen.
        """
        zeile = self.db.execute(
            "SELECT id FROM bild WHERE groesse = ? AND pruefsumme = ?",
            (groesse, pruefsumme),
        ).fetchone()

        zeit = aufgenommen.astimezone(timezone.utc).isoformat() if aufgenommen else None
        breite, laenge = ort if ort else (None, None)

        if zeile is None:
            zeiger = self.db.execute(
                "INSERT INTO bild (groesse, pruefsumme, pfad, aufgenommen, "
                "breite, laenge, titel, beschreibung, favorit, papierkorb, "
                "archiviert) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (groesse, pruefsumme, pfad, zeit, breite, laenge, titel,
                 beschreibung, int(favorit), int(papierkorb), int(archiviert)),
            )
            return int(zeiger.lastrowid or 0)

        kennung = int(zeile[0])
        self.db.execute(
            """UPDATE bild SET
                 pfad         = COALESCE(?, pfad),
                 aufgenommen  = COALESCE(aufgenommen, ?),
                 breite       = COALESCE(breite, ?),
                 laenge       = COALESCE(laenge, ?),
                 titel        = CASE WHEN titel = '' THEN ? ELSE titel END,
                 beschreibung = CASE WHEN beschreibung = '' THEN ? ELSE beschreibung END,
                 favorit      = MAX(favorit, ?),
                 papierkorb   = MAX(papierkorb, ?),
                 archiviert   = MAX(archiviert, ?)
               WHERE id = ?""",
            (pfad, zeit, breite, laenge, titel, beschreibung,
             int(favorit), int(papierkorb), int(archiviert), kennung),
        )
        return kennung

    def album_zuordnen(self, bild_id: int, name: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO album (name) VALUES (?)", (name,))
        self.db.execute(
            "INSERT OR IGNORE INTO bild_album (bild_id, album_id) "
            "SELECT ?, id FROM album WHERE name = ?",
            (bild_id, name),
        )

    def fundort_merken(self, bild_id: int, quelle: str, pfad: str) -> None:
        """Wo das Bild ursprünglich lag.

        Auch für Kopien, die nicht übernommen wurden – nur so bleibt
        nachvollziehbar, warum ein Bild zu einem Album gehört, obwohl es
        im Archiv nach Datum einsortiert ist.
        """
        self.db.execute(
            "INSERT OR IGNORE INTO fundort (bild_id, quelle, pfad) VALUES (?,?,?)",
            (bild_id, quelle, pfad),
        )

    def sichern(self) -> None:
        self.db.commit()

    # -- Lesen -------------------------------------------------------------

    def zahlen(self) -> Zahlen:
        einzeln = self.db.execute(
            "SELECT COUNT(*), COUNT(aufgenommen), COUNT(breite), SUM(favorit) "
            "FROM bild"
        ).fetchone()
        alben = self.db.execute("SELECT COUNT(*) FROM album").fetchone()[0]
        fundorte = self.db.execute("SELECT COUNT(*) FROM fundort").fetchone()[0]
        return Zahlen(
            bilder=einzeln[0], mit_datum=einzeln[1], mit_ort=einzeln[2],
            favoriten=einzeln[3] or 0, alben=alben, fundorte=fundorte,
        )

    def alben(self) -> list[tuple[str, int]]:
        """Alle Alben mit der Zahl ihrer Bilder, größte zuerst."""
        return [
            (name, anzahl)
            for name, anzahl in self.db.execute(
                "SELECT album.name, COUNT(*) FROM album "
                "JOIN bild_album ON album.id = bild_album.album_id "
                "GROUP BY album.id ORDER BY COUNT(*) DESC"
            )
        ]

    def mit_ort(self) -> Iterable[tuple[str, float, float]]:
        """Alle Bilder, von denen bekannt ist, wo sie entstanden."""
        return self.db.execute(
            "SELECT pfad, breite, laenge FROM bild WHERE breite IS NOT NULL"
        )

    def schliessen(self) -> None:
        self.db.commit()
        self.db.close()

    def __enter__(self) -> Bestand:
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()

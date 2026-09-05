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

#: Nachträglich hinzugekommene Spalten.
#:
#: SQLite kennt kein ``ADD COLUMN IF NOT EXISTS``; deshalb wird
#: nachgesehen und nur ergänzt, was fehlt. So bleibt eine Datenbank
#: benutzbar, die mit einer älteren Fassung angelegt wurde – bei einem
#: Bestand, für den 29 GB durchgerechnet wurden, wäre ein Neuanlegen
#: eine Zumutung.
NACHRUESTEN = {
    "bild": {
        # Der Wahrnehmungs-Fingerabdruck aus wolkenernte.aehnlich.
        # NULL heißt: noch nicht gerechnet. 0 heißt: gerechnet, aber
        # ohne Aussage - ein strukturloses Bild.
        "fingerabdruck": "INTEGER",
    },
}


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
        self._nachruesten()
        self.db.commit()

    def _nachruesten(self) -> None:
        """Fehlende Spalten ergänzen, ohne die Daten anzutasten."""
        for tabelle, spalten in NACHRUESTEN.items():
            vorhanden = {
                zeile[1] for zeile in
                self.db.execute(f"PRAGMA table_info({tabelle})")
            }
            for name, art in spalten.items():
                if name not in vorhanden:
                    self.db.execute(
                        f"ALTER TABLE {tabelle} ADD COLUMN {name} {art}"
                    )

    # -- Fingerabdruecke ---------------------------------------------------
    #
    # **SQLite kennt nur vorzeichenbehaftete 64-Bit-Zahlen.** Der
    # Fingerabdruck nutzt alle 64 Bit ohne Vorzeichen; jeder Wert mit
    # gesetztem oberstem Bit - also ungefähr die Hälfte - führt beim
    # Speichern zu »Python int too large to convert to SQLite INTEGER«.
    # Deshalb wird beim Schreiben in den vorzeichenbehafteten Bereich
    # umgerechnet und beim Lesen zurück. Die Bitmuster bleiben dabei
    # unverändert, und nur auf sie kommt es an.

    @staticmethod
    def _als_vorzeichen(wert: int) -> int:
        return wert - (1 << 64) if wert >= (1 << 63) else wert

    @staticmethod
    def _ohne_vorzeichen(wert: int) -> int:
        return wert + (1 << 64) if wert < 0 else wert

    def ohne_fingerabdruck(self) -> list[tuple[int, str]]:
        """Bilder, deren Fingerabdruck noch fehlt – Kennung und Pfad."""
        return [
            (int(kennung), pfad) for kennung, pfad in self.db.execute(
                "SELECT id, pfad FROM bild "
                "WHERE fingerabdruck IS NULL AND pfad IS NOT NULL"
            )
        ]

    def fingerabdruck_merken(self, bild_id: int, wert: int) -> None:
        self.db.execute("UPDATE bild SET fingerabdruck = ? WHERE id = ?",
                        (self._als_vorzeichen(wert), bild_id))

    def fingerabdruecke(self) -> list[tuple[str, int]]:
        """Alle vorhandenen Fingerabdrücke als Paare aus Pfad und Wert."""
        return [
            (pfad, self._ohne_vorzeichen(int(wert)))
            for pfad, wert in self.db.execute(
                "SELECT pfad, fingerabdruck FROM bild "
                "WHERE fingerabdruck IS NOT NULL AND pfad IS NOT NULL"
            )
        ]

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

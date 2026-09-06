"""Was im Archiv liegt – gelesen vom Dateisystem, ergänzt aus der Datenbank.

**Warum das Dateisystem die Wahrheit ist und nicht die Datenbank.** Im
Archiv liegen Bilder. Die Datenbank weiß etwas *über* sie – Orte, Alben,
Titel –, aber sie ist eine Beigabe. Wer eine Datei von Hand hineinlegt
oder herausnimmt, soll das in der Oberfläche sehen, ohne erst ein
Werkzeug laufen lassen zu müssen. Und wer die Datenbank löscht, verliert
Zusatzangaben, nicht seine Fotos.

**Dieses Modul lag zuerst unter ``web/``** – und wäre damit für eine
zweite Oberfläche nicht zu haben gewesen. Jahre zählen, Alben sammeln,
suchen, filtern: Das braucht jede Oberfläche gleichermaßen, und was
zwei Teile brauchen, gehört keinem von beiden. Hier steht deshalb
nichts, was einen Browser oder ein Fenster kennt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

#: Der Ordner für Bilder ohne bekanntes Aufnahmedatum – derselbe Name
#: wie in :mod:`wolkenernte.archiv`.
OHNE_DATUM = "ohne-datum"

BILDER = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic", ".heif"}
VIDEOS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".3gp", ".mpg", ".m2ts"}

@dataclass
class Bild:
    """Ein Eintrag im Archiv."""

    pfad: str
    """Relativ zum Archiv, mit ``/`` getrennt."""

    groesse: int
    zeit: datetime
    """Der Dateizeitstempel – beim Ernten auf das Aufnahmedatum gesetzt."""

    ist_video: bool = False

    datum_bekannt: bool = True
    """Ob das Aufnahmedatum wirklich bekannt ist.

    **Bei ``False`` ist ``zeit`` der Zeitpunkt der Übernahme**, nicht
    der Aufnahme. Solche Bilder liegen im Ordner ``ohne-datum``; ohne
    diese Unterscheidung erschienen sie in der Jahresliste unter dem
    Jahr, in dem geerntet wurde - beim ersten Ausprobieren standen 291
    Dateien unter »2026«, obwohl niemand wusste, wann sie entstanden
    sind."""

    titel: str = ""
    ort: tuple[float, float] | None = None
    favorit: bool = False
    alben: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.pfad.rsplit("/", 1)[-1]

    @property
    def endung(self) -> str:
        return "." + self.name.rsplit(".", 1)[-1].lower() if "." in self.name else ""


class Bestandsliste:
    """Der Inhalt des Archivs, einmal eingelesen."""

    def __init__(self, archiv: Path) -> None:
        self.archiv = archiv
        self.bilder: list[Bild] = []
        self._einlesen()
        self._datenbank_dazu()
        # Neueste zuerst - so sieht man beim Öffnen, was zuletzt kam.
        # Undatierte ans Ende: Ihr Zeitstempel ist der Zeitpunkt der
        # Übernahme und wäre sonst immer der jüngste von allen.
        self.bilder.sort(key=lambda b: (b.datum_bekannt, b.zeit), reverse=True)

    def _einlesen(self) -> None:
        for pfad in self.archiv.rglob("*"):
            if not pfad.is_file() or pfad.name.startswith("."):
                continue
            endung = pfad.suffix.lower()
            if endung not in BILDER and endung not in VIDEOS:
                continue
            # Alles unterhalb von .wolkenernte gehört uns, nicht dem
            # Anwender - Vorschaubilder und Datenbank bleiben draußen.
            relativ = pfad.relative_to(self.archiv)
            if relativ.parts and relativ.parts[0] == ".wolkenernte":
                continue
            try:
                angaben = pfad.stat()
            except OSError:
                continue
            pfad_text = str(relativ).replace("\\", "/")
            self.bilder.append(Bild(
                pfad=pfad_text,
                groesse=angaben.st_size,
                zeit=datetime.fromtimestamp(angaben.st_mtime),
                ist_video=endung in VIDEOS,
                datum_bekannt=not pfad_text.startswith(OHNE_DATUM + "/"),
            ))

    def _datenbank_dazu(self) -> None:
        """Orte, Titel und Alben ergänzen, falls die Datenbank da ist.

        Fehlt sie, zeigt die Oberfläche eben nur Bilder und Daten. Sie
        ist eine Beigabe, keine Voraussetzung.
        """
        from .bestand import ORT as DB_ORT

        if not (self.archiv / DB_ORT).exists():
            return

        import sqlite3

        try:
            db = sqlite3.connect(f"file:{self.archiv / DB_ORT}?mode=ro", uri=True)
        except sqlite3.Error:
            return

        try:
            nach_pfad = {b.pfad: b for b in self.bilder}
            for pfad, titel, breite, laenge, favorit in db.execute(
                "SELECT pfad, titel, breite, laenge, favorit FROM bild "
                "WHERE pfad IS NOT NULL"
            ):
                bild = nach_pfad.get(pfad)
                if bild is None:
                    continue
                bild.titel = titel or ""
                bild.favorit = bool(favorit)
                if breite is not None and laenge is not None:
                    bild.ort = (breite, laenge)

            for pfad, name in db.execute(
                "SELECT bild.pfad, album.name FROM bild "
                "JOIN bild_album ON bild.id = bild_album.bild_id "
                "JOIN album ON album.id = bild_album.album_id "
                "WHERE bild.pfad IS NOT NULL"
            ):
                bild = nach_pfad.get(pfad)
                if bild is not None:
                    bild.alben.append(name)
        except sqlite3.Error:
            pass
        finally:
            db.close()

    # -- Auswerten ---------------------------------------------------------

    def jahre(self) -> list[tuple[int, int]]:
        """Alle Jahre mit der Zahl ihrer Bilder, neueste zuerst.

        Bilder ohne bekanntes Datum bleiben draußen – sie gehören in
        kein Jahr. Ihre Zahl steht in :attr:`ohne_datum`.
        """
        zaehler: dict[int, int] = {}
        for bild in self.bilder:
            if not bild.datum_bekannt:
                continue
            zaehler[bild.zeit.year] = zaehler.get(bild.zeit.year, 0) + 1
        return sorted(zaehler.items(), reverse=True)

    @property
    def ohne_datum(self) -> list[Bild]:
        return [b for b in self.bilder if not b.datum_bekannt]

    def alben(self) -> list[tuple[str, int]]:
        zaehler: dict[str, int] = {}
        for bild in self.bilder:
            for name in bild.alben:
                zaehler[name] = zaehler.get(name, 0) + 1
        return sorted(zaehler.items(), key=lambda p: -p[1])

    def auswahl(
        self,
        *,
        jahr: int | None = None,
        album: str | None = None,
        nur_mit_ort: bool = False,
        nur_favoriten: bool = False,
        nur_videos: bool = False,
        nur_ohne_datum: bool = False,
    ) -> list[Bild]:
        treffer = self.bilder
        if jahr is not None:
            treffer = [b for b in treffer
                       if b.datum_bekannt and b.zeit.year == jahr]
        if album is not None:
            treffer = [b for b in treffer if album in b.alben]
        if nur_mit_ort:
            treffer = [b for b in treffer if b.ort]
        if nur_favoriten:
            treffer = [b for b in treffer if b.favorit]
        if nur_videos:
            treffer = [b for b in treffer if b.ist_video]
        if nur_ohne_datum:
            treffer = [b for b in treffer if not b.datum_bekannt]
        return treffer

    def suchen(self, text: str) -> list[Bild]:
        """Bilder nach Dateiname, Titel, Album oder Ordner suchen.

        Ohne Groß- und Kleinschreibung und ohne Volltextindex: Bei
        fünfzehntausend Einträgen ist ein Durchlauf durch die Liste
        schneller, als ein Index kosten würde – und er bleibt immer
        aktuell.

        Mehrere Wörter müssen **alle** vorkommen, aber nicht
        nebeneinander: »berlin 2023« findet Berliner Bilder aus 2023.
        """
        woerter = [w.lower() for w in text.split() if w]
        if not woerter:
            return []

        treffer = []
        for bild in self.bilder:
            heuhaufen = " ".join((
                bild.pfad, bild.titel, " ".join(bild.alben),
                bild.zeit.strftime("%d.%m.%Y %B %Y"),
            )).lower()
            if all(wort in heuhaufen for wort in woerter):
                treffer.append(bild)
        return treffer

    def bei(self, pfad: str) -> Bild | None:
        for bild in self.bilder:
            if bild.pfad == pfad:
                return bild
        return None

    @property
    def gesamtgroesse(self) -> int:
        return sum(b.groesse for b in self.bilder)

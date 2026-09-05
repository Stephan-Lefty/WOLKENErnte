"""Google-Takeout-Archive lesen – ohne sie auszupacken.

**Warum nicht entpacken.** Ein Takeout kann hunderte Gigabyte umfassen.
Es auszupacken hieße, denselben Bestand zweimal auf der Platte zu haben,
und zwar genau dann, wenn jemand aufräumen will, weil der Platz knapp
ist. Ein ZIP führt sein Inhaltsverzeichnis am Ende mit; damit kommt man
an jede einzelne Datei heran, ohne das Ganze anzufassen. ``zipfile``
aus der Standardbibliothek kann das, es kommt also kein Fremdpaket dazu.

Nebenbei erspart das unter Windows die Pfadlängengrenze, an der das
Auspacken tiefer Takeout-Ordner gern scheitert.

**Warum alle Teilarchive zusammen gelesen werden.** Google zerlegt den
Export in ``takeout-...-001.zip``, ``-002.zip`` und so fort, und diese
Aufteilung folgt keiner inhaltlichen Ordnung: **Ein Bild kann im einen
Archiv liegen und seine Metadaten im nächsten.** Wer jedes ZIP für sich
betrachtet, verliert Aufnahmedatum und Ortsangabe für alle Bilder an
den Nahtstellen – und merkt es nicht, weil die Bilder ja da sind. Diese
Klasse legt deshalb einen gemeinsamen Namensraum über alle Teile.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


class TakeoutFehler(Exception):
    """Das Archiv ließ sich nicht öffnen oder ergibt keinen Sinn."""


@dataclass(frozen=True)
class Eintrag:
    """Eine Datei irgendwo in den Teilarchiven."""

    pfad: str
    """Der Pfad innerhalb des Archivs, mit ``/`` getrennt."""

    quelle: Path
    """Welches Teilarchiv sie enthält. Für Fehlermeldungen – ohne diese
    Angabe sucht man bei zwanzig ZIP-Dateien lange."""

    groesse: int
    """Die entpackte Größe in Bytes."""

    pruefsumme: int = 0
    """Die CRC-32, die im ZIP ohnehin mitgeführt wird.

    **Damit lassen sich Doppelgänger finden, ohne auch nur ein Byte zu
    entpacken.** Bei einem Takeout ist das der Unterschied zwischen
    Sekunden und einer Viertelstunde: Google legt jedes Bild, das in
    einem Album steckt, ein zweites Mal ab.

    Als alleiniger Beweis taugt sie nicht – eine CRC-32 ist zum Erkennen
    von Übertragungsfehlern gedacht, nicht gegen absichtliche
    Kollisionen. Zusammen mit der Größe ist sie aber ein sehr guter
    Vorfilter; nachrechnen muss man dann nur noch die wenigen
    Verdächtigen."""

    @property
    def name(self) -> str:
        """Der reine Dateiname ohne Verzeichnisse."""
        return self.pfad.rsplit("/", 1)[-1]

    @property
    def ordner(self) -> str:
        """Der Ordner, in dem die Datei liegt. Leer, wenn ganz oben."""
        return self.pfad.rsplit("/", 1)[0] if "/" in self.pfad else ""


class Archiv:
    """Mehrere Takeout-ZIP-Dateien als ein Bestand.

    Wird als Kontextverwalter benutzt, damit die offenen Dateien
    zuverlässig wieder geschlossen werden::

        with Archiv.aus_ordner(Path("~/Downloads").expanduser()) as archiv:
            for eintrag in archiv:
                ...
    """

    def __init__(self, teile: list[Path]) -> None:
        if not teile:
            raise TakeoutFehler("Keine ZIP-Dateien angegeben.")

        self._zips: dict[Path, zipfile.ZipFile] = {}
        self._index: dict[str, Eintrag] = {}
        #: Pfade, die in mehr als einem Teilarchiv vorkommen. Nicht
        #: stillschweigend übergehen: Das passiert, wenn jemand zwei
        #: Exporte durcheinanderwirft, und dann stimmen die Zählungen
        #: hinten und vorne nicht.
        self.doppelte: list[str] = []

        for teil in teile:
            try:
                datei = zipfile.ZipFile(teil)
            except (OSError, zipfile.BadZipFile) as fehler:
                self.schliessen()
                raise TakeoutFehler(f"{teil.name} ließ sich nicht öffnen: {fehler}")
            self._zips[teil] = datei

            for info in datei.infolist():
                if info.is_dir():
                    continue
                if info.filename in self._index:
                    self.doppelte.append(info.filename)
                    continue
                self._index[info.filename] = Eintrag(
                    pfad=info.filename, quelle=teil, groesse=info.file_size,
                    pruefsumme=info.CRC,
                )

    # -- Aufbau ------------------------------------------------------------

    @classmethod
    def aus_ordner(cls, ordner: Path) -> Archiv:
        """Alle Takeout-ZIP-Dateien eines Ordners zusammenfassen.

        Sortiert wird nach Namen, damit ``-002`` vor ``-010`` kommt –
        eine reine Textsortierung führte sonst zu einer Reihenfolge, die
        beim Suchen von Fehlern verwirrt. Für das Ergebnis ist die
        Reihenfolge gleichgültig, für die Lesbarkeit von Meldungen nicht.
        """
        if not ordner.is_dir():
            raise TakeoutFehler(f"{ordner} ist kein Ordner.")
        teile = sorted(
            (p for p in ordner.iterdir() if p.suffix.lower() == ".zip"),
            key=lambda p: p.name,
        )
        if not teile:
            raise TakeoutFehler(f"In {ordner} liegt keine ZIP-Datei.")
        return cls(teile)

    # -- Lesen -------------------------------------------------------------

    def __iter__(self) -> Iterator[Eintrag]:
        return iter(self._index.values())

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, pfad: str) -> bool:
        return pfad in self._index

    def eintrag(self, pfad: str) -> Eintrag | None:
        return self._index.get(pfad)

    def lesen(self, pfad: str) -> bytes:
        """Den Inhalt einer Datei holen – gleich, in welchem Teil sie liegt."""
        eintrag = self._index.get(pfad)
        if eintrag is None:
            raise TakeoutFehler(f"{pfad} kommt in diesem Archiv nicht vor.")
        return self._zips[eintrag.quelle].read(pfad)

    def teile(self) -> list[Path]:
        """Die eingelesenen Teilarchive, in der Reihenfolge des Aufbaus."""
        return list(self._zips)

    # -- Aufräumen ---------------------------------------------------------

    def schliessen(self) -> None:
        for datei in self._zips.values():
            datei.close()
        self._zips.clear()

    def __enter__(self) -> Archiv:
        return self

    def __exit__(
        self,
        art: type[BaseException] | None,
        wert: BaseException | None,
        spur: TracebackType | None,
    ) -> None:
        self.schliessen()

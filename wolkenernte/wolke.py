"""Ein Wolkenspeicher als Quelle – Bilder von dort ins Archiv holen.

Verhält sich wie :class:`wolkenernte.lokal.Ordner` und
:class:`wolkenernte.takeout.Archiv`: auflisten, lesen, Prüfsummen. Damit
gilt für eine Wolke derselbe Ablauf wie für einen Ordner auf der Platte
– ernten, erfassen, pruefen –, und ``archiv.uebernehmen()`` muss nicht
wissen, woher die Bilder kommen.

**Prüfsummen kommen von rclone, wenn der Anbieter welche führt.**
Nextcloud liefert über WebDAV keine; dann bleibt das Feld auf 0, und die
Prüfung findet beim Schreiben statt – dort, wo die Daten ohnehin durch
die Hand gehen. Bei Anbietern, die Hashes kennen, wird schon vor dem
Herunterladen verglichen und mancher Griff gespart.

**Löschen geht nur über einen einzigen Weg.** :meth:`Wolke.loeschen`
gibt es, aber sie ist absichtlich schmucklos: Sie prüft nichts, sie
entscheidet nichts, sie führt aus. Wer sie ruft, hat vorher
:func:`wolkenernte.aufraeumen.erlaubnis_pruefen` gefragt und
nachgewiesen, dass der Inhalt im Archiv liegt. Diese Klasse weiß über
den Anbieter dahinter nichts und kann darum auch nicht beurteilen, ob
gelöscht werden darf.
"""

from __future__ import annotations

import tempfile
import zlib
from collections.abc import Callable, Iterator
from pathlib import Path

from .lokal import MEDIEN
from .rclone import Dienst, RcloneFehler
from .takeout import Eintrag, TakeoutFehler


class Wolke:
    """Der Inhalt eines Zugangs, einmal aufgelistet.

    ``zugang`` ist der Name aus der rclone-Konfiguration, ``unterordner``
    ein Pfad darin – etwa ``Fotos/2024``. Leer heißt: alles.
    """

    def __init__(self, dienst: Dienst, zugang: str,
                 unterordner: str = "") -> None:
        self.dienst = dienst
        self.zugang = zugang.rstrip(":")
        self.unterordner = unterordner.rstrip("/")
        self._index: dict[str, Eintrag] = {}
        self._geholt: dict[str, Path] = {}
        self._ablage = Path(tempfile.mkdtemp(prefix="wolkenernte-"))

        self._auflisten()

    @property
    def wurzel(self) -> str:
        """Der Pfad in rclones Schreibweise.

        **Ein führender Schrägstrich bleibt stehen.** Bei einem
        Wolkenzugang ist der Unterordner relativ, dort stört er nicht –
        aber beim ``local``-Backend, mit dem sich alles ohne
        Zugangsdaten erproben lässt, ist der Pfad absolut. Wer ihn
        wegschneidet, sucht ``tmp/...`` statt ``/tmp/...``, und rclone
        antwortet mit »directory not found«.
        """
        return (f"{self.zugang}:{self.unterordner}" if self.unterordner
                else f"{self.zugang}:")

    def _auflisten(self) -> None:
        """Den ganzen Bestand holen – einmal, rekursiv.

        Ein Aufruf je Unterordner wäre bei einer gewachsenen
        Fotosammlung ein Aufruf je Monat und Album; über eine Leitung
        ist das der Unterschied zwischen Sekunden und Minuten.
        """
        try:
            eintraege = self.dienst.rufen("operations/list", {
                "fs": self.wurzel, "remote": "",
                "opt": {"filesOnly": True, "recurse": True,
                        # Hashes mitliefern, wo der Anbieter welche hat.
                        "hashTypes": ["crc32"]},
            }).get("list") or []
        except RcloneFehler as fehler:
            raise TakeoutFehler(f"{self.wurzel} ließ sich nicht lesen: {fehler}")

        for eintrag in eintraege:
            pfad = eintrag.get("Path") or ""
            if not pfad:
                continue
            hashes = eintrag.get("Hashes") or {}
            self._index[pfad] = Eintrag(
                pfad=pfad,
                # Für eine Wolke gibt es keine Datei auf der Platte;
                # hier steht der Pfad, unter dem rclone sie kennt.
                quelle=Path(f"{self.wurzel.rstrip('/')}/{pfad}"),
                groesse=int(eintrag.get("Size") or 0),
                pruefsumme=_als_zahl(hashes.get("crc32")),
            )

    # -- Lesen, wie bei den anderen Quellen --------------------------------

    def __iter__(self) -> Iterator[Eintrag]:
        return iter(self._index.values())

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, pfad: str) -> bool:
        return pfad in self._index

    def eintrag(self, pfad: str) -> Eintrag | None:
        return self._index.get(pfad)

    def medien(self) -> list[str]:
        """Nur die Bilder und Videos, ohne Metadaten und Beiwerk."""
        return [p for p in self._index
                if "." + p.rsplit(".", 1)[-1].lower() in MEDIEN]

    def lesen(self, pfad: str) -> bytes:
        """Eine Datei herunterladen und ihren Inhalt zurückgeben.

        **Der Umweg über die Platte ist Absicht.** rclone kann über die
        Schnittstelle nur von einem Ort zum anderen kopieren, nicht in
        den Arbeitsspeicher liefern. Und für große Videos ist das auch
        besser so: Ein Zwei-Gigabyte-Film gehört nicht am Stück in den
        Speicher.

        Wer das Bild ohnehin nur weiterschreiben will, nimmt
        :meth:`holen` – das spart den Umweg ganz.
        """
        return self.holen(pfad).read_bytes()

    def holen(self, pfad: str, ziel: Path | None = None) -> Path:
        """Eine Datei herunterladen. Gibt den Pfad auf der Platte zurück.

        Ohne ``ziel`` landet sie in einem Ablageordner, der beim
        Schließen wieder verschwindet. Was schon geholt wurde, wird
        nicht zweimal geholt.
        """
        eintrag = self._index.get(pfad)
        if eintrag is None:
            raise TakeoutFehler(f"{pfad} liegt nicht in {self.wurzel}.")

        if ziel is None:
            vorhanden = self._geholt.get(pfad)
            if vorhanden is not None and vorhanden.exists():
                return vorhanden
            ziel = self._ablage / pfad.replace("/", "_")

        ziel.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.dienst.rufen("operations/copyfile", {
                "srcFs": self.wurzel, "srcRemote": pfad,
                "dstFs": str(ziel.parent), "dstRemote": ziel.name,
            })
        except RcloneFehler as fehler:
            raise TakeoutFehler(f"{pfad} ließ sich nicht holen: {fehler}")

        if not ziel.is_file():
            raise TakeoutFehler(f"{pfad} kam nicht an.")

        if ziel.parent == self._ablage:
            self._geholt[pfad] = ziel
        return ziel

    def loeschen(self, pfad: str) -> None:
        """Eine Datei in der Wolke löschen. Endgültig.

        **Diese Methode prüft nichts.** Kein Anbieter, kein Nachweis,
        keine Rückfrage – das steht alles in
        :mod:`wolkenernte.aufraeumen`, und dort gehört es hin. Hier
        wäre eine halbe Prüfung schlimmer als keine: Sie sähe nach
        Sicherheit aus und wäre keine.

        Der Eintrag verschwindet auch aus dem Verzeichnis dieser
        Wolke. Sonst zeigte ein zweiter Durchgang eine Datei, die es
        nicht mehr gibt.
        """
        eintrag = self._index.get(pfad)
        if eintrag is None:
            raise TakeoutFehler(f"{pfad} liegt nicht in {self.wurzel}.")
        try:
            self.dienst.rufen("operations/deletefile", {
                "fs": self.wurzel, "remote": pfad,
            })
        except RcloneFehler as fehler:
            raise TakeoutFehler(
                f"{pfad} ließ sich nicht löschen: {fehler}") from fehler
        del self._index[pfad]
        weg = self._geholt.pop(pfad, None)
        if weg is not None:
            weg.unlink(missing_ok=True)

    # -- Prüfsummen --------------------------------------------------------

    def pruefsummen_rechnen(
        self,
        *,
        nur_medien: bool = True,
        zusatzgroessen: set[int] | None = None,
        fortschritt: Callable[[int, int], None] | None = None,
    ) -> int:
        """Fehlende Prüfsummen nachrechnen – durch Herunterladen.

        **Das ist teuer.** Bei einem Anbieter ohne Hashes bedeutet es,
        den ganzen Bestand über die Leitung zu holen. Gerechnet wird
        deshalb nur, wo es etwas nützt: bei mehrfach vorkommenden Größen
        und bei Größen, die auch in einer zweiten Quelle stehen.

        Für das Übernehmen ist das ohnehin nicht nötig – dort geht jede
        Datei durch die Hand, und die Summe fällt nebenbei ab.
        """
        kandidaten = [self._index[p] for p in
                      (self.medien() if nur_medien else list(self._index))]
        kandidaten = [e for e in kandidaten if not e.pruefsumme]

        haeufigkeit: dict[int, int] = {}
        for eintrag in kandidaten:
            haeufigkeit[eintrag.groesse] = haeufigkeit.get(eintrag.groesse, 0) + 1

        zusatz = zusatzgroessen or set()
        zu_rechnen = [e for e in kandidaten
                      if haeufigkeit[e.groesse] > 1 or e.groesse in zusatz]

        for nummer, eintrag in enumerate(zu_rechnen, 1):
            if fortschritt:
                fortschritt(nummer, len(zu_rechnen))
            try:
                datei = self.holen(eintrag.pfad)
                summe = 0
                with datei.open("rb") as offen:
                    while brocken := offen.read(1 << 20):
                        summe = zlib.crc32(brocken, summe)
            except (TakeoutFehler, OSError):
                continue
            self._index[eintrag.pfad] = Eintrag(
                pfad=eintrag.pfad, quelle=eintrag.quelle,
                groesse=eintrag.groesse, pruefsumme=summe,
            )
        return len(zu_rechnen)

    # -- Aufräumen ---------------------------------------------------------

    def schliessen(self) -> None:
        """Die heruntergeladenen Dateien wegräumen.

        Nicht den Dienst beenden – der gehört dem Aufrufer, und er
        bedient womöglich noch andere Zugänge.
        """
        import shutil

        shutil.rmtree(self._ablage, ignore_errors=True)
        self._geholt.clear()

    def __enter__(self) -> Wolke:
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()


def _als_zahl(wert: object) -> int:
    """Einen Hash aus rclones Antwort in eine Zahl wandeln.

    rclone liefert CRC-32 als Hexadezimaltext. Fehlt er – Nextcloud
    führt über WebDAV keine Hashes –, bleibt es bei 0: **unbekannt**,
    nicht »null«.
    """
    if not isinstance(wert, str) or not wert:
        return 0
    try:
        return int(wert, 16)
    except ValueError:
        return 0

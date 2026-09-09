"""Der Webdienst, über den man sein Archiv durchsieht.

    wolkenernte oberflaeche <Archiv>

**Warum eine Weboberfläche und keine Fensteranwendung.** Der Browser
kann Bilder und Videos bereits anzeigen, in jedem Format, das das System
beherrscht – dafür muss nichts nachinstalliert werden. Eine
Qt-Oberfläche wären über hundert Megabyte zusätzlich und auf jeder
Plattform eigene Schwierigkeiten mit der Videowiedergabe. Dieses
Programm bringt stattdessen nur HTML mit und überlässt das Anzeigen dem,
der es ohnehin kann.

**Der Dienst hört ausschließlich auf 127.0.0.1.** Er zeigt private Fotos
und hat keine Anmeldung; er darf das Gerät nicht verlassen. Die
Portnummer vergibt das Betriebssystem, damit zwei Aufrufe sich nicht in
die Quere kommen.
"""

from __future__ import annotations

import http.server
import socket
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from . import seiten, vorschau
from ..bestandsliste import Bestandsliste, zeitraum_lesen

JE_SEITE = 120

TYPEN = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".avif": "image/avif",
    ".heic": "image/heic", ".heif": "image/heif",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
    ".m4v": "video/x-m4v", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
}


class Dienst(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, adresse, behandler, archiv: Path) -> None:
        super().__init__(adresse, behandler)
        self.archiv = archiv
        self.liste = Bestandsliste(archiv)
        self.sperre = threading.Lock()

    def neu_einlesen(self) -> None:
        with self.sperre:
            self.liste = Bestandsliste(self.archiv)


class Behandler(http.server.BaseHTTPRequestHandler):
    server_version = "WOLKENErnte"

    # Ruhe im Protokoll: Bei einem Raster mit 120 Kacheln kämen sonst
    # 120 Zeilen je Seitenaufruf.
    def log_message(self, *_: object) -> None:
        pass

    # -- Antworten ---------------------------------------------------------

    def _senden(self, daten: bytes, typ: str, *, code: int = 200,
                zwischenspeichern: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        if zwischenspeichern:
            self.send_header("Cache-Control", "private, max-age=86400")
        # Der Dienst zeigt private Bilder. Kein fremder Rahmen, kein
        # Weiterreichen der Adresse.
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(daten)
        except (BrokenPipeError, ConnectionResetError):
            # Der Browser hat die Verbindung fallen gelassen - beim
            # schnellen Blättern durch ein Raster ist das der Normalfall.
            pass

    def _seite(self, html: str, code: int = 200) -> None:
        self._senden(html.encode("utf-8"), "text/html; charset=utf-8", code=code)

    def _fehler(self, text: str, code: int = 404) -> None:
        self._seite(f"<!doctype html><meta charset=utf-8>"
                    f"<body style='font:16px sans-serif;padding:2rem'>"
                    f"<p>{text}</p><p><a href='/'>Zur Übersicht</a></p>", code)

    # -- Wegweiser ---------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        zerlegt = urlparse(self.path)
        werte = parse_qs(zerlegt.query)
        liste: Bestandsliste = self.server.liste  # type: ignore[attr-defined]

        def eins(name: str) -> str | None:
            wert = werte.get(name, [None])[0]
            return wert or None

        if zerlegt.path == "/":
            self._seite(seiten.uebersicht(liste))
        elif zerlegt.path == "/raster":
            self._raster(liste, werte, eins)
        elif zerlegt.path == "/suche":
            wort = eins("q") or ""
            self._seite(seiten.suche(liste, wort, liste.suchen(wort)))
        elif zerlegt.path == "/doppelt":
            nummer = eins("seite")
            self._doppelt(liste, int(nummer) if (nummer or "").isdigit() else 1)
        elif zerlegt.path == "/bild":
            self._einzeln(liste, eins("p"))
        elif zerlegt.path == "/vorschau":
            self._vorschau(liste, eins("p"))
        elif zerlegt.path == "/datei":
            self._datei(liste, eins("p"))
        elif zerlegt.path == "/neu":
            self.server.neu_einlesen()  # type: ignore[attr-defined]
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self._fehler("Diese Seite gibt es nicht.")

    def _doppelt(self, liste, seite: int = 1) -> None:
        """Gruppen ähnlicher Bilder.

        Gerechnet wird hier **nicht** – das dauert Minuten und darf
        keine Seite blockieren. Fehlen die Fingerabdrücke noch, sagt die
        Seite das und verweist auf den Befehl.
        """
        from ..bestand import ORT as DB_ORT
        from ..doppelgaenger import einstufen, finden

        if not (liste.archiv / DB_ORT).exists():
            self._seite(seiten.doppelt(liste, [], fertig=False))
            return

        from ..bestand import Bestand
        with Bestand(liste.archiv) as bestand:
            offen = len(bestand.ohne_fingerabdruck())
        if offen:
            self._seite(seiten.doppelt(liste, [], fertig=False))
            return

        gruppen = []
        for pfade in finden(liste.archiv):
            bilder = [b for b in (liste.bei(p) for p in pfade) if b]
            if len(bilder) > 1:
                gruppen.append((bilder, einstufen(pfade)))
        self._seite(seiten.doppelt(liste, gruppen, fertig=True, seite=seite))

    def _raster(self, liste, werte, eins) -> None:
        jahr = None
        if eins("jahr") and eins("jahr").isdigit():
            jahr = int(eins("jahr"))
        album = eins("album")
        schlagwort = eins("schlagwort")
        seite = int(eins("seite")) if (eins("seite") or "").isdigit() else 1

        # Ein unlesbares Datum wird **gesagt**, nicht übergangen. Sonst
        # zeigte die Seite den ganzen Bestand, und der Anwender hielte
        # das für das Ergebnis seines Zeitraums.
        von_text, bis_text = eins("von") or "", eins("bis") or ""
        zeitfehler = None
        try:
            von = zeitraum_lesen(von_text)
            bis = zeitraum_lesen(bis_text, ende=True)
        except ValueError as schief:
            zeitfehler = str(schief)
            von = bis = None

        bilder = liste.auswahl(
            jahr=jahr, album=album, schlagwort=schlagwort, von=von, bis=bis,
            nur_mit_ort=bool(eins("ort")),
            nur_favoriten=bool(eins("favoriten")),
            nur_videos=bool(eins("videos")),
            nur_ohne_datum=bool(eins("ohnedatum")),
        )
        zusatz = "".join(f"{n}=1&" for n in
                         ("ort", "favoriten", "videos", "ohnedatum") if eins(n))
        # Beim Blättern muss der Zeitraum mit - sonst steht man auf
        # Seite 2 wieder im ganzen Bestand.
        zusatz += "".join(f"{n}={quote(w)}&" for n, w in
                          (("von", von_text), ("bis", bis_text)) if w)
        self._seite(seiten.raster(liste, bilder, seite=seite, je_seite=JE_SEITE,
                                  jahr=jahr, album=album, zusatz=zusatz,
                                  schlagwort=schlagwort,
                                  von=von_text, bis=bis_text,
                                  zeitfehler=zeitfehler))

    def _einzeln(self, liste, pfad) -> None:
        bild = liste.bei(pfad) if pfad else None
        if bild is None:
            self._fehler("Dieses Bild gibt es nicht.")
            return
        self._seite(seiten.einzeln(liste, bild))

    def _vorschau(self, liste, pfad) -> None:
        bild = liste.bei(pfad) if pfad else None
        if bild is None:
            self._fehler("Unbekannt.")
            return
        daten = vorschau.hole(liste.archiv, bild.pfad)
        if daten:
            self._senden(daten, "image/jpeg", zwischenspeichern=True)
            return
        # Kein Vorschaubild - etwa bei Videos oder ohne Pillow. Ein
        # schlichtes Ersatzbild statt eines kaputten Symbols.
        self._senden(_ersatzbild(bild.ist_video), "image/svg+xml",
                     zwischenspeichern=True)

    def _datei(self, liste, pfad) -> None:
        """Die Originaldatei ausliefern.

        **Der Pfad wird nicht geprüft, sondern nachgeschlagen.** Nur was
        in der eingelesenen Liste steht, wird ausgeliefert; eine Angabe
        wie ``../../etc/passwd`` findet sich dort nicht und läuft ins
        Leere. Das ist sicherer als jede Prüfung auf verdächtige
        Zeichen, die man vergessen kann.
        """
        bild = liste.bei(pfad) if pfad else None
        if bild is None:
            self._fehler("Diese Datei gibt es nicht.")
            return
        datei = liste.archiv / bild.pfad
        try:
            daten = datei.read_bytes()
        except OSError:
            self._fehler("Die Datei ließ sich nicht lesen.", 500)
            return
        self._senden(daten, TYPEN.get(bild.endung, "application/octet-stream"),
                     zwischenspeichern=True)


def _ersatzbild(ist_video: bool) -> bytes:
    zeichen = "▶" if ist_video else "?"
    from .. import farben
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            f'<rect width="100" height="100" fill="{farben.GRAU_KOHLE}"/>'
            f'<text x="50" y="58" font-size="28" text-anchor="middle"'
            f' fill="{farben.GRAU_MITTE}">{zeichen}</text></svg>').encode()


def starten(archiv: Path, *, port: int = 0, browser: bool = True) -> int:
    """Den Dienst starten und laufen lassen, bis Strg-C kommt."""
    if not archiv.is_dir():
        print(f"Kein Archiv: {archiv}")
        return 1

    dienst = Dienst(("127.0.0.1", port), Behandler, archiv)
    _, echter_port = dienst.socket.getsockname()[:2]
    adresse = f"http://127.0.0.1:{echter_port}/"

    anzahl = len(dienst.liste.bilder)
    if anzahl == 0:
        print(f"In {archiv} liegen keine Bilder.")
        print("Erst »wolkenernte ernten« laufen lassen.")
        return 1

    print(f"WOLKENErnte zeigt {anzahl} Dateien aus {archiv}")
    print(f"  {adresse}")
    if not vorschau.verfuegbar():
        print("  Hinweis: Ohne Pillow gibt es keine Vorschaubilder.")
        print("           Unter Manjaro: pacman -S python-pillow")
    print("  Beenden mit Strg-C")

    if browser:
        threading.Timer(0.4, lambda: webbrowser.open(adresse)).start()

    try:
        dienst.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        dienst.shutdown()
        dienst.server_close()
    return 0


def freier_port() -> int:
    """Einen freien Port erfragen – nur für Tests."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])

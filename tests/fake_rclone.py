"""Ein nachgebautes ``rclone rcd`` für die Tests.

**Warum nachgebaut und nicht das echte.** Die Tests sollen überall
laufen – in der CI, auf einem Rechner ohne rclone, in jeder Fassung.
Und sie sollen Dinge prüfen, die sich mit dem echten Programm nur
umständlich herstellen lassen: eine falsche Fassungsnummer, ein Dienst,
der gar nicht erst hochkommt, ein Aufruf ohne Anmeldung.

Dasselbe Muster wie ``tests/fake_imap.py`` bei MailBurg. Der Nachbau
verhält sich in den geprüften Punkten wie das Original – vor allem
weist er unangemeldete Aufrufe mit 401 ab.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

#: Was der Nachbau als Fassung meldet. Über die Umgebungsvariable
#: ``FAKE_RCLONE_VERSION`` änderbar – so lässt sich prüfen, dass eine zu
#: alte Fassung abgewiesen wird.
FASSUNG = os.environ.get("FAKE_RCLONE_VERSION", "1.75.0")

REMOTES = ["probe:", "zweite:"]


class Behandler(BaseHTTPRequestHandler):
    def log_message(self, *_: object) -> None:
        pass

    def do_POST(self) -> None:  # noqa: N802
        benutzer = os.environ.get("RCLONE_RC_USER", "")
        kennwort = os.environ.get("RCLONE_RC_PASS", "")
        if benutzer or kennwort:
            import base64
            erwartet = "Basic " + base64.b64encode(
                f"{benutzer}:{kennwort}".encode()
            ).decode()
            if self.headers.get("Authorization") != erwartet:
                # Genau wie das Original: ohne Anmeldung geht nichts.
                self._antworten({"error": "Unauthorized"}, code=401)
                return

        laenge = int(self.headers.get("Content-Length") or 0)
        try:
            werte = json.loads(self.rfile.read(laenge) or b"{}")
        except json.JSONDecodeError:
            werte = {}

        weg = self.path.lstrip("/")
        if weg == "rc/noop":
            self._antworten(werte)
        elif weg == "config/listremotes":
            self._antworten({"remotes": REMOTES})
        elif weg == "operations/list":
            self._antworten({"list": [
                {"Path": "IMG_1.jpg", "Name": "IMG_1.jpg", "Size": 1234,
                 "IsDir": False},
                {"Path": "IMG_2.jpg", "Name": "IMG_2.jpg", "Size": 5678,
                 "IsDir": False},
            ]})
        elif weg == "operations/deletefile":
            GELOESCHT.append(f"{werte.get('fs')}{werte.get('remote')}")
            self._antworten({})
        elif weg == "core/stats":
            self._antworten({"bytes": 0, "transfers": 0, "errors": 0})
        else:
            self._antworten({"error": f"couldn't find method {weg}"}, code=404)

    def _antworten(self, werte: dict, code: int = 200) -> None:
        roh = json.dumps(werte).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)


GELOESCHT: list[str] = []


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "version":
        print(f"rclone v{FASSUNG}")
        return 0

    if os.environ.get("FAKE_RCLONE_STIRBT"):
        # Für den Test, dass ein sofortiges Ende erkannt wird.
        print("Fatal error: konnte nicht starten", file=sys.stdout, flush=True)
        return 1

    adresse = "127.0.0.1"
    port = 5572
    for i, teil in enumerate(sys.argv):
        if teil == "--rc-addr" and i + 1 < len(sys.argv):
            adresse, _, hafen = sys.argv[i + 1].rpartition(":")
            port = int(hafen)

    HTTPServer((adresse, port), Behandler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())

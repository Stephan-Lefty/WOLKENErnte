#!/usr/bin/env python3
"""Das AUR-Paket auf die neueste Fassung heben.

    python3 verpacken/aur/nachziehen.py           # Fassung aus dem Quelltext
    python3 verpacken/aur/nachziehen.py 0.5.0     # oder ausdrücklich

**Warum ein Skript und nicht drei Handgriffe.** Beim Nachziehen von
Hand vergisst man genau eine Sache: die Prüfsumme. Das Paket baut dann
trotzdem – aus dem alten, zwischengespeicherten Archiv – und niemand
merkt es, bis ein fremder Rechner es zum ersten Mal wirklich lädt. Hier
wird das Archiv **geholt** und die Summe daraus **gerechnet**; eine
falsche kann gar nicht entstehen.

Und ``.SRCINFO`` wird gleich mit erzeugt. Das AUR liest ausschließlich
diese Datei; ein PKGBUILD mit neuer Fassung und eine alte ``.SRCINFO``
daneben ergeben ein Paket, das im AUR weiterhin die alte Fassung
anbietet – wieder ohne dass irgendwo etwas fehlschlägt.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent

VORLAGE = ("https://github.com/Stephan-Lefty/WOLKENErnte/archive/"
           "refs/tags/v{fassung}.tar.gz")


def fassung_aus_dem_quelltext() -> str:
    """Die Fassung steht ausschließlich in ``wolkenernte/__init__.py``."""
    text = (WURZEL / "wolkenernte" / "__init__.py").read_text("utf-8")
    treffer = re.search(r'^__version__ = "([^"]+)"', text, re.M)
    if not treffer:
        raise SystemExit("In wolkenernte/__init__.py steht keine Fassung.")
    return treffer.group(1)


def pruefsumme(fassung: str) -> str:
    """Das Quellarchiv holen und rechnen.

    Es wird **nicht aufbewahrt**: Ein Archiv von fünf Megabyte im
    Repository liegen zu lassen, nur um eine Prüfsumme zu bilden, wäre
    Verschwendung – und beim nächsten Mal läge das falsche da.
    """
    adresse = VORLAGE.format(fassung=fassung)
    print(f"Hole {adresse}")
    try:
        with urllib.request.urlopen(adresse, timeout=60) as antwort:
            roh = antwort.read()
    except urllib.error.HTTPError as fehler:
        if fehler.code == 404:
            raise SystemExit(
                f"Für v{fassung} gibt es keine Veröffentlichung. Erst die "
                f"Marke setzen und den Release anlegen, dann nachziehen."
            ) from fehler
        raise SystemExit(f"GitHub antwortet mit {fehler.code}.") from fehler
    except urllib.error.URLError as fehler:
        raise SystemExit(f"Keine Verbindung: {fehler.reason}") from fehler

    print(f"  {len(roh) / 1e6:.1f} MB")
    return hashlib.sha256(roh).hexdigest()


def eintragen(fassung: str, summe: str) -> None:
    pfad = HIER / "PKGBUILD"
    text = pfad.read_text("utf-8")

    neu, wie_oft = re.subn(r"^pkgver=.*$", f"pkgver={fassung}", text, flags=re.M)
    if wie_oft != 1:
        raise SystemExit("pkgver= steht nicht genau einmal im PKGBUILD.")
    text = neu

    # Die Freigabenummer beginnt bei jeder neuen Fassung wieder bei 1;
    # sie zählt Änderungen *am Paket*, nicht am Programm.
    text = re.sub(r"^pkgrel=.*$", "pkgrel=1", text, flags=re.M)

    neu, wie_oft = re.subn(r"^sha256sums=\('[0-9a-f]*'\)$",
                           f"sha256sums=('{summe}')", text, flags=re.M)
    if wie_oft != 1:
        raise SystemExit("sha256sums= steht nicht genau einmal im PKGBUILD.")
    pfad.write_text(neu, "utf-8")
    print(f"PKGBUILD auf {fassung} gesetzt, Prüfsumme eingetragen.")


def srcinfo_erzeugen() -> None:
    ergebnis = subprocess.run(
        ["makepkg", "--printsrcinfo"], cwd=HIER,
        capture_output=True, text=True, check=False)
    if ergebnis.returncode != 0:
        raise SystemExit(f"makepkg scheiterte:\n{ergebnis.stderr}")
    (HIER / ".SRCINFO").write_text(ergebnis.stdout, "utf-8")
    print(".SRCINFO neu erzeugt.")


def main() -> int:
    fassung = sys.argv[1] if len(sys.argv) > 1 else fassung_aus_dem_quelltext()
    print(f"WOLKENErnte {fassung} ins AUR-Paket nachziehen\n")

    # **Erst holen, dann schreiben.** Gibt es die Veröffentlichung noch
    # nicht, bricht es hier ab und das PKGBUILD bleibt unangetastet -
    # statt eine neue Fassung einzutragen, zu der es kein Archiv gibt.
    summe = pruefsumme(fassung)
    eintragen(fassung, summe)
    srcinfo_erzeugen()

    print("\nProbebauen (empfohlen, dauert eine halbe Minute):")
    print(f"  cd {HIER} && makepkg -f")
    print("\nDann ins AUR:")
    print("  cp PKGBUILD .SRCINFO ~/aur/wolkenernte/")
    print("  cd ~/aur/wolkenernte")
    print(f"  git add PKGBUILD .SRCINFO && git commit -m '{fassung}' && "
          f"git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

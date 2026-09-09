#!/usr/bin/env python3
"""Ein .deb für Debian und Ubuntu bauen.

    python3 verpacken/debian/deb-bauen.py

**Ohne debhelper und ohne Debian-Rechner.** Ein vollständiger
Debian-Quellbaum wäre der saubere Weg für eine Aufnahme *in* Debian –
aber dafür bräuchte es einen Debian-Rechner, einen Sponsor und ein
Verfahren, das Monate dauert. Wer das Programm heute auf seinem Debian
installieren will, braucht eine Datei. Die entsteht hier, aus dem
fertigen Wheel, mit ``dpkg-deb``.

**Drei Dinge sind bei Debian anders als bei Arch**, und alle drei sind
Fallen:

1. **``dist-packages``, nicht ``site-packages``.** Debian trennt die
   beiden: In ``site-packages`` landet, was der Anwender selbst mit pip
   installiert, in ``dist-packages`` das, was aus Paketen kommt. Ein
   Paket, das nach ``site-packages`` schreibt, wird vom System-Python
   schlicht nicht gefunden.
2. **Die Paketnamen sind andere.** Pillow heißt ``python3-pil``, und
   PySide6 ist in ein Dutzend Pakete zerlegt – gebraucht wird
   ``python3-pyside6.qtwidgets``.
3. **rclone ist zu alt.** Debian stable liefert eine Fassung unter
   1.75.0, und darunter fehlt die Schnittstelle, über die WOLKENErnte
   spricht. Deshalb steht rclone **ohne Versionsangabe** unter
   *Empfohlen*: Eine unerfüllbare Angabe blockierte die Installation,
   und das Programm sagt beim Start ohnehin selbst, was ihm fehlt.

**Kein ``postinst``.** Die Anwendungsdatenbank und der Symbolzwischen-
speicher werden von Debian über Trigger aufgefrischt; sie in einem
Wartungsskript selbst aufzurufen, verbietet die Debian-Policy
ausdrücklich.
"""

from __future__ import annotations

import gzip
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent.parent
BAU = WURZEL / "verpacken/debian/bau"

#: Welche Symbolgrößen ins Paket kommen.
#:
#: Genau die, für die eine eigene Fassung gezeichnet wurde – unter 48
#: Pixeln überlebt weder die Perforation noch der zweite Berggipfel.
GROESSEN = (16, 24, 32, 48, 64, 128, 256)

#: Was ohne das Paket nicht läuft.
#:
#: **Nur Python.** Der Kern kommt ohne Fremdpakete aus; alles andere
#: ist Kür und steht weiter unten. Ein Paket, das PySide6 erzwingt,
#: zöge auf einem Server hundert Megabyte Qt nach sich, die niemand
#: braucht.
PFLICHT = "python3 (>= 3.11)"

#: Was fast jeder will – wird von apt standardmäßig mitinstalliert.
EMPFOHLEN = [
    "python3-pyside6.qtwidgets",   # die Fensteranwendung
    "python3-pil",                 # Vorschaubilder, Doppelgänger, EXIF
    "rclone",                      # der Zugang zu den Cloudspeichern
    # Vorschaubilder aus Videos. Stand unter »Suggests«, solange es
    # nichts zu holen gab; seit 0.4.1 zieht ffmpeg das Einzelbild, und
    # ohne es bleibt jedes Video eine graue Kachel. Neben PySide6 mit
    # seinen hundert Megabyte fällt die Größe nicht ins Gewicht.
    "ffmpeg",
]

#: Was nur manche brauchen.
VORGESCHLAGEN = [
    "python3-numpy",               # kommt mit onnxruntime ohnehin
    "python3-onnxruntime",         # Schlagwörter aus dem Bild
    "libimage-exiftool-perl",      # Metadaten von Fotos und Videos
]

BESCHREIBUNG = """\
 Holt Bilder und Videos aus Cloudspeichern in ein Archiv auf der eigenen
 Platte, ordnet sie nach Aufnahmedatum, findet Doppelgänger und räumt
 auf Wunsch in der Cloud auf - aber nur, was nachweislich angekommen
 ist.
 .
 Unterstützt Nextcloud, Dropbox, OneDrive, Google Drive, Box, pCloud,
 iCloud Drive und Proton Drive über rclone. Google Fotos und Proton
 Fotos bieten keine Schnittstelle mehr an; für sie zeigt das Programm
 den Weg über den Datenexport des Anbieters.
 .
 Es gibt eine Fensteranwendung (python3-pyside6.qtwidgets) und eine
 Weboberfläche, die nur auf dem eigenen Rechner erreichbar ist. Der Kern
 läuft ohne beides.
 .
 Hinweis: rclone muss mindestens in Fassung 1.75.0 vorliegen. Debian
 stable liefert eine ältere; "wolkenernte rclone" sagt, was vorhanden
 ist."""


def fassung() -> str:
    zeile = next(z for z in (WURZEL / "wolkenernte/__init__.py").read_text()
                 .splitlines() if z.startswith("__version__"))
    return zeile.split('"')[1]


def rufen(*befehl: str, wo: Path | None = None) -> None:
    ergebnis = subprocess.run(befehl, cwd=wo or WURZEL)
    if ergebnis.returncode:
        sys.exit(f"Fehlgeschlagen: {' '.join(befehl)}")


def wheel_bauen() -> Path:
    """Das Wheel erzeugen, aus dem das Paket entsteht.

    ``dist`` wird vorher geleert: Liegen dort zwei Wheels, greift der
    Einbau zum falschen – ein Fehler, der beim Bauen des Arch-Pakets
    schon einmal zugeschlagen hat.
    """
    shutil.rmtree(WURZEL / "dist", ignore_errors=True)
    shutil.rmtree(WURZEL / "build", ignore_errors=True)
    rufen(sys.executable, "-m", "build", "--wheel")
    wheels = list((WURZEL / "dist").glob("*.whl"))
    if len(wheels) != 1:
        sys.exit(f"Erwartet wurde genau ein Wheel, gefunden: {wheels}")
    return wheels[0]


def baum_bauen(wheel: Path, version: str) -> Path:
    shutil.rmtree(BAU, ignore_errors=True)
    paket = BAU / f"wolkenernte_{version}_all"

    # **dist-packages, nicht site-packages.** Sonst findet das
    # System-Python das Paket nicht.
    ziel = paket / "usr/lib/python3/dist-packages"
    ziel.mkdir(parents=True)
    rufen(sys.executable, "-m", "pip", "install", "--no-deps", "--no-compile",
          "--target", str(ziel), str(wheel))

    # Der Startbefehl. Nicht der aus dem Wheel: Dessen Erste Zeile zeigt
    # auf den Python, mit dem gebaut wurde - auf einem Debian ist das
    # der falsche Pfad.
    binaer = paket / "usr/bin"
    binaer.mkdir(parents=True)
    start = binaer / "wolkenernte"
    start.write_text(
        "#!/usr/bin/python3\n"
        "import sys\n\n"
        "from wolkenernte.__main__ import main\n\n"
        "sys.exit(main())\n"
    )
    start.chmod(0o755)
    # Das Wheel bringt seinen eigenen Starter mit - der muss weg, sonst
    # liegen zwei da.
    shutil.rmtree(ziel / "bin", ignore_errors=True)

    # **pip-Spuren austragen.** ``INSTALLER`` sagt »pip«, ``REQUESTED``
    # und ``direct_url.json`` behaupten, jemand habe das Paket von Hand
    # aus einer Datei installiert. In einem Distributionspaket ist
    # beides schlicht falsch - installiert hat dpkg.
    for verzeichnis in ziel.glob("*.dist-info"):
        for name in ("REQUESTED", "direct_url.json"):
            verzeichnis.joinpath(name).unlink(missing_ok=True)
        verzeichnis.joinpath("INSTALLER").write_text("dpkg\n")

    # Menüeintrag und Symbole.
    anwendungen = paket / "usr/share/applications"
    anwendungen.mkdir(parents=True)
    shutil.copyfile(WURZEL / "verpacken/wolkenernte.desktop",
                    anwendungen / "wolkenernte.desktop")
    for groesse in GROESSEN:
        quelle = WURZEL / f"assets/icon-{groesse}.png"
        if not quelle.exists():
            continue
        ordner = (paket / "usr/share/icons/hicolor"
                  / f"{groesse}x{groesse}/apps")
        ordner.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(quelle, ordner / "wolkenernte.png")

    # **Was Debian verlangt.** Ohne copyright und changelog ist ein
    # Paket nach Policy unvollständig, auch wenn dpkg es baut.
    doku = paket / "usr/share/doc/wolkenernte"
    doku.mkdir(parents=True)
    lizenz = (WURZEL / "LICENSE").read_text()
    doku.joinpath("copyright").write_text(
        "Format: https://www.debian.org/doc/packaging-manuals/"
        "copyright-format/1.0/\n"
        "Upstream-Name: WOLKENErnte\n"
        "Source: https://github.com/Stephan-Lefty/WOLKENErnte\n\n"
        "Files: *\n"
        "Copyright: 2026 Stephan Rösner\n"
        "License: MIT\n"
        + "".join(f" {z}\n" if z.strip() else " .\n"
                 for z in lizenz.splitlines())
    )
    eintrag = (
        f"wolkenernte ({version}-1) unstable; urgency=medium\n\n"
        f"  * Fassung {version}.\n\n"
        f" -- Stephan Rösner <noreply@example.invalid>  "
        f"{time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime())}\n"
    )
    with gzip.GzipFile(doku / "changelog.Debian.gz", "wb", mtime=0) as gz:
        gz.write(eintrag.encode())

    return paket


def steuerdatei(paket: Path, version: str) -> None:
    steuerung = paket / "DEBIAN"
    steuerung.mkdir()

    groesse = sum(p.stat().st_size for p in paket.rglob("*") if p.is_file())
    steuerung.joinpath("control").write_text(
        f"Package: wolkenernte\n"
        f"Version: {version}-1\n"
        # **all, nicht amd64.** Reines Python; dasselbe Paket läuft auf
        # jedem Rechner, auch auf einem Raspberry Pi.
        f"Architecture: all\n"
        f"Maintainer: Stephan Rösner <noreply@example.invalid>\n"
        f"Installed-Size: {groesse // 1024}\n"
        f"Depends: {PFLICHT}\n"
        f"Recommends: {', '.join(EMPFOHLEN)}\n"
        f"Suggests: {', '.join(VORGESCHLAGEN)}\n"
        f"Section: graphics\n"
        f"Priority: optional\n"
        f"Homepage: https://github.com/Stephan-Lefty/WOLKENErnte\n"
        f"Description: Bilder aus Cloudspeichern holen und dort aufräumen\n"
        f"{BESCHREIBUNG}\n"
    )

    # md5sums: nicht vorgeschrieben, aber ohne sie kann "debsums" nicht
    # prüfen, ob eine Datei nachträglich verändert wurde.
    zeilen = []
    for datei in sorted(paket.rglob("*")):
        if not datei.is_file() or "DEBIAN" in datei.parts:
            continue
        summe = hashlib.md5(datei.read_bytes()).hexdigest()  # noqa: S324
        zeilen.append(f"{summe}  {datei.relative_to(paket)}")
    steuerung.joinpath("md5sums").write_text("\n".join(zeilen) + "\n")


def main() -> int:
    version = fassung()
    print(f"WOLKENErnte {version} als .deb\n")

    wheel = wheel_bauen()
    print(f"  Wheel: {wheel.name}")

    paket = baum_bauen(wheel, version)
    steuerdatei(paket, version)

    ziel = WURZEL / "dist" / f"wolkenernte_{version}-1_all.deb"
    # --root-owner-group: Sonst trägt jede Datei die Kennung dessen, der
    # gebaut hat, und dpkg meckert beim Installieren.
    rufen("dpkg-deb", "--build", "--root-owner-group", str(paket), str(ziel))

    print(f"\n{ziel}  ({ziel.stat().st_size / 1e6:.1f} MB)")
    print("\nInstallieren:")
    print(f"  sudo apt install ./{ziel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

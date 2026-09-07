#!/usr/bin/env python3
"""Die englischen Fragen einmal in Zahlenreihen umrechnen.

**Läuft beim Bauen, nicht beim Nutzer.** Dieses Werkzeug braucht den
Textteil des Modells (242 MB) und ``onnxruntime``; das Ergebnis ist
eine Datei von etwa dreihundert Kilobyte, die dem Programm beiliegt.
Auf dem Rechner des Nutzers läuft davon nichts.

Genau darin liegt der Kniff: Weil unsere Fragen feststehen, muss der
Textteil nur einmal laufen – hier. Das spart dem Nutzer 242 MB und
macht den Umweg über ein mehrsprachiges Modell überflüssig. Die Frage
ist englisch, weil das Modell nur Englisch kann; der deutsche Name
daneben ist unserer und braucht keine Übersetzung.

Aufruf:

    python3 werkzeuge/begriffe_einbetten.py

Danach liegt ``wolkenernte/daten/begriffe.npz`` neu vor und gehört ins
Repository. Wer :mod:`wolkenernte.begriffe` ändert, muss dieses
Werkzeug laufen lassen – sonst zeigen die Zahlen auf die falschen
Wörter. Das Programm merkt das und weigert sich, aber erst zur
Laufzeit.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import onnxruntime as ort  # noqa: E402

from werkzeuge.clip_zerleger import Zerleger  # noqa: E402
from wolkenernte.begriffe import VORLAGEN, alle_begriffe  # noqa: E402
from wolkenernte.modelle import TEXTTEIL, holen, ordner, vorhanden  # noqa: E402

#: Wie viele Wortstücke der Textteil erwartet – fest, nicht verhandelbar.
LAENGE = 77

ZIEL = Path(__file__).resolve().parent.parent / "wolkenernte/daten/begriffe.npz"


def zerlegen(zerleger: Zerleger, satz: str) -> np.ndarray:
    """Einen Satz in die 77 Zahlen wandeln, die das Modell erwartet.

    Kürzere Sätze werden mit Nullen aufgefüllt, längere abgeschnitten –
    unsere längste Zerlegung hat 19 Stücke, das Abschneiden ist reine
    Vorsorge.
    """
    stuecke = zerleger.zahlen(satz)[:LAENGE]
    gefuellt = stuecke + [0] * (LAENGE - len(stuecke))
    return np.array([gefuellt], dtype=np.int32)


def hauptteil() -> int:
    datei = vorhanden(TEXTTEIL) or holen(
        TEXTTEIL,
        lambda geladen, gesamt: print(
            f"\r  {geladen / gesamt:6.1%}", end="", flush=True))
    zerlegerdatei = ordner() / "tokenizer.json"
    if not zerlegerdatei.is_file():
        print(f"Der Zerleger fehlt: {zerlegerdatei}\n"
              "Zu holen von https://huggingface.co/immich-app/"
              "ViT-B-32__openai/resolve/main/textual/tokenizer.json",
              file=sys.stderr)
        return 1

    zerleger = Zerleger.aus_datei(zerlegerdatei)
    sitzung = ort.InferenceSession(
        str(datei), providers=["CPUExecutionProvider"])

    zeilen = alle_begriffe()
    print(f"{len(zeilen)} Fragen, je {len(VORLAGEN)} Formulierungen")

    matrix = np.zeros((len(zeilen), 512), dtype=np.float32)
    for nummer, (gruppe, name, frage) in enumerate(zeilen):
        # Mehrere Formulierungen desselben Gedankens, gemittelt. Ein
        # einzelner Satz trifft launisch; hier kostet der Mittelwert
        # nichts, weil er nur einmal gerechnet wird.
        gesammelt = np.zeros(512, dtype=np.float32)
        for vorlage in VORLAGEN:
            (reihe,) = sitzung.run(
                None, {"text": zerlegen(zerleger, vorlage.format(frage))})
            vektor = reihe[0].astype(np.float32)
            gesammelt += vektor / (np.linalg.norm(vektor) or 1.0)
        matrix[nummer] = gesammelt / (np.linalg.norm(gesammelt) or 1.0)
        print(f"\r  {nummer + 1}/{len(zeilen)}  {gruppe}/{name}      ",
              end="", flush=True)
    print()

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        ZIEL, matrix=matrix,
        fragen=np.array([f for _, _, f in zeilen], dtype=object).astype(str))
    print(f"{ZIEL} geschrieben, {ZIEL.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(hauptteil())

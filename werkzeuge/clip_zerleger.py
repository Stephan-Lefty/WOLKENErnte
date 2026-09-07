"""Sätze in die Zahlen zerlegen, die der Textteil des Modells erwartet.

**Läuft nur beim Bauen.** Auf dem Rechner des Nutzers wird kein Satz
zerlegt – die englischen Fragen aus :mod:`wolkenernte.begriffe` sind
längst zu Zahlenreihen geworden, bevor das Programm ausgeliefert wird.

Warum selbst gebaut? Weil das fertige Paket ``tokenizers`` eine
kompilierte Rust-Erweiterung ist, die es unter Arch nicht als Paket
gibt – und für **hundertfünfzig kurze englische Sätze**, einmal, wäre
ein eigener Probierkasten mit pip ein hoher Preis. Das Verfahren selbst
ist überschaubar: Byte-Paar-Kodierung, wie sie CLIP von GPT-2 geerbt
hat, und die Regeln dazu stehen alle in ``tokenizer.json``.

Gegengeprüft wird gegen bekannte Zerlegungen, siehe
``tests/test_clip_zerleger.py``.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

#: Anfang und Ende eines Satzes. Das Modell erwartet beide.
ANFANG = "<|startoftext|>"
ENDE = "<|endoftext|>"

#: Wie ein Satz in Wörter zerfällt, bevor die Byte-Paare drankommen.
#:
#: CLIPs Vorlage schreibt das mit den Unicode-Kategorien ``\p{L}``
#: (Buchstabe) und ``\p{N}`` (Ziffer), die Pythons ``re`` nicht kennt.
#: Übersetzt:
#:
#: * ``\p{L}+`` → ``[^\W\d_]+`` – ein Wortzeichen, das weder Ziffer
#:   noch Unterstrich ist
#: * ``\p{N}`` → ``\d`` – und zwar **eine** Ziffer, nicht mehrere:
#:   ``2024`` zerfällt in vier Stücke, so will es das Verfahren
#: * ``[^\s\p{L}\p{N}]+`` → ``(?:[^\s\w]|_)+`` – Satzzeichen. Der
#:   Unterstrich muss ausdrücklich hinein, weil ``\w`` ihn einschließt,
#:   ``\p{L}`` und ``\p{N}`` aber nicht.
#:
#: Der letzte Punkt ist die Stelle, an der ein erster Anlauf danebenlag:
#: Ein falsch übersetzter Ausdruck verschluckte **jedes Satzzeichen**.
#: Die Wörter waren dann alle richtig zerlegt – nur der Schlusspunkt
#: fehlte, und damit hätte das Modell andere Sätze gesehen als im
#: Training.
#:
#: Die Anführungszeichen-Fälle (``'s``, ``'t``, …) stehen vor den
#: Buchstaben, damit *don't* nicht als *don* und *t* zerfällt.
WOERTER = re.compile(
    r"<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|"
    r"[^\W\d_]+|\d|(?:[^\s\w]|_)+",
    re.IGNORECASE)


@lru_cache(maxsize=1)
def _bytes_nach_zeichen() -> dict[int, str]:
    """Jedes Byte auf ein druckbares Zeichen abbilden.

    Der Kniff aus GPT-2: Byte-Paar-Kodierung arbeitet auf Text, die
    Eingabe ist aber ein Bytestrom. Die 188 ohnehin druckbaren Bytes
    bleiben sie selbst, die übrigen 68 wandern nach oben in einen
    Bereich, in dem sie mit nichts kollidieren.
    """
    druckbar = (list(range(ord("!"), ord("~") + 1))
                + list(range(ord("¡"), ord("¬") + 1))
                + list(range(ord("®"), ord("ÿ") + 1)))
    zeichen = list(druckbar)
    naechstes = 0
    for wert in range(256):
        if wert not in druckbar:
            druckbar.append(wert)
            zeichen.append(256 + naechstes)
            naechstes += 1
    return {wert: chr(code) for wert, code in zip(druckbar, zeichen)}


def saeubern(satz: str) -> str:
    """Was CLIP vor dem Zerlegen mit einem Satz macht.

    HTML-Entitäten auflösen, Zeichen vereinheitlichen, Leerraum
    zusammenziehen, klein schreiben. Unsere eigenen Sätze bräuchten
    das nicht – aber wer hier abweicht, bekommt andere Zahlen als das
    Modell im Training gesehen hat.
    """
    entschaerft = html.unescape(html.unescape(satz))
    vereinheitlicht = unicodedata.normalize("NFC", entschaerft)
    return " ".join(vereinheitlicht.split()).strip().lower()


class Zerleger:
    """Der Zerleger, aufgebaut aus ``tokenizer.json``."""

    def __init__(self, wortschatz: dict[str, int],
                 verschmelzungen: list[tuple[str, str]]) -> None:
        self.wortschatz = wortschatz
        self.rang = {paar: nummer
                     for nummer, paar in enumerate(verschmelzungen)}
        self.bytes_nach_zeichen = _bytes_nach_zeichen()
        self._gemerkt: dict[str, list[str]] = {}

    @classmethod
    def aus_datei(cls, datei: Path) -> Zerleger:
        beschreibung = json.loads(datei.read_text(encoding="utf-8"))
        modell = beschreibung["model"]
        verschmelzungen = []
        for eintrag in modell["merges"]:
            if isinstance(eintrag, str):
                links, rechts = eintrag.split(" ", 1)
            else:
                links, rechts = eintrag
            verschmelzungen.append((links, rechts))
        return cls(modell["vocab"], verschmelzungen)

    def _zerlegen(self, wort: str) -> list[str]:
        """Ein einzelnes Wort in seine Stücke zerlegen.

        Das Ende des Wortes wird mit ``</w>`` markiert – so
        unterscheidet das Verfahren *in* am Wortende von *in* mitten in
        *inside*.
        """
        gemerkt = self._gemerkt.get(wort)
        if gemerkt is not None:
            return gemerkt

        stuecke = list(wort[:-1]) + [wort[-1] + "</w>"]
        while len(stuecke) > 1:
            paare = list(zip(stuecke, stuecke[1:]))
            bestes = min(paare, key=lambda paar: self.rang.get(paar, 1 << 30))
            if bestes not in self.rang:
                break
            links, rechts = bestes
            neu: list[str] = []
            stelle = 0
            while stelle < len(stuecke):
                if (stelle < len(stuecke) - 1
                        and stuecke[stelle] == links
                        and stuecke[stelle + 1] == rechts):
                    neu.append(links + rechts)
                    stelle += 2
                else:
                    neu.append(stuecke[stelle])
                    stelle += 1
            stuecke = neu

        self._gemerkt[wort] = stuecke
        return stuecke

    def zahlen(self, satz: str) -> list[int]:
        """Ein Satz als Zahlenfolge, mit Anfangs- und Endmarke."""
        folge = [self.wortschatz[ANFANG]]
        for wort in WOERTER.findall(saeubern(satz)):
            umgeschrieben = "".join(
                self.bytes_nach_zeichen[byte]
                for byte in wort.encode("utf-8"))
            folge.extend(self.wortschatz[stueck]
                         for stueck in self._zerlegen(umgeschrieben))
        folge.append(self.wortschatz[ENDE])
        return folge

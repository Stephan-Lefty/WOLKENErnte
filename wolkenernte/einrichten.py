"""Einen Zugang zu einem Wolkenspeicher einrichten.

rclone führt dabei ein Gespräch: Es stellt eine Frage, bekommt eine
Antwort, stellt die nächste. Über die Schnittstelle sieht das so aus,
dass jeder Aufruf von ``config/create`` entweder eine Frage zurückgibt
oder meldet, dass es fertig ist.

**Der Ablauf ist für alle Anbieter derselbe.** Anbieterspezifisch sind
nur die Startangaben und die Beschriftungen – die Fragen selbst kommen
von rclone und werden hier nur weitergereicht. Das ist der Grund, warum
dieselben knapp hundert Zeilen Nextcloud, Dropbox, OneDrive, pCloud,
Proton Drive und iCloud tragen: Wer OneDrive einrichtet, bekommt eine
Laufwerksliste, die rclone erst zur Laufzeit von Microsoft holt – die
kann kein Programm vorher kennen.

**Drei Zustände, nicht zwei.** Die Antwort kann auch ein reiner Fehler
ohne Frage sein; iCloud macht das, wenn der 2FA-Code leer bleibt.
rclones eigenes Beispielprogramm behandelt diesen Fall nicht und liefe
dort in einen Absturz.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .rclone import Dienst, RcloneFehler


@dataclass(frozen=True)
class Frage:
    """Was rclone vom Anwender wissen will."""

    name: str
    hilfe: str = ""
    vorgabe: str = ""
    art: str = "string"
    """``string``, ``bool``, ``int`` – bestimmt, wie gefragt wird."""

    pflicht: bool = False
    geheim: bool = False
    """Ein Kennwort. Nicht anzeigen, nicht protokollieren."""

    auswahl: list[str] = field(default_factory=list)
    nur_auswahl: bool = False
    """Ob **nur** die Vorschläge zulässig sind."""

    fehler: str = ""
    """Was beim letzten Versuch schiefging."""

    @classmethod
    def aus_antwort(cls, option: dict, fehler: str = "") -> Frage:
        beispiele = option.get("Examples") or []
        return cls(
            name=option.get("Name", ""),
            hilfe=(option.get("Help") or "").strip(),
            vorgabe=str(option.get("Default") or ""),
            art=option.get("Type", "string"),
            pflicht=bool(option.get("Required")),
            geheim=bool(option.get("IsPassword")),
            auswahl=[str(b.get("Value", "")) for b in beispiele],
            nur_auswahl=bool(option.get("Exclusive")),
            fehler=fehler,
        )


class Abbruch(Exception):
    """Der Anwender hat die Einrichtung abgebrochen."""


def einrichten(
    dienst: Dienst,
    name: str,
    art: str,
    *,
    angaben: dict[str, str] | None = None,
    fragen: Callable[[Frage], str | None] | None = None,
    hoechstens: int = 60,
) -> None:
    """Einen Zugang anlegen und dabei alle Rückfragen beantworten.

    ``angaben`` sind die Werte, die von vornherein feststehen – etwa
    Adresse und Benutzername bei Nextcloud. ``fragen`` wird für alles
    aufgerufen, was rclone darüber hinaus wissen will; gibt es ``None``
    zurück, bricht die Einrichtung ab.

    Ohne ``fragen`` läuft nur durch, was ohne Rückfragen auskommt –
    Nextcloud etwa, wenn alle Angaben mitgegeben wurden.
    """
    angaben = dict(angaben or {})

    # rclone soll den Browser nicht selbst öffnen: Bei einer
    # Fensteranwendung soll das Programm entscheiden, wann und wie.
    angaben.setdefault("config_auth_no_browser", "true")

    opt: dict = {"nonInteractive": True, "obscure": True}

    for _ in range(hoechstens):
        antwort = dienst.rufen("config/create", {
            # **Die Angaben müssen bei jedem Durchgang vollständig
            # mitgeschickt werden**, nicht nur beim ersten. So steht es
            # in rclones Dokumentation zu --continue, und es ist die
            # Sorte Fehler, die sich erst beim dritten Anbieter zeigt.
            "name": name, "type": art, "parameters": angaben, "opt": opt,
        })

        zustand = antwort.get("State") or ""
        if not zustand:
            return  # fertig

        option = antwort.get("Option")
        fehler = antwort.get("Error") or ""

        if option is None:
            # Reiner Fehlerzustand ohne Frage - iCloud macht das bei
            # leerem 2FA-Code. Mit demselben Zustand und leerer Antwort
            # weiter, sonst dreht sich das Gespräch im Kreis.
            if not fehler:
                raise RcloneFehler(
                    f"rclone meldet Zustand {zustand!r} ohne Frage und ohne Grund."
                )
            antwortwert = ""
        else:
            if fragen is None:
                raise RcloneFehler(
                    f"rclone fragt nach {option.get('Name')!r}, "
                    "aber es ist niemand da, der antworten könnte."
                )
            gegeben = fragen(Frage.aus_antwort(option, fehler))
            if gegeben is None:
                raise Abbruch("Einrichtung abgebrochen.")
            antwortwert = gegeben

        opt = {**opt, "continue": True, "state": zustand, "result": antwortwert}

    raise RcloneFehler(
        f"Die Einrichtung von {name} kam nach {hoechstens} Schritten "
        "zu keinem Ende."
    )


def nextcloud_adresse(eingabe: str, benutzer: str) -> str:
    """Aus einer Nextcloud-Adresse die machen, die rclone braucht.

    **Sie muss auf ``/remote.php/dav/files/BENUTZER/`` enden.** Endet
    sie auf das ältere ``/remote.php/webdav/``, greift rclones
    Erkennung für stückweises Hochladen nicht, und Übertragungen
    scheitern erst später und ohne erkennbaren Zusammenhang. rclones
    eigene Dokumentation zeigt im Beispiel bis heute die alte Form.

    Deshalb wird hier zurechtgerückt, statt sich auf die Eingabe zu
    verlassen.
    """
    adresse = eingabe.strip().rstrip("/")
    for anhang in ("/remote.php/webdav", "/remote.php/dav/files",
                   "/remote.php/dav", "/remote.php"):
        if adresse.endswith(anhang):
            adresse = adresse[: -len(anhang)]
            break
    # Ein bereits vollständiger Pfad mit Benutzernamen am Ende.
    if "/remote.php/dav/files/" in eingabe:
        adresse = eingabe.split("/remote.php/dav/files/")[0]
    return f"{adresse}/remote.php/dav/files/{benutzer}/"


def nextcloud(
    dienst: Dienst, name: str, adresse: str, benutzer: str, kennwort: str
) -> None:
    """Einen Nextcloud-Zugang anlegen.

    Der einfachste Fall überhaupt: WebDAV kennt keine Rückfragen, alles
    steht von vornherein fest.

    **Ein App-Passwort verwenden, nicht das Kontokennwort.** Bei
    eingeschalteter Zwei-Faktor-Anmeldung nimmt Nextcloud das
    Kontokennwort über WebDAV gar nicht an – und ein Kennwort, das nur
    für dieses eine Programm gilt, lässt sich einzeln zurückziehen.
    """
    einrichten(dienst, name, "webdav", angaben={
        "url": nextcloud_adresse(adresse, benutzer),
        "vendor": "nextcloud",
        "user": benutzer,
        "pass": kennwort,
    })

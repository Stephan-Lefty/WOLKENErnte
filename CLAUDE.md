# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-09-05)

**Das Repository ist neu und privat.** Es gibt ein Gerüst, 29 grüne Tests
und genau eine Fähigkeit: `python3 -m wolkenernte` gibt aus, was bei
welchem Anbieter möglich ist. Sonst nichts – kein Abruf, kein Löschen,
keine Oberfläche.

Der Name entstand nach vier verworfenen Vorschlägen; die Begründungen
stehen im erledigten Teil der [TODO.md](TODO.md). Schreibweise wie bei
POSTKutsche: **WOLKENErnte**, das Python-Paket dagegen klein,
`wolkenernte`.

## Das Wichtigste zuerst: die Anbietertabelle

`wolkenernte/anbieter.py` ist der Kern dieses Programms, obwohl dort
nichts gerechnet wird. Sie hält fest, was ein Wolkenspeicher einem
fremden Programm erlaubt – **einzeln nach auflisten, laden, löschen**,
nicht als »unterstützt ja/nein«.

**Warum das keine Fußnote in der Anleitung ist.** Der Wunsch, aus dem
dieses Programm entstand, lautete: alle Bilder aus allen Wolken holen
und dort löschen. Genau die drei zuerst genannten Anbieter können das
nicht:

- **Google Fotos** – seit 31.03.2025 sieht ein fremdes Programm nur
  noch die eigenen Uploads; eine Löschmethode gab es nie.
- **iCloud Fotos** – vollständig lesbar, ausdrücklich nur lesend.
- **Proton Fotos** – eigener Bereich, für rclone unsichtbar.

Die Belege mit Datum in [docs/anbieter.md](docs/anbieter.md).

**Drei Dinge daran sind Absicht und sollten so bleiben:**

`darf_loeschen()` gibt für **unbekannte** Kennungen `False` zurück. Wer
einen Anbieter hinzufügt und die Tabelle vergisst, bekommt ein Programm,
das zu wenig anbietet – nicht eines, das zu viel verspricht.

**Die Oberfläche fragt diese Tabelle, bevor sie einen Löschknopf
anzeigt.** Einen Knopf, der nichts tut, soll es nicht geben.

`tests/test_anbieter.py` nagelt die drei bekannten Grenzen fest. Wenn
eine davon eines Tages fällt, schlägt der Test fehl und zwingt dazu, den
Beleg nachzutragen – statt dass eine Zusage stillschweigend hereinrutscht.

## Wie es weitergehen soll

rclone als Motor, angesprochen über `rclone rcd` und dessen
HTTP-Schnittstelle. **Anmeldung ist dabei Pflicht, nicht Kür:** Wer die
Schnittstelle erreicht, kann über `core/command` beliebige Befehle
ausführen und über `config/dump` sämtliche Zugangsdaten auslesen. An
`127.0.0.1` binden, Benutzer und Kennwort setzen, und einen Test dafür
schreiben.

Der Kern bleibt ohne Fremdpakete – `urllib` und `json` genügen für
rclone. Alles Weitere ist Kür und wird zur Laufzeit geprüft.

## Zwei Entscheidungen, die man leicht rückgängig macht, ohne den Grund zu kennen

**Keine Browser-Steuerung.** Sie wäre der einzige Weg, in Google Fotos
und iCloud Fotos zu löschen. Sie sitzt aber auf undokumentierten
internen Schnittstellen, bricht ohne Vorwarnung, und bei Apple verstößt
sie ausdrücklich gegen die Nutzungsbedingungen. Für Google Fotos ist der
vorgesehene Weg deshalb: Takeout einlesen, ansehen, Doppelgänger finden –
und beim Aufräumen ehrlich auf den Browser verweisen.

**pi-heif statt pillow-heif.** Gleicher Entwickler, gleicher Code, aber
die fertigen Pakete von pillow-heif enthalten x265, einen HEVC-Kodierer
unter GPL. Wer die mitliefert, verteilt GPL-Code und muss das eigene
Programm darunter stellen. WOLKENErnte zeigt Bilder nur an; der reine
Dekodierer genügt.

## Das Programmsymbol

`assets/icon.svg` ist die Quelle, alle PNG und die `.ico` werden daraus
erzeugt. Der Verlauf ist `BLAU_HELL → BLAU_TIEF` aus `farben.py`,
derselbe wie bei MailBurg.

Zwei Dinge, die beim Bauen schiefgingen und wieder schiefgehen würden:
**Die Wolke muss die breiteste Form im Bild sein** – ist sie schmaler
als das, was darunter steht, verschmelzen beide beim Verkleinern zu
etwas, das wie eine Eistüte aussieht. Und **Motive vertragen nur wenige,
große Elemente**: zwei Berggipfel oder acht Filmlöcher sind bei 32 Pixeln
nicht mehr auseinanderzuhalten.

## Die Testläufe kosten Kontingent

Dieses Repository ist **privat**, Actions-Minuten werden also
abgerechnet. GitHub rundet jeden einzelnen Job auf volle Minuten auf und
rechnet macOS zehnfach, Windows zweifach. Bei MailBurg summierte sich
das an einem Arbeitstag auf 1.800 von 2.000 Minuten.

Deshalb: bei jedem Push **ein** Job auf Linux, die teuren Systeme
wöchentlich und auf Zuruf. Solange das Repository privat ist, bleibt das
so.

## Tests

```
python3 -m unittest discover -s tests -t .
```

`tests/__init__.py` muss existieren, sonst findet `discover` das
Verzeichnis nicht.

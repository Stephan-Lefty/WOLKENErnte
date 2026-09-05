[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md)

# Änderungsprotokoll

Alle nennenswerten Änderungen an WOLKENErnte. Neueste zuerst.

## 0.1.0 – 2026-09-05

Der erste Stand. Ein Gerüst mit genau einer Fähigkeit – aber der, die
man zuerst braucht.

**Die Anbietertabelle steht im Code, nicht in der Anleitung.**
`wolkenernte/anbieter.py` hält für jeden Wolkenspeicher fest, ob sich
dort auflisten, herunterladen und **löschen** lässt. Die Oberfläche wird
diese Tabelle fragen, bevor sie einen Löschknopf anzeigt; einen Knopf,
der nichts tut, soll es nicht geben.

Der Grund für diesen Aufwand: Ausgerechnet die drei Anbieter, an die man
bei Fotos zuerst denkt, können das Gewünschte nicht.

- **Google Fotos** – seit dem 31.03.2025 sieht ein fremdes Programm nur
  noch die Bilder, die es selbst hochgeladen hat. Eine Löschfunktion gab
  es dort nie. Bleibt der Umweg über Google Takeout.
- **iCloud Fotos** – vollständig lesbar, aber ausdrücklich nur lesend.
  Mit erweitertem Datenschutz gar nicht erreichbar.
- **Proton Fotos** – liegt in einem eigenen Bereich, den fremde
  Programme nicht sehen. Kein Weg vorhanden.

Die Belege dazu in [docs/anbieter.md](docs/anbieter.md).

**Drei Tests halten diese Grenzen fest.** Wenn eine davon eines Tages
fällt, schlägt der Test fehl und zwingt dazu, den Beleg nachzutragen –
statt dass eine Zusage stillschweigend hereinrutscht. Ebenso festgelegt:
Ein unbekannter Anbieter darf **nicht** löschen. Wer die Tabelle beim
Hinzufügen vergisst, bekommt ein Programm, das zu wenig anbietet, nicht
eines, das zu viel verspricht.

**Die Farben kommen aus MailBurg**, unverändert, mitsamt den gemessenen
Kontrastwerten. `tests/test_farben.py` prüft sie gegen WCAG 2.1 – für
ein Programm, das im Kern Bilder anzeigt, ist Lesbarkeit kein
Nebenschauplatz.

**Das Programmsymbol** liegt als SVG vor und wird daraus in allen Größen
bis hinunter zu 16 Pixeln erzeugt. Zwei Dinge sind dabei gelernt worden:
Die Wolke muss die breiteste Form im Bild sein, sonst verschmilzt sie
beim Verkleinern mit dem, was darunter steht. Und Bergmotiv wie
Filmperforation vertragen nur wenige, große Elemente – zwei Gipfel oder
acht Löcher sind bei 32 Pixeln nicht mehr auseinanderzuhalten.

**Die Testläufe kosten Kontingent.** Dieses Repository ist privat,
Actions-Minuten werden also abgerechnet, und GitHub rundet jeden Job auf
volle Minuten auf – macOS zehnfach, Windows zweifach. Deshalb von
Anfang an: bei jedem Push *ein* Job auf Linux, die teuren Systeme
wöchentlich und auf Zuruf.

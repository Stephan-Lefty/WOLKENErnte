[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md)

# Änderungsprotokoll

Alle nennenswerten Änderungen an WOLKENErnte. Neueste zuerst.

## 0.3.0 – 2026-09-07

**Die Fensteranwendung.** `wolkenernte fenster <Archiv>` öffnet ein
richtiges Fenster statt des Browsers: Raster, Filter nach Jahr und
Album, Suche, Einzelansicht mit Bild und Video, Blättern mit den
Pfeiltasten. Sie steht **neben** der Weboberfläche, nicht an ihrer
Stelle – wer keine hundert Megabyte PySide6 nachinstallieren will,
behält den Browserweg. Beide sitzen auf demselben Fundament.

Bei 14.767 Bildern steht das Fenster in einer halben Sekunde. Der Kniff:
nichts im Voraus tun. Qt fragt eine Listenansicht nur nach dem, was
gerade zu sehen ist; das Modell antwortet sofort mit einem Platzhalter
und lädt im Hintergrund nach.

**Der Anschluss an rclone**, das Fundament für den Abruf aus den Wolken.
Finden, Fassung prüfen, als Dienst starten, Zugänge einrichten,
auflisten, löschen. Abgesichert, denn wer diese Schnittstelle erreicht,
hat Shell-Zugriff: nur `127.0.0.1`, Zugangsdaten je Start neu gewürfelt
und über die Prozessumgebung übergeben, `--rc-no-auth` niemals.

`wolkenernte zugang nextcloud` legt einen Zugang an und macht gleich die
Probe. Vier Tests laufen gegen das **echte** rclone.

**Geprüft statt angenommen:** `werkzeuge/videoprobe.py` weist nach, dass
Qt H.264, HEVC und VP9 abspielt – mit tatsächlich ankommenden
Einzelbildern, nicht bloß ohne Fehlermeldung. libmpv wird nicht
gebraucht. Nebenbei kam heraus, dass dieser Bestand kein iPhone-Material
enthält: 239 VP9, 181 H.264, 5 HEVC.

**Die Bestandsliste liegt jetzt außerhalb des Browserteils.** Jahre
zählen, Alben sammeln, suchen, filtern – das braucht jede Oberfläche.

### Fehler, die erst der Blick auf den Bildschirm zeigte

Das Raster riss Lücken: `KeepAspectRatioByExpanding` bringt das Bild auf
Kachelgröße, schneidet aber nichts ab – Hochformate blieben hochkant.

Die Einzelansicht zeigte Bilder um 90 Grad gekippt. `QPixmap.load()`
ignoriert die EXIF-Aufnahmerichtung; im Raster fiel es nicht auf, weil
die Vorschaubilder von Pillow kommen, das von sich aus dreht.

Beim Umzug der Bestandsliste fiel eine Eigenschaft weg, die die
Weboberfläche noch benutzte – und **alle 239 Tests blieben grün**, weil
die Einzelansicht in keinem Test vorkam. Seither ruft
`tests/test_seiten.py` jede Seite einmal auf.

Und der Paketbau brach ab, weil sich in `dist/` die Pakete mehrerer
Fassungen sammelten und der Installer sie nacheinander auspackte.

## 0.2.0 – 2026-09-05

**Eine Oberfläche im Browser.** `wolkenernte oberflaeche` startet einen
Dienst, der nur auf diesem Rechner erreichbar ist: Bilder in Kacheln,
Filter nach Jahr und Album, Einzelansicht mit Ort und Datum, Videos
spielt der Browser ab. Keine Fensterbibliothek nötig – das wären über
hundert Megabyte, und die Videowiedergabe macht auf jeder Plattform
eigene Schwierigkeiten.

**Suche** über Dateinamen, Titel, Alben und Datum. **Doppelgängersuche**
über einen selbstgebauten Wahrnehmungs-Fingerabdruck, der auch dasselbe
Foto in zwei Auflösungen findet.

**Die Datenbank neben dem Archiv** hält fest, was nicht in die Bilddatei
passt: Ortsangaben, Titel, Alben, Favoriten. Ohne sie wären beim Löschen
der Quellen 3.770 Ortsangaben verloren gewesen – Google entfernt sie
beim Hochladen aus dem Bild.

**Menüeintrag unter »Grafik«** und ein PKGBUILD für Arch und Manjaro.

An einem echten Bestand: 14.770 Bilder aus 47 GB Quellen, 29 GB im
Archiv, 13.605 bytegleiche Kopien übergangen. Von 1.708 Gruppen
ähnlicher Bilder zeigen 1.332 dieselbe Aufnahme in mehreren Fassungen;
dort sind 1.447 Fassungen überzählig.

### Fehler, die erst das Ausprobieren zeigte

Ein `replace(",", ".")` für Tausenderpunkte lief über die ganze Seite
und zerlegte den `viewport`-Eintrag – auf dem Handy unbrauchbar.

SQLite kennt nur vorzeichenbehaftete 64-Bit-Zahlen; der Fingerabdruck
nutzt alle 64. Die Hälfte aller Bilder brach den Lauf ab.

Bilder ohne Aufnahmedatum standen in der Jahresliste unter »2026« – sie
tragen den Zeitstempel der Übernahme. Jetzt gesondert gezählt: 291.

Bilder mit schlichtem Hell-Dunkel-Verlauf ergeben achtmal dasselbe
Zeilenmuster und galten als »ähnlich«, obwohl sie nichts gemeinsam
hatten. 468 solcher Fingerabdrücke bleiben jetzt draußen.

Ein Regex zum Vergleichen von Dateinamen entfernte `_<Ziffern>` und
machte aus `IMG_20210110_113920` den Stamm `img` – jedes Kamerabild
hätte denselben gehabt.

Und die Doppelgängerseite zeigte 60 Gruppen auf einmal, über
vierhundert Vorschaubilder; der Browser lief in eine
Zeitüberschreitung. Jetzt zwanzig je Seite.

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

**Das Programmsymbol gibt es in drei Fassungen**, erzeugt von
`werkzeuge/symbole.py`: die volle ab 48 Pixeln, eine ohne Filmstreifen
für 24 und 32, und eine nur aus Wolke und Pfeil für 16. Dasselbe Bild
für alle Größen zu verkleinern ergibt kein reduziertes, sondern ein
zerfallenes – die feinsten Bestandteile verschwinden zuerst und lassen
Reste stehen, die für sich nichts mehr aussagen.

Vier Dinge sind dabei gelernt worden: Die Wolke muss die breiteste Form
im Bild sein, sonst verschmilzt sie beim Verkleinern mit dem, was
darunter steht. Bergmotiv und Filmperforation vertragen nur wenige,
große Elemente – zwei Gipfel oder acht Löcher sind bei 32 Pixeln nicht
mehr auseinanderzuhalten. Die Bildkachel darf die Wolke nicht ausfüllen,
sonst liest man ein Rechteck mit weißem Saum statt einer Wolke. Und bei
16 Pixeln brauchen Wolke und Pfeil etwa gleich viel Platz, sonst wirkt
der Pfeil wie ein Fortsatz der Wolke.

**Die Testläufe kosten Kontingent.** Dieses Repository ist privat,
Actions-Minuten werden also abgerechnet, und GitHub rundet jeden Job auf
volle Minuten auf – macOS zehnfach, Windows zweifach. Deshalb von
Anfang an: bei jedem Push *ein* Job auf Linux, die teuren Systeme
wöchentlich und auf Zuruf.

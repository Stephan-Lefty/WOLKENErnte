# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-09-07, Montagmittag)

**359 Tests grün.** Seit heute Mittag gibt es **Schlagwörter**. Die
Hälfte, die kein Modell braucht – Jahreszeit, Tageszeit, Bildformat,
Herkunft – läuft und trifft: 14.767 Bilder, nur 31 ohne jedes
Schlagwort. Die andere Hälfte, die ins Bild schaut, ist gebaut, aber
**noch nie gelaufen**.

**Genau ein Schritt fehlt**, und ohne ihn tut die Bilderkennung
nichts:

```
python3 werkzeuge/begriffe_einbetten.py
```

Das rechnet die 150 englischen Fragen einmal in Zahlenreihen um und
schreibt `wolkenernte/daten/begriffe.npz` (rund 300 KB, gehört ins
Repository). Es braucht `onnxruntime` und `tokenizers`; unter Manjaro
liegt ersteres als `python-onnxruntime-cpu` in `extra`. Die beiden
Modellhälften liegen bereits unter
`~/.local/share/WOLKENErnte/modelle/`, ebenso `tokenizer.json`.

Danach ist die erste Frage: **Was kommt am echten Bestand heraus?** Die
Schwellen in `begriffe.py` sind geschätzt, nicht gemessen – dieselbe
Lage wie bei »Kamera«, bevor auffiel, dass es 58 % traf.

**Der eigentliche Zweck bleibt offen:** aus einer Wolke ernten. Der
Weg dorthin steht in `wolke.py`, erprobt ist er nur gegen rclones
`local`-Backend.

## Wie die Schlagwörter deutsch werden, ohne Übersetzung

Ein CLIP-Modell besteht aus zwei Hälften: Die eine wandelt Bilder in
Zahlenreihen, die andere Sätze. Beide zusammen sind 582 MB.

Weil unsere Fragen aber **feststehen** – sie stehen in `begriffe.py` –,
läuft der Textteil nur einmal, beim Bauen. Sein Ergebnis sind 300 KB,
die dem Programm beiliegen. Auf dem Rechner des Nutzers läuft nur der
Bildteil.

Daraus folgt das Deutsche fast nebenbei: Die **Frage** ist englisch,
weil das Modell nur Englisch kann. Der **Name** daneben ist unserer –
wir schreiben ihn hin, wie er heißen soll. Niemand übersetzt etwas, es
gibt keinen Übersetzungsfehler und kein mehrsprachiges Modell (die
kosten 250 MB bis 1,6 GB extra, nur für den Textteil, und antworten auf
Deutsch schlechter als auf Englisch). digiKam löst dasselbe Problem
mit einem Online-Übersetzer, pro Bild und pro Wort; für ein Programm,
das offline arbeiten soll, ist das kein Weg.

**Gruppen statt einer langen Liste.** Die Zahlen des Modells lassen
sich *innerhalb* einer Auswahl vergleichen, nicht über das ganze Feld:
»Strand« und »Küche« stehen nie zur selben Frage an. Ohne Gruppen fräßen
außerdem fünf Verwandte alle fünf Plätze.

**Und eine Schwelle je Gruppe.** Die Gegenprobe sagt, warum: Ohne sie
bekommt ein völlig flaues Bild »Strand, Porträt, Gruppenbild, Feier,
Sonnenuntergang«.

**ViT-B/32, nicht MobileCLIP.** MobileCLIP ist auf dem Papier
schneller, aber die Zahlen stammen vom Neuronenrechenwerk eines
iPhones; auf einem gewöhnlichen Rechner ist MobileCLIP-S2 gemessen
1,5-mal *langsamer*. Ein ViT ist im Kern eine Kette großer
Matrixmultiplikationen, und darin ist die ONNX-Laufzeit stark.

## Was vorher war (2026-09-07, Vormittag)

**0.3.0, 272 Tests grün, öffentlich.** Seit heute gibt es die
**Fensteranwendung**: `wolkenernte fenster <Archiv>` öffnet ein Raster
mit Filtern, Suche und Einzelansicht, Videos laufen über
`QMediaPlayer`. Bei 14.767 Bildern steht das Fenster in einer halben
Sekunde.

**Was weiterhin fehlt, ist der eigentliche Zweck:** aus einer Wolke
ernten. Zugänge einrichten, auflisten und löschen geht – aber das Stück
zwischen `rclone.auflisten()` und `archiv.uebernehmen()` ist nicht
gebaut. Das ist der nächste Schritt, und er fängt bei **Nextcloud** an,
weil Stephan das erproben kann.

Am echten Bestand erprobt: 14.767 Bilder aus 47 GB Quellen, 29 GB im
Archiv, 13.605 bytegleiche Kopien übergangen, 1.332 Gruppen mit
derselben Aufnahme in mehreren Fassungen.

### Zwei Oberflächen, ein Fundament

`wolkenernte/bestandsliste.py` kennt weder Browser noch Fenster. Wer
etwas an Jahren, Alben, Suche oder Filtern ändert, ändert es **dort** –
sonst laufen die beiden Oberflächen auseinander. Was wirklich
oberflächenabhängig ist, steht in `web/seiten.py` (welche Formate ein
Browser darstellt) beziehungsweise `fenster/ansicht.py` (was Qt kann).

## Der Aufbau

```
wolkenernte/
├── anbieter.py     was bei welchem Anbieter geht - das Herzstück
├── takeout.py      ZIP-Archive lesen, ohne auszupacken
├── zuordnung.py    Bild ↔ Metadatendatei
├── metadaten.py    JSON auswerten
├── lokal.py        Ordner auf der Platte als Quelle
├── archiv.py       ins Archiv übernehmen
├── bestand.py      die Datenbank daneben
├── aehnlich.py     Wahrnehmungs-Fingerabdruck
├── doppelgaenger.py  Gruppen bilden und einstufen
├── rclone.py       rclone finden, starten, ansprechen
├── einrichten.py   Zugänge anlegen (das Frage-Antwort-Spiel)
├── zugang.py       dasselbe von der Kommandozeile
├── schlagworte.py  Schlagwörter ohne Modell (Datum, Name, Maße)
├── begriffe.py     die 75 deutschen Wörter, nach denen gesucht wird
├── bilderkennung.py  aus Ähnlichkeiten werden Wörter - ohne Fremdpakete
├── bildmodell.py   der Bildteil des Modells (braucht onnxruntime)
├── modelle.py      das Modell holen, prüfen, wiederfinden
├── bestandsliste.py  was im Archiv liegt - für beide Oberflächen
├── ernten.py / erfassung.py / nachweis.py   die drei Abläufe
├── fenster/        die Fensteranwendung (braucht PySide6)
└── web/            die Weboberfläche
```

## Fünf Entscheidungen, die man ohne den Grund umdreht

**Die Anbietertabelle steht im Code**, nicht in der Anleitung. Die
Oberfläche fragt sie, bevor sie einen Löschknopf zeigt; einen Knopf, der
nichts tut, soll es nicht geben. `darf_loeschen()` gibt für **unbekannte**
Kennungen `False` zurück – wer einen Anbieter hinzufügt und die Tabelle
vergisst, bekommt ein Programm, das zu wenig anbietet, nicht eines, das
zu viel verspricht.

**Keine Browser-Steuerung.** Sie wäre der einzige Weg, in Google Fotos
und iCloud Fotos zu löschen. Sie sitzt aber auf undokumentierten
internen Schnittstellen und verstößt bei Apple gegen die
Nutzungsbedingungen.

**Kopieren, nicht verschieben, und nichts löschen ohne Nachweis.** Der
Ablauf ist ernten → erfassen → pruefen, und erst danach darf eine Quelle
weg. `nachweis.py` rechnet dafür jede Datei einzeln nach; der
Größen-Vorfilter aus dem Ernten taugt zum Finden von Doppelgängern, nicht
zum Beweis der Vollständigkeit.

**Verknüpft wird über Größe und Prüfsumme, nicht über den Dateinamen.**
Bilder werden im Archiv umbenannt, wenn ihr Name belegt ist; ihr Inhalt
ändert sich nicht.

**pi-heif statt pillow-heif.** Gleicher Entwickler, gleicher Code, aber
die fertigen Pakete von pillow-heif enthalten x265 unter GPL.

**Die rclone-Schnittstelle ist Shell-Zugriff.** Das steht so in rclones
eigener Doku. Deshalb: nur `127.0.0.1`, Zugangsdaten bei jedem Start neu
gewürfelt und über die **Prozessumgebung** übergeben – die
Kommandozeile kann unter Linux jeder in `/proc` lesen – und
`--rc-no-auth` niemals. Drei Tests nageln das fest.

## Was das Ausprobieren gelehrt hat

Diese Fehler waren alle grün getestet, bevor echte Daten sie zeigten.

**Die 51-Zeichen-Regel für Takeout-Metadateien gilt nicht immer.** Sie
steht so in GooglePhotosTakeoutHelper; in einem Archiv vom 05.09.2026
kürzt Google gar nicht. Mit der Regel fanden 62,6 % der Bilder ihre
Metadaten, ohne sie 99,2 %. **Der Test, der das hätte fangen müssen,
behauptete das Gegenteil** – er verlangte ausdrücklich, dass kein
Kandidat länger als 51 Zeichen ist.

**SQLite kennt nur vorzeichenbehaftete 64-Bit-Zahlen.** Der
Fingerabdruck nutzt alle 64; die Hälfte aller Bilder brach den Lauf ab.

**Ein `replace(",", ".")` für Tausenderpunkte** lief über die ganze
HTML-Seite und zerlegte den `viewport`-Eintrag.

**Bilder ohne Aufnahmedatum** tragen den Zeitstempel der Übernahme und
standen deshalb in der Jahresliste unter »2026«.

**Ein Regex für Dateinamen** entfernte `_<Ziffern>` und machte aus
`IMG_20210110_113920` den Stamm `img` – jedes Kamerabild hätte denselben
gehabt, alles wäre »dieselbe Aufnahme« gewesen.

**Bei `operations/list` gehört der ganze Pfad in `fs`.** Ein erster
Anlauf trennte am Doppelpunkt und übergab den Rest als `remote`; rclone
antwortete »directory not found«, obwohl der Ordner existierte.

**Qt beachtet die EXIF-Aufnahmerichtung nicht von allein.**
`QPixmap.load()` zeigt hochkant gehaltene Bilder auf der Seite; im
Raster fiel es nicht auf, weil die Vorschaubilder von Pillow kommen.
`QImageReader.setAutoTransform(True)` kann es.

**`KeepAspectRatioByExpanding` schneidet nicht zu.** Das Raster riss
deshalb Lücken, obwohl `setUniformItemSizes` gesetzt war.

**Ein Muster ohne Ziffern trifft menschliche Dateinamen.** `"20"` in
der Handyliste steht in jeder Jahreszahl und in fast jeder UUID: 1.587
Bilder bekamen »Handy«, die keins waren. Dabei fiel ein zweiter Fehler
auf – wer vom Drohnenmuster eine Ziffer *direkt* nach `dji_` verlangt,
trifft `dji_fly_20241227_…` nicht, und das Handymuster erbt alle 479
Drohnenfotos, weil deren Name selbst eine Zeitangabe trägt.

**Und die eigenen Testbilder taugten nicht:** Synthetische Sägezahn-
muster werden beim Verkleinern zu gleichmäßigem Grau; beide Testbilder
bekamen denselben Fingerabdruck. Testmuster müssen **relativ zur
Bildgröße** definiert sein, sonst prüfen sie beim Skalieren etwas
anderes.

## Das Programmsymbol

`assets/icon-quelle.png` ist die Vorlage und wird **nicht nachgezeichnet**
– ein früherer SVG-Nachbau geriet zu einer eigenen Auslegung. Daraus
erzeugt `werkzeuge/symbole.py` alle Größen ab 48 Pixeln. Für 16, 24 und
32 gibt es eigene, ärmere SVG-Fassungen: Dort überleben weder
Perforation noch zwei Berggipfel.

## Vor der nächsten Veröffentlichung

Im Repo dürfen keine echten Albumnamen stehen. »Nordsee 2023« und »Mein
Viertel« sind Platzhalter; die ursprünglichen verrieten Wohnort und
Urlaubsziel. Bilddateien vor dem Übernehmen mit `-strip` von Metadaten
befreien.

## Tests

```
python3 -m unittest discover -s tests -t .
```

`tests/__init__.py` muss existieren, sonst findet `discover` nichts.
Der Testlauf ist auch mit `-W error::DeprecationWarning` grün – Warnungen
gelten als Fehler.

Die Fenstertests laufen über `QT_QPA_PLATFORM=offscreen`, brauchen also
keine Anzeige. Ohne PySide6 werden sie übersprungen, ohne rclone die
vier gegen das echte rclone.

**Zwei Fallen beim Schreiben von Tests**, beide schon zugeschnappt:
Testdateien entstehen im selben Augenblick, die Sortierung nach Zeit ist
dann beliebig – nie auf Stelle 0 festnageln. Und ein Testarchiv sollte
die Dateizeit setzen, weil das echte Archiv das Aufnahmedatum trägt.

**Gegenproben gehören dazu.** Grüne Tests sind verdächtig: Bei der
Zuordnung fielen vier Tests um, als die Klammer-Verschiebung
herausgenommen wurde; beim Takeout-Leser fünf, als nur das erste
Teilarchiv gelesen wurde. Solche Proben in einer **Kopie** machen, nicht
in der Arbeitskopie.

**Und Testwerte müssen so aussehen wie die echten.** Der erste Anlauf
für die Bilderkennung war grün und wertlos: Er prüfte mit einem
Vorsprung von 0,16, während ein solches Modell in Wirklichkeit für
*jede* Frage etwa 0,22 zurückgibt und der Sieger um Hundertstel vorn
liegt. Damit wäre jede Schwelle erfüllt gewesen, und die Tests hätten
nichts nachgewiesen. Jetzt stehen 0,008 und 0,03 im Test, und drei
Gegenproben belegen, dass er umfällt, wenn man Schwelle, Begrenzung
oder Streckung herausnimmt.

# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-09-09, Mittwoch)

**654 Tests grün.** Zwei Dinge kamen heute dazu.

**Videos haben Vorschaubilder.** ffmpeg als eigener Prozess, `-ss` vor
`-i`. Alle 424 liefern eines, Median 161 ms. Gegriffen wird bei einer
Sekunde, nicht am Anfang – gemessen: am Anfang 11 fast schwarze und 10
strukturlose Bilder, eine Sekunde später 6 und 2. Ein *Fehlschlag*
bekommt ein Gedächtnis (leere Datei im Zwischenspeicher), ein
*fehlendes ffmpeg* nicht. Im Fenster liegt seither ein Abspielzeichen
in der Ecke der Kachel; vorher war das Symbol die ganze Kachel.

**Zeitraum mit Kalender**, in beiden Oberflächen. Der Filter steht in
`bestandsliste.auswahl()`, das Lesen der Datumsangabe in
`zeitraum_lesen()`. Drei Entscheidungen, die man ohne den Grund
umdreht: Verglichen wird der **Tag** (`zeit.date()`), nicht der
Zeitpunkt – sonst fällt der Bis-Tag heraus. `2024` heißt als
Untergrenze 1. Januar, als Obergrenze 31. Dezember. Und der Filter ist
beim Start **aus**, weil sonst die 317 Bilder ohne Aufnahmedatum
wortlos verschwänden.

Zwei Fallen aus Qt, beide zugeschnappt: `setDateRange` **klemmt** den
Wert, und ein `setDate` auf den bereits stehenden Wert sendet **kein**
Signal – ein Test, der so den Filter einschalten wollte, prüfte nichts.
Und die Wochenendfarbe im Kalender setzt Qt im Code; keine Regel im
Stilblatt kommt dagegen an. Ihr reines Rot erreicht auf dunklem Grund
3,81, verlangt sind 4,5.

## Was vorher war (2026-09-07, Montagmittag)

**378 Tests grün.** Seit heute gibt es **Schlagwörter**, beide Hälften,
und beide sind am echten Bestand gemessen.

Die Hälfte ohne Modell – Jahreszeit, Tageszeit, Bildformat, Herkunft –
trifft 14.767 Bilder, nur 31 gehen leer aus. Die Hälfte, die ins Bild
schaut, läuft mit **6,4 Bildern je Sekunde** (39 Minuten für den ganzen
Bestand), vergibt 2,6 Wörter je Bild, und 1,8 % bekommen nichts.

`wolkenernte/daten/begriffe.npz` liegt im Repository. Zum Laufen fehlt
auf einem fremden Rechner nur `onnxruntime` (unter Manjaro:
`python-onnxruntime-cpu` aus `extra`) und beim ersten Aufruf das
335-MB-Modell, das sich selbst holt.

`wolkenernte verschlagworten <Archiv>` führt beides zusammen und
schreibt es in die Datenbank; beide Oberflächen zeigen, filtern und
suchen danach.

**Was als Nächstes ansteht:** die Begriffsliste weiter nachziehen –
»Ostern« liegt bei 7 % und meint dabei meist nur Frühlingsblumen,
»Schaf« bei 5 % ist verdächtig –, und Schlagwörter von Hand ergänzen
können.

### Drei Wörter, die das Modell nicht kann

Alle drei sahen im Kleinen brauchbar aus und fielen erst am **ganzen
Bestand** durch. Das Muster ist jedes Mal dasselbe: Wo ein exaktes
Zeichen existiert, ist es besser als jedes Modell.

| Wort | Was das Modell tat | Was es stattdessen sagt |
|---|---|---|
| Schwarzweiß | an 11 % aller Bilder, meist farbige | Farbsättigung – die echten liegen bei exakt 0 |
| Luftaufnahme | 36 von 480 Drohnenbildern; Anteil 0,04 gegen 0,03 bei allen anderen, also **keine** Trennung | der Dateiname (`dji_`) |
| Zeichnung | auch bei 0,90 gewöhnliche Handyfotos | nichts – das Wort ist ersatzlos weg |

**Und der Deckel ist eine Notbremse, kein Einstellwert.** Als
»Schwarzweiß« aus der Machart-Gruppe flog, schrumpfte die von fünf
Antworten auf vier, und die gerechnete Schwelle sprang auf 0,90 – die
Gruppe vergab danach an 1 % der Bilder noch ein Wort. Praktisch
gelöscht, ohne dass irgendwo etwas fehlschlug. Ein Test nagelt das
seither fest: **keine Gruppe darf am Deckel liegen.**

### Wo die beiden Hälften sich treffen

In `verschlagworten.fuer_ein_bild()`, und das ist mehr als Buchhaltung:
**Zwei Dinge kann das Modell schlechter als Rechnen.**

»Schwarzweiß« hing an 11 % aller Bilder, darunter lauter farbige. Die
Farbsättigung sagt es dagegen genau – die schwarzweißen Bilder tragen
nicht *wenig* Farbe, sondern **gar keine**, und ihre Dateinamen sagen
unabhängig davon dasselbe (`bw`, `SW`, `schwarzweiss`). Entschieden
wird nach 95 % der Pixel, nicht nach dem höchsten Wert: Ein einziges
rotes Pixel entschiede sonst über das ganze Bild.

»Sonnenaufgang« und »Sonnenuntergang« liegen bei 0,975 – ununterscheidbar
für das Modell und für einen Menschen, der nur das Bild sieht. Die Uhr
kann es. Das Modell fragt darum nur nach dem Phänomen, die Aufnahmezeit
vergibt den Namen.

### Aus der Wolke ernten – jetzt im Fenster

Menü **Wolke**: anmelden, Ordnerbaum durchsehen, holen, aufräumen.
Dasselbe gibt es als `wolkenernte aufraeumen` auf der Kommandozeile.

**Der Aufräumdialog zeigt Bilder, keine Dateinamen.** Eine Liste aus
vierhundert Zeilen `IMG_20240816_172342.jpg` liest niemand; vor Bildern
erkennt man sofort, wenn etwas dabei ist, das man behalten wollte. Die
Dateien liegen beim Prüfen ohnehin schon auf der Platte. Was nicht
nachgewiesen ist, lässt sich gar nicht erst ankreuzen – kein
abgeblendetes Häkchen, sondern gar keins.

**An einer echten Nextcloud erprobt** – anmelden, Ordner aussuchen,
holen, erfassen und der Aufräum-Probelauf. **Nicht erprobt ist
`--wirklich`**, also das scharfe Löschen.

Fünf Fehler fielen erst dort auf, obwohl alles gegen rclones
`local`-Backend grün war. Sie haben eine gemeinsame Form: **Etwas war
angelegt, beschrieben und kam nirgends an.** Der Haken »Unterordner
mitnehmen« (``recurse`` stand fest auf ``True``), der Schalter
``--ohne-unterordner`` (der Aufruf blieb unverändert), die
Doppelgängerprüfung über mehrere Läufe hinweg, die Herkunft bei
Cloudquellen – und fünf Minuten Stillstand, weil zum Suchen von 17
Bildern das ganze Archiv gerechnet wurde.

Daraus ist `tests/test_kommandozeile.py` entstanden: Für jeden Schalter
wird geprüft, **was beim Aufgerufenen ankommt**, nicht wie er heißt.

Vier Bedingungen fürs Löschen, alle vier müssen gelten: der Anbieter
erlaubt es; gleiche Größe **und** Prüfsumme im Archiv; die Prüfsumme
für *diesen* Lauf gerechnet, nicht aus der Datenbank geglaubt; und
`--wirklich`. Ein leeres Archiv bricht ab – wer zuerst aufräumt und
dann erntet, hätte sonst alles verloren.

**`darf_loeschen()` bekam bisher den Namen des Zugangs, nicht seine
Art.** Wer seine Nextcloud »meinewolke« nennt, fand damit keinen
Anbieter, und die Antwort war »nein«: sicher, aber unbrauchbar – es
hätte sich nie irgendwo etwas aufräumen lassen. `Dienst.art()` fragt
jetzt rclone, und rclone kennt auch nur `webdav`; erst das Feld
`vendor` macht daraus eine Nextcloud.

### Was die Messung gelehrt hat

Der erste Lauf war **unbrauchbar**, und zwar sichtbar: »Regen« hing an
60 % aller Bilder, »Zeichnung« an 37 %, und 147 von 200 Bildern trugen
die vollen fünf Wörter. Zwei Ursachen, beide grundsätzlich:

**Jede Gruppe musste einen Sieger küren.** Der Vergleich fragt nicht
*ob*, sondern *welches* – bei sechs Antworten hat die beste immer
einen ordentlichen Anteil, auch wenn keine passt. Dagegen hilft
`NICHTS`: »irgendein Foto« läuft in jeder Gruppe mit, taucht nie als
Schlagwort auf, und wenn es gewinnt, schweigt die Gruppe. »Regen« fiel
von 60 auf 20 %.

**Die Schwellen waren von Hand gesetzt.** Derselbe Anteil bedeutet in
einer Gruppe aus sechs Antworten etwas anderes als in einer aus
fünfundzwanzig. Jetzt wird gerechnet: `STRENGE / (n + 1)`, also
fast fünfmal so wahrscheinlich wie reines Raten. Eine Zahl statt fünf,
und sie wächst von selbst mit, wenn eine Gruppe kleiner wird.

Und zwei Begriffe hat die Messung **widerlegt**: »Sonnenaufgang« lag
bei 0,975 an »Sonnenuntergang« – das Modell kann sie nicht
unterscheiden, die Uhr könnte es; »Innenraum« lag bei 0,969 an
»Zuhause« und sagte weniger.

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
├── verschlagworten.py  der Durchlauf - hier treffen sich beide Hälften
├── begriffe.py     die 75 deutschen Wörter, nach denen gesucht wird
├── bilderkennung.py  aus Ähnlichkeiten werden Wörter - ohne Fremdpakete
├── bildmodell.py   der Bildteil des Modells (braucht onnxruntime)
├── modelle.py      das Modell holen, prüfen, wiederfinden
├── bestandsliste.py  was im Archiv liegt - für beide Oberflächen
├── ernten.py / erfassung.py / nachweis.py   die drei Abläufe
├── aufraeumen.py   in der Wolke löschen - der Schritt ohne Rückweg
├── bearbeiten.py   ein Bild an GIMP & Co. weiterreichen
├── symbole.py      das Programmsymbol, jetzt im Paket
├── fenster/        die Fensteranwendung (braucht PySide6)
│   └── wolken.py   anmelden, durchsehen, holen
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

**Ein Zeitstempel ohne Uhrzeit ist trotzdem einer.** Fast jedes Bild
bekam »Nachtaufnahme«. Die Verteilung der Aufnahmezeiten sagt warum:
Die Stunde 1 trägt 1.488 Aufnahmen, die Stunden 2 bis 5 zusammen 39.
Das ist Mitternacht UTC in mitteleuropäischer Zeit – 1.465 von 14.476
Bildern tragen gar keine Uhrzeit, nur ein Datum. Sichtbar wurde das
erst, als der Durchlauf über den ganzen Bestand lief; an einer
Stichprobe wäre es nicht aufgefallen.

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

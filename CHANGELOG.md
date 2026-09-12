[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md)

# Änderungsprotokoll

Alle nennenswerten Änderungen an WOLKENErnte. Neueste zuerst.

## Unveröffentlicht

**Das Fenster des Takeout-Laufs verschwindet nicht mehr unter der laufenden
Arbeit.** Es wartete zehn Sekunden und ging dann trotzdem – das Holen von neun
Gigabyte dauert länger, und der Faden gehört diesem Fenster: Qt hätte ihn
mitsamt seinem C++-Gegenstück unter der laufenden Arbeit weggeräumt, und ein
herrenloser Faden hätte weiter in ein Archiv geschrieben, das niemand mehr
beobachtet. Jetzt bleibt das Fenster stehen, bis der Schritt fertig ist.

Und der Abbruchknopf verspricht nur, was er halten kann: `ernten` kennt keinen
Abbruch, also greift er **zwischen** den Schritten. Er sagt das jetzt auch –
samt der Folge, dass die Bilder dann ohne Orte und Alben im Archiv liegen. Die
ZIP-Dateien bleiben in jedem Fall liegen.

## 0.4.5 – 2026-09-12

**Der Google-Takeout ist im Fenster angekommen.** Menü *Cloudspeicher →
Google-Takeout einlesen (ZIP-Dateien)*. Bis hierher war ausgerechnet der
wichtigste Anbieter derjenige, für den das Fenster nichts anzubieten hatte:
Google Fotos ist für fremde Programme verschlossen, der Export ist der einzige
Weg an den eigenen Bestand – und er ging nur auf der Kommandozeile.

**Erst nachsehen, dann anfassen.** Der Dialog sagt vor dem Lauf, was er bringt,
und das kostet fast nichts: Ein ZIP führt Größe und CRC-32 in seinem
Inhaltsverzeichnis, das Archiv hat dieselben Angaben in seiner Datenbank – und
die CRC-32 im ZIP ist bitgleich mit der, die WOLKENErnte selbst rechnet
(nachgemessen, nicht angenommen). Am echten Export:

```
• 6.587 Bilder und Videos in der Quelle, 5.939 davon verschieden
• 648 liegen in der Quelle doppelt – Google legt jedes Bild in einem Album zweimal ab
• 5.910 liegen schon im Archiv und werden übergangen
• 29 kämen hinzu (724 MB)
```

Neun Gigabyte, fünf Teilarchive, Antwort in **0,2 Sekunden**. Über die Dateien
gerechnet dauert dasselbe **130 Sekunden** – bei identischem Ergebnis; beide
Wege sind gegeneinander geprüft. Der Knopf heißt danach »29 holen«, nicht
»Einlesen«.

**Drei Wege zur Quelle**, weil neun Gigabyte selten dort liegen, wo man rät: ein
Pfadfeld, in das sich ein Pfad aus dem Dateimanager einfügen lässt, ein
Ordnerwähler, und ein Dateiwähler – der zeigt die angeschlossenen Datenträger
in seiner Seitenleiste und ist damit der Weg zu `/mnt/raid`, einer USB-Platte
oder einem Netzlaufwerk. Der Ordner wird gemerkt.

**Angehakt werden Exporte, nicht einzelne Teildateien.** Die wichtigste
Entscheidung in diesem Dialog. Google zerlegt den Export ohne Rücksicht auf
Zusammengehöriges; wer drei von fünf Teilen nimmt, verliert an jeder Nahtstelle
Datum und Ort – und merkt es nicht, weil die Bilder ja da sind. Die Teile
stehen aufklappbar darunter. Fremde ZIP-Dateien im selben Ordner bleiben
getrennt: Im Download-Ordner lag neben dem Takeout ein Faktura-Programm und ein
Spielstand.

**Der Lauf macht drei Schritte, nicht einen:** holen, **erfassen**, nachweisen.
Das Erfassen ist keine Kür – Orte, Titel und Albumzugehörigkeiten stehen
ausschließlich in den JSON-Dateien des Takeouts. Wer holt und die ZIPs dann
wegwirft, hat die Bilder und sonst nichts.

**Und die ZIP-Dateien dürfen danach weg** – unter vier Bedingungen, alle vier
müssen gelten, dieselbe Strenge wie beim Aufräumen in der Wolke: Der Lauf ist
durch; `erfassen` ist mitgelaufen; **jedes einzelne** Bild ist im Archiv
nachgewiesen, mit für diesen Lauf gerechneten Prüfsummen statt aus der
Datenbank geglaubten; und es gibt eine Rückfrage, bei der **»Behalten« die
Vorgabe** ist. Fehlt eine, bleiben die ZIPs liegen.

Dabei gefunden: **`ernten` schreibt keine Datenbankzeile**, das tut erst
`erfassen`. Die Vorschau meldet darum, wie viele Archivdateien sie nicht
berücksichtigen kann – sie irrt dann zur sicheren Seite und verspricht eher zu
viel Zuwachs, als ein Bild unterzuschlagen.

**Eine einzelne Takeout-ZIP-Datei geht jetzt auch.** Bisher musste man auf den
*Ordner* mit den ZIPs zeigen; wer die Datei selbst angab – das Erste, was man
probiert –, bekam einen Stapelabzug und die Meldung »ist kein Ordner«, obwohl es
sehr wohl ein Takeout-Archiv war.

**Die Geschwisterteile kommen dabei mit.** Wer `…-001.zip` nennt, meint den
Export, nicht das erste Zwanzigstel davon. Läse man nur dieses eine Teil,
fehlten an jeder Nahtstelle die Metadaten – Google zerlegt den Export ohne
Rücksicht auf Zusammengehöriges, ein Bild liegt im einen Archiv und seine JSON
im nächsten. Die Bilder wären da, Datum und Ort weg, und niemand merkte es.
Erkannt wird die Teilung am Namen; ein *anderer* Export im selben Ordner bleibt
draußen.

**Die Aufschriften »Jahr«, »Album« und »Schlagwort«** sind aus der
Fensterleiste verschwunden – der erste Eintrag jedes Kastens sagt dasselbe
(»Alle Jahre«, »Alle Alben«, »Alle Schlagwörter«), und das Suchfeld brauchte die
Breite: Sein Platzhalter war abgeschnitten. **Weggenommen ist nur das
Sichtbare.** Vorlesesoftware hörte sonst dreimal »Kombinationsfeld«
hintereinander; die Namen stehen jetzt in `accessibleName` und als Einblendung
unter dem Mauszeiger. Dieselben Namen bekamen auch das Suchfeld und die beiden
Datumsfelder – Qt verbindet eine Aufschrift nicht von selbst mit dem Feld
daneben.

## 0.4.4 – 2026-09-09

**Der eigene Zwischenspeicher zählt nicht mehr als Bestand.** In
`.wolkenernte/vorschau/` liegen tausende JPEG-Dateien, und für ein `rglob("*")`
sehen die aus wie Fotos. Drei Stellen im Programm haben sie mitgezählt:

* `erfassen` legte für jedes Vorschaubild eine Datenbankzeile an – am echten
  Bestand 1.470 Stück, die Datenbank behauptete danach 16.294 Bilder, wo 14.821
  liegen.
* `archiv_kennungen` hätte ein Vorschaubild als Nachweis dafür gelten lassen,
  dass ein Bild im Archiv liegt. **Daran hängt das Löschen in der Wolke.**
* `archiv_ist_leer` hätte ein Archiv, aus dem die Bilder verschwunden sind und
  in dem nur noch der Zwischenspeicher steht, für gefüllt gehalten – und damit
  genau die Notbremse gelöst, die den gefährlichsten Fall abfangen soll.

Jetzt entscheidet eine Stelle, `archiv.medien()`, und die lässt `.wolkenernte`
aus. Zwei Tests halten es fest.

**`wolkenernte erfassen` kommt ohne Quelle aus.** Dann wird nur das Archiv
selbst eingelesen: Jede Datei bekommt eine Datenbankzeile. Das braucht, wer
Bilder von Hand hineingelegt hat – ohne Zeile bekommen sie kein Schlagwort und
keinen Titel, und die Oberfläche zeigt sie zwar (das Dateisystem ist die
Wahrheit), aber die Datenbank kennt sie nicht. Am echten Bestand waren das 54
Bilder. Vorhandene Angaben werden dabei nicht angetastet, und es entstehen
keine Fundorte: Das Archiv als eigenen Fundort einzutragen wäre eine
Selbstverständlichkeit in vierzehntausend Zeilen.

**`ohne-datum` ist kein Album.** `albumname()` nimmt den letzten Ordner vor der
Datei; im Archiv heißt der für Bilder ohne Aufnahmedatum `ohne-datum`, und der
wäre als Album durchgegangen – mit dreihundert Bildern darin. Die Jahresordner
fängt die Jahresprüfung ab, dieser trägt keine Jahreszahl und rutschte durch.

## 0.4.3 – 2026-09-09

**`wolkenernte uhrzeit`** rechnet die EXIF-Uhrzeit in einem bestehenden
Archiv nach. Sie wurde bis einschließlich 0.4.1 als UTC gelesen, obwohl EXIF
die Ortszeit der Kamera trägt; der Zeitstempel in der Datei liegt deshalb um
den Abstand zu Greenwich daneben. 0.4.2 hat den Fehler behoben, aber nur für
neue Läufe – was vorher geerntet wurde, trägt ihn weiter. Ein zweiter Erntelauf
würde das auch richtigstellen, nur gibt es die Quellen oft nicht mehr, und das
Archiv ist die einzige Kopie.

**Erkannt wird nicht geraten, sondern nachgerechnet.** Aus dem EXIF *dieser
Datei* wird ermittelt, was die alte Fassung daraus gemacht hätte; nur wenn der
Zeitstempel damit auf die Sekunde übereinstimmt, wird er ersetzt. Bilder, deren
Datum aus einer Takeout-JSON kam, bleiben damit unangetastet, der Lauf lässt
sich beliebig wiederholen, und auf einem Rechner, der auf UTC steht, tut er gar
nichts.

Voreingestellt ist der **Probelauf** – wie beim Aufräumen ändert erst
`--wirklich` etwas. Jeder Lauf schreibt ein Protokoll und lässt sich mit
`--zurueck` vollständig aufheben.

Am eigenen Bestand gemessen: **5.017 von 14.105 Bildern** tragen den
Fingerabdruck, verschoben um eine oder zwei Stunden je nach Sommerzeit. An
einer Kopie von 40 echten Dateien ist der ganze Weg durchgespielt – die Inhalte
bleiben dabei byteweise unangetastet, angefasst wird nur der Zeitstempel.

**Der Ordner bleibt, wo er ist.** Beim Bauen sah es so aus, als müsse eine
Aufnahme vom 1. Januar 00:30 ins Vorjahr umziehen. Sie muss nicht:
`zielordner()` nimmt `.year` und `.month` des Zeitobjekts, und die zeigen die
Wanduhr, gleich welche Zeitzone daranhängt. Ein Test hält das fest, damit die
Annahme nicht unbemerkt kippt.

## 0.4.2 – 2026-09-09

**`wolkenernte neuigkeiten`** fragt bei GitHub nach, ob es eine neuere
Fassung gibt. Das ist der **einzige Netzaufruf**, den WOLKENErnte von
sich aus an einen fremden Server richtet, und er geschieht nur auf
ausdrückliches Verlangen – kein Aufruf beim Start, keiner im
Hintergrund. Übertragen wird nichts als die Anfrage.

Anlass war ein Fund am eigenen Rechner: Dort lief 0.3.0, während 0.4.0
und 0.4.1 längst veröffentlicht waren. Wer selbst baut, erfährt von
einer neuen Fassung sonst gar nichts.

Verglichen wird über Zahlen, nicht über Text – als Text wäre `0.10.0`
kleiner als `0.4.1`, und der Hinweis bliebe genau dann aus, wenn er am
nötigsten ist. Ist die eigene Fassung *höher* als die veröffentlichte,
sagt der Befehl das ausdrücklich: Dann arbeitet jemand aus dem
Quelltext, und »aktuell« wäre zwar nicht falsch, aber nichtssagend.

**Die EXIF-Uhrzeit stimmt wieder.** Das Aufnahmedatum aus dem Bild wurde als
UTC gelesen, obwohl EXIF die Ortszeit der Kamera trägt. Ein Foto von 15:44 stand
danach als »16:44« unter dem Bild – um genau den Abstand zu Greenwich, das ganze
Jahr über. Der Test, der das hätte fangen müssen, prüfte Jahr, Monat, Tag und
die Zeitzone und sah bei der **Stunde** weg. Betroffen sind nur Bilder, deren
Datum aus EXIF stammt, nicht die aus einer Takeout-JSON – und bei bereits
geernteten Archiven bleibt der falsche Zeitstempel in der Datei stehen, bis
erneut geerntet wird.

**Dateigrößen in der passenden Einheit.** Ein frisch geerntetes Archiv stand in
beiden Oberflächen als »0.0 GB« da, als wäre nichts darin. Jetzt kB, MB oder GB,
je nachdem – und gerade beim ersten Blick auf ein neues Archiv sagt das etwas.

**Bildschirmfotos** liegen unter [docs/bilder/](docs/bilder/README.md). Sie
zeigen ein **erfundenes** Archiv: gerechnete Aufnahmen, Platzhalter als
Albumnamen. Alles andere darauf ist echt – die Bilder laufen durch `ernten`,
`erfassen` und `verschlagworten` wie jeder andere Bestand. Erzeugt werden sie
mit `werkzeuge/bildschirmfotos.py`; beide Fehler oben sind dabei aufgefallen.

**Ein AUR-Paket** liegt unter `verpacken/aur/` bereit: PKGBUILD aus dem
veröffentlichten Quellarchiv statt aus dem Arbeitsverzeichnis, dazu
`.SRCINFO` und `nachziehen.py`, das bei jeder neuen Fassung das Archiv
holt, die Prüfsumme daraus rechnet und beides einträgt. Von Hand
vergisst man genau die Prüfsumme – das Paket baut dann trotzdem, aus
dem alten zwischengespeicherten Archiv, und es fällt erst auf, wenn ein
fremder Rechner es lädt.

## 0.4.1 – 2026-09-09

**Vorschaubilder für Videos.** Die 424 Videos zeigten bisher nur ein
Abspielsymbol; jetzt holt ffmpeg ein Einzelbild heraus – als eigener
Prozess, damit ein beschädigtes Video höchstens sich selbst mitreißt,
und mit `-ss` **vor** `-i`, damit gesprungen und nicht dekodiert wird.
Alle 424 liefern ein Bild, im Mittel in 161 ms.

Gegriffen wird bei einer Sekunde, nicht am Anfang: An 394 Videos
gemessen sind am Anfang 11 Vorschaubilder fast schwarz und 10 ohne jede
Struktur, eine Sekunde später nur noch 6 und 2. Die 30 Videos, die
kürzer sind, fallen auf den Anfang zurück. Ein Fehlschlag bekommt ein
Gedächtnis, damit nicht jedes Blättern erneut in die volle ffmpeg-Frist
läuft – ein *fehlendes* ffmpeg dagegen wird nicht festgeschrieben: Wer
es nachinstalliert, soll seine Videos danach sehen.

Im Fenster liegt jetzt ein Abspielzeichen in der Ecke der Kachel. Vorher
war das Symbol die ganze Kachel und die Unterscheidung geschenkt; mit
einem echten Standbild sähe ein Video sonst aus wie ein Foto.

**Zeitraum mit Kalender.** »Alle Bilder und Videos zwischen dem 24. und
dem 26. Dezember 2024«, in beiden Oberflächen. Im Fenster zwei Felder
mit Kalenderblatt, im Browser `type="date"` – beide Male der Kalender,
den das System ohnehin mitbringt, statt eines nachgebauten.

Beide Enden zählen mit: Verglichen wird der **Tag**, nicht der
Zeitpunkt. Wer »bis zum 30. Juni« sagt, meint den ganzen 30. Juni;
gegen dessen Mitternacht verglichen fiele der Tag vollständig heraus.
Eine unvollständige Angabe meint einen Zeitraum – `2024` ist als
Untergrenze der 1. Januar und als Obergrenze der 31. Dezember. Bilder
ohne bekanntes Aufnahmedatum bleiben draußen; ihr Zeitstempel ist der
Zeitpunkt der Übernahme und wäre eine falsche Antwort.

Der Filter ist beim Start **aus**. Wäre er es nicht, verschwänden die
317 Bilder ohne Aufnahmedatum wortlos. Er schaltet sich aber von selbst
ein, sobald jemand ein Datum ändert – ein Datum zu wählen und nichts
geschehen zu sehen, wäre die schlechtere Antwort.

Nebenbei: Qts Wochenendrot im Kalender erreicht auf dem dunklen Grund
nur einen Kontrast von 3,81 – für Text verlangt WCAG 4,5. Jetzt steht
dort `ROT_HELL` aus der Palette mit 7,07.

## 0.4.0 – 2026-09-07

**Schlagwörter.** Jedes Bild bekommt höchstens fünf, und sie kommen aus
zwei Quellen. Die eine kostet nichts: Jahreszeit, Tageszeit, Bildformat
und Herkunft lassen sich aus Datum, Dateiname und Bildmaßen ableiten –
14.767 Bilder, nur 31 gehen leer aus. Die andere schaut ins Bild, mit
einem CLIP-Modell über ONNX Runtime, und läuft mit 4,5 Bildern je
Sekunde offline auf der Hauptrecheneinheit.

**Die Frage ist englisch, die Antwort deutsch.** Das Modell versteht nur
Englisch, aber unsere Fragen stehen fest – also wird der Textteil
**einmal beim Bauen** gerechnet und liegt als 268 KB bei. Auf dem
Rechner des Anwenders läuft nur der Bildteil. Kein mehrsprachiges
Modell (die kosten 250 MB bis 1,6 GB extra), keine Übersetzung, kein
Übersetzungsfehler.

Der erste Lauf über 400 echte Bilder war unbrauchbar: »Regen« hing an
60 % aller Bilder. Zwei Ursachen, beide grundsätzlich – jede Gruppe
musste einen Sieger küren (jetzt läuft eine stumme Antwort mit, und
gewinnt sie, schweigt die Gruppe), und die Schwellen waren von Hand
gesetzt (jetzt gerechnet, relativ zum Zufall). Danach: 2,6 Wörter je
Bild, häufigstes 13,5 %.

Drei Wörter hat die Messung **widerlegt** und sie sind heraus:
»Schwarzweiß« (die Farbsättigung sagt es exakt), »Luftaufnahme« (bei
480 Drohnenbildern keinerlei Trennung vom Rest) und »Zeichnung« (traf
auch bei 0,90 gewöhnliche Handyfotos).

**Aus der Cloud ernten – im Fenster.** Ein Menü »Cloudspeicher«:
anmelden, Ordnerbaum durchsehen, holen, aufräumen. Die Anbieterliste
zeigt vorher, was jeder kann – sehen, holen, löschen – und nennt bei
Google Fotos und Proton Fotos den Grund, warum es dort nicht geht,
statt den Eintrag wegzulassen. Die Rückfragen kommen von rclone selbst,
also gibt es nichts, was je Anbieter nachzupflegen wäre.

**Aufräumen mit den Bildern vor Augen.** Vier Bedingungen, alle vier
müssen gelten: Der Anbieter erlaubt es, die Datei liegt mit gleicher
Größe **und** Prüfsumme im Archiv, die Prüfsumme wurde für *diesen*
Lauf gerechnet, und der Anwender hat bestätigt. Was nicht nachgewiesen
ist, lässt sich gar nicht erst ankreuzen. Ein leeres Archiv bricht ab –
wer zuerst aufräumt und dann erntet, hätte sonst alles verloren.

**An einer echten Nextcloud erprobt**, und das war der Punkt: Fünf
Fehler fielen erst dort auf, obwohl alles gegen rclones `local`-Backend
grün war. Sie haben eine gemeinsame Form – *etwas war angelegt,
beschrieben und kam nirgends an*: der Haken »Unterordner mitnehmen«,
der Schalter `--ohne-unterordner`, die Doppelgängerprüfung über mehrere
Läufe hinweg, die Herkunft bei Cloudquellen. Dazu fünf Minuten
Stillstand, weil zum Suchen von 17 Bildern das ganze Archiv gerechnet
wurde – jetzt nur die passenden Größen, 296 Sekunden gegen weniger als
eine.

**Ein .deb für Debian und Ubuntu**, gebaut aus dem Wheel mit
`dpkg-deb`. Nach `dist-packages`, mit Debians eigenen Paketnamen, und
rclone ohne Versionsangabe unter *Empfohlen*, weil Debian stable eine
zu alte Fassung liefert.

**Und das Symbol kommt endlich mit.** Es lag unter `assets/` und gehört
damit nicht zum Python-Paket; wer über pip installierte, bekam ein
Fenster ohne Symbol – ohne Fehlermeldung.

Rechte Maustaste im Raster: Bilder an GIMP, darktable oder ein anderes
Programm weiterreichen. Angeboten wird nur, was wirklich installiert
ist.

561 Tests.

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

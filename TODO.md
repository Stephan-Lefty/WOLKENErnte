[Deutsch](TODO.md) | [English](TODO.en.md) | [Übersicht](README.md) | [Änderungsprotokoll](CHANGELOG.md) | [Anleitungen](docs/README.md)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes wird
nicht gelöscht, sondern nach unten verschoben – mit dem Datum, an dem es fertig
wurde.

## Offen

### Der eigentliche Zweck: aus einer Wolke ernten

Ernten, anmelden und aufräumen stehen (siehe *Erledigt*), und an einer echten
Nextcloud sind Anmelden, Durchsehen, Holen, Erfassen und der Aufräum-Probelauf
gelaufen. Was fehlt, ist der letzte Schritt.

- [ ] **Das scharfe Löschen ist noch nie gelaufen.** Anmelden, Ordner aussuchen,
  holen und der Probelauf sind an einer echten Nextcloud erprobt; `--wirklich`
  fehlt. Dafür braucht es einen eigenen Probeordner in der Cloud, nicht einen,
  in dem gebrauchte Dateien liegen.
- [ ] **Ein Bild von Hand aus dem Archiv nehmen.** Wer etwas geerntet hat, das
  er dort nicht haben will – fremde Grafiken zwischen Familienfotos –, kann
  es bisher nur im Dateimanager löschen, und die Datenbank weiß nichts davon.
- [ ] Fortschritt über `core/stats`, lange Aufträge asynchron mit
  `_async: true` und `job/status`. Der Ernter zeigt bisher die Zahl der
  Dateien, nicht die Übertragungsrate.

**Die Reihenfolge der Anbieter:** Zum Erproben stehen Nextcloud, Proton Drive
und Google Fotos bereit. Diese drei zuerst – alles andere wäre Code, der nur
der Papierlage nach funktioniert. Danach OneDrive, Dropbox und pCloud, die sich
denselben Ablauf über die Browser-Anmeldung teilen; zuletzt iCloud Fotos, wo
ohnehin nur die Hälfte geht.

- [ ] Das Feld `erprobt` in `anbieter.py` benutzen, sobald ein Anbieter
  tatsächlich gelaufen ist – und in beiden Oberflächen kenntlich machen, was
  bisher nur eingebaut und was wirklich erprobt ist.

### Schlagwörter

Beide Hälften laufen und sind gemessen (siehe *Erledigt*). Was fehlt, ist der
Weg von dort in die Datenbank und in die Oberflächen.

- [ ] **»Ostern« nachprüfen.** Es liegt bei 5,8 % und meint dabei meist nur
  Frühlingsblumen. Wie bei »Zeichnung« und »Luftaufnahme« gilt: erst messen,
  dann entscheiden – ein Wort, das die Hälfte danebenliegt, gehört heraus.
- [ ] **Schlagwörter von Hand ergänzen und wegnehmen.** Bisher kommen sie
  ausschließlich aus dem Durchlauf; wer eines falsch findet, kann nichts tun.
  Eine eigene Herkunft (`"hand"`) dafür, die kein Durchlauf je überschreibt.
- [ ] **Videos bekommen keine Schlagwörter aus dem Bild.** Sobald ffmpeg ein
  Einzelbild liefert, ändert sich das – die Buchführung ist schon darauf
  eingerichtet und lässt Videos auf der Stufe »abgeleitet« stehen.
- [ ] Modell erst holen, wenn der Anwender die Bilderkennung wirklich will. Ein
  Programm, das beim ersten Start ungefragt 335 MB zieht, ist unhöflich.
- [ ] Prüfen, ob die INT8-Fassung reicht: viermal kleiner (85 statt 335 MB),
  2,4-mal schneller. Ob die Treffer darunter leiden, ist für *Suche nach
  Ähnlichkeit* schlecht belegt – also selbst messen.

### Fensteranwendung – was noch fehlt

- [ ] **Vollbild** mit der Leertaste, ohne Kopfzeile.
- [ ] **Löschkorb**: Mehrfachauswahl im Raster, Entf sammelt, ein zweiter
  Schritt führt aus. Der Löschknopf erscheint nur, wo
  `anbieter.darf_loeschen()` es erlaubt – bei den anderen steht der Grund,
  nicht ein ausgegrauter Knopf.
- [ ] **Doppelgängeransicht** wie in der Weboberfläche, mit der Einstufung
  »dieselbe Aufnahme« gegen »ähnlich«.
- [ ] **HEIC über pi-heif** als Pillow-Erweiterung; Qt bringt außerhalb von
  macOS kein HEIF-Modul mit. Bisher zeigt die Einzelansicht dort das
  Vorschaubild.

### Aufnahmedatum

- [x] **Bereits geerntete Archive nachziehen.** — *Erledigt am 2026-09-09:
  `wolkenernte uhrzeit`, Probelauf voreingestellt, mit Protokoll und
  `--zurueck`. Erkannt wird über den Fingerabdruck der alten Rechnung, nicht
  über eine Vermutung; Bilder aus Takeout-JSONs bleiben deshalb unangetastet
  und der Lauf ist beliebig wiederholbar. Dabei fiel auf, dass der **Ordner
  nie betroffen war**: `zielordner()` liest `.year`/`.month` des Zeitobjekts,
  und die zeigen die Wanduhr.*
- [x] **Den Lauf am eigenen Bestand scharf schalten.** — *Erledigt am
  2026-09-09: 5.017 von 14.105 Bildern richtiggestellt, Verschiebung −1 h oder
  −2 h je nach Sommerzeit. Nachgeprüft: Bei allen 5.017 stimmt die Dateizeit
  jetzt mit der EXIF-Wanduhr überein, der Nachlauf findet 0, und in der
  Datenbank sind 5.002 Zeilen nachgezogen. Das Protokoll liegt unter
  `.wolkenernte/uhrzeit-reparatur.jsonl`.*
- [x] **Dateien im Archiv ohne Datenbankzeile.** — *Erledigt am 2026-09-09:
  `wolkenernte erfassen <Archiv>` kommt jetzt ohne Quelle aus und liest nur
  das Archiv ein. 54 Bilder nachgetragen, danach 0 ohne Zeile;
  `verschlagworten` hat ihnen Schlagwörter gegeben (57 → 3, und die drei sagt
  auch das Modell nichts). Orte, Titel, Alben, Favoriten und Fundorte blieben
  dabei Zahl für Zahl gleich.*
- [x] **Der Zwischenspeicher galt als Bestand.** — *Erledigt am 2026-09-09:
  Beim ersten Lauf legte `erfassen` für 1.470 Vorschaubilder eine
  Datenbankzeile an. Dieselbe Verwechslung steckte in `archiv_kennungen` (dem
  Nachweis, an dem das Löschen in der Wolke hängt) und in `archiv_ist_leer`
  (der Notbremse davor). Jetzt entscheidet `archiv.medien()` an einer Stelle.*
- [ ] **Videos aus einem gewöhnlichen Ordner haben kein Datum.** EXIF gibt es
  bei ihnen nicht, und das Feld `creation_time` im Container liest niemand.
  Ohne Takeout-JSON daneben landet jedes Video in `ohne-datum`. `ffprobe` kann
  es auslesen, und ffmpeg ist ohnehin schon eine Empfehlung.

### Bilder und Videos

- [ ] Vorschaubilder: erst das **eingebettete Vorschaubild** versuchen, das in
  HEIC und JPEG ohnehin steckt – rund zehnmal schneller, als das Vollbild zu
  dekodieren.
- [ ] Zwischenspeicher nach dem freedesktop-Muster
  (`$XDG_CACHE_HOME/thumbnails/`), damit der Dateimanager des Anwenders und
  WOLKENErnte sich denselben teilen.
- [x] **Vorschaubilder für Videos** mit ffmpeg als eigenem Prozess, `-ss`
  **vor** `-i` (Sprung vor dem Dekodieren). Ein beschädigtes Video reißt so das
  Programm nicht mit. — *Erledigt: alle 424 Videos liefern ein Bild, Median
  161 ms, der ganze Bestand in 71 Sekunden. Gegriffen wird bei einer Sekunde,
  nicht am Anfang (dort sind 11 Bilder fast schwarz statt 6 und 10 ohne
  Struktur statt 2); die 30 kürzeren Videos fallen auf den Anfang zurück. Die
  41 Videos mit Drehwinkel kommen richtig herum heraus.*
- [ ] **HDR-Material braucht Tonwertabbildung.** Für diesen Bestand
  unkritisch – er enthält nur fünf HEVC-Dateien –, aber wer HDR-Aufnahmen
  geschickt bekommt, sieht graue Vorschaubilder. Vorher mit `ffprobe` auf
  `color_transfer` prüfen; bei SDR-Material verschlechtert dieselbe Kette das
  Bild.

### Doppelgänger

- [ ] **Vorschaubilder der Anbieter hashen, nicht die Originale.** Drive,
  OneDrive und Dropbox liefern Vorschauen über ihre Schnittstellen; ein
  Wahrnehmungs-Hash über ein 256-Pixel-Bild erkennt »dasselbe Foto, anders
  komprimiert« praktisch genauso gut. Das erspart den Download von
  zehntausenden Dateien, bevor der Anwender überhaupt etwas entschieden hat.
- [ ] **Live Photos sind ein Paar aus HEIC und MOV.** Wer sie nicht als eines
  erkennt, meldet lauter Doppelgänger, die keine sind. Erkennung über den
  `ContentIdentifier`, nicht über den Dateinamen.

### Google Takeout

- [ ] Beim Löschen ehrlich sein: Anleitung anzeigen, wie im Browser aufgeräumt
  wird. **Keine Browser-Steuerung.** Sie sitzt auf undokumentierten internen
  Schnittstellen, bricht ohne Vorwarnung, und bei Apple verstößt sie
  ausdrücklich gegen die Nutzungsbedingungen.

### Ausliefern

**Grundsatz:** Was WOLKENErnte braucht, bringt es mit oder lässt es vom
Paketverwalter mitbringen. Niemand soll rclone von Hand herunterladen.

- [ ] **Das AUR-Paket hochladen.** *Zurückgestellt am 2026-09-09.* Alles liegt
  fertig unter `verpacken/aur/` und steht auf 0.4.2: PKGBUILD und `.SRCINFO`
  sind nachgezogen, die Prüfsumme ist aus dem veröffentlichten Quellarchiv
  gerechnet, und `makepkg -f` baut daraus sauber durch. Es fehlt **nur** der
  AUR-Zugang: der öffentliche SSH-Schlüssel im Konto auf aur.archlinux.org,
  dann `git clone ssh://aur@aur.archlinux.org/wolkenernte.git`, die beiden
  Dateien hineinkopieren und pushen. Danach kommt jede neue Fassung mit
  `pamac update` von selbst. **Der Anlass:** Auf dem Rechner des Entwicklers
  lief 0.3.0, während 0.4.0 und 0.4.1 längst veröffentlicht waren – wer selbst
  baut, erfährt von einer neuen Fassung sonst gar nichts.
- [ ] **Auf PyPI veröffentlichen**, damit `pip install -U wolkenernte` geht.
  Braucht ein Konto und einen Token. Für alle, die kein Arch fahren, ist das
  der übliche Weg.
- [ ] **Ein APT-Verzeichnis** wäre das Gegenstück für Debian und Ubuntu – heute
  ist das `.deb` eine Datei am Release, die niemand aktualisiert. Aufwand:
  eigene Signierschlüssel und ein Ort zum Ablegen.

- [ ] **rclone unter Linux als Paketabhängigkeit** eintragen, sobald der Abruf
  eingebaut ist – vorher wäre es eine Zusage, die das Programm nicht einlöst.
  **Mindestens 1.75.0.** Arch und Manjaro sind aktuell genug; **bei Debian
  stable ist das offen.** Liegt dort eine ältere Fassung, muss rclone ins .deb.
- [ ] **rclone unter Windows mitliefern.** Kein Paketverwalter, also liegt
  `rclone.exe` im Programmordner. Rund 70 MB.
- [ ] **ffmpeg über `imageio-ffmpeg`.** Bringt die Binärdatei mit, steht unter
  BSD, keine Systeminstallation auf keinem der drei Systeme.
- [ ] **Beim Start prüfen, was da ist**, und im Klartext sagen, was fehlt –
  statt mitten im Abruf abzubrechen mit einer Meldung, die nach einem Defekt
  des Rechners aussieht.
- [ ] **Windows: `.exe`** nach dem Muster von `MailBurg/werkzeuge/mailburg.spec`,
  aber als **Ordner** (`--onedir`), nicht als einzelne Datei. PySide6 steht
  unter LGPLv3, und die verlangt, dass der Anwender die Bibliothek austauschen
  kann.
- [ ] **Das .deb auf einem echten Debian ausprobieren.** Gebaut und aus dem
  ausgepackten Paket gestartet ist es; installiert wurde es noch nie – hier
  steht kein Debian.
- [ ] **rclone in Debian stable ist zu alt** (unter 1.75.0). Entweder rclone
  ins .deb legen oder auf trixie-backports verweisen.

### Später

- [ ] Windows und macOS überhaupt erst einmal ausprobieren. Bisher ist nichts
  davon dort gelaufen; die Angaben in `pyproject.toml` sagen das auch so.
  `werkzeuge/videoprobe.py` beantwortet die Videofrage dort in einer Minute.
- [ ] Proton Drive im Auge behalten: Das offizielle SDK gibt es seit Januar
  2026, aber ohne Anmeldemodul. Sobald das kommt, ist es der saubere Weg – und
  vielleicht auch der erste Zugang zu Proton Fotos.

## Erledigt

### Zeitraum mit Kalender (2026-09-09)

- [x] **»Alles zwischen … und …«** in beiden Oberflächen, Bilder und Videos
  gleichermaßen. Der Filter steht im Fundament (`bestandsliste.auswahl`), nicht
  in einer Oberfläche – sonst laufen die beiden auseinander.
- [x] **Der Kalender kommt vom System**: im Fenster `QDateEdit` mit
  Kalenderblatt, im Browser `type="date"`. Ein nachgebauter wäre mehr Code und
  schlechter bedienbar.
- [x] **Beide Enden zählen mit.** Verglichen wird der Tag, nicht der Zeitpunkt –
  sonst fiele der Bis-Tag vollständig heraus.
- [x] **Eine unvollständige Angabe meint einen Zeitraum**: `2024` ist als
  Untergrenze der 1. Januar, als Obergrenze der 31. Dezember. Der Februar wird
  gerechnet, nicht geraten.
- [x] **Beim Start ist der Filter aus** – sonst verschwänden die 317 Bilder ohne
  Aufnahmedatum wortlos. Er schaltet sich ein, sobald jemand ein Datum ändert.
- [x] **Ein unlesbares Datum wird gesagt**, nicht übergangen; sonst hielte man
  den ganzen Bestand für das Ergebnis seines Zeitraums.
- [x] **Qts Wochenendrot ersetzt**: 3,81 Kontrast auf dunklem Grund, verlangt
  sind 4,5. Jetzt `ROT_HELL` mit 7,07.
- [x] Neun Gegenproben, jede fällt auf genau die Tests, die sie treffen soll.

### Ein .deb für Debian (2026-09-07)

- [x] **`verpacken/debian/deb-bauen.py`** baut aus dem Wheel ein Paket mit
  `dpkg-deb` – ohne debhelper, ohne Debian-Rechner.
- [x] **Nach `dist-packages`**, nicht `site-packages`; sonst findet das
  System-Python nichts.
- [x] **Debian-Paketnamen**: `python3-pil`, `python3-pyside6.qtwidgets`.
- [x] **Pflicht ist nur `python3`** – PySide6 zöge auf einem Server hundert
  Megabyte Qt nach sich.
- [x] **copyright, changelog.Debian.gz und md5sums**, wie die Policy es
  verlangt; **kein `postinst`**, weil sie das verbietet.
- [x] **Ausgepackt und daraus gestartet** – Symbole, Begriffsdatei und
  Menüeintrag geprüft.

### An einer echten Nextcloud erprobt (2026-09-07)

Das meiste davon fiel erst dort auf – gegen rclones `local`-Backend lief alles.

- [x] **Der Haken »Unterordner mitnehmen« tat nichts.** `recurse` stand fest
  auf `True`; wer in einem Ordner aufräumen wollte, bekam alles darunter.
- [x] **`--ohne-unterordner` stand in der Hilfe und kam nirgends an.** Seither
  gibt es `tests/test_kommandozeile.py`: Für jeden Schalter wird geprüft, was
  beim Aufgerufenen ankommt, nicht wie er heißt.
- [x] **Fünf Minuten Stillstand vor dem Aufräumen.** Das ganze Archiv wurde
  durchgerechnet, um 17 Bilder zu suchen. Jetzt nur die passenden Größen: 296
  Sekunden gegen weniger als eine.
- [x] **Dasselbe Bild aus zwei Clouds kam zweimal ins Archiv.** Der
  Doppelgängerschutz galt nur innerhalb eines Laufs.
- [x] **`erfassen` versteht Cloudzugänge** – vorher gab es für eine Cloud keinen
  Weg, Orte, Titel, Alben und Fundorte festzuhalten. Bei einer Cloud wiegt das
  schwerer: Nach dem Aufräumen ist sie leer.
- [x] **Das Fenster erfasst gleich beim Holen mit**, weil es dort keinen
  zweiten Schritt gibt.
- [x] **Nachgewiesen: alle 21.044 Bilder aus dem Google-Fotos-Ordner sind im
  Archiv.** `wolkenernte pruefen`, 13,3 Minuten.

### Aus der Wolke ernten, im Fenster (2026-09-07)

- [x] **Eine Quelle nach dem Muster von `lokal.py`**, die über rclone liest –
  `wolke.py`, mit demselben Ablauf wie bisher.
- [x] **Ein Menü »Wolke«**: Nextcloud anmelden, Ordnerbaum durchsehen, holen.
  Der Baum lädt erst beim Aufklappen nach und zeigt die Zahl der Bilder je
  Ordner.
- [x] **Gespeichert wird erst, wenn die Verbindung steht.** Ein Zugang, der nur
  auf dem Papier existiert, fällt sonst viel später auf.
- [x] **Der Erntelauf im Hintergrundfaden**, mit Fortschritt und Abbruch.
- [x] **`wolkenernte aufraeumen`** – löschen, aber nur was nachweislich im
  Archiv liegt: gleiche Größe, gleiche Prüfsumme, für diesen Lauf gerechnet,
  und nur mit `--wirklich`.
- [x] **`Dienst.art()`**, weil `darf_loeschen()` bisher den *Namen* des Zugangs
  bekam statt seiner Art. Wer seine Nextcloud »meinewolke« nennt, hätte nie
  irgendwo aufräumen können.
- [x] **Das Aufräumen im Fenster**, mit Vorschaubildern: Was nicht
  nachgewiesen ist, lässt sich gar nicht erst ankreuzen, und der rote
  Löschknopf ist ausdrücklich nicht der voreingestellte.

### Schlagwörter (2026-09-07)

- [x] **Jahreszeit, Tageszeit, Bildformat und Herkunft** aus dem ableiten, was
  ohnehin bekannt ist. Am echten Bestand: 14.767 Bilder, nur 31 ohne jedes
  Schlagwort.
- [x] **Höchstens fünf je Bild.** Wer zwanzig vergibt, beschreibt nichts mehr,
  sondern verrauscht die Suche. Bei Platzmangel hat Erkanntes Vorrang vor
  Abgeleitetem – die Jahreszeit lässt sich aus dem Datum nachrechnen, das
  ohnehin danebensteht.
- [x] **Kamera und Handy getrennt**, nachdem ein erster Anlauf »Kamera« an
  8.589 von 14.767 Bildern gehängt hatte.
- [x] **Die Ziffern gehören zum Muster.** `"20"` in der Handyliste traf jede
  Jahreszahl und fast jede UUID: 1.587 Fehlgriffe.
- [x] **Die Begriffsliste für die Bilderkennung** – 75 deutsche Schlagwörter in
  fünf Gruppen, mit englischen Fragen daneben.
- [x] **Die Auswertung**, die aus Ähnlichkeiten Schlagwörter macht – Gruppen
  statt einer langen Liste, Schwelle je Gruppe, kein Fremdpaket nötig.
- [x] **Das Modell holen, prüfen, wiederfinden** – mit SHA-256, ohne zweiten
  Griff ins Netz, unter `user_data_dir`.
- [x] **Den CLIP-Zerleger selbst gebaut** statt `tokenizers` (Rust, unter Arch
  nicht paketiert) zu verlangen. Gegen den echten gehalten: 455 Sätze, null
  Abweichungen.
- [x] **`wolkenernte/daten/begriffe.npz` erzeugt** – 280 KB, liegt im
  Repository. Zum Laufen fehlt nur noch `onnxruntime`.
- [x] **An 400 echten Bildern gemessen, und der erste Lauf war unbrauchbar:**
  »Regen« an 60 % aller Bilder, 147 von 200 Bildern mit den vollen fünf
  Wörtern. Zwei Ursachen behoben – die stumme Antwort »irgendein Foto«, die
  eine Gruppe schweigen lässt, und die **gerechnete** statt gesetzte Schwelle.
  Danach: 2,6 Wörter je Bild, 1,8 % ohne, häufigstes Wort 13,5 %.
- [x] **6,4 Bilder je Sekunde** auf der Hauptrecheneinheit, solange die Bilder
  im Zwischenspeicher liegen; über den ganzen Bestand hinweg ist die Platte der
  Engpass, nicht die Rechnung.
- [x] **Der Durchlauf** `wolkenernte verschlagworten`, der beides zusammenführt
  und in die Datenbank schreibt – mit Fortschritt und einem Merker, damit der
  zweite Lauf nur das Fehlende anfasst.
- [x] **In beiden Oberflächen**: anzeigen, filtern, suchen. Der Unterbau steht
  einmal in `bestandsliste.py`.
- [x] **Ohne Uhrzeit keine Tageszeit.** 1.465 von 14.476 Bildern tragen nur ein
  Datum; »Nachtaufnahme« fiel damit von 2.004 auf 539.
- [x] **»Schwarzweiß« wird gerechnet, nicht geraten** – aus der Farbsättigung.
- [x] **»Sonnenaufgang« nach der Uhr**, weil das Modell ihn vom Untergang nicht
  unterscheiden kann (0,975).

### Die Fensteranwendung (2026-09-07)

- [x] **PySide6** als Kür-Abhängigkeit, Aufruf über `wolkenernte fenster`.
- [x] **Rasteransicht virtualisiert** – das Modell liefert sofort einen
  Platzhalter und lädt im Hintergrund nach. Bei 14.767 Bildern steht das
  Fenster in einer halben Sekunde.
- [x] Vorschaubilder im Hintergrund über `QThreadPool`, gemeinsamer
  Zwischenspeicher mit der Weboberfläche.
- [x] **Videos mit `QMediaPlayer`** – geprüft mit `werkzeuge/videoprobe.py`:
  H.264, HEVC und VP9 spielen ab, mit tatsächlich ankommenden Einzelbildern.
  libmpv wird nicht gebraucht; python-vlc wäre ohnehin ausgeschieden, weil es
  unter Wayland keine Einbettung hat.
- [x] Tastatursteuerung: Pfeiltasten zum Blättern, Escape zurück.
- [x] Filter nach Jahr und Album, Suche über Namen, Titel, Alben und Datum.

### Der Anschluss an rclone (2026-09-06)

- [x] rclone finden, Fassung prüfen, als Dienst starten.
- [x] **Abgesichert**: nur `127.0.0.1`, Zugangsdaten je Start neu gewürfelt und
  über die Prozessumgebung übergeben – die Kommandozeile kann unter Linux jeder
  in `/proc` lesen. `--rc-no-auth` niemals. Drei Tests nageln das fest.
- [x] Zugänge einrichten über rclones Frage-Antwort-Ablauf, mit dem dritten
  Zustand, den rclones eigenes Beispielprogramm vergisst.
- [x] `wolkenernte zugang nextcloud` mit Adressprüfung und Probe.
- [x] Vier Tests gegen das echte rclone über das `local`-Backend.

### Fundament (2026-09-05 und 2026-09-06)

- [x] **Beide Oberflächen teilen sich den Kern.** Die Auswertung liegt in
  `wolkenernte/bestandsliste.py` und kennt keine Oberfläche.
- [x] Takeout-Archive lesen, ohne auszupacken, über alle Teilarchive hinweg.
- [x] Bild und Metadatendatei zuordnen, mit Sicherheitsangabe.
- [x] Ins Archiv übernehmen, nach Aufnahmedatum geordnet, Doppelgänger nur
  einmal.
- [x] Die Datenbank daneben: Orte, Titel, Alben, Favoriten.
- [x] Nachweisen, dass jedes Bild angekommen ist – vor jedem Löschen.
- [x] Doppelgänger über einen eigenen Wahrnehmungs-Fingerabdruck, eingestuft
  nach »dieselbe Aufnahme« und »ähnlich«.
- [x] Weboberfläche mit Raster, Suche und Doppelgängeransicht.
- [x] **Namen prüfen lassen.** Vier Vorschläge verworfen: *CloudFlow* (der
  Laufschuh macht ihn unauffindbar), *MediaDock* (aktive deutsche Wortmarke),
  *MediaMover* (Allerweltsbegriff), *Heimholer* (NS-Konnotation).
- [x] **Prüfen, was bei den Anbietern überhaupt geht** – Ergebnis in
  `wolkenernte/anbieter.py` und `docs/anbieter.md`.

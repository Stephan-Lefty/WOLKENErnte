[Deutsch](TODO.md) | [English](TODO.en.md) | [Übersicht](README.md) | [Änderungsprotokoll](CHANGELOG.md) | [Anleitungen](docs/README.md)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes wird
nicht gelöscht, sondern nach unten verschoben – mit dem Datum, an dem es fertig
wurde.

## Offen

### Die Reihenfolge: erst das, was sich erproben lässt

Zum Ausprobieren stehen bereit: **Nextcloud, Proton Drive und Google
Fotos**. Diese drei kommen deshalb zuerst – nicht weil sie die
einfachsten wären, sondern weil alles andere Code wäre, der nur der
Papierlage nach funktioniert. Dieselbe Regel wie bei MailBurg und macOS:
Was nicht gelaufen ist, wird auch nicht als fertig ausgegeben.

1. **Nextcloud.** Der ganze Weg einmal komplett – auflisten, holen,
   Prüfsumme vergleichen, löschen –, ohne dass ein fremder Anbieter
   dazwischenfunkt. Keine Browser-Anmeldung, nur Adresse, Benutzername
   und App-Passwort.
2. **Proton Drive.** Der wertvollste Test von allen: Der Zugang ist
   nachgebaut, gilt als Beta und bricht erfahrungsgemäß nach
   Proton-Aktualisierungen. Hier zeigt sich, wie gut WOLKENErnte mit
   einem Anbieter umgeht, der plötzlich nicht mehr antwortet.
   Stolperstein bei der Einrichtung: Der 2FA-Code läuft ab, während man
   noch konfiguriert.
3. **Google Takeout.** Technisch mit dem Rest nicht verwandt – kein
   Abruf, sondern ein Archivleser. **Das Archiv rechtzeitig anfordern:**
   Google braucht dafür Stunden bis Tage.

Danach erst OneDrive, Dropbox und pCloud (sie teilen sich denselben
Ablauf über die Browser-Anmeldung) und zuletzt iCloud Fotos, wo ohnehin
nur die Hälfte geht.

- [ ] Das Feld `erprobt` in `anbieter.py` benutzen, sobald ein Anbieter
  tatsächlich gelaufen ist – und in der Oberfläche kenntlich machen, was
  bisher nur eingebaut und was wirklich erprobt ist.

### Als Nächstes: rclone ansprechen

- [ ] **rclone finden oder beilegen.** Erst auf dem Rechner suchen
  (`shutil.which`), sonst die beigelegte Binärdatei nehmen. Fassung prüfen –
  das iCloud-Modul gibt es erst ab 1.69, Fotos darin erst ab 1.74.
- [ ] **`rclone rcd` als Kindprozess starten**, an `127.0.0.1` gebunden, mit
  Benutzer und Kennwort. **Beides ist Pflicht, nicht Kür:** Wer die
  Schnittstelle erreicht, kann über `core/command` beliebige Befehle auf dem
  Rechner ausführen und über `config/dump` alle Zugangsdaten auslesen. Ein
  Test muss festhalten, dass ohne Anmeldung nichts geht.
- [ ] Auflisten über `operations/list`, Fortschritt über `core/stats`,
  Aufträge asynchron mit `_async: true` und `job/status`.
- [ ] **Löschen ausschließlich über `anbieter.darf_loeschen()`.** Kein
  zweiter Pfad, keine Ausnahme.

### Bilder ansehen

- [ ] Vorschaubilder: erst das **eingebettete Vorschaubild** versuchen, das in
  HEIC und JPEG ohnehin steckt – das ist rund zehnmal schneller, als das
  Vollbild zu dekodieren.
- [ ] Zwischenspeicher nach dem freedesktop-Muster
  (`$XDG_CACHE_HOME/thumbnails/`), damit der Dateimanager des Anwenders und
  WOLKENErnte sich denselben teilen.
- [ ] HEIC über **pi-heif**, nicht pillow-heif – dessen fertige Pakete
  enthalten x265 unter GPL, und das vertrüge sich nicht mit MIT.
- [ ] iPhone-Bilder tragen meist **Display P3**. Ohne Umrechnung nach sRGB
  wirken sie in der Oberfläche zu knallig.

### Videos

- [ ] Vorschaubilder mit **ffmpeg als eigenem Prozess**, `-ss` **vor** `-i`
  (Sprung vor dem Dekodieren, auf langen Dateien um Größenordnungen
  schneller). Ein beschädigtes Video reißt so das Programm nicht mit.
- [ ] **HDR-Material braucht Tonwertabbildung.** iPhone-Videos ab dem 12er
  sind HLG/BT.2020; ohne Umsetzung wird jede Vorschau grau und flau. Vorher
  mit `ffprobe` auf `color_transfer` prüfen – bei SDR-Material verschlechtert
  dieselbe Kette das Bild.
- [ ] Wiedergabe zunächst mit `QMediaPlayer` versuchen. Erst wenn das an
  echtem iPhone-Material scheitert, libmpv nachrüsten. **Nicht** python-vlc:
  unter Wayland gibt es dort bis heute keine Einbettung.

### Doppelgänger finden

- [ ] **Vorschaubilder der Anbieter hashen, nicht die Originale.** Drive,
  OneDrive und Dropbox liefern Vorschauen über ihre Schnittstellen; ein
  Wahrnehmungs-Hash über ein 256-Pixel-Bild erkennt »dasselbe Foto, anders
  komprimiert« praktisch genauso gut. Das erspart den Download von
  zehntausenden Dateien, bevor der Anwender überhaupt etwas entschieden hat.
- [ ] Suche über **Banding** (Hash in Blöcke zerlegen, exakte Nachschlagetabelle
  je Block), **nicht** über einen BK-Baum. Der gilt zwar als Standardlösung,
  bricht aber genau bei den Schwellen zusammen, die man für Bild-Hashes
  braucht – bei Schwelle 8 war er in einer Messung langsamer als der stumpfe
  Vergleich aller Paare.
- [ ] **Live Photos sind ein Paar aus HEIC und MOV.** Wer sie nicht als eines
  erkennt, meldet lauter Doppelgänger, die keine sind. Erkennung über den
  `ContentIdentifier`, nicht über den Dateinamen.

### Google Takeout

- [ ] Archiv einlesen, Metadaten aus den beiliegenden JSON-Dateien den Bildern
  zuordnen (Takeout trennt beides).
- [ ] Beim Löschen ehrlich sein: Anleitung anzeigen, wie im Browser aufgeräumt
  wird. **Keine Browser-Steuerung.** Sie sitzt auf undokumentierten internen
  Schnittstellen, bricht ohne Vorwarnung, und bei Apple verstößt sie
  ausdrücklich gegen die Nutzungsbedingungen.

### Oberfläche

- [ ] Rasteransicht mit Vorschaubildern, Mehrfachauswahl, Löschkorb.
- [ ] **Vor dem Löschen prüfen, dass die Kopie wirklich angekommen ist.**
  Erst Prüfsumme vergleichen, dann drüben entfernen – nie umgekehrt.
- [ ] Der Löschknopf erscheint nur, wo `anbieter.darf_loeschen()` es erlaubt.
  Bei den anderen steht der Grund, nicht ein ausgegrauter Knopf.

### Eine Fensteranwendung statt des Browsers

Gewünscht als nächster großer Schritt. Der Kern trägt das bereits: Nur
`wolkenernte/web/` ist browserabhängig, alles darunter weiß nichts von einer
Oberfläche. Eine Qt-Fassung käme **daneben**, nicht anstelle – wer keine
hundert Megabyte nachinstallieren will, behält den Browserweg.

- [ ] **PySide6** als optionale Abhängigkeit (`oberflaeche`-Extra), Aufruf über
  `wolkenernte fenster <Archiv>`.
- [ ] **Rasteransicht virtualisiert**, nicht als Liste aller Bilder. Bei 15.000
  Aufnahmen entscheidet das über flüssig oder unbenutzbar – `QListView` im
  Icon-Modus mit eigenem Modell, das Vorschaubilder erst beim Sichtbarwerden
  nachlädt.
- [ ] Vorschaubilder im Hintergrund erzeugen (`QThreadPool`), sonst steht die
  Oberfläche beim ersten Öffnen minutenlang.
- [ ] **Videos mit `QMediaPlayer`.** Seit Qt 6.5 ist FFmpeg das Standard-Backend
  und in den PySide6-Paketen enthalten; die H.264- und HEVC-*Dekoder* sind LGPL
  und damit dabei. **An echtem iPhone-Material prüfen**, bevor darauf gebaut
  wird. Scheitert es, ist libmpv der Rückfall – **nicht** python-vlc, das hat
  unter Wayland bis heute keine Einbettung.
- [ ] **HEIC über pi-heif**, als Pillow-Erweiterung; Qt bringt außerhalb von
  macOS kein HEIF-Modul mit.
- [ ] Tastatursteuerung: Pfeiltasten, Leertaste für Vollbild, Entf für den
  Löschkorb. Das ist der eigentliche Gewinn gegenüber dem Browser.
- [ ] **Beide Oberflächen teilen sich den Kern.** Was in `web/bestandsliste.py`
  an Auswertung steckt, gehört vorher eine Ebene tiefer – sonst wird es
  doppelt gepflegt und läuft auseinander.

### Ausliefern – der Anwender soll nichts nachinstallieren müssen

**Grundsatz:** Was WOLKENErnte braucht, bringt WOLKENErnte mit oder lässt
es vom Paketverwalter mitbringen. Niemand soll rclone von Hand herunterladen.

- [ ] **rclone unter Linux als Paketabhängigkeit**, nicht mitgeliefert. Dann
  installiert der Paketverwalter es mit, und der Anwender bekommt
  Sicherheitsaktualisierungen über sein System.
  **Vorher prüfen:** Wir brauchen **mindestens 1.75.0** – erst dort gibt es
  `config/oauthstatus` (die Anmelde-Adresse für den Browser) und den Fix für
  die iCloud-2FA. Arch und Manjaro sind aktuell genug; **bei Debian stable ist
  das offen**. Liegt dort eine ältere Fassung, muss rclone auch im .deb
  mitgeliefert werden.
- [ ] **rclone unter Windows mitliefern.** Kein Paketverwalter, also liegt
  `rclone.exe` im Programmordner. Rund 70 MB – die Fassung wird spürbar
  größer als MailBurg.
- [ ] **ffmpeg über `imageio-ffmpeg`.** Bringt die Binärdatei mit, steht unter
  BSD, keine Systeminstallation auf keinem der drei Systeme.
- [ ] **Beim Start prüfen, was da ist**, und im Klartext sagen, was fehlt –
  statt mitten im Abruf abzubrechen mit einer Meldung, die nach einem Defekt
  des Rechners aussieht. Auch die Fassung prüfen, nicht nur die Anwesenheit.
- [ ] **Windows: `.exe` nach dem Muster von `MailBurg/werkzeuge/mailburg.spec`** –
  aber als **Ordner** (`--onedir`), nicht als einzelne Datei. PySide6 steht
  unter LGPLv3, und die verlangt, dass der Anwender die Bibliothek austauschen
  kann; bei einer eingebackenen Einzeldatei geht das nicht.
- [ ] **Debian: `.deb`.** Gibt es in keinem der Repositorys bisher – das wäre
  das erste. Abhängigkeiten: python3, rclone (Fassung s. o.).
- [ ] **Arch/Manjaro: `PKGBUILD`** – ebenfalls neu, in keinem der
  Repositorys gibt es bisher eines.
- [ ] `.desktop`-Datei und Symbole an den vorgesehenen Ort
  (`/usr/share/applications`, `/usr/share/icons/hicolor/<größe>/apps/`) –
  Muster in `Denkzettel/desktop/` und `SilentInstaller/data/`.

### Später

- [ ] Windows und macOS überhaupt erst einmal ausprobieren. Bisher ist nichts
  davon dort gelaufen; die Angaben in `pyproject.toml` sagen das auch so.
- [ ] Proton Drive im Auge behalten: Das offizielle SDK gibt es seit Januar
  2026, aber ohne Anmeldemodul. Sobald das kommt, ist es der saubere Weg –
  und vielleicht auch der erste Zugang zu Proton Fotos.

## Erledigt

- [x] **Namen prüfen lassen.** (2026-09-05) Vier Vorschläge geprüft:
  *CloudFlow* scheitert an der Auffindbarkeit – »Cloudflow« ist ein Laufschuh
  von On, dazu sind PyPI, Play Store und alle Domains vergeben. *MediaDock*
  hat eine aktive deutsche Wortmarke gegen sich und ein gleichnamiges
  deutsches Softwareprodukt mit Werktitelschutz. *MediaMover* wäre rechtlich
  unbedenklich, ist aber ein Allerweltsbegriff mit 49 gleichnamigen
  GitHub-Ablagen. *Heimholer* schied wegen der Nebenbedeutungen aus –
  Bestattung und NS-Vokabular. **WOLKENErnte** ist in beiden Markenregistern
  ohne Treffer, Domains und Paketnamen sind frei.
- [x] **Prüfen, was bei den Anbietern überhaupt geht.** (2026-09-05) Ergebnis
  in `wolkenernte/anbieter.py` und `docs/anbieter.md`.

[Deutsch](TODO.md) | [English](TODO.en.md) | [Übersicht](README.md) | [Änderungsprotokoll](CHANGELOG.md) | [Anleitungen](docs/README.md)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes wird
nicht gelöscht, sondern nach unten verschoben – mit dem Datum, an dem es fertig
wurde.

## Offen

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

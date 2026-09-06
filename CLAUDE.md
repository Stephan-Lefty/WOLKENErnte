# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-09-06, Sonntagabend)

**239 Tests grün, öffentlich.** Der rclone-Anschluss steht jetzt: Das
Programm findet rclone, prüft die Fassung, startet es als abgesicherten
Dienst, richtet Zugänge ein, listet auf und löscht. **Vier Tests laufen
gegen das echte rclone** – mit dem `local`-Backend, das keine
Zugangsdaten braucht, sich für die Schnittstelle aber wie jede Wolke
verhält.

Was damit noch nicht geht: **aus einer echten Wolke ernten.** Der Weg
von `rclone.auflisten()` zu `archiv.uebernehmen()` fehlt – bisher kann
nur ein Takeout-Archiv oder ein Ordner als Quelle dienen.

Am echten Bestand erprobt: 14.770 Bilder aus 47 GB Quellen, 29 GB im
Archiv, 13.605 bytegleiche Kopien übergangen, 1.332 Gruppen mit
derselben Aufnahme in mehreren Fassungen.

**Die Videofrage ist geklärt** (2026-09-06): `QMediaPlayer` spielt H.264,
HEVC und VP9 aus diesem Bestand ab – geprüft mit
`werkzeuge/videoprobe.py`, das auf ein tatsächlich ankommendes Einzelbild
wartet und nicht bloß darauf, dass kein Fehler kommt. libmpv wird nicht
gebraucht. Nebenbei kam heraus: Der Bestand enthält **kein**
iPhone-Material – 239 VP9, 140 H.264 und nur 5 HEVC.

### Die beiden nächsten Schritte

**Nextcloud wirklich ernten.** `wolkenernte zugang nextcloud` legt einen
Zugang an; was fehlt, ist eine Quelle nach dem Muster von `lokal.py`,
die über rclone liest. Dann gilt derselbe Ablauf wie bisher: ernten,
erfassen, pruefen – und erst danach löschen, **ausschließlich über
`anbieter.darf_loeschen()`**.

**Eine Fensteranwendung ohne Browser**, gewünscht als übernächster
Schritt. Zuschnitt in der TODO. Wichtig: Was in `web/bestandsliste.py`
an Auswertung steckt, muss vorher eine Ebene tiefer – sonst wird es für
zwei Oberflächen doppelt gepflegt.

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
├── ernten.py / erfassung.py / nachweis.py   die drei Abläufe
└── web/            die Oberfläche - das Einzige, was den Browser kennt
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

**Gegenproben gehören dazu.** Grüne Tests sind verdächtig: Bei der
Zuordnung fielen vier Tests um, als die Klammer-Verschiebung
herausgenommen wurde; beim Takeout-Leser fünf, als nur das erste
Teilarchiv gelesen wurde. Solche Proben in einer **Kopie** machen, nicht
in der Arbeitskopie.

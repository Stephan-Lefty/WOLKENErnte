[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md) | [Anleitungen](docs/README.md)

<p align="center">
  <img src="assets/icon-256.png" alt="WOLKENErnte" width="140">
</p>

# WOLKENErnte

Bilder und Videos aus den Wolken holen – und dort aufräumen.

Fotos liegen heute verstreut: ein Teil bei Google, ein Teil bei Apple, ein Teil
bei Proton, dazu OneDrive, Dropbox und die eigene Nextcloud. WOLKENErnte holt
sie an einen Ort Ihrer Wahl, ordnet sie nach Aufnahmedatum, findet Doppelgänger
– und soll später auf Ihr Wort hin drüben löschen, was Sie nicht mehr brauchen.

**Was heute schon geht:** Google-Takeout-Archive einlesen, Bilder aus Ordnern
übernehmen, Doppelgänger finden, alles im Browser durchsehen.
**Was noch nicht geht:** der Abruf aus den Wolken und das Löschen dort. Dafür
fehlt der rclone-Teil – siehe [TODO.md](TODO.md).

## Was bei welchem Anbieter geht

Diese Tabelle ist der wichtigste Abschnitt dieser Datei. Ausgerechnet die drei
Anbieter, an die man bei Fotos zuerst denkt, sind die schwierigsten.

| Anbieter | sehen | holen | **in der Wolke löschen** |
|---|:---:|:---:|:---:|
| Nextcloud (WebDAV) | ja | ja | **ja** |
| Dropbox | ja | ja | **ja** |
| Microsoft OneDrive | ja | ja | **ja** |
| Google **Drive** | ja | ja | **ja** |
| Box, pCloud | ja | ja | **ja** |
| iCloud **Drive** | ja | ja | **ja** |
| Proton **Drive** | ja | ja | **ja** |
| **iCloud Fotos** | ja | ja | **nein** |
| **Google Fotos** | nein | nein | **nein** |
| **Proton Fotos** | nein | nein | **nein** |

**Google Fotos** ist für fremde Programme seit dem 31. März 2025 verschlossen.
Eine Anwendung sieht dort nur noch die Bilder, die sie selbst hochgeladen hat –
Ihre eigene Mediathek ist unerreichbar. Eine Löschfunktion hat es dort nie
gegeben. Der Weg führt über *Google Takeout*: Sie fordern das Archiv selbst an,
WOLKENErnte wertet es aus. Aufgeräumt wird danach von Hand im Browser.

**iCloud Fotos** lässt sich vollständig ansehen und herunterladen, aber nicht
anfassen – der Zugang ist ausdrücklich nur lesend. Mit eingeschaltetem
*erweitertem Datenschutz* geht dort gar nichts.

**Proton Fotos** liegt in einem eigenen Bereich, den fremde Programme nicht
sehen. Dafür gibt es derzeit keinen Weg – auch keinen umständlichen.

Die Belege zu jeder Aussage stehen in [docs/anbieter.md](docs/anbieter.md), mit
Datum. Diese Lage ändert sich schnell.

## Loslegen

```
wolkenernte ernten      ~/Bilder/Archiv  ~/Downloads/takeout-Ordner
wolkenernte erfassen    ~/Bilder/Archiv  ~/Downloads/takeout-Ordner
wolkenernte pruefen     ~/Bilder/Archiv  ~/Downloads/takeout-Ordner
wolkenernte oberflaeche ~/Bilder/Archiv
```

**Die Reihenfolge ist keine Geschmackssache.** Erst *ernten* – die Bilder ins
Archiv. Dann *erfassen* – Orte, Titel und Alben in die Datenbank, denn die
stehen nur in den Quellen und wären beim Löschen verloren. Dann *pruefen* – der
Nachweis, dass wirklich jedes Bild angekommen ist. **Und erst danach** darf eine
Quelle gelöscht werden.

Weitere Befehle: `wolkenernte anbieter` zeigt die Tabelle von oben,
`wolkenernte bestand` die Zahlen aus der Datenbank, `wolkenernte doppelt` sucht
ähnliche Bilder.

## Das Archiv

```
Archiv/
├── 2023/2023-07/IMG_1234.jpg     nach Aufnahmedatum geordnet
├── ohne-datum/IMG_5678.jpg       wenn keines zu ermitteln war
└── .wolkenernte/
    ├── bestand.db                Orte, Titel, Alben, Favoriten
    └── vorschau/                 Vorschaubilder
```

Nach Datum und nicht nach Alben: Ein Bild kann in mehreren Alben liegen, aber
nur an einer Stelle auf der Platte. Die Albumzugehörigkeit steht in der
Datenbank.

**Ihre Bilder bleiben gewöhnliche Dateien.** Kein eigenes Format, keine
Verschlüsselung, kein Verzeichnisdienst. Wer WOLKENErnte in zehn Jahren nicht
mehr hat, öffnet den Ordner mit jedem beliebigen Programm.

## Die Oberfläche

`wolkenernte oberflaeche` startet einen Dienst und öffnet den Browser: Bilder in
Kacheln, Filter nach Jahr und Album, Suche über Dateinamen, Titel und Alben,
Einzelansicht mit Ort und Aufnahmedatum, Videowiedergabe.

**Der Dienst hört ausschließlich auf 127.0.0.1** und ist von außen nicht
erreichbar. Er zeigt private Fotos und hat keine Anmeldung.

Warum der Browser und kein Fenster: Er kann Bilder und Videos bereits anzeigen,
in jedem Format, das das System beherrscht. Eine Fensteranwendung ist geplant –
siehe [TODO.md](TODO.md) – aber sie kostet über hundert Megabyte zusätzlich, und
das soll man nicht zahlen müssen, nur um seine Fotos anzusehen.

## Einrichten

**Arch und Manjaro**

```
cd verpacken/arch && makepkg -si
```

**Alle anderen** – der Kern läuft mit Python 3.11 aufwärts ohne Fremdpakete:

```
python3 -m wolkenernte oberflaeche ~/Bilder/Archiv
```

Empfohlen, aber nicht nötig: **Pillow** für Vorschaubilder und die
Doppelgängersuche (`pacman -S python-pillow`). Ohne Pillow zeigt die Oberfläche
die Originale – das ist langsamer, aber sie bleibt benutzbar.

## Wie es gebaut ist

Der Kern kommt **ohne Fremdpakete** aus. Der geplante Abruf aus den Wolken wird
[rclone](https://rclone.org/) übernehmen, das als eigener Dienst läuft und über
eine gewöhnliche HTTP-Schnittstelle angesprochen wird – dafür genügen `urllib`
und `json` aus der Standardbibliothek.

Das hat einen Nebeneffekt, der Geld spart: Weil die Zugangsdaten zu Google der
Anwender selbst anlegt, entfällt das jährliche CASA-Sicherheitsaudit, das Google
für weitreichende Zugriffsrechte verlangt – je nach Prüflabor 500 bis 4.500
US-Dollar im Jahr.

## Lizenz

[MIT](LICENSE)

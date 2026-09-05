[Übersicht](../README.md) | [Anleitungen](README.md) | [Anbieter](anbieter.md)

# Google Takeout – wie das Archiv aufgebaut ist

**Stand: 2026-09-05.** Die Regeln unten sind aus den Werkzeugen
[GooglePhotosTakeoutHelper Neo](https://github.com/Xentraxx/GooglePhotosTakeoutHelper_Neo)
und [immich-go](https://github.com/simulot/immich-go) abgelesen, die sie
ihrerseits aus echten Archiven abgeleitet haben. Google dokumentiert
nichts davon.

## Warum es diesen Umweg überhaupt gibt

Google Fotos ist für fremde Programme seit dem 31.03.2025 verschlossen –
siehe [anbieter.md](anbieter.md). Der einzige Weg an den eigenen Bestand
führt über ein Archiv, das man bei Google selbst anfordert.

Praktisches dazu ([Google-Hilfe](https://support.google.com/accounts/answer/3024190?hl=de)):
Das Archiv **läuft nach etwa sieben Tagen ab** und lässt sich **fünfmal**
herunterladen. Wählbare Teilgrößen sind 1, 2, 4, 10 und 50 GB.

## Der Ordner heißt nicht überall gleich

Die Ordnernamen richten sich nach der Sprache des Google-Kontos:
`Google Fotos` oder `Google Photos`, `Fotos von 2024` oder
`Photos from 2024`, `Papierkorb` oder `Bin`.

**Deshalb wird der Ordner nicht am Namen erkannt, sondern an seinem
Aufbau** – daran, dass er Jahresordner oder Medien mit Metadatendateien
enthält. Beide oben genannten Werkzeuge machen das inzwischen so; eine
Liste übersetzter Ordnernamen wäre immer unvollständig.

## Die Metadatendateien

Neben jedem Bild liegt eine JSON mit Aufnahmedatum, Ort und Titel. Ihr
Name folgt Regeln, die an mehreren Stellen brechen.

**Die Umstellung Ende 2024.** Vorher `IMG_1234.jpg.json`, seither
`IMG_1234.jpg.supplemental-metadata.json`. Beide Formen kommen in
Archiven vor, je nachdem, wann die Bilder hochgeladen wurden.

**Die 51-Zeichen-Grenze.** Ist der JSON-Name länger, kürzt Google – und
zwar im Suffix. So entstehen `.supplemental-metadat.json`,
`.suppl.json`, im Extremfall `.s.json`. Der Rest ist immer ein **Anfang**
von `supplemental-metadata`; daran erkennt man ihn zuverlässig, denn
keine Dateiendung ist ein Anfang dieses Wortes.

Die Zahl ist **51**, nicht 46. 46 ist nur, was für den Namen bleibt,
wenn `.json` abgezogen ist.

**Die Klammer steht auf der anderen Seite.** Das ist die tückischste
Regel. Bei Namensgleichheit hängt Google an das *Bild* eine Nummer vor
der Endung, an die *JSON* aber dahinter:

```
IMG_1234(1).jpg   →   IMG_1234.jpg(1).json
```

Daneben gibt es `IMG_1234.jpg.supplemental-metadata(1).json` und
`IMG_1234.jpg(1).supplemental-metadata.json`. Wer nur die naheliegende
Form `IMG_1234(1).jpg.json` sucht, findet für **kein einziges Duplikat**
Metadaten.

**Bearbeitete Fassungen haben keine eigene Datei.** `IMG_1234-bearbeitet.jpg`
(auf Englisch `-edited`) verweist auf die JSON des Originals. Die
Anhängsel `-effects`, `-motion`, `-animation`, `-smile`, `-collage` und
`-mix` bleiben immer englisch, die übrigen sind übersetzt.

## Die wichtigste Regel: unsichere Treffer kennzeichnen

Wer bei der Zuordnung großzügig rät, schreibt einem Bild die Angaben
eines **anderen** zu. Genau das ist im GooglePhotosTakeoutHelper passiert
([Issue #139](https://github.com/Xentraxx/GooglePhotosTakeoutHelper_Neo/issues/139)):
Ortsangaben und Aufnahmedaten fremder Fotos wanderten in die Bilder, mit
Abweichungen von hunderten Kilometern.

WOLKENErnte führt deshalb an jeder Zuordnung ein Kennzeichen mit, ob die
Metadaten **genau dieses** Bild beschreiben. Bei einem unsicheren Treffer
werden **weder Datum noch Ort** angezeigt – lieber keine Angabe als eine
falsche. Titel und Beschreibung sind auch dann brauchbar.

## Der Inhalt der JSON

```json
{
  "title": "IMG_0799.HEIC",
  "description": "",
  "creationTime": { "timestamp": "1563466129", "formatted": "..." },
  "photoTakenTime": { "timestamp": "1563379729", "formatted": "..." },
  "geoData":     { "latitude": 35.3387, "longitude": 25.1442, "altitude": 15.0 },
  "geoDataExif": { "latitude": 35.3387, "longitude": 25.1442, "altitude": 15.0 },
  "url": "https://photos.google.com/photo/...",
  "favorited": true
}
```

- **`photoTakenTime.timestamp`** ist die Aufnahmezeit, in Sekunden seit
  1970, **in UTC**. Das ist die verlässliche Angabe.
- **`formatted` niemals auswerten** – der Text ist übersetzt und je nach
  Konto anders aufgebaut.
- **`creationTime`** ist der Zeitpunkt des Hochladens, nicht der Aufnahme.
- **Ort: erst `geoDataExif`, bei (0,0) auf `geoData` zurückfallen.**
  Stehen in beiden Nullen, ist **kein Ort bekannt** – (0,0) liegt im
  Golf von Guinea und ist nie eine echte Angabe.
- **`title`** enthält den ursprünglichen Dateinamen ohne `(N)` und
  überlebt die Kürzung – der beste Weg zurück zum echten Namen.
- **`trashed`, `archived`, `favorited`** stehen nur da, wenn sie zutreffen.

## Was im Archiv fehlt oder falsch ist

- **Die EXIF-Daten im Bild selbst sind unzuverlässig.** Google rechnet
  beim Hochladen um; Datum und Ort im Bild fehlen oft oder stimmen
  nicht. Die Wahrheit steht in der JSON. Das ist der Grund, warum es all
  diese Werkzeuge überhaupt gibt.
- **Alben enthalten physische Kopien.** Dasselbe Foto liegt im
  Jahresordner *und* in jedem Album, in dem es vorkommt. Für die
  Doppelgängersuche ist das der häufigste Fall – und die Kopien sind
  bytegleich.
- **Manchmal fehlt die JSON ganz.**
- **Live Photos kommen als zwei getrennte Dateien** (HEIC und MOV), ohne
  Hinweis darauf, dass sie zusammengehören.
- **Sehr große Dateien liegen außerhalb der ZIP-Archive.** Ist eine Datei
  größer als die gewählte Teilgröße, legt Google sie einzeln daneben –
  ihre Metadaten bleiben aber im Archiv.

## Was daraus für WOLKENErnte folgt

Die Regeln stecken in [`wolkenernte/zuordnung.py`](../wolkenernte/zuordnung.py),
die Archive werden von [`wolkenernte/takeout.py`](../wolkenernte/takeout.py)
gelesen – **ohne Auspacken**, direkt aus den ZIP-Dateien und über alle
Teilarchive hinweg, weil ein Bild und seine Metadaten in verschiedenen
Teilen liegen können.

Zum Nachsehen, wie ein konkretes Archiv aufgebaut ist:

```
python3 werkzeuge/takeout_pruefen.py /pfad/zu/den/zips
```

Das gibt nur Zahlen und Namensmuster aus, keine Datei- oder Albumnamen.

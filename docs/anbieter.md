[Übersicht](../README.md) | [Anleitungen](README.md) | [TODO](../TODO.md)

# Was bei welchem Anbieter geht – mit Belegen

**Stand: 2026-09-05.** Diese Lage ändert sich schnell. Wer hier etwas ändert,
ändert bitte auch dieses Datum, den Beleg **und**
[`wolkenernte/anbieter.py`](../wolkenernte/anbieter.py) – die Tabelle im Code
ist die maßgebliche, diese Datei begründet sie nur.

## Zusammenfassung

| Anbieter | sehen | holen | löschen | Weg |
|---|:---:|:---:|:---:|---|
| Nextcloud (WebDAV) | ja | ja | ja | rclone |
| Dropbox | ja | ja | ja | rclone |
| Microsoft OneDrive | ja | ja | ja | rclone |
| Google Drive | ja | ja | ja | rclone |
| Box, pCloud | ja | ja | ja | rclone |
| iCloud Drive | ja | ja | ja | rclone (erprobungsbedürftig) |
| Proton Drive | ja | ja | ja | rclone (Beta) |
| iCloud Fotos | ja | ja | **nein** | rclone, nur lesend |
| Google Fotos | **nein** | **nein** | **nein** | nur Takeout |
| Proton Fotos | **nein** | **nein** | **nein** | kein Weg |

## Google Fotos – verschlossen

Am **31. März 2025** hat Google die Zugriffsrechte `photoslibrary`,
`photoslibrary.readonly` und `photoslibrary.sharing` ersatzlos gestrichen.
Seither liefert `mediaItems.list` nur noch »media items created by your app« –
also ausschließlich, was das fragende Programm selbst hochgeladen hat.

Eine Löschmethode hat die Schnittstelle **nie** besessen: `mediaItems.delete`
existiert nicht. `batchRemoveMediaItems` entfernt lediglich aus einem Album, das
die Anwendung selbst angelegt hat.

Die als Ersatz angebotene *Picker API* verlangt, dass der Anwender jedes Bild
einzeln in Googles eigener Oberfläche auswählt, und entfernt beim Herunterladen
die Ortsangabe aus den Metadaten. Für ein Sicherungswerkzeug ist sie unbrauchbar.

Auch die *Data Portability API* hilft nicht: Google Fotos ist dort nicht unter
den unterstützten Diensten, und alle Zugriffsrechte lauten »Move a copy of…« –
gelöscht wird damit nichts.

Folgen in der Praxis: `gphotos-sync` wurde im März 2026 archiviert. rclone
führt sein Google-Fotos-Modul als **veraltet** und schreibt selbst: »the Google
Photos API does not allow media to be deleted permanently«.

- <https://developers.google.com/photos/support/updates>
- <https://developers.google.com/photos/library/reference/rest/v1/mediaItems>
- <https://rclone.org/googlephotos/>

## Google Drive – vollständig, und ohne Prüfgebühr

Herunterladen und Löschen sind über die offizielle Schnittstelle möglich.
Entscheidend ist die Wahl des Zugriffsrechts: `drive` und `drive.readonly`
gelten als *restricted* und ziehen ein jährliches CASA-Sicherheitsaudit nach
sich – je nach Prüflabor 500 bis 4.500 US-Dollar.

`drive.file` ist **nicht** eingeschränkt, erlaubt aber trotzdem `files.delete`
für Dateien, die der Anwender freigegeben oder das Programm selbst angelegt hat.
Google empfiehlt diesen Weg ausdrücklich als Ausweichpfad. Weil WOLKENErnte den
Zugang ohnehin über rclone herstellt und der Anwender seine Zugangsdaten selbst
anlegt, stellt sich die Frage für dieses Programm gar nicht erst.

Wichtig zu wissen: Was in Google **Fotos** liegt, ist seit 2019 in Google
**Drive** nicht mehr sichtbar. Die beiden Einträge in der Tabelle sind wirklich
zwei verschiedene Dinge.

- <https://developers.google.com/workspace/drive/api/guides/api-specific-auth>
- <https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification>

## iCloud Fotos – lesen ja, anfassen nein

Apple bietet für die Fotomediathek eines Nutzers **keine** Schnittstelle für
fremde Programme an. CloudKit Web Services deckt nur den eigenen Container einer
Anwendung ab, nicht die Mediathek des Anwenders.

rclone bildet seit Fassung 1.69 den Weg über die Weboberfläche nach, seit 1.74
auch für Fotos – ausdrücklich **nur lesend**: »iCloud Photos is read-only.
Upload, delete, rename, and move operations are not supported.«

Zwei Einschränkungen, die der Anwender vorher wissen muss:

- Mit eingeschaltetem **erweitertem Datenschutz** (Advanced Data Protection) ist
  der Zugriff über das Web gesperrt, und damit auch dieser Weg.
- Die Anmeldung verlangt das **echte** Apple-Passwort; anwendungsspezifische
  Passwörter werden nicht angenommen. Das Vertrauensmerkmal gilt 30 Tage.

Löschen könnte allein `icloudpd`, und auch das nur nach »Zuletzt gelöscht«.
Dieser Weg ist bewusst **nicht** eingebaut: Apples Nutzungsbedingungen
untersagen den automatisierten Zugriff ausdrücklich, und das Risiko einer
Kontosperre trägt der Anwender.

- <https://rclone.org/iclouddrive/>
- <https://developer.apple.com/forums/thread/74434>

## Proton – Drive ja, Fotos nein

Proton veröffentlicht keine Schnittstellenbeschreibung. rclone hat den Zugang
nachgebaut; für »Meine Dateien« funktioniert das vollständig, einschließlich
Löschen. Der Umgang mit der Verschlüsselung ändert sich von Zeit zu Zeit –
rechnen Sie damit, dass es nach einer Proton-Aktualisierung vorübergehend steht.

**Proton Fotos ist ein eigener Bereich** (`/Photos`), und rclone bildet als
Wurzel nur »Meine Dateien« ab. Die über die Handy-App gesicherten Bilder sind
damit weder auflistbar noch ladbar noch löschbar. Der entsprechende Wunsch ist
seit Mai 2024 offen, ohne Bearbeiter.

Seit Januar 2026 gibt es ein quelloffenes Proton-Drive-SDK, dem jedoch das
Anmeldemodul fehlt – für eigenständige fremde Programme also noch nicht
verwendbar. Proton nennt als Ziel Ende 2026 oder Anfang 2027.

- <https://rclone.org/protondrive/>
- <https://github.com/rclone/rclone/issues/7832>
- <https://proton.me/blog/drive-sdk-january-2026>

## Was daraus folgt

WOLKENErnte beschränkt sich auf die Anbieter, bei denen der ganze Ablauf ehrlich
funktioniert, und sagt bei den übrigen, woran es liegt. Für Google Fotos gibt es
den Umweg über Takeout – einlesen, ansehen, Doppelgänger finden –, aufgeräumt
wird dort von Hand im Browser.

**Browser-Steuerung ist bewusst kein Bestandteil.** Sie sitzt auf
undokumentierten internen Schnittstellen, bricht ohne Vorwarnung, und bei Apple
verstößt sie ausdrücklich gegen die Nutzungsbedingungen. Ein Programm, dem man
seinen Bildbestand anvertraut, sollte nicht das erste sein, das eine Kontosperre
auslöst.

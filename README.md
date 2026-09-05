[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md) | [Anleitungen](docs/README.md)

<p align="center">
  <img src="assets/icon-256.png" alt="WOLKENErnte" width="140">
</p>

# WOLKENErnte

Bilder und Videos aus den Wolken holen – und dort aufräumen.

Fotos liegen heute verstreut: ein Teil bei Google, ein Teil bei Apple, ein Teil
bei Proton, dazu OneDrive, Dropbox und die eigene Nextcloud. WOLKENErnte holt
sie an einen Ort Ihrer Wahl, zeigt sie Ihnen, findet Doppelgänger – und löscht
auf Ihr Wort hin drüben, was Sie nicht mehr brauchen.

**Das ist ein Gerüst, noch kein Programm.** Bisher kann WOLKENErnte genau
eines: Auskunft darüber geben, was bei welchem Anbieter überhaupt möglich ist.
Das klingt nach wenig, ist aber der Teil, den man zuerst braucht – siehe den
nächsten Abschnitt.

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
*erweitertem Datenschutz* (Advanced Data Protection) geht dort gar nichts.

**Proton Fotos** liegt in einem eigenen Bereich, den fremde Programme nicht
sehen. Dafür gibt es derzeit keinen Weg – auch keinen umständlichen.

Die Belege zu jeder dieser Aussagen stehen in [docs/anbieter.md](docs/anbieter.md).
Diese Lage ändert sich schnell; das Datum dort sagt Ihnen, wie alt die Auskunft ist.

## Warum es das braucht

Es gibt viele gute Fotoverwalter – immich, PhotoPrism, Ente. Sie alle sind
**Zielarchive**: Sie holen Bilder herein und fassen die Quelle nie wieder an.
Und es gibt Dateimanager für Wolkenspeicher, die löschen können, aber keine
Doppelgänger finden. Und es gibt Doppelgängersucher, die nur auf der eigenen
Platte arbeiten.

Kein einziges freies Programm verbindet beides: mehrere Wolken, Vorschau,
Doppelgängersuche **und** Aufräumen in der Quelle.

## Ausprobieren

```
git clone https://github.com/Stephan-Lefty/WOLKENErnte.git
cd WOLKENErnte
python3 -m wolkenernte
```

Zeigt die Anbietertabelle mitsamt den Einschränkungen. Mehr kann es noch nicht.

## Wie es gebaut ist

Der Kern kommt **ohne Fremdpakete** aus. Die Arbeit an den Wolken erledigt
[rclone](https://rclone.org/), das als eigener Dienst läuft und über eine
gewöhnliche HTTP-Schnittstelle angesprochen wird – dafür genügen `urllib` und
`json` aus der Standardbibliothek. rclone steht unter MIT und darf beigelegt
werden.

Das hat einen Nebeneffekt, der bares Geld spart: Weil die Zugangsdaten zu
Google der Anwender selbst anlegt, entfällt das jährliche
CASA-Sicherheitsaudit, das Google für weitreichende Zugriffsrechte verlangt –
je nach Prüflabor 500 bis 4.500 US-Dollar im Jahr.

Alles Weitere ist Kür und wird zur Laufzeit geprüft: Pillow und pi-heif für
Bilder, ImageHash für Doppelgänger, ffmpeg für Videovorschauen, PySide6 für die
Oberfläche.

## Lizenz

[MIT](LICENSE)

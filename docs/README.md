[Übersicht](../README.md) | [Änderungsprotokoll](../CHANGELOG.md) | [TODO](../TODO.md)

# Anleitungen

- [Was bei welchem Anbieter geht](anbieter.md) – mit Belegen und Datum.
  **Lesen Sie das zuerst.** Ausgerechnet Google Fotos, iCloud Fotos und Proton
  Fotos können nicht das, was man von ihnen erwartet.
- [Google Takeout – wie das Archiv aufgebaut ist](takeout.md) – Ordnernamen,
  die Benennung der Metadatendateien und die Fallen bei der Zuordnung. Für
  Google Fotos ist das der einzige Weg an den eigenen Bestand.
- [Bildschirmfotos](bilder/README.md) – wie beide Oberflächen aussehen.

**Im Fenster selbst** steht die Anleitung zum Google-Takeout unter *Hilfe →
Google-Bilder holen*: anfordern, herunterladen, einlesen. Sie beschreibt das
Ziel jedes Schrittes und verlinkt Googles eigene Hilfe – abgetippte Klickwege
durch fremde Netzseiten sind nach dem nächsten Umbau falsch.

## Die Befehle im Überblick

| Befehl | wofür |
|---|---|
| `anbieter` | zeigt, was bei welchem Anbieter möglich ist |
| `rclone` | prüft, ob der Zugang zu den Wolken bereit ist |
| `zugang` | Zugänge einrichten und ansehen |
| `ernten` | Bilder aus Quellen ins Archiv holen |
| `erfassen` | Orte, Titel und Alben in die Datenbank schreiben |
| `pruefen` | nachweisen, dass alles angekommen ist |
| `aufraeumen` | in der Wolke löschen, was nachweislich im Archiv liegt |
| `uhrzeit` | die EXIF-Uhrzeit in einem alten Archiv nachrechnen |
| `bestand` | zeigt, was in der Datenbank steht |
| `doppelt` | sucht ähnliche Bilder |
| `verschlagworten` | Schlagwörter vergeben |
| `fenster` | Archiv als Fensteranwendung durchsehen |
| `oberflaeche` | Archiv im Browser durchsehen |
| `neuigkeiten` | bei GitHub nachfragen, ob es eine neuere Fassung gibt |

**Die Reihenfolge von `ernten`, `erfassen` und `pruefen` ist keine
Geschmackssache** – sie steht in der [README](../README.md) begründet. Erst
danach darf eine Quelle gelöscht werden.

Eine ausführliche Anleitung zum Abruf aus den Wolken fehlt noch. Den Abruf
selbst gibt es: im Fenster unter **Wolke**, auf der Kommandozeile als `zugang`,
`ernten` und `aufraeumen`.

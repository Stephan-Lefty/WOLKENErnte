[Übersicht](../README.md) | [Änderungsprotokoll](../CHANGELOG.md) | [TODO](../TODO.md)

# Anleitungen

- [Was bei welchem Anbieter geht](anbieter.md) – mit Belegen und Datum.
  **Lesen Sie das zuerst.** Ausgerechnet Google Fotos, iCloud Fotos und Proton
  Fotos können nicht das, was man von ihnen erwartet.
- [Google Takeout – wie das Archiv aufgebaut ist](takeout.md) – Ordnernamen,
  die Benennung der Metadatendateien und die Fallen bei der Zuordnung. Für
  Google Fotos ist das der einzige Weg an den eigenen Bestand.

## Die Befehle im Überblick

| Befehl | wofür |
|---|---|
| `anbieter` | zeigt, was bei welchem Anbieter möglich ist |
| `rclone` | prüft, ob der Zugang zu den Wolken bereit ist |
| `zugang` | Zugänge einrichten und ansehen |
| `ernten` | Bilder aus Quellen ins Archiv holen |
| `erfassen` | Orte, Titel und Alben in die Datenbank schreiben |
| `pruefen` | nachweisen, dass alles angekommen ist |
| `bestand` | zeigt, was in der Datenbank steht |
| `doppelt` | sucht ähnliche Bilder |
| `fenster` | Archiv als Fensteranwendung durchsehen |
| `oberflaeche` | Archiv im Browser durchsehen |

**Die Reihenfolge von `ernten`, `erfassen` und `pruefen` ist keine
Geschmackssache** – sie steht in der [README](../README.md) begründet. Erst
danach darf eine Quelle gelöscht werden.

Eine Anleitung zum Abruf aus den Wolken gibt es noch nicht, weil es den Abruf
noch nicht gibt. Eine Anleitung für etwas, das es nicht gibt, wäre eine Zusage,
die niemand einhält.

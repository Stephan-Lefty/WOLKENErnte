"""Die Farben des Programms.

Übernommen aus MailBurg, absichtlich unverändert: Alle Programme dieses
Hauses tragen dieselben Blau- und Grautöne. Wer hier etwas ändert,
ändert es dort mit – sonst stehen zwei Programme nebeneinander, die
aussehen, als kämen sie von verschiedenen Herstellern.

Die Kontrastwerte in den Kommentaren sind gemessen, nicht geschätzt.
``tests/test_farben.py`` hält sie fest.
"""

from __future__ import annotations

# -- Blau, die Leitfarbe ---------------------------------------------------
BLAU_HELL = "#0e8af6"    # oberes Ende des Verlaufs im Icon
BLAU = "#1668e3"         # Flächen, Knöpfe, Hervorhebungen
BLAU_TIEF = "#0047a7"    # unteres Ende des Verlaufs im Icon
BLAU_DUNKEL = "#0d3a8a"  # Ränder und Schatten auf blauem Grund
BLAU_NACHT = "#0d2141"   # Hintergründe im dunklen Thema
BLAU_LEUCHT = "#6cb6ff"  # Verweise auf dunklem Grund; auf hellem zu blass

# -- Grau, alles andere ----------------------------------------------------
GRAU_PAPIER = "#f7f9fc"  # Seitenhintergrund, helles Thema
GRAU_HELL = "#d6dde8"    # Linien, Trenner, Rahmen
GRAU_MITTE = "#97a1ad"   # zurückgenommener Text auf *dunklem* Grund
GRAU_LEISE = "#667080"   # zurückgenommener Text auf hellem Grund
GRAU = "#5b6672"         # Fließtext auf hellem Grund
GRAU_DUNKEL = "#3a4048"  # Überschriften
GRAU_KOHLE = "#2b323c"   # Flächen im dunklen Thema
GRAU_NACHT = "#20262f"   # Seitenhintergrund, dunkles Thema
WEISS = "#ffffff"

# -- Zustände --------------------------------------------------------------
ROT = "#c62828"          # Fehler, Gescheitertes
ROT_HELL = "#ef9a9a"     # dasselbe auf dunklem Grund
GRUEN = "#2e7d32"        # Erledigtes, Geholtes
GRUEN_HELL = "#81c784"   # dasselbe auf dunklem Grund

#: Der Verlauf des Programmsymbols, von oben nach unten.
ICON_VERLAUF = (BLAU_HELL, BLAU_TIEF)


def _kanal(wert: float) -> float:
    """Ein Farbkanal, von der Bildschirmdarstellung ins Lineare."""
    wert /= 255
    return wert / 12.92 if wert <= 0.04045 else ((wert + 0.055) / 1.055) ** 2.4


def helligkeit(farbe: str) -> float:
    """Die relative Leuchtdichte nach WCAG."""
    farbe = farbe.lstrip("#")
    r, g, b = (int(farbe[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def kontrast(vorne: str, hinten: str) -> float:
    """Das Kontrastverhältnis zweier Farben, zwischen 1 und 21.

    WCAG verlangt 4,5 für Fließtext und 3,0 für große Schrift und für
    Bedienelemente. Geprüft wird das in ``tests/test_farben.py`` – für
    ein Programm, das im Kern Bilder anzeigt, ist Lesbarkeit kein
    Nebenschauplatz.
    """
    a, b = helligkeit(vorne), helligkeit(hinten)
    hell, dunkel = max(a, b), min(a, b)
    return (hell + 0.05) / (dunkel + 0.05)

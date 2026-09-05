"""Die HTML-Seiten der Oberfläche.

Von Hand zusammengesetzt, ohne Vorlagensprache: Der Kern soll ohne
Fremdpakete auskommen, und für ein halbes Dutzend Seiten ist eine
Bibliothek dafür mehr Aufwand als Nutzen.

Alle Farben kommen aus :mod:`wolkenernte.farben` – dieselben wie im
Programmsymbol und wie bei MailBurg.
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

from .. import __version__, farben
from .bestandsliste import Bestandsliste, Bild

STIL = f"""
:root {{
  --blau: {farben.BLAU}; --blau-hell: {farben.BLAU_HELL};
  --blau-tief: {farben.BLAU_TIEF}; --leucht: {farben.BLAU_LEUCHT};
  --grund: {farben.GRAU_NACHT}; --flaeche: {farben.GRAU_KOHLE};
  --linie: {farben.GRAU_DUNKEL}; --text: {farben.GRAU_HELL};
  --leise: {farben.GRAU_MITTE};
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--grund); color: var(--text);
  font: 15px/1.5 system-ui, sans-serif; }}
a {{ color: var(--leucht); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

header {{ position: sticky; top: 0; z-index: 10; display: flex; gap: 1rem;
  align-items: center; padding: .7rem 1.2rem; background: linear-gradient(
  180deg, var(--blau-hell), var(--blau-tief)); color: #fff; }}
header a {{ color: #fff; }}
header h1 {{ font-size: 1.1rem; margin: 0; font-weight: 600; }}
header .zahlen {{ margin-left: auto; opacity: .85; font-size: .85rem; }}
header form {{ margin-left: auto; }}
header input {{ padding: .35rem .8rem; border-radius: 999px; border: 0;
  background: rgba(255,255,255,.2); color: #fff; width: 15rem; }}
header input::placeholder {{ color: rgba(255,255,255,.7); }}
header input:focus {{ outline: 2px solid #fff; background: rgba(255,255,255,.3); }}

.gruppe {{ margin: 0 0 1.6rem; padding: 1rem; border-radius: 10px;
  background: var(--flaeche); }}
.gruppe h3 {{ margin: 0 0 .8rem; font-size: .95rem; font-weight: 600;
  display: flex; gap: .6rem; align-items: center; }}
.stufe {{ font-size: .75rem; font-weight: 500; padding: .1rem .6rem;
  border-radius: 999px; background: var(--blau); color: #fff; }}
.stufe.lose {{ background: var(--linie); color: var(--leise); }}
.gruppe .raster {{ grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }}
.gruppe .beste {{ outline: 2px solid var(--leucht); }}
.hinweis {{ padding: 1rem 1.2rem; border-radius: 10px; margin-bottom: 1.5rem;
  background: var(--flaeche); border-left: 4px solid var(--blau-hell); }}

nav {{ display: flex; flex-wrap: wrap; gap: .4rem; padding: .8rem 1.2rem;
  border-bottom: 1px solid var(--linie); }}
nav a {{ padding: .25rem .7rem; border-radius: 999px;
  background: var(--flaeche); color: var(--text); font-size: .85rem; }}
nav a.aktiv {{ background: var(--blau); color: #fff; }}
nav a:hover {{ text-decoration: none; outline: 1px solid var(--leucht); }}

main {{ padding: 1.2rem; }}
.raster {{ display: grid; gap: .5rem;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }}
.kachel {{ position: relative; aspect-ratio: 1; background: var(--flaeche);
  border-radius: 8px; overflow: hidden; display: block; }}
.kachel img {{ width: 100%; height: 100%; object-fit: cover; display: block;
  background: var(--flaeche); }}
.kachel .marke {{ position: absolute; bottom: 0; left: 0; right: 0;
  padding: .3rem .5rem; font-size: .72rem; color: #fff;
  background: linear-gradient(transparent, rgba(0,0,0,.75)); }}
.kachel .ecke {{ position: absolute; top: .4rem; right: .5rem;
  font-size: .9rem; text-shadow: 0 1px 3px #000; }}

.blaetter {{ display: flex; gap: .5rem; align-items: center;
  justify-content: center; margin: 1.5rem 0; }}
.blaetter a, .blaetter span {{ padding: .4rem .9rem; border-radius: 6px;
  background: var(--flaeche); }}
.blaetter .jetzt {{ background: var(--blau); color: #fff; }}

.einzel {{ max-width: 1200px; margin: 0 auto; }}
.einzel img, .einzel video {{ max-width: 100%; max-height: 78vh;
  display: block; margin: 0 auto; border-radius: 8px; background: #000; }}
.angaben {{ display: grid; gap: .4rem 1.5rem; margin-top: 1.2rem;
  grid-template-columns: max-content 1fr; font-size: .9rem; }}
.angaben dt {{ color: var(--leise); }}
.angaben dd {{ margin: 0; }}

.karten {{ display: grid; gap: .8rem;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }}
.karte {{ padding: 1rem; border-radius: 10px; background: var(--flaeche); }}
.karte b {{ display: block; font-size: 1.6rem; color: #fff; }}
.karte span {{ color: var(--leise); font-size: .85rem; }}
footer {{ padding: 2rem 1.2rem; color: var(--leise); font-size: .8rem; }}
"""


def zahl(wert: int) -> str:
    """Eine Zahl mit Punkten als Tausendertrennung.

    Als eigene Funktion, weil der naheliegende Weg – die fertige Seite
    durch ``replace(",", ".")`` schicken – hier bereits einmal den
    ``viewport``-Eintrag zerlegt hat: Aus ``width=device-width,initial-
    scale=1`` wurde ein Punkt statt eines Kommas, und die Seite war auf
    dem Handy unbrauchbar. Umformatiert wird die Zahl, nicht das HTML.
    """
    return f"{wert:,}".replace(",", ".")


def _kopf(titel: str, liste: Bestandsliste, suchwort: str = "") -> str:
    gb = liste.gesamtgroesse / 1e9
    return f"""<!doctype html><html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(titel)} – WOLKENErnte</title><style>{STIL}</style></head><body>
<header><h1><a href="/">WOLKENErnte</a></h1>
<form action="/suche"><input type="search" name="q" placeholder="Suchen …"
 value="{escape(suchwort)}" autocomplete="off"></form>
<span class="zahlen">{zahl(len(liste.bilder))} Dateien · {gb:.1f} GB</span></header>
"""


def _fuss() -> str:
    return (f'<footer>WOLKENErnte {__version__} · läuft nur auf diesem Rechner'
            f'</footer></body></html>')


def _navigation(liste: Bestandsliste, jahr: int | None, album: str | None) -> str:
    teile = ['<nav>']
    teile.append(f'<a href="/raster"{"" if jahr or album else " class=aktiv"}>Alle</a>')
    for j, anzahl in liste.jahre():
        aktiv = " class=aktiv" if j == jahr else ""
        teile.append(f'<a href="/raster?jahr={j}"{aktiv}>{j} <span>({anzahl})</span></a>')
    if liste.ohne_datum:
        teile.append(f'<a href="/raster?ohnedatum=1">ohne Datum '
                     f'<span>({len(liste.ohne_datum)})</span></a>')
    teile.append('<a href="/doppelt">Doppelgänger</a>')
    teile.append('</nav>')

    alben = liste.alben()
    if alben:
        teile.append('<nav>')
        for name, anzahl in alben[:20]:
            aktiv = " class=aktiv" if name == album else ""
            teile.append(f'<a href="/raster?album={quote(name)}"{aktiv}>'
                         f'{escape(name)} <span>({anzahl})</span></a>')
        teile.append('</nav>')
    return "".join(teile)


def uebersicht(liste: Bestandsliste) -> str:
    """Die Startseite: Zahlen, Jahre, Alben."""
    mit_ort = sum(1 for b in liste.bilder if b.ort)
    videos = sum(1 for b in liste.bilder if b.ist_video)
    favoriten = sum(1 for b in liste.bilder if b.favorit)

    karten = [
        (zahl(len(liste.bilder)), "Bilder und Videos", "/raster"),
        (zahl(videos), "davon Videos", "/raster?videos=1"),
        (zahl(mit_ort), "mit Ortsangabe", "/raster?ort=1"),
        (zahl(favoriten), "Favoriten", "/raster?favoriten=1"),
        (zahl(len(liste.ohne_datum)), "ohne Datum", "/raster?ohnedatum=1"),
        (f"{len(liste.alben())}", "Alben", None),
        (f"{liste.gesamtgroesse/1e9:.1f} GB", "Größe", None),
    ]

    inhalt = ['<main><div class="karten">']
    for wert, was, ziel in karten:
        innen = f"<b>{wert}</b><span>{was}</span>"
        inhalt.append(f'<a class="karte" href="{ziel}">{innen}</a>' if ziel
                      else f'<div class="karte">{innen}</div>')
    inhalt.append("</div>")

    neueste = liste.bilder[:12]
    if neueste:
        inhalt.append("<h2>Zuletzt aufgenommen</h2>")
        inhalt.append(raster_kacheln(neueste))
    inhalt.append("</main>")

    return (_kopf("Übersicht", liste) + _navigation(liste, None, None)
            + "".join(inhalt) + _fuss())


def raster_kacheln(bilder: list[Bild]) -> str:
    teile = ['<div class="raster">']
    for bild in bilder:
        p = quote(bild.pfad)
        marke = (escape(bild.zeit.strftime("%d.%m.%Y")) if bild.datum_bekannt
                 else "ohne Datum")
        ecke = "▶" if bild.ist_video else ("★" if bild.favorit else "")
        ecke_html = f'<span class="ecke">{ecke}</span>' if ecke else ""
        teile.append(
            f'<a class="kachel" href="/bild?p={p}" title="{escape(bild.name)}">'
            f'<img loading="lazy" src="/vorschau?p={p}" alt="">'
            f'{ecke_html}<span class="marke">{marke}</span></a>'
        )
    teile.append("</div>")
    return "".join(teile)


def raster(
    liste: Bestandsliste, bilder: list[Bild], *, seite: int, je_seite: int,
    jahr: int | None, album: str | None, zusatz: str,
) -> str:
    seiten = max(1, -(-len(bilder) // je_seite))
    seite = max(1, min(seite, seiten))
    ausschnitt = bilder[(seite - 1) * je_seite: seite * je_seite]

    was = f"{jahr}" if jahr else (album or "Alle Bilder")
    inhalt = [f"<main><h2>{escape(str(was))} – {zahl(len(bilder))} Dateien</h2>"]
    inhalt.append(raster_kacheln(ausschnitt))

    if seiten > 1:
        grund = f"jahr={jahr}&" if jahr else (f"album={quote(album)}&" if album else "")
        grund += zusatz
        inhalt.append('<div class="blaetter">')
        if seite > 1:
            inhalt.append(f'<a href="/raster?{grund}seite={seite-1}">← zurück</a>')
        inhalt.append(f'<span class="jetzt">Seite {seite} von {seiten}</span>')
        if seite < seiten:
            inhalt.append(f'<a href="/raster?{grund}seite={seite+1}">weiter →</a>')
        inhalt.append("</div>")
    inhalt.append("</main>")

    return (_kopf(str(was), liste) + _navigation(liste, jahr, album)
            + "".join(inhalt) + _fuss())


def einzeln(liste: Bestandsliste, bild: Bild) -> str:
    p = quote(bild.pfad)
    if bild.ist_video:
        anzeige = (f'<video controls preload="metadata" src="/datei?p={p}">'
                   f'</video>')
    elif bild.direkt_anzeigbar:
        anzeige = f'<img src="/datei?p={p}" alt="{escape(bild.name)}">'
    else:
        # HEIC und Verwandte kann der Browser nicht - dafür gibt es das
        # Vorschaubild, das Pillow erzeugt hat.
        anzeige = f'<img src="/vorschau?p={p}" alt="{escape(bild.name)}">'

    zeilen = [
        ("Datei", escape(bild.name)),
        ("Aufgenommen", bild.zeit.strftime("%d.%m.%Y um %H:%M")
         if bild.datum_bekannt else
         "<i>unbekannt</i> – weder Metadaten noch EXIF gaben etwas her"),
        ("Größe", f"{bild.groesse/1e6:.1f} MB"),
        ("Liegt in", escape(bild.pfad.rsplit("/", 1)[0])),
    ]
    if bild.titel and bild.titel != bild.name:
        zeilen.insert(1, ("Titel", escape(bild.titel)))
    if bild.ort:
        breite, laenge = bild.ort
        zeilen.append(("Ort", f'<a href="https://www.openstreetmap.org/'
                              f'?mlat={breite}&mlon={laenge}#map=15/{breite}/{laenge}"'
                              f' target="_blank" rel="noreferrer">'
                              f'{breite:.5f}, {laenge:.5f}</a>'))
    if bild.alben:
        zeilen.append(("Alben", ", ".join(
            f'<a href="/raster?album={quote(a)}">{escape(a)}</a>' for a in bild.alben)))
    if bild.favorit:
        zeilen.append(("Markiert", "★ Favorit"))

    angaben = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in zeilen)
    inhalt = (f'<main><div class="einzel">{anzeige}'
              f'<dl class="angaben">{angaben}</dl>'
              f'<p><a href="/datei?p={p}" download>Herunterladen</a></p>'
              f"</div></main>")

    return (_kopf(bild.name, liste) + _navigation(liste, None, None)
            + inhalt + _fuss())


def suche(liste: Bestandsliste, wort: str, treffer: list[Bild]) -> str:
    """Die Trefferliste einer Suche."""
    if not wort.strip():
        inhalt = "<main><p>Bitte einen Suchbegriff eingeben.</p></main>"
    elif not treffer:
        inhalt = (f"<main><p>Nichts gefunden für "
                  f"<b>{escape(wort)}</b>.</p>"
                  f"<p>Gesucht wird in Dateinamen, Titeln, Alben und "
                  f"Datumsangaben.</p></main>")
    else:
        inhalt = (f"<main><h2>{zahl(len(treffer))} Treffer für "
                  f"„{escape(wort)}“</h2>"
                  + raster_kacheln(treffer[:300]))
        if len(treffer) > 300:
            inhalt += (f"<p>Angezeigt werden die ersten 300. "
                       f"Mit mehr Wörtern wird die Suche genauer.</p>")
        inhalt += "</main>"
    return (_kopf(f"Suche: {wort}", liste, wort)
            + _navigation(liste, None, None) + inhalt + _fuss())


#: Wie viele Gruppen eine Seite zeigt.
#:
#: **Zwanzig, nicht sechzig.** Bei sechzig Gruppen mit bis zu zwanzig
#: Bildern standen über vierhundert Vorschaubilder auf einer Seite; der
#: Browser brauchte dafür so lange, dass er beim Prüfen in eine
#: Zeitüberschreitung lief. Was ein Programm nicht darstellen kann,
#: kann ein Mensch erst recht nicht vergleichen.
GRUPPEN_JE_SEITE = 20


def doppelt(liste: Bestandsliste, gruppen: list[tuple[list[Bild], str]],
            fertig: bool, seite: int = 1) -> str:
    """Gruppen ähnlicher Bilder, jede für sich zum Vergleichen."""
    if not fertig:
        inhalt = ('<main><div class="hinweis"><b>Die Fingerabdrücke '
                  'werden noch gerechnet.</b><br>Beim ersten Mal dauert '
                  'das einige Minuten. Auf der Kommandozeile zeigt '
                  '<code>wolkenernte doppelt</code> den Fortschritt.'
                  '</div></main>')
        return (_kopf("Doppelgänger", liste) + _navigation(liste, None, None)
                + inhalt + _fuss())

    if not gruppen:
        inhalt = ('<main><div class="hinweis"><b>Keine Doppelgänger '
                  'gefunden.</b><br>Bytegleiche Kopien hat schon das '
                  'Ernten aussortiert; hier ginge es um dasselbe Bild in '
                  'zwei Fassungen – etwa das Original und die Version aus '
                  'einem Messenger.</div></main>')
        return (_kopf("Doppelgänger", liste) + _navigation(liste, None, None)
                + inhalt + _fuss())

    sicher = [g for g, stufe in gruppen if stufe == "dieselbe Aufnahme"]
    ueberzaehlig = sum(len(g) - 1 for g in sicher)
    teile = [f'<main><h2>{zahl(len(gruppen))} Gruppen</h2>'
             f'<div class="hinweis">'
             f'<b>{zahl(len(sicher))} Gruppen zeigen dieselbe Aufnahme</b> in '
             f'mehreren Fassungen – erkennbar am gleichen Dateinamen unter '
             f'Anhängseln wie <code>(1)</code> oder <code>-bearbeitet</code>. '
             f'Dort sind {zahl(ueberzaehlig)} Fassungen überzählig.<br><br>'
             f'Die übrigen <b>sehen nur ähnlich aus</b> – meist '
             f'Serienaufnahmen, die verschiedene Augenblicke zeigen. '
             f'Umrandet ist jeweils die größte Fassung. '
             f'<b>Es wird nichts gelöscht;</b> die Ansicht ist zum '
             f'Vergleichen da.</div>']

    seiten_zahl = max(1, -(-len(gruppen) // GRUPPEN_JE_SEITE))
    seite = max(1, min(seite, seiten_zahl))
    ausschnitt = gruppen[(seite - 1) * GRUPPEN_JE_SEITE: seite * GRUPPEN_JE_SEITE]

    for nummer, (gruppe, stufe) in enumerate(
        ausschnitt, (seite - 1) * GRUPPEN_JE_SEITE + 1
    ):
        nach_groesse = sorted(gruppe, key=lambda b: -b.groesse)
        lose = "" if stufe == "dieselbe Aufnahme" else " lose"
        teile.append(f'<div class="gruppe"><h3>Gruppe {nummer} · '
                     f'{len(gruppe)} Fassungen '
                     f'<span class="stufe{lose}">{escape(stufe)}</span></h3>'
                     f'<div class="raster">')
        for stelle, bild in enumerate(nach_groesse):
            p = quote(bild.pfad)
            rand = " beste" if stelle == 0 else ""
            teile.append(
                f'<a class="kachel{rand}" href="/bild?p={p}" '
                f'title="{escape(bild.pfad)}">'
                f'<img loading="lazy" src="/vorschau?p={p}" alt="">'
                f'<span class="marke">{bild.groesse/1e6:.1f} MB · '
                f'{escape(bild.zeit.strftime("%d.%m.%Y"))}</span></a>')
        teile.append("</div></div>")

    if seiten_zahl > 1:
        teile.append('<div class="blaetter">')
        if seite > 1:
            teile.append(f'<a href="/doppelt?seite={seite-1}">← zurück</a>')
        teile.append(f'<span class="jetzt">Seite {seite} von {seiten_zahl}</span>')
        if seite < seiten_zahl:
            teile.append(f'<a href="/doppelt?seite={seite+1}">weiter →</a>')
        teile.append("</div>")
    teile.append("</main>")

    return (_kopf("Doppelgänger", liste) + _navigation(liste, None, None)
            + "".join(teile) + _fuss())

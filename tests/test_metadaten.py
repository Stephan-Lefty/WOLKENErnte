"""Metadatendateien auswerten – und die Fallen darin umgehen."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from wolkenernte.metadaten import Angaben, MetadatenFehler, aus_json, ist_album


def _json(**felder: object) -> bytes:
    return json.dumps(felder).encode()


#: Ein vollständiger Datensatz.
#:
#: Die ``formatted``-Texte weichen hier **absichtlich** vom Zeitstempel
#: ab: 1563379729 sind 16:08:49 UTC, nicht 20:28:49. So steht es im
#: Beispiel, das in der Recherche kursierte – und genau daran zeigt
#: sich, warum der Text nichts taugt und nur die Zahl zählt.
VOLL = _json(
    title="IMG_0799.HEIC",
    description="Sonnenuntergang",
    creationTime={"timestamp": "1563466129", "formatted": "18.07.2019, 22:28:49 UTC"},
    photoTakenTime={"timestamp": "1563379729", "formatted": "17.07.2019, 20:28:49 UTC"},
    geoData={"latitude": 35.3387, "longitude": 25.1442, "altitude": 15.0},
    geoDataExif={"latitude": 35.3387, "longitude": 25.1442, "altitude": 15.0},
    favorited=True,
)


class DieGrundangaben(unittest.TestCase):
    def test_titel_und_beschreibung(self) -> None:
        a = aus_json(VOLL)
        self.assertEqual(a.titel, "IMG_0799.HEIC")
        self.assertEqual(a.beschreibung, "Sonnenuntergang")

    def test_aufnahmezeit_ist_utc(self) -> None:
        a = aus_json(VOLL)
        self.assertEqual(
            a.aufgenommen, datetime(2019, 7, 17, 16, 8, 49, tzinfo=timezone.utc)
        )

    def test_der_zeitstempel_schlaegt_den_text(self) -> None:
        """In ``VOLL`` behauptet ``formatted`` 20:28:49, der Zeitstempel
        sagt 16:08:49. Gelesen wird die Zahl.

        Diese Abweichung ist nicht erfunden – sie stand so in einem
        Beispiel, das für bare Münze genommen wurde. Wer den Text
        auswertet, liegt hier über vier Stunden daneben.
        """
        a = aus_json(VOLL)
        assert a.aufgenommen is not None
        self.assertNotEqual(a.aufgenommen.hour, 20)
        self.assertEqual(a.aufgenommen.hour, 16)

    def test_hochladezeit_ist_eine_andere(self) -> None:
        """``creationTime`` ist der Zeitpunkt des Hochladens. Wer sie
        für die Aufnahmezeit hält, datiert eingescannte Bilder auf das
        Jahr des Einscannens."""
        a = aus_json(VOLL)
        self.assertNotEqual(a.aufgenommen, a.hochgeladen)
        self.assertGreater(a.hochgeladen, a.aufgenommen)

    def test_ort(self) -> None:
        self.assertEqual(aus_json(VOLL).ort, (35.3387, 25.1442))

    def test_markierungen(self) -> None:
        a = aus_json(VOLL)
        self.assertTrue(a.favorit)
        self.assertFalse(a.papierkorb)
        self.assertFalse(a.archiviert)

    def test_fehlende_felder_sind_kein_fehler(self) -> None:
        a = aus_json(_json(title="x.jpg"))
        self.assertEqual(a.titel, "x.jpg")
        self.assertIsNone(a.aufgenommen)
        self.assertIsNone(a.ort)


class DerNullpunktIstKeinOrt(unittest.TestCase):
    """(0,0) liegt im Golf von Guinea und ist nie eine echte Aufnahme.

    Ein erheblicher Teil der Takeout-Dateien trägt dort Nullen, obwohl
    Google den Ort kennt. Wer sie übernimmt, versammelt seinen halben
    Bestand auf einem Punkt im Atlantik.
    """

    def test_beide_null(self) -> None:
        a = aus_json(_json(
            geoData={"latitude": 0.0, "longitude": 0.0},
            geoDataExif={"latitude": 0.0, "longitude": 0.0},
        ))
        self.assertIsNone(a.ort)

    def test_exif_geht_vor(self) -> None:
        a = aus_json(_json(
            geoData={"latitude": 1.0, "longitude": 1.0},
            geoDataExif={"latitude": 2.0, "longitude": 2.0},
        ))
        self.assertEqual(a.ort, (2.0, 2.0))

    def test_rueckfall_wenn_exif_null_ist(self) -> None:
        a = aus_json(_json(
            geoData={"latitude": 1.0, "longitude": 1.0},
            geoDataExif={"latitude": 0.0, "longitude": 0.0},
        ))
        self.assertEqual(a.ort, (1.0, 1.0))

    def test_nur_eine_koordinate_null_ist_gueltig(self) -> None:
        """Der Nullmeridian und der Äquator sind echte Orte."""
        a = aus_json(_json(geoDataExif={"latitude": 51.5, "longitude": 0.0}))
        self.assertEqual(a.ort, (51.5, 0.0))


class DieZeitstempelFallen(unittest.TestCase):
    def test_formatted_wird_nicht_gelesen(self) -> None:
        """Nur der Zeitstempel zählt – der Text ist übersetzt."""
        a = aus_json(_json(photoTakenTime={"formatted": "17.07.2019, 20:28:49 UTC"}))
        self.assertIsNone(a.aufgenommen)

    def test_null_heisst_unbekannt_nicht_1970(self) -> None:
        a = aus_json(_json(photoTakenTime={"timestamp": "0"}))
        self.assertIsNone(a.aufgenommen)

    def test_leerer_zeitstempel(self) -> None:
        self.assertIsNone(aus_json(_json(photoTakenTime={"timestamp": ""})).aufgenommen)

    def test_unsinniger_zeitstempel(self) -> None:
        a = aus_json(_json(photoTakenTime={"timestamp": "keine Zahl"}))
        self.assertIsNone(a.aufgenommen)


class UnsichereZuordnung(unittest.TestCase):
    """Die wichtigste Regel des Moduls.

    Stammen die Metadaten möglicherweise von einem anderen Bild, dürfen
    Datum und Ort nicht übernommen werden. Titel und Beschreibung schon
    – die gelten auch für eine bearbeitete Fassung.
    """

    def test_datum_und_ort_werden_verschwiegen(self) -> None:
        a = aus_json(VOLL, sicher=False)
        self.assertIsNone(a.aufgenommen)
        self.assertIsNone(a.hochgeladen)
        self.assertIsNone(a.ort)

    def test_titel_und_beschreibung_bleiben(self) -> None:
        a = aus_json(VOLL, sicher=False)
        self.assertEqual(a.titel, "IMG_0799.HEIC")
        self.assertEqual(a.beschreibung, "Sonnenuntergang")

    def test_das_verschweigen_wird_kenntlich_gemacht(self) -> None:
        """»Kein Datum« und »Datum verschwiegen« sind zwei verschiedene
        Aussagen – die Oberfläche muss sie unterscheiden können."""
        self.assertTrue(aus_json(VOLL, sicher=False).unvollstaendig)
        self.assertFalse(aus_json(VOLL).unvollstaendig)

    def test_markierungen_bleiben_ebenfalls(self) -> None:
        self.assertTrue(aus_json(VOLL, sicher=False).favorit)


class AlbumUndSonderfaelle(unittest.TestCase):
    def test_album_wird_erkannt(self) -> None:
        self.assertTrue(ist_album({"title": "Urlaub 2019"}))

    def test_bild_ist_kein_album(self) -> None:
        self.assertFalse(ist_album({"title": "x.jpg", "photoTakenTime": {}}))

    def test_eingewickelte_albumdaten(self) -> None:
        a = aus_json(_json(albumData={"title": "Urlaub"}))
        self.assertEqual(a.titel, "Urlaub")

    def test_kaputte_datei(self) -> None:
        with self.assertRaises(MetadatenFehler):
            aus_json(b"{kein json")

    def test_json_ohne_objekt(self) -> None:
        with self.assertRaises(MetadatenFehler):
            aus_json(b"[1, 2, 3]")

    def test_falsche_datentypen_stuerzen_nicht_ab(self) -> None:
        a = aus_json(_json(title=42, geoData="nirgends", photoTakenTime="jetzt"))
        self.assertEqual(a.titel, "")
        self.assertIsNone(a.ort)
        self.assertIsNone(a.aufgenommen)

    def test_leere_angaben_sind_der_vorgabewert(self) -> None:
        self.assertEqual(aus_json(b"{}"), Angaben())


if __name__ == "__main__":
    unittest.main()

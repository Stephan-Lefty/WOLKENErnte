[Deutsch](README.md) | [English](README.en.md) | [Changelog](CHANGELOG.md) | [TODO](TODO.en.md) | [Guides](docs/README.md)

<p align="center">
  <img src="assets/icon-256.png" alt="WOLKENErnte" width="140">
</p>

# WOLKENErnte

Harvest photos and videos from your clouds – and clear them out over there.

Photos end up scattered: some at Google, some at Apple, some at Proton, plus
OneDrive, Dropbox and your own Nextcloud. WOLKENErnte brings them to a place of
your choosing, orders them by capture date, finds duplicates – and is meant to
delete at the source, on your word, whatever you no longer need.

**What already works:** reading Google Takeout archives, importing images from
folders, finding duplicates, browsing everything in the browser.
**What does not work yet:** fetching from the clouds and deleting there. The
rclone part is still missing – see [TODO.en.md](TODO.en.md).

## What works with which provider

This table is the most important section of this file. The three providers you
think of first when it comes to photos are, of all things, the hardest.

| Provider | list | download | **delete in the cloud** |
|---|:---:|:---:|:---:|
| Nextcloud (WebDAV) | yes | yes | **yes** |
| Dropbox | yes | yes | **yes** |
| Microsoft OneDrive | yes | yes | **yes** |
| Google **Drive** | yes | yes | **yes** |
| Box, pCloud | yes | yes | **yes** |
| iCloud **Drive** | yes | yes | **yes** |
| Proton **Drive** | yes | yes | **yes** |
| **iCloud Photos** | yes | yes | **no** |
| **Google Photos** | no | no | **no** |
| **Proton Photos** | no | no | **no** |

**Google Photos** has been closed to third-party programs since 31 March 2025.
An application now only sees the pictures it uploaded itself – your own library
is out of reach. A delete function never existed there in the first place. The
way around it is *Google Takeout*: you request the archive yourself and
WOLKENErnte processes it. Clearing out afterwards is done by hand in the browser.

**iCloud Photos** can be listed and downloaded in full, but not touched – access
is explicitly read-only. With *Advanced Data Protection* enabled, nothing works
there at all.

**Proton Photos** lives in a separate area that third-party programs cannot see.
There is currently no way in – not even an awkward one.

The evidence for each statement is in [docs/anbieter.md](docs/anbieter.md), with
a date. This situation changes quickly.

## Getting started

```
wolkenernte ernten      ~/Pictures/Archive  ~/Downloads/takeout-folder
wolkenernte erfassen    ~/Pictures/Archive  ~/Downloads/takeout-folder
wolkenernte pruefen     ~/Pictures/Archive  ~/Downloads/takeout-folder
wolkenernte oberflaeche ~/Pictures/Archive
```

**The order is not a matter of taste.** First *ernten* (harvest) – images into
the archive. Then *erfassen* (record) – places, titles and albums into the
database, because those exist only in the sources and would be lost. Then
*pruefen* (verify) – proof that every image really arrived. **And only then**
may a source be deleted.

Further commands: `wolkenernte anbieter` prints the table above,
`wolkenernte bestand` the figures from the database, `wolkenernte doppelt`
searches for similar images.

## The archive

```
Archive/
├── 2023/2023-07/IMG_1234.jpg     ordered by capture date
├── ohne-datum/IMG_5678.jpg       when none could be determined
└── .wolkenernte/
    ├── bestand.db                places, titles, albums, favourites
    └── vorschau/                 thumbnails
```

By date and not by album: an image can be in several albums but only in one
place on disk. Album membership lives in the database.

**Your pictures stay ordinary files.** No custom format, no encryption, no
directory service. Anyone who no longer has WOLKENErnte in ten years opens the
folder with any program they like.

## The interface

`wolkenernte oberflaeche` starts a service and opens the browser: images as
tiles, filters by year and album, search across filenames, titles and albums,
single view with location and capture date, video playback.

**The service listens on 127.0.0.1 only** and cannot be reached from outside. It
shows private photos and has no authentication.

Why the browser and not a window: it can already display images and videos, in
every format the system supports. A desktop application is planned – see
[TODO.en.md](TODO.en.md) – but it costs over a hundred megabytes extra, and
nobody should have to pay that just to look at their photos.

## Installing

**Arch and Manjaro**

```
cd verpacken/arch && makepkg -si
```

**Everywhere else** – the core runs on Python 3.11+ with no third-party packages:

```
python3 -m wolkenernte oberflaeche ~/Pictures/Archive
```

Recommended but not required: **Pillow** for thumbnails and duplicate detection.
Without it the interface serves the originals – slower, but still usable.

## How it is built

The core needs **no third-party packages**. The planned cloud access will be
handled by [rclone](https://rclone.org/), which runs as its own service and is
addressed over an ordinary HTTP interface – `urllib` and `json` from the
standard library are enough for that.

This has a side effect that saves money: because the user creates their own
Google credentials, there is no need for the annual CASA security audit that
Google requires for far-reaching access scopes – 500 to 4,500 US dollars per
year, depending on the assessor.

## Licence

[MIT](LICENSE)

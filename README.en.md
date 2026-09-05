[Deutsch](README.md) | [English](README.en.md) | [Changelog](CHANGELOG.md) | [TODO](TODO.en.md) | [Guides](docs/README.md)

<p align="center">
  <img src="assets/icon-256.png" alt="WOLKENErnte" width="140">
</p>

# WOLKENErnte

Harvest photos and videos from your clouds – and clear them out over there.

Photos end up scattered: some at Google, some at Apple, some at Proton, plus
OneDrive, Dropbox and your own Nextcloud. WOLKENErnte brings them to a place of
your choosing, shows them to you, finds duplicates – and, on your word, deletes
what you no longer need at the source.

**This is scaffolding, not yet a program.** So far WOLKENErnte does exactly one
thing: tell you what is actually possible with each provider. That sounds like
little, but it is the part you need first – see the next section.

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

The evidence for each of these statements is in [docs/anbieter.md](docs/anbieter.md).
This situation changes quickly; the date there tells you how old the information is.

## Why this is needed

There are many good photo managers – immich, PhotoPrism, Ente. All of them are
**destination archives**: they pull pictures in and never touch the source
again. And there are file managers for cloud storage that can delete but cannot
find duplicates. And there are duplicate finders that only work on your own disk.

Not a single free program combines all of it: multiple clouds, preview,
duplicate detection **and** clearing out at the source.

## Trying it out

```
git clone https://github.com/Stephan-Lefty/WOLKENErnte.git
cd WOLKENErnte
python3 -m wolkenernte
```

Prints the provider table along with its limitations. That is all it can do so far.

## How it is built

The core needs **no third-party packages**. The cloud work is done by
[rclone](https://rclone.org/), which runs as its own service and is addressed
over an ordinary HTTP interface – `urllib` and `json` from the standard library
are enough for that. rclone is MIT licensed and may be bundled.

This has a side effect that saves real money: because the user creates their own
Google credentials, there is no need for the annual CASA security audit that
Google requires for far-reaching access scopes – depending on the assessor, 500
to 4,500 US dollars per year.

Everything else is optional and checked at runtime: Pillow and pi-heif for
images, ImageHash for duplicates, ffmpeg for video thumbnails, PySide6 for the
interface.

## Licence

[MIT](LICENSE)

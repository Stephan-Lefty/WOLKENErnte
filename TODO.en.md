[Deutsch](TODO.md) | [English](TODO.en.md) | [Overview](README.en.md) | [Changelog](CHANGELOG.md) | [Guides](docs/README.md)

# TODO

Running list of open items. What is still open comes first. Completed items are
not deleted but moved down – with the date they were finished.

## Open

### The order: whatever can be tested comes first

Available for testing: **Nextcloud, Proton Drive and Google Photos**.
These three come first – not because they are the easiest, but because
everything else would be code that only works on paper. Same rule as
MailBurg and macOS: what has not run is not declared finished.

1. **Nextcloud.** The whole path once, end to end – list, fetch, compare
   checksum, delete – without a third-party provider interfering. No
   browser sign-in, just address, username and app password.
2. **Proton Drive.** The most valuable test of all: the access is
   reverse-engineered, classed as beta, and tends to break after Proton
   updates. This is where it shows how well WOLKENErnte copes with a
   provider that suddenly stops answering. Setup pitfall: the 2FA code
   expires while you are still configuring.
3. **Google Takeout.** Technically unrelated to the rest – not a fetch
   but an archive reader. **Request the archive in good time:** Google
   takes hours to days to produce it.

Only then OneDrive, Dropbox and pCloud (they share the same browser
sign-in flow), and finally iCloud Photos, where only half of it works
anyway.

- [ ] Start using the `erprobt` (tested) field in `anbieter.py` once a
  provider has actually run – and make visible in the interface what is
  merely implemented versus genuinely tested.

### Next up: talking to rclone

- [ ] **Find rclone or bundle it.** Look on the machine first
  (`shutil.which`), otherwise use the bundled binary. Check the version – the
  iCloud backend only exists from 1.69, Photos within it only from 1.74.
- [ ] **Start `rclone rcd` as a child process**, bound to `127.0.0.1`, with
  user and password. **Both are mandatory, not optional:** anyone who reaches
  that interface can run arbitrary commands on the machine via `core/command`
  and read every credential via `config/dump`. A test must pin down that
  nothing works without authentication.
- [ ] List via `operations/list`, progress via `core/stats`, jobs asynchronously
  with `_async: true` and `job/status`.
- [ ] **Delete exclusively through `anbieter.darf_loeschen()`.** No second path,
  no exception.

### Viewing images

- [ ] Thumbnails: try the **embedded preview** first, which HEIC and JPEG carry
  anyway – roughly ten times faster than decoding the full image.
- [ ] Cache following the freedesktop convention (`$XDG_CACHE_HOME/thumbnails/`)
  so that the user's file manager and WOLKENErnte share the same one.
- [ ] HEIC via **pi-heif**, not pillow-heif – the latter's binary wheels contain
  x265 under GPL, which would not sit well with MIT.
- [ ] iPhone images usually carry **Display P3**. Without conversion to sRGB
  they look oversaturated in the interface.

### Videos

- [ ] Thumbnails with **ffmpeg as a separate process**, `-ss` **before** `-i`
  (seek before decoding, orders of magnitude faster on long files). A corrupt
  video then cannot take the program down with it.
- [ ] **HDR material needs tone mapping.** iPhone videos from the 12 onwards are
  HLG/BT.2020; without conversion every thumbnail turns grey and washed out.
  Check `color_transfer` with `ffprobe` first – on SDR material the same chain
  makes the picture worse.
- [ ] Try playback with `QMediaPlayer` first. Only add libmpv if that fails on
  real iPhone material. **Not** python-vlc: it still has no Wayland embedding.

### Finding duplicates

- [ ] **Hash the providers' thumbnails, not the originals.** Drive, OneDrive and
  Dropbox serve previews through their APIs; a perceptual hash over a 256-pixel
  image detects "same photo, different compression" just as well. This saves
  downloading tens of thousands of files before the user has decided anything.
- [ ] Search via **banding** (split the hash into blocks, exact lookup table per
  block), **not** a BK-tree. It is the textbook answer but collapses at exactly
  the thresholds perceptual hashes need – at threshold 8 one measurement had it
  slower than brute-force comparison of all pairs.
- [ ] **Live Photos are a HEIC and MOV pair.** Failing to recognise them as one
  reports a flood of duplicates that are not duplicates. Detect via the
  `ContentIdentifier`, not the filename.

### Google Takeout

- [ ] Read the archive, match metadata from the accompanying JSON files to the
  images (Takeout separates the two).
- [ ] Be honest about deletion: show instructions for clearing out in the
  browser. **No browser automation.** It rides on undocumented internal
  interfaces, breaks without warning, and with Apple it explicitly violates the
  terms of service.

### Interface

- [ ] Grid view with thumbnails, multiple selection, delete basket.
- [ ] **Verify the copy actually arrived before deleting.** Compare checksums
  first, then remove at the source – never the other way round.
- [ ] The delete button only appears where `anbieter.darf_loeschen()` permits
  it. Elsewhere the reason is shown, not a greyed-out button.

### Later

- [ ] Actually try Windows and macOS at all. Nothing has run there yet; the
  entries in `pyproject.toml` say as much.
- [ ] Keep an eye on Proton Drive: the official SDK has existed since January
  2026, but without an authentication module. Once that arrives it becomes the
  clean route – and perhaps the first way into Proton Photos.

## Done

- [x] **Have the name checked.** (2026-09-05) Four candidates examined:
  *CloudFlow* fails on discoverability – "Cloudflow" is a running shoe by On,
  and PyPI, the Play Store and every domain are taken. *MediaDock* has an active
  German word mark against it and a German software product of the same name
  carrying title protection. *MediaMover* would be legally harmless but is a
  generic term with 49 identically named GitHub repositories. *Heimholer* was
  ruled out for its connotations – funerals and National Socialist vocabulary.
  **WOLKENErnte** returns no hits in either trade mark register, and domains and
  package names are free.
- [x] **Establish what is actually possible with each provider.** (2026-09-05)
  Result in `wolkenernte/anbieter.py` and `docs/anbieter.md`.

[Deutsch](TODO.md) | [English](TODO.en.md) | [Overview](README.en.md) | [Changelog](CHANGELOG.md) | [Guides](docs/README.md)

# TODO

Running list of open items. What is still open comes first. Completed items are
not deleted but moved down – with the date they were finished.

## Open

### The actual purpose: harvesting from a cloud

Harvesting, signing in and cleaning up are in place (see *Done*), and signing
in, browsing, fetching, recording and the clean-up dry run have run against a
real Nextcloud. What is missing is the last step.

- [ ] **Deleting for real has never run.** Signing in, picking a folder,
  harvesting and the dry run are proven against a real Nextcloud; `--wirklich`
  is not. That needs a dedicated test folder in the cloud, not one holding
  files in use.
- [ ] **Remove a picture from the archive by hand.** Anyone who harvested
  something they did not want there can only delete it in the file manager,
  and the database learns nothing about it.
- [ ] Progress via `core/stats`, long jobs asynchronously with `_async: true`
  and `job/status`. The harvester currently shows a file count, not a rate.

**Order of providers:** Nextcloud, Proton Drive and Google Photos are available
for testing. Those three first – everything else would be code that only works
on paper. Then OneDrive, Dropbox and pCloud, which share the same browser
sign-in flow; finally iCloud Photos, where only half of it works anyway.

- [ ] Start using the `erprobt` (tested) field in `anbieter.py` once a provider
  has actually run – and show in both interfaces what is merely implemented
  versus genuinely tested.

### Keywords

Both halves run and are measured (see *Done*). What is missing is the route
from there into the database and the interfaces.

- [ ] **Check "Ostern".** It sits at 5.8 % and mostly means spring flowers.
  The same rule as for "Zeichnung" and "Luftaufnahme" applies: measure first,
  then decide – a word that is wrong half the time should go.
- [ ] **Add and remove keywords by hand.** They currently come only from the
  pass; anyone who finds one wrong can do nothing about it. A separate origin
  (`"hand"`) for those, which no pass ever overwrites.
- [ ] **Videos get no keywords from the image.** That changes once ffmpeg can
  supply a still – the bookkeeping already allows for it and leaves videos at
  the "abgeleitet" level.
- [ ] Only fetch the model once the user actually wants image recognition. A
  program that pulls 335 MB unasked on first start is rude.
- [ ] Check whether the INT8 version is good enough: four times smaller (85
  instead of 335 MB), 2.4 times faster. Whether retrieval quality suffers is
  poorly documented – so measure it.

### Desktop application – what is still missing

- [ ] **Fullscreen** with the space bar, without the header.
- [ ] **Removal basket**: multiple selection in the grid, Delete collects, a
  second step carries it out. The delete button only appears where
  `anbieter.darf_loeschen()` permits it – elsewhere the reason is shown, not a
  greyed-out button.
- [ ] **Duplicate view** as in the web interface, with the distinction between
  "same shot" and "similar".
- [ ] **HEIC via pi-heif** as a Pillow plugin; outside macOS, Qt ships no HEIF
  module. For now the single view falls back to the thumbnail there.

### Capture date

- [x] **Repair archives already harvested.** — *Done on 2026-09-09:
  `wolkenernte uhrzeit`, dry run by default, with a log and `--zurueck`.
  Detection goes by the fingerprint of the old calculation, not by a guess, so
  images dated from a Takeout JSON are left alone and the run can be repeated
  freely. It turned out the **folder was never affected**: `zielordner()` reads
  `.year`/`.month` off the time object, and those show the wall clock.*
- [x] **Run it for real against the developer's own archive.** — *Done on
  2026-09-09: 5,017 of 14,105 images put right, shifted by −1 h or −2 h
  depending on daylight saving. Verified afterwards: for all 5,017 the file
  time now matches the EXIF wall clock, a second pass finds 0, and 5,002 rows
  were carried along in the database. The log sits in
  `.wolkenernte/uhrzeit-reparatur.jsonl`.*
- [x] **Files in the archive with no database row.** — *Done on 2026-09-09:
  `wolkenernte erfassen <archive>` now works without a source and reads only
  the archive. 54 images added, afterwards 0 without a row; `verschlagworten`
  gave them keywords (57 → 3, and about those three the model has nothing to
  say either). Places, titles, albums, favourites and origins stayed identical
  down to the number.*
- [x] **The thumbnail cache counted as inventory.** — *Done on 2026-09-09: on
  the first run `erfassen` created a database row for 1,470 thumbnails. The
  same confusion sat in `archiv_kennungen` (the proof that cloud deletion
  hangs on) and in `archiv_ist_leer` (the emergency brake before it). One
  place decides now: `archiv.medien()`.*
- [ ] **Videos from a plain folder have no date.** They carry no EXIF, and
  nobody reads the container's `creation_time` field. Without a Takeout JSON
  beside them every video ends up in `ohne-datum`. `ffprobe` can read it, and
  ffmpeg is a recommendation already.

### Images and videos

- [ ] Thumbnails: try the **embedded preview** first, which HEIC and JPEG carry
  anyway – roughly ten times faster than decoding the full image.
- [ ] Cache following the freedesktop convention (`$XDG_CACHE_HOME/thumbnails/`)
  so the user's file manager and WOLKENErnte share the same one.
- [x] **Video thumbnails** with ffmpeg as a separate process, `-ss` **before**
  `-i` (seek before decoding). A corrupt video then cannot take the program down
  with it. — *Done: all 424 videos yield a frame, median 161 ms, the whole
  archive in 71 seconds. The frame is taken one second in, not at the start
  (there 11 thumbnails are near-black instead of 6, and 10 without structure
  instead of 2); the 30 shorter videos fall back to the start. The 41 videos
  carrying a rotation come out the right way up.*
- [ ] **HDR material needs tone mapping.** Not critical for this archive – it
  holds only five HEVC files – but anyone receiving HDR footage will see grey
  thumbnails. Check `color_transfer` with `ffprobe` first; on SDR material the
  same chain makes the picture worse.

### Duplicates

- [ ] **Hash the providers' thumbnails, not the originals.** Drive, OneDrive and
  Dropbox serve previews through their APIs; a perceptual hash over a 256-pixel
  image detects "same photo, different compression" just as well. This saves
  downloading tens of thousands of files before the user has decided anything.
- [ ] **Live Photos are a HEIC and MOV pair.** Failing to recognise them as one
  reports a flood of duplicates that are not duplicates. Detect via the
  `ContentIdentifier`, not the filename.

### Google Takeout

- [x] Be honest about deletion: say that clearing out has to be done by hand in
  the browser. — *Done on 2026-09-12: it is in the help page
  (*Hilfe → Google-Bilder holen*), along with the reason.* **No browser
  automation.** It rides on undocumented internal interfaces, breaks without
  warning, and with Apple it explicitly violates the terms of service.

### Shipping

**Principle:** whatever WOLKENErnte needs, it either brings along or has the
package manager bring along. Nobody should download rclone by hand.

- [ ] **Upload the AUR package.** **Deliberately postponed – Stephan will do it
  in a few weeks (decided on 2026-09-12).** Nothing to do here until then;
  asking about it again means asking for the fourth time.

  The package itself is not what is missing: `verpacken/aur/` tracks the latest
  version, `nachziehen.py` fetches the source archive on every release and
  computes the checksum from it, and `makepkg -f` builds cleanly. **Only** the
  account access is missing – the public SSH key in the profile on
  aur.archlinux.org, then `git clone
  ssh://aur@aur.archlinux.org/wolkenernte.git`, copy the two files in and push.

  **What prompted it, in case that gets forgotten:** the developer's own machine
  was running 0.3.0 while 0.4.0 and 0.4.1 had long been published – build it
  yourself and nothing tells you a new version exists. Until the AUR,
  `wolkenernte neuigkeiten` closes that gap.
- [ ] **Publish on PyPI** so that `pip install -U wolkenernte` works. Needs an
  account and a token. For everyone not on Arch this is the usual route.
- [ ] **An APT repository** would be the counterpart for Debian and Ubuntu –
  today the `.deb` is a file attached to a release that nobody updates. Cost:
  own signing keys and somewhere to host it.

- [ ] **rclone as a Linux package dependency** once fetching is implemented –
  before that it would be a promise the program does not keep. **At least
  1.75.0.** Arch and Manjaro are current enough; **for Debian stable this is
  open.** If an older version ships there, rclone must go into the .deb.
- [ ] **Bundle rclone on Windows.** No package manager, so `rclone.exe` sits in
  the program folder. Around 70 MB.
- [ ] **ffmpeg via `imageio-ffmpeg`.** Ships the binary, BSD licensed, no system
  installation on any platform.
- [ ] **Check at startup what is present** and state plainly what is missing –
  rather than aborting mid-transfer with a message that reads like a broken
  machine.
- [ ] **Windows: `.exe`** following `MailBurg/werkzeuge/mailburg.spec`, but as a
  **folder** (`--onedir`), not a single file. PySide6 is LGPLv3, which requires
  the user to be able to replace the library.
- [ ] **Try the .deb on a real Debian.** It is built and has been started from
  the unpacked package; it has never been installed – there is no Debian here.
- [ ] **rclone in Debian stable is too old** (below 1.75.0). Either ship rclone
  inside the .deb or point at trixie-backports.

### Credentials

From outside feedback (2026-09-09): "I had wondered how you were going to store
the login credentials securely. rclone answers that, of course." **Only half.**
rclone does store them, but `obscure` is obfuscation, not encryption – `rclone
reveal` undoes it in one line. What protects them today is file mode `0600`.

- [ ] **Allow an encrypted rclone configuration.** rclone's own answer is
  `rclone config password`. Today that does **not** work: `Dienst.starten()`
  passes `--ask-password=false`, because a daemon has no terminal to ask at.
  The way would be `RCLONE_CONFIG_PASS` through the process environment – the
  same reasoning as for `RCLONE_RC_PASS`, since on Linux anyone can read a
  process's command line in `/proc`. Open is **who asks for the master
  password** and how often; asking at every start makes the desktop
  application unusable.
- [ ] **And answer the question behind it honestly:** as long as the photo
  archive beside it consists of ordinary files, an encrypted credential
  protects little – whoever has the machine has the photos. The same reasoning
  killed the startup password in MailBurg. It is still worth doing, because a
  credential opens *someone else's* account, not just your own data.

### Later

- [ ] Actually try Windows and macOS at all. Nothing has run there yet; the
  entries in `pyproject.toml` say as much. `werkzeuge/videoprobe.py` answers the
  video question there in a minute.
- [ ] Keep an eye on Proton Drive: the official SDK has existed since January
  2026, but without an authentication module. Once that arrives it becomes the
  clean route – and perhaps the first way into Proton Photos.

## Done

### Date range with a calendar (2026-09-09)

- [x] **"Everything between … and …"** in both interfaces, images and videos
  alike. The filter lives in the foundation (`bestandsliste.auswahl`), not in
  one interface – otherwise the two drift apart.
- [x] **The calendar comes from the system**: `QDateEdit` with a calendar popup
  in the window, `type="date"` in the browser. A hand-built one would be more
  code and harder to use.
- [x] **Both ends are included.** The comparison is by day, not by instant –
  otherwise the closing day drops out entirely.
- [x] **An incomplete entry means a period**: `2024` is 1 January as a lower
  bound and 31 December as an upper one. February is computed, not guessed.
- [x] **The filter is off at startup** – otherwise the 317 images without a
  capture date would vanish silently. It turns itself on as soon as someone
  changes a date.
- [x] **An unreadable date is reported**, not ignored; otherwise the whole
  archive would be mistaken for the result of the range.
- [x] **Qt's weekend red replaced**: contrast 3,81 on the dark background where
  4,5 is required. Now `ROT_HELL` at 7,07.
- [x] Nine counter-checks, each failing exactly the tests it should.

### Proven against a real Nextcloud (2026-09-07)

Most of this only surfaced there – everything passed against rclone's `local`
backend.

- [x] **The "include subfolders" checkbox did nothing.** `recurse` was hard-wired
  to `True`; anyone cleaning up one folder was shown everything below it.
- [x] **`--ohne-unterordner` was in the help and arrived nowhere.** Hence
  `tests/test_kommandozeile.py`: for every switch, check what reaches the
  callee, not what it is called.
- [x] **Five minutes of apparent freeze before cleanup.** The whole archive was
  hashed to look for 17 images. Now only matching sizes: 296 seconds against
  less than one.
- [x] **The same image from two clouds landed twice.** Duplicate protection only
  applied within a single run.
- [x] **`erfassen` understands cloud accounts** – previously there was no way to
  record places, titles, albums and origins for a cloud. That weighs more for a
  cloud: after cleanup it is empty.
- [x] **The window records origins while harvesting**, since there is no second
  step there.
- [x] **Verified: all 21,044 images from the Google Photos folder are in the
  archive.** `wolkenernte pruefen`, 13.3 minutes.

### Harvesting from a cloud, in the window (2026-09-07)

- [x] **A source modelled on `lokal.py`** reading via rclone – `wolke.py`, with
  the same sequence as before.
- [x] **A "Wolke" menu**: sign in to Nextcloud, browse the folder tree, harvest.
  The tree loads on expansion and shows the image count per folder.
- [x] **Nothing is stored until the connection is proven.** An account that
  exists only on paper would otherwise surface much later.
- [x] **The harvest runs in a background thread**, with progress and cancel.
- [x] **`wolkenernte aufraeumen`** – delete, but only what is provably in the
  archive: same size, same checksum, computed for this run, and only with
  `--wirklich`.
- [x] **`Dienst.art()`**, because `darf_loeschen()` was being handed the account
  *name* rather than its type. Anyone calling their Nextcloud "meinewolke"
  could never have cleaned up anywhere.
- [x] **The cleanup in the window**, with thumbnails: what is not proven
  cannot even be ticked, and the red delete button is deliberately not the
  default one.

### Keywords (2026-09-07)

- [x] **Season, time of day, aspect ratio and origin** derived from what is
  known anyway. Against the real collection: 14,767 images, only 31 without any
  keyword at all.
- [x] **At most five per image.** Assigning twenty describes nothing and only
  adds noise to search. When space runs short, recognised beats derived – the
  season can be recomputed from the date standing right next to it.
- [x] **Camera and phone kept apart**, after a first attempt hung "Kamera" on
  8,589 of 14,767 images.
- [x] **The digits belong to the pattern.** `"20"` in the phone list matched
  every year and nearly every UUID: 1,587 false hits.
- [x] **The term list for image recognition** – 75 German keywords in five
  groups, with English questions alongside.
- [x] **The evaluation** that turns similarities into keywords – groups instead
  of one long list, a threshold per group, no third-party package needed.
- [x] **Fetching, verifying and locating the model** – with SHA-256, without a
  second reach for the network, under `user_data_dir`.
- [x] **Built the CLIP tokenizer ourselves** instead of requiring `tokenizers`
  (Rust, not packaged on Arch). Checked against the real one: 455 sentences,
  zero deviations.
- [x] **Generated `wolkenernte/daten/begriffe.npz`** – 280 KB, in the
  repository. All that is missing to run it is `onnxruntime`.
- [x] **Measured across 400 real images, and the first run was useless:**
  "Regen" on 60 % of all images, 147 of 200 images carrying the full five
  words. Two causes fixed – the silent answer "just a photograph" that lets a
  group stay quiet, and a **computed** rather than hand-set threshold.
  Afterwards: 2.6 words per image, 1.8 % with none, most frequent word 13.5 %.
- [x] **6.4 images per second** on the CPU while the files are in the page
  cache; across the whole collection the disk is the bottleneck, not the maths.
- [x] **The pass** `wolkenernte verschlagworten`, which brings both halves
  together and writes to the database – with progress and a marker so the
  second run only touches what is missing.
- [x] **In both interfaces**: display, filter, search. The groundwork sits once
  in `bestandsliste.py`.
- [x] **No time of day without a time.** 1,465 of 14,476 images carry only a
  date; "Nachtaufnahme" dropped from 2,004 to 539.
- [x] **"Schwarzweiß" is computed, not guessed** – from colour saturation.
- [x] **"Sonnenaufgang" by the clock**, because the model cannot tell it from
  sunset (0.975).

### The desktop application (2026-09-07)

- [x] **PySide6** as an optional dependency, invoked via `wolkenernte fenster`.
- [x] **Virtualised grid view** – the model returns a placeholder immediately
  and loads in the background. With 14,767 images the window is up in half a
  second.
- [x] Thumbnails in the background via `QThreadPool`, sharing the cache with the
  web interface.
- [x] **Videos via `QMediaPlayer`** – verified with `werkzeuge/videoprobe.py`:
  H.264, HEVC and VP9 all play, with frames actually arriving. libmpv is not
  needed; python-vlc would have been ruled out anyway for lacking Wayland
  embedding.
- [x] Keyboard control: arrow keys to browse, Escape to go back.
- [x] Filters by year and album, search across names, titles, albums and dates.

### The rclone connection (2026-09-06)

- [x] Find rclone, check the version, start it as a service.
- [x] **Secured**: `127.0.0.1` only, credentials freshly generated per start and
  passed through the process environment – on Linux anyone can read the command
  line in `/proc`. Never `--rc-no-auth`. Three tests pin this down.
- [x] Set up accounts through rclone's question-and-answer flow, including the
  third state that rclone's own example program forgets.
- [x] `wolkenernte zugang nextcloud` with address normalisation and a live check.
- [x] Four tests against the real rclone using the `local` backend.

### Foundation (2026-09-05 and 2026-09-06)

- [x] **Both interfaces share the core.** The evaluation logic lives in
  `wolkenernte/bestandsliste.py` and knows about no interface.
- [x] Read Takeout archives without unpacking, across all parts.
- [x] Match image to metadata file, with a confidence flag.
- [x] Import into the archive, ordered by capture date, duplicates only once.
- [x] The database alongside: places, titles, albums, favourites.
- [x] Prove every image arrived – before any deletion.
- [x] Duplicates via a home-grown perceptual fingerprint, classified as "same
  shot" versus "similar".
- [x] Web interface with grid, search and duplicate view.
- [x] **Have the name checked.** Four candidates rejected: *CloudFlow* (the
  running shoe makes it undiscoverable), *MediaDock* (active German word mark),
  *MediaMover* (generic term), *Heimholer* (National Socialist connotation).
- [x] **Establish what is actually possible with each provider** – result in
  `wolkenernte/anbieter.py` and `docs/anbieter.md`.

# craft-obs

openSUSE packages for the Craft App Suite, built on the
[Open Build Service](https://build.opensuse.org) (project
[`home:xanaddams:craft`](https://build.opensuse.org/project/show/home:xanaddams:craft))
and installed and updated with zypper.

| Package | Upstream | What it is |
|---|---|---|
| `artcraft-launcher` | [storytold/craft-launcher](https://github.com/storytold/craft-launcher) | Installs and opens the suite; patched to leave repo-installed apps to zypper |
| `photocraft` | [storytold/photocraft](https://github.com/storytold/photocraft) | Image editing, layers, PSD |
| `vectorcraft` | [storytold/vectorcraft](https://github.com/storytold/vectorcraft) | Vector illustration, SVG and PDF |
| `filmcraft` | [storytold/filmcraft](https://github.com/storytold/filmcraft) | Video editing, color and sound |
| `lightcraft` | [storytold/lightcraft](https://github.com/storytold/lightcraft) | Photo library and raw development |
| `pdfcraft` | [storytold/pdfcraft](https://github.com/storytold/pdfcraft) | PDF reading, organizing, signing |
| `effectcraft` | [storytold/effectcraft](https://github.com/storytold/effectcraft) | Motion graphics and visual effects |
| `designcraft` | [storytold/designcraft](https://github.com/storytold/designcraft) | Page layout and publishing |
| `gridcraft` | [storytold/gridcraft](https://github.com/storytold/gridcraft) | Spreadsheets (.xlsx, CSV) |
| `wordcraft` | [storytold/wordcraft](https://github.com/storytold/wordcraft) | Word processing (.docx, ODT, PDF) |
| `deckcraft` | [storytold/deckcraft](https://github.com/storytold/deckcraft) | Presentations (.pptx) |
| `cadcraft` | [storytold/cadcraft](https://github.com/storytold/cadcraft) | 2D CAD (DXF, DWG) |
| `soundcraft` | [storytold/soundcraft](https://github.com/storytold/soundcraft) | Audio recording and mixing |

## Install

Add the repository for your distribution once:

| Distribution | Repository URL |
|---|---|
| openSUSE Slowroll | `https://download.opensuse.org/repositories/home:/xanaddams:/craft/openSUSE_Slowroll/` |
| openSUSE Tumbleweed | `https://download.opensuse.org/repositories/home:/xanaddams:/craft/openSUSE_Tumbleweed/` |
| openSUSE Leap 16.0 | `https://download.opensuse.org/repositories/home:/xanaddams:/craft/16.0/` |

```sh
sudo zypper ar -f -p 90 <repository URL> craft
sudo zypper ref craft      # accept the key "home:xanaddams OBS Project"
sudo zypper in artcraft-launcher pdfcraft photocraft   # or whichever apps you want
```

Key fingerprint: `59D7 D86F 8957 B282 14B4 BAA9 C534 9190 818C 2F9B`.
From then on, `zypper up` (or `zypper dup`) brings in new releases.

## How updates flow

```
storytold tags vX.Y.Z  ->  daily Action bumps upstream.conf, the spec and .changes, commits here
                       ->  Action: git archive + cargo vendor -> two .tar.zst, upload to OBS
                       ->  OBS: build for each repository, sign, publish  ->  zypper up
```

Each folder is one OBS package: `<name>.spec`, `<name>.changes`, `upstream.conf` (the
upstream repo and packaged tag), `_constraints` (build machine size) and any patches.
The Action (`.github/workflows/obs-sync.yml` and `.github/obs-sync.py`) runs daily at
07:17 UTC, on every push to `main`, and on demand (Actions > OBS sync > Run workflow).
OBS builds have no network access, so the Action vendors the Rust crates itself.

## Maintenance

Nothing to do for normal releases. When something needs attention you get an email:

- **OBS build failed** (the last good version stays published): usually upstream moved a
  file or changed what the build needs, or the launcher patch no longer applies. Fix the
  spec or patch here, add a `.changes` entry (newest first), push.
- **GitHub run failed:** check the run log. If you changed your OBS password, update the
  `OBS_PASSWORD` secret. An OBS outage fixes itself on the next daily run.
- **Scheduled runs paused:** GitHub pauses scheduled workflows after 60 days without a
  commit. Re-enable it on the Actions page.
- **Signing key expiry (April 2028):** `osc signkey --extend home:xanaddams`, then accept
  the extended key in zypper once.

## Notes

- Every package installs a marker file, `/usr/share/<name>/distro-package`.
  `artcraft-launcher/distro-managed.patch` makes the launcher check it: it won't replace
  itself, or any Craft app installed from this repository, with upstream's GitHub RPM, and
  tells you to update with zypper instead. Apps that aren't packaged here still come from
  GitHub through the launcher.
- Each app package ships the GUI (`<name>`) and the command-line tool (`<name>-cli`),
  the desktop entry, MIME types, AppStream metadata and icons. Binaries are stripped.
- PdfCraft's Help > Check for updates only opens the GitHub releases page; it never
  installs anything, so it needs no patch.
- Seven apps need Rust 1.95 or newer. Slowroll and Tumbleweed have it. If Leap 16.0's own
  Rust is too old, its builds fail with a message naming the required rustc version; the fix
  is to build Leap against `devel:languages:rust` too (see the Meta snippet below).
- The ArtCraft name, app names and icons belong to their authors and are shipped unmodified.

## Adding another app

Copy one of the app folders (e.g. `gridcraft/`), rename the folder, spec and `.changes`,
set `REPO` and `TAG` in `upstream.conf`, and adjust the spec (the tarballs are named
`<repo-name>-<version>.tar.zst` and `vendor-<version>.tar.zst`). Push: the Action creates
the OBS package and uploads it.

## Recreating this setup elsewhere

1. On <https://build.opensuse.org>, create a project (here `home:xanaddams:craft`) and add
   the distributions under **Repositories** (here Slowroll, Tumbleweed and Leap 16.0;
   i586 disabled). If Leap's Rust is too old, add `devel:languages:rust` (repository
   `16.0`) as an extra path, above the Leap one, in the project's **Meta** tab:
   ```xml
   <repository name="16.0">
     <path project="devel:languages:rust" repository="16.0"/>
     <path project="openSUSE:Leap:16.0" repository="standard"/>
     ...
   </repository>
   ```
2. In this repo's **Settings > Secrets and variables > Actions**, add the secrets
   `OBS_USER` and `OBS_PASSWORD`, and optionally the variable `OBS_PROJECT`
   (default `home:<OBS_USER>:craft`).
3. Run the workflow. The first run vendors and uploads every package (about 50 MB each),
   so it takes up to an hour; OBS then builds them in parallel. Packages are created on
   OBS automatically.

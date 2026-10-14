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
| `figcraft` | [storytold/figcraft](https://github.com/storytold/figcraft) | UI design and prototyping |

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

## Notes

- Every package installs a marker file, `/usr/share/<name>/distro-package`. The launcher
  is patched (`artcraft-launcher/distro-managed.patch`) to check it: it won't replace itself,
  or any Craft app installed from this repository, with upstream's GitHub RPM, and tells you
  to update with zypper instead.
- Each app package ships the GUI (`<name>`) and the command-line tool (`<name>-cli`),
  the desktop entry, MIME types, AppStream metadata and icons.
- The ArtCraft name, app names and icons belong to their authors and are shipped unmodified.

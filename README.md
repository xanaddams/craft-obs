# craft-obs

openSUSE packages for the Craft App Suite, built on the
[Open Build Service](https://build.opensuse.org) and installed and updated with zypper.

Each folder is one OBS package: `<name>.spec`, any patches, and `upstream.conf` (the
upstream repo and the packaged tag). A daily GitHub Action checks upstream for a new
release, bumps the tag and the spec's `Version:`, builds the source tarball and the
vendored Rust crates (OBS builds have no network), uploads everything and commits to OBS,
which builds, signs and publishes.

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

## One-time setup

1. **OBS account.** Sign in at <https://build.opensuse.org> with an openSUSE account.
2. **Project.** In your home project, create a subproject named `craft`
   (giving `home:<obs-user>:craft`). Under **Repositories**, add **openSUSE Slowroll**
   (x86_64, plus aarch64 if wanted). Add Tumbleweed or others the same way later.
3. **Packages.** In that project, create an empty package for each folder here (same name).
4. **GitHub secrets.** In this repo's **Settings > Secrets and variables > Actions**:
   - secret `OBS_USER`: your OBS username
   - secret `OBS_PASSWORD`: your OBS password
   - variable `OBS_PROJECT`: `home:<obs-user>:craft` (optional; that is the default)
5. **First run.** **Actions > OBS sync > Run workflow.** It uploads the package files to
   OBS (about 50 MB, mostly the vendored crates). Follow the build on the package's page;
   a build takes 10-20 minutes.

## Install on Slowroll

Copy the repository URL from the package's **Download package** page on OBS, then:

```sh
sudo zypper ar -f -p 90 https://download.opensuse.org/repositories/home:/<obs-user>:/craft/<repo-name>/ craft
sudo zypper --gpg-auto-import-keys ref craft   # check the key is your OBS project's
sudo zypper in artcraft-launcher
```

From then on, `zypper dup` picks up new releases.

## How updates flow

```
storytold tags vX.Y.Z  ->  daily Action bumps upstream.conf + spec, commits here
                       ->  Action: git archive + cargo vendor -> two .tar.zst, upload to OBS
                       ->  OBS: build for each repository, sign, publish  ->  zypper dup
```

Editing a spec or patch here and pushing to `main` uploads it to OBS straight away.
If a build fails (e.g. upstream changed in a way the spec or patch doesn't handle), OBS
emails you and keeps the last good version published.

## Notes

- Every package installs a marker file, `/usr/share/<name>/distro-package`.
  `artcraft-launcher/distro-managed.patch` makes the launcher check it: it won't replace
  itself, or any Craft app installed from this repository, with upstream's GitHub RPM, and
  tells you to update with zypper instead. Apps it installs that aren't from here (e.g. a
  new app not packaged yet) still come from GitHub.
- Each app package ships the GUI (`<name>`) and the command-line tool (`<name>-cli`),
  the desktop entry, MIME types, AppStream metadata and icons. Binaries are stripped.
- `<name>.changes` is the openSUSE changelog; the workflow adds an entry on every version
  bump. Add one by hand (newest first) when you change a spec or patch.
- PdfCraft's Help > Check for updates only opens the GitHub releases page; it never
  installs anything, so it needs no patch.
- Seven apps need Rust 1.95 or newer. Slowroll and Tumbleweed have it; on Leap 16.0, if the
  build fails on the Rust version, add `devel:languages:rust` as a repository path for the
  Leap target (project > Repositories > the Leap repository > Add additional path).
- The ArtCraft name, app names and icons belong to their authors and are shipped unmodified.

## Adding another app

Copy one of the app folders (e.g. `gridcraft/`), rename the folder, spec and `.changes`,
set `REPO` and `TAG` in `upstream.conf`, and adjust the spec (the tarballs are named
`<repo-name>-<version>.tar.zst` and `vendor-<version>.tar.zst`). Create the matching empty
package on OBS; the Action does the rest.

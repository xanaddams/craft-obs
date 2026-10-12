# craft-obs

openSUSE packages for the Craft App Suite, built on the
[Open Build Service](https://build.opensuse.org) and installed and updated with zypper.

Each folder is one OBS package: `<name>.spec`, any patches, and `upstream.conf` (the
upstream repo and the packaged tag). A daily GitHub Action checks upstream for a new
release, bumps the tag and the spec's `Version:`, builds the source tarball and the
vendored Rust crates (OBS builds have no network), uploads everything and commits to OBS,
which builds, signs and publishes.

| Package | Upstream |
|---|---|
| `artcraft-launcher` | [storytold/craft-launcher](https://github.com/storytold/craft-launcher) |

## One-time setup

1. **OBS account.** Sign in at <https://build.opensuse.org> with an openSUSE account.
2. **Project.** In your home project, create a subproject named `craft`
   (giving `home:<obs-user>:craft`). Under **Repositories**, add **openSUSE Slowroll**
   (x86_64, plus aarch64 if wanted). Add Tumbleweed or others the same way later.
3. **Package.** In that project, create an empty package named `artcraft-launcher`.
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

## Notes on artcraft-launcher

- `distro-managed-self-update.patch` stops the launcher from offering to replace itself
  with upstream's GitHub RPM; zypper owns updates. The spec installs the marker file the
  patch checks for (`/usr/share/artcraft-launcher/distro-package`).
- The launcher still installs the *other* Craft apps from GitHub releases. Once those
  apps have packages here, install them with zypper instead.
- The ArtCraft name and icons are trademarks of the ArtCraft Team, shipped unmodified.

## Adding another app

Copy `artcraft-launcher/`, rename the folder and spec, set `REPO` and `TAG` in
`upstream.conf`, and adjust the spec's build and install steps (the tarballs are named
`<repo-name>-<version>.tar.zst` and `vendor-<version>.tar.zst`). Create the matching empty
package on OBS; the Action does the rest.

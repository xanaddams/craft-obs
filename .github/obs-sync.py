#!/usr/bin/env python3
"""Upload every package folder (one with an upstream.conf) to OBS.

For each package:
  - the source tarball (<name>-<ver>.tar.zst, from `git archive` of the upstream tag) and
    the vendored crates (vendor-<ver>.tar.zst: cargo-vendor/ and cargo-vendor.toml) are built here, unless
    OBS already has them for this version, because build.opensuse.org has no network access
    during builds and doesn't run the cargo_vendor service;
  - the spec, patches and other files in the folder are uploaded when they differ from OBS;
  - files on OBS that are no longer wanted (old tarballs, a stale _service) are dropped;
  - a package that doesn't exist on OBS yet is created;
  - if the spec uses craft-fonts-<ver>.tar.zst, the craft-fonts commit pinned in upstream's
    release workflow is packed too (the fonts upstream's own release builds embed).
Then one OBS commit is made per package that changed, which starts the build.

Env: OBS_USER, OBS_PASSWORD, optional OBS_PROJECT (default home:<OBS_USER>:craft),
optional OBS_API (default https://api.opensuse.org).
"""
import base64
import hashlib
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = os.environ.get("OBS_API", "https://api.opensuse.org")
USER = os.environ["OBS_USER"]
PROJECT = os.environ.get("OBS_PROJECT") or f"home:{USER}:craft"
AUTH = "Basic " + base64.b64encode(f"{USER}:{os.environ['OBS_PASSWORD']}".encode()).decode()
LOCAL_ONLY = {"upstream.conf"}


class ObsError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def obs(method, path, data=None, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=data, method=method, headers={"Authorization": AUTH})
    if data is not None:
        req.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise ObsError(e.code, f"OBS {method} {url}: {e.code}\n{e.read().decode(errors='replace')}") from None


def ensure_package(pkg, summary):
    """Create the OBS package if it doesn't exist yet."""
    try:
        return obs("GET", f"/source/{PROJECT}/{pkg}")
    except ObsError as e:
        if e.code != 404:
            raise
    print(f"  creating package {PROJECT}/{pkg}", flush=True)
    meta = ET.Element("package", name=pkg, project=PROJECT)
    ET.SubElement(meta, "title").text = summary
    ET.SubElement(meta, "description").text = summary
    obs("PUT", f"/source/{PROJECT}/{pkg}/_meta", ET.tostring(meta))
    return obs("GET", f"/source/{PROJECT}/{pkg}")


def spec_summary(pkg_dir):
    for spec in pkg_dir.glob("*.spec"):
        for line in spec.read_text().splitlines():
            if line.startswith("Summary:"):
                return line.split(":", 1)[1].strip()
    return pkg_dir.name


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sh(cmd, cwd=None):
    print(f"  $ {cmd}", flush=True)
    subprocess.run(["bash", "-euo", "pipefail", "-c", cmd], cwd=cwd, check=True)


def read_conf(path):
    conf = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return conf


FONTS_PIN = re.compile(
    r"(?:CRAFT_FONTS_REF|craft-fonts-ref)\s*:\s*([0-9a-f]{40})"
    r"|storytold/craft-fonts[^\n]*\n(?:[^\n]*\n){0,3}?\s*ref:\s*([0-9a-f]{40})")


def fonts_pin(src):
    """The craft-fonts commit upstream's release workflow embeds, at this tag."""
    for wf in sorted((src / ".github" / "workflows").glob("*.y*ml")):
        m = FONTS_PIN.search(wf.read_text())
        if m:
            return m.group(1) or m.group(2)
    return None


def make_tarballs(repo, tag, name, ver, out, fonts=False):
    src = out / "src"
    sh(f"git clone -q --depth 1 --branch {tag} https://github.com/{repo}.git {src}")
    sh(f"git -C {src} archive --prefix={name}-{ver}/ HEAD | zstd -q -19 -T0 -o {out}/{name}-{ver}.tar.zst")
    # cargo vendor prints the [source] replacements for crates.io *and* git dependencies;
    # the spec appends them to .cargo/config.toml.
    sh("cargo vendor --locked --versioned-dirs cargo-vendor > cargo-vendor.toml 2> /dev/null"
       " && grep -q vendored-sources cargo-vendor.toml", cwd=src)
    sh(f"tar --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 -cf - cargo-vendor cargo-vendor.toml"
       f" | zstd -q -19 -T0 -o {out}/vendor-{ver}.tar.zst", cwd=src)
    if fonts:
        # The fonts upstream's release builds embed (CRAFT_FONTS_DIR), at the commit they pin.
        pin = fonts_pin(src)
        if not pin:
            raise RuntimeError(f"{repo} {tag}: no craft-fonts pin found in .github/workflows")
        sh(f"git clone -q --filter=blob:none --no-checkout https://github.com/storytold/craft-fonts.git {out}/craft-fonts"
           f" && git -C {out}/craft-fonts checkout -q {pin}")
        sh(f"tar --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 -cf - craft-fonts/fonts"
           f" craft-fonts/LICENSE-APACHE craft-fonts/LICENSE-MIT craft-fonts/ATTRIBUTION.md"
           f" | zstd -q -19 -T0 -o {out}/craft-fonts-{ver}.tar.zst", cwd=out)


def sync(pkg_dir, comment):
    pkg = pkg_dir.name
    conf = read_conf(pkg_dir / "upstream.conf")
    repo, tag = conf["REPO"], conf["TAG"]
    name, ver = repo.split("/")[1], tag.removeprefix("v").replace("-", "~")  # as in the spec
    print(f"== {pkg}: {repo} {tag} -> {PROJECT}/{pkg}", flush=True)

    listing = ensure_package(pkg, spec_summary(pkg_dir))
    remote = {e.get("name"): e.get("md5") for e in ET.fromstring(listing).iter("entry")}
    wanted = {}  # name -> md5

    for f in sorted(pkg_dir.iterdir()):
        if f.is_file() and f.name not in LOCAL_ONLY:
            wanted[f.name] = md5(f)
            if remote.get(f.name) != wanted[f.name]:
                print(f"  uploading {f.name}", flush=True)
                obs("PUT", f"/source/{PROJECT}/{pkg}/{f.name}", f.read_bytes(), rev="repository")

    tarballs = [f"{name}-{ver}.tar.zst", f"vendor-{ver}.tar.zst"]
    fonts = any("craft-fonts-%{version}.tar.zst" in sp.read_text() for sp in pkg_dir.glob("*.spec"))
    if fonts:
        tarballs.append(f"craft-fonts-{ver}.tar.zst")
    if all(t in remote for t in tarballs):
        for t in tarballs:
            wanted[t] = remote[t]
    else:
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            make_tarballs(repo, tag, name, ver, out, fonts)
            for t in tarballs:
                p = out / t
                print(f"  uploading {t} ({p.stat().st_size // 1024 // 1024} MB)", flush=True)
                with open(p, "rb") as fh:
                    obs("PUT", f"/source/{PROJECT}/{pkg}/{t}", fh.read(), rev="repository")
                wanted[t] = md5(p)

    if wanted == remote:
        print("  OBS already up to date", flush=True)
        return
    dropped = sorted(set(remote) - set(wanted))
    if dropped:
        print(f"  dropping {', '.join(dropped)}", flush=True)
    filelist = ET.Element("directory")
    for n, m in sorted(wanted.items()):
        ET.SubElement(filelist, "entry", name=n, md5=m)
    reply = obs("POST", f"/source/{PROJECT}/{pkg}", ET.tostring(filelist),
                cmd="commitfilelist", comment=comment)
    if b'error="' in reply:
        raise RuntimeError(f"OBS commit for {pkg} reported missing files:\n{reply.decode()}")
    print(f"  committed to {PROJECT}/{pkg}", flush=True)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    comment = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, cwd=root).stdout.strip()
    failed = []
    for conf in sorted(root.glob("*/upstream.conf")):
        try:
            sync(conf.parent, comment or "obs-sync")
        except Exception as e:  # keep going: one broken package shouldn't hold up the rest
            print(f"::error::{conf.parent.name}: {e}", flush=True)
            failed.append(conf.parent.name)
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()

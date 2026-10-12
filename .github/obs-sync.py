#!/usr/bin/env python3
"""Upload every package folder (one with an upstream.conf) to OBS.

For each package:
  - the source tarball (<name>-<ver>.tar.zst, from `git archive` of the upstream tag) and
    the vendored crates (vendor-<ver>.tar.zst, from `cargo vendor`) are built here, unless
    OBS already has them for this version, because build.opensuse.org has no network access
    during builds and doesn't run the cargo_vendor service;
  - the spec, patches and other files in the folder are uploaded when they differ from OBS;
  - files on OBS that are no longer wanted (old tarballs, a stale _service) are dropped.
Then one OBS commit is made per package that changed, which starts the build.

Env: OBS_USER, OBS_PASSWORD, optional OBS_PROJECT (default home:<OBS_USER>:craft),
optional OBS_API (default https://api.opensuse.org).
"""
import base64
import hashlib
import os
import pathlib
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


def obs(method, path, data=None, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=data, method=method, headers={"Authorization": AUTH})
    if data is not None:
        req.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"OBS {method} {url}: {e.code}\n{e.read().decode(errors='replace')}")


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


def make_tarballs(repo, tag, name, ver, out):
    src = out / "src"
    sh(f"git clone -q --depth 1 --branch {tag} https://github.com/{repo}.git {src}")
    sh(f"git -C {src} archive --prefix={name}-{ver}/ HEAD | zstd -q -19 -T0 -o {out}/{name}-{ver}.tar.zst")
    sh("cargo vendor -q --locked --versioned-dirs vendor > /dev/null", cwd=src)
    sh(f"tar --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 -cf - vendor"
       f" | zstd -q -19 -T0 -o {out}/vendor-{ver}.tar.zst", cwd=src)


def sync(pkg_dir, comment):
    pkg = pkg_dir.name
    conf = read_conf(pkg_dir / "upstream.conf")
    repo, tag = conf["REPO"], conf["TAG"]
    name, ver = repo.split("/")[1], tag.removeprefix("v")
    print(f"== {pkg}: {repo} {tag} -> {PROJECT}/{pkg}", flush=True)

    remote = {e.get("name"): e.get("md5") for e in ET.fromstring(obs("GET", f"/source/{PROJECT}/{pkg}")).iter("entry")}
    wanted = {}  # name -> md5

    for f in sorted(pkg_dir.iterdir()):
        if f.is_file() and f.name not in LOCAL_ONLY:
            wanted[f.name] = md5(f)
            if remote.get(f.name) != wanted[f.name]:
                print(f"  uploading {f.name}", flush=True)
                obs("PUT", f"/source/{PROJECT}/{pkg}/{f.name}", f.read_bytes(), rev="repository")

    tarballs = [f"{name}-{ver}.tar.zst", f"vendor-{ver}.tar.zst"]
    if all(t in remote for t in tarballs):
        for t in tarballs:
            wanted[t] = remote[t]
    else:
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            make_tarballs(repo, tag, name, ver, out)
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
        sys.exit(f"OBS commit for {pkg} reported missing files:\n{reply.decode()}")
    print(f"  committed to {PROJECT}/{pkg}", flush=True)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    comment = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, cwd=root).stdout.strip()
    for conf in sorted(root.glob("*/upstream.conf")):
        sync(conf.parent, comment or "obs-sync")


if __name__ == "__main__":
    main()

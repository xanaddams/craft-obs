#
# spec file for package artcraft-launcher
#
# Copyright (c) 2026 Alexander Roldan
#
# Packaged from the upstream source at https://github.com/storytold/craft-launcher
# (MIT OR Apache-2.0). The ArtCraft name and icons are trademarks of the ArtCraft Team
# (docs/brand/LICENSE-brand.txt) and are shipped unmodified.
#

Name:           artcraft-launcher
# Version is rewritten by the set_version service from the upstream tag.
Version:        0.2.1
Release:        0
Summary:        Install, update and launch the Craft App Suite
License:        Apache-2.0 OR MIT
URL:            https://github.com/storytold/craft-launcher
Source0:        craft-launcher-%{version}.tar.zst
Source1:        vendor.tar.zst
# Leave self-updates to zypper: the launcher would otherwise offer to replace this
# package with upstream's GitHub RPM.
Patch0:         distro-managed-self-update.patch
BuildRequires:  cargo >= 1.90
BuildRequires:  cargo-packaging
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
BuildRequires:  zstd
# Windowing and GPU libraries are dlopen()ed at runtime, so rpm can't find them
# automatically. Soname requirements, as in upstream's own nfpm.yaml.
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon-x11.so.0()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       (libvulkan.so.1()(64bit) or libEGL.so.1()(64bit))
Recommends:     xdg-desktop-portal
ExclusiveArch:  x86_64 aarch64

%description
ArtCraft Launcher lists every app in the Craft App Suite (PhotoCraft, LightCraft,
FilmCraft, DesignCraft, VectorCraft, PdfCraft, EffectCraft, WordCraft, DeckCraft,
GridCraft, CADCraft and SoundCraft), installs the right build for this computer,
and opens them from one window or the system tray.

This build is managed by the system package manager and does not update itself.

%prep
%autosetup -p1 -a1 -n craft-launcher-%{version}
# Make sure cargo builds from the vendored crates (in case the vendor tarball
# doesn't carry its own .cargo/config.toml).
if ! grep -q vendored-sources .cargo/config.toml 2>/dev/null; then
cat >> .cargo/config.toml <<'EOF2'

[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF2
fi

%build
export ARTCRAFT_LAUNCHER_BUILD_DATE=$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)
%{cargo_build} -p artcraft-launcher

%install
BIN=$(find target -type f -path '*/release/artcraft-launcher' | head -n1)
install -Dm0755 "$BIN" %{buildroot}%{_bindir}/artcraft-launcher

ID=ai.storyteller.artcraft-launcher
install -Dm0644 packaging/linux/$ID.desktop %{buildroot}%{_datadir}/applications/$ID.desktop
install -d %{buildroot}%{_datadir}/metainfo
sed -e "s/@VERSION@/%{version}/g" \
    -e "s/@DATE@/$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)/g" \
    packaging/linux/$ID.metainfo.xml.in > %{buildroot}%{_datadir}/metainfo/$ID.metainfo.xml
install -d %{buildroot}%{_datadir}/icons
cp -R assets/app-icon/hicolor %{buildroot}%{_datadir}/icons/

# Marker read by Patch0: updates come from the package manager.
install -d %{buildroot}%{_datadir}/artcraft-launcher
echo "Installed from a distribution package; update with zypper." \
    > %{buildroot}%{_datadir}/artcraft-launcher/distro-package

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.artcraft-launcher.desktop
%{buildroot}%{_bindir}/artcraft-launcher --version

%files
%license LICENSE-APACHE LICENSE-MIT NOTICE
%doc README.md ATTRIBUTION.md
%{_bindir}/artcraft-launcher
%{_datadir}/applications/ai.storyteller.artcraft-launcher.desktop
%{_datadir}/metainfo/ai.storyteller.artcraft-launcher.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.artcraft-launcher.*
%{_datadir}/artcraft-launcher/

%changelog

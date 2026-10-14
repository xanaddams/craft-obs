#
# spec file for package deckcraft
#
# Copyright (c) 2026 Alexander Roldan
#
# Packaged from the upstream source at https://github.com/storytold/deckcraft
# (MIT OR Apache-2.0). App names and icons belong to their authors and are shipped unmodified.
#

# openSUSE's %%cargo_build adds full debug info (-C debuginfo=2). We ship no -debuginfo
# package and strip the binaries, and debug info is what pushes the LTO link past 10 GB on
# the aarch64 build workers, so build without it.
%global build_rustflags -Clink-arg=-Wl,-z,relro,-z,now -C debuginfo=0

Name:           deckcraft
# Version is set by the obs-sync workflow from upstream.conf.
Version:        0.6.1
Release:        0
Summary:        Create and present slide decks
License:        Apache-2.0 OR MIT
URL:            https://github.com/storytold/deckcraft
Source0:        deckcraft-%{version}.tar.zst
Source1:        vendor-%{version}.tar.zst
BuildRequires:  cargo >= 1.90
BuildRequires:  cargo-packaging
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
BuildRequires:  shared-mime-info
BuildRequires:  zstd
BuildRequires:  pkgconfig(alsa)
# Windowing and GPU libraries are dlopen()ed at runtime, so rpm can't find them
# automatically. Soname requirements, as in upstream's nfpm.yaml.
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon-x11.so.0()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       (libvulkan.so.1()(64bit) or libEGL.so.1()(64bit))
Recommends:     xdg-desktop-portal
ExclusiveArch:  x86_64 aarch64

%description
DeckCraft builds presentations and slide shows: themes, layouts, shapes,
pictures, tables, charts, transitions and animations. It opens and saves
PowerPoint (.pptx) files and presents them full screen with a presenter view.

This build is managed by the system package manager; update it with zypper.

%prep
%autosetup -p1 -a1 -n deckcraft-%{version}
# cargo-vendor.toml (in the vendor tarball) points crates.io and git dependencies at
# cargo-vendor/ (not vendor/, which some apps use for their own patched crates).
mkdir -p .cargo
cat cargo-vendor.toml >> .cargo/config.toml

%build
%ifarch aarch64
# The aarch64 build workers have less memory: split the final optimisation a little.
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=4
%endif
export DECKCRAFT_BUILD_DATE=$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)
%{cargo_build} -p deckcraft -p deckcraft-cli

%install
for bin in deckcraft deckcraft-cli; do
  install -Dm0755 "$(find target -type f -path "*/release/$bin" | head -n1)" %{buildroot}%{_bindir}/$bin
done
%if 0%{!?_enable_debug_packages:1}
# Without a -debuginfo package nothing strips the binaries.
strip --strip-all %{buildroot}%{_bindir}/deckcraft %{buildroot}%{_bindir}/deckcraft-cli
%endif

ID=ai.storyteller.deckcraft
install -Dm0644 packaging/linux/$ID.desktop %{buildroot}%{_datadir}/applications/$ID.desktop
install -Dm0644 packaging/linux/$ID.mime.xml %{buildroot}%{_datadir}/mime/packages/$ID.xml
install -d %{buildroot}%{_datadir}/metainfo
sed -e "s/@VERSION@/%{version}/g" \
    -e "s/@DATE@/$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)/g" \
    packaging/linux/$ID.metainfo.xml.in > %{buildroot}%{_datadir}/metainfo/$ID.metainfo.xml
(cd assets/app-icon/hicolor && find . -type f \( -name "$ID.png" -o -name "$ID.svg" \)) | while read -r f; do
  install -Dm0644 "assets/app-icon/hicolor/$f" "%{buildroot}%{_datadir}/icons/hicolor/$f"
done

# Marker read by the patched artcraft-launcher: updates come from the package manager.
install -d %{buildroot}%{_datadir}/deckcraft
echo "Installed from a distribution package; update with zypper." \
    > %{buildroot}%{_datadir}/deckcraft/distro-package

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.deckcraft.desktop
%{buildroot}%{_bindir}/deckcraft-cli --version

%files
%license LICENSE-APACHE LICENSE-MIT NOTICE
%doc README.md
%{_bindir}/deckcraft
%{_bindir}/deckcraft-cli
%{_datadir}/applications/ai.storyteller.deckcraft.desktop
%{_datadir}/metainfo/ai.storyteller.deckcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.deckcraft.xml
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.deckcraft.*
%{_datadir}/deckcraft/

%changelog

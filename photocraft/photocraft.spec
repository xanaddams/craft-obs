#
# spec file for package photocraft
#
# Copyright (c) 2026 Alexander Roldan
#
# Packaged from the upstream source at https://github.com/storytold/photocraft
# (MIT OR Apache-2.0). App names and icons belong to their authors and are shipped unmodified.
#

# openSUSE's %%cargo_build adds full debug info (-C debuginfo=2). We ship no -debuginfo
# package and strip the binaries, and debug info is what pushes the LTO link past 10 GB on
# the aarch64 build workers, so build without it.
%global build_rustflags -Clink-arg=-Wl,-z,relro,-z,now -C debuginfo=0

Name:           photocraft
# Version is set by the obs-sync workflow from upstream.conf.
Version:        0.14.0
Release:        0
Summary:        Edit photos and layered PSD documents
License:        (Apache-2.0 OR MIT) AND OFL-1.1
URL:            https://github.com/storytold/photocraft
Source0:        photocraft-%{version}.tar.zst
Source1:        vendor-%{version}.tar.zst
# The fonts upstream's release builds embed: storytold/craft-fonts at the commit the
# app's release workflow pins (packed by the obs-sync workflow).
Source2:        craft-fonts-%{version}.tar.zst
BuildRequires:  cargo >= 1.95
BuildRequires:  cargo-packaging
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
BuildRequires:  shared-mime-info
BuildRequires:  zstd
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
PhotoCraft is an open-source, native image editor with the familiar menus,
shortcuts, panels and tools professionals expect: layers, masks, adjustment
layers, layer styles, type and brushes.

This build is managed by the system package manager; update it with zypper.

%prep
%autosetup -p1 -a1 -n photocraft-%{version}
%setup -q -T -D -a2 -n photocraft-%{version}
# cargo-vendor.toml (in the vendor tarball) points crates.io and git dependencies at
# cargo-vendor/ (not vendor/, which some apps use for their own patched crates).
mkdir -p .cargo
cat cargo-vendor.toml >> .cargo/config.toml

%build
%ifarch aarch64
# The aarch64 build workers have less memory: split the final optimisation a little.
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=4
%endif
export PHOTOCRAFT_BUILD_DATE=$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)
export CRAFT_FONTS_DIR="$PWD/craft-fonts" CRAFT_FONTS_REQUIRED=1
%{cargo_build} -p photocraft -p photocraft-cli --features heif

%install
for bin in photocraft photocraft-cli; do
  install -Dm0755 "$(find target -type f -path "*/release/$bin" | head -n1)" %{buildroot}%{_bindir}/$bin
done
%if 0%{!?_enable_debug_packages:1}
# Without a -debuginfo package nothing strips the binaries.
strip --strip-all %{buildroot}%{_bindir}/photocraft %{buildroot}%{_bindir}/photocraft-cli
%endif

ID=ai.storyteller.photocraft
install -Dm0644 packaging/linux/$ID.desktop %{buildroot}%{_datadir}/applications/$ID.desktop
install -Dm0644 packaging/linux/$ID.mime.xml %{buildroot}%{_datadir}/mime/packages/$ID.xml
install -d %{buildroot}%{_datadir}/metainfo
sed -e "s/@VERSION@/%{version}/g" \
    -e "s/@DATE@/$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)/g" \
    packaging/linux/$ID.metainfo.xml.in > %{buildroot}%{_datadir}/metainfo/$ID.metainfo.xml
(cd assets/app-icon/hicolor && find . -type f \( -name "$ID.png" -o -name "$ID.svg" \)) | while read -r f; do
  install -Dm0644 "assets/app-icon/hicolor/$f" "%{buildroot}%{_datadir}/icons/hicolor/$f"
done

# Licences of the embedded fonts.
mkdir -p fonts-licenses
for f in craft-fonts/fonts/*/OFL.txt; do
  cp "$f" "fonts-licenses/$(basename "$(dirname "$f")")-OFL.txt"
done

# Marker read by the patched artcraft-launcher: updates come from the package manager.
install -d %{buildroot}%{_datadir}/photocraft
echo "Installed from a distribution package; update with zypper." \
    > %{buildroot}%{_datadir}/photocraft/distro-package

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.photocraft.desktop
%{buildroot}%{_bindir}/photocraft-cli --version

%files
%license LICENSE-APACHE LICENSE-MIT NOTICE
%license fonts-licenses/*
%doc README.md
%{_bindir}/photocraft
%{_bindir}/photocraft-cli
%{_datadir}/applications/ai.storyteller.photocraft.desktop
%{_datadir}/metainfo/ai.storyteller.photocraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.photocraft.xml
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.photocraft.*
%{_datadir}/photocraft/

%changelog

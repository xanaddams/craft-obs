#
# spec file for package wordcraft
#
# Copyright (c) 2026 Alexander Roldan
#
# Packaged from the upstream source at https://github.com/storytold/wordcraft
# (MIT OR Apache-2.0). App names and icons belong to their authors and are shipped unmodified.
#

Name:           wordcraft
# Version is set by the obs-sync workflow from upstream.conf.
Version:        0.6.1
Release:        0
Summary:        Write and design documents; open and save Word files
License:        Apache-2.0 OR MIT
URL:            https://github.com/storytold/wordcraft
Source0:        wordcraft-%{version}.tar.zst
Source1:        vendor-%{version}.tar.zst
BuildRequires:  cargo >= 1.90
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
WordCraft is a fast, open-source word processor with a familiar ribbon:
styles, tables, track changes, references, mail merge, and .docx, PDF, ODT,
RTF, HTML and Markdown files. It can be driven by AI agents over MCP.

This build is managed by the system package manager; update it with zypper.

%prep
%autosetup -p1 -a1 -n wordcraft-%{version}
# cargo-vendor.toml (in the vendor tarball) points crates.io and git dependencies at
# cargo-vendor/ (not vendor/, which some apps use for their own patched crates).
mkdir -p .cargo
cat cargo-vendor.toml >> .cargo/config.toml

%build
export WORDCRAFT_BUILD_DATE=$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%%s)}" +%%Y-%%m-%%d)
%{cargo_build} -p wordcraft -p wordcraft-cli

%install
for bin in wordcraft wordcraft-cli; do
  install -Dm0755 "$(find target -type f -path "*/release/$bin" | head -n1)" %{buildroot}%{_bindir}/$bin
done
%if 0%{!?_enable_debug_packages:1}
# Without a -debuginfo package nothing strips the binaries.
strip --strip-all %{buildroot}%{_bindir}/wordcraft %{buildroot}%{_bindir}/wordcraft-cli
%endif

ID=ai.storyteller.wordcraft
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
install -d %{buildroot}%{_datadir}/wordcraft
echo "Installed from a distribution package; update with zypper." \
    > %{buildroot}%{_datadir}/wordcraft/distro-package

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.wordcraft.desktop
%{buildroot}%{_bindir}/wordcraft-cli --version

%files
%license LICENSE-APACHE LICENSE-MIT NOTICE
%doc README.md
%{_bindir}/wordcraft
%{_bindir}/wordcraft-cli
%{_datadir}/applications/ai.storyteller.wordcraft.desktop
%{_datadir}/metainfo/ai.storyteller.wordcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.wordcraft.xml
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.wordcraft.*
%{_datadir}/wordcraft/

%changelog

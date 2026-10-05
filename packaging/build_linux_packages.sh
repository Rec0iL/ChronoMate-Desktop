#!/usr/bin/env bash
# Wrap the PyInstaller onedir build (dist/chronomate) into .deb, .rpm and .tar.gz.
# Usage: packaging/build_linux_packages.sh <version> [outdir]
# Requires: fpm (gem install fpm), rpm (for the .rpm target).
set -euo pipefail

VERSION="${1:?usage: $0 <version> [outdir]}"
VERSION="${VERSION#v}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mkdir -p "${2:-$ROOT/release}" && cd "${2:-$ROOT/release}" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

[ -x "$ROOT/dist/chronomate/chronomate" ] || { echo "dist/chronomate not found - run pyinstaller first" >&2; exit 1; }

# Package layout: /opt/chronomate (app), /usr/bin/chronomate (symlink), desktop entry + icon
mkdir -p "$STAGE/opt" "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/256x256/apps"
cp -a "$ROOT/dist/chronomate" "$STAGE/opt/chronomate"
ln -s /opt/chronomate/chronomate "$STAGE/usr/bin/chronomate"
install -m 644 "$ROOT/packaging/chronomate.desktop" "$STAGE/usr/share/applications/chronomate.desktop"
install -m 644 "$ROOT/packaging/build-icons/chronomate.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/chronomate.png"
chmod -R go-w "$STAGE"

# Generic tarball (portable, no root needed)
tar -C "$ROOT/dist" -czf "$OUT/ChronoMate-${VERSION}-linux-x86_64.tar.gz" chronomate

COMMON=(
  -s dir -n chronomate -v "$VERSION" --iteration 1
  --description "Companion application for HT-X3000 / HT-50 airsoft chronographs"
  --url "https://github.com/Rec0iL/ChronoMate-Desktop"
  --maintainer "Rec0iL <recoil666@gmail.com>"
  -C "$STAGE" opt usr
)

# Debian / Ubuntu
fpm -t deb -p "$OUT/ChronoMate-${VERSION}-linux-amd64.deb" -a amd64 \
  -d libegl1 -d libgl1 -d libxkbcommon-x11-0 -d libxcb-cursor0 -d libfontconfig1 -d libdbus-1-3 \
  --category utils \
  "${COMMON[@]}"

# Fedora / RHEL / openSUSE-style
fpm -t rpm -p "$OUT/ChronoMate-${VERSION}-linux-x86_64.rpm" -a x86_64 \
  -d mesa-libEGL -d mesa-libGL -d libxkbcommon-x11 -d xcb-util-cursor -d fontconfig -d dbus-libs \
  --rpm-compression gzip \
  "${COMMON[@]}"

ls -la "$OUT"

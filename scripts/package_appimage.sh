#!/usr/bin/env bash
# Build Omega Thrust's Linux AppImage from its Linux release zip.
#
# The zip (scripts/package_release.sh) holds the release: the executable and
# everything it reads beside it. The AppImage keeps the executable in
# usr/bin/ and the rest in usr/share/omegathrust/; packaging/linux/AppRun
# copies that into a writable data folder, since the runtime reads and writes
# its files beside the file it was started as. linuxdeploy adds the shared
# libraries that the executable needs and a Linux system may lack, and
# appimagetool packs the folder with the AppImage runtime. All three tools are
# pinned by version and sha256, and downloaded once into the tools folder.
#
# Usage: scripts/package_appimage.sh <release zip> [<out dir>]
# Writes <out dir>/omegathrust-<version>-linux-x64.AppImage and a .sha256
# beside it; <out dir> defaults to the zip's folder. Tools folder:
# $APPIMAGE_TOOLS_DIR, default .cache/appimage-tools/.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
ZIP=$(realpath "${1:?usage: $0 <release zip> [<out dir>]}")
OUT=$(realpath -m "${2:-$(dirname "$ZIP")}")
TOOLS=$(realpath -m "${APPIMAGE_TOOLS_DIR:-$ROOT/.cache/appimage-tools}")

LINUXDEPLOY_URL=https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20251107-1/linuxdeploy-x86_64.AppImage
LINUXDEPLOY_SHA256=c20cd71e3a4e3b80c3483cef793cda3f4e990aca14014d23c544ca3ce1270b4d
APPIMAGETOOL_URL=https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage
APPIMAGETOOL_SHA256=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
RUNTIME_URL=https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64
RUNTIME_SHA256=2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d

# fetch <url> <sha256> <file>: download the file unless it is already there
# with that sha256, and refuse one that does not match.
fetch() {
    local url=$1 sha=$2 file=$3
    if [[ ! -f $file ]] || ! echo "$sha  $file" | sha256sum --check --status; then
        curl -fsSL --http1.1 --retry 5 --retry-all-errors -o "$file.part" "$url"
        echo "$sha  $file.part" | sha256sum --check --quiet
        mv -- "$file.part" "$file"
    fi
    chmod +x "$file"
}

mkdir -p "$TOOLS" "$OUT"
fetch "$LINUXDEPLOY_URL" "$LINUXDEPLOY_SHA256" "$TOOLS/linuxdeploy-x86_64.AppImage"
fetch "$APPIMAGETOOL_URL" "$APPIMAGETOOL_SHA256" "$TOOLS/appimagetool-x86_64.AppImage"
fetch "$RUNTIME_URL" "$RUNTIME_SHA256" "$TOOLS/runtime-x86_64"

WORK=$OUT/appimage-work
rm -rf -- "$WORK"
mkdir -p "$WORK/zip"
unzip -q "$ZIP" -d "$WORK/zip"
VERSION=$(tr -d '[:space:]' < "$WORK/zip/psx_game_version.txt")

APPDIR=$WORK/AppDir
PAYLOAD=$APPDIR/usr/share/omegathrust
mkdir -p "$APPDIR/usr/bin" "$PAYLOAD"
mv -- "$WORK/zip/Omega_Thrust" "$APPDIR/usr/bin/Omega_Thrust"
cp -a "$WORK/zip/." "$PAYLOAD/"
install -m 0755 "$ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/linux/omegathrust.desktop" "$WORK/omegathrust.desktop"
cp "$PAYLOAD/assets/psxrecomp.png" "$WORK/omegathrust.png"

# The tools are AppImages themselves; this lets them run without FUSE.
export APPIMAGE_EXTRACT_AND_RUN=1
# linuxdeploy's own strip (binutils 2.35) cannot read the .relr.dyn sections
# that current toolchains give shared libraries, and linuxdeploy then fails.
# The libraries it copies come stripped from their distribution, and the
# executable stays as it is in the zip.
NO_STRIP=1 "$TOOLS/linuxdeploy-x86_64.AppImage" --appdir "$APPDIR" \
    --executable "$APPDIR/usr/bin/Omega_Thrust" \
    --desktop-file "$WORK/omegathrust.desktop" \
    --icon-file "$WORK/omegathrust.png"

IMAGE=$OUT/omegathrust-$VERSION-linux-x64.AppImage
ARCH=x86_64 "$TOOLS/appimagetool-x86_64.AppImage" \
    --runtime-file "$TOOLS/runtime-x86_64" "$APPDIR" "$IMAGE"
(cd "$OUT" && sha256sum "$(basename "$IMAGE")" > "$(basename "$IMAGE").sha256")
rm -rf -- "$WORK"
cat "$IMAGE.sha256"

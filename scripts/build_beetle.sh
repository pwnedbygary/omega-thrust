#!/usr/bin/env bash
# Build psx-beetle, the framework's Beetle PSX oracle, out of tree in
# .cache/beetle/, following psxrecomp/docs/beetle-linux.md. The framework
# sources are archives of the commits that HEAD pins for psxrecomp and its two
# nested submodules, so the submodule checkout is never written to.
# beetle-psx-libretro is cloned at the commit the doc pins, with the
# framework's patches applied in the doc's order, beside the archived runtime/,
# where the runtime's CMakeLists.txt expects it. The first run needs network
# access for the clone. Usage, from the repository root:
#   bash scripts/build_beetle.sh        (JOBS=N sets the parallel jobs; default 4)
set -euo pipefail
[ -d psxrecomp ] && [ -f framework_pins.txt ] || { echo "run from the repository root" >&2; exit 1; }
B=.cache/beetle
BEETLE_REV=5759277be50052b9f3f388578bf56cc7899d833f  # 5759277b in psxrecomp/docs/beetle-linux.md
JOBS=${JOBS:-4}

pin() {  # the commit that commit $1 of repository $3 records for submodule path $2
  git -C "$3" ls-tree "$1" "$2" | awk '$2 == "commit" {print $3}'
}
fw=$(pin HEAD psxrecomp .)
net=$(pin "$fw" lib/recomp-net psxrecomp)
rbe=$(pin "$fw" lib/retcomm-rbengine psxrecomp)
[ -n "$fw" ] && [ -n "$net" ] && [ -n "$rbe" ] || { echo "cannot read the framework pins" >&2; exit 1; }

rm -rf "$B/psxrecomp" "$B/build"
mkdir -p "$B/psxrecomp/lib/recomp-net" "$B/psxrecomp/lib/retcomm-rbengine"
git -C psxrecomp archive "$fw" | tar -x -C "$B/psxrecomp"
git -C psxrecomp/lib/recomp-net archive "$net" | tar -x -C "$B/psxrecomp/lib/recomp-net"
git -C psxrecomp/lib/retcomm-rbengine archive "$rbe" | tar -x -C "$B/psxrecomp/lib/retcomm-rbengine"
echo "framework: psxrecomp $fw recomp-net $net retcomm-rbengine $rbe"

if [ ! -d "$B/beetle-psx.git" ]; then
  git clone --bare https://github.com/libretro/beetle-psx-libretro.git "$B/beetle-psx.git"
fi
if ! git -C "$B/beetle-psx.git" cat-file -e "$BEETLE_REV^{commit}" 2>/dev/null; then
  git -C "$B/beetle-psx.git" fetch origin '+refs/heads/*:refs/heads/*'
fi
git clone -q "$B/beetle-psx.git" "$B/psxrecomp/beetle-psx"
git -C "$B/psxrecomp/beetle-psx" checkout -q "$BEETLE_REV"
echo "beetle-psx: $(git -C "$B/psxrecomp/beetle-psx" rev-parse HEAD)"
for p in wtrace_hook sio_trace_hook cdcmd_trace_hook rtrace_irq_hook \
         guest_cycles_hook cdc_dma_peek_hook spu_event_hook; do
  git -C "$B/psxrecomp/beetle-psx" apply "../docs/beetle_$p.patch"
  echo "applied beetle_$p.patch"
done

# STATIC_LINKING=1 makes mednafen_psx_libretro.so an ar archive; cmake expects
# it as libmednafen_psx.a.
nice -n 19 make -C "$B/psxrecomp/beetle-psx" platform=unix STATIC_LINKING=1 HAVE_LIGHTREC=0 -j"$JOBS"
cp "$B/psxrecomp/beetle-psx/mednafen_psx_libretro.so" "$B/psxrecomp/beetle-psx/libmednafen_psx.a"
cmake -S "$B/psxrecomp/runtime" -B "$B/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DPSX_RECOMP_UI=OFF -DPSX_DEBUG_TOOLS=ON -DPSXRECOMP_ALLOW_NO_BIOS=ON
nice -n 19 ninja -C "$B/build" -j"$JOBS" psx-beetle
sha256sum "$B/build/psx-beetle"
echo "psxrecomp submodule, porcelain with ignored files:"
git -C psxrecomp status --porcelain --ignored

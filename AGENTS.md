# Omega Thrust — repository instructions

This repository follows the global engineering protocol: scope, minimal change,
verify, bookkeeping, frozen snapshot, independent read-only review,
explicit-path commit, non-force push. This file adds only repository-specific
facts. Framework rules for game work are in `psxrecomp/CLAUDE.md` (RULE -1:
faithful core, no per-game hacks; §4: never modify generated code; §14: unknown
is acceptable, guessing is not; §16: Beetle oracle).

## Pins

Bump a pin only as its own reviewed change. Never edit files in a submodule
checkout; a framework fix goes through the fork (below). Do not run
`git submodule update --remote`: `.gitmodules` sets `branch = master` for both
submodules, so it would move the pins.

| Path | Commit | Source |
|---|---|---|
| `psxrecomp` | `898d834cd90413659c863b432e6ef932ad5d0e81` | psxrecomp nightly 20261007 (`8077e71`) plus one fix, in the fork pwnedbygary/psxrecomp |
| `psxrecomp/lib/recomp-net` | `e2491d2a78e37fb18fca087ebc34ad8261caae9c` | nested pin, unchanged since `8077e71` |
| `psxrecomp/lib/retcomm-rbengine` | `2a03e73693acee0fb78076ea058642c931bef12e` | nested pin, unchanged since `8077e71` |
| `recomp-ui` | `864f77802ba3191a9b955ddc23de7e624b6d83a2` | paired with `8077e71` in the gitlinks of mstan/TombaRecomp@43915ca |

`bash psxrecomp/tools/ci/record_pins.sh --root .` must print the same SHAs as
`framework_pins.txt`.

A framework fix we cannot wait for goes into the fork that `.gitmodules`
names, as one commit on a branch from the commit we pin, and the pin moves to
it as its own reviewed change. Each such fix is reported upstream. An update
to an upstream commit that fixes the same issue drops the fork's commit; an
update to one that does not yet fix it applies the commit again, on a new
branch from that upstream commit. Never delete or force-push a fork branch:
every commit here that pins it needs it to stay fetchable. Now: `898d834` on
branch `omega-thrust/keybinds-beside-exe`, which makes the runtime read
`keybinds.ini` from the executable's directory (psxrecomp#752). A clone made
before the pin moved to the fork must run `git submodule sync --recursive`
once; until then it fetches `psxrecomp` from upstream, which lacks `898d834`.

## Disc

Omega Boost (USA), SCUS-94449, one MODE2/2352 track. The bin must match
`game.toml` `[prepare_disc]`: 582616272 bytes, CRC32 `2f89bc87`, SHA-1
`772c58d8af1b69cfeb53e0763cab71ee431ed37b`. Volume ID `OMEGABOOST`; boot EXE
`SCUS_944.49`, sha256
`d9477ba8e9ade1d58aae35bf9aeff9071295b6a46b6f8020aeb857f0a2a0f541` (recorded
here because `disc_probe.json` is not tracked). To prepare the disc from a CHD:

```sh
mkdir -p disc && chdman extractcd -i "<path>/Omega Boost.chd" \
  -o "disc/Omega Boost (USA).cue" -ob "disc/Omega Boost (USA).bin"
```

## Never commit

- `disc/`, `bios/`, `*.bin`, `*.cue`, `*.chd`, any retail BIOS dump, or C derived from one.
- `overlay_captures.*` (verbatim game code: the capture store, its `.d` history
  and the `.addendum.jsonl` capture history), `/.cache/`, `/analysis/`.
- `disc_probe.json` (absolute local path), `settings.toml`, `*.cfg`,
  `.psxrecomp.env`, `.env`, build directories.
- Memory card images and save files (`*.mcd`, `*.mcr`, `*.gme`), such as the
  unlocked save in `.cache/saves/`.
- Zone data from `scripts/zones/zone_data.py`: its dumps (`*.zone.toml`), the
  zone files it builds and its packages (`*.psxmod`) hold data from the disc.

If `[runtime] overlay_capture_history` is ever enabled, put
`overlay_capture_persist_dir` under `.cache/`: its
`<game_id>_<session>_<seq>_<sig>.json` snapshots are full capture copies and
no ignore pattern matches them elsewhere. For the same reason, keep a store
named by `PSX_OVERLAY_CAPTURES` outside the repository or under `.cache/`; the
ignore pattern matches only the default `overlay_captures.*` names.

`generated/` is committed but never hand-edited: change the seeds or
`aot/overlays.json`, or take a recompiler fix through a reviewed pin bump, then
regenerate.

## Verified commands

Run framework Python tools with `PYTHONDONTWRITEBYTECODE=1` so the `psxrecomp`
submodule stays clean.

```sh
# Refresh the local disc_probe.json; tracked probe outputs go to a scratch dir
# and must come out byte-identical to the committed files, except the
# game.toml window_title line (see Naming).
SCRATCH=$(mktemp -d)
PYTHONDONTWRITEBYTECODE=1 python3 psxrecomp/tools/new_project_layout/probe_disc.py "$PWD/disc/Omega Boost (USA).cue" \
  --json-out "$PWD/disc_probe.json" \
  --write-game-toml "$SCRATCH/game.toml" --write-catalog "$SCRATCH/catalog_identity.json" \
  --write-seeds "$SCRATCH/ghidra_funcs.txt" --write-boot-exe "$SCRATCH/disc" \
  --disc-rel "disc/Omega Boost (USA).cue" --out-dir disc --players 1 \
  --display-name "Omega Thrust" \
  --description "Native PC recompilation of Omega Boost (PlayStation, 1999), built with psxrecomp. Requires your own disc." \
  --publisher "Sony Computer Entertainment" --year 1999 --region USA

bash psxrecomp/tools/ci/check_boot_exe.sh .
bash psxrecomp/tools/ci/check_bios_stamps.sh --framework psxrecomp
cmake -S . -B build-scaffold-check -G Ninja -DCMAKE_BUILD_TYPE=Release   # configure only
```

Generate the game C (`generated/`, committed) and build. `generate` first runs
an incremental build of the emitters with the system clang. It builds them in
the project-root `build-recompiler/` only if emitters already exist there, and
otherwise inside the submodule at `psxrecomp/recompiler/build`, so on a fresh
checkout run `build_emitters.sh` once first, as the upstream scaffold does. That
script uses CMake's default compiler (GCC on this host) and writes no toolchain
stamp, so the next `generate` rebuilds `build-recompiler/` once with clang;
later runs are incremental (`--force-emitters` wipes and rebuilds it). The
output is byte-identical across runs. The runtime builds use the system GCC and
the CI template flags; `build-dev` adds the TCP debug server (127.0.0.1:4370).

`generate` then builds the static overlay shard that `aot/overlays.json`
declares (`static_output`). Working from the original disc only, never from
overlay captures, it checks the disc SHA-1 and four scene-loader instructions
(0x80075AF4 to 0x80075B00, which put a scene's data at 0x80120000 when the
scene has no `.BIN`), takes the 25 scene `.BIN` files whole at 0x80120000,
translates the overlay functions it finds statically into C variants guarded by
the CRC of the bytes they came from, and writes `generated/overlays_static.c`,
`overlays_static_0000.c` to `overlays_static_0024.c` and `AOT_STATIC_AUDIT.json`
(work files in `.cache/aot-static/`). It reuses the shard and prints
`RESULT_STATIC=reused` only if the generation inputs recorded in the audit are
unchanged (profile, `game.toml`, disc, recompiler binary and its cache tag,
CPS mode, gcc path, framework tool hashes, mod packages) and the published
files still match the audit's hashes
(`psxrecomp/tools/aot_overlay_pipeline.py:932-1001`). Otherwise it rebuilds
the shard, as `--force-aot-static` always does. The audit identifies the
recompiler by the sha256 of its binary, so a recompiler binary that differs,
or another gcc path (the audit records `/usr/bin/gcc`), triggers a rebuild;
rebuilding the emitters from the same sources with the same toolchain gives
the same binary, so a fresh checkout's `generate` and `--force-emitters` keep
the shard. A new clang on the host does trigger a rebuild: `generate` sees the
toolchain change, rebuilds the emitters from scratch and then the shard (after
clang 23.1.3 arrived, the C came out the same and only the audit changed).
Every rebuild rewrites the audit: its `recipe_input_sha256` hashes an
inventory of files in a new temporary work directory, so it changes every
time, even when a forced rebuild with unchanged inputs writes the same C.
`CMakeLists.txt` links the shard through `GAME_OVERLAY_STATIC_C` (see the
comment there on where it may go), and configure fails if that and
`static_output` disagree. Overlay code the shard does not cover still runs in
the interpreter.

The runtime build and the static overlay step write one file inside the
submodule, whenever it is missing or stale: the framework's
`psxrecomp/runtime/include/overlay_codegen_hash.h`
(`psxrecomp/runtime/runtime.cmake:1778`,
`psxrecomp/tools/aot_overlay_pipeline.py:902-920`), which `psxrecomp/.gitignore:76`
ignores. It cannot be redirected without patching the submodule.
`git -C psxrecomp status --porcelain --ignored` should list only that file.

```sh
bash psxrecomp/tools/ci/build_emitters.sh   # once, while build-recompiler/ has no emitters
PYTHONDONTWRITEBYTECODE=1 python3 psxrecomp/psxrecomp_cli.py generate --config game.toml \
  --project-root . --disc "disc/Omega Boost (USA).cue" --no-toolchain-download
bash psxrecomp/tools/ci/check_generated.sh --root .   # needs generated/ staged or committed

cmake -S . -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DPSXRECOMP_REQUIRE_GAME_C=ON -DPSXRECOMP_BIOS_STALE_FATAL=ON \
  -DPSXRECOMP_FORCE_SETUP_HOST=OFF -DPSXRECOMP_ALLOW_NO_BIOS=OFF -DPSX_SETUP_WIZARD=ON
cmake --build build-release --target psx-runtime -j6
# build-dev: the same two commands with -B build-dev / --build build-dev and
# -DPSX_DEBUG_TOOLS=ON added to the configure.
```

## Running

If the shell exports `APPIMAGE` (for example an agent hosted in an AppImage),
the runtime resolves every exe-relative file (`game.toml`, the bundled BIOS,
settings, mod state) beside that AppImage, so launch with `env -u APPIMAGE`.
Run from a scratch working directory: the runtime writes
`psx_last_run_report.json` to the cwd. Headless run with the debug server,
starting from the repository root:

```sh
REPO=$PWD
RUN=$(mktemp -d)
mkdir "$RUN/memcards"
cd "$RUN"
env -u APPIMAGE "$REPO/build-dev/Omega_Thrust" --headless --game "$REPO/game.toml" \
  --disc "$REPO/disc/Omega Boost (USA).cue" --memcard-dir "$RUN/memcards" --debug-port 4370
```

`PSX_BIOS_HLE=0` selects the LLE boot, and `--bios <SCPH-1001 v2.2 dump>` the
retail BIOS (never copied into the repository). The debug server answers one
JSON request per TCP connection, and its I/O thread answers `ping` itself
without frame data, so poll `frame`.

Without `--headless` the launcher opens and writes `keybinds.ini`,
`config.ini`, `input.ini` and `launcher-window.ini` beside the executable. A
windowed run with `--no-launcher` writes `input.ini` and `keybinds.ini` there
when they are missing (`load_input_config()`); headless runs write neither.
When it closes, by PLAY or by Quit, the launcher saves `settings.toml` there
and writes `[controller] multitap_analog` into the `game.toml` that `--game`
names (`psxrecomp/runtime/src/main.cpp:16157-16421`); PLAY also writes
`bios.cfg` and `disc.cfg` (`main.cpp:16439-16594`). Every later run from that
directory, headless included, reads `settings.toml` (renderer, internal
resolution, supersampling, texture filtering, controller and multitap
settings, and the BIOS, disc and memory card paths; `main.cpp:15062-15078`)
and `bios.cfg` (an explicit BIOS choice; `main.cpp:3004-3017`). So run the
launcher only from a copy of the build outside `build-dev/`, such as
`.cache/play/build/`, with `--game` naming that copy's `game.toml`.
`build-dev/` must hold none of those files, and the tracked `game.toml` must
stay unchanged.

Run one runtime per build directory at a time. Every launch commits the mod
selection (`psxrecomp/runtime/src/main.cpp:16635-16638`; `save_selection`
defaults to true, `psxrecomp/runtime/include/mod_runtime.h:22`, and is checked
at `psxrecomp/runtime/src/mod_runtime.cpp:1647`) to `<build>/mods/state.toml`
through the fixed temporary name `state.toml.tmp`
(`psxrecomp/runtime/src/mod_packages.cpp:2826-2904`), so a second launch from
the same build at the same moment can exit with "cannot launch with selected
mods: cannot publish state".

## Routes

`scripts/routes/run_route.py` plays a route on the headless dev build. Routes
use the format of `psxrecomp/tools/perf_routes/`: `steps` of `frames` and
`buttons`, the inverted pad word (65535 neutral, 65527 Start; bit names in
`psxrecomp/tools/pad_trace.py`), plus optional `note` and `shot` keys. The
runtime plays the steps itself (`input_route_*` debug commands), one step frame
per runtime frame, so input timing is exact relative to the route's start
frame, which varies between runs. The runner takes each shot after its step has
ended, a few frames late, so end every shot step at least 30 frames before the
next button change; each record holds the frame read just before the
screenshot. A failed screenshot (for example "display disabled") is recorded
and does not fail the run.

A run fails if the boot banner in `runtime.log` (`bios_boot=`, `image=`) does
not match `--mode`, the runtime exits early, the route stops early or times
out, or `dispatch_stats` reports an unknown-dispatch or segment miss. The
runner sets `PSX_BIOS_HLE` for the mode and removes `PSX_BIOS_HLE_KEEP_INTRO`
and `APPIMAGE`. It accepts `--bios` only for `lle-scph1001`, refuses a port
that already accepts connections, and sends commands only after its own
runtime prints `debug server LISTENING`. It writes `result.json`,
`runtime.log`, the screenshots and the runtime's `cwd/` and `memcards/` to
`.cache/routes/<name>/<mode>/`, where `<name>` is the route's `name`. It reuses
an output directory only if the directory is empty or holds a `result.json`
written by the runner, and then deletes only its own earlier outputs. A run
refused before launch (bad arguments, a busy port) leaves the output directory
untouched, so a `result.json` there may be an earlier run's; trust the runner's
exit status. Two runs of the same route and mode share an output directory, so
run routes one at a time.

The runtime's exit code 2 (the runner then exits 1) with a
`cwd/starvation_dump.jsonl` means its starvation watchdog fired after 4 s
without a heartbeat (`psxrecomp/runtime/src/starvation_ring.c:61-79`,
`:255-277`). The runtime checks it as guest cycles advance
(`psxrecomp/runtime/src/psx_cycles.c:364-367`), so a reported gap far above
4 s means the emulation itself stopped for at least the gap minus 4 s. A host
stall triggers it too: if the host journal shows one at that moment and the
dump's ring ends within a few milliseconds of the last heartbeat, copy the
run's outputs aside (a new run deletes them) and run it again.

The committed routes are `title_to_zone1.json` (boot to zone-1 gameplay),
`menus.json` (opens and leaves every main-menu screen except CAMPAIGN PLAY),
`memcard.json` (LOAD/SAVE: saves to memory card slot 1, then loads it back),
`demo_zone1.json` to `demo_zone6.json` (REPLAY > DEMONSTRATION: each zone's
recorded replay until shortly after its COMPLETED screen), and
`demo_zone7.json`, `demo_zone8.json`, `demo_zone_last.json`,
`demo_zone_u1.json` to `demo_zone_u9.json` and `demo_zone_v5.json` (the same
for the 13 zones that the unlocked save below opens; each route first loads
the save with LOAD SLOT1). Each route's `notes` give its pad words and timing
rules. A new route also needs an entry in this list and in `LISTED` in
`scripts/routes/test_routes.py`.

A route that needs a memory card declares `card1_sha256`, the sha256 of a raw
128 KiB card image, and then runs only with `--card1` naming an image of that
size and hash. The runner checks both before launch and copies the image into
the run's `memcards/card1.mcd`, so the original is never written (after a run,
the copy's write-test frame, at offset 0x1F80, has changed).
`--card1` is refused for a route that declares no card, and `test_routes.py`
checks that exactly the unlocked-zone routes declare one. Those routes need
the North American save "All Zones Unlocked (Gamesharked)", GameFAQs save
20242 for Omega Boost: a DexDrive `.gme` file (download it in a browser; a
scripted download got HTTP 403). Its raw card image is the file's last 131,072
bytes, with sha256
`e3b71c252ce26cf26136e7e552f2f258ecc1bca02da8c92bb1e7b6c905860b4e`. Keep it
in the ignored `.cache/saves/`:

```sh
mkdir -p .cache/saves
tail -c 131072 <download>.gme > .cache/saves/all-zones.mcd
```

```sh
python3 scripts/routes/run_route.py scripts/routes/<route>.json --mode hle-openbios
python3 scripts/routes/run_route.py scripts/routes/<route>.json --mode lle-openbios
python3 scripts/routes/run_route.py scripts/routes/<route>.json \
  --mode lle-scph1001 --bios <SCPH-1001 v2.2 dump>
# routes with card1_sha256 also take --card1 .cache/saves/all-zones.mcd
python3 -B scripts/routes/test_run_route.py   # runner tests against a fake runtime
python3 -B scripts/routes/test_routes.py      # route files: exactly the listed routes, validity, unique names, shot margins
```

Verify every route change in all three modes and with `test_routes.py`, and
every runner change with both test files and every route in all three modes.

## Beetle oracle

`psx-beetle` is the framework's build of Beetle PSX, the oracle that accuracy
claims are checked against (`psxrecomp/CLAUDE.md` §16).
`scripts/build_beetle.sh` builds it out of tree in `.cache/beetle/` by the
recipe in `psxrecomp/docs/beetle-linux.md`: archives of the framework commits
that HEAD pins (the submodule checkout is never written to),
beetle-psx-libretro at `5759277be50052b9f3f388578bf56cc7899d833f` with the
framework's seven `docs/beetle_*.patch` applied in order, then
`ninja psx-beetle`. The first run clones beetle-psx-libretro into
`.cache/beetle/beetle-psx.git`, so it needs network access.

`scripts/routes/beetle_route.py` plays a committed route on it in
`lle-openbios` mode (the framework's `psxrecomp/bios/openbios.bin`) or
`lle-scph1001` mode (`--bios`); Beetle has no HLE boot. psx-beetle has no
`input_route_*` commands, so the driver keeps one debug connection open,
follows the frame count, and sends each press, and each shot once its step has
ended, together with a `ping` on the frame before. Every press and shot then
lands on its exact route frame, counted from `--start` (default 60), or the run
fails. A run also fails if the BIOS image does not have the sha256 in its
framework profile (`psxrecomp/bios/OpenBIOS.toml` or `SCPH1001.toml`), if
`beetle.log` does not report that image's SHA-1 for `system/scph5501.bin` (the
name Beetle wants with this US disc; without it Beetle quietly boots its own,
different OpenBIOS), or if psx-beetle exits early, a ping fails or reports no
frame number, or the route times out. Both memory cards start as formatted blank
cards, as psx-runtime formats missing ones, and `--card1` follows
`run_route.py`'s rules. Beetle reads the cards from its working directory under
the disc's name, `cwd/Omega Boost (USA).0.mcr` and `.1.mcr`. It saves a card the
game changed back to that file about two emulated seconds after the game's last
write to it, and on exit if it changed since (beetle-psx `libretro.cpp`,
`mednafen/psx/frontio.cpp`), so read the cards only after psx-beetle has
exited. The `dummy.*.mcr` lines in `beetle.log` come from a separate warn-only
check (`psxrecomp/runtime/src/beetle_libretro.cpp:543-567`) of files it does not
load. The driver writes the cards under Beetle's names and fails the run if
psx-beetle writes any other file in `cwd/`. Runs are unpaced unless `--paced`.
Unpaced, Beetle takes about 3 ms per frame on average, and that is all the
time the driver has to answer each ping; if the host holds it back longer, an
event lands a frame late and the run fails, so run it again (`--paced` gives
every frame 1/59.94 s). Outputs go to `.cache/beetle-routes/<name>/<mode>/`
under `run_route.py`'s reuse rules, with the driver's own marker. The debug
port is 4382; run routes one at a time. The driver and its tests run on Linux
only (`TCP_QUICKACK`, `/proc`).

```sh
bash scripts/build_beetle.sh                  # JOBS=N sets the parallel jobs
python3 -B scripts/routes/beetle_route.py scripts/routes/<route>.json \
  --mode lle-openbios
python3 -B scripts/routes/beetle_route.py scripts/routes/<route>.json \
  --mode lle-scph1001 --bios <SCPH-1001 v2.2 dump>
# routes with card1_sha256 also take --card1 .cache/saves/all-zones.mcd
python3 -B scripts/routes/test_beetle_route.py   # against a fake psx-beetle
```

Beetle's boot reaches the same screens as psx-runtime's on other frames, so
compare screens and results along a route, not frame by frame. Verify every
driver change with its tests and every route in both modes. A route change
needs a Beetle run only when a claim that the route's screens or results are
correct depends on it (`psxrecomp/CLAUDE.md` §15: never call a result correct
without checking it against the oracle).

## Mods

The game's own mod catalog is `mods/preloaded/packages/`. Every build stages
it, with the framework's builtin `psx.*` packages, into `<exe>/mods/bundled/`
(`psxrecomp/docs/MOD_PACKAGES.md`). Trusted plugins are C sources in
`src/mods/`, linked through `EXTRAS_SOURCES` in `CMakeLists.txt`, and a
package selects a plugin by its id. An enabled feature whose plugin id nothing
registers fails before launch, and the audit fails if a linked plugin is named
by no manifest:

```sh
env -u APPIMAGE build-dev/Omega_Thrust --audit-mod-plugins \
  psxrecomp/mods/builtin mods/preloaded
```

The audit does not see a plugin that registers only instruction hooks, such as
`omega.branching` and `omega.zone-clear`: its list of registered ids leaves
them out (`psxrecomp/runtime/src/mod_packages.cpp:1578-1585`), while the
launch check counts them (`:1496-1502`). For those, a run with the feature on
is the check. An instruction hook also needs its address in `game.toml`
`[recompiler] mod_instruction_sites`, then a regenerate: the generated code
calls `psx_mod_instruction` before that instruction, which returns at once
while no active plugin hooks an instruction. Changing the list changes the
hash of `game.toml` that the static overlay audit records, so `generate`
rebuilds the shard and rewrites `AOT_STATIC_AUDIT.json`; with the sites
listed now, all four in the EXE, the rebuilt shard's C stayed the same.

`omega.cheat.unlock-all` ("Unlock All Zones and Boost Levels", group Cheats,
off by default) runs the plugin `omega.unlock-all`
(`src/mods/omega_unlock_all.c`). While its feature is on, at every emulated
VBlank once the game has started, the plugin sets the zone flags A[0..18] and
the boost-level flags B[0..13] (`docs/MODDING_FEASIBILITY.md`, "Unlocks and
the save") and counts each byte it writes as `omega.unlock-all.writes` (debug
command `mod_counters`). The game saves these flags with its LOAD/SAVE
environment data, so a save made while the feature is on keeps the unlocks.

`omega.gameplay.branching` ("Branching Campaign (prototype)", group Gameplay,
off by default) runs `omega.branching` (`src/mods/omega_branching.c`), an
instruction plugin at the campaign loop's step-limit check (0x8002FB2C). While
it is on, an S grade on the 1ST ZONE makes the campaign play the 3RD ZONE,
then the 2ND ZONE, MOVIE IM 0 and the 4TH ZONE; any other grade keeps the
stock order, and every zone is played once. Its rules read only the zone
result records, and it counts each redirect as `omega.branching.redirects`.

`omega.debug.zone-clear` ("Clear Zones Instantly (testing)", group Debug,
hidden, off by default) runs `omega.zone-clear` (`src/mods/omega_zone_clear.c`),
an instruction plugin in the zone timeline runner (0x80071558). While it is
on, a zone that uses that shared timeline ends through the game's own clear
path as soon as the player is in play; runs have checked this in the 1ST to
4TH ZONE of CAMPAIGN PLAY, in all three boot modes. With nothing destroyed
the results grade it low (D in zones 2 to 4, B in the 1ST ZONE), and S with
the option `all-destroyed` (every spawned enemy counted as destroyed). It
counts each clear as `omega.zone-clear.clears`. The 5TH ZONE, the LAST ZONE,
U5, U9 and V5 have no timeline runner and end through their own code, so it
does not clear them; the 8TH ZONE, U4 and U8 have one but also call the clear
routine from their own code, and how that meets a forced clear is untested.
Its results and records are not genuine; it exists so scripted runs can
reach each branch.

`omega.enhancement.mouse-aim` ("Mouse Aim", group Quality of Life, off by
default) runs `omega.mouse-aim` (`src/mods/omega_mouse_aim.c`). While it is
on and the player is flying (CAMPAIGN PLAY, ZONE PLAY or TRAINING), the mouse
steers, moving player 1's left stick, and the keyboard's left-stick keys (W,
A, S, D and the arrows in `controls/keybinds.ini`) strafe: they move the mech
up, left, down and right relative to the view without turning it, at the
option Strafe speed (in percent of the cruising speed, default 50). Releasing
the left button presses ATTACK once, which launches the homing lasers at the
targets locked on since the last press, and holding the right button presses
it again and again, firing the laser rifle. The framework's mouse policy
captures the mouse only while the left button is held and moves only the
right stick, so the plugin puts the game window in SDL's relative mouse mode
itself and drives player 1 through a controller source: the mouse on the
left stick, and the stick keys on the right stick, which the game ignores in
flight. Instruction hooks in two of the player's three movements (0x80033044
and 0x800337CC, listed in `game.toml`) read the right stick from the pad record
and add a force along the screen's right and down axes; the game's own drag
ends the sideways motion when the keys come up. While SCAN is held (L1, Q in
`controls/keybinds.ini`), the game runs SCAN's movement, 0x800334D8, which
keeps the view on the enemy and slides the mech with the left stick, so there
the mouse slides the mech instead of steering it. The hook in that movement
moves the mech along the axes of that slide: those of the rotation that the
game builds from the view's angles at player +0x40, which includes the view's
roll, as the camera does. The slide also does two things the strafe does not:
where the stage names a target and does not move the player along z, it pulls
the mech along the direction the view turns toward (0x8003A0E0), and where the
stage moves the player along z, it keeps the z part of its sideways force,
which the strafe drops. The force, and the code after the hooks, drag included,
are the same in both movements, but in a headless run right after zone 1's
fly-by, where the view turned to keep the enemy ahead, a full strafe at the
default moved the mech sideways at about 98 units a frame against 80, and the
game's own slide sped up in the same proportion; in the windowed checks, where
the view held still, the strafe ran as fast as outside SCAN. What causes the
difference is not traced. After a press of a boost key (Triangle or Circle in
the game's default setup), in SCAN or not, the game runs its third movement,
0x80032414, which has no hook, so the keys do not strafe while it runs: 18
steps, or 6 if the boost is a sideways dash, as it is while the word at
0x800A7EF4 is set and the left stick is pushed more than half way along either
axis (0x80032144). Both hooks also add their force to the player's words +0xBC
to +0xC4, which the game clears every step, as the game's own slide does with
its sideways force. The camera (0x800630B4) hangs behind the mech on a spring
pushed against those words, so it falls behind a strafe, the mech slides across
the screen, and the camera catches up when the keys come up. The hooks act only
in flight and on the live pad, so a saved replay is not expected to play the
strafe back (derived, not tested).
A source's sticks replace player 1's own, so a gamepad's sticks neither steer
nor strafe in flight while the feature is on, though its buttons do. The
cursor is free while the game is paused, out of flight or not in the focused
window. The plugin presents player 1 as an analog pad, so in
flight the game steers by the stick, not the d-pad, and keeps the game's TYPE
setting (CONTROL SETUPS) at B, so that up flies the mech up, or at A with its
option Invert vertical. The game saves TYPE with its environment data and reads
it back from the card at the title screen, so a save made while the feature is
on keeps that TYPE with the feature off too, until CONTROL SETUPS changes it.
The plugin counts its work as `omega.mouse-aim.*`. Beyond `mod_plugins.h` it
relies on `psx_sdl.h` and `psx_keybinds_sticks()`, so a pin bump must check
it again. The runtime discards a controller source's input in headless runs
and under a debug-server input override
(`psxrecomp/runtime/include/mod_plugins.h:825-827`), so the routes cannot
check the plugin: check a change to it in a windowed run (so far, the 1ST
ZONE of CAMPAIGN PLAY). The strafe hooks read the pad record, which the debug
server's `set_input` axes also reach, so a headless run can drive them. Check
the strafe's directions against the game's own movement, from one save state:
outside SCAN, strafing right must move the mech to the side that turning
right takes it, and strafing up to the side that climbing takes it; in SCAN,
each strafe to the side that the game's slide in the same direction takes it,
with Invert vertical off (TYPE B): the slide's vertical direction follows TYPE
(0x800306C4), and under TYPE A pushing the stick up slides the mech down, while
W still strafes up. A check along the hooks' own axes would share any sign
error in them.
`controls/keybinds.ini` is the keyboard layout made for it: copy it beside
the executable as `keybinds.ini`, where windowed runs read it, or set the
same keys on the launcher's Controls page.

The runtime reads the feature selection from `<exe>/mods/state.toml`, and
every launch writes it back. Routes and the Beetle comparison run with every
feature off, so `build-dev/mods/state.toml` must enable none. To try a
feature, enable it on the launcher's Mods page in the play copy
(`.cache/play/build/`). For a headless run with a feature on, copy
`build-dev/Omega_Thrust` (a copy, not a symlink: `run_route.py` resolves
`--binary`) with `bios/`, `assets/`, `game_options.toml`,
`psx_game_version.txt` and `mods/bundled/` into a directory under `.cache/`
or outside the repository, so git never sees the binary and `assets/`, write
its own `mods/state.toml` (format in `MOD_PACKAGES.md`, "State and
migration"), and pass `--binary`, a free `--port` and `--out` to
`run_route.py`; without `--out`, a run of a committed route replaces that
route's feature-off outputs in `.cache/routes/<name>/<mode>/`. psx-beetle runs
no plugins, so a mod's effect can be checked against it only through what the
game saves, such as a card saved with the feature on.

## Zone data

`scripts/zones/zone_data.py` (Python standard library only) turns a zone's
wave timeline and formations into editable text and back, byte for byte,
reading the zone files from the player's disc (`--disc`, default
`disc/Omega Boost (USA).cue`). A zone file, `<DIR>/<DIR>.BIN`, loads whole at
0x80120000. Fourteen of them pass a table to the game's shared timeline
runner: 8-byte entries of a wave callback and a delay, ending in an end entry
everywhere but the 8TH ZONE (`docs/MODDING_FEASIBILITY.md`, "Scenes and
files"). The 5TH ZONE, the LAST ZONE, U5, U9, V5 and the files that are not
zones have no such table. In the 1ST, 2ND, 3RD and 6TH ZONE, wave callbacks
also start formations through 0x80057F0C: each passes a record of eight
words (where its steps and members are, a position added to the player's,
three angles) and, as instruction immediates, its numbers of steps and
members; 33 records in all (`docs/MODDING_FEASIBILITY.md`, "Formations").
Five of them start on only one value of the difficulty word, 0x800A7C34, and
the dump's notes say which.

```sh
python3 scripts/zones/zone_data.py list      # zone files, tables, formations
python3 scripts/zones/zone_data.py dump S1   # to .cache/zones/S1.zone.toml
python3 scripts/zones/zone_data.py build .cache/zones/S1.zone.toml
python3 scripts/zones/zone_data.py check     # dump and rebuild every zone
python3 scripts/zones/zone_data.py package .cache/zones/S1.zone.toml
python3 scripts/zones/zone_data.py remix scripts/zones/remixes/crossfire.toml
python3 -B scripts/zones/test_zone_data.py   # tests (the disc is optional)
```

A dump names the stock file's size and sha256, and `build` (default output
`.cache/zones/<DIR>.BIN`) reads that file from the disc again and refuses any
other. It writes the edits in place: the waves and the end entry must fit in
the stock table's slots, a wave may use only the stock table's callbacks, and
the first entry must be a wave, because the runner's constructor calls entry
0 without checking it; slots left over become zero words. Delays count runner
ticks, about one every two frames (30 a second). A formation keeps its
address and its numbers of steps and members, which the code that passes it
fixes; its position, angles, steps (turn, speed, ticks, flags) and member
offsets may change, and the dump's comments give their units. Which enemy
the members are is code: each of the four zones spawns every member of every
formation with one function of its own. Dumps, built zone files and packages
hold data from the disc, so the tool writes them only under `.cache/` or
outside the repository. Verify every change to the tool with its tests and
`check`.

`package` makes the game load the edits. It writes a `.psxmod` (default
`.cache/zones/<id>-<version>.psxmod`, id `omega.remix.` and the zone's folder
in lowercase, such as `omega.remix.s1`): a zip with `manifest.toml` at its
root, which the launcher's Mods page installs into
`<exe>/mods/installed/<id>/<version>/`. Its one feature, `remix` (group
Remix, off by default), is a `disc_user` overlay (`MOD_PACKAGES.md`, "Native
operations") that puts the built file's bytes on the disc from the first
byte `build` may write to the last (the table's slots and every formation
part, with the stock bytes between them), so the game reads them when it
loads the zone; no plugin, hook site or regenerate is involved. The manifest
names the sha256 of the disc image the runtime mounts, which for a cue sheet
is the data file it names (`psxrecomp/runtime/src/mod_runtime.cpp`
`sha256_file`), so with the feature on the runtime refuses to start from any
other image; and the sha256 of the stock bytes under the overlay, which the
runtime checks before launch, refusing to start if they differ. An edit
leaves the zone's precompiled code running: a static variant's guard is the
CRC of its own code ranges, and in every zone with a timeline none of those
ranges covers a byte `build` may write. To play a package headless, add it
to a copy of the build as in "Mods": unpack it into the copy's
`mods/installed/<id>/<version>/` and enable its feature in the copy's
`mods/state.toml`.

A remix recipe holds only edits, never data from the disc, so recipes are
kept in the repository (`scripts/zones/remixes/`). `remix` applies one to the
zones on the player's disc, through `build`'s rules, and writes one
`.psxmod` (default `.cache/zones/<id>-<version>.psxmod`) whose `remix`
feature carries an overlay for each zone, guarded as `package`'s is. A recipe
names the package (`id`, `version`, `name`, `description`) and, for each
`zone` (such as `"S1"`), a new timeline (`waves`: stock waves by number, 0
first as in a dump, each with a `delay` in ticks, `"clear"` or `"stock"`) and
formation edits by record `address`: `spread`, a factor above 0 for the
members' offsets; `pace`, a factor above 0 for the steps' speeds and turns
that also divides each step's duration (a pace that would leave a first step
no ticks is refused); `yaw`, degrees that turn the whole flight about the
vertical axis through the player's position when the formation starts;
`move`, added to the position after `yaw`. The player flies on along positive
z at about 320 units a tick, so a formation turned to start behind reaches it
only if it starts near enough (`move`) and flies faster than the player
(`pace` speeds up a slow one). `crossfire.toml` remixes the 1ST, 2ND, 3RD
and 6TH ZONE. The tests parse every committed recipe and, with the disc,
build it.

## Naming

The project is Omega Thrust: window title "Omega Thrust", executable
`Omega_Thrust`, launcher catalog name, `.recomp.json` `project`. Text about the
original game says Omega Boost: `.recomp.json` `game`, the README summary and
the packager's `--disc-hint`. `CMakeLists.txt` `WINDOW_TITLE` and `game.toml`
`[runtime] window_title` must agree; the runtime prefers the `game.toml` value.
Re-rendering `game.toml` with `probe_disc.py --write-game-toml` writes "Omega
Thrust Recompiled" and must be corrected.

## Bookkeeping

- Handoff: `.agent/HANDOFF.md`, updated before every review.
- Evidence logs: `.cache/evidence/<step>/` (ignored); summarize results in the handoff.
- Host toolchain: GCC 16.2.1 (runtime), clang 23.1.3 (emitters, chosen by
  `psxrecomp_cli.py`), CMake 4.4.4, Ninja 1.13.2, Python 3.14.8 (the framework
  requires 3.11+), SDL3 3.4.18.

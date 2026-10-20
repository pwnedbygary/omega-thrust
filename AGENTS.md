# Omega Thrust — repository instructions

This repository follows the global engineering protocol: scope, minimal change,
verify, bookkeeping, frozen snapshot, independent read-only review,
explicit-path commit, non-force push. This file adds only repository-specific
facts. Framework rules for game work are in `psxrecomp/CLAUDE.md` (RULE -1:
faithful core, no per-game hacks; §4: never modify generated code; §14: unknown
is acceptable, guessing is not; §16: Beetle oracle).

## Pins

Bump a pin only as its own reviewed change. Never patch a submodule. Do not run
`git submodule update --remote`: `.gitmodules` sets `branch = master` for both
submodules, so it would move the pins.

| Path | Commit | Source |
|---|---|---|
| `psxrecomp` | `8077e71098ce0347d7d41d267630bc856816cf77` | psxrecomp nightly 20261007 |
| `psxrecomp/lib/recomp-net` | `e2491d2a78e37fb18fca087ebc34ad8261caae9c` | nested pin of `8077e71` |
| `psxrecomp/lib/retcomm-rbengine` | `2a03e73693acee0fb78076ea058642c931bef12e` | nested pin of `8077e71` |
| `recomp-ui` | `864f77802ba3191a9b955ddc23de7e624b6d83a2` | paired with `8077e71` in the gitlinks of mstan/TombaRecomp@43915ca |

`bash psxrecomp/tools/ci/record_pins.sh --root .` must print the same SHAs as
`framework_pins.txt`.

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

If `[runtime] overlay_capture_history` is ever enabled, put
`overlay_capture_persist_dir` under `.cache/`: its
`<game_id>_<session>_<seq>_<sig>.json` snapshots are full capture copies and
no ignore pattern matches them elsewhere. For the same reason, keep a store
named by `PSX_OVERLAY_CAPTURES` outside the repository or under `.cache/`; the
ignore pattern matches only the default `overlay_captures.*` names.

`generated/` is committed but never hand-edited: change the seeds, or take a
recompiler fix through a reviewed pin bump, then regenerate.

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

The runtime build writes one file inside the submodule, whenever it is missing
or stale: the framework's `psxrecomp/runtime/include/overlay_codegen_hash.h`
(`psxrecomp/runtime/runtime.cmake:1778`), which `psxrecomp/.gitignore:76`
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
without frame data, so poll `frame`. Without `--headless` the launcher opens and
writes `input.ini` and `keybinds.ini` beside the executable.

Run one runtime per build directory at a time. Every launch commits the mod
selection (`psxrecomp/runtime/src/main.cpp:16626-16629`; `save_selection`
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

The committed routes are `title_to_zone1.json` (boot to zone-1 gameplay),
`menus.json` (opens and leaves every main-menu screen except CAMPAIGN PLAY),
`memcard.json` (LOAD/SAVE: saves to memory card slot 1, then loads it back) and
`demo_zone1.json` to `demo_zone6.json` (REPLAY > DEMONSTRATION: each zone's
recorded replay until shortly after its COMPLETED screen). Each route's `notes`
give its pad words and timing rules. A new route also needs an entry in this
list and in `LISTED` in `scripts/routes/test_routes.py`.

```sh
python3 scripts/routes/run_route.py scripts/routes/<route>.json --mode hle-openbios
python3 scripts/routes/run_route.py scripts/routes/<route>.json --mode lle-openbios
python3 scripts/routes/run_route.py scripts/routes/<route>.json \
  --mode lle-scph1001 --bios <SCPH-1001 v2.2 dump>
python3 -B scripts/routes/test_run_route.py   # runner tests against a fake runtime
python3 -B scripts/routes/test_routes.py      # route files: exactly the listed routes, validity, unique names, shot margins
```

Verify every route change in all three modes and with `test_routes.py`, and
every runner change with both test files and every route in all three modes.

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
- Host toolchain: GCC 16.2.1 (runtime), clang 23.1.1 (emitters, chosen by
  `psxrecomp_cli.py`), CMake 4.4.4, Ninja 1.13.2, Python 3.14.7 (the framework
  requires 3.11+), SDL3 3.4.18.

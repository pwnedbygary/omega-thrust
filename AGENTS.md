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
- `overlay_captures.json` (verbatim game code), `/.cache/`, `/analysis/`.
- `disc_probe.json` (absolute local path), `settings.toml`, `*.cfg`,
  `.psxrecomp.env`, `.env`, build directories.

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

Generate and build commands are added here once verified.

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
- Host toolchain: GCC 16.2.1, CMake 4.4.4, Ninja 1.13.2, Python 3.14.7 (the
  framework requires 3.11+), SDL3 3.4.18.

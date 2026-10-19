# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 1 scaffold. Invariant: the repository holds the New
Project Layout scaffold produced by the nightly `setup_project.sh`, with
`psxrecomp` at `8077e71` and `recomp-ui` at `864f778`, no disc or BIOS data and
no absolute local paths tracked, and the window titled "Omega Thrust".
Baseline: empty repository, no commits. Out of scope: generate/build (Phase 2),
CI, packaging, boxart, netplay.

## Phase 0 observations (`.cache/evidence/phase0/`)

- Nightly tarball `psxrecomp-src-nightly-20261007-8077e71098.tar.gz`: sha256
  `1b6dc4845ae7…` matches the release `SHA256SUMS` (itself sha256 `cf42077e15bd…`).
  Its `NIGHTLY_COMMIT` is `8077e71098ce0347d7d41d267630bc856816cf77`.
- `Omega Boost.chd` (sha256 `0fe927f9ee45…`): `chdman verify` passes (raw and overall SHA1).
- Extracted bin: 582616272 bytes, CRC32 `2f89bc87`, MD5 `f1f9af8786f8…`, SHA-1
  `772c58d8af1b…`, equal to Redump disc 1505 (USA, SCUS-94449, one track).
  chdman wrote the standard single-track `MODE2/2352` cue. Redump's cue file was
  not downloaded (its endpoint returned HTML). `disc-extract-verify.txt` has a
  blank `extract_exit=` because chdman's exit status was not captured; the
  digests above prove the extraction.
- SCPH-1001 dump on the share: sha256 `71af94d1e47a…`, CRC32 `37157331`, equal to
  the framework's SCPH1001 v2.2 profile. Not copied into the repository.
- Host: GCC 16.2.1, clang 23.1.1, CMake 4.4.4, Ninja 1.13.2, Python 3.14.7,
  SDL3 3.4.18, git 2.56.0, chdman 0.289, Linux 7.2.9 x86_64, 16 threads.

## Phase 1 observations (`.cache/evidence/phase1/`)

- Ran the tarball's `tools/new_project_layout/setup_project.sh` in a scratch
  directory outside the repository (`<scratch>` below), with
  `PSXRECOMP_URL=https://github.com/RetroPortingToolKit/psxrecomp.git` and a
  scratch `core.hooksPath` whose `pre-commit` exits 1. The script printed
  "skipped initial commit" (`scaffold.log`). Flags:

  ```text
  --yes --name "Omega Thrust" --github-owner pwnedbygary --github-repo omega-thrust
  --dir "<scratch>/scaffold" --disc "<scratch>/disc-src/Omega Boost (USA).cue"
  --stage-disc --players 1 --region USA --enable-recomp-ui --enable-wizard
  --no-netplay --no-ci --no-fetch-boxart --no-generate --no-build --no-github
  --publisher "Sony Computer Entertainment" --year 1999
  --description "Native PC recompilation of Omega Boost (PlayStation, 1999), built with psxrecomp. Requires your own disc."
  ```

- The script added submodules at branch tips (psxrecomp `7ce88a6`, recomp-ui
  `11e0aa6`, recomp-net `e530593`). Re-pinned to psxrecomp `8077e71` and
  recomp-ui `864f778`; nested recomp-net `e2491d2` and rbengine `2a03e73`
  (`repin.log`).
- `diff -rq` of the pinned submodule against the verified tarball: only the
  tarball's `NIGHTLY_COMMIT`, `NIGHTLY_SUBMODULES` and a `__pycache__` created by
  running the script differ.
- `assets/psxrecomp.{svg,png,ico}` are identical at master and `8077e71`.
- After copying into the workspace, and before the `window_title` change below,
  re-running the probe produced byte-identical `game.toml`,
  `catalog_identity.json`, seeds and boot EXE; `disc_probe.json` differs only in
  `cue_path` (`reprobe.log`).
- Probe result: SCUS-94449, volume ID `OMEGABOOST`, boot EXE `SCUS_944.49`
  (sha256 `d9477ba8e9ad…`), entry `0x80090334`, load `0x80010000`, text size
  `0x110800`, 697 seeds (the entry PC plus 696 JAL targets), disc fingerprint
  `307271d0964c…`. The probe's "cue has only 1 TRACK" warning is expected:
  Redump lists one track for this disc.

## Deliberate deviations from the raw scaffold output

- `framework_pins.txt` regenerated after re-pinning.
- `game_options.toml` tracked; the script leaves it untracked, but CMake stages
  it next to the executable and the packager reads it.
- `disc_probe.json` untracked and ignored (`.gitignore` exception removed): it
  records the absolute local `cue_path`, and only local scaffold tools read it.
  Its volume ID and boot EXE sha256 are recorded in `AGENTS.md` instead.
- `game.toml` `window_title` "Omega Thrust Recompiled" changed to "Omega Thrust"
  (the chosen name). The runtime prefers `game.toml` over the compiled
  `WINDOW_TITLE` (`psxrecomp/runtime/src/main.cpp:14509`, `:14601`).
- Original-game wording (user decision): the script derives every name from
  `--name`. `.recomp.json` now has `"game": "Omega Boost"` and
  `"project": "Omega Thrust"` (recomp.fyi v1 defines `game` as the title as it
  shipped), byte-identical to the output of `write_recomp_json.py --game "Omega
  Boost" --project "Omega Thrust" --region USA --probe-json disc_probe.json`.
  The README summary and the packager's `--disc-hint` say Omega Boost.
- `.gitignore`: the header no longer claims alignment with the CI template.
  Adds `*.cfg` (replacing `bios.cfg`, `disc.cfg`, `rom.cfg`), `.psxrecomp.env`,
  `.env`, `overlay_captures.json*` at any depth, and any-case `bin`, `cue`,
  `iso`, `chd`, `img`, `ecm`, `pbp` image names.
- Added `AGENTS.md` and `.agent/HANDOFF.md`.
- Kept as generated: `codegen_setup.c` ends with a blank line, so
  `git diff --cached --check` reports `codegen_setup.c:45: new blank line at
  EOF` and exits 2. The blob is byte-identical to the script's output from
  `templates/codegen_setup.c.in`.

## Changed files (all new; this is the root commit)

`.agent/HANDOFF.md`, `.github/raid-discord.png`, `.gitignore`, `.gitmodules`,
`.recomp.json`, `AGENTS.md`, `CMakeLists.txt`, `README.md`, `VERSION`,
`assets/psxrecomp.{ico,png,svg}`, `catalog_identity.json`,
`codegen_setup.{c,h}`, `framework_pins.txt`, `game.toml`, `game_options.toml`,
`mods/preloaded/README.md`, `mods/preloaded/packages/.gitkeep`,
`psx_symbols.h`, `scripts/package_release.sh`, `seeds/ghidra_funcs.txt`,
`symbols.toml`, `tools/sync_symbols.py`, and the gitlinks `psxrecomp` and
`recomp-ui`.

## Phase 1 checks (final tree, `.cache/evidence/phase1/checks-r2.log`)

- `check_boot_exe.sh .`: names agree on `SCUS_944.49`, exit 0.
- `check_bios_stamps.sh --framework psxrecomp`: OpenBIOS `26dc9778f248` and
  SCPH1001 `f15f850430c9` current, exit 0.
- `record_pins.sh --root .` output equals `framework_pins.txt`.
- `git submodule status --recursive`: pins as above, no submodule modified.
- `git grep --cached -nE '/(home|tmp|mnt|media|run)/'`: no output.
- `git ls-files -ci --exclude-standard`: no output (no tracked file is ignored).
- `git check-ignore`: `disc_probe.json`, `disc/…`, `.cache/…`, `input.cfg`,
  `.env`, `.psxrecomp.env`, `GAME.BIN`, `x.Ecm`, `x.PBP` and
  `captures/SCUS-94449/overlay_captures.json` (and its `.d` history) are ignored.
- The documented probe command (fresh `mktemp -d`): `catalog_identity.json` and
  the seeds equal the tracked files, the boot EXE equals the local
  `disc/SCUS_944.49`, and `game.toml` differs only in the `window_title` line.
- The documented chdman recipe, run in a fresh directory, reproduces the cue and
  bin in `disc/` byte for byte.
- `cmake -S . -B build-scaffold-check -G Ninja -DCMAKE_BUILD_TYPE=Release`:
  exit 0; system SDL3, recomp-ui SDL3 backend, Vulkan headers and glslc,
  vendored libchdr; setup-host mode because `generated/` does not exist yet.
- `git diff --cached --check`: exit 2, only the `codegen_setup.c` template line above.
- Not run: emitters, generate, product build, runtime (Phase 2).

## Early Phase 2 observations (scratch, outside this change)

Recorded for continuity; Phase 2 re-verifies them in this worktree.

- `build_emitters.sh` built the emitters with GCC; `generate` then rebuilt them
  with clang because the build directory had no toolchain stamp. Both write
  only the ignored `build-recompiler/`.
- Framework recompiler tests on GCC 16.2.1: 135 of 140 pass. Failing:
  `bios_module_build`, `compile_overlays_static_tail`,
  `reachable_discovery_codegen`, `aot_overlay_discovery`,
  `mod_owned_display_controls` (framework untouched, so pre-existing).
- Generate with the 697 probe seeds: 46 shards, 2,371,078 lines, about 70 MB of
  C, 1700 dispatch entries, 8 s.
- A scratch build with the CI flags plus `PSX_DEBUG_TOOLS=ON` linked
  `Omega_Thrust` in 67 s; the only compiler warning is in the vendored
  `stb_image.h`. Its configure wrote the ignored
  `psxrecomp/runtime/include/overlay_codegen_hash.h` into this worktree's
  submodule, because the scratch tree symlinks `psxrecomp`.
- Headless run with an explicit OpenBIOS `--bios`: the intro plays (SCEA card,
  intro sequence, FMV); 0 unknown-dispatch and 0 segment misses in 60 s; about
  100 frames per second.
- The agent shell exports `APPIMAGE` (the harness's own AppImage). The runtime
  anchors every exe-relative file on `$APPIMAGE` (`main.cpp:2545-2550`), so runs
  started from that shell outside the exe directory missed `game.toml` and the
  bundled BIOS, and wrote their mod state beside the harness AppImage (removed
  with the user's permission). Launch with `env -u APPIMAGE` and an explicit
  `--game`.
- The TCP debug server answers one request per connection, and its I/O thread
  answers `ping` itself without frame data (`debug_server.c:16141-16186`).

## Hypotheses and unknowns

- Whether the 697 boot-EXE seeds carry the game past the intro: unknown until
  Phase 2/3.
- recomp-ui `864f778` compatibility is inferred from TombaRecomp's pairing; the
  scratch build compiled and linked it, but the launcher has not been shown.

## Review and commit state

- Snapshot tree `462f6f1` (staged diff sha256 `eca4abe8…`): two independent
  read-only reviewers (the second was started by mistake on the same tree), both
  NEEDS CHANGES with the same blocking findings:
  1. This handoff tracked absolute scratch paths, and its path-check line was false.
  2. The `AGENTS.md` probe command never created `$SCRATCH`.
  3. The `AGENTS.md` chdman recipe failed without an existing `disc/`.
- All three are fixed in the current snapshot. Adopted nonblocking suggestions:
  original-game naming (user decision), `.gitignore` coverage of the
  never-commit list, disc provenance and the `git submodule update --remote`
  warning in `AGENTS.md`, recompiler and pairing wording, the full scaffold
  flags, the changed-files list, and the notes on the one-track warning, the
  blank `extract_exit=` and the template blank line.
- Current snapshot: pending delta re-review.
- Commits: none. Remote `pwnedbygary/omega-thrust`: not created yet.

## Next action

After a PASS on the current snapshot: re-check the tree id and staged-diff
hash, commit, `gh repo create pwnedbygary/omega-thrust --private --source .
--remote origin`, `git push -u origin HEAD`, and delete the scratch scaffold.
Then Phase 2: generate twice and compare hashes, build release and dev
(`PSX_DEBUG_TOOLS=ON`) binaries, and run the smoke matrix with
`env -u APPIMAGE`, an explicit `--game`, and one run per exe directory at a time.

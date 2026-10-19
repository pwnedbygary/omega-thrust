# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 2. Invariant: `generated/` holds the game C that the
pinned recompiler produces from the tracked `game.toml` and seeds, byte-identical
across runs; release and dev builds of `Omega_Thrust` configure with the CI
template flags and link from tracked sources; `check_generated.sh` passes; the
`psxrecomp` submodule has no tracked changes, and the framework's ignored
`overlay_codegen_hash.h`, written by the runtime build, is the only by-product
the documented flow leaves inside it; the two deferred round-2 `.gitignore`
findings are resolved; `AGENTS.md` lists the verified generate, build and run
commands. Baseline: `6ad5c9e`. Out of scope: input-driven play, seeds growth and
overlay AOT (Phase 3), Beetle (Phase 4), CI, packaging.

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

## Phase 1 (commit `6ad5c9e`)

Scaffold from the tarball's `setup_project.sh` (commit blocked), submodules
re-pinned to psxrecomp `8077e71` and recomp-ui `864f778`. Probe: SCUS-94449,
volume ID `OMEGABOOST`, boot EXE `SCUS_944.49` (sha256 `d9477ba8e9ad…`), entry
`0x80090334`, load `0x80010000`, text size `0x110800`, 697 seeds (the entry PC
plus 696 JAL targets). The full Phase 1 record (scaffold flags, checks, review
rounds) is in `git show 6ad5c9e:.agent/HANDOFF.md`.

## Deliberate deviations from the raw scaffold output

- `framework_pins.txt` regenerated after re-pinning.
- `game_options.toml` tracked; the script leaves it untracked, but CMake stages
  it next to the executable and the packager reads it.
- `disc_probe.json` untracked and ignored: it records the absolute local
  `cue_path`, and only local scaffold tools read it. Its volume ID and boot EXE
  sha256 are recorded in `AGENTS.md` instead.
- `game.toml` `window_title` "Omega Thrust Recompiled" changed to "Omega Thrust".
  The runtime prefers `game.toml` over the compiled `WINDOW_TITLE`
  (`psxrecomp/runtime/src/main.cpp:14509`, `:14601`).
- Original-game wording (user decision): `.recomp.json` has `"game": "Omega
  Boost"` and `"project": "Omega Thrust"`; the README summary and the packager's
  `--disc-hint` say Omega Boost.
- `.gitignore` is based on `templates/gitignore.in`, with `disc_probe.json`
  ignored and broader config, env, capture and image patterns.
- `codegen_setup.c` ends with a blank line, byte-identical to the template
  output (`git diff --check` flags it).

## Phase 2 observations (`.cache/evidence/phase2/`)

- Emitters: `generate` always runs an incremental emitter build with the system
  clang and stamps the toolchain. It builds in the project-root
  `build-recompiler/` only when a `psxrecomp-game` binary is already there, and
  otherwise in `psxrecomp/recompiler/build` inside the submodule
  (`psxrecomp_cli.py:637-652`; that path is ignored by `psxrecomp/.gitignore:25`,
  so `git status` stays clean either way). `build_emitters.sh` builds the
  emitters into `build-recompiler/` (its default `--build-dir`) with CMake's
  default compiler (GCC here) and writes no stamp, so the next `generate` wipes
  that directory and rebuilds it once with clang (`psxrecomp_cli.py:683-692`).
  The upstream scaffold runs `build_emitters.sh` before `generate`
  (`setup_project.sh:947-956`). This
  workspace's `build-recompiler/` came from that step, run early in Phase 2
  (`build_emitters.log`), and `AGENTS.md` now documents it as a one-time step.
- `generate.sh`, run 1 with `--force-emitters`: clean emitter rebuild (69 ninja
  steps, clang 23.1.1), 11 s. Run 2, the documented command: "ninja: no work to
  do", "0 updated". Both: 49 files, 72,927,315 bytes, manifests identical. Run 1
  also equals an earlier scratch run that used a separate emitter build and an
  empty output directory. `psxrecomp`: 0 porcelain lines before and after; with
  `--ignored`, only the runtime build's `runtime/include/overlay_codegen_hash.h`
  (`generate-summary.log`; see the build bullet).
- Recompiler: 697 seeds loaded. The `jr $ra` scan finds 1192 functions and call
  discovery 66 more (1258); with the seeds merged the analyzer has 1568, and two
  pre-passes add 133 entry points at mid-function branch targets, so it
  generates 1701 functions (1701 `func_` definitions in the shards, 1701 `F`
  lines in `SCUS_944.49_full.ranges`; the dispatch file declares 1700). 46
  shards (the generator reports 2,371,078 lines; `wc -l` counts 2,372,917).
  Eight
  warnings "out-of-function branch/jump …, emitting fallthrough" for
  `func_8003B9C4`, `func_80047C44`, `func_80048280`, `func_800482FC`,
  `func_80048460`, `func_800493BC`, `func_80065708`, `func_8007A5D4`.
- Largest generated file: `SCUS_944.49_full_42.c`, 7,066,060 bytes. No staged
  file contains a local filesystem path or the local user name. The README
  badge URLs (Phase 1, from the scaffold's `--github-owner`) name the project's
  GitHub repository by design.
- Framework recompiler tests with clang 23.1.1 (`build-fwtests/`, sources from
  the verified tarball tree so no test output lands in the submodule): 126 of
  132 pass. Failing: the five from the GCC run (`bios_module_build`,
  `compile_overlays_static_tail`, `reachable_discovery_codegen`,
  `aot_overlay_discovery`, `mod_owned_display_controls`) plus
  `gpu_upload_history`, whose fixture compiles with `-Werror` and trips clang's
  `-Wunused-but-set-global`. Framework untouched, so pre-existing. The GCC run
  left five temp directories in the system temp directory (psxrecomp test
  fixtures, one holding a
  `psxrecomp-duckstation-oracle` `oracle.json`). An earlier version of this
  handoff said they were removed; they were still there at the review and were
  removed during the fix (`tmp-cleanup.log`). None from the clang run remain.
- Release build (`build-release`, GCC 16.2.1, CI flags): the four CI configure
  markers present; `psx-runtime` linked in 89 s at `-j6`; one warning, in the
  vendored `stb_image.h`. Dev build (`build-dev`, plus `PSX_DEBUG_TOOLS=ON`):
  markers present, 63 s, same warning. Both builds run the framework's codegen
  hash step ("Hashing recompiler codegen" in both build logs), which writes
  `psxrecomp/runtime/include/overlay_codegen_hash.h`
  (`psxrecomp/runtime/runtime.cmake:1778`; ignored by `psxrecomp/.gitignore:76`).
  It is the only file the documented flow writes inside the submodule, and it
  cannot be redirected without patching the submodule.
- Smoke matrix: dev binary, headless, no input, fail-fast on, screenshot
  requests at frames 300/900/1800/3600/5400/7200 (`smoke.py`,
  `smoke_summary.py`; per-checkpoint detail in `smoke_detail.log`):

  | Mode | Last frame | Wall | Exit | Dispatch, segment, unknown misses |
  |---|---|---|---|---|
  | HLE boot, OpenBIOS | 7201 | 60.4 s | 0 | 0, 0, 0 at every checkpoint |
  | LLE boot, OpenBIOS (`PSX_BIOS_HLE=0`) | 7207 | 55.1 s | 0 | 0, 0, 0 |
  | LLE boot, SCPH-1001 (`--bios`) | 7200 | 53.6 s | 0 | 0, 0, 0 |

  - Logs: HLE reports `bios_boot=HLE (shell skipped)` with kernel calls staying
    LLE on OpenBIOS; SCPH-1001 reports `bios_boot=LLE (real intro)`.
  - Screens: two requests returned "display disabled" and saved no image, HLE
    at frame 333 and SCPH-1001 at frame 910. SCPH-1001 frame 300 shows the Sony
    Computer Entertainment logo (OpenBIOS LLE: black). HLE frame 900: "A
    Polyphony Digital Production". Frame 1800 differs by mode because the boots
    take different lengths: HLE shows a field of orange glyphs inside the
    letterbox (as in an earlier scratch run), LLE OpenBIOS shows orange text
    "Alpha core dumped" followed by dots, and SCPH-1001 shows a flat gray
    letterboxed frame. Frames 3600 and 5400 show the live-action intro FMV in
    every mode, as does frame 7200 in both OpenBIOS modes. SCPH-1001 frame 7200
    is entirely black (brightest channel value 1); why is unknown.
  - Interpreter: 0.82–0.92 billion instructions run in the dirty-RAM
    interpreter by frame 7200, about 73% of them at PC `0x001208C8`, in overlay
    code above the EXE text end (`0x80120800`). The runtime reports "tcc tier
    active but no bundled toolchain … (overlay gaps -> interpreter)". The
    overlay capture store is `build-dev/overlay_captures.json`.
  - Text divergence (`dirty_ram_stats`): final `text_native_blocked` /
    `text_diverged_pages` are 8 / 1 (HLE), 6,336,172 / 4 (LLE OpenBIOS) and
    14,595,855 / 37 (SCPH-1001). Both counters reach these values by the
    frame-1800 checkpoint and stay flat to frame 7200. Hypothesis: the LLE
    boots run BIOS shell code inside the EXE's text range before the game EXE
    loads. What exactly the counters count (`psxrecomp/runtime/src/memory.c`)
    has not been read.
- Launcher (`launcher.sh`): the release binary opened "Omega Thrust - Launcher"
  with the disc verified (SCUS-94449, NTSC-U, ISO header OK, `Omega Boost
  (USA).cue`), D-Pad mode, two memory cards and no setup wizard; captured with
  `spectacle -b -n -a`; the script printed exit 0 after SIGTERM (its own output
  was not saved). It wrote `input.ini` and
  `keybinds.ini` in `build-release/`; no `saves/` directory was created.

## Phase 2 changes

- `generated/` added: `SCUS_944.49_decls.h`, `SCUS_944.49_dispatch.c`,
  `SCUS_944.49_full.ranges`, `SCUS_944.49_full_00.c` … `_45.c` (49 files).
- `.gitignore`: the header names its real base, `templates/gitignore.in`
  (round-2 finding F1); `overlay_captures.json*` widened to `overlay_captures.*`
  so the `.addendum.jsonl` capture history is ignored (round-2 finding F2).
- `AGENTS.md`: never-commit list names `overlay_captures.*`; rule that
  `overlay_capture_persist_dir` goes under `.cache/` and a
  `PSX_OVERLAY_CAPTURES` store outside the repository or under `.cache/`;
  verified generate commands (with the one-time `build_emitters.sh`) and build
  commands; the codegen-hash header as the one by-product inside the submodule;
  a Running section whose command runs from a scratch working directory; clang
  listed as the emitter compiler.
- This handoff: Phase 1 detail condensed (full record in `6ad5c9e`).

## Phase 2 checks (`checks-p2.log` on the round-1 tree; `checks-p2-r2.log` and `checks-p2-r3.log` re-run the gates on later rounds)

- The documented generate command: "0 updated", manifest equals run 1.
- `check_generated.sh --root .`: exit 0, dispatch plus 46 shards tracked.
- `check_boot_exe.sh .` and `check_bios_stamps.sh --framework psxrecomp`: exit 0.
- `record_pins.sh --root .` equals `framework_pins.txt`; submodules at the four
  pins, 0 porcelain lines each. With `--ignored`, only `psxrecomp` lists a file,
  `runtime/include/overlay_codegen_hash.h` (`checks-p2-r3.log`).
- Local-path grep over staged content (home, temp, mount and run directory
  prefixes, the local user name and the share's folder names; pattern in
  `checks-p2.sh`), re-run on each round's text: no match. No tracked file is
  ignored.
- `git check-ignore`: `overlay_captures.json`, `overlay_captures.addendum.jsonl`
  and `overlay_captures.json.d/…` at any depth, `build-*/…` and `.cache/…` are
  ignored; `generated/*` is not.
- The documented release and dev configure commands: exit 0, all four markers.
  Re-running configure regenerates `psx_bios_registry.c` and the mod-catalog
  stamps, so the next build recompiles that one file and relinks.
- `git diff --cached --check`: exit 2; every hit is generator output in
  `generated/` (trailing whitespace and blank lines at EOF), which is never
  hand-edited.
- Fresh-clone layout (`fresh_emitters.sh`, `fresh_emitters.log`, `fresh/`): a
  scratch export of round-1 tree `fac6f5e` (same `game.toml`, seeds and
  `generated/` as this snapshot) plus psxrecomp `8077e71`, with `generated/`
  removed. `build_emitters.sh`, then the documented `generate` twice. Run 1
  logged "Unstamped build directory … rebuilding once", rebuilt
  `build-recompiler/` with clang and wrote "46 updated"; run 2 logged "ninja:
  no work to do" and "0 updated". Output identical to the tree's `generated/`
  (`diff -r`) and to run 1's manifest (49 files, 72,927,315 bytes).
  `psxrecomp/recompiler/build` was not created, and nothing under `psxrecomp/`
  was created or changed.
- The documented headless run command, extracted from `AGENTS.md` and run
  unchanged from the repo root (`run_doc_check.sh`, `run_doc_check.log`): game
  config loaded, debug server listening, frame 566 reached, exit 0 after
  `quit`. The run report and memory cards were written in the `mktemp`
  directory, none in the repo root. `quit` replied "emu busy or frozen":
  `handle_quit` shuts the server down and exits before the I/O thread sees its
  reply (`debug_server.c:12805-12811`, `:16169-16183`).

## Hypotheses and unknowns

- Whether the orange glyph field (HLE frame 1800) and the gray frame
  (SCPH-1001 frame 1800) are correct: unknown until the Beetle comparison. The
  "Alpha core dumped" text in the LLE OpenBIOS run suggests the glyph field is
  part of the intro's computer-text sequence.
- Whether the eight emitted fallthroughs are faithful: unknown.
- The 697 seeds carry the intro to frame 7200 with no dispatch miss; menus and
  gameplay are untested (no input yet).
- Overlay code above `0x80120800` runs in the interpreter; its share of frame
  time and any accuracy effect are unknown.
- recomp-ui `864f778`: the launcher dashboard works; starting the game from
  PLAY has not been exercised.

## Review and commit state

- Phase 1: round 2 PASS on tree `b5ef902`; commit `6ad5c9e` pushed to the
  private `origin/master`. Its two Low findings (F1, F2) are resolved above.
  Declined round-2 suggestions: a separate worktree for later phases (instead,
  tracked and staged content does not change while a review runs), and noting
  that upstream treats `disc_probe*.json` as committed provenance (it embeds an
  absolute local path; the identity facts are in `AGENTS.md`).
- Phase 2 round 1, tree `fac6f5e`: NEEDS CHANGES. Resolutions:
  - Medium: this handoff and `AGENTS.md` said `generate` builds the emitters in
    `build-recompiler/`; on a fresh checkout it builds them in
    `psxrecomp/recompiler/build`. `AGENTS.md` now documents the one-time
    `build_emitters.sh` step (the upstream flow) and the real rule; the
    citations above are corrected; the fresh-clone check above verifies it.
  - Low: the function count now reads 1701 generated functions, with the steps.
  - Low: the run command used `$PWD` paths while telling the reader to run
    from a scratch directory. It now captures `REPO` first; verified unchanged.
  - Low: the screenshot summary listed two images that do not exist and missed
    the black SCPH-1001 frame 7200. Corrected.
  - Claims without saved evidence: the launcher's exit status is now labelled
    as unsaved output. The temp-directory claim was false and is corrected in
    the framework-tests bullet.
  - Suggestions adopted: the `PSX_OVERLAY_CAPTURES` rule and the "ninja: no
    work to do" wording. Declined: editing the README badges (they name the
    project's own repository) and narrowing `overlay_captures.*` (the broad
    pattern is the safer default; a future source file with that name would
    need a negation rule). The launcher's own output will be saved on its next
    run.
- Phase 2 round 2, tree `0e23f13`: NEEDS CHANGES, with every round-1 finding
  confirmed resolved and one new Low finding: the documented runtime build
  writes the framework's ignored `overlay_codegen_hash.h` inside the submodule,
  which the scope and `AGENTS.md` did not say. Resolved by documenting it as the
  one by-product (scope, build bullet, `AGENTS.md`, with the `--ignored` check).
  Suggestions adopted: the generator-reported line count, aligned
  `PSX_OVERLAY_CAPTURES` wording, citing the later check logs, and "CMake's
  default compiler" for `build_emitters.sh`.
- Phase 2 round 3: pending delta re-review.

## Next action

After a PASS: re-check the tree id and staged-diff hash, commit, push, and
delete the scratch generate and smoke copies. Then Phase 3: commit a route
runner under `scripts/routes/` built from `smoke.py`, drive input to the title
screen and menus, harvest misses, and decide on static overlay AOT for the hot
overlay at `0x801208C8`.

# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 3 change 4 (static overlay AOT), round 3. Invariant:
`aot/overlays.json` declares the 25 scene `.BIN` files whole at their load
address 0x80120000 (19 confirmed by the framework's generic extractor, 6 with
`allow_missing`), the disc's data-track SHA-1, the loader instructions that set
that base (`0x80075AF4` to `0x80075B00` in `SCUS_944.49`), 25 expected
records, strict bounds and `static_output` `generated/overlays_static.c`. The
documented `generate` writes `generated/overlays_static.c`,
`overlays_static_0000.c` to `overlays_static_0024.c` and
`AOT_STATIC_AUDIT.json` from the original disc only; the audit reports every
pair valid and every guard matching the known input bytes; a second run reuses
the shard and leaves `generated/` byte-identical, and the 49 earlier generated
files do not change. `CMakeLists.txt` links the shard through
`GAME_OVERLAY_STATIC_C`, placed above the list arguments, and both builds link
it with the codegen host. On that build, all nine committed routes pass in all
three boot modes with no unknown-dispatch or segment miss, and the
interpreter's instruction count at overlay addresses falls (measured). The
submodules stay at their pins with only the documented ignored by-product. No
new file holds a local path or base64 game bytes, and none exceeds 50 MB.
`AGENTS.md` describes the static step, its reuse rule and the
`recipe_input_sha256` behaviour. This file records change 3's round-2 verdict
and commit. Baseline: `8d56854`. Out of scope: runner and route changes, new
seeds, release packaging (`overlay_cache`), live campaign play, zones 7 and
later, Beetle (Phase 4), CI.

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

## Phase 2 (commit `e58cf21`)

`generated/`: 49 files, 72,927,315 bytes, 1701 functions from 697 seeds,
byte-identical across runs and when regenerated in a fresh-clone export.
`generate` builds its emitters with clang 23.1.1 in `build-recompiler/` after a
one-time `build_emitters.sh`; the release and dev builds (GCC 16.2.1, CI
template flags) link with one warning, in the vendored `stb_image.h`. A
no-input smoke matrix (HLE OpenBIOS, LLE OpenBIOS, LLE SCPH-1001) reached frame
7200 with no dispatch, segment or unknown-dispatch miss. The runtime build
writes the framework's ignored `overlay_codegen_hash.h` inside the submodule
whenever it is missing or stale (`psxrecomp/runtime/hash_codegen.cmake:47-53`).
Review: rounds 1 and 2 NEEDS CHANGES (documentation), round 3 PASS on tree
`8ab2284`. The full record is in `git show e58cf21:.agent/HANDOFF.md`.

## Phase 3 change 1 (commit `fc06141`)

`scripts/routes/run_route.py` plays a route in the format of
`psxrecomp/tools/perf_routes/` on the headless dev build through the runtime's
native `input_route_*` commands
(`psxrecomp/runtime/src/debug_server.c:8031-8097`; one step frame per runtime
frame, `main.cpp:7524`). A run fails unless the boot banner matches the mode,
the route plays to its end within the timeout, no unknown-dispatch or segment
miss is reported, and the runtime exits 0 after `quit`.
`scripts/routes/test_run_route.py` checks the runner against a fake runtime (15
tests), and `scripts/routes/title_to_zone1.json` reaches zone-1 gameplay in all
three modes. Facts carried forward: `psx-beetle` cannot replay routes at this
pin (`psxrecomp/runtime/src/beetle_debug_server.c:1847-1855`); route start
frames vary (22 to 112 in that change's saved runs); shots trail the end of
their step by 0 to 16 frames; the runner passes `PSX_OVERLAY_CAPTURES` through,
so route runs add to `build-dev/overlay_captures.json` (ignored). Of the 32
captures saved by then, 28 equal a scene `.BIN` (LOGO, MOVIE, TITLE, BRI1) at
offset `load_addr - 0x80120000`, and none is a zone file. Review: round 1
NEEDS CHANGES (two Medium, four Low), round 2 NEEDS CHANGES (one Low), round 3
PASS on tree `ede62b41`. The full record is in
`git show fc06141:.agent/HANDOFF.md`.

## Phase 3 change 2 (commit `4c22512`)

`scripts/routes/menus.json` opens every main-menu screen except CAMPAIGN PLAY
(TRAINING, ZONE PLAY, REPLAY, LOAD/SAVE, RANKING, OPTION, and OPTION > CONTROL
SETUPS) and backs out of each. `scripts/routes/demo_zone1.json` to
`demo_zone6.json` play each zone's REPLAY > DEMONSTRATION recording until
shortly after its COMPLETED results screen, which shows the same clear time in
all three modes (zone 1 1:45.06, zone 2 3:30.36, zone 3 4:11.43, zone 4
3:37.83, zone 5 3:51.06, zone 6 3:38.20). `scripts/routes/test_routes.py`
checks the committed route files without a build: exactly the listed routes,
accepted by `run_route.load_route`, unique names that match the file names,
and every shot step ending at least 30 frames before the next button change.
All 24 runs (eight routes, three modes) passed with no miss. Facts carried
forward: the main-menu cursor does not skip ZONE PLAY, which opens a zone
select; in the DEMONSTRATION list, 1ST to 6TH ZONE can be selected, and 7TH,
8TH, U1, U4, U8 and V5 showed DISABLE when selected (LAST, U2, U3, U5, U6, U7
and U9 were never selected); the 53 captures in the `build-dev` store then
held 47 scene `.BIN` pages (TITLE, BRI1, TU, LOGO, MOVIE) and no zone file.
Review: round 1 NEEDS CHANGES (four Low, this file's observations), round 2
NEEDS CHANGES (one Low, the checks section), round 3 PASS on tree `acd0532`
with no findings. The full record is in `git show 4c22512:.agent/HANDOFF.md`.

## Phase 3 change 3 (commit `8d56854`)

`scripts/routes/memcard.json` saves the environment data from LOAD/SAVE to
memory card 1, slot 1 (SAVE COMPLETED), loads it back (CHECKING MEMORY CARD,
the LOAD SAVED DATA? prompt, Up to OK, OPENING DATA, DATA READ COMPLETED) and
returns to the main menu. It passed in all three modes with no miss, and each
run's memory card 1 then held one valid save, `BASCUS-94449OMEBENV` (8192
bytes, a title starting 【ＶＩＥＷ】), while memory card 2 stayed blank.
`AGENTS.md` lists the route, and a new route needs an entry in that list and
in `LISTED` in `scripts/routes/test_routes.py`. Facts carried forward: the
load prompt's cursor starts on CANCEL; the LOAD/SAVE cursor does not wrap,
while OPTION's wraps and is remembered between visits; the environment save
does not record DIFFICULTY or INFORMATION; scripted zone-1 input without
steering (Square held, with taps of each shoulder button) cleared only the
first wave, with a best score of 4115, and whether the zone then needs
steering is a hypothesis; `psxrecomp-analyze` at the pin found no function
outside the generated code, 23 direct calls into the scene-overlay area and
160 indirect transfers with no static target, so it gave no seed; GameFAQs
(unverified) says zones U1 to U9 and V5 and the boost levels unlock by
completing the game under difficulty, AP and continue conditions. Review:
round 1 NEEDS CHANGES (one Low, the zone-1 bullet), round 2 PASS on tree
`41ee4b2`. The full record is in `git show 8d56854:.agent/HANDOFF.md`.

## Phase 3 change 4 observations (`.cache/evidence/overlay-aot/`, `.cache/evidence/phase3-4/`)

- Overlay layout (`overlay-aot/capture_search.py` / `.log`, `ram_search.py` /
  `ram_search-zone1.log`). Of 85 capture entries (53 in the `build-dev` store,
  32 in change 3's scratch exploration store, since deleted), 75 equal a scene
  `.BIN` (TITLE, BRI1, LOGO, TU, MOVIE) at offset `load_addr - 0x80120000`. The
  other 10 entries, 6 distinct pages, match MOVIE, BRI1 or TU at the same base
  for their first 1632 to 7456 bytes and then differ, which fits data the game
  writes inside the loaded image (hypothesis). During zone-1 gameplay
  (`title_to_zone1`, frame 7243) all 53,816 bytes of `S1/S1.BIN` are in RAM at
  0x80120000, and no other `.BIN` is. No capture holds a zone page although
  zone code ran (hypothesis: the store records a page only when it is
  replaced, and every zone run so far ended inside the zone).
- Loader (Phase 3 change 1 research; the checked words are in
  `aot/overlays.json`): in `func_80075AB4`, the block at `0x80075AF4` loads
  0x80120000 (`lui v0,0x8012`, `addiu v0,v0,0`) and stores it to `0x8009C03C`
  and to `16(s0)`.
- Generic extractor (`overlay-aot/extract_generic.log`; the framework's bounded
  discovery on the original disc, output in scratch): 19 files are raw-code
  producers at 0x80120000 by its call-fit scores (BRI1, BRI2, MOVIE, S1 to S6,
  S8 to S10, TITLE, TU, U2, U4, U6, U7, U9). It misses LOGO, U1, U3, U5, U8
  and V5 because their calls give too few votes for one address, not because
  they are small: U8 (44,948 bytes) is larger than seven of the 19 files
  found. The extractor places a file by voting: each call target in it votes
  for every load address at which it would land on an apparent function
  prologue, and an address is accepted only with at least 8 votes, twice the
  runner-up's, and at least a quarter as many votes as the file has apparent
  prologues (`psxrecomp/tools/aot_overlay_spike/extract_generic.py:328-360`).
  Rerun with the pinned extractor's own functions (`phase3-4/r2/raw_votes.py`
  / `.log`, which also reproduces the 19 scores in the extractor's log), each
  of the six has 0x80120000 as its top address, with 7 votes (LOGO, U3), 4
  (U5, V5) or 3 (U1, U8) against a runner-up's 1 or 2; U5, U8 and V5 also fail
  the quarter rule. RAM reads during the replays of U1, U3, U5, U8 and V5
  confirm that address (next bullet), and captures confirm LOGO's. A wrong
  address would cost coverage, not correctness, because every variant is
  guarded by the CRC of the bytes it was compiled from
  (`extract_generic.py:301-303`, `:336-338`). For these six files,
  `allow_missing` makes the pipeline build the record from the file's own
  bytes (prologues, leaf entries, supplemental seeds) instead of stopping
  (`psxrecomp/tools/aot_overlay_pipeline.py:559-572`); it does not skip the
  file.
- Load address of U1, U3, U5, U8 and V5 (`phase3-4/r3/ramcheck/`: `ramcheck.sh`
  / `.log`, `<zone>-ram.log`, the run outputs, `summary.py`; scratch, run
  during review round 2). On the scratch trial's build, in HLE OpenBIOS, each
  zone's DEMONSTRATION replay played with the user's unlocked save as card 1
  (through a scratch copy of the runner that preloads card 1 and scratch
  routes, both copied there), and after the replay's `t01800` shot step
  `overlay-aot/ram_search.py` read all 2 MiB of RAM (frames 12,766 to 13,981).
  In each run the file's 64 bytes at offset 0x1000 are at 0x80121000, and RAM
  equals the file from 0x80120000 for its first 7,804 of 7,808 bytes (U1), all
  13,712 (U3), 3,020 of 17,072 (U5), 44,944 of 44,948 (U8) and 3,548 of 19,616
  (V5). `ram_search.py` counts only the bytes before the first difference, so
  how much of U5 and V5 differs after that is not measured. Every other `.BIN`
  is absent or agrees for at most 4 bytes from the base its window implies.
  All five runs passed with no unknown-dispatch or segment miss.
- The generated dispatch runs in CPS mode
  (`generated/SCUS_944.49_dispatch.c:37616-37618`), and the static step
  compiles for it (`cps` is true in the audit's generation inputs).
- Scratch trial (`overlay-aot/trial/`): a fresh export of tree `41ee4b2` with
  this profile and the CMake wiring. `generate` built the shard, then reused it
  (identical manifests; the 49 earlier files unchanged). The first build failed
  to link with three undefined `psxrecomp_codegen_host_*` functions
  (`trial/attempt1/`). Its CMake edit was not saved, but the failure matches
  the after-`CODEGEN_SETUP_SOURCES` placement below exactly. With the keyword
  above the lists, the build linked (117 s at `-j4`).
- Keyword placement (`phase3-4/order_check.sh` / `.log`, configure only, on the
  trial tree). Above `GEN_FULL_GLOB` and `CODEGEN_SETUP_SOURCES`, configure
  passes and `build.ninja` has the 26 shard objects and the codegen host. After
  `GEN_FULL_GLOB`, configure fails
  (`psxrecomp/runtime/overlay_static_sources.cmake:42`). After
  `CODEGEN_SETUP_SOURCES`, configure passes with the 26 shard objects but no
  codegen host. Cause: `psxrecomp_add_game_runtime` parses those two as list
  arguments and forwards keywords it does not know
  (`psxrecomp/runtime/runtime.cmake:2536-2548`), so the keyword and its path
  join the setup-source list. The host source is appended after them
  (`:2721-2724`) and everything is passed on as `EXTRAS_SOURCES`
  (`:2747-2751`), where `psxrecomp_add_runtime_target` takes the path as its
  one-value `GAME_OVERLAY_STATIC_C` and leaves the host source unparsed
  (`:1399-1441`).
- Interpreter load (`overlay-aot/trial/trial_compare.sh` / `.log`,
  `insn_probe.py`; HLE OpenBIOS; the workspace `build-dev` without the shard
  against the trial build with it). `title_to_zone1` and `demo_zone1` passed on
  both builds. The interpreter ran 473,777,645 and 729,291,822 instructions
  without the shard and 1,113,140 and 1,171,851 with it; at overlay addresses,
  353,737,535 (190 PCs) and 578,435,952 (307 PCs) without it, and 1,309 (7
  PCs) and 12 (1 PC) with it.
- Workspace `generate` (`phase3-4/generate.sh` / `.log`). Run 1 built the shard
  in 20 s ("Verified 25 images / 25 recipes", "Published 34846 audited static
  variants in 26 files"). Run 2 printed `RESULT_STATIC=reused`, and the
  manifest stayed identical. The 49 tracked files are unchanged. The 27 new
  files hold 124,835,237 bytes in 3,534,300 lines; the largest is
  `overlays_static.c` at 10,798,356 bytes, and none has a local path. The 26 C
  files equal the trial's, and the audit differs from the trial's only in
  `recipe_input_sha256`. Audit: 25 recipes, `all_pairs_valid` and
  `all_guards_match_known_input_bytes` true, `full_static_coverage_proven`
  false, 34,846 published variants. psxrecomp shows only the ignored
  `overlay_codegen_hash.h`, which the static step writes with the runtime
  build's script (`aot_overlay_pipeline.py:902-920`).
- `recipe_input_sha256` (`phase3-4/recipe_hash.sh` / `.log`). The audit hashes
  `runtime-input-inventory.json` in a new `mkdtemp` work directory
  (`aot_overlay_pipeline.py:1098`, `:1119`;
  `psxrecomp/tools/audit_aot_cache.py:89`, `:187`), and the inventory names
  each job's input by absolute path (`aot_overlay_pipeline.py:706`). The work
  directory kept from the first scratch run shows both: its inventory hashes
  to `981632e9…`, the value that run's audit recorded, and names its inputs
  below `disc-aot-elxgt_z9/`. So every fresh build records a new value. Reuse
  instead compares the generation inputs recorded in the audit (profile,
  `game.toml`, disc SHA-1, recompiler, cache tag, CPS, gcc path, tool hashes,
  mod packages) and requires the published files to match the audit's hashes
  (`aot_overlay_pipeline.py:932-1001`).
- Guards and forced rebuild (`phase3-4/aot_checks.sh` / `.log`, on the trial
  copy). The pipeline's static action with the profile as committed published
  27 files, and their C equals the workspace's. With a wrong loader word it
  failed ("Loader evidence changed: SCUS_944.49 0x80075AF4", exit 1); with a
  wrong disc SHA-1 it reported the profile not applicable (exit 3); with 24
  expected records it failed ("Expected 24 recipes, got 25", exit 1). None of
  the three published a file. `generate --force-aot-static` in the trial
  rebuilt the shard: all 26 C files equal the workspace's, and the audit
  differs from the workspace's only in `recipe_input_sha256`, which also
  changed from the trial's earlier value.
- Content: the audit lists entries, CRCs and recipe names (34,846 variants),
  and neither it nor any shard file has a `bytes_b64` or base64 field, so no
  new file carries raw game bytes.
- Builds (`phase3-4/build.sh` / `.log`, the documented commands). Configure
  reports the usual markers, and both `build.ninja` files have the 26 shard
  objects and the codegen host. `build-release` took 79 s (286 of 287 steps)
  and `build-dev` 80 s (288 of 289) at `-j6`, each with the one vendored
  `stb_image.h` warning. The binaries are 55,203,560 and 56,790,000 bytes,
  each with 34,850 `psx_ov_static` symbols. Without the shard they were
  27,895,960 and 28,958,232 bytes: measured in Phase 2 but in no saved log,
  and re-measured by review round 1 on its own builds of `8d56854`
  (`phase3-4/review-r1.md`).
- Committed route runs (`phase3-4/routes.sh` / `routes.log`,
  `routes_summary.log`; the documented commands on this `build-dev`, one
  runtime at a time). All 27 runs pass: each boot banner matches its mode, no
  shot reports an unknown-dispatch or segment miss, every screenshot was taken,
  and every runtime exits 0. Start frames are 21 to 143, and each run's latest
  shot came 11 to 17 frames after its step ended. The contact sheets
  (`routes/<route>-<mode>_sheet.png`, `routes/<route>-modes_sheet.png`) of
  `title_to_zone1`, `menus` and `memcard` show the same screens as their runs
  before the shard (changes 2 and 3). Compared pixel by pixel
  (`r3/shot_diff.py` / `.log`), their 102 shots other than the intro differ
  from the earlier runs' in at most 4.9% of pixels (26 not at all), and the
  intro shot can catch the intro movie at a different moment (0 to 84.7% of
  pixels differ; `r3/intro-pair.png`). Gameplay shots in a replay can catch a
  different moment from run to run (review round 1 saw a rerun without the
  shard differ from the earlier run at 8 of 40 shots, `review-r1.md`), so for
  the six replays the comparison is their results screens: all six reach
  theirs in every mode, in the same route-frame ranges as change 2
  (`clear_time_check.log`, change 2's pixel rule;
  `routes/demo-zone<k>-end_sheet.png`). Zone 6's last results shot, `t14400`,
  is again on the boundary: HLE and SCPH-1001 show the results there and LLE
  OpenBIOS does not (in change 2 both LLE modes did and HLE did not). Card 1
  after the memcard runs has sha256 `42dd8d89…` in every mode, the same as
  change 3's runs.
- Interpreter counters (`probe/`, `probe_summary.log`; `insn_probe.py` beside
  each run). The interpreter ran 1.10 to 2.86 million instructions per run. At
  overlay addresses it ran 12 in each replay (one PC, 0x80120370), 1,194 in
  `menus` and 2,628 in `memcard` (0x80135EFC ran 1,182 and 2,616 of them), and
  1,309 in `title_to_zone1` (seven PCs, as in the trial), the same count for
  each route in all three modes. Without the shard, the trial measured
  353,737,535 and 578,435,952 for `title_to_zone1` and `demo_zone1`.
- Autocompile off (`phase3-4/autocompile_off.sh` / `autocompile.log`,
  `autocompile/`; HLE OpenBIOS, route outputs and capture stores in scratch;
  `status_probe.py` samples `autocompile_status` and `overlay_loader_status`).
  `title_to_zone1` and `demo_zone1` pass with the default setting and with
  `PSX_OVERLAY_AUTOCOMPILE_OFF=1`, which adds "overlay autocompile disabled by
  environment" to the log. In both settings the runtime prints "tcc tier active
  but no bundled toolchain … (overlay gaps -> interpreter)", autocapture is
  disabled, the compile provider is not configured and ran nothing
  (`configured` 0, `runs` 0), the DLL loader registered and loaded nothing
  (`registered` 0, `loads` 0, `dispatch_native` 0), and the interpreter ran
  the same overlay instructions (1,309 and 12). The loader's `static_hits`
  counted 15.7 to 16.2 million dispatches into the shard per run
  (`title_to_zone1` 15,744,982 and 15,721,135, `demo_zone1` 16,198,526 and
  16,071,491; `autocompile/*-status.json`), direct evidence that the shard
  runs. Its `dispatch_interp_fallback` (252,575 to 267,736) equals
  `static_address_misses` plus 1 in `demo_zone1` and plus 219 in
  `title_to_zone1`, and `static_crc_misses` was 456 and 358; what each counter
  counts was not traced in the source. So in this build the shard is the only
  native path for overlay code with either setting, and the setting changed
  nothing observable on these routes.

## Phase 3 change 4 changes

- `aot/overlays.json` (new): the profile described above, byte-identical to the
  one the trial verified (`overlay-aot/overlays.scratch.json` plus
  `static_output`).
- `CMakeLists.txt`: `GAME_OVERLAY_STATIC_C
  "${CMAKE_CURRENT_SOURCE_DIR}/generated/overlays_static.c"` after `APP_ICON`,
  above the list arguments, with a comment on its placement.
- `generated/`: 27 new files written by `generate` (`overlays_static.c`,
  `overlays_static_0000.c` to `overlays_static_0024.c`,
  `AOT_STATIC_AUDIT.json`); the 49 earlier files are unchanged.
- `AGENTS.md`: `generated/` also changes through `aot/overlays.json`; a new
  paragraph on the static step (inputs, outputs, reuse, `--force-aot-static`,
  `recipe_input_sha256`, the CMake keyword, interpreter fallback); the
  submodule by-product paragraph names the static step as a second writer of
  `overlay_codegen_hash.h`.
- `.agent/HANDOFF.md`: this rewrite. The Phase 0 to Phase 3 change 2 sections
  are unchanged, and change 3 is condensed.
- Round 2 changes only this file (review round 1: the extractor bullet, the
  fresh-export check, the loader counters, the interpreted PCs, the source of
  the earlier binary sizes, the screen comparison, the review state) and
  `AGENTS.md` (the full reuse rule).
- Round 3 changes this file (review round 2: the extractor wording, the RAM
  reads that place U1, U3, U5, U8 and V5, the pixel comparison of the
  non-replay shots, the review state, the next action) and `AGENTS.md` (which
  recompiler change forces a shard rebuild).

## Phase 3 change 4 checks

- Route runs: the 27 committed runs and the four autocompile runs above all
  pass (`routes_summary.log` "runs not passing: 0", `autocompile.log`), and no
  listener is left on port 4370.
- `checks-p3-4.sh` / `.log` (staged tree): all pass. Identity and status;
  `scripts/` and the 49 earlier generated files unchanged; the Phase 0 to change
  2 handoff sections equal HEAD and no placeholder is left; no local path in
  staged content; the largest blob is `overlays_static.c` (10,798,356 bytes),
  and no new file has a base64 field; the staged profile equals the verified
  scratch profile plus `static_output`; the keyword sits above the list
  arguments; `check_generated`, `check_boot_exe` and `check_bios_stamps` exit
  0; the pins equal `framework_pins.txt`, and the submodules are clean except
  psxrecomp's ignored `overlay_codegen_hash.h`; no tracked file is ignored; the
  documented `generate` reuses the shard and changes nothing; in a fresh export
  of the staged tree, `build_emitters.sh` and the documented `generate`
  regenerate the game C unchanged ("0 updated") and reuse the committed shard
  (`RESULT_STATIC=reused`), so `generated/` equals the staged files, and they
  write nothing under the export's `psxrecomp/` except that header (the reuse
  shows the shard is current, not that it reproduces; the forced rebuilds
  show that); both builds are current; the route, probe and autocompile
  summaries above; `test_routes.py` (4 OK) and `test_run_route.py` (15 OK)
  leave nothing behind; `git diff --cached --check` is clean outside
  `generated/`.
- Round 2, `r2/checks-p3-4-r2.sh` / `.log` (staged tree): the delta from the
  round-1 tree `1bf8f2b` touches only this file and `AGENTS.md`, and every
  other staged file equals round 1; the Phase 0 to change 2 sections still
  equal `HEAD`; no placeholder; no local path; the three gates exit 0; the
  pins and submodules are as in round 1; no tracked file is ignored; both
  test files pass and leave nothing behind. In a fresh export of the round-2
  tree, the documented `generate` reuses the shard, and `generate
  --force-aot-static` rebuilds it (`RESULT_STATIC=built`): all 26 C files are
  byte-identical to the staged ones, and the audit differs only in
  `recipe_input_sha256`. The facts behind the round-2 wording reproduce from
  saved files (`raw_votes.log`, `pc_entries.log`, the autocompile status
  probes, the disc listing). `git diff --cached --check` is clean outside
  `generated/`. No route was re-run: no route, script or build input changed.
- Round 3, `r3/checks-p3-4-r3.sh` / `.log` (staged tree): the delta from the
  round-2 tree `edd0ffe` touches only this file and `AGENTS.md`, and every
  other staged file equals round 1; the Phase 0 to change 2 sections still
  equal `HEAD`; no placeholder; no local path; the three gates exit 0; the
  pins and submodules are as before; no tracked file is ignored; both test
  files pass and leave nothing behind. In a fresh export of the round-3 tree,
  `build_emitters.sh` builds the recompiler with GCC; the documented
  `generate` rebuilds it with clang into the binary whose sha256 the audit
  records (`e13f0e78…`) and reuses the shard; `generate --force-emitters`
  wipes `build-recompiler/`, rebuilds the same binary and again reuses the
  shard, with `generated/` unchanged after each step; `generate
  --force-aot-static` then rebuilds the shard with all 26 C files
  byte-identical and only `recipe_input_sha256` changed in the audit.
  `ramcheck/summary.py` and `shot_diff.py` reproduce their saved output, and
  the saved RAM logs hold the numbers above. `git diff --cached --check` is
  clean outside `generated/`. No route was re-run on the workspace build: no
  route, script or build input changed.

## Hypotheses and unknowns

- The screens between the Polyphony card and the intro movie differ by boot
  mode at every checkpoint so far. At frame 1800 (Phase 2,
  `git show e58cf21:.agent/HANDOFF.md`), HLE showed the orange glyph field,
  LLE OpenBIOS orange text "Alpha core dumped ....", and SCPH-1001 a flat gray
  letterboxed frame; at the first exploration checkpoint of Phase 3 change 1,
  HLE showed the glyph field and LLE OpenBIOS a flat gray frame. The boots take
  different lengths, so equal frame numbers are not the same point of the
  intro. Whether these screens are correct: unknown until the Beetle
  comparison.
- Whether the eight emitted fallthroughs are faithful: unknown.
- Untested by committed routes: TRAINING lessons, ZONE PLAY zones, CAMPAIGN
  PLAY past zone 1, SAVE REPLAY and LOAD REPLAY, zones 7 and later, the extra
  zones, the ending and credits. The DEMONSTRATION routes run zones 1 to 6
  under recorded input; whether that reaches the code live play reaches is
  unknown. Any of the 160 statically unresolved indirect transfers that the
  routes do not reach can still miss later.
- What the environment save holds: unknown (not DIFFICULTY or INFORMATION; the
  next change examines an unlocked save, see Next action).
- Overlay code now runs from the static shard, except a few PCs that still go
  to the interpreter (0x80120370 in every route, 0x80135EFC in `menus` and
  `memcard`, seven PCs in `title_to_zone1`; `probe_summary.log`). The shard
  has no entry at 0x80135EFC (`phase3-4/r2/pc_entries.py` / `.log`, the
  probes' top five PCs against the audit). 0x80120370 has a MOVIE variant but
  lies below the runtime's overlay region floor, 0x120800, the end of the EXE
  text (`runtime.log`). The other four `title_to_zone1` PCs the probe kept
  (0x80127690, 0x801276B0, 0x801264B8, 0x8012649C) have variants only from
  S8, BRI2, S6 and U7, so other code at those addresses fails the CRC guard
  (hypothesis). Why the game runs code there, and whether the shard behaves
  like the interpreter beyond the committed routes: unknown until the Beetle
  comparison. `full_static_coverage_proven` is false: code the extractor
  cannot find statically still goes to the interpreter.
- How Phase 4 will feed route input to `psx-beetle`, which has no
  `input_route_*` command: unknown.
- recomp-ui `864f778`: the launcher dashboard works; starting the game from
  PLAY has not been exercised.

## Review and commit state

- Phase 1: round 2 PASS on tree `b5ef902`; commit `6ad5c9e`.
- Phase 2: round 3 PASS on tree `8ab2284`; commit `e58cf21`.
- Phase 3 change 1: round 3 PASS on tree `ede62b41`; commit `fc06141`.
  Deferred suggestions: ignore SIGINT during the runner's cleanup (round 2),
  and enforce one runtime per build with a lock file (round 3).
- Phase 3 change 2: round 3 PASS on tree `acd0532` (staged diff `9683aa9c…`)
  with no findings, after round 1 NEEDS CHANGES (four Low) and round 2 NEEDS
  CHANGES (one Low); commit `4c22512`, pushed to the private `origin/master`.
- Phase 3 change 3: round 2 PASS on tree `41ee4b2` (staged diff `ab8c63aa…`)
  with no findings, after round 1 NEEDS CHANGES (one Low, the zone-1 bullet);
  commit `8d56854`, pushed to the private `origin/master`. Round 2's three
  wording suggestions concern the committed record and are noted here: six Ups
  from LOAD SLOT2 end on LOAD SLOT1 whether or not the cursor wraps, so
  `difficulty3-top` is not no-wrap evidence (`load-slot1` and `difficulty3`
  are); in `explore-memcard`, the screens left the script at the load, while
  its OPTION presses had already landed on other rows than intended, because
  OPTION wraps and remembers its cursor; "its second Cross" means the load's
  second Cross.
- Phase 3 change 4, round 1 (tree `1bf8f2b`, staged diff `02a028bb…`;
  report `phase3-4/review-r1.md`): NEEDS CHANGES, two Low findings, both
  wording in this file that the draft commit message repeated. The checks
  bullet said the fresh export reproduced `generated/`, but its log shows
  `generate` reused the committed shard; resolved there, with forced rebuilds
  as the reproduction evidence. "The six small files" was wrong (U8 is 44,948
  bytes) and gave the wrong cause; resolved in the extractor bullet with the
  votes reproduced (`r2/raw_votes.log`). That reproduction differs from the
  report in two details: U5's and V5's runner-up has 1 vote, not 2, and U5
  and U8 fail the quarter rule as well as V5. The reviewer also built the
  tree, re-ran all 27 route runs (all pass, the same overlay instruction
  counts) and forced a shard rebuild (byte-identical C). Suggestions adopted:
  cite `static_hits`; narrow the interpreted PCs; complete the reuse rule in
  `AGENTS.md` (cache tag, CPS mode, mod packages, published files, the gcc
  path the audit records); say where the earlier binary sizes come from;
  restrict the screen comparison to the non-replay routes; reflow a stray
  short line. Not adopted: relating the interpreted PCs to the pages where
  captures diverge from TU and BRI1, which is a correlation only.
- Phase 3 change 4, round 2 (tree `edd0ffe`, staged diff `df201116…`;
  report `phase3-4/r2/review-r2.md`): NEEDS CHANGES, one Low finding, new in
  round 2's `AGENTS.md` text: it said another recompiler build is enough to
  force a shard rebuild, but the audit records the recompiler by the sha256 of
  its binary (`aot_overlay_pipeline.py:951`), and a rebuild from the same
  sources with the same toolchain gives the same binary, so the shard is
  reused (round 2's own fresh export showed the clang rebuild followed by
  `RESULT_STATIC=reused`). Resolved in `AGENTS.md`, with a `--force-emitters`
  rebuild added to the round-3 checks. The reviewer confirmed both round-1
  findings resolved. Suggestions adopted: the intro-shot caveat, with an exact
  pixel count (the report's 17% and 44% came from another measure); the
  extractor wording ("few calls" replaced by the votes); a stray short line in
  the draft commit message. Deferred: naming the last two interpreted
  `title_to_zone1` PCs, which the reviewer's own probe gives as 0x80126160
  (variants from S3, S5, S9 and TITLE) and 0x801261AC (U2, U4), because this
  record's probes kept only their top five PCs; the CRC-guard hypothesis above
  covers only the four PCs it names.
- Phase 3 change 4, round 3: pending delta re-review.

## Next action

After a PASS: commit and push. For zones 7 and later the user chose the
GameFAQs North American DexDrive save "All Zones Unlocked (Gamesharked)"
(GameFAQs save 20242), which the user downloaded. It stays outside version
control, in the ignored `.cache/saves/`; the raw card image (the file minus
its 3,904-byte DexDrive header) has sha256 `e3b71c25…` and holds one
`BASCUS-94449OMEBENV` save. In a scratch run on the trial build with that image
as card 1 (`.cache/evidence/phase3-5/exploration/`; a scratch copy of the
runner that preloads card 1), after LOAD SLOT1 all 19 DEMONSTRATION entries
show SELECT OK and all 19 ZONE PLAY zones show OPENED; the run passed with no
miss. Next change: a runner option that preloads card 1 from a pinned image,
and DEMONSTRATION routes for the 13 zones it opens (7TH, 8TH, LAST, U1 to U9,
V5). Independent of that, one change each:

- harvesting any misses with `psxrecomp/tools/collect_game_misses.py` (none so
  far);
- Phase 4, which needs a way to feed the same input to `psx-beetle`.

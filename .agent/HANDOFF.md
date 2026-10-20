# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 3 change 5 (routes for the zones an unlocked save
opens), round 2. Invariant: `scripts/routes/run_route.py` accepts an optional
route key `card1_sha256`. A route that declares it runs only with `--card1`
naming a readable 131,072-byte image with that sha256. The size (before the
file is read), the read and the hash are checked before launch, and each
refusal prints one line, so a refused run starts no runtime and leaves the
output directory untouched. The runner copies the image into the run's
`memcards/card1.mcd` and never writes the original, and `result.json` records
the declared hash (null for the other routes, whose cards start blank as
before). `--card1` is refused for a route that declares no card. Thirteen new
routes, `demo_zone7.json`, `demo_zone8.json`, `demo_zone_last.json`,
`demo_zone_u1.json` to `demo_zone_u9.json` and `demo_zone_v5.json`, declare
the hash of the user's unlocked save, load it with LOAD SLOT1, and play the
zone's REPLAY > DEMONSTRATION recording until shortly after its COMPLETED
results screen; no other route declares a card. All 22 committed routes pass
in all three boot modes with no unknown-dispatch or segment miss, and the 13
new replays reach their results screens. Both test files pass and leave
nothing behind; the new runner tests fail on the committed runner, and the
preload test fails if the runner links the image instead of copying it.
`AGENTS.md` documents the key, the option, the save's source and conversion,
and lists the routes; no save or card image is tracked, and `.gitignore` adds
`*.gme` and any-case memory card patterns. This file records change 4's
round-3 verdict and commit and adopts round 3's suggestion. Baseline:
`a4117a0`. Out of scope: other runner changes (SIGINT during cleanup, a lock
file), new seeds, the overlay shard, live campaign play, the ending, Beetle
(Phase 4), CI, packaging.

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

## Phase 3 change 4 (commit `a4117a0`)

`aot/overlays.json` declares the 25 scene `.BIN` overlays whole at
0x80120000, guarded by the disc's data-track SHA-1, the loader instructions
that set that base (`0x80075AF4` to `0x80075B00` in `SCUS_944.49`) and 25
expected records. The framework's generic extractor places 19 of the files;
LOGO, U1, U3, U5, U8 and V5 use `allow_missing`, because their calls give too
few votes for one address. The documented `generate` writes
`generated/overlays_static.c`, `overlays_static_0000.c` to
`overlays_static_0024.c` and `AOT_STATIC_AUDIT.json` from the original disc
(34,846 variants, each guarded by the CRC of the bytes it came from; 124.8 MB
of C, largest file 10.8 MB), and reuses them while the generation inputs in
the audit, including the recompiler binary's sha256 and the gcc path, are
unchanged; a forced rebuild writes the same C, and only the audit's
`recipe_input_sha256` changes. `CMakeLists.txt` links the shard through
`GAME_OVERLAY_STATIC_C`, above `GEN_FULL_GLOB` and `CODEGEN_SETUP_SOURCES`
(after the first, configure fails; after the second, the codegen host drops
out of the link). With the shard, the interpreter's instructions at overlay
addresses fell from 353,737,535 to 1,309 on `title_to_zone1` and from
578,435,952 to 12 on `demo_zone1`, and stayed at or below 2,628 in all 27
route runs, all of which passed. Facts carried forward: captures place LOGO,
and RAM reads place S1 during zone-1 gameplay and U1, U3, U5, U8 and V5 during
their replays, all at 0x80120000. Review round 3 reproduced the reads of the
five replay files (not S1's) on its own build of the committed tree and
counted every agreeing byte: U5 and V5 differ from their files in only 116
bytes each, in 18 small ranges starting at the first difference
(`phase3-4/r3/review-r3.md`; the change's own script counted only the bytes
before that difference). A few overlay PCs still go to
the interpreter (0x80120370 in every route, 0x80135EFC in `menus` and
`memcard`, seven PCs in `title_to_zone1`). The loader's `static_hits` counted
15.7 to 16.2 million dispatches into the shard per run, and
`PSX_OVERLAY_AUTOCOMPILE_OFF=1` changed nothing observable, because this build
has no overlay toolchain. Review: round 1 NEEDS CHANGES (two Low, this file's
wording), round 2 NEEDS CHANGES (one Low, `AGENTS.md`'s rebuild rule), round 3
PASS on tree `9ceae0d` with no findings. The full record is in
`git show a4117a0:.agent/HANDOFF.md`.

## Phase 3 change 5 observations (`.cache/evidence/phase3-5/`)

- The save (the user's decision for zones 7 and later): GameFAQs save 20242
  for Omega Boost, "All Zones Unlocked (Gamesharked)", a North American
  DexDrive file (GameFAQs lists it with the date 01/26/2010; the file itself
  carries no date). The user downloaded it in a browser after a
  scripted download got HTTP 403. The download, `omega-boost.20242.gme`
  (134,976 bytes, sha256 `40e7b8fb534b…`, header `123-456-STD`, card data from
  offset 3,904), is left untouched; a copy is in the ignored `.cache/saves/`.
  Its last 131,072 bytes, `.cache/saves/all-zones.mcd` (sha256
  `e3b71c252ce2…`), are a valid card image: header `MC`, every directory
  frame's checksum valid, and one save, `BASCUS-94449OMEBENV` in block 1 (8,192
  bytes, the same 【ＶＩＥＷ】 title as the game's own save).
- Against the game's own save from change 3 (card sha256 `42dd8d89…`), the
  directory entry is identical. Inside the save, the download has 19 bytes of
  01 at offsets 0x200 to 0x212 and 13 at 0x214 to 0x220, where the game's save
  has 01 only at 0x200 and 0x214 (hypothesis: one unlock flag per
  DEMONSTRATION entry, then the boost levels); a 4-byte value at 0x310 differs
  (hypothesis: a checksum), and the fill from 0x380 is 00 instead of FF.
- Exploration (`exploration/`; scratch, HLE OpenBIOS, change 4's trial build,
  a scratch copy of the runner that preloads card 1): after LOAD SLOT1, all 19
  DEMONSTRATION entries show SELECT OK and all 19 ZONE PLAY zones show OPENED.
  Listed times: 7TH 4:33, 8TH 1:44, LAST 4:56, U1 2:47, U2 2:22, U3 1:05, U4
  1:57, U5 1:07, U6 1:14, U7 1:46, U8 1:17, U9 2:05, V5 1:01 (8TH and LAST
  /HARD, the others /NORMAL).
- Scratch HLE runs of the 13 routes (`scratch-hle/`: generator, run script and
  log, outputs, `clear_time_check-hle.log`; the routes have the committed
  steps but no `card1_sha256` and older notes; the same scratch runner and
  build): all 13 passed with no miss. In each replay the results screen first
  appears in a shot 120 to 660 frames before the listed time (7TH at
  `t15900`, CLEAR TIME 4:15.50). U1 also shows a results screen mid-replay, at
  `t04800`, before its final one at `t09900` to `t10200` (CLEAR TIME 2:29.66).
- Scratch LLE runs (`scratch-lle/`: the runner and routes of this change as
  drafted, on change 4's trial build, port 4373): `demo_zone7`, `demo_zone8`,
  `demo_zone_last` and `demo_zone_u1` to `demo_zone_u3` passed in LLE OpenBIOS
  with no miss (start frames 37, 39, 55, 65, 61 and 60). I stopped the run
  during `demo_zone_u4` with SIGTERM, because the committed runs repeat it:
  its `result.json` records `runner stopped: SystemExit: stopped by SIGTERM`
  and runtime exit code 0. LLE SCPH-1001 was not run in scratch.
- After a run, memory card 1 differs from the image in 7 bytes, all in frame
  63 (offset 0x1F80, the card's write-test frame): the image has
  `11111111800c5a2708004003…`, the run's copy `11111111` followed by zeros.
  Which component writes it (game, BIOS or runtime) was not traced. The image
  itself is unchanged after the runs. In the 13 card routes, card 2 ends
  exactly as the runtime formats a missing card: its frame 63 is still the
  copy of frame 0 written then (`psxrecomp/runtime/src/memcard.c:45-84`,
  called at `:148-149`), and the rest equals the memcard route's card 2. In
  all 27 blank-card runs, frame 63 of both cards is rewritten (`11111111…`).
  So nothing changed card 2 in the card routes. My first card check expected
  card 2 to equal the memcard route's card 2 and reported 39 mismatches, all
  in this frame (`card_check-first.log`); the corrected check allows frame 63
  only.
- Committed route runs (`routes.log`, `routes_summary.log`): all 66 runs, the
  22 routes in three modes, passed: the boot banner matched the mode, no shot
  saw an unknown-dispatch or segment miss, every screenshot was taken, and the
  runtime exited 0. Start frames 34 to 139; shots at most 17 frames late. Each
  new route's `zone-cursor` shot shows its own zone in all three modes
  (`routes/zone-cursor-headers_sheet.png`). Each new route interprets 1,194
  overlay instructions in every mode (0x80135EFC 1,182 and 0x80120370 12, as
  `menus` does), and the nine earlier routes repeat change 4's counts
  (`probe_summary.log`).
- Results screens (`clear_time_check.log`, change 2's pixel rule): every
  replay reaches its results screen in all three modes. First to last results
  shot of the new routes: 7TH `t15900` to `t16500`; 8TH `t05700` to `t06300`
  (LLE OpenBIOS from `t06000`); LAST `t17400` to `t18000`; U1 `t09900` to
  `t10200`, after the mid-replay screen at `t04800`; U2 `t08100` to `t08700`;
  U3 `t03300` to `t03900` (LLE OpenBIOS from `t03600`); U4 `t06600` to
  `t06900`; U5 `t03600` to `t03900` (both LLE modes to `t04200`); U6 `t03900`
  to `t04500`; U7 `t05700` to `t06300`; U8 `t04200` to `t04800`; U9 `t06900`
  to `t07500`; V5 `t03300` to `t03600`. In each route the CLEAR TIME is the
  same in all three modes (`routes/clear-times_sheet.png`,
  `routes/results-mid_sheet.png`): 7TH 4:15.50, 8TH 1:26.60, LAST 4:39.06, U1
  2:29.66, U2 2:04.76, U3 0:48.23, U4 1:39.36, U5 0:49.56, U6 0:56.43, U7
  1:28.60, U8 0:59.86, U9 1:47.53, V5 0:44.33. Zones 1 to 6 repeat change 2's
  ranges; zone 6's last results shot was `t14100` in all three modes this
  time, where changes 2 and 4 also saw `t14400` in some modes.

## Phase 3 change 5 changes

- `scripts/routes/run_route.py`: the `card1_sha256` route key (64 lowercase
  hex digits, checked by `load_route`, which now also returns it) and the
  `--card1` option, as in the invariant; the docstring describes both. Round
  2: the image's size is checked with `stat()` before it is read, and an
  `OSError` from either becomes a one-line refusal naming the file.
- `scripts/routes/test_run_route.py`: the fake runtime records the sha256 of
  the `card1.mcd` it finds at startup and then rewrites that file's
  write-test frame, as real runs change it (round 2). New tests: a declared
  image is preloaded (the fake sees its hash, the run's copy holds the fake's
  write, the original is unchanged, `result.json` records the hash); the card
  arguments are checked before launch (no `--card1`, a missing file, another
  hash, the wrong size, an unreadable file (round 2; skipped as root),
  `--card1` for a route without the key: each exits 1 without a traceback,
  starts no runtime and creates no output directory); a hash that is not
  lowercase hex is a bad route; the pass test checks that a route without the
  key starts with no card 1 and records null. Since round 2, every subtest of
  the three argument tests starts from a clean state (no fake runtime, output
  directory or `.cache/`), so one regression fails one subtest. 17 tests.
- `scripts/routes/test_routes.py`: lists the 13 routes and checks that exactly
  they declare the save's hash.
- 13 route files, written by `.cache/evidence/phase3-5/gen_routes.py`, which
  reuses change 2's generator helpers; the checks regenerate them byte for
  byte.
- `AGENTS.md`: the never-commit list adds memory card images and save files;
  the route list adds the 13 routes; a paragraph on `card1_sha256` and
  `--card1`, the save's source and the commands that extract its card image.
- `.gitignore`: `*.gme`, and `.mcd`, `.mcr` and `.gme` in any letter case.
- `.agent/HANDOFF.md`: this rewrite. The Phase 0 to Phase 3 change 3 sections
  are unchanged, and change 4 is condensed with round 3's suggestion adopted.
  Round 2: the two corrected attributions, the adopted suggestions, the round 2
  checks and review state, and Next action, which now records the spike's
  results since round 1.

## Phase 3 change 5 checks

- Tests (`tests.sh` / `tests.log`): `test_routes.py` 5 OK and
  `test_run_route.py` 17 OK (11.4 s), with no temp directory, fake runtime or
  `__pycache__` left. Against the committed runner (a scratch copy with the
  new tests and routes), `test_routes.py` fails with 44 errors (the old
  `load_route` returns two values, so both per-route tests fail for each of
  the 22 routes), and `test_run_route.py` with 8 failures and 1 error, all in
  the card tests: the pass test (`result.json` has no `card1_sha256`), the
  bad-route card case and the check after it that no output directory was
  created, the five card-argument cases and the preload test.
- Route runs (`routes.sh` / `routes.log`): the documented commands, one run at
  a time on `build-dev` (port 4370), every route in all three modes, 02:03 to
  03:40 local time. `build-dev` was current: a rebuild afterwards ran no
  compile step and left the binary's sha256 and mtime (00:00, before the
  runs) unchanged (`build-dev-check.log`). The image hashed the same before
  and after (`card-before.sha256`, `card-after.sha256`).
  `routes_summary.log`: no run failed. `card_check.log`: every `result.json`
  records its route's hash (null for the nine others); card 1 differs from the
  image, and card 2 from the memcard route's card 2, only in frame 63. No
  listener on 4370 afterwards.
- `checks-p3-5.sh` / `.log` (staged tree): all pass. Nothing is unstaged or
  untracked; `generated/`, `aot/`, the build files, the submodules and the
  nine earlier routes equal HEAD, and so do this file's header and its Phase 0
  to Phase 3 change 3 sections; no placeholder, no added line over 80 columns,
  no local path. The three gates pass, the pins are equal, the submodules are
  clean and only psxrecomp's `overlay_codegen_hash.h` is ignored there. No
  tracked file is ignored, the save files and any-case card names are, and no
  card or save file is tracked. Every route passes `load_route`; the three
  generators reproduce all 21 generated routes byte for byte; `tests.sh` gives
  the results above; dropping the hash from `demo_zone7.json` or adding it to
  `menus.json` fails only `test_only_the_unlocked_save_routes_need_card1`. The
  route-run summaries are as above, `card_check.py` reproduces its log, and
  `git diff --cached --check` exits 0.
- Round 2 tests (`r2/tests.log`): `test_routes.py` 5 OK and
  `test_run_route.py` 17 OK, nothing left behind. Against the committed
  runner: the same 44 errors, and 8 failures and 1 error, now the pass test,
  the bad-route card case (whose output-directory check now runs inside the
  subtest), the six card-argument cases and the preload test.
- Round 2 regressions (`r2/test_regressions.py` / `.log`; the test file runs
  from a scratch copy beside each runner variant): the round-2 runner passes
  all 17 tests; the round-1 runner fails only the unreadable-image case; a
  runner that symlinks the image fails only the preload test, and passes
  round 1's tests; a runner without the SCPH-1001 `--bios` check fails the two
  cases that now launch, where round 1's tests also failed the third. Nothing
  was left behind. The real runner refuses a mode-000 copy of the save in one
  line (exit 1, no output directory).
- Round 2 route runs (`r2/routes.sh` / `r2/routes.log`): the documented
  commands with the round-2 runner, every route in all three modes, one run at
  a time on `build-dev`, 10:03 to 11:40 local time; round 1's outputs were
  moved to `routes-out-r1/` first. Two scratch spike runs on another build
  (port 4373, 11:13 to 11:26) overlapped about ten of these runs.
  `r2/routes_summary.log`: all 66 runs pass (banner matching the mode, no
  miss, every screenshot taken, exit 0; start frames 25 to 138, shots at most
  18 frames late). `r2/probe_summary.log` gives round 1's counts for every
  route. `r2/clear_time_check.log`: every replay reaches its results screen in
  every mode; against round 1, the first or last results shot moved by one
  shot in six route-mode pairs (U3 and U5 in two modes each, zones 6 and 8TH
  in one each), the edge variance noted above. `r2/card_check.log`: problems
  0, the same lines as round 1's; the image hashed the same before and after
  (`r2/card-before.sha256`, `r2/card-after.sha256`). No listener on 4370
  afterwards.
- Round 2, `r2/checks-p3-5-r2.sh` / `.log` (staged tree): all pass. Against
  the round-1 tree, only this file, the runner and the runner tests changed;
  `generated/`, `aot/`, the build files and the submodules equal HEAD, and so
  do this file's header and its Phase 0 to Phase 3 change 3 sections; no
  placeholder, no added line over 80 columns, no local path. The three gates
  pass, the pins are equal, the submodules are clean and only psxrecomp's
  `overlay_codegen_hash.h` is ignored there; no tracked file is ignored, the
  save files and any-case card names are, and no card or save file is
  tracked. Every route passes `load_route`; the three generators reproduce
  the 21 generated routes; `tests.sh` gives the round 2 results above, and
  `test_regressions.py` reproduces its log (test durations aside); the two
  card-test mutations fail only `test_only_the_unlocked_save_routes_need_card1`.
  The route-run summaries are as above, `card_check.py` reproduces its log, a
  rebuild of `build-dev` compiles nothing and keeps the binary, and
  `git diff --cached --check` exits 0.

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
- Untested by committed routes: TRAINING lessons, ZONE PLAY zones, and SAVE
  REPLAY and LOAD REPLAY, which scripted menu input may reach; CAMPAIGN PLAY
  past zone 1, the ending and credits, which need steering. The
  DEMONSTRATION routes now run all 19 zones, but under recorded input; whether
  that reaches the code live play reaches is unknown. Any of the 160
  statically unresolved indirect transfers that the routes do not reach can
  still miss later.
- The unlocked save is user-made ("Gamesharked"): the routes show which
  replays its flags open, not that completing the game writes the same flags.
  Which byte opens which zone, and what else the environment save holds, are
  hypotheses (it does not record DIFFICULTY or INFORMATION, change 3).
- Overlay code now runs from the static shard, except a few PCs that still go
  to the interpreter (0x80120370 in every route; 0x80135EFC in `menus`,
  `memcard` and the 13 unlocked-zone routes, 1,182 instructions in each of
  those 13; seven PCs in `title_to_zone1`; `phase3-4/probe_summary.log`,
  `phase3-5/probe_summary.log`). The
  shard has no entry at 0x80135EFC (`phase3-4/r2/pc_entries.py` / `.log`, the
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
- Phase 3 change 4: round 3 PASS on tree `9ceae0d` (staged diff `a248fe03…`)
  with no findings, after round 1 NEEDS CHANGES (two Low: the fresh-export
  check reused rather than reproduced the shard, and the six `allow_missing`
  files are call-sparse, not small) and round 2 NEEDS CHANGES (one Low: which
  recompiler change forces a shard rebuild); commit `a4117a0`, pushed to the
  private `origin/master`. Reports: `phase3-4/review-r1.md`,
  `phase3-4/r2/review-r2.md`, `phase3-4/r3/review-r3.md`. Round 3's one
  suggestion (record its reproduction of the RAM reads and the U5 and V5 byte
  counts) is adopted in the change 4 section above. Still deferred: naming the
  last two interpreted `title_to_zone1` PCs (0x80126160 and 0x801261AC, from
  the reviewer's own round-1 probe, reported in round 2).
- Phase 3 change 5: round 1 NEEDS CHANGES on tree `a831f14` (staged diff
  `f9f6044f…`; report `phase3-5/review-r1.md`), three Low. (1) The preload
  test's check that the original image is unchanged could not fail, because
  the fake runtime only read the card: a runner that symlinked the image
  passed all 17 tests. (2) The condensed change 4 record said review round 3
  reproduced S1's RAM read (it ran only the five replays) and credited the two
  deferred PCs to round 2's probe (the reviewer's round-1 probe, reported in
  round 2). (3) An unreadable `--card1` ended in a traceback. Resolved in
  round 2: the fake rewrites the card's write-test frame, and the symlink
  mutation now fails the preload test while passing round 1's tests; both
  attributions are corrected; the runner refuses an unreadable image in one
  line, and the round-1 runner fails only the new test case for it
  (`r2/test_regressions.py` / `.log`). Suggestions adopted: the size check
  before reading; a clean state for every argument subtest (a mutation that
  drops the BIOS check now fails two subtests instead of three); 0x80135EFC
  in the 13 card routes; the scripted-route candidates in Next action; the
  save's date as GameFAQs lists it. Declined: an upper bound on the pixel
  rule at the full counts (label 361, banner 1103). On round 1's outputs it
  drops 20 shots, all of them results screens on the contact sheet, with
  labels up to 573 and banners up to 1,274 while the sweep bar crosses the
  boxes (`r2/clear_time_check_capped.py`, `-round1-outputs.log`,
  `r2/capped-dropped_sheet.png`). Deferred: the notes' fine-cadence wording
  (it starts at the listed TIME minus 1,200 frames rounded down to a multiple
  of 300); all 19 demo routes share the sentence, so the next change that
  regenerates them fixes it. The earlier deferred suggestions stand.
- Phase 3 change 5, round 2: pending delta re-review.

## Next action

After a PASS: commit and push. Every zone's DEMONSTRATION replay then runs
under a committed route. No route reaches TRAINING lessons, ZONE PLAY zones,
or SAVE REPLAY and LOAD REPLAY yet, which scripted menu input may reach, nor
CAMPAIGN PLAY past zone 1, the ending and the credits, which need steering:
scripted input without steering cleared only zone 1's first wave (change 3).
For those, the user chose a spike first, in scratch. Its first step is done
(`.cache/evidence/spike-replay/`): each of `REPLAY/REPLAY00.DAT` to
`REPLAY18.DAT` (23,404 bytes) holds one zone's recorded input, an 8-byte
input state per 30 fps game frame, run-length coded (`decode_replay.py`,
`decode.log`). Each file's frame count, difficulty and level match its
DEMONSTRATION entry's listed time, difficulty and LEVEL. Every recording
steers with the analog stick, off centre in 82 to 99% of its frames
(`stick_use.py` / `.log`), and routes carry only the 16 button bits, so the
recordings cannot become route input without a framework change. The user
chose to continue with the debug server's memory writes, time-boxed, in
scratch and labelled harness-assisted. The campaign loop (0x8002F814) walks a
17-step script at 0x8001232C: two briefings, nine zones, four between-zone
movies (INTER1 to INTER4), END_ALL and the staff credits (STAFF320). The
functions it calls save its script pointer and step on the stack; rewriting
both while a step runs makes the loop continue after the chosen step
(`spike_ending.py`, `spike_tour.py`). Skipping the zones that way, the four
movies, END_ALL, the credits and the closing copyright screen ran with no miss
(`runs/ending/`, `runs/tour/`, with contact sheets). A Start press on the
copyright screen ended the campaign. The game then entered state 7, whose
handler (`func_8002DC48`) calls the replay player's step (0x80077228), and the
function at 0x800571B8 called the scene entry stored when the BRI1 briefing
started (0x80120EAC). Other data filled the overlay area there (the word at
0x80120EAC is a reserved opcode), so the runtime halted on an unknown dispatch
(`runs/tour/postmortem.log`). The writes skipped every zone step, which
normally runs between those scenes, so this may be an artifact of the harness
(hypothesis); real play to the ending, or the same path under Beetle, would
settle it. How to continue is the user's decision. Independent of that, one
change each:

- harvesting any misses with `psxrecomp/tools/collect_game_misses.py` (none so
  far);
- Phase 4, which needs a way to feed the same input to `psx-beetle`.

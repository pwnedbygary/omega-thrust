# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 3 change 2 (menu and demonstration routes), round 3.
Invariant: `scripts/routes/menus.json` opens every main-menu screen except
CAMPAIGN PLAY (TRAINING, ZONE PLAY, REPLAY, LOAD/SAVE, RANKING, OPTION, and
OPTION > CONTROL SETUPS) and backs out of each without starting a lesson, zone
or replay. `scripts/routes/demo_zone1.json` to `demo_zone6.json` each play one
zone's REPLAY > DEMONSTRATION recording until shortly after its COMPLETED
screen. Every committed route passes `scripts/routes/run_route.py` (unchanged)
in all three boot modes with no unknown-dispatch or segment miss.
`scripts/routes/test_routes.py` checks the committed route files without a
build: they are exactly the eight routes `AGENTS.md` lists, the runner accepts
each file, route names are unique and match their file names, and every shot
step ends at least 30 frames before the next button change. `AGENTS.md` lists
the routes and their commands, and its `state.toml` paragraph cites the source
that ties every launch to `save_state`. The observations below match the saved
evidence. Baseline: `fc06141`. Out of scope: runner changes, new seeds, overlay
AOT, memory-card writes, starting a lesson or a ZONE PLAY zone, CAMPAIGN PLAY
past zone 1, Beetle (Phase 4), CI, packaging.

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

## Phase 3 change 2 observations (`.cache/evidence/phase3-2/`)

- Scratch exploration before the routes, HLE OpenBIOS only, every run PASS
  with no miss (`exploration/`, with the route files `exploration/explore_*.json`;
  capture stores left out because they hold game code):
  - Main menu (`exploration/explore-menu/`, `explore-menus2/`,
    `explore-z67-loadsave/`, `cand-menus2/`): the cursor starts on CAMPAIGN
    PLAY, and each Down moves it one entry: TRAINING, ZONE PLAY, REPLAY,
    LOAD/SAVE, RANKING, OPTION. Start confirms on the main menu. On the screens
    below it, Cross confirms (Circle also opened CONTROL SETUPS), and Triangle
    goes back one screen with the cursor where it was.
  - Correction to an earlier report to the user: "the cursor skips ZONE PLAY"
    and "presses 60 frames apart drop one" were misreadings of
    `exploration/explore-menu/`, whose shot steps ended exactly at the next
    press. Its `down2` shot was read at frame 5495, after the third Down
    (frames 5487 to 5492), so it showed REPLAY. Three Downs 60 frames apart
    reached REPLAY in `exploration/explore-demo/`, as expected, and with the
    30-frame margin two Downs reach ZONE PLAY, which opens
    (`exploration/cand-menus2/hle-openbios/05-zone-play.png`).
  - Screens (`exploration/cand-menus2/hle-openbios/`, sheet
    `exploration/cand_menus2_sheet.png`; the committed menus route shows the
    same in all three modes, `.cache/routes/menus/<mode>/`, with the same file
    names): TRAINING lists LESSON 1 to 4 (LESSON 1 "SCAN SEARCH MISSION");
    ZONE PLAY shows 1ST ZONE OPENED with LEVEL 1 2 3; REPLAY lists START
    REPLAY, SAVE REPLAY, LOAD REPLAY and DEMONSTRATION under the line "NO
    REPLAY DATA", with DISABLE beside START REPLAY and SAVE REPLAY only
    (`07-replay.png`); LOAD/SAVE shows LOAD SLOT1 ("LOAD SLOT 1 ENVIRONMENT
    DATA"), SAVE SLOT1, LOAD SLOT2 and SAVE SLOT2; RANKING shows a score
    table; OPTION lists CONTROL, SELECT BGM, BGM VOLUME, SE VOLUME,
    DIFFICULTY, INFORMATION and ADJUST SCREEN under the line "CONTROL SETUPS"
    (`13-option.png`); Cross on CONTROL opens CONTROL SETUPS, the controller
    diagram (`14-control-setups.png`). With no input, the TRAINING list stayed
    for 9000 frames (`exploration/explore-training/`,
    `exploration/training_sheet.png`).
  - DEMONSTRATION (`exploration/explore-zonelist/`, `explore-z67-loadsave/`,
    `explore-demo*/`, `explore-z1/` to `explore-z6/`): Cross opens a list of
    19 entries (1ST to 8TH ZONE, LAST ZONE, U1 to U9 ZONE, V5 ZONE; the disc
    has `REPLAY/REPLAY00.DAT` to `REPLAY18.DAT`). 1ST to 6TH ZONE show SELECT
    OK, with listed TIME 2:02, 3:48, 4:29, 3:55 and 4:08 /NORMAL and 3:55
    /HARD. Of the other 13 entries, the saved shots select six, and each shows
    DISABLE: 7TH ZONE (`explore-z67-loadsave/hle-openbios/01-zone7.png`) and
    8TH (while the list scrolls), U1, U4, U8 and V5 ZONE
    (`explore-zonelist/hle-openbios/01-zdown06.png` to `05-zdown18.png`; those
    shot steps end where the next Down begins, so some shots show the entry
    after the one their name implies). LAST ZONE, U2, U3, U5, U6, U7 and U9
    ZONE were never selected, so their state is unknown. Cross on an enabled
    zone plays its recording with a REPLAY overlay. The watches in
    `explore-z1/` to `explore-z6/` set the committed routes' timing.
- Committed routes, documented commands as written, one runtime at a time
  (`routes.sh`, `routes.log`, `routes/<name>-<mode>.log`, summary
  `routes_summary.log`; outputs in `.cache/routes/<name>/<mode>/`; sheets
  `routes/<name>-<mode>_sheet.png`): all 24 runs (8 routes in 3 modes) PASS,
  from 21:07:56 to 21:44:33. In every run the banner matches the mode, every
  shot reports 0 unknown-dispatch and 0 segment misses, every screenshot was
  taken, and the runtime exits 0. Start frames 30 to 123; shots at most 16
  frames late. The menus route shows the same 17 intended screens in every mode
  (`routes/menus-modes_sheet.png`), and the zone-1 route the intro, title, main
  menu, briefing and zone-1 gameplay (`routes/title-to-zone1-modes_sheet.png`).
  `routes.sh` first moved change 1's round-3 outputs from
  `.cache/routes/title-to-zone1/<mode>/` to
  `.cache/evidence/phase3-1/r3/routes/<mode>/`.
- Demonstration end screens (`demo_end_sheets.py`,
  `routes/demo-zone<k>-end_sheet.png`; pixel check `r2/clear_time_check.py` /
  `.log`): a shot shows the COMPLETED results screen when its COMPLETED banner
  is fully drawn and its CLEAR TIME line has appeared (the check requires at
  least 1100 cyan pixels in the banner, which counts 1103 when full, and at
  least 100 in the label, which counts 361 when full). Neither threshold alone
  separates the cases: a half-drawn banner with its wipe bar reaches 1155
  pixels in the banner box (zone 6 `t13500`, HLE), and gameplay beams put up to
  167 in the label box (zone 4 `t06600`, HLE) and up to 759 in the banner box
  (zone 6 `t02400`, HLE); only the two together do. By that rule every
  zone's replay shows its results screen with the same clear time in all three
  modes, at the same shots except zone 6's last: zone 1 `t06900` to `t07500`
  (1:45.06), zone 2 `t13200` to `t13800` (3:30.36), zone 3 `t15600` to
  `t16200` (4:11.43), zone 4 `t13500` (label still being drawn) to `t14100`
  (3:37.83), zone 5 `t14400` to `t15000` (3:51.06), zone 6 `t13800` to
  `t14100` in HLE and to `t14400` in both LLE modes (3:38.20). In zones 1 and
  6 the shot before the range shows only a half-drawn banner (`t06600`,
  `t13500`). Gameplay follows the results screen in every zone.
- Zone 6's `t14400` shot is black in HLE (route frame 22067, 7 frames late) and
  the results screen in both LLE modes (22063 and 22064). In the reviewer's
  independent build the same shot showed the results screen in all three
  modes, HLE at route frame 22064 and LLE OpenBIOS at 22065
  (`r2/review-r1.md`). So the HLE results screen ends after frame 22064 and by
  22067, consistent with one end frame (22066 or 22067) in every mode; a
  difference of a frame or two between modes is not excluded.

## Phase 3 change 2 changes

- `scripts/routes/menus.json` (new): 62 steps, 11,202 frames. Each screen is
  opened with a 6-frame press and left with Triangle; presses are at least 120
  frames apart, and every shot step ends 30 frames before the next press.
- `scripts/routes/demo_zone1.json` to `demo_zone6.json` (new): 47 to 69 steps,
  16,030 to 24,682 frames. Each opens REPLAY > DEMONSTRATION, moves to its zone
  and presses Cross, then waits until 1200 frames after the listed TIME,
  rounded up to a multiple of 600, with a shot every 600 frames and every 300
  from 1200 frames before the listed TIME (rounded down to a multiple of 300).
  Shot step `tNNNNN` ends NNNNN frames after the Cross press began.
- Both are written by the scratch generator `gen_routes.py` (not committed):
  one step per line like `title_to_zone1.json`, mode 0644. The committed JSON
  is the source of truth; the checks regenerate the files and compare them byte
  for byte.
- `scripts/routes/test_routes.py` (new, 100755): four stdlib tests over the
  committed route files: the route files are exactly the eight routes
  `AGENTS.md` lists (round-1 and round-2 suggestions); `run_route.load_route`
  accepts each file, and its `name` with `-` read as `_` equals the file name;
  names are unique; every shot step ends at least 30 frames before the next
  button change. It adopts change 1's round-3 suggestion that `load_route` warn
  about shot margins, as a test of the committed files instead of a runner
  change.
- `AGENTS.md`: lists the committed routes, shows the route commands for any
  `<route>.json`, adds `test_routes.py`, extends the verification rule to every
  route, and cites `psxrecomp/runtime/include/mod_runtime.h:22` and
  `psxrecomp/runtime/src/mod_runtime.cpp:1647` in the `state.toml` paragraph
  (change 1's round-3 suggestion 3).
- `.agent/HANDOFF.md`: this rewrite. The Phase 0 to Phase 2 sections are
  unchanged, and Phase 3 change 1 is condensed.

## Phase 3 change 2 checks

- `build-dev` is current with `fc06141`: `cmake --build build-dev --target
  psx-runtime -j6` re-ran only its always-run steps (the game-C check and the
  mod-catalog staging and verification) and compiled nothing
  (`build-dev-check.log`).
- `test_routes_regression.sh` / `.log`: `test_routes.py` fails the shot-margin
  test for exactly the four shot steps (intro, title, main-menu, briefing) of
  the round-2 `title_to_zone1.json` (sha256 `2d2bf910354f…`, tree `24d16254`),
  which ended at the next press, and passes on the committed route.
- Route runs: `routes.sh` with the SCPH-1001 v2.2 dump; `routes_summary.py`
  reports `runs not passing: 0` (`routes_summary.log`), and `routes.log` ends
  with no listener on port 4370.
- Round 1, `checks-p3-2.sh` / `.log` (staged tree `6ab537c0`, with the round-1
  `test_routes.py`): the runner and its tests are unchanged from `HEAD`; the
  local-path grep finds nothing; `check_generated`, `check_boot_exe` and
  `check_bios_stamps` exit 0; the pins equal `framework_pins.txt`, the four
  submodules are at their pins with no changes, and the only ignored file
  inside them is psxrecomp's `overlay_codegen_hash.h`; no tracked file is
  ignored; every route passes `run_route.load_route`; regenerating the menus
  and demo routes with `gen_routes.py` gives byte-identical files;
  `test_routes.py` passes its 4 tests and `test_run_route.py` its 15, leaving
  no fake runtime, temp directory or `__pycache__`; `routes_summary.py` exits
  0; nothing listens on ports 4370 to 4379; `git diff --cached --check` exits
  0.
- Round 2, `r2/checks-p3-2-r2.sh` / `.log` (staged tree `9a95a09`): the same
  checks, all passing, plus: the delta from the round-1 tree changes only this
  file, `AGENTS.md` and `test_routes.py`, and no route file; this file's
  Phase 0 to Phase 2 sections equal `HEAD`, and it has no placeholder; and
  `r2/clear_time_check.py` reproduces its saved log byte for byte.
  `r2/test_routes_listed.sh` / `.log`: on a scratch copy of the scripts the 4
  tests pass, and without `menus.json` exactly the listed-routes test fails
  (route `menus`), exit 1.
- Round 3, `r3/checks-p3-2-r3.sh` / `.log` (staged tree): the round-2 checks,
  with the delta taken from the round-2 tree, all passing.
  `r3/test_routes_listed.sh` / `.log`: on a scratch copy the 4 tests pass;
  without `menus.json`, and with an unlisted copy of it named
  `extra_route.json`, exactly `test_route_files_match_the_list` fails, exit 1
  each time.

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
- Untested by committed routes: memory-card saves and loads, TRAINING lessons,
  ZONE PLAY zones, CAMPAIGN PLAY past zone 1, zones 7 and later (every later
  DEMONSTRATION entry selected so far shows DISABLE), the ending and credits.
  The DEMONSTRATION routes run zones 1 to 6 under recorded input. Whether that
  reaches the code live play reaches, and whether scripted input can clear a
  zone: unknown.
- Overlay code above `0x80120800` runs in the interpreter; its share of frame
  time and any accuracy effect are unknown. The capture store beside
  `build-dev` (every run since Phase 2 that did not redirect it, now including
  every committed route in all three modes) holds 53 captures
  (`capture_match.log`, from `.cache/evidence/phase3-1/r2/capture_match.py`):
  47 equal a scene `.BIN` at offset `load_addr - 0x80120000` (TITLE 36, BRI1
  5, TU 3, LOGO 2, MOVIE 1), and 6 match none (pages at `0x80121000`,
  `0x80122000`, two at `0x80126000` and two at `0x80127000`). None equals a
  zone file, although zones 1 to 6 played. Where zone code runs, and what the
  unmatched pages hold: unknown.
- How Phase 4 will feed route input to `psx-beetle`, which has no
  `input_route_*` command: unknown.
- recomp-ui `864f778`: the launcher dashboard works; starting the game from
  PLAY has not been exercised.

## Review and commit state

- Phase 1: round 2 PASS on tree `b5ef902`; commit `6ad5c9e`.
- Phase 2: round 3 PASS on tree `8ab2284`; commit `e58cf21`.
- Phase 3 change 1: round 3 PASS on tree `ede62b41` (staged diff
  `8bab9784…`) with no findings, after round 1 NEEDS CHANGES (two Medium, four
  Low) and round 2 NEEDS CHANGES (one Low); commit `fc06141`, pushed to the
  private `origin/master`. Its round-3 suggestions: the shot-margin check (1)
  is adopted here as `test_routes.py`; on the lag definitions (2), round-1 lags
  were read after the screenshot, so the 0-to-14 range of change 1's saved
  runs treats them as upper bounds; the `save_state` citations (3) are applied
  here; a lock file that enforces one runtime per build (4) is deferred,
  because it is a runner change and a second launch from one build already
  fails closed at startup. Round-2 suggestion 8 (ignore SIGINT during cleanup)
  stays deferred.
- Phase 3 change 2, round 1 (tree `6ab537c0`, staged diff `aa1ac2c1…`; report
  saved as `.cache/evidence/phase3-2/r2/review-r1.md`): NEEDS CHANGES, four
  Low findings in this file's observations, all corrected above. (1) The
  REPLAY screen shows DISABLE beside START REPLAY and SAVE REPLAY only, not
  LOAD REPLAY. (2) OPTION's entries run from CONTROL to ADJUST SCREEN; CONTROL
  SETUPS is the description line. (3) Only six of the 13 later DEMONSTRATION
  entries were ever selected. (4) Zone 6's range started at a half-drawn
  banner, which zone 1's range leaves out; every range now follows one pixel
  rule. Suggestions adopted: the zone 6 end-frame observation, the zone 6
  caveat in the commit message, `test_routes.py` checking every listed route,
  and the lag-range and build-check wording. The reviewer re-ran all 24 route
  runs on its own build: 24 PASS, 0 misses.
- Phase 3 change 2, round 2 (tree `9a95a09`, staged diff `55e7e7cb…`): NEEDS
  CHANGES, one Low finding: this file's checks section still described round 1
  only, so a round-1 log read as the checks of the committed tree, and the new
  test's regression evidence was not recorded. The checks section now has a
  bullet per round. The reviewer confirmed all four round-1 findings and the
  five suggestions resolved. Suggestions adopted: the sentence on why the pixel
  rule needs both thresholds; `test_routes.py` now requires the route files to
  be exactly the listed routes, so an unlisted file fails too; the commit
  message reuses this file's wording for zone 6's end frame.
- Phase 3 change 2, round 3: pending delta re-review.

## Next action

After a PASS: commit and push. Next Phase 3 changes, one per commit:

- a zone-1 route with real input, to learn whether scripted play can clear a
  zone, and memory-card save and load routes through LOAD/SAVE;
- harvesting any misses with `psxrecomp/tools/collect_game_misses.py` (none so
  far);
- static overlay AOT for the scene `.BIN` overlays, as its own change.

Phase 4 needs a way to feed the same input to `psx-beetle`.

# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 3 change 3 (memory-card route), round 2. Invariant:
`scripts/routes/memcard.json` opens LOAD/SAVE, saves the environment data to
memory card 1, slot 1 (SAVE COMPLETED), returns to the main menu, opens
LOAD/SAVE again and loads slot 1 (CHECKING MEMORY CARD, the LOAD SAVED DATA?
prompt, OK, OPENING DATA, DATA READ COMPLETED), then returns to the main menu.
It passes `scripts/routes/run_route.py` (unchanged) in all three boot modes
with no unknown-dispatch or segment miss, and each run's memory card 1 then
holds one valid save, `BASCUS-94449OMEBENV`. `scripts/routes/test_routes.py`
lists it with the eight earlier routes. `AGENTS.md` lists the route and says
that a new route needs an entry in that list and in `LISTED` (change 2's
round-3 suggestion). This file records change 2's round-3 verdict and commit,
the zone-1 live-input exploration, the static coverage comparison and the
unlock conditions of the later zones, and its observations match the saved
evidence. Baseline: `4c22512`. Out of scope: runner changes, new seeds, overlay
AOT, live campaign play, zones 7 and later, Beetle (Phase 4), CI, packaging.

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

## Phase 3 change 3 observations (`.cache/evidence/phase3-3/`)

- Scratch exploration, HLE OpenBIOS only, in `exploration/` (generators
  `gen_explore.py` and `gen_explore2.py`, routes in `routes/`, runs and contact
  sheets in `out/`; the scratch capture store is not copied). Every run passed
  with no miss.
- LOAD/SAVE (`out/explore-memsave-*`, `explore-memcard-*`, `explore-memcard2-*`,
  `explore-memcard3-*`): the cursor starts on LOAD SLOT1 at every visit and does
  not wrap. The no-wrap evidence is in `explore-memcard`: three Ups from LOAD
  SLOT1 stayed there (`load-slot1`); later, six Ups from LOAD SLOT2 stopped on
  LOAD SLOT1 (`difficulty3-top`), and four Downs then stopped on SAVE SLOT2
  (`difficulty3`). That run went off its script at its load: its second Cross
  landed on the prompt's CANCEL, so it never loaded, and its shots from
  `after-load` to `difficulty3` show LOAD/SAVE where the script expected the
  main menu and OPTION. SAVE SLOT1 and Cross show SAVE COMPLETED within 300
  frames; Cross then returns to the main menu with LOAD/SAVE highlighted. LOAD
  SLOT1 and Cross show CHECKING MEMORY CARD, then the LOAD SAVED DATA? prompt
  with the save's header (Slot 1, PLAY TIME 0: 0: 0, NO PLAY DATA) and OK above
  CANCEL. The prompt's cursor starts on CANCEL. The outcomes establish this:
  Cross on the prompt returned to LOAD/SAVE without loading (`explore-memcard`
  `after-load`, `explore-memcard2`), while Up and then Cross loaded
  (`explore-memcard3`, and the committed route in all three modes). The lit
  entry only supports it (`exploration/prompt-b-x4.png`, `r2/prompt-crops.png`):
  in seven of nine prompt shots CANCEL is lit before Up and OK after it, and in
  two (`explore-memcard3` `load-prompt-b`, the committed HLE OpenBIOS run's
  `load-ok`) neither is, which fits a blinking highlight (hypothesis). In
  `explore-memcard3`, Cross on OK showed OPENING DATA 107 frames after the
  press (`load-1`) and DATA READ COMPLETED at 287 and 576 frames (`load-2`,
  `load-3`); Triangle 606 frames after the press returned to the main menu, as
  in every committed run.
- After a save, memory card 1 holds one save (`mcd_ls.py`): directory checksums
  valid, block 1 in use (state `0x51`), 8192 bytes, name
  `BASCUS-94449OMEBENV`, one block, a full-width Shift-JIS title starting
  【ＶＩＥＷ】. Memory card 2 stays blank. The saved block is byte-identical in
  four runs that saved with different OPTION settings (DIFFICULTY HARD, or
  NORMAL with INFORMATION changed), so the environment data does not record
  those two settings; after loading a save made at HARD, OPTION still showed
  NORMAL (`exploration/memcard3-rows.png`).
- OPTION's cursor starts on CONTROL at the first visit, wraps (six Ups from
  CONTROL reached SELECT BGM), and is remembered between visits. The CONTROL
  SETUPS diagram (Type A, `exploration/control-setups-x3.png`) labels VIPER B.
  and SCAN on the left shoulder buttons, BACK VIEW and STOP on the right, BOOST
  on Triangle and Circle, ATTACK on Square and Cross, DOWN on d-pad up, UP on
  d-pad down and VIEW CHANGE on Select.
- Zone 1 under scripted input (`out/explore-z1-*`, from CAMPAIGN PLAY, 12,000
  frames each): no input scored 0. The attack run (`gen_explore.py`
  `zone1_attack`) held Square for 48 of every 60 frames, with a 6-frame L1 tap
  at the start of each 600-frame block, and scored 3635. The scan runs
  (`gen_explore2.py` `zone1_scan`) held Square the same way and tapped R1, L1,
  L2 or R2 for 6 frames at the start of every 60 frames; they scored 4115,
  3620, 3740 and 3740. Every score was reached within about 2400 frames and did
  not change after (`exploration/scan-compare.png` and the run sheets in
  `out/`). Only the run tapping L1 every 60 frames turned the view (the
  background moves between shots); the attack run's L1 tap every 600 frames did
  not visibly turn it (`g02400` to `g12000` on its sheet). That fits SCAN on L1
  (hypothesis). Input without feedback cleared only the first wave. Hypothesis,
  untested because no run steered: the zone then needs navigation toward its
  objective (the briefing says MODE: SEARCH). Per the probe budget there are no
  further blind variants.
- Static coverage (`static_coverage.py` / `.log`; `psxrecomp-analyze` built
  from the verified tarball tree of `8077e71`, the pinned source, in the scratch
  framework-test build). It finds 1262 functions, all among the 1701 generated
  entry points. Its 219 address-taken targets, its one resolved pointer call
  and the 296 case targets of its 34 recovered jump tables (21 proven, 12
  guarded, 1 scanned) are all generated entry points. 23 direct calls target
  the scene-overlay area (`0x80120A70` to `0x80128F40`): the boot EXE calls
  into the loaded overlay. 160 indirect transfers (155 `jalr`, 5 `jr`) have no
  static target set, so only runtime can find their targets. Static analysis
  gives no new seed.
- Unlocks (reference, unverified: the GameFAQs cheats page and A. Dean's FAQ,
  `gamefaqs.gamespot.com/ps/198233-omega-boost/cheats` and `/faqs/5017`): zones
  U1 to U9 and V5 and the boost levels A to E unlock by completing the game
  under conditions on difficulty, AP (the average zone score over nine zones)
  and continues, and the FAQ's author could not pin the conditions down. 7TH,
  8TH and LAST ZONE are campaign zones. GameFAQs lists two North American saves
  with everything unlocked (a DexDrive save described as "Gamesharked", and a
  PS3 virtual memory card); neither was downloaded. So zones 7 and later, the
  extra zones and the ending need either a campaign play-through or save data.
- Committed route runs (`routes.sh` / `routes.log` with the documented
  commands; outputs in `.cache/routes/memcard/<mode>/`; sheets
  `routes/memcard-<mode>_sheet.png` and `routes/memcard-modes_sheet.png`):
  all three modes pass with matching banners, start frames 64 (HLE OpenBIOS),
  42 (LLE OpenBIOS) and 111 (LLE SCPH-1001), 14 screenshots each, shots 0 to
  16 frames late, no miss at any record and runtime exit 0. Every mode shows
  the same screens (SAVE COMPLETED, the main menu, CHECKING MEMORY CARD, the
  LOAD SAVED DATA? prompt, OPENING DATA, DATA READ COMPLETED, the main menu),
  and each run's memory card 1 then holds the one save described above, while
  memory card 2 stays blank.

## Phase 3 change 3 changes

- `scripts/routes/memcard.json` (new): 48 steps, 9260 frames; the
  `explore-memcard3` flow without the OPTION visits. Written by
  `.cache/evidence/phase3-3/gen_routes.py` (not committed), which reuses the
  change 2 generator's helpers; mode 0644, one step per line.
- `scripts/routes/test_routes.py`: `LISTED` adds `memcard`.
- `AGENTS.md`: the route list adds `memcard.json`, and a new route needs an
  entry in that list and in `LISTED`.
- `.agent/HANDOFF.md`: this rewrite. The Phase 0 to Phase 3 change 1 sections
  are unchanged, and change 2 is condensed.
- Round 2 changes only this file: the LOAD/SAVE and zone-1 observations (review
  round 1), the checks and the review state.

## Phase 3 change 3 checks

- `build-dev` is current with `4c22512`: `cmake --build build-dev --target
  psx-runtime -j6` re-ran only its always-run steps and compiled nothing
  (`build-dev-check.log`).
- Route runs: `routes.sh` with the SCPH-1001 v2.2 dump; the three runs pass
  (see the observations above), and `routes.log` ends with no listener on port
  4370.
- `checks-p3-3.sh` / `.log` (staged tree): the earlier routes, the runner and
  its tests are unchanged from `HEAD`; the Phase 0 to Phase 3 change 1 sections
  of this file equal `HEAD`; the local-path grep finds nothing;
  `check_generated`, `check_boot_exe` and `check_bios_stamps` exit 0; the pins
  equal `framework_pins.txt`, the four submodules are at their pins with no
  changes, and the only ignored file inside them is psxrecomp's
  `overlay_codegen_hash.h`; no tracked file is ignored; all nine routes pass
  `run_route.load_route`; both generators reproduce their routes byte for
  byte; `test_routes.py` passes its 4 tests, and a copy without `memcard.json`
  fails only `test_route_files_match_the_list`; `test_run_route.py` passes its
  15 tests, leaving no fake runtime, temp directory or `__pycache__`; the three
  memcard runs pass with no missing screenshot; nothing listens on ports 4370
  to 4379; `git diff --cached --check` exits 0.
- Round 2, `r2/checks-p3-3-r2.sh` / `.log` (staged tree): the delta from the
  round-1 tree `ee9e132` touches only this file, and every other staged file
  equals round 1; the Phase 0 to Phase 3 change 1 sections still equal `HEAD`;
  no placeholder; the local-path grep finds nothing; the three gates exit 0;
  the pins and submodules are as in round 1; no tracked file is ignored; both
  test files pass, leaving no fake runtime; the facts behind the round-2
  wording reproduce from the saved routes and records (the attack route's 20
  Square+L1 steps, `explore-memcard`'s shots, the load timings of
  `explore-memcard3` and the committed runs); `git diff --cached --check` exits
  0. No route was re-run: no route, script or build input changed.

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
- What the environment save holds: unknown (not DIFFICULTY or INFORMATION).
- Overlay code above `0x80120800` runs in the interpreter; its share of frame
  time and any accuracy effect are unknown. Of the 53 captures in the
  `build-dev` store at change 2, 6 matched no scene `.BIN` (pages at
  `0x80121000`, `0x80122000`, two at `0x80126000` and two at `0x80127000`).
  Where zone code runs, and what those pages hold: unknown.
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
  Its round-3 suggestion (a new route needs entries in the `AGENTS.md` list and
  in `LISTED`) is applied in this change.
- Phase 3 change 3, round 1 (tree `ee9e132`, staged diff `05db29eb…`): NEEDS
  CHANGES, one Low finding: the zone-1 bullet described the attack run as
  Square held with short gaps, but every 600-frame block of that run starts
  with a 6-frame Square+L1 tap, and the bullet did not say that this tap did
  not turn the view. Resolved in the zone-1 bullet. Suggestions adopted: label
  the navigation claim a hypothesis; rest the prompt's CANCEL default on the
  outcomes, with the lit entry as support only (`r2/prompt-crops.png`); name
  `explore-memcard`'s off-script shots and its no-wrap shots; give the load
  timings from the records. The reviewer placed the off-script shots at
  `cursor-option2` to `difficulty3`, but `cursor-option2` to `menu2` show the
  main menu and OPTION as scripted; they start at `after-load`
  (`out/explore-memcard-hle-openbios_sheet.png`).
- Phase 3 change 3, round 2: pending delta re-review.

## Next action

After a PASS: commit and push. Reaching zones 7 and later, the extra zones and
the ending needs a decision by the user: a campaign play-through on the dev
build while misses are collected, a save with the zones unlocked (the user's
own, or one of the GameFAQs saves), or leaving them for now. Independent of
that, one change each:

- static overlay AOT for the scene `.BIN` overlays;
- harvesting any misses with `psxrecomp/tools/collect_game_misses.py` (none so
  far);
- Phase 4, which needs a way to feed the same input to `psx-beetle`.

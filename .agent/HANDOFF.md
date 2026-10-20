# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 3 change 1 (route runner), round 3. Invariant:
`scripts/routes/run_route.py` plays a route in the format of
`psxrecomp/tools/perf_routes/` on the headless dev build through the runtime's
native `input_route_*` commands. A run fails unless the runtime boots in the
requested mode (checked against its boot banner), plays the whole route within
the timeout, reports no unknown-dispatch or segment miss, and exits 0 after
`quit`. Malformed routes, a missing or misplaced `--bios`, a missing binary, a
port that already accepts connections, and a non-empty output directory not
written by the runner are rejected before a runtime starts. The runner sends
commands only to its own runtime, deletes only its own earlier outputs
(including shots numbered 100 and up), records every post-launch failure in
`result.json`, and stops its runtime on SIGTERM or SIGHUP.
`scripts/routes/test_run_route.py` checks this against a fake runtime and
leaves no fake running, even when the runner under test hangs.
`scripts/routes/title_to_zone1.json` reaches Campaign Play zone-1 gameplay in
all three boot modes with zero misses, and each of its shots ends 30 frames
before the next press. `AGENTS.md` documents the route commands and running one
runtime per build at a time; the two deferred Phase 2 wording suggestions are
applied. Baseline: `e58cf21`. Out of scope: new seeds, overlay AOT, menus past
the main menu, play past idling in zone 1, Beetle (Phase 4), CI, packaging.

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

## Phase 3 observations (`.cache/evidence/phase3-1/`)

- Native input routes: the dev runtime plays scripted input itself through
  `input_route_clear`, `input_route_append {frames, buttons}`,
  `input_route_start` (its reply carries `start_frame`), `input_route_status`
  and `input_route_stop`, up to 4096 steps
  (`psxrecomp/runtime/src/debug_server.c:299`, `:8031-8097`). One step frame is
  consumed per runtime frame in the host frame loop
  (`psxrecomp/runtime/src/main.cpp:7524`). `psx-beetle` cannot replay routes at
  this pin: its input getter implements only the finite `set_input` hold
  (`psxrecomp/runtime/src/beetle_debug_server.c:1847-1855`), and it has no
  `input_route_*` command. Upstream's route files are
  `psxrecomp/tools/perf_routes/*.json`, read by `tools/perf_campaign.py`, which
  ignores extra keys. Pad bit names: `psxrecomp/tools/pad_trace.py:38-41`.
- Runtime behavior the runner relies on (`psxrecomp/runtime/src/`): stdout is
  line-buffered (`main.cpp:14218`). The debug server starts at
  `main.cpp:17177` and prints `debug server LISTENING on 127.0.0.1:<port>` or
  `debug server bind(<port>) FAILED` (`debug_server.c:15753-15768`); the boot
  banner `bios_boot=HLE (shell skipped)` or `LLE (real intro)`, then
  `image=<id>`, follows (`main.cpp:17770-17775`). `PSX_BIOS_HLE` and
  `PSX_BIOS_HLE_KEEP_INTRO` override the configuration ('0' or empty off,
  anything else on; `main.cpp:17734-17737`). An explicit `--bios` that is
  missing or fails validation falls back to the bundled OpenBIOS
  (`main.cpp:3009-3031`). `frames` is parsed with `(int)strtol`
  (`debug_server.c:4785-4786`). `dispatch_stats.miss_total` and
  `unknown_dispatch_log.total` read the same counter, `s_unknown_seq`
  (`debug_server.c:12824-12830`; `:3750-3753` for `unknown_dispatch_log`
  without `tail`, as the runner sends it). Error replies carry `error`
  (`send_err`, `debug_server.c:4969`), except the I/O thread's busy reply,
  which carries `err` (`:16180`).
- Two runtimes from one build: in a scratch exploration run for the next
  change, two route runs launched at the same moment from `build-dev`, and one
  runtime exited during startup with "cannot launch with selected mods: cannot
  publish state: No such file or directory" (its log was overwritten by the
  rerun and is not saved). Every launch commits the mod selection to
  `<exe dir>/mods/state.toml` (`main.cpp:15418-15425`, `:16626-16629`) by
  writing `state.toml.tmp` and renaming it (`mod_packages.cpp:2826-2904`); that
  message is raised only there (`:2902`). Derived: concurrent launches from one
  build race on the fixed temporary name. `AGENTS.md` now says to run one
  runtime per build directory at a time.
- Exploration (`exploration/explore_title/<mode>/`, route
  `exploration/explore_title.route.json`, sheets
  `exploration/explore_title_sheet*.png`; a 1500-frame wait, then Start every
  300 frames; all three modes PASS with no miss): Start skips the intro movie
  to the title ("CHECKING MEMORY CARD", then "PUSH START BUTTON"). In the HLE
  run, Start presses 300 and 600 frames after the skip did nothing and the next
  opened the main menu (CAMPAIGN PLAY, TRAINING, ZONE PLAY, REPLAY, LOAD/SAVE,
  RANKING, OPTION). Start then chose CAMPAIGN PLAY, a briefing screen followed,
  then "1ST ZONE" and gameplay; later presses toggled PAUSE. The SCPH-1001 boot
  ran one press interval behind, because its BIOS intro is longer. At the first
  checkpoint (`exploration/explore_boot3.png`), HLE (frame 1594) showed an
  orange glyph field, LLE OpenBIOS (frame 1544) a flat gray frame, and
  SCPH-1001 (frame 1609) the "A Polyphony Digital Production" card.
- Route drafts (scratch runs; their outputs were overwritten and are not
  saved): without a press on the briefing screen, the route stopped there and
  its last screenshot was a black transition frame. A menu press 1200 frames
  after the skip still worked, but the title was already dimming, so the
  committed route presses at 1050.
- Earlier runs with the committed route's frames and buttons
  (`exploration/title_to_zone1/`, `exploration/title_to_zone1-rep/`; one shot
  was named `zone1-intro` instead of `zone1-start`), two per mode: all PASS,
  start frames 78, 35, 104 and 64, 34, 104 (HLE OpenBIOS, LLE OpenBIOS,
  LLE SCPH-1001).
- Round-1 runner, documented commands (`round1-routes/<mode>/`,
  `route-<mode>.log`, `title_to_zone1_sheet.png`): start frames 70, 33, 112;
  PASS.
- Round-2 runner (sha256 `8c24dbfe753c…`), documented commands as written
  (`r2/route-<mode>.log`, `r2/title_to_zone1_sheet.png`; outputs moved in
  round 3 from `.cache/routes/title-to-zone1/<mode>/` to `r2/routes/<mode>/`):
  banners HLE/OPENBIOS, LLE/OPENBIOS and LLE/SCPH-1001; start frames 39, 22,
  103; 0 unknown-dispatch and segment misses at every checkpoint; runtime exit
  0; PASS. Screens in every mode: intro movie, title, main menu, zone-1
  gameplay at both zone checkpoints. The briefing shots came 8, 9 and 8 frames
  late (`r3/shot_lags.log`), after the 6-frame Start press that leaves the
  briefing had begun, so the frame they show, called the briefing's loading
  screen in round 2, is more likely the transition out of the briefing.
- Round-3 runner (sha256 `65cf0142a2c3…`) and 14-step route (sha256
  `0ce2e08074bb…`), documented commands as written (`r3/route-<mode>.log`,
  `r3/title_to_zone1_sheet.png`; outputs in
  `.cache/routes/title-to-zone1/<mode>/`): banners HLE/OPENBIOS, LLE/OPENBIOS
  and LLE/SCPH-1001; start frames 40, 38, 86; 0 misses at every checkpoint;
  runtime exit 0; PASS. Every mode shows the intro movie, the title, the main
  menu, the briefing itself (green wireframe globe, "MODE: SEARCH") and zone-1
  gameplay at both zone checkpoints. The briefing shots came 0, 1 and 1 frames
  late, 29 to 30 frames before the press.
- Start frames in the saved runs range from 22 to 112, so the route relies on
  slack around each press.
- Shot lag (the frame read before the screenshot minus the step's end): 0 to
  14 frames over the saved route runs of rounds 1 to 3 (`r3/shot_lags.log`),
  up to 15 in the next change's exploration runs
  (`.cache/evidence/phase3-2/exploration/`), and 16 for a first shot right
  after boot in the reviewer's round-2 runs.
- The runner does not set `PSX_OVERLAY_CAPTURES`; it passes the caller's value
  through, so by default route runs add to the capture store beside the
  executable (`build-dev/overlay_captures.json`, ignored).
- Overlays (`r2/capture_match.py`, `r2/capture_match.log`,
  `r2/capture_unmatched.log`): of the 32 captures in
  `build-dev/overlay_captures.json.d/`, 28 equal a disc `.BIN` at offset
  `load_addr - 0x80120000`: LOGO (`24F6240482D747F4.json` at 0,
  `C1772753D9719E05.json` at `0x1000`), MOVIE, TITLE and BRI1
  (`2B5FCA8B59AA8E4D.json` at `0x1000`). Two more equal MOVIE.BIN except 3
  words at `0x80122D20`. The pages at `0x80126000` and `0x80127000` differ from
  every `.BIN` in thousands of bytes, and no capture is a zone file, although
  the route reached zone 1. Hypothesis: every scene `.BIN` loads whole at
  `0x80120000`; candidate loader `func_80075AB4`, which stores `0x80120000` to
  two pointers (`generated/SCUS_944.49_full_28.c`).

## Phase 3 changes

- `scripts/routes/run_route.py` (new):
  - validates the route (name and shot names ASCII letters, digits, '-' or
    '_'; 1 to 4096 steps; `frames` 1 to 2^31−1; `buttons` 0 to 65535);
  - validates the arguments: `--bios` must name a file and is accepted only for
    SCPH-1001; the binary, `game.toml` and the disc must exist; the port must
    not answer;
  - clears only its own earlier outputs in `.cache/routes/<name>/<mode>/`
    (`cwd/`, `memcards/`, `runtime.log`, `result.json`, and shot files named
    with two or more digits, a dash and the shot name);
  - starts `build-dev/Omega_Thrust` headless from `cwd/`, removing `APPIMAGE`
    and `PSX_BIOS_HLE_KEEP_INTRO`, setting `PSX_BIOS_HLE` for the mode and
    passing `--bios` for SCPH-1001;
  - waits for its own LISTENING line, the boot banner and a `frame` reply,
    and fails if the banner does not match the mode;
  - appends and starts the route, and takes each shot together with the frame
    and the miss counters;
  - sends `quit` to its own server, or kills the runtime;
  - writes `result.json`, carrying a `runner` marker, at the start and the end;
  - exits 1 on any failure.
- `scripts/routes/test_run_route.py` (new): 15 stdlib `unittest` tests that run
  the runner against a fake runtime written to a temporary directory. Each
  fake appends its PID to a list that cleanup kills, and exits when its parent
  (the runner) goes away or after 120 s.
- `scripts/routes/title_to_zone1.json` (new): the route above, 14 steps and
  7674 frames; each shot step ends 30 neutral frames before the next press.
- `AGENTS.md`: a Routes section (format, failure conditions, the 30-frame shot
  margin, output reuse, a refused run leaving an older `result.json` in place,
  routes one at a time) and, under Running, one runtime per build directory at
  a time. The codegen-hash paragraph now cites
  `psxrecomp/runtime/runtime.cmake:1778` by its project-relative path and says
  the header is written whenever it is missing or stale (the two deferred
  Phase 2 suggestions).
- This handoff: Phase 2 condensed (full record in `e58cf21`).

## Phase 3 checks

- Round 1 (runner sha256 `e41b6985863f…`): `validate_runner.sh` /
  `validate_runner.log`, nine malformed routes and SCPH-1001 without `--bios`
  exit 1 before any runtime starts; the three documented route commands PASS;
  staged-tree checks in `checks-p3-1.sh` / `checks-p3-1.log`.
- Round 2, on the round-2 runner:
  - `python3 -B scripts/routes/test_run_route.py -v` (`r2/tests-new.log`): 15
    tests OK in 10.6 s; no temporary directory, fake process or `__pycache__`
    left by this run. Runs of the same tests against the round-1 runner did
    leak fake runtimes: the reviewer found two still alive, which were killed
    in round 3 (`r3/leaked-fakes.log`).
  - The same test file against the round-1 runner (`r2/tests-old-runner.log`):
    all 15 tests fail (17 failures and 4 errors, counting subtests). Twelve
    reproduce a review finding: route names that escape the output root or are
    not strings, frames above 2^31−1, deleted user files, unchecked `--bios`,
    an inherited `PSX_BIOS_HLE=0` and a mismatched banner reported as PASS, a
    busy port, a foreign server driven, a hang past `--timeout` (stopped by the
    test's 60 s limit), tracebacks on an error status reply and a missing
    binary, and the fake runtime left running after SIGTERM. The other three
    fail only on new output (`status` in `result.json`, the miss message, the
    screenshot note).
  - `validate_runner.sh` on the round-2 runner (`r2/validate_runner.log`): the
    same cases exit 1 before any runtime starts; no `__pycache__`.
  - Real-runtime checks (`r2/real_checks.sh` / `r2/real_checks.log`; outputs
    and captures in scratch): a 512 KiB zero-filled `--bios` booted OpenBIOS
    and failed on the banner before the route started; an inherited
    `PSX_BIOS_HLE=0 PSX_BIOS_HLE_KEEP_INTRO=1` with `--mode hle-openbios`
    booted HLE and passed, with its "display disabled" screenshot recorded; a
    second runner refused port 4370 while a first run held it, without creating
    its output directory, and the first run passed.
  - The three documented route commands: PASS (above).
  - Staged-tree checks, including `git status --short` before staging:
    `r2/checks-p3-1-r2.sh` / `r2/checks-p3-1-r2.log`.
- Round 3:
  - `python3 -B scripts/routes/test_run_route.py -v` (`r3/tests-new.log`): 15
    tests OK in 10.7 s; no temporary directory, fake process or `__pycache__`
    left.
  - Harness and cleanup regressions (`r3/harness_regression.sh` /
    `r3/harness_regression.log`, per-suite logs beside it; scratch copies of
    the earlier runners taken from git): the round-2 tests against the round-1
    runner left one fake runtime running, reproducing the finding; the round-3
    tests against the same runner left none, with the same 17 failures and 4
    errors; the round-3 tests against the round-2 runner fail only the reuse
    test, because `100-stale.png` survives.
  - Fake watchdog (`r3/watchdog_check.sh` / `r3/watchdog_check.log`, and
    `r3/harness_regression.log`): with the parent killed after the fake
    printed its LISTENING line, the fake exited within 0.22 s in three of
    three trials; with the parent alive, it exited after 121 s. A first
    attempt killed the parent before the fake had read its parent PID; that
    fake was still alive 5 s later and gone by the next check, the case the
    120 s limit covers.
  - Route input (`r3/route_stream_check.py` / `r3/route_stream_check.log`):
    the 14-step route's per-frame button stream equals the 10-step round-2
    route's (7674 frames). The runtime consumes one frame of one step per
    frame (`debug_server.c:16377-16390`), so splitting a step leaves the input
    unchanged. The first four shot steps end 30 frames before the next change.
  - The three documented route commands: PASS (above).
  - Not covered by the suite: the kill after an unanswered `quit` (30 s). The
    reviewer checked it on the real runtime in round 2 by stopping the
    runtime with SIGSTOP.
  - Staged-tree checks, including `git status --short` before staging:
    `r3/checks-p3-1-r3.sh` / `r3/checks-p3-1-r3.log`. The round-2 checks
    script's leftover-fake count could never match (its pattern required the
    command line to end in `fake_runtime`, but the fake's arguments follow
    it); round 3 counts python processes whose arguments contain
    `fake_runtime`.

## Hypotheses and unknowns

- The screens between the Polyphony card and the intro movie differ by boot
  mode at every checkpoint so far. At frame 1800 (Phase 2,
  `git show e58cf21:.agent/HANDOFF.md`), HLE showed the orange glyph field,
  LLE OpenBIOS orange text "Alpha core dumped ....", and SCPH-1001 a flat gray
  letterboxed frame; at the first exploration checkpoint, HLE showed the glyph
  field and LLE OpenBIOS a flat gray frame. The boots take different lengths,
  so equal frame numbers are not the same point of the intro. Whether these
  screens are correct: unknown until the Beetle comparison.
- Whether the eight emitted fallthroughs are faithful: unknown.
- Untested by committed routes: the main-menu entries other than CAMPAIGN PLAY,
  memory-card saves, zones after zone 1, the ending and credits. Whether
  scripted input can clear a zone: unknown.
- Overlay code above `0x80120800` runs in the interpreter; its share of frame
  time and any accuracy effect are unknown. What the two unmatched capture
  pages hold, and where the zone code runs: unknown.
- How Phase 4 will feed route input to `psx-beetle`, which has no
  `input_route_*` command: unknown.
- recomp-ui `864f778`: the launcher dashboard works; starting the game from
  PLAY has not been exercised.

## Review and commit state

- Phase 1: round 2 PASS on tree `b5ef902`; commit `6ad5c9e`.
- Phase 2: round 3 PASS on tree `8ab2284`; commit `e58cf21`, pushed to the
  private `origin/master`. Its two deferred nonblocking suggestions are applied
  in this change.
- Phase 3 change 1, round 1 (tree `c39a0cdf`): NEEDS CHANGES, two Medium and
  four Low findings, resolved as follows.
  - Medium 1, a PASS could name a mode that never ran: the boot banner must
    match the mode; `PSX_BIOS_HLE` is set in every mode and
    `PSX_BIOS_HLE_KEEP_INTRO` removed; `--bios` must name a file.
  - Medium 2, unguarded recursive delete of `--out` and the route `name`: a
    non-empty directory without the runner's `result.json` is refused, only
    the runner's outputs are deleted, and `name` is validated.
  - Low 3, the timeout skipped while queries failed and SIGTERM orphaned the
    runtime: the deadline is checked on every poll; SIGTERM and SIGHUP raise
    `SystemExit`, and cleanup stops the runtime.
  - Low 4, the runner drove whatever answered on the port: a busy port is
    refused, commands start only after the runner's own LISTENING line, and
    `quit` goes only to its own server.
  - Low 5, no upper bound on `frames`, a crash on `ok:false` status replies,
    tracebacks: `frames` is capped at 2^31−1, error replies are recorded,
    post-launch failures go into `result.json`, and a missing binary is
    reported before launch.
  - Low 6, handoff claims: the Beetle claim is corrected, the intro-screen
    claim restated from the Phase 2 record, the exploration and earlier runs
    saved under `exploration/`, the route drafts labelled unsaved, the
    start-frame range recomputed from saved runs, and `git status` before
    staging saved in the checks log.
  - All eight nonblocking suggestions adopted: the "one step frame per runtime
    frame" wording; `<name>` explained; the miss check reads the two distinct
    counters; the frame read before each screenshot; failed screenshots
    documented; "does not set" for `PSX_OVERLAY_CAPTURES`; capture files cited;
    `--bios` rejected in the OpenBIOS modes.
- Phase 3 change 1, round 2 (tree `24d16254`): NEEDS CHANGES, one Low finding,
  resolved as follows. All six round-1 findings were confirmed resolved.
  - Low, the test suite could leave fake runtimes running when the runner
    under test hangs (each fake overwrote one PID file, and the test's 60 s
    timeout killed only the runner): each fake appends its PID and cleanup
    kills them all; each fake exits when its parent goes away or after 120 s;
    the two leaked fakes were killed (`r3/leaked-fakes.log`).
  - Suggestions adopted: shot cleanup matches two or more digits (1); the
    late-shot count dropped from `AGENTS.md` in favour of a 30-frame shot
    margin, which the route now follows (2, 3); the pass test checks nominal
    frames against values derived from its own route (4); the refused-run note
    (6); the handoff nits (7); routes one at a time (9).
  - Documented instead of changed: the suite does not cover the kill after an
    unanswered `quit` (5).
  - Deferred: ignoring SIGINT during cleanup (8). A test needs a fake that
    ignores `quit` and a 30 s wait. Until then a second Ctrl-C during cleanup
    can leave the runtime running, and the next run refuses the busy port.
- Phase 3 change 1, round 3: pending delta re-review.

## Next action

After a PASS: commit and push. Next Phase 3 changes, one per commit:

- routes through the other main-menu entries (OPTION, LOAD/SAVE with a memory
  card, TRAINING, ZONE PLAY, REPLAY, RANKING) and through REPLAY →
  DEMONSTRATION, which plays recorded run-throughs of zones 1 to 6 without
  input. Scratch exploration for that change, HLE only, with no miss
  (`.cache/evidence/phase3-2/exploration/`): zone 1's recording reached the
  zone-complete screen; zones 2 and 3 played for about 185 s of their listed
  3:48 and 4:29 (`demo_durations.log` there); zones 7 and later show DISABLE;
- a zone-1 route with real input, to learn whether scripted play can clear a
  zone;
- harvesting any misses with `psxrecomp/tools/collect_game_misses.py`;
- static overlay AOT for the scene `.BIN` overlays, as its own change.

Phase 4 needs a way to feed the same input to `psx-beetle`.

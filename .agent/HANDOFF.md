# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison.

Current iteration, Phase 4 change 2 (bookkeeping: the first watched play
session and what it turned up), round 2. Invariant: this file records Phase 4
change 1's round-3 PASS and commit `6d0a173`; the first watched play session,
zones 1 to 4 of CAMPAIGN PLAY and an environment save to card 1 from the
menus, with no unknown dispatch or segment miss; the cause of the vertical
line on the title screen (psxrecomp's bilinear filter wraps neighbour texels
across 256-texel page edges; derived) and of the blurred UI (the filter
applies to every textured prim), both framework behaviour, reported upstream
as psxrecomp #719 and #720, with Nearest filtering as the user's choice for
now; the writer of the SCPH-1001 exception-stub difference (the runtime clears
RAM 0x00-0x0F when the game starts), reported as #721; and the launcher state
that the session left in `build-dev/` and in the tracked `game.toml`, now
moved to a play copy of the build, so that headless runs from `build-dev/`
behave as before the session. `AGENTS.md` says what the launcher writes, on
PLAY and on Quit, and that it runs only from a copy outside `build-dev/` with
its own `game.toml`. Baseline: `6d0a173`. Out of scope: code, route, runner,
driver, framework and submodule changes; renderer fixes (upstream); the
3D-only filter enhancement (declined for now); further play sessions; CI,
packaging.

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

## Phase 3 change 5 (commit `2a3fe3a`)

`scripts/routes/run_route.py` accepts the route key `card1_sha256`: such a
route runs only with `--card1` naming a readable 131,072-byte image with that
sha256 (size, read and hash checked before launch, one-line refusals), and the
runner copies the image into the run's `memcards/card1.mcd`. Thirteen routes,
`demo_zone7.json`, `demo_zone8.json`, `demo_zone_last.json`,
`demo_zone_u1.json` to `demo_zone_u9.json` and `demo_zone_v5.json`, load the
user's unlocked save with LOAD SLOT1 and play each zone's DEMONSTRATION replay
to its results screen. The save is GameFAQs save 20242 for Omega Boost, "All
Zones Unlocked (Gamesharked)", a North American DexDrive file the user
downloaded; its raw card image (`.cache/saves/all-zones.mcd`, ignored, sha256
`e3b71c252ce2…`) opens all 19 DEMONSTRATION entries and ZONE PLAY zones.
Against the game's own save it sets 19 one-byte flags at 0x200 to 0x212 and 13
at 0x214 to 0x220 of the save block (hypothesis: zone unlocks, then boost
levels). All 66 runs (22 routes in three modes) passed with no miss, and each
new zone shows the same CLEAR TIME in every mode: 7TH 4:15.50, 8TH 1:26.60,
LAST 4:39.06, U1 2:29.66, U2 2:04.76, U3 0:48.23, U4 1:39.36, U5 0:49.56, U6
0:56.43, U7 1:28.60, U8 0:59.86, U9 1:47.53, V5 0:44.33. After a run, card 1
differs from the image only in its write-test frame (frame 63, offset 0x1F80;
the writer was not traced); a card the runtime formats keeps frame 63 as a
copy of frame 0 unless the run rewrites it
(`psxrecomp/runtime/src/memcard.c:45-84`). Since review round 2, every
argument subtest of the runner tests starts from a clean state, so a mutation
fails only the subtests it affects. Review: round 1 NEEDS CHANGES (three Low: a
preload test that could not fail, two misattributed change 4 review rounds in
this file, a traceback on an unreadable `--card1`), round 2 PASS on tree
`91d6447` with no findings. The full record is in
`git show 2a3fe3a:.agent/HANDOFF.md`.

## Spike: replays and the campaign script (scratch, harness-assisted)

The user chose a time-boxed scratch spike for what scripted routes cannot
reach (`.cache/evidence/spike-replay/`). Each of `REPLAY/REPLAY00.DAT` to
`REPLAY18.DAT` (23,404 bytes) holds one zone's recorded input, an 8-byte input
state per 30 fps game frame, run-length coded (`decode_replay.py`,
`decode.log`); its frame count, difficulty and level match the zone's
DEMONSTRATION entry. Every recording steers with the analog stick, off centre
in 82 to 99% of its frames (`stick_use.py` / `.log`), and routes carry only
the 16 button bits. CAMPAIGN PLAY's loop (0x8002F814) walks a 17-step script
at 0x8001232C: two briefings, nine zones, four between-zone movies (INTER1 to
INTER4), END_ALL and the staff credits. Rewriting the script pointer and step
that its callees save on the stack (debug-server memory writes;
`spike_ending.py`, `spike_tour.py`) skipped the zones: the four movies,
END_ALL, the credits and the closing copyright screen ran with no miss
(`runs/ending/`, `runs/tour/`). After a Start press on the copyright screen,
the game entered state 7, whose handler (`func_8002DC48`) calls the replay
player's step (0x80077228), and the function at 0x800571B8 called the scene
entry stored when BRI1 started (0x80120EAC) while other data filled the
overlay area there (a reserved opcode), so the runtime halted on an unknown
dispatch
(`runs/tour/postmortem.log`). The writes skipped every zone step, so this may
be an artifact of the harness (hypothesis); psx-beetle has no memory-write
command, so only genuine play to the ending can settle it.

## Phase 4 change 1 observations (`.cache/evidence/phase4-1/`)

- The build (`build_beetle.log`, 45 s with `JOBS=8`): `scripts/build_beetle.sh`
  archived psxrecomp `8077e71`, recomp-net `e2491d2` and retcomm-rbengine
  `2a03e73`, checked out beetle-psx-libretro `5759277be500…`, applied the
  seven patches and built a psx-beetle identical to the prototype build's
  (sha256 `63d0e568a6e5…`, `prototype-binary.sha256`). Afterwards the
  psxrecomp submodule still lists only its ignored `overlay_codegen_hash.h`.
- psx-beetle at the pin (source): each pass of its main loop reads the debug
  connection, takes the pad override, then runs one frame
  (`psxrecomp/runtime/src/beetle_main.cpp:226-233`). The server holds one
  client and handles every complete request line it has read
  (`beetle_debug_server.c:1785-1837`); `press` holds a pad word for exactly
  `frames` frames from the frame about to run (`:380-387`, `:1847-1855`), and
  `ping` reports the frame count (`:300-305`). It has no `input_route_*`,
  memory-write or quit command (the table at `:1652-1719`), sets no
  `TCP_NODELAY` (`:1755`) and sends each reply on its own (`send_raw`,
  `:222`). Without `scph5501.bin` in the BIOS path's directory, Beetle boots
  its own OpenBIOS build (`psxrecomp/docs/beetle-macos.md`, section 4); an
  image with another SHA-1 under that name is used, and the log reports
  "Firmware found but has invalid SHA1" with the image's SHA-1.
- psx-beetle's memory cards (the patched tree in
  `.cache/beetle/psxrecomp/beetle-psx`): the host selects the mednafen card
  method with save directory `.` (`beetle_libretro.cpp:419`, `:431`), so
  Beetle reads `./<disc base name>.<n>.mcr` when the game loads, here
  `Omega Boost (USA).0.mcr` and `.1.mcr` (`libretro.cpp:2190-2208`; the name
  from `MDFN_MakeFName`, `:5440-5468`, and the content path, `:4416`), and
  keeps its own card if the file is missing
  (`mednafen/psx/frontio.cpp:968-996`). It saves a card the game changed to
  the same file about two emulated seconds after the game's last write to it
  (checked at the end of each emulated frame, `libretro.cpp:4855-4897`), and
  again on exit if the card changed since (`retro_unload_game`, `:4590-4596`;
  `CloseGame`, `:2546-2567`); `SaveMemcard` writes only a card changed since
  its last save (`frontio.cpp:1009-1029`). SIGTERM reaches the exit path as
  SDL's quit event (`beetle_main.cpp:212-221`). The second batch's card files
  changed during the runs (file times against `beetle_routes.log`, now in
  `batch2/`): `memcard`'s two cards 13 s and 19 s into its 26 s runs,
  `demo_zone1`'s two cards 13 s into 49 s, and `demo_zone7`'s card 1 (LLE
  SCPH-1001) 11 s into 89 s, while its card 2 kept the time the driver wrote
  it. `beetle_libretro.cpp:543-567` separately checks `dummy.0.mcr` and
  `dummy.1.mcr` and only logs what it finds; Beetle does not load them.
- The scratch prototype (`prototype/`: its driver, batch script and log, and
  each run's `result.json` and `beetle.log`) opened a new connection per
  request. Beetle notices a closed connection only on its next loop pass, so
  the prototype saw every other frame: in its batch (LLE OpenBIOS,
  `prototype/run_demos-openbios.log`), four replays failed with every press
  flagged one frame late (zones 1 and 2, U2 and U7: 11, 12, 28 and 33
  presses), and the other 15 passed. The committed driver keeps one
  connection.
- A second hazard, found by the driver's tests: after a two-command batch, the
  driver's view of the frame count jumped about 13 frames at the fake's 300
  fps (about 40 ms). The kernel held the second reply until the first was
  acknowledged (Nagle), and the driver delayed that acknowledgement. The
  driver now acknowledges at once (`TCP_QUICKACK` before every read).
- The driver's blank card equals byte for byte the card psx-runtime formats
  for a missing slot (sha256 `7706c7d43eda…`, compared with change 5's
  `demo-zone7` card 2).
- The first full batch (`batch1/`, 12:16 to 12:56) ran the driver as it then
  was: it wrote the cards as `dummy.0.mcr` and `dummy.1.mcr`, the names in
  psx-beetle's log check, and required that check's "OK" lines. Beetle never
  loaded them; every run's `cwd/` also held Beetle's own
  `Omega Boost (USA).0.mcr` and `.1.mcr`, the cards it saved. The 26
  unlocked-save runs never had the save: LOAD SLOT1 reported "THERE IS NO
  OMEGA BOOST DATA PRESENT", later presses landed on other screens (a "Slot 2
  SAVE COMPLETED", the ZONE PLAY list) and no replay ran
  (`batch1/diag/zone7-beetle-load_sheet.png`). The driver passed them, since
  it checks timing, not screens; the results comparison found no results
  screen on Beetle in any of the 13 replays (`batch1/compare_results.log`).
  The other 18 runs started from Beetle's own formatted cards; the second
  batch supersedes them. The driver now writes Beetle's names and fails a run
  if psx-beetle writes any other file in `cwd/`, which would have failed all
  44 first-batch runs. The check sees only cards Beetle saves: in the
  unlocked-save routes the game never writes card 2, so there it covers card
  1 only; both names come from one expression.
- Also in the first batch, `demo_zone_u6` in LLE OpenBIOS failed: its first
  event, the intro shot, landed on frame 3931 instead of 3930
  (`batch1/failed/`). The driver answers each ping within the time Beetle takes
  to run one frame, about 3 ms unpaced (the 17,156-frame route took 49 s,
  `batch1/rerun.log`), so a longer host delay makes an event land late and
  fails the run, as designed. The same command then passed. `beetle_routes.sh`
  now re-runs such a run once and keeps the failed attempt in `failed/`.
- Runs (`beetle_routes.sh`): the second batch (13:17 to 14:00, with the
  round-1 driver; its log, hash files, outputs and per-run logs are now in
  `batch2/`) passed all 22 routes in both modes on the first try (44 runs, no
  retry). Every press and shot landed on its route frame, no screenshot is
  missing, psx-beetle exited 0 every time, and the save image, the psx-beetle
  binary and the driver were unchanged (`inputs-before.sha256`,
  `inputs-after.sha256`); `beetle_summary.log` counts all 44, and no listener
  was left. Each run's `cwd/` held only Beetle's two card files. The round-2
  driver differs from round 1's only in its docstring. The third batch, with
  it (15:03 to 15:46; `beetle_routes.log`, the hash files and `routes/` here,
  outputs in `.cache/beetle-routes/`), passed the same way: 44 runs, no
  retry, inputs unchanged, no listener left. Its screenshots, cards and
  `result.json` files, and even its `beetle.log` files, equal the second
  batch's byte for byte (`r2/batch_compare.py` / `.log`), and the comparison
  logs below, regenerated from it, equal their copies in `batch2/`.
- Results screens (`compare_results.py` / `.log`, `results-<mode>_sheet.png`):
  by the comparison's rule, 33 of the 38 replay-mode pairs match (17 of 19 in
  LLE OpenBIOS, 16 in SCPH-1001). In them no compared pixel of the banner,
  CLEAR TIME, DESTROY RATIO or PILOT ABILITY rows differs, and those rows are
  fully compared except in U8 (both modes: 5, 35 and 23 pixels left out) and
  zone 3 in SCPH-1001 (42 of 832 in PILOT ABILITY), within the rule's limit of
  one in five. The controls, each replay's psx-runtime screens against the
  next replay's Beetle screens, differ in 423 to 2,591 pixels. The other
  five pairs are zone 7 in both modes, U1 in both, and LAST in SCPH-1001;
  `diag_rows.py` / `.log` lists their differing pixels. In zone 7 they are 27
  and 29 background pixels at x 134 to 199, around "100%" and "RANK", all
  dark in psx-runtime's first results shot. The white light sweep, whose grey
  248 passes the rule's text test, covers 49 of the 56 by psx-runtime's
  second results shot and Beetle's third; the other seven turn grey at other
  shots, except (191,101) in SCPH-1001, which never does on Beetle (its third
  shot shows (248,248,120) there; `r2/zone7-sweep-crops.png`). The small
  "(43/43)" and "(100pts)" digits, from x 230, have no differing pixel. In
  LAST they are four grey (160,160,160) pixels of the mech model behind the
  text. U1's final results screen has one results shot on Beetle; on it the
  banner, CLEAR TIME, DESTROY RATIO and PILOT ABILITY rows have no differing
  text pixel (726 to 890 per row), and only SCORE BONUS differs (160 of 306
  pixels). Viewed at 2x (`diag2/`), the text is the same on both:
  zone 7 CLEAR TIME 4:15.50 (96pts), DESTROY RATIO 100% (43/43), PILOT
  ABILITY RANK S (96pts); LAST 4:39.06 (92pts), 100% (3/3), RANK S (92pts),
  SCORE BONUS 77632; U1 2:29.66 (40pts), 94% (189/201), RANK C (37pts).
  Beetle never reaches its first results shot before psx-runtime does; at the
  final results screen it is one 300-frame shot later in zones 3, 4, 8, U1,
  U7 and U9 in both modes, and U3 in LLE OpenBIOS.
- SCORE BONUS (`r3/score_bonus.py` / `.log`, `r3/score-bonus-<mode>_sheet.png`:
  2x crops of the row from each side's last two results shots, read by eye):
  the rule finds no differing pixel in 19 of the 38 pairs, and in five more
  both sides' last results shots show the same figure: zone 7 in both modes
  (34760, under the light sweep), U8 in both (40896; the differing pixels are
  background graphics at x 139 to 190, at the figure's left end) and U2 in
  SCPH-1001 (22276; four background pixels at x 100 to 159). That is 24
  pairs; that the shared figure is the final tally is derived (Beetle reaches
  the screen later yet shows the same figure). In the other 14 (12 of the
  matching 33, and U1's final screen in both modes) the figures differ, and
  in each the lower one is Beetle's at the same route frame or the one from
  the earlier shot, as a tally still counting would show (derived): for
  example zone 3 23872 against 19776 at t16200, U1 12896 against 04000.
- U1 also shows a results screen in mid-replay, which psx-runtime's t04800
  shot catches and Beetle draws between the committed route's shots
  (`r2/u1_fine.py`, `r2/u1_fine.sh` / `.log`, `r2/u1_mid.py` / `.log`,
  `r2/u1-mid_sheet.png`). A scratch copy of the route, with its neutral shot
  steps from t03600 to t06000 split into 100-frame shots (the same input),
  passes the rule's results-screen test on psx-runtime from t04800 to t05200
  in both modes and on Beetle from t05000 (LLE OpenBIOS) or t04900
  (SCPH-1001) to t05300; Beetle's LLE OpenBIOS t04900 shot already shows the
  COMPLETED banner, with only "CL" of the CLEAR TIME label drawn. By the
  comparison's rule its banner, CLEAR TIME, DESTROY RATIO and PILOT ABILITY
  rows match (no differing pixel, none left out). SCORE BONUS reads 12896 on
  both sides in both modes (psx-runtime holds it at t05100 and t05200); in
  SCPH-1001 the rule finds one differing pixel, a grey (160,160,160) dot on
  Beetle's side at (178,155), left of the figure, and every digit pixel
  matches (`r3/score_bonus.log`). Its text equals the final screen's.
  Beetle's 19 shots up to t03600 equal the batch's byte for byte.
- The other routes' screens (`compare_screens.py` / `.log`,
  `screens-<route>-<mode>_sheet.png`): `title_to_zone1`, `menus` and
  `memcard` show the same screens in the same order on both emulators
  (viewed). The title, menu and memory card screens have the same RGB on
  90.2% to 99.9% of the display area (animated backgrounds make up the rest),
  the two zone-1 gameplay shots on 73% to 74%; the intro movie and the
  briefing are not measured, as their frame sizes differ.
- Memory cards at the end of each route (`card_compare.py` / `.log`): in LLE
  OpenBIOS, both of Beetle's cards equal psx-runtime's byte for byte after
  all 22 routes, including `memcard`'s saved block (card 1 sha256
  `42dd8d89acd1…`, as in Phase 3 change 3) and the rewritten write-test frame
  (frame 63) of blank cards. So that write comes from code both emulators
  run, the game or the BIOS, not from psx-runtime (derived). In SCPH-1001
  mode, every card the game rewrote differs in frame 63 only, in seven of
  bytes 4 to 11: Beetle has `80 0c 5a 27 08 00 40 03`, psx-runtime zeros
  (byte 9 is zero on both; card 2 of the unlocked-save routes, which the game
  leaves alone, is identical). Those bytes, `addiu k0,k0,0x0c80` and `jr k0`,
  are words 2 and 3 of the BIOS's exception-vector stub (`lui k0,0; addiu
  k0,k0,0x0c80; jr k0; nop`, at 0xBFC10A0C in the SCPH-1001 image), and the
  unlocked save's own frame 63 has the same bytes (Phase 3 change 5).
- Exception vectors (`vector_probe.py` / `.log`, frame 1200 or later of a
  boot with no input): RAM at 0x80000080 holds that stub in both emulators.
  At 0x80000000, Beetle holds `03000000` followed by stub words 2 to 4, and
  psx-runtime `11111111` followed by zeros; in OpenBIOS mode both vectors
  match. Frame 63 equals the first 16 bytes of RAM at address 0 with
  0x11111111 over its first word, which fits the write test writing frame 63
  from address 0 (derived from equal bytes, not traced). Hypothesis:
  psx-runtime's recompiled SCPH-1001 boot does not leave the BIOS's stub copy
  at the UTLB vector (0x80000000). That is a framework accuracy difference;
  no game-visible effect has been seen, and a fix is a framework change.
- Intro (`intro/intro.sh` / `intro.log`; `intro/intro_grid.py` / `.log`,
  `intro/grid-*_sheet.png`): sampled every 120 frames for 3,960 frames with
  no input, all five runs (psx-runtime HLE, LLE OpenBIOS and SCPH-1001;
  Beetle OpenBIOS and SCPH-1001) show the same order: the BIOS screens (the
  OpenBIOS logo, or the SCE, SONY and PlayStation screens), the SCEA
  "Presents" card, the Polyphony card, the orange text line (seen earlier as
  "Alpha core dumped ...."), the orange glyph field, then the movie with its
  scenes in the same order. Only the frames differ: the glyph field first
  appears in the samples at frame 1624 (psx-runtime HLE), 1959 (psx-runtime
  LLE OpenBIOS), 2100 (Beetle OpenBIOS), 2137 (psx-runtime SCPH-1001) and
  2580 (Beetle SCPH-1001). psx-runtime saved no screenshot at some boot
  samples ("display disabled"). Beetle reaches each screen later than
  psx-runtime in the same BIOS mode, as with the results screens; why is not
  established (hypothesis: Beetle's CD timing).

## Phase 4 change 1 changes

- `scripts/build_beetle.sh` (new): the build in the invariant, from the
  prototype script (`.cache/evidence/phase4/beetle_build.sh`) with the
  beetle-psx-libretro commit in full, the framework archived from the
  gitlinks that HEAD records, and `pipefail`.
- `scripts/routes/beetle_route.py` (new): the driver in the invariant. It
  imports `load_route`, `port_answers` and shared constants from
  `run_route.py`, which is unchanged, and sets `sys.dont_write_bytecode`, so
  the import leaves no `__pycache__` even without `-B`. Since the first batch
  it writes the cards under Beetle's names and fails a run if psx-beetle
  writes any other file in `cwd/`.
- `scripts/routes/test_beetle_route.py` (new): 15 tests against a fake
  psx-beetle whose frame loop follows Beetle's order (read requests, take the
  override, run the frame), whose replies and log lines copy Beetle's, and
  whose cards follow Beetle's (read from `<disc name>.<n>.mcr` at startup;
  card 1 is saved, though only on exit). They cover presses and shots on
  their exact frames (including a shot and a press on the same frame) and the
  resulting input stream frame by frame; the SCPH-1001 mode; the cards Beetle
  loads (blank, or the card-1 preload: the copy changes, the image does not);
  cards Beetle does not load (the fake uses other names, so a stray card
  appears); arguments refused before launch (card, including, since round 2,
  an image of the wrong size and an unreadable one; BIOS, profile, route
  name, `--start`), each with no traceback, no fake started and no output
  directory; a missing or wrong BIOS report; late input (the fake handles each
  request one frame late); an exit during the route; stalled frames (the
  timeout applies); a failed screenshot (recorded, not a failure); a nonzero
  exit after SIGTERM; a busy port; a server that reports a bind failure;
  output-directory reuse; and SIGTERM to the driver. Blank cards are checked
  against the PS1 card layout in psx-spx, not against the driver's code.
- `AGENTS.md`: a "Beetle oracle" section (the build, the driver, its failure
  rules, Beetle's card names and when it saves the cards, the one-frame
  timing window, that the driver and its tests are Linux-only, the commands,
  comparing along routes rather than frames, and when a route change needs a
  Beetle run).
- `.agent/HANDOFF.md`: this rewrite. The Phase 0 to Phase 3 change 4 sections
  are unchanged; change 5 is condensed, and the spike has its own section.

## Phase 4 change 1 checks

- Driver tests: `python3 -B scripts/routes/test_beetle_route.py` passes 15
  tests in about 21 s and leaves no temporary entry, fake process or
  `__pycache__`; since round 2 the argument test also refuses a wrong-size
  and an unreadable `--card1` image.
- Memory card fix (`card_regression.py` / `.log`): the tests against the
  driver as it was before the fix (rebuilt in scratch by undoing its three
  code hunks) fail exactly the three card tests; against the fixed driver
  they pass.
- Mutations (`mutations.py`; round 1 `mutations.log`, nine; round 2
  `r2/mutations.log`, eleven): each mutation, each removing one safeguard,
  fails the tests (the two added in round 2, removing the card size checks
  and the unreadable-card report, fail only the argument test); the
  unmutated copy passes; no leftovers.
- Beetle route runs: the second and third batches above; the first batch is
  kept in `batch1/`, the second in `batch2/`. The round-2 driver's re-run of
  the intro sampling route on Beetle gave the same shots and cards as the
  round-1 driver's in both modes (35 of 35 files each, `r2/u1_fine.log`).
- Comparisons: `beetle_summary.py`, `compare_results.py`, `diag_rows.py`,
  `compare_screens.py`, `card_compare.py`, `vector_probe.py`,
  `intro/intro_grid.py`, `r2/zone7_pixels.py`, `r2/u1_mid.py` and
  `r3/score_bonus.py`, with the results above.
- `checks-p4-1.sh` / `.log` (round 1, tree `9706929`): all pass. Nothing is
  unstaged or untracked; files outside this change, and the header and the
  Phase 0 to Phase 3 change 4 sections of this file, equal HEAD; no
  placeholder, no added line over 80 columns and no local path; the three
  gates pass, the pins and submodules are unchanged and clean, and only
  psxrecomp's `overlay_codegen_hash.h` is ignored there; Beetle's outputs are
  ignored and no tracked file is; the scripts pass `bash -n` and pyflakes;
  the batch hashed the staged driver; the tests, the mutations, the card
  regression and the committed runner's tests pass; the batch counts and
  every comparison log reproduce (`compare_results.py` and `card_compare.py`
  exit 1, for the five replays and the SCPH-1001 write-test frames described
  above); no listener is left; `git diff --cached --check` is clean.
- `r2/checks-p4-1-r2.sh` / `.log` (round 2, tree `9d7f44a`): all pass. The
  delta from the round-1 tree changes only the handoff, `AGENTS.md`, the
  driver and its tests, and the driver's code without its docstring parses
  to the same syntax tree as round 1's. Every round-1 check holds again: the
  identity, files outside this change, the preserved handoff sections, no
  placeholder, doubled blank line, added line over 80 columns or local path,
  the gates, pins, submodules and ignore rules, `bash -n` and pyflakes, the
  driver tests, the card regression and the committed runner's tests.
  `mutations.py` reproduces `r2/mutations.log`. The third batch hashed the
  staged driver and passed 44 of 44 runs with no retry, `r2/batch_compare.py`
  finds no difference from the second batch, and every comparison log
  reproduces from the third batch and equals its `batch2/` copy
  (`compare_results.py` and `card_compare.py` exit 1, for the five replays and
  the SCPH-1001 write-test frames described above). `r2/zone7_pixels.py`,
  `r2/u1_mid.py` (against both batches) and `intro/intro_grid.py` reproduce
  their results; no listener is left; `git diff --cached --check` is clean.
- `r3/checks-p4-1-r3.sh` / `.log` (round 3, staged tree): all pass. The
  delta from the round-2 tree changes only this file. Every round-2 check
  holds again, `r3/score_bonus.py` reproduces `r3/score_bonus.log` into a
  scratch directory, no temporary crop is left in `phase4-1/` after
  `r2/u1_mid.py` and `r3/score_bonus.py`, and the commit message draft has no
  line over 72 columns, no local path and only its verdict placeholder.

## Phase 4 change 2 observations (`.cache/evidence/phase4-2/`)

- Play session 1 (`play/session-01/`, 2026-10-20 from 16:40 to 17:07) was
  started by the first version of `play/play.sh` (it now runs the play copy,
  below) and watched by `play/watch_play.py`, which polls the debug server
  every 2 s (read-only queries plus a screenshot every 30 s). The user played
  the windowed `build-dev` binary (sha256 `07ff3159…`, HEAD `6d0a173`) on the
  SCPH-1001 v2.2 dump (LLE boot), with an analog pad (a Flydigi Vader 3 in
  X-input mode, which needed the kernel's `xpad` driver; seen in the kernel
  log at the time, not saved) and the launcher's video settings: OpenGL,
  1080p internal resolution (5x), supersampling, antialiasing and bilinear
  filtering (`runtime.log`). The launcher's PLAY started the game, and the
  debug server first answered at frame 41. The window closed at frame 64,634
  (`cwd/psx_last_run_report.json`, exit origin `sdl_window_close`), with
  runtime exit 0 (`session.txt`). That report counts 0 unknown dispatches and
  0 segment misses, and so did every watcher poll, at 59.9 frames/s, up to
  the last one answered, at frame 64,525 (`watch.log`). Of the 35 screenshots
  (`shots_sheet.png`), the last ones show zone 4 paused (the pause screen
  reads 4TH ZONE) and then the title screen, so zones 1 to 3 were cleared (two
  of their results screens fall in the sample); the capture store holds a page
  of S4.BIN (`capture_search.log`). The interpreter's overlay rows
  (`dirty_ram_stats`) held 849 instructions in 8 rows at frames 18,869, 36,892
  and 54,917. The watcher kept the five largest rows, 831 instructions at PCs
  that the committed routes also interpret: 0x80135EFC 448 (`menus`,
  `memcard` and the unlocked-zone routes), 0x80127690 299 and 0x801276B0 63
  (`title_to_zone1`), 0x80120370 12 (every route; `phase3-4/probe_summary.log`
  and `phase3-5/probe_summary.log`) and 0x8012649C 9 (`title_to_zone1`;
  `phase3-4/r2/pc_entries.log`). The other three rows, 18 instructions, are
  not named. The total did not change from frame 18,869 to frame 54,917,
  which is in zone 4 (shot 0029); the rest of zone 4 was not sampled. Live
  input is not recorded, so the session has no Beetle comparison.
- Card 1 holds an environment save made in the menus. It is byte-identical
  to the save the `memcard` route makes through LOAD/SAVE (sha256
  `42dd8d89…`, one `BASCUS-94449OMEBENV` block; `.cache/routes/memcard/`). It
  was last written at 16:50:36, about nine seconds after the watcher's
  main-menu shot with LOAD/SAVE highlighted (`shots/0000-f0002659.png`,
  16:50:26), in a card directory no earlier run had used (the runtime wrote
  its `.pst_bios_isolated` marker there at 16:49:56, which it does only where
  none exists, `psxrecomp/runtime/src/savestate.c:227-228`). Card 2 equals
  the card 1 that `title_to_zone1` and `menus` leave after the game's write
  test (`887419c3…`). So a save to slot 1 ran under live play in SCPH-1001 mode
  with no miss (derived; the player's presses are not recorded). Neither card
  file changed after 16:50:36, so the game wrote no card after that save.
- The vertical line on the title screen (`render/`) comes from psxrecomp's
  bilinear filter, not from the recompiled game. It lies at native x = 256.
  In the OpenGL shader's plain bilinear path
  (`psxrecomp/runtime/src/gpu_gl_renderer.c:1489-1516`), `fetch_texel` wraps
  a neighbour's texture coordinate to 0..255 (`:1402`) before clamping it to
  the prim's limits (`:1410-1411`), so at a prim edge on a 256-texel page
  boundary the neighbour comes from the far side of the texture. That this
  makes the session's line is derived, from its position and from the probe
  below; which prims the title draws at x = 256 was not traced. The Vulkan
  shader has the same order (`psxrecomp/runtime/shaders/geo_tex.frag:34-42`),
  and the renderer's "stable" mode clamps first
  (`gpu_gl_renderer.c:1425-1429`). `render/seam_probe.py` reproduces it on a
  scratch copy of `build-dev` with the session's video settings,
  `--headless-opengl` and an HLE boot, varying only `texture_filtering`. On
  the title screen, column 256 is darker than both neighbours (by more than 24
  in R+G+B) in 45 of 224 rows of the native capture with bilinear, and in 2
  with nearest, the same 2 as in the software renderer's headless capture and
  in Beetle's, which come from the picture (`seam_swirl.log`). The session's
  own capture of the title, after play, has 122 rows where column 256 is
  brighter than both neighbours (none in the bilinear probe's capture, 6 in
  the nearest, software and Beetle captures): the seam's colour depends on
  what the wrapped texel holds. `seam_crop_native.png` shows the five
  captures side by side. Upstream master `fe8d937` has the same code;
  reported as psxrecomp #719.
- Bilinear filtering and the UI: `texture_filtering` accepts only `nearest`
  or `bilinear` at the pin
  (`psxrecomp/recompiler/src/config_loader.cpp:675-680`; master adds `xbr`),
  and bilinear applies to every textured prim, the 2D UI included. The
  renderer's 3D-only "stable" mode, which leaves untracked UI unfiltered and
  clamps before it wraps, can be selected only by a trusted mod plugin
  (`psxrecomp/runtime/include/mod_plugins.h:78-82`), and only OpenGL has it:
  the Vulkan backend turns any non-zero mode into bilinear
  (`psxrecomp/runtime/src/gpu_vk_renderer.c:2609`). Reported as a feature
  request, psxrecomp #720. The user chose Nearest filtering for now.
- The SCPH-1001 exception-stub difference (change 1, exception vectors) is
  psxrecomp behaviour, not a recompilation error. At the first dispatch of
  the game's entry, `fntrace_mark_game_started()`
  (`psxrecomp/runtime/src/fntrace.c:55-64`) calls
  `memory_clear_low_boot_scratch()`, a `memset(ram, 0, 0x10)`
  (`psxrecomp/runtime/src/memory.c:189-191`). After that,
  `psx_write_word_raw` drops stores to RAM 0x0-0xF from the BIOS's relocated
  stub copy, and stores to RAM 0 from listed BIOS delay loops
  (`memory.c:1956-1989`; the comments cite Tomba 2's card write with buffer
  0). `stub/stub_probe.py` (a scratch copy of `build-dev`, LLE SCPH-1001,
  boot write trace on RAM 0x0-0x90) shows the stub written at frame 0, word
  0 = 3 from frame 388 (the psx-spx state; in the first run's trace, delay
  loops in the BIOS shell, relocated to RAM at 0x8005xxxx, write it,
  `probe-runtime-scph1001.log`), and 0x00-0x0F zero from frame 896, when the
  game starts. No traced guest store explains that: after frame 0 the trace
  holds no store to 0x04-0x0F, and word 0's last store before the game's own
  (0x11111111 at frame 1,049) is a BIOS delay loop's at frame 895, which
  leaves 3. The trace hook runs after the store filters
  (`psxrecomp/runtime/src/memory.c:2029`), so stores they drop do not appear.
  The DMA trace (frames 96 to 1,102; the EXE's last sector lands at frame
  893) has no transfer to low RAM (`probe-runtime-scph1001-r3.log`,
  `dma-around-896.log`, `dma-low-check.log`). psx-spx (Kernel (BIOS),
  "Garbage Area at Address 00000000h", saved as
  `stub/psx-spx-kernelbios.txt`) documents the copy as present on hardware
  and names games that read it (R-Types, Fade to Black); Beetle keeps it. In
  Omega Boost it changes only bytes 4 to 11 of card frame 63, because the
  game uses RAM 0 as its write-test buffer. Reported as psxrecomp #721,
  scoped to the clear and the stub-copy filter (the delay-loop filter matches
  Beetle, where the game's write-test word survives).
- Launcher state. While it was open, the session's launcher wrote
  `keybinds.ini` and `config.ini` beside `build-dev/Omega_Thrust`; when the
  user pressed PLAY it wrote `input.ini`, `launcher-window.ini`,
  `settings.toml`, `bios.cfg` and `disc.cfg` there
  (`play/launcher-file-times.txt`), and `multitap_analog = true` into the
  tracked `game.toml` that `--game` named
  (`psxrecomp/runtime/src/main.cpp:16309-16317`; the line restates the
  default, `main.cpp:14454`). Quit would also have written that line and
  `settings.toml` (`main.cpp:16148-16412`). Every launch reads
  `settings.toml` beside the executable (`main.cpp:15053-15069`) and treats
  `bios.cfg` as an explicit BIOS choice (`main.cpp:3004-3017`). So
  `title_to_zone1` in `hle-openbios` mode from `build-dev/` booted SCPH-1001
  and failed the runner's banner check (`play/hazard-route.log`), and the
  headless software renderer took the 5x and bilinear settings, which the
  runner does not check (`play/hazard-route/runtime.log`); `--memcard-dir`
  still clears the settings' card paths (`main.cpp:15352-15361`). With the
  user's agreement, the seven files moved to a play copy of the build,
  `.cache/play/build/` (their hashes match,
  `play/launcher-files-moved.sha256`). The launcher's `game.toml` is kept as
  `play/game.toml.launcher-modified` (`play.sh` gives the play copy the
  tracked one at each session start), and the tracked `game.toml` is back to
  HEAD. The same route from `build-dev/` then passed on OpenBIOS, with no 5x
  or bilinear line in its log (`play/hazard-route-after.log`,
  `play/hazard-route-after/runtime.log`). A headless run of the play copy
  with its own `game.toml` loaded that file and the user's settings, booted
  SCPH-1001 and ran 1,223 frames with no miss (`play/playcopy-check/`).
  `play/play.sh` now refreshes the play copy from `build-dev/` (never the
  launcher's files or `mods/state.toml`), passes the copy's `game.toml`, and
  keeps the cards in `.cache/play/memcards/`, which starts with copies of
  session 1's two cards. The play copy's `settings.toml` still selects
  bilinear filtering and names `session-01/memcards/` for the cards, which
  `play.sh`'s `--memcard-dir` overrides; its `mods/state.toml` names the
  disabled HD-texture pack by its `build-dev/` path.
- Upstream issues, filed under the user's account with the user's agreement
  (texts in `upstream/`): psxrecomp #719 (the bilinear seam), #720 (the
  3D-only filter as a user setting) and #721 (the low-RAM clear at game
  start).

## Phase 4 change 2 changes

- `.agent/HANDOFF.md`: this scope, the change 2 sections, the hypotheses, the
  review state (change 1's round-3 verdict and commit) and the next action.
  The Phase 0 to Phase 4 change 1 sections are unchanged.
- `AGENTS.md`: the Running section says what the launcher writes and where,
  on PLAY and on Quit, what later runs read, and that the launcher runs only
  from a copy of the build outside `build-dev/` with its own `game.toml`.
- Round 2 (review round 1's findings): this file now records the session's
  card save, which interpreter rows the watcher kept and how far its samples
  reach, the trace sentence, the seam's row counts and the closing frame;
  `AGENTS.md` adds Quit and the settings later runs read.
- Untracked (ignored): the play copy and its card directory, `play/play.sh`
  and the evidence under `.cache/evidence/phase4-2/`. On GitHub: the three
  upstream issues above. The tracked `game.toml` is back to HEAD.

## Phase 4 change 2 checks

- Round 1, `checks-p4-2.sh` / `.log` (staged tree): all pass. Only this file
  and `AGENTS.md` change; the header and the Phase 0 to Phase 4 change 1
  sections of this file equal HEAD; there is no placeholder, doubled blank
  line, added line over 80 columns or local path; the three gates pass, the
  pins and submodules are unchanged and clean, and only psxrecomp's
  `overlay_codegen_hash.h` is ignored there; no tracked file is ignored, and
  the play copy is; `build-dev/` holds none of the launcher's files, the
  tracked `game.toml` equals HEAD, the moved files match their hashes and the
  play copy's binary equals `build-dev`'s; `title_to_zone1` in `hle-openbios`
  mode from `build-dev/` passes, with no 5x or filter line in its log; the
  three test files pass and leave nothing behind; every evidence file this
  file cites exists; the three upstream issues are open; no listener is left;
  `git diff --cached --check` is clean.
- Round 2, `r2/checks-p4-2-r2.sh` / `.log` (staged tree): all pass. Round
  1's checks again on the round-2 tree, with the evidence list extended to
  the files round 2 cites; the play copy's launcher files keep the times in
  `play/launcher-file-times.txt`; and each corrected fact reproduces from its
  evidence and source lines: the card hashes, the save's directory entry and
  the card and shot times; the three interpreter samples (849 instructions in
  8 rows, 831 in the five kept) and each PC's routes; the trace's low-RAM
  stores by address and frame, with the first run's frame-389 stores; the
  launcher's PLAY and Quit writes in `main.cpp`; the seam row counts and the
  exit report; the hazard-route logs and the Vulkan filter line.

## Hypotheses and unknowns

- The intro screens that differed by boot mode at equal frame numbers (Phase
  2, `git show e58cf21:.agent/HANDOFF.md`, and Phase 3 change 1) are points
  of one sequence that every mode, and Beetle, shows in the same order (Phase
  4 change 1, intro). Why Beetle reaches each screen later than psx-runtime in
  the same BIOS mode, at boot, in the intro and at the results screens:
  unknown (hypothesis: Beetle's CD timing).
- Whether the eight emitted fallthroughs are faithful: unknown.
- Untested by committed routes: TRAINING lessons, ZONE PLAY zones, and SAVE
  REPLAY and LOAD REPLAY, which scripted menu input may reach; CAMPAIGN PLAY
  past zone 1, the ending and credits, which need steering. Zones 1 to 4 of
  CAMPAIGN PLAY and a save to card 1 ran once under live play without a miss
  (change 2); live input is neither recorded nor compared with Beetle. The
  DEMONSTRATION routes run all 19 zones, but under recorded input; whether
  that reaches the code live play reaches is unknown. Any of the 160
  statically unresolved indirect transfers that neither reached can still
  miss later.
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
  (hypothesis). Along the committed routes, Beetle, which runs the original
  overlay code, shows the same results text (and the same SCORE BONUS figure
  in 24 of the 38 pairs; in the others it was still counting, derived), the
  same screens in the same order and (in OpenBIOS mode) the same cards. Why
  the game runs code at those PCs, and whether the shard behaves like the
  interpreter beyond the routes: unknown. In the live session (change 2) the
  overlay rows held 849 interpreted instructions, 831 of them at five of
  those PCs (three rows, 18 instructions, are not named), and the total did
  not change from frame 18,869 to frame 54,917, in zone 4; the rest of zone 4
  was not sampled. `full_static_coverage_proven` is false: code the extractor
  cannot find statically still goes to the interpreter.
- In SCPH-1001 mode, psx-runtime's RAM lacks the BIOS's exception stub at
  0x80000004 to 0x8000000F, which Beetle has: the runtime clears RAM
  0x00-0x0F when the game starts and then drops the BIOS's stub-copy stores
  there (change 2), reported as psxrecomp #721. In Omega Boost it changes
  only the card's write-test frame; no game-visible effect has been seen.
- recomp-ui `864f778`: the launcher dashboard works, and PLAY started the
  game in play session 1 (change 2). It saves its state beside the executable
  and into the `--game` file, so it runs only from the play copy.
- With bilinear filtering, psxrecomp's OpenGL and Vulkan shaders wrap
  neighbour texels across 256-texel page edges (#719), and the filter also
  smooths the 2D UI (#720); the user plays with Nearest for now. The route
  runner and the Beetle comparisons use headless software-renderer captures,
  which no filter setting reaches while `build-dev/` holds no `settings.toml`.

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
- Phase 3 change 5: round 2 PASS on tree `91d6447` (staged diff `5ecf0036…`)
  with no findings, after round 1 NEEDS CHANGES on tree `a831f14` (three Low:
  the preload test could not fail, because the fake runtime only read the
  card; two misattributed change 4 review rounds in this file; a traceback on
  an unreadable `--card1`); commit `2a3fe3a`, pushed to the private
  `origin/master`. Reports: `phase3-5/review-r1.md`, `phase3-5/r2/review-r2.md`.
  Declined in round 2: capping the pixel rule at the full counts, which would
  drop 20 real results screens (`phase3-5/r2/capped-dropped_sheet.png`). Round
  2's suggestions: "a mutation fails only the subtests it affects" (applied in
  the change 5 section above); the commit message's spike wording (fixed in
  the commit); the debug server's `set_input` and `press` take stick axes
  `lx`, `ly`, `rx` and `ry` (`psxrecomp/runtime/src/debug_server.c:7951-7980`),
  so the recordings' stick values could be injected without a framework
  change, though not frame-exactly (in Next action); a label bound near 600 in
  the evidence pixel rule (evidence tooling, deferred). Still deferred: the
  demo routes' fine-cadence notes (fixed when they are next regenerated),
  ignoring SIGINT during the runner's cleanup, a lock file for one runtime per
  build, and naming the last two interpreted `title_to_zone1` PCs.
- Phase 4 change 1: round 1 NEEDS CHANGES on tree `9706929` (staged diff
  `5663f5b7…`; report `phase4-1/review-r1.md`), six Low, resolved in round 2.
  L1: Beetle also saves a changed card about two emulated seconds after the
  game's last write, not only on exit; corrected in `AGENTS.md`, the driver's
  docstring, the test comments and this file, with the source lines and the
  second batch's file times. L2: zone 7's differing pixels are background
  under the light sweep, not the small digits; corrected, with
  `r2/zone7-sweep-crops.png`. L3: U1's mid-replay results screen is now
  recorded and compared (a finer-sampled scratch run). L4: the results claim
  names what was compared (the four text rows, three pairs with pixels left
  out, SCORE BONUS only where final). L5: the prototype batch had four
  failures, not two; corrected. L6: the commit message is rewritten (seven
  bytes, the light sweep, U1's SCORE BONUS, the same screens in the same
  order). Suggestions adopted: the `beetle_main.cpp:226-233` citation;
  wrong-size and unreadable `--card1` test cases, with two more mutations
  (eleven, all caught); the driver is Linux-only (`AGENTS.md`, docstring);
  the stray check covers only card 1 in the unlocked-save routes (first-batch
  bullet); when a route change needs a Beetle run (`AGENTS.md`); the Engram
  memories corrected. Deferred: tests for the connect-too-late and reply-id
  checks (each needs a new fake behaviour; the next driver change), and a
  finer shot cadence where a replay shows a mid-replay results screen (a
  route change; the scratch run covers U1). The reviewer's `git status` in the
  ignored `.cache/beetle/psxrecomp/beetle-psx` refreshed that checkout's index
  stat cache (content unchanged; `build_beetle.sh` recreates the checkout).
- Phase 4 change 1: round 2 NEEDS CHANGES on tree `9d7f44a` (staged diff
  `1b8e5f50…`; report `phase4-1/r2/review-r2.md`), two Low, resolved in
  round 3. R2-1: five pairs whose SCORE BONUS figure is the same on both
  sides (zone 7 and U8 in both modes, U2 in SCPH-1001) were recorded as still
  counting; their differing pixels are the light sweep or background. Read
  from the digits (`r3/score_bonus.py`), the figure is the same in 24 pairs
  and differs in 14; the scope, the results and U1 bullets, the hypotheses
  and the commit message are corrected, and U1's one differing mid-replay
  pixel in SCPH-1001 is recorded as a background dot, not counting. R2-2: the
  sweep covers 49 of zone 7's 56 differing pixels at the stated shots, not
  all of them, and zone 3's PILOT ABILITY row left out 42 of 832 pixels, not
  of 790; both corrected. Suggestions adopted: `u1_mid.py` removes its
  temporary crop; the commit message words the screen comparison as this
  file does; the U1 bullet says its shot ranges come from the rule's
  results-screen test; "final" is labelled derived; Engram #225 corrected.
- Phase 4 change 1: round 3 PASS on tree `7598286` (staged diff `3c600242…`)
  with no findings (report `phase4-1/r3/review-r3.md`); commit `6d0a173`,
  pushed to the private `origin/master`. Round 3's one suggestion, to keep
  "at the figure's left end" for U8 in the commit body, is noted: the commit
  body calls those pixels background.
- Phase 4 change 2: round 1 NEEDS CHANGES on tree `2180832` (staged diff
  `96d3744c…`; report `phase4-2/review-r1.md`), five Low, resolved in round
  2. L1: card 1 holds an environment save, byte-identical to the `memcard`
  route's, so the session did save; recorded in a card bullet, and the play
  copy's card directory starts with session 1's cards. L2: the watcher kept
  five of the eight interpreter rows (831 of 849 instructions), and its last
  sample is frame 54,917, in zone 4; both stated, with each PC's source. L3:
  after frame 0 the trace has stores to word 0 (BIOS delay loops up to frame
  895, the game at frame 1,049) but none to 0x04-0x0F; corrected, with the
  trace hook's place after the store filters. L4: the launcher writes the
  `game.toml` line and `settings.toml` on Quit as well as on PLAY; corrected
  in `AGENTS.md` and noted in the launcher bullet. L5: the bilinear probe's
  capture has no brighter rows, and the window closed at frame 64,634 (the
  exit report, which also counts 0 misses); corrected. Suggestions adopted:
  the seam link labelled derived; the 5x and filter lines cited from
  `play/hazard-route/runtime.log`, and the after-move run copied to
  `play/hazard-route-after/`; `play.sh` replacing the play copy's `game.toml`
  noted; the play copy's settings and mod state recorded; "the ending and
  credits" in Next action; "stable" mode is OpenGL-only; `AGENTS.md` names
  internal resolution, supersampling, texture filtering and card paths;
  "untracked (ignored)". The launcher file times are now saved
  (`play/launcher-file-times.txt`), and "in the same second" for the
  `game.toml` write, which no saved artifact shows, is dropped. On #721's
  wording: the first probe run's trace (`stub/probe-runtime-scph1001.log`,
  lines 13-24) shows the frame-389 stores from delay loops in the relocated
  BIOS shell, so "the shell's CD delays" stands; whether to note on #721
  that its frame-1200 bullet may catch Beetle before the game starts (Beetle's
  SCPH-1001 boot runs behind) is the user's call.
- Phase 4 change 2, round 2: pending delta re-review.

## Next action

After a PASS: commit and push. Play continues from the play copy:
`play/play.sh <session dir> <SCPH-1001 dump>` (in `.cache/evidence/phase4-2/`)
refreshes `.cache/play/build/` from `build-dev/`, runs the windowed game there
with its own `game.toml` and with persistent cards in `.cache/play/memcards/`,
and watches the debug server. The play copy's settings still select bilinear
filtering; the user's choice, Nearest, is set in the launcher. Still
unreached: CAMPAIGN PLAY zones 5 to 8 and LAST, the ending and credits (the
spike reached the ending and credits only by rewriting the campaign script,
and its post-credits halt is unexplained), TRAINING lessons, ZONE PLAY zones,
SAVE REPLAY and LOAD REPLAY. psxrecomp #719, #720 and #721 are open
upstream; any fix arrives through a reviewed pin bump. Independent
changes: harvesting misses with `psxrecomp/tools/collect_game_misses.py`
(none so far); finding why Beetle reaches screens later than psx-runtime (for
example by comparing when each CD read completes).

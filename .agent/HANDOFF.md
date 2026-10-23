# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison. Phase 5, at the user's
request, is modding: unlocks, branching, new levels, and later perhaps a fan
sequel or remake that borrows Colony Wars' free-roaming structure. Phase 6,
also the user's choice, works through an independent audit of the committed
code (`.cache/evidence/code-quality/audit-r1.md`): its fixes and
readability cleanups, each its own small reviewed change.

Current iteration, Phase 6 change 2, round 2: the first `zone_data.py`
cleanup, the audit's steps 2 to 4 (findings 5, 6 and 8). Invariant:
`scripts/zones/zone_data.py` names what it passed as positional tuples or
raw numbers, and, for any file shorter than 267,255,808 bytes, nothing it
does changes. Named tuples carry a zone's timeline (`Timeline`, with `slots`),
its layout (`Layout`, with `span`), the parts build may write (`Part`) and
the zones a package edits (`ZoneEdit`); constants and small decoders name the
MIPS opcodes, functions, registers and fields and the ISO 9660 offsets; record
formats and value ranges are named once and the ranges checked with
`in_range()`; terse names (`ws`, `k`, `f`, `cb`) become words. The module
docstring, every message, the command line and every output stay the same:
the 142 outputs of the baseline from HEAD's tool (`list`, `check`, every
timeline zone's dump, the zone files the dumps build, builds and packages of
the dumps kept under `.cache/zones/`, the stock S1 package and the Crossfire
remix) come out byte-identical, the 61 tests pass unchanged, and HEAD's tool
and the new one give the same result on the same generated inputs. This file
records change 1's round 3 PASS and commit `0761991`, condenses change 1 and
takes up round 3's suggestions; `AGENTS.md`'s Beetle oracle section, per
suggestion 6, names a ping reply without a frame number among the reasons a
run fails. Round 2 answers review round 1's two findings and takes up its
suggestions (Review and commit state). Baseline: `0761991`.
Out of scope: splitting the long functions and moving code into modules
(the next steps), the audit's three `zone_data.py` fixes, the route scripts,
the tests, the C plugins, the framework and submodules.

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

## Phase 4 change 1 (commit `6d0a173`)

`scripts/build_beetle.sh` builds psx-beetle, the framework's Beetle PSX
oracle, out of tree in `.cache/beetle/`: archives of the framework commits
that HEAD pins (the submodule checkout is never written), beetle-psx-libretro
`5759277be500…` with the framework's seven patches, then `ninja psx-beetle`
(sha256 `63d0e568a6e5…`). `scripts/routes/beetle_route.py` plays a committed
route on it in `lle-openbios` or `lle-scph1001` mode. psx-beetle has no
`input_route_*`, memory-write or quit command, so the driver keeps one debug
connection, follows the frame count and sends each press, and each shot once
its step has ended, with a `ping` on the frame before: every event lands on
its route frame, counted from `--start`, or the run fails. A run also fails if
the BIOS image's sha256 is not its framework profile's, or if Beetle's log
does not report that image's SHA-1. Beetle reads the memory cards from its
working directory as `<disc name>.0.mcr` and `.1.mcr`, and saves a changed
card about two emulated seconds after the game's last write to it and again on
exit if it changed since; the driver writes the cards under those names and
fails a run if psx-beetle writes any other file there. The first full batch
had used the `dummy.*.mcr` names from a warn-only log check, files Beetle
never loads, so its 26 unlocked-save runs never had the save. Unpaced, Beetle
takes about 3 ms per frame, the driver's whole window to answer a ping; one
first-batch run landed its first shot a frame late and passed when run again.
`scripts/routes/test_beetle_route.py` has 15 tests against a fake psx-beetle;
eleven mutations, each removing one safeguard, all fail them. The second and
third batches passed all 22 routes in both modes (44 runs each, byte-identical
to each other). On the 19 replays' results screens the banner, CLEAR TIME,
DESTROY RATIO and PILOT ABILITY text is the same on both emulators: 33 of the
38 replay-mode pairs match by the comparison's pixel rule. Of the other five,
zone 7 (both modes) and LAST (SCPH-1001) differ only in pixels outside the
glyphs (zone 7: background pixels lit by the light sweep; LAST: the mech model
behind the text), and U1 (both modes) fails the rule because Beetle has fewer
than two results shots (`phase4-1/compare_results.log`), and on its one shot
those four rows have no differing pixel; the same text was read at 2x. In 24
pairs both sides show the same SCORE BONUS figure; in the
other 14 the figures differ as a tally still counting would (derived). U1's
mid-replay results screen matches in a finer-sampled scratch run.
`title_to_zone1`, `menus` and `memcard` show the same screens in the same order
(title, menu and memory card screens 90.2 to 99.9% equal in RGB, zone-1
gameplay 73 to 74%). In LLE OpenBIOS both emulators leave byte-identical cards
after every route; in SCPH-1001 mode every card the game rewrote differs in
seven bytes of its write-test frame (frame 63): words 2 and 3 of the BIOS's
exception stub on Beetle, zeros on psx-runtime (explained in change 2). The
intro screens that differed by boot mode are points of one sequence that all
five runs (three psx-runtime boot modes, two Beetle) show in the same order;
Beetle reaches each screen later than psx-runtime in the same BIOS mode
(hypothesis: CD timing). Review: round 1 NEEDS CHANGES (six Low), round 2
NEEDS CHANGES (two Low), round 3 PASS on tree `7598286` with no findings. The
full record is in `git show 6d0a173:.agent/HANDOFF.md`.

## Phase 4 change 2 (commit `a005f9e`)

Bookkeeping after the first watched play session
(`.cache/evidence/phase4-2/`). On 2026-10-20 the user played the windowed
`build-dev` binary on the SCPH-1001 v2.2 dump with an analog pad (a Flydigi
Vader 3 in X-input mode, which needed the kernel's `xpad` driver; seen in the
kernel log at the time, not saved), watched by `play/watch_play.py`
(read-only debug-server polls every 2 s, a screenshot every 30 s). Zones 1 to
3 of CAMPAIGN PLAY were cleared, and zone 4 was paused before the title
screen. Card 1 holds an environment save from the menus, byte-identical to the
`memcard` route's (derived from hashes and file times). No earlier run had
used the card directory: every run writes a `.pst_bios_isolated` marker into
it at startup (`psxrecomp/runtime/src/main.cpp:17801-17819`,
`savestate.c:393`), only where none exists (`savestate.c:227-228`), and the
marker's time is this session's. The window closed at frame 64,634 with no
unknown dispatch or segment miss in the exit report or in any watcher poll;
the polls show 73.5 frames/s in the first minute after the server answered
(frames 41 to 4,460) and 59.9 frames/s after that (`watch.log`). The
interpreter's overlay rows held 849 instructions from frame 18,869 to 54,917,
831 of them at five PCs the routes also interpret (0x80120370 in every route:
`phase3-5/probe_summary.log`, and `phase3-4/r2/pc_entries.log` for
`title_to_zone1`). Findings, all framework behaviour: the line
through the title screen comes from the bilinear filter, whose shaders wrap a
neighbour texel to the far side of a 256-texel page before clamping it
(`psxrecomp/runtime/src/gpu_gl_renderer.c:1402`, `:1410-1411`; reproduced on
a scratch copy; that it makes the session's line is derived), psxrecomp #719;
bilinear also blurs the 2D UI, and the 3D-only "stable" mode is reachable only
from a mod plugin and only on OpenGL, #720; the user plays with Nearest for
now. At the first dispatch of the game's entry the runtime clears RAM
0x00-0x0F and then drops the BIOS's stub-copy stores there
(`psxrecomp/runtime/src/fntrace.c:55-64`, `memory.c:189-191`, `:1956-1989`),
where psx-spx and Beetle keep a copy of the exception stub: that is change 1's
SCPH-1001 write-test difference, #721. In the probe's third run the low words
change at frames 388 (word 0 = 3), 896 (cleared) and 1,049 (the game's first
write); the first run, whose trace shows the frame-389 writers (delay loops in
the relocated BIOS shell), saw 389, 895 and 1,048. The launcher writes
`keybinds.ini`, `config.ini`, `input.ini` and `launcher-window.ini` beside the
executable, and when it closes, by PLAY or Quit, `settings.toml` there and
`[controller] multitap_analog` into the `--game` file (PLAY also writes
`bios.cfg` and `disc.cfg`). Later runs from that directory read them, so a
`hle-openbios` route from `build-dev/` booted SCPH-1001. The files moved to a
play copy, `.cache/play/build/`, which `play/play.sh` refreshes from
`build-dev/` and runs with its own `game.toml` and persistent cards in
`.cache/play/memcards/`; the tracked `game.toml` is back to HEAD, and
`AGENTS.md` says the launcher runs only from such a copy. Review: round 1
NEEDS CHANGES (five Low), round 2 PASS on tree `58a89e7` with no findings;
round 2's four wording suggestions are applied in this section (the
card-marker citation, the frame rates, the 0x80120370 citation, the probe
runs' frames). The full record is in `git show a005f9e:.agent/HANDOFF.md`.

## Phase 5 change 1 (commit `390a09b`)

Docs: the modding research the user asked for (new levels, branching paths,
unlocks, an eventual fan sequel or remake, Colony Wars' free roaming in Omega
Boost's engine), done on 2026-10-20 by three read-only research agents (the
framework's mod system, Omega Boost's internals, Colony Wars with prior art)
and checked against the pinned source, the disc and the web. The write-up is
`docs/MODDING_FEASIBILITY.md`; its evidence is in
`.cache/evidence/mod-research/` (among others `framework-check.txt`,
`verify_internals.py` / `.log`, `internals/`, `cw_check.py` / `.log`,
`gamehacking-codes.txt`, `prior-art.log`, `plugin-linking.log`,
`cmake-repeat-keyword.log`, `time-extension-article.txt`,
`time-extension-date.log`, `loader-dis.txt`, `precedents.log`, and
`level_labels.sh` / `.log` with `level-labels/`). The zone list's LEVEL labels
in change 5's `12-zone-cursor.png` shots are each zone's DEMONSTRATION level
value plus 1 for values 0 to 8, B for 10 and D for 12, the same in all three
boot modes; U1's, which only the draft left unclear, reads B in the 10x glyph
comparison with 8TH's "8" (`level-labels/glyphs-8-u1-u3.png`). The GameFAQs
cheats page now answers scripted fetches with HTTP 403 and no record saved
its unlock list, so the write-up does not compare the unlock rules with it.
`AGENTS.md` said, and the Phase 3 change 4 section above still says, that the
four words the static overlay step checks set the overlay base. The scene
loader branches past them (0x80075AEC) when the scene has a `.BIN`, so they
run only for a scene without one, putting its data at 0x80120000; with a
`.BIN` the data goes after the file (`loader-dis.txt`). `AGENTS.md` now says
so; the check still pins loader code beside the overlay load. The user's
account posted a comment on psxrecomp #721: the issue's frame-1200 comparison
may catch Beetle before its game starts, and the card bytes are the
like-for-like evidence (`phase4-2/upstream/issue-3-comment-1.md`). The user
then chose the "unlock all zones and boost levels" mod as the next change.
Review: round 1 NEEDS CHANGES (three Low, all in the doc), round 2 PASS on
tree `034e6be` with no findings. The full record is in
`git show 390a09b:.agent/HANDOFF.md`.

## Phase 5 change 2 (commit `9500812`)

The opt-in mod the user chose to prove the plugin, package and launcher
wiring: the package `omega.cheat.unlock-all` and its VBlank plugin
`omega.unlock-all` set the zone flags A[0..18] and the boost-level flags
B[0..13] while the feature is on (`AGENTS.md`, Mods; evidence in
`.cache/evidence/phase5-2/`). With the feature off, all 66 route runs passed,
the plugin wrote nothing, and the overlay counts equalled Phase 3 change 5
round 2's. With it on, from copies of the build with their own
`mods/state.toml` (scratch routes `unlock-on` and `unlock-saved`), ZONE PLAY
showed every zone and level OPENED and DEMONSTRATION every entry SELECT OK in
all three boot modes. A save made then holds the flags with a correct
checksum (0x09F245F2, the GameFAQs save's 0x09F244F2 plus 0x100 for B[13]),
and loaded with the feature off it opened the same on psx-runtime and, in
both of its modes, on psx-beetle. The plugin counted 64 writes, the last
during boot; in HLE mode 33 by VBlank 272 and 31 more by VBlank 422 (change
2's reviewer's probe; Derived: consistent with one boot-time reset of every
flag except the two the game sets itself; the writer is not traced). A
package targets a game by `game_id`, and by an EXE or disc hash only if it
sets one; release installs commonly do not carry a loose EXE to hash
(`psxrecomp/runtime/src/mod_runtime.cpp:1329`). `EXTRAS_SOURCES` sits above
`GEN_FULL_GLOB`, since after a multi-value keyword it would be read as that
keyword's values. Review: round 1 PASS on tree `6a7d573` (staged diff
`180a2cf5…`) with no findings; the report, not saved at the time, is now in
`phase5-2/review-r1.md`. The full record is in
`git show 9500812:.agent/HANDOFF.md`.

## Phase 5 change 3 (commit `b2e4e6a`)

The branching campaign prototype the user chose (`AGENTS.md`, Mods; evidence
in `.cache/evidence/phase5-3/`). Two packages, both off by default, run
instruction plugins at sites listed in `game.toml` `[recompiler]
mod_instruction_sites`. `omega.gameplay.branching` hooks the campaign loop's
step-limit check (0x8002FB2C): after an S on the 1ST ZONE the campaign plays
the 3RD ZONE, then the 2ND ZONE, MOVIE IM 0 and the 4TH ZONE. The hidden test
package `omega.debug.zone-clear` hooks the timeline runner (0x80071558) and
ends a zone through the game's own clear path, graded low with nothing
destroyed (D in zones 2 to 4, B in the 1ST ZONE, whose destroy factor is 0.5
at a ratio of 0; `records/`) and S with its `all-destroyed` option.
Regenerating added the three hook calls (`_03` twice, `_26` once) and rebuilt
the static shard with the same C; the audit changed only in its input
hashes. The launcher check change 2 left open passed: on a private X display,
from a copy of the build, the Mods page lists the unlock package under
Cheats, and PLAY wrote it into `mods/state.toml` and started the game with
A[0..18] and B[0..13] set (`launcher/`). With the test clear on, in all
three boot modes (scratch route `branch_check.json`), the S path played
scenes 3, 5, 4, 6 and 7 with three redirects, and low grades or branching
off kept the stock order. With both off, all 66 route runs passed with
change 2's overlay counts and no plugin counter. One of them
(`demo_zone_u4`, LLE OpenBIOS) had first been aborted by the runtime's
starvation watchdog after userspace on the host stalled for 25 to 27 s
(`failed/`, with the host journal) and passed when run again
(`rerun.log`). The 8TH ZONE (`S9.BIN`), U4 and U8 call the clear
routine from their own code as well as through the runner, and the 5TH ZONE,
the LAST ZONE, U5, U9 and V5 have no runner (`clear_callers.py` / `.log`);
the test clear ran only in the 1ST to 4TH ZONE. The audit does not count
instruction-only plugins (`mod_packages.cpp:1578-1585`). Review: round 2 PASS
on tree `aeccb7e` (staged diff `cc2fcbf3…`), after round 1 NEEDS CHANGES (see
Review and commit state). The full record is in
`git show b2e4e6a:.agent/HANDOFF.md`.

## Phase 5 change 4 (commit `b19fbe4`)

The zone data tool the user chose (`AGENTS.md`, Zone data; evidence in
`.cache/evidence/phase5-4/`). `scripts/zones/zone_data.py` reads the zone
files from the player's disc, writes the wave timeline of each of the
fourteen that pass a table to the runner's constructor (0x80071624) as TOML,
and builds the zone file back from it: byte-identical when unedited, edits
written in place within the stock slots. The runner, read from the EXE,
starts entry 0 without checking it, moves on when a delay runs out or as
soon as it has no child task left (the tasks the waves create, 0x80057F0C's
formation groups and 0x80063C5C's timers among them), waits on -100 only for
that, and after the end entry calls the clear routine 90 ticks later. The
8TH ZONE's table has no end entry, and no table can grow in place. Only the
1ST, 2ND, 3RD and 6TH ZONE's files call 0x80057F0C (38 of the 121 entries
pass it a formation record and two counts); 0x80063C5C appears in 17
entries across the fourteen zones, 11 of them in the ten without the
formation call (change 4's round-2 suggestion). A read-only watch of the
live runner during each zone's DEMONSTRATION replay (HLE mode) found it
running the tables the tool reports, with their delays, at 0.493 ticks per
frame over twelve zones; it reached the end entry's countdown in eleven
zones, and the 8TH ZONE, U4 and U8 ended through their own code. 25 tests;
24 planted bugs caught. Review: round 2 PASS on tree `645c1b9` (staged diff
`b704cfd7…`), after round 1 NEEDS CHANGES (see Review and commit state). The
full record is in `git show b19fbe4:.agent/HANDOFF.md`.

## Phase 5 change 5 (commit `bdd413f`)

The first playable remix the user chose (`AGENTS.md`, Zone data; evidence in
`.cache/evidence/phase5-5/`). `zone_data.py package <dump>` builds the zone
file as `build` does and writes a `.psxmod` whose one feature, off by
default, was a `disc_user` overlay of the stock table's slots (change 6
widened it to every byte `build` may write), targeting SCUS-94449 with the
sha256 of the disc image's data file, which the runtime compares with the
image it mounts (`mod_runtime.cpp:349-400`), and guarded by the stock bytes'
sha256, which it checks before launch (`:1628-1640`). The runtime copies each
overlay's part within each sector the CD path reads
(`mod_runtime.cpp:2547-2631`). A scratch remix of the 1ST ZONE (its first
four waves 60 ticks apart, then the end entry), installed in a copy of
`build-dev`, played in CAMPAIGN PLAY with no input in all three boot modes:
the remixed table loaded, the zone ended (CLEAR TIME 0:11.10, 15 spawned, 0
destroyed, rank B) and the campaign went on to the 2ND ZONE; with the
feature off the stock table ran. In none of the fourteen timeline zones
does a matching static variant guard a byte before the table's end, all
1,391 of the 1ST ZONE's match the remixed file, and the runs interpreted
1,309 overlay instructions in seven rows, as the stock route does, all seven
rows present before the zone file loaded (in five of the six runs the
count's last step, up to 371 instructions, falls between a sample before the
load and one after it). 34 tests; 44 planted bugs caught.
Review: round 3 PASS on tree `29e0e44` (staged diff `35b66fc5…`), after
rounds 1 and 2 NEEDS CHANGES (see Review and commit state). The full record
is in `git show bdd413f:.agent/HANDOFF.md`.

## Phase 5 change 6 (commit `88e0268`)

The formation records the user chose to decode (`AGENTS.md`, Zone data;
`docs/MODDING_FEASIBILITY.md`, "Formations"; evidence in
`.cache/evidence/phase5-6/`). In the 1ST, 2ND, 3RD and 6TH ZONE, 30 wave
callbacks pass 33 records to 0x80057F0C, each eight words (where its steps
and members are, a position added to the player's, and three binary angles,
pitch, yaw and roll, yaw the outermost: the heading is (cos a0 sin a1, -sin
a0, cos a0 cos a1)), with its numbers of steps (20 bytes: three turns, a
speed, ticks, flags) and members (16-bit offsets) as instruction immediates.
The task (update 0x80058300) counts each step's ticks (the first step lasts
its ticks, a later one ticks + 1), adds the turns, moves the centre along the
heading, rebuilds the member slots (centre + R × offset) and ends after its
last step. Each zone spawns every member with one function, so which enemy a
member is, is code. Five calls run on only one value of the difficulty word
0x800A7C34, which was 0 in all 2,829 samples of change 3's campaign runs
(non-zero is presumably HARD): the 3RD ZONE's wave-17 callback starts
0x8012227C, 0x80122320 and 0x801223C4 while it is non-zero and 0x8012248C
while it is zero, and the 6TH ZONE's wave-10 callback starts 0x80121F50 only
while it is non-zero. `zone_data.py` dumps the records (format 2) with notes
from a control-flow analysis of each callback and builds them in place, and
`package` covers every byte `build` may write (feature and payload `remix`).
A scratch remix of the 1ST ZONE (wave 1 moved and its members doubled; wave
2's first step twice as fast for half the ticks) ran in CAMPAIGN PLAY with no
input in all three boot modes: the formation tasks moved and placed their
members as predicted, next to runs with the feature off; the 868-byte overlay
crossed a sector boundary; no matching static variant guards a byte `build`
may write in any timeline zone; every run interpreted 1,309 overlay
instructions in seven rows. 49 tests; 91 planted bugs caught. Review: round
4 PASS on tree `aba593e` (staged diff `3dd57240…`), after rounds 1 to 3 NEEDS
CHANGES (see Review and commit state). The full record is in
`git show 88e0268:.agent/HANDOFF.md`.

## Phase 5 change 7 (commit `feb71aa`)

The remix pack the user chose (`AGENTS.md`, Zone data; evidence in
`.cache/evidence/phase5-7/`). `zone_data.py remix <recipe>` applies a
recipe, which holds only edits (stock waves by number with new delays;
formation edits by record address: spread, pace, yaw, move), to the zones on
the player's disc through `build`'s rules, and writes one `.psxmod` whose
`remix` feature carries an overlay for each zone; the framework reads every
`[[overlay]]` entry of a feature (`mod_packages.cpp:2449-2540`). The recipe
`scripts/zones/remixes/crossfire.toml` ("Omega Remix: Crossfire") remixes
the 1ST, 2ND, 3RD and 6TH ZONE. A formation starts at the player's position
plus its record's position, and the player flies on along positive z at
about 320 units a tick (9,600 a second), so yaw 180 turns a flight about the
player's position at the moment the formation starts, not about the
player's flight. In round 1, 8 of the 14 turned formations therefore never
came within 26,000 units of the player; round 2 moved them nearer and sped
some up, with values from a flight model (`approach.py`) that gives each
record's closest distance within 2,512 units of the runs'. Scripted runs
started each zone from ZONE PLAY with no input, unlock-all on, the pack on
and off, in all three boot modes: all 24 passed with no miss. In every run
the loaded bytes, the delay read at each entry start and each formation's
start angles, spacing, speed, ticks and start position matched the file the
run should use and failed against the other (`remix_check.py`); every
formation the recipe moves started on its stated side and came within 387
to 5,040 units of the player (`approach.py check`); and every run
interpreted the same 12 overlay instructions. 61 tests; 131 planted bugs
caught. Review: round 3 PASS on tree `ad268a4` (staged diff `aaa58aa5…`),
after rounds 1 and 2 NEEDS CHANGES (see Review and commit state). The full
record is in `git show feb71aa:.agent/HANDOFF.md`.

After the commit, a launcher check (scratch; evidence in
`.cache/evidence/phase5-7/launcher/`) drove the launcher on a private X
display, from a copy of `build-dev` with its own `mods/`. The Mods page's
"Install .psxmod" opened the desktop's file picker (`kdialog`), which took
the pasted path of the play copy's pack (built from the committed recipe;
no pack is committed, since a pack holds disc data); the page then said
"Package installed. Changes apply when you press PLAY." and listed "Omega
Remix: Crossfire 1.0.0" under Remix, and the installed files equal the
archive's. Ticked, PLAY wrote the selection to `mods/state.toml` (and, as
documented, `multitap_analog` into the copy's `game.toml`). The game (HLE
OpenBIOS), driven through CAMPAIGN PLAY into the 1ST ZONE, ran the pack's
timeline and formations with no miss: every check of `remix_check.py` and
every claim of `approach.py` held against the pack's file, and the checks
failed against the stock file (`route/check_run.log`). That saved output
equals a check of the watcher's first 1,235 rows (to frame 7,410) and of no
other prefix of the log, so it was made while the watcher was still
writing (Derived); the whole log, to frame 8,550, passes with more samples
(`phase5-8/launcher_prefix.py` / `.log`, `phase5-8/launcher-check-run.log`).
The page listed the branching package under Gameplay and did not list the
hidden test package. Play by hand is still the user's.

## Phase 5 change 8 (commit `141aee4`)

Step 5's spike, the user's choice: can a brand-new zone be added? Only text
is committed: the answers are in `docs/MODDING_FEASIBILITY.md` (section 6,
step 5, with "Scenes and files", the hazards in "The campaign" and section
7), and the spike's packages, scratch plugin, scripts and runs stay in the
ignored `.cache/evidence/phase5-8/`. Three scratch packages, built from the
player's disc by `make_spike.py`, ran CAMPAIGN PLAY, scripted, in all three
boot modes beside the stock build: all 14 runs passed with no miss. The
game found a new file, `P2.BIN` (S1.BIN with a short timeline), through a
directory record a package adds to S1's directory sector, with the file's
sectors in the disc's postgap, 150 zero Form 2 sectors (case A, a
`disc_raw` overlay), or appended after the disc by a scratch plugin from a
verified resource (case B); the 1ST ZONE played that file, cleared, and
wrote the result record that change 5's remix wrote. With seven `main_exe`
patches, the cut scene index 23 loaded, started and ended the zone on
psx-runtime (case C), but its title card read only "ZONE" and its pause
panel "ZO", it showed no results panel, by the music code it gets no music,
and its result record (slot 20) overwrote the first three words of the
settings block at 0x800A7D90, whose second word is the ZONE PLAY list's
selection. Its name lookup loads a word from 9 plus 4 times the language
index, never aligned, which Beetle and the console's CPU raise an address
error for and psx-runtime does not (Derived), so a new zone at index 23
needs a name. The postgap holds some extra zones' files but no campaign
zone's (every S directory holds at least 525,806 bytes). In each boot mode
every case's text-mismatch counter equals the stock run's, so the EXE
patches changed no code (Derived). Change 7's round 3 suggestions 3 and 4
were applied (`approach.py check` tests the change of side itself;
`AGENTS.md`'s remix paragraph reflowed), and the launcher check's saved
output was explained as read while its watcher was still writing
(Derived). Review: round 3 PASS on tree `0f3cf66` (staged diff
`5ca2fc2c…`), after rounds 1 and 2 NEEDS CHANGES (see Review and commit
state). The full record is in `git show 141aee4:.agent/HANDOFF.md`.

## Phase 6 change 1 (commit `0761991`)

The audit's first finding, in the Beetle driver. A separate read-only agent
audited the committed code after the user asked for solid, readable code
(`.cache/evidence/code-quality/audit-r1.md`): readable and careful, its 98
tests passing, with four bugs on inputs that neither this disc nor the
pinned psx-beetle gives; the user chose to take all of its fixes and
cleanups, one reviewed change each. The driver took the frame from the ping
it sends with each press or shot without checking the reply, so a failed
ping ended the summary in a TypeError traceback that hid the cause.
`ping_frame()` now checks every ping reply: a failed ping fails the run with
"ping failed: <reason>", and an ok reply whose frame is missing or not an
integer with "ping reply <reply> has no frame number" (round 3, after review
round 2 found that rounds 1 and 2 had turned one such reply from a clean
failure into a KeyError), so the audit's second proposal, `finish()`
surviving a missing frame, is not needed. The pinned psx-beetle always
answers a ping ok with a frame (`beetle_debug_server.c:300-305`), so only a
fake or a later build reaches this. Three tests cover a failed ping sent
alone, one sent with an event and six replies without a usable frame (18
tests); 16 planted bugs are caught; with round 3's driver every route passed
in both Beetle modes, byte-identical to Phase 4 change 1's third batch. The
checks found two problems outside the fix, each left to its own change
(Next action): a hang in both route scripts, whose SIGTERM and SIGHUP
handler can raise inside `Popen.poll()` while it holds the child's waitpid
lock, so that `stop()` then waits forever (`phase6-1/lock_leak.py`, `.log`),
and Ctrl-C's KeyboardInterrupt can do the same (Derived from the source,
not tested); and driver tests that fail now and then with a late event,
because the fake psx-beetle's frame clock runs at 300 frames a second
whether or not the driver has answered (`phase6-1/r3/suite_probe.log`).
Review: round 3 PASS on tree `7bc8c4e` (staged diff `e78cb4b5…`), after
rounds 1 and 2 NEEDS CHANGES (see Review and commit state). The Blender MCP
server, set up outside the repository at the user's request, is recorded in
`.cache/evidence/blender-mcp/setup.md`; new models still need the OMD model
format decoded. The full record is in `git show 0761991:.agent/HANDOFF.md`.

## Phase 6 change 2 observations (`.cache/evidence/phase6-2/`)

- The audit's section 4 splits the `zone_data.py` cleanup into steps: named
  tuples (step 2); named opcodes, registers and ISO 9660 offsets (3); named
  record formats and value ranges (4); splitting `gate()` (5) and
  `parse_recipe()`, `build()` and `package()` (6); and, optionally,
  modules (7). This change takes steps 2 to 4 together, since none of them
  moves code; steps 5 and 6 come next, and the three fixes after them, in
  the order the user chose.
- The baseline is in `.cache/evidence/code-quality/zone-baseline/`, moved
  from `/tmp`, which the reboots wiped. `zone_baseline.sh` records 142
  outputs of a copy of the tool from the player's disc: `list` and `check`,
  every timeline zone's dump to a file and to stdout, the zone file each
  dump builds, a build and a package of every dump kept under
  `.cache/zones/`, the stock S1 dump's package and the Crossfire recipe's.
  `baseline-head/` holds them from HEAD's tool (`head/`, equal to
  `git show HEAD:scripts/zones/zone_data.py`). Run again today, HEAD's tool
  gives the same 142 outputs (`baseline-head-now.log`), and so does the
  refactored tool: `diff -r` against `baseline-head/` finds no difference.
- `differential.py` runs HEAD's tool and the new one on the same inputs and
  requires the same result, or the same exception and message: 200,000
  random MIPS words (`control`, `destination`), 50,000 random sequences
  (`trace`), 4,000 sequences of a `lui` and one to three register moves
  with `$zero` as their first or second source (`trace`; random words
  rarely make them), 5,000 random programs with difficulty loads and
  branches (`flow`, `gate`, `describe`, `callback_span`), each of the 25
  files `list` shows, stock and 24 times with one to three words corrupted
  (`read_table`, `read_formations`, `layout`, `render`, and `build` on what
  renders), the three parsers at both edges of every range they check and
  with lists of the wrong length (`parse`, `parse_recipe`,
  `parse_formations`) and 1,980 random remix edits of the disc's 33
  formation records (`reshape`): 481,061 inputs, no difference
  (`r2/differential.log`). Round 2 added the moves, the delay's low edge in
  `parse_recipe` and the lists of the wrong length (round 1: 475,289
  inputs, `differential.log`). The inputs reach past the trivial cases: 49
  `gate` results depend on the difficulty word, 4,395 hold only on some
  paths and 556 on every path; 11,080 random sequences and 3,405 of the
  moves trace a value; every reader and parser fails on some.
- `mutations.py` plants 27 bugs, one per run, in the new names: opcodes,
  registers, field decoders, jump targets, branch targets one word early
  and one word late (added in round 2), record formats, ISO offsets, the
  two properties, the ranges and the limits. The tests fail for 24
  (`r2/mutations.log`) and pass for three: moves recognised only with
  `$zero` as the second source, a delay of 2**31 accepted, and branch
  targets one word late. Only `test_the_dump_says_when_a_call_runs` catches
  an early target, through its case where the `lw`'s base differs on two
  paths (case 15); a branch landing one word later gives the same note in
  every case. Planted in HEAD's code, the same three bugs pass HEAD's tests
  (`gaps_at_head.py`, `r2/gaps_at_head.log`), so those gaps were in the
  tests before this change. Planted in the new tool, each of them, and a
  fourth that passed review round 1's own mutations (lists of four values
  taken where three are needed), makes `differential.py` report
  differences (`gaps_differential.py`, `r2/gaps_differential.log`). Tests
  for them belong to the tests step (Next action).
- The audit's three `zone_data.py` probes still reproduce their log
  (`probes-zone.log`, equal to `code-quality/probes/probes-zone.log`): the
  latent bugs that the next changes fix are still there, as a refactor
  leaves them.
- One expression is rewritten rather than renamed: `describe()` now takes a
  `jal`'s target region from the address after the instruction, through
  `jump_target()`, as `flow()` always did, instead of from the load
  address. The two agree for any file shorter than about 267 MB (Derived);
  the largest file `list` shows, `TITLE/TITLE.BIN`, has 131,384 bytes.
- Two older evidence scripts, `phase5-7/remix_check.py` (line 90) and
  `phase5-7/remix_watch.py` (line 128), import the working tool and unpack
  `layout()` into six names, so with this change they raise a ValueError
  (review round 1). Reuse them with commit `0761991`'s tool, or unpack the
  `Layout`.
- Change 1's round 3 suggestions: 1 (`isinstance(frame, int)` accepts a
  JSON `true`) changes the driver, so it goes with the route-scripts change,
  which runs every route in both Beetle modes anyway; 2 is done (the base
  driver's traceback is kept as `phase6-1/r3/regression-base-tests.log`); 3
  (`mutation_compare.py` matches catches by test name only) belongs to the
  tests step, with a fake that waits for the driver; 4 (two line numbers in
  the round-3 request) needs no change, the passages being at lines 1432 to
  1437 and 1389 of that snapshot's file; 5 and 6 are applied (the short line
  in Next action; `AGENTS.md`).

## Phase 6 change 2 changes

- `scripts/zones/zone_data.py`: named tuples `Timeline` (call_at, address,
  waves, end; `slots`), `Part` (start, stop, label), `Layout` (timeline,
  formations, parts; `span`) and `ZoneEdit` (path, lba, stock, built).
  `read_table` returns a `Timeline`, which still equals the plain tuples the
  tests compare it with, and `layout` a `Layout` in place of its 6-tuple
  (its one test checks only its errors). Struct formats `ENTRY`,
  `POINTERS`, `PLACEMENT`, `STEP_FIELDS` and `OFFSET`, with the step and
  record sizes taken from them; ranges `S16`, `U16`, `S32`, `U32` and
  `TICK_COUNT`, checked by `in_range()` and `integers(value, count, bounds)`;
  `MAX_COUNT` and `FULL_TURN`. MIPS constants (opcodes, `SPECIAL` functions,
  registers, `JR_RA`, `SCAN_LIMIT`) and decoders (`opcode`, `rs`, `rt`,
  `rd`, `funct`, `immediate`, `jump_target`, `branch_target`, `is_call`,
  `is_move`, `address_of`, `index_of`); ISO 9660 offsets and
  `little_endian()`. Locals named `ws`, `k`, `f` and `cb` are now `code`,
  `index` or `call`, `formation` or `edit`, and `callback`. The module
  docstring, the messages and the command line are unchanged.
- Round 2, for review round 1 (Review and commit state): `Timeline.call` is
  `call_at`, an address, since `call` in `gate()` is a word index; `HI_LO`
  is `MULT_DIV`; `branch_target(word, index)` takes its arguments in
  `jump_target(word, address)`'s order; the `Layout` that `build()` reads is
  `stock_layout`, and `render()` and `cmd_list()`, which use only its
  timeline and formations, unpack it; the last formation `f` is `edit`;
  `cmd_list()`'s `waves` is `wave_count`; and two comments are reworded
  (the root directory's record, and `is_move()`'s docstring).
- `AGENTS.md`: the Beetle oracle section's list of what fails a run adds
  "or reports no frame number" (change 1's round 3 suggestion 6; the
  paragraph reflowed, its other words unchanged).
- `.agent/HANDOFF.md`: the scope; change 1 condensed; these sections; the
  review state; the next action (where the hang fix goes, the test gaps,
  round 3's short line).
- Untracked (ignored): `.cache/evidence/phase6-2/` (the baseline rerun,
  `differential.py`, `mutations.py`, `gaps_at_head.py`,
  `gaps_differential.py`, the probes' log, the checks, the snapshots, the
  review requests and reports, and round 2's logs in `r2/`), the baseline in
  `.cache/evidence/code-quality/zone-baseline/`, and
  `.cache/evidence/phase6-1/r3/regression-base-tests.log`.

## Phase 6 change 2 checks

- `python3 -B scripts/zones/test_zone_data.py`: 61 OK with the player's
  disc, the test file unchanged; pyflakes is clean; the tool's longest line
  is 99 columns.
- `zone_baseline.sh` with the staged tool: its 142 outputs and their
  `SHA256SUMS` equal `baseline-head/`, which HEAD's tool reproduces today
  (`baseline-head-now.log`).
- `differential.py` / `r2/differential.log`: 481,061 inputs, no difference
  (round 1: 475,289, `differential.log`).
- `mutations.py` / `r2/mutations.log`: the unmutated copy passes with
  nothing skipped, and 24 of the 27 planted bugs fail the tests (round 1: 23
  of 25, `mutations.log`); `gaps_at_head.py` / `r2/gaps_at_head.log` shows
  that the other three pass HEAD's tests too, and `gaps_differential.py` /
  `r2/gaps_differential.log` that each of them, and lists of four values,
  makes `differential.py` report differences (2,245, 165, 3,688 and 28 of
  them).
- `probes-zone.log`: the audit's three `zone_data.py` probes reproduce their
  log.
- Round 1, `checks-p6-2.sh` / `.log` (the staged tree): only `zone_data.py`,
  this file and `AGENTS.md` change; the `AGENTS.md` words differ from HEAD only
  by the inserted "reports no frame number, or"; the tool's docstring and
  imports, this file's header, its Phase 0 to Phase 5 change 8 sections and
  its review state up to change 1's round 2 entry equal HEAD; no
  placeholder, doubled blank line, heading without a blank line before it,
  added line over 80 columns in the Markdown files or over 99 in the tool,
  new reflow leftover or local path; the three gates pass, the pins equal
  `framework_pins.txt` and the submodules are clean; pyflakes; the four
  test files pass with nothing left behind; `--help` of the tool and of
  each subcommand equals HEAD's; the baseline, the differential, the probes
  and the mutations reproduce their logs; nothing listens on 4370 to 4389;
  and `git diff --cached --check` is clean.
- Round 2, `r2/checks-p6-2-r2.sh` / `.log` (the staged tree): round 1's
  checks, with the differential, the mutations and both gap scripts run on
  the staged tool and equal to round 2's logs; round 1's tree rebuilt from
  its frozen index entries, and the delta from it (this file and the tool;
  `AGENTS.md` unchanged since round 1); the saved report equal to session
  message 648; no `f`, `HI_LO`, `zone = layout(` or `.call` left in the
  tool; the case that catches an early branch target (case 15) and none
  that catches a late one; and no old wording outside quotations and round
  1's figures. All pass. The first run (`r2/checks-p6-2-r2-first.log`) found
  two short lines that round 2's edits left in the scope, since reflowed
  with no word changed.

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
  replays its flags open, not that completing the game writes the same flags;
  per the internals research the game's unlock rules cannot produce it
  (agent, derived: it has U1's and level B's flags, which need a HARD clear,
  but no clear flag). Its bytes are the zone flags A[0..18] and boost-level
  flags B[0..12] of the environment save, and its checksum, the 32-bit sum of
  the block's 68 words at +0x200, holds (re-checked on both card images, Phase
  5 change 1). With A[0..18] and B[0..13] all set, the unlock mod (change 2)
  opens every ZONE PLAY zone and level and every DEMONSTRATION entry
  (entries 1 to 6 are open without any flag), and a save keeps them. It sets
  both arrays at once, so which A[i] opens which zone, and whether ZONE PLAY
  needs B[value], is untested. That the game verifies the checksum is still
  the agent's static reading, not traced.
- Overlay code now runs from the static shard, except a few PCs that still go
  to the interpreter (0x80120370 in every route; 0x80135EFC in `menus`,
  `memcard` and the 13 unlocked-zone routes, 1,182 instructions in each of
  those 13; seven PCs in `title_to_zone1`; `phase3-4/probe_summary.log`,
  `phase3-5/probe_summary.log`, which show each run's top three PCs, and
  `phase3-4/r2/pc_entries.log` for 0x80120370 in `title_to_zone1`). The
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
- Modding: the open questions are in `docs/MODDING_FEASIBILITY.md`, section
  7. Its claims marked "agent" come from a research agent's static reading of
  the disc and were not re-checked, except the two flag arrays and that the
  screens follow them (change 2), the campaign loop's advance, result word
  and records (change 3), the wave timeline (change 4) and the formations
  (change 6), all marked re-checked there, and in change 8 the file lookup,
  the post-load switch, the zone slots and the record's overlap with the
  settings block. The launcher's Mods page lists the unlock package and
  turns it on (change 3), lists the branching package under Gameplay and
  does not list the hidden test package (change 7's launcher check).
- Branching prototype (change 3): with zones cleared instantly, the S path
  and the stock order hold up to the start of the 5TH ZONE in all three boot
  modes. The rest of the campaign, its end and the unlock rules after a
  reordered start are not run; the order rejoins at the 4TH ZONE and all
  nine records are written, so the end should not differ (hypothesis). The
  plugin keeps no state, so a save state taken during the reordered steps
  should resume correctly (untested). The branch under live play is
  untested. An instant clear grades the zone from the counts at that moment,
  so a clear after the player has destroyed some enemies grades between the
  zone's low grade and S. The test clear has run only in the 1ST to 4TH ZONE
  of CAMPAIGN PLAY. It cannot reach the 5TH ZONE, the LAST ZONE, U5, U9 or
  V5, which end in their own overlay code (that needs hooks there); the 8TH
  ZONE, U4 and U8 have the runner but also call the clear routine from their
  own code, and how a forced clear meets that is untested.
- Zone data tool (changes 4 to 7): the game reads the tables the tool
  decodes, in the DEMONSTRATION replays of the fourteen zones, in HLE mode
  only (change 4). Edits have run with no input in all three boot modes: in
  the 1ST ZONE in CAMPAIGN PLAY (changes 5 and 6) and, with the Crossfire
  pack, in the 1ST, 2ND, 3RD and 6TH ZONE from ZONE PLAY (change 7). Those
  runs reached each zone's last formation wave within their 80 seconds
  (entries 6, 9 or 10, 19 and 16 of 9, 14, 23 and 19); the waves after
  those under a remix and remixes played by hand are untested. The
  launcher's Mods page installed the pack, and its 1ST ZONE then ran as
  predicted in CAMPAIGN PLAY (change 7's launcher check, HLE OpenBIOS
  only). Crossfire's comments say from which side each moved formation
  comes and that it comes close; with no input that holds in every run
  (`approach.py check`). With input the player strafes and turns, so
  where those formations pass in play, what the player sees of them,
  whether they fire at the player and how hard the remix plays are
  untested. Its shorter waits may change clear times and so ratings; no
  results screen was reached or compared. That edits up to a table's end,
  which covers every formation part, keep the static shard's variants
  valid is derived for all fourteen zones from their ranges; edits after
  the table are unknown. In change 7's runs the remixed zones ran no
  overlay code in the interpreter (12 instructions, all at 0x80120370, as
  in every route); change 5's runs could not place up to 371 instructions
  before or after the 1ST ZONE's load. A remix runs only from the image
  its package names: a CHD of the same disc should hash the same (the
  runtime hashes its decoded sectors), but that is untested.
  The 8TH ZONE's table has no end entry: if its last wave were ever cleared
  before the zone's own code ends the zone, the runner would take the debug
  string after the table as an entry (Derived; never seen). Formation
  values far outside the stock ones (positions, speeds, turns) are
  untested; what flags 0x4000 and 0x8000 do and what the low flag bits do
  outside the 1ST ZONE are unknown, as is how the waves of the ten timeline
  zones without formations place their enemies. Other enemies in a
  formation need code (a plugin, or new code in the zone file). The notes on
  when a call runs come from a static analysis that evaluates no condition
  but the difficulty word and ends a path at any `jr`; no gated record has
  run with the word non-zero. Review round 3 lists synthetic shapes the
  analysis gets wrong or states loosely (`r3/review-r3.md`): an
  unconditional `b` over an epilogue placed before the call, but reached
  only after it, gives "only on some paths" for a call that always runs; a
  call reached only through a `jr` jump table is attributed to code outside
  the table's callbacks, and a branch on the word to such a `jr` that can
  return to the call gets a definite note; where the word decides through a
  `bgtz`, a join or a load in a delay slot, the note says "only on some
  paths". The gate test pins two such conservative notes, for a `bltz` and a
  `blez` on the word (cases 6 and 7), which would change if the analysis
  evaluated those branches (change 6's round-4 review). None of these shapes
  is in the four zones: the 30 callbacks that reach the 33 calls use only
  `beq` and `bne` against zero, `j`, `jal` and `jr $ra`
  (`r4/callback_inventory.py` / `.log`), and the reviewer's own
  path-sensitive model, which follows the word through joins and delay
  slots and resolves branches whose outcome is fixed, agrees with every
  note. Fixing them is deferred.
- New zones (change 8's spike): a file added to the disc loads, and index
  23 starts and ends a zone, in all three boot modes of psx-runtime with no
  input, under scratch packages; nothing of it is committed. On Beetle and
  a console, index 23's name lookup would raise an address error exception
  at the title card (Derived from the EXE and Beetle's source; case C never
  ran there, since psx-beetle runs no mods), and what the exception handler
  then does is unknown. Why index 23 shows no results panel or HUD after
  its clear is not traced. That its result record moves the ZONE PLAY
  list's selection is derived from TITLE's code and untested; that it gets
  no music is derived from the music code. Whether Beetle or a console
  reads data sectors with zero error-correction bytes is a hypothesis. A
  zone file longer than the stock one, a whole zone with its own data,
  play by hand and the other indexes whose files are missing (slot -1) are
  untried. What the settings block's first word does is unknown.
- Framework observation (change 8's review): psx-runtime raises no
  exception for a misaligned load. This build's generated code checks no
  alignment (it never calls `psx_unaligned_access`), and
  `psx_cyc_load_word`'s main-RAM path copies the four bytes with `memcpy`
  (`psxrecomp/runtime/include/psx_cyc.h:253-255`), where the R3000A and
  Beetle raise an address error. The recompiler's strict translator does
  emit alignment checks (word loads at
  `psxrecomp/recompiler/src/strict_translator.cpp:1061`, word stores at
  `:1240`), but they call `psx_unaligned_access`
  (`psxrecomp/runtime/src/traps.c:1090`), which halts the run through
  `trap_crash` (`:211-218`) rather than raise the guest's exception, though
  its own comment calls the fault survivable (`:1091`): `trap_crash` calls
  `psx_fatal_halt`, which exits or, with a debug listener, serves
  post-mortem queries forever (`psxrecomp/runtime/src/crash_trace.c:848-885`).
  An upstream report should mention that contradiction too (change 8's
  round 3 suggestion 1). Whether stock play ever makes such a load is
  unknown. A fix would be a framework change, arriving through a reviewed
  pin bump; it is recorded here for later, not pursued.

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
  counts) is adopted in the change 4 section above. Naming the last two
  interpreted `title_to_zone1` PCs (0x80126160 and 0x801261AC, from the
  reviewer's own round-1 probe, reported in round 2) stayed deferred until
  Phase 5 change 5, whose runs play that route's input for its whole 7,674
  frames (the same first 12 steps, then neutral input in both) and whose
  samples name both (`phase5-5/r2/pc_rows.log`).
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
  ignoring SIGINT during the runner's cleanup, and a lock file for one
  runtime per build (the PC naming deferred here too was closed in Phase 5
  change 5).
- Phase 4 change 1: round 3 PASS on tree `7598286` (staged diff `3c600242…`)
  with no findings, after round 1 NEEDS CHANGES on tree `9706929` (six Low:
  when Beetle saves the cards, zone 7's differing pixels, U1's mid-replay
  results screen, the results claim's coverage, the prototype's failures, the
  commit message) and round 2 NEEDS CHANGES on tree `9d7f44a` (two Low: five
  SCORE BONUS pairs recorded as still counting, the light sweep's share of
  zone 7's pixels); commit `6d0a173`, pushed to the private `origin/master`.
  Reports: `phase4-1/review-r1.md`, `phase4-1/r2/review-r2.md`,
  `phase4-1/r3/review-r3.md`. Deferred: tests for the driver's
  connect-too-late and reply-id checks (each needs a new fake behaviour; the
  next driver change), and a finer shot cadence where a replay shows a
  mid-replay results screen (a route change). The full entries are in
  `git show a005f9e:.agent/HANDOFF.md`.
- Phase 4 change 2: round 2 PASS on tree `58a89e7` (staged diff `c0135069…`)
  with no findings, after round 1 NEEDS CHANGES on tree `2180832` (five Low:
  the session's card save, which interpreter rows the watcher kept, the trace
  sentence, the launcher's Quit writes, two numbers); commit `a005f9e`,
  pushed to the private `origin/master`. Reports: `phase4-2/review-r1.md`,
  `phase4-2/r2/review-r2.md`. Round 2's four wording suggestions are applied
  in the change 2 section above. The comment on #721 that round 1 left to the
  user was posted (Phase 5 change 1 observations).
- Phase 5 change 1: round 2 PASS on tree `034e6be` (staged diff `fa055e21…`)
  with no findings, after round 1 NEEDS CHANGES on tree `03d7a5f` (three Low,
  all in the doc: the persistence claim ignored that option values persist
  in `mods/state.toml`; "cannot carry code" misstated a citation that says
  native code; the GameFAQs comparison had no saved source); commit
  `390a09b`, pushed to the private `origin/master`. Reports:
  `phase5-1/review-r1.md`, `phase5-1/r2/review-r2.md`. Round 2's five
  wording suggestions were applied in change 2: four in the doc, one in the
  change 1 section above.
- Phase 5 change 2: round 1 PASS on tree `6a7d573` (staged diff
  `180a2cf5…`) with no findings; commit `9500812`, pushed to the private
  `origin/master`. Report: `phase5-2/review-r1.md`. Its six wording
  suggestions were applied in change 3: `--out` and the copy's location in
  `AGENTS.md`'s feature-on recipe; the DEMONSTRATION and per-index scope of
  the unlock claims (hypotheses above); the 64 writes recorded as derived;
  "commonly do not carry" a loose EXE; the `EXTRAS_SOURCES` placement
  reason; "still says" in the change 1 section. Its limitation, the
  launcher, was closed by change 3's launcher check.
- Phase 5 change 3: round 2 PASS on tree `aeccb7e` (staged diff
  `cc2fcbf3…`) with no findings, after round 1 NEEDS CHANGES on tree
  `6a643ec` (one Medium: the 8TH ZONE, U4 and U8 also call the clear routine
  from their own code, and the test clear had been claimed for every runner
  zone; three Low: the doc's record bullet still marked "agent", a citation
  one line off, and "the whole host stopped"); commit `b2e4e6a`, pushed to
  the private `origin/master`. Reports: `phase5-3/review-r1.md`,
  `phase5-3/r2/review-r2.md`. Round 2's suggestions: "for at least the gap
  minus 4 s" in `AGENTS.md` (applied in change 4); two short lines left by a
  reflow in this file (gone with the condensed sections); the commit
  draft's verdict (filled in the commit).
- Phase 5 change 4: round 2 PASS on tree `645c1b9` (staged diff
  `b704cfd7…`) with no findings, after round 1 NEEDS CHANGES on tree
  `180c490` (one Medium: most wave callbacks were said to call 0x80057F0C,
  but only four zones' files do, and the runner's children were called
  groups though 0x80063C5C's timers are children too; two Low: the 6TH
  ZONE's extra results shot, and no test isolating `end = false` over a
  stock end entry); commit `b19fbe4`, pushed to the private `origin/master`.
  Reports: `phase5-4/review-r1.md`, `phase5-4/r2/review-r2.md`. Round 1's
  entry here listed "the file-end bound" among the caught mutations; the
  planted one covered the table address's bound, and the read loop's bound
  had no test until change 5 added one. Round 2's four suggestions were
  applied in change 5: that correction, the 17-entry count, the short line,
  and the doc's "timing and placement" sentence.
- Phase 5 change 5: round 3 PASS on tree `29e0e44` (staged diff
  `35b66fc5…`) with no findings, after round 1 NEEDS CHANGES on tree
  `f3967fd` (three Low: data-only edits called re-checked though only the
  table was; the interpreter comparison named seven addresses where the
  probes keep five rows; no test packaged a shorter table) and round 2
  NEEDS CHANGES on tree `85d92ee` (one Low: "the last few instructions"
  understated the count's last step, up to 371); commit `bdd413f`, pushed to
  the private `origin/master`. Reports: `phase5-5/review-r1.md`,
  `phase5-5/r2/review-r2.md`, `phase5-5/r3/review-r3.md`. Round 3's two
  suggestions are applied in change 6: the short line left by a reflow in
  the zone data hypothesis (rewritten), and a test of `build` and `package`
  with an output path that is not valid UTF-8.
- Phase 5 change 6, round 1: NEEDS CHANGES on tree `8b81d1d` (staged diff
  `b7a9f818…`; one Medium: five records start on only one value of the
  difficulty word, and the doc and this file said a 3RD ZONE callback starts
  four formations; three Low: no test for an unaligned record or zero steps;
  the doc's wave 2 sentence left out its result; the reflow of change 5's
  hypothesis dropped its interpreter limitation). The reviewer reproduced
  the remix runs in two boot modes. Report: `phase5-6/review-r1.md`. All
  four are resolved and its seven suggestions adopted (changes, round 2).
- Phase 5 change 6, round 2: NEEDS CHANGES on tree `fe799fe` (staged diff
  `24447efa…`; two Low, both about round 2's `gate`: its stated contract was
  broader than its checks, silent for other branch kinds and wrong after a
  call, on a short-circuit OR and past an early return; and its tests
  exercised only `beqz`), after confirming round 1's four findings and
  seven suggestions resolved. On the disc every note was right, by the
  reviewer's own control-flow analysis of all 33 calls. Report:
  `phase5-6/r2/review-r2.md`. Both are resolved and its six suggestions
  adopted (changes, round 3).
- Phase 5 change 6, round 3: NEEDS CHANGES on tree `f944f75` (staged diff
  `c8c391f4…`; one Low: no test pinned the rules that keep the analysis
  from stating a wrong condition, so five planted bugs that give wrong
  notes, four of them definite, passed all 49 tests), after confirming
  round 2's two findings and six suggestions resolved. On the disc the
  reviewer's own path-sensitive model agrees with every note. Report:
  `phase5-6/r3/review-r3.md`. Resolved; two of its five suggestions are
  adopted and three deferred (changes, round 4; hypotheses).
- Phase 5 change 6, round 4: PASS on tree `aba593e` (staged diff
  `3dd57240…`) with no findings, after confirming round 3's finding resolved
  and its suggestions' dispositions accurate; the reviewer checked each new
  case's note against its own path-sensitive model and ran each planted bug
  against the case written for it. Commit `88e0268`, pushed to the private
  `origin/master`. Report: `phase5-6/r4/review-r4.md`. Its three
  suggestions are applied in change 7: a test case for `bgtz`, the one
  branch kind the analysis follows that no test covered; and, in the
  hypotheses, the `bltz` and `blez` cases' conservative notes and the shape
  of a `b` over an epilogue placed before the call.
- Phase 5 change 7, round 1: NEEDS CHANGES on tree `673549e` (staged diff
  `3da54354…`), from a fresh reviewer that recomputed the snapshot, applied
  the recipe from the record layout on its own (no byte differs from the
  tool's build), re-derived yaw's direction and pace's ticks, re-ran the
  checks and re-read the runs. Report: `phase5-7/review-r1.md`. F1
  (Medium): 8 of the 14 turned formations never came within 26,000 units
  of the player, so the recipe, the pack's description and the doc said
  wrongly that they attack from behind. F2 (Low): the handoff gave the
  player's speed about five times too high. F3 (Low): an empty recipe name
  was accepted, which the framework refuses. F4 (Low): an integer beyond
  float range raised a traceback. Resolved: F1, the eight retuned with a
  flight model checked against the runs, the zones re-run and the recipe's
  claims checked in the runs (`approach.py check`); F2, the speed
  corrected; F3 and F4, refused, with tests and planted bugs. Of its seven
  suggestions: the three test gaps are closed, each with a planted bug;
  spread of 0 or less and a pace that leaves a first step 0 ticks are
  refused; the yaw wording is adopted; the 6TH ZONE's left formation is
  redesigned, so the wording it proposed for it no longer applies; the
  first remix check's failures are described sample by sample; the
  closest-approach check is `approach.py check`; the host Python (now
  3.14.8; `AGENTS.md` says 3.14.7) is left to a toolchain refresh with a
  rebuild, as the other tools may have moved too.
- Phase 5 change 7, round 2: NEEDS CHANGES on tree `3e9f932` (staged diff
  `132d90f8…`), from a fresh reviewer that confirmed round 1's four
  findings resolved: it recomputed the claims, re-ran the claims check on
  both rounds' runs, checked the flight model and the retuned values,
  applied both recipes from the record layout on its own (the same bytes as
  the tool's, ties to even), fed the new torn-read rule synthetic rows and
  ran the refusals on the command line. Report: `phase5-7/review-r2.md`.
  F1 (Low): the run record said only the recipe changed after the runs,
  but the tool had too, and nothing recorded what. Resolved:
  `tool_at_runs.py` shows that only the tool's docstring paragraph and the
  recipe's header comment changed (it rebuilds both run-time hashes), and
  the handoff and commit draft say so. Its suggestions, all taken:
  `approach.py compare` takes a recipe, and the checks reproduce round 1's
  comparison with round 1's recipe (`remix_check.py` checks only the
  current runs, so it keeps the committed recipe); `design-try.log` (from
  `design_try.sh`) holds the trials behind the three designs `design.log`
  lacks; an "across" claim now also needs the start side and a crossing
  behind the player; the recipe header, the docstring and `AGENTS.md` are
  reworded, the handoff says where the 1ST ZONE's first formation is first
  seen, and the docstring says ties round to even. The reviewer saw
  `test_beetle_route` fail once while its own scripts ran; three isolated
  re-runs passed, and the file is unchanged by this change.
- Phase 5 change 7, round 3: PASS on tree `ad268a4` (staged diff
  `aaa58aa5…`) with no findings, from a fresh reviewer that rebuilt the
  run-time tool and recipe from the staged files (their hashes are the
  runs', and their code and data the staged ones), re-ran the checks script
  and re-analysed the runs' watch logs. Commit `feb71aa`, pushed to the
  private `origin/master`. Report: `phase5-7/review-r3.md`. Of its five
  suggestions, the two on the commit draft's wording and the one on
  `snapshot-r3.sh`'s header were applied before the commit. Suggestion 3
  (`approach.py check` should test the change of side itself) and
  suggestion 4 (round 2's wording left in this file's change 7 sections,
  and `AGENTS.md`'s remix paragraph ending on a one-word line) are applied
  in change 8: the check is rewritten, the condensed change 7 section
  replaces those sections, and the paragraph is reflowed. Rebuilding round
  2's tree, the reviewer refreshed the times of 18 loose tree objects in
  `.git/objects`; their content is unchanged.
- Phase 5 change 8, round 1: NEEDS CHANGES on tree `7cb1a3a` (staged diff
  `4c56035f…`), from a fresh reviewer that re-read the claims against the
  disc, the runs and the pinned source and re-ran `checks-p5-8.sh` (its log
  reproduced byte for byte). Report: `phase5-8/review-r1.md`, saved from
  OpenCode's session database after this conversation was compressed. The
  findings, each checked in the disassembly or the sources and resolved in
  round 2: F1 (Medium), index 23's name lookup is a misaligned load that
  Beetle and the R3000A raise an exception for and psx-runtime does not, so
  case C holds on psx-runtime only and a name becomes a requirement; F2,
  the slot rule is at 15 places, not 16 or more, and the index's 42
  references are 30 loads, 2 stores and 10 that form its address; F3, the
  settings block's second word is the ZONE PLAY list's selection, so index
  23's record moves the selection rather than choosing the zone ZONE PLAY
  starts; F4, the postgap holds some extra zones' files
  (`r2/dir_totals.log`); F5, the switch's exit entries had lost their label
  (now listed in full and re-checked); F6, no pack is committed.
  Suggestions 1 to 8 and 10 are applied; 9 (psx-runtime's missing exception
  for a misaligned load) is recorded in the hypotheses.
- Phase 5 change 8, round 2: NEEDS CHANGES on tree `097a63c` (staged diff
  `9987d4a3…`), from the same reviewer, which found all six round-1
  findings resolved and recomputed every fact the fixes rest on. Report:
  `phase5-8/r2/review-r2.md` (session message 1263). One Low finding,
  made by round 2's own fix: step 5 still called the 1ST ZONE record's
  clear time "333 frames" after the doc had given that field's unit as
  1/30 s. Round 3 fixes it and applies all five suggestions (see the Round
  3 changes bullet). The report gives U7's sound bank as the 8TH ZONE's
  (S8); S8 is the 7TH ZONE's directory, and the doc says so. Its run of
  the round-2 checks matched the saved log except at the saved-report
  step, where `r2/review_text.py` read the session's newest message, by
  then one of the reviewer's round-2 messages, and raised IndexError.
- Phase 5 change 8, round 3: PASS on tree `0f3cf66` (staged diff
  `5ca2fc2c…`) with no findings, from the same reviewer, which re-ran the
  round-3 checks (its log byte-identical), re-read every 333 in the doc,
  read the sound-bank table from the EXE, and corrected its own round-2
  report (S8 is the 7TH ZONE's directory, as the doc says). Commit
  `141aee4`, pushed to the private `origin/master`. Report:
  `phase5-8/r3/review-r3.md` (session message 1473). Its two suggestions
  are taken up in Phase 6 change 1: the framework observation in the
  hypotheses now notes that `psx_unaligned_access`'s comment calls the
  fault survivable while the function halts the run; and the round-3
  checks bullet's "both doc mentions of the clear time give its unit" was
  loose (the doc names the unit, 1/30 s, in "Scenes and files" and "The
  campaign", while step 5 gives the time as 333 and 0:11.10), which the
  condensed change 8 section, replacing that bullet, no longer says.
- Phase 6 change 1, round 1: NEEDS CHANGES on tree `6915986` (staged diff
  `7ee8f7d7…`), from a fresh read-only reviewer that found the fix, its
  tests and `AGENTS.md` correct: it re-ran the tests, the regression, the
  mutations and the batch comparison (all as recorded), hashed the batch's
  outputs itself, and made three Beetle runs of its own, identical to the
  third batch once the output directory and port were normalised. Report:
  `phase6-1/review-r1.md` (session message 865). Two Low findings, both in
  this file: F1, the record of the checks' final run left out the extra
  failing test its log shows and said the extra failures happened once; F2,
  nothing recorded that the audit's second proposal, a missing frame in
  `finish()`, was left out. Round 2 records both (observations).
  Suggestions 1 (no test failed a lone ping, so a mutation that skips
  `ping_frame` in `Beetle.frame()` passed), 2 (the per-ping wording), 3
  (Ctrl-C opens the hang's window too) and 4 (the iso probe wrote outside
  the checks' scratch) are adopted; 5 (`ping_frame` refusing a reply
  without an integer frame) changes the driver, so round 2 left it, with
  F2's proposal, to the route-scripts change, which runs every route in
  both Beetle modes anyway.
- Phase 6 change 1, round 2: NEEDS CHANGES on tree `32da4f3` (staged diff
  `91c5cbc9…`), from the same reviewer, which found both round-1 findings
  and suggestions 1 to 4 landed and re-ran the round-2 checks (its log as
  recorded, but for timings). Report: `phase6-1/r2/review-r2.md` (session
  message 1128). One Low finding: the F2 bullet said an ok ping reply
  without a usable frame still ended in a traceback, as at the base, but a
  missing frame sent with only a press failed cleanly at the base and
  raised a KeyError in rounds 1 and 2 (the reviewer ran both drivers on all
  six such replies). Round 3 makes `ping_frame` refuse those replies
  instead (changes). Its suggestions: 1 (only `ping_frame` refusing a reply
  without an integer frame turns all six into clean failures) is what round
  3 does; 2 ("failed spuriously under load" stated as fact what the
  observations call a hypothesis) and 3 (the reviewer's three Beetle runs
  matched the third batch only once the output directory and port were
  normalised) are applied.
- Phase 6 change 1, round 3: PASS on tree `7bc8c4e` (staged diff
  `e78cb4b5…`), from the same reviewer, with no findings: it ran the six
  replies against the staged driver and two mutated copies, re-ran the
  checks script and hashed all 1,588 entries of the new batch against the
  third batch. Report: `phase6-1/r3/review-r3.md` (session message 1416).
  Commit `0761991`, pushed to `origin/master`. Its six suggestions are taken
  up in change 2 (observations): 2, 5 and 6 applied, 4 answered, 1 (refusing
  a JSON `true` as a frame) left to the route-scripts change and 3 (matching
  mutation catches by reason) to the tests step.
- Phase 6 change 2, round 1: NEEDS CHANGES on tree `a17bef3` (staged diff
  `5471e1f4…`), from a fresh read-only reviewer, which found the code
  behaviour-preserving: it re-ran the checks script and compared HEAD's
  module with the new one in its own harness (struct formats, every range at
  both ends, 360,960 decoded words, the jump and branch targets, `flow` and
  `gate`, 63,595 traces, every message template), finding no difference.
  Report: `phase6-2/review-r1.md` (session message 648). Two Low findings,
  both in this file and the commit draft: F1, `differential.py` did not
  cover the `move` gap, as this file said it did (with that bug planted it
  reported no difference); F2, three smaller overstatements: no planted bug
  touched `branch_target()`, `parse_recipe` was never tried at the delay's
  low edge, and one formation `f` kept its name. Round 2 adds register moves
  to the differential, which now reports that bug; plants branch targets
  one word early and one word late, of which the tests miss the late one, a
  third gap that HEAD's tests miss too; gives the parsers the delay's low
  edge and lists of the wrong length; and renames the `f` (observations,
  changes). Its suggestions: 1 (more gaps for the tests step) is in the next
  action; 2 (`branch_target`'s argument order), 3 (`MULT_DIV`), 4
  (`stock_layout`) and 5 (four small names and wordings) are applied; so is
  6 (this file: the gaps phrased as bugs, the Ctrl-C path's label kept, the
  scope bounded by the file size, the two Phase 5 scripts).
- Phase 6 change 2, round 2: pending delta re-review.

## Next action

After a PASS: commit and push. Then the rest of the code-quality work the
user chose (`.cache/evidence/code-quality/audit-r1.md`; its section 4 gives
the order and section 5 what must not change), each step its own reviewed
change, and each `zone_data.py` step proven against the baseline in
`code-quality/zone-baseline/` and with `phase6-2/differential.py`:
splitting `gate()`, then `parse_recipe()` (which should also stop changing
its input), `build()` and `package()` (which should take its text from its
callers), and perhaps modules for the disc reader and the MIPS analysis;
the three fixes (register values traced across a join, a "calls nothing"
note for a callback that returns before the formation it starts, a
traceback on a malformed directory record; the probes in
`code-quality/probes/` reproduce each); the route-script hang (below),
which the user placed just before the next step; one module for what the
two route scripts share, with smaller `main()` functions and with
`ping_frame` refusing a JSON `true` (change 1's round 3 suggestion 1), then
every route in the three runtime modes and the two Beetle modes; test
helpers (the driver tests' fake psx-beetle runs its frames on a free 300 Hz
clock, so while the host is busy a test now and then fails with a late
event, see change 1; the fake could wait for the driver except in the tests
about lateness, `test_output_directory_rules` should print the driver's
output when a run fails, `mutation_compare.py` could match catches by
reason, and `test_zone_data.py` misses three bugs that change 2 planted
(moves recognised only with `$zero` as the second source, a delay of 2**31
accepted, branch targets one word late) and others that change 2's review
round 1 found: lists of four values taken where three are needed (by its
reading a `struct.error` traceback, not run), the low edge of 16-bit signed
fields and the high edges of 16- and 32-bit unsigned ones, a record size
without its pointers, the destinations of `cfc`, `mfc2`, `lui` and `lwr`,
`or` moves, `jalr` in `is_call()` and `control()`, and the order of `blez`
and `bgtz`; `differential.py` reports the first four); names for the C
plugins' registers (the same object code). For new zones (the
doc's section 6, step 5), the candidates: a plugin that gives index 23 a
name (required, see the hypotheses), a result record that overwrites
nothing, a results screen and music; or a new zone in an existing zone's
slot, a new file reached through a new directory record as in the spike's
case A, which keeps that slot's name, results and music. Either way, the
zone's own code means cloning an existing zone's code with new tables,
which needs a MIPS toolchain and a map of the EXE functions that zones
call. New models or textures need the OMD model format decoded first (the
doc's section 7); the Blender MCP server is set up for making them. For
zone data: how the ten timeline zones without formations place their
enemies; other enemies in a formation (code); rating thresholds; a remix
checked against psx-beetle with a patched disc image. Branching follow-ups
stay open: branches into the extra zones (each needs its result record
redirected or protected, see the doc's hazards); a test clear for the
zones that end in their own code; a committed feature-on route (a runner
option for a run directory with its own `mods/state.toml`); a whole
campaign with instant clears, which would also show whether the spike's
post-credits halt happens with every zone loaded.

The checks also found a hang outside the audit, in both route scripts (see
change 1), and the user placed its fix just before the route-scripts
refactor. One way to fix it: the signal handlers, SIGINT's too, only record
the signal, and the scripts' loops raise SystemExit when they see it, so no
exception starts inside `Popen.poll()`; `test_sigterm_stops_beetle` should
also kill a driver that outlives its wait, as the runner's test does. Like
any change to those scripts, it needs their tests and every route in the
three runtime modes and the two Beetle modes.

The user can play Crossfire: start a session with `play/play.sh <session
dir> <SCPH-1001 dump>` (in `.cache/evidence/phase4-2/`), press "Install
.psxmod" on the launcher's Mods page, paste the full path of
`.cache/play/remixes/omega.remix.crossfire-1.0.0.psxmod` into the file
picker, tick "Omega Remix: Crossfire" (group Remix) and press PLAY.
CAMPAIGN PLAY then plays the remixed 1ST, 2ND and 3RD ZONE, the stock 4TH
and 5TH and the remixed 6TH; with "Unlock All Zones and Boost Levels" also
on, ZONE PLAY offers each directly. The user's notes can retune the
recipe: edit its numbers, run `remix` with a new version and install that.
The Flydigi pad in X-input mode needs `sudo modprobe xpad` again after each
reboot (the `xone` package blacklists `xpad`).

Play continues from the play copy: `play/play.sh <session dir> <SCPH-1001
dump>` (in `.cache/evidence/phase4-2/`) refreshes `.cache/play/build/` from
`build-dev/`, runs the windowed game there with its own `game.toml` and with
persistent cards in `.cache/play/memcards/`, and watches the debug server. The
play copy's settings still select bilinear filtering; the user's choice,
Nearest, is set in the launcher. Still unreached: CAMPAIGN PLAY zones 5 to 8
and LAST, the ending and credits (the spike reached the ending and credits
only by rewriting the campaign script, and its post-credits halt is
unexplained), TRAINING lessons, ZONE PLAY's zones other than the four change
7 started, SAVE REPLAY and LOAD REPLAY. psxrecomp #719, #720 and #721 are
open upstream; any fix arrives through a reviewed pin bump. Independent
changes: harvesting misses with `psxrecomp/tools/collect_game_misses.py`
(none so far); finding why Beetle reaches screens later than psx-runtime
(for example by comparing when each CD read completes).

The host's clang is now 23.1.3 and its Python 3.14.8, where `AGENTS.md` says
23.1.1 and 3.14.7. Refresh that line with the next rebuild, after checking
whether emitters built with the newer clang change the static shard's audit.

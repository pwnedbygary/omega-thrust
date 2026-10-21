# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison. Phase 5, at the user's
request, is modding: unlocks, branching, new levels, and later perhaps a fan
sequel or remake that borrows Colony Wars' free-roaming structure.

Current iteration, Phase 5 change 3 (the branching campaign prototype the
user chose, step 2 of `docs/MODDING_FEASIBILITY.md` section 6), round 2.
Invariant: two game-owned packages, both off by default, select trusted
instruction plugins linked through `EXTRAS_SOURCES`, at two sites now listed
in `game.toml` `[recompiler] mod_instruction_sites`. Regenerating adds the
hook calls to two game shards and records the new `game.toml` in the static
overlay audit; the shard's C is unchanged. `omega.gameplay.branching`
(feature `branching`, "Branching Campaign (prototype)") hooks the campaign
loop's step-limit check (0x8002FB2C). With an S grade on the 1ST ZONE the
campaign plays the 3RD ZONE, then the 2ND ZONE, MOVIE IM 0 and the 4TH ZONE;
with any other grade it keeps the stock order; every zone is played once.
The hidden test package `omega.debug.zone-clear` (feature `zone-clear`)
hooks the zone timeline runner (0x80071558) and ends a zone that uses it
through the game's own clear path once the player is in play, graded low
with nothing destroyed (D, or B in the 1ST ZONE) and S with its option
`all-destroyed`; it has run in the 1ST to 4TH ZONE of CAMPAIGN PLAY only.
Checked in all three boot modes from copies of the build with their own
`mods/state.toml`: the S path with both on, and the stock order with low
grades and with S grades while branching is off.
With both off, all 22 committed routes pass in all three modes with the same
overlay counts as before. `AGENTS.md` documents both packages, the hook-site
rule and the audit's blind spot for instruction-only plugins, and adds `--out`
and the copy's location to the feature-on recipe (change 2's first review
suggestion). The doc records step 1's launcher check, step 2's results and
the campaign facts checked on the way. This file records change 2's PASS and
commit `9500812`, the launcher check and change 2's other review suggestions,
and condenses change 2. Round 2 resolves review round 1's findings: the 8TH
ZONE, U4 and U8 also call the clear routine from their own code, now recorded
from a saved script, and every claim about the test clear is limited to the
zones it ran in; the doc's record bullet is marked re-checked; a citation and
the host-stall wording are corrected. Baseline: `9500812`. Out of scope: the
zones that end outside the shared timeline (5TH, LAST, U5, U9, V5) for the
test clear, and runs of the test clear in other zones; branches into extra
zones (the result-record hazard in the doc); the whole
campaign and its end under the branch; runner, driver, route and test
changes; a committed feature-on route; framework and submodule changes; play
sessions; CI, packaging.

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

## Phase 5 change 3 observations (`.cache/evidence/phase5-3/`)

- The launcher check change 2 left open (`launcher/`; 2026-10-21, before this
  change's edits). The recomp-ui launcher ran on a private Xvfb display from
  a scratch copy of `build-dev` (binary `64f65d9d2f0a…`, no `settings.toml`
  or `mods/state.toml`, its own `game.toml`), driven by xdotool clicks and
  screenshots. Its Mods page lists "Unlock All Zones and Boost Levels" under
  Cheats, unticked, with the manifest's description, version and author.
  Ticking it writes nothing until the launcher closes. PLAY wrote
  `mods/state.toml` (format 2) with the feature enabled, and the game it
  started (HLE OpenBIOS) reported 64 plugin writes, the last at frame 422 as
  in the headless runs, A[0..18] and B[0..13] set, A[19] and B[14..19]
  clear, and no miss (`queries.log`, `shots/`). The launcher also wrote its
  files and `multitap_analog` into the copy, as `AGENTS.md` says;
  `build-dev` and tracked files were untouched.
- The campaign loop, the results code and how a zone ends, read from the
  disassembly (`dis_excerpts.sh` / `dis-excerpts.txt`, which rebuild it from
  `disc/SCUS_944.49`; all 529 lines equal the same ranges of the spike's
  listing, saved as `spike-excerpt.txt`). The doc's "The campaign" now gives
  the addresses. In short: the loop keeps the script pointer in $s0 and the
  step in $s1 and reaches the step-limit check at 0x8002FB2C only after a
  step whose result word is 0 or 1, with both already advanced; the results
  code writes a zone's record only while 0x800A7950 is 0 (campaign mode, by
  the agent's reading) and grades the rating 0 (S) to 4 (D), against a start
  value of 6; the destroy ratio is 0 while no enemy has spawned
  (0x80057268); and a zone ends through 0x80034104, which the shared
  timeline runner calls 90 frames after an empty entry.
- Which zones reach that routine, and how (`clear_callers.py` /
  `clear-callers.log`; it counts, in every scene `.BIN` and the EXE, the
  `jal` to the routine and to the runner's constructor, `j` to the routine
  and data words holding its address, and checks each call's argument; the
  scene-to-file map comes from the EXE's path table, and the campaign script
  ties scene 10 to step 12, the 8TH ZONE). Zones 1 to 4, 6 and 7, U1 to U3,
  U6 and U7 call the runner's constructor once and the routine never. The 8TH
  ZONE (`S9.BIN`), U4 and U8 call the constructor once and also call the
  routine from their own code: one, two and one calls (S9 +0x15AC8, U4
  +0x4830 and +0x5118, U8 +0xA460). The 5TH ZONE, the LAST ZONE, U5, U9 and
  V5 call it once and have no runner. The EXE's only call is the runner's
  (0x80071604); every call passes the player pointer from 0x8009C064, and no
  file has a `j` to the routine or a data word holding its address. Round 1
  said only the five zones without a runner call it themselves; its log
  (`clear-callers-first.log`, from an unsaved command) listed only those
  five and the 1ST ZONE.
- Zone state in play (`explore/state-tz1.log`, from `title_to_zone1` in HLE
  mode, logged by an earlier `probe_state.py` without the grade and counter
  columns): scene index 3, the player object at 0x80134124 in state 0 at
  load and 3 in play, 0x800A794A counting enemies spawned (5, 10, 15, 20, 26
  by frame 7,534) and 0x800A794C kills (0, since the route does not fire).
- Instruction hooks at the pin: registration and contract in
  `mod_plugins.h:46-55` and `MOD_PACKAGES.md:964-979`; sites must be aligned
  main-RAM addresses (`recompiler/src/config_loader.cpp:1712-1721`); the
  generator emits `psx_mod_instruction(cpu, address, word);` before the
  instruction (`code_generator.cpp:918-924`), and that call returns at once
  while no active plugin hooks an instruction (`mod_runtime.cpp:2489-2491`).
  The sites enter `overlay_codegen_config_hash` (`config_loader.cpp:82-83`),
  which names the runtime's overlay cache (`main.cpp:15028-15030`). The
  plugin audit lists registered ids without instruction or save-state
  plugins (`mod_packages.cpp:1578-1585`), while plan resolution counts them
  (`:1496-1502`).
- Regenerating (`generate1.log`, `generate2.log`): two shards changed and the
  total went from 2,371,078 to 2,371,081 lines. `_03` gets the call in both
  of its copies of block 0x8002FB28 (the campaign loop's code is emitted in
  two generated functions), `_26` once before 0x80071558. The static step
  rebuilt the shard (25 of 25 images verified, 34,846 variants in 26 files)
  with every C file unchanged; the audit changed only in
  `game_toml_sha256`, the configuration part of `cache_tag` (`gcc15c8ed0` to
  `gc9265efab`), `recipe_input_sha256` and `generation_inputs_sha256`. The
  second run printed "0 updated" and `RESULT_STATIC=reused`, and
  `generated/` was identical. The submodule shows only the ignored
  `overlay_codegen_hash.h`.
- Builds (`build-dev-first.log`, `build-dev.log`, `build-release.log`):
  `build-dev/Omega_Thrust` is `da70e6c0dd92…` (it was `64f65d9d2f0a…`),
  `build-release/Omega_Thrust` `943fb8039b6f…`. The rebuild after the
  zone-clear plugin's comment and manifest description changed compiled that
  one file and gave the same binary. So did reflowing five lines of the two
  plugin sources to 80 columns, with no other change, after the first checks
  run flagged them: both files compiled again and both builds gave the same
  binaries (`build-dev-reflow.log`, `build-release-reflow.log`,
  `reflow-binaries-*.sha256`). Both builds link both plugins (`nm`),
  stage both new manifests unchanged, and warn only in `stb_image.h`. The
  audit passes with 9 manifests, 9 declared ids and 7 registered ids: the two
  instruction plugins are not counted (`plugin-audit-dev.log`).
- Exploration (`explore/`, HLE, branching on and S clears, 45 cycles of a
  shot and a Cross press after CAMPAIGN PLAY): scenes 3, 5, 4, then 6 after
  MOVIE IM 0, then 7, with COMPLETED screens reading CLEAR TIME 0:05.03 and
  similar, DESTROY RATIO 100% and RANK S (100pts)
  (`explore-s-sheet1.png`). The clear never fired in the 5TH ZONE: the
  player stayed in state 3 until killed, GAME OVER counted down its
  continues, and a per-zone summary followed.
- Feature-on runs (`branch_runs.sh` / `.log`, `runs/`, `branch_summary.py`
  / `.log`): the scratch route `branch_check.json` (`gen_branch_check.py`:
  CAMPAIGN PLAY as in `title_to_zone1`, then 32 cycles of a 300-frame wait
  with a shot and a 6-frame Cross press; 109 steps, 15,726 frames), run by
  the committed runner from copies of the build (`mod_view.sh`), with
  `probe_state.py` logging the scene index, the player's state, the zone 1
  to 4 grades and the plugin counters from RAM. All nine runs passed with no
  miss and exit 0 (start frames 47 to 135), in all three boot modes:
  - branching on, S clears: scenes 3, 5, 4, 6, 7 (the 1ST, 3RD, 2ND, 4TH and
    5TH ZONE), grades S in zones 1 to 4, 3 redirects, 4 clears;
  - branching on, clears with nothing destroyed: the stock order 3, 4, 5, 6,
    7, grades B, D, D, D, no redirect, 4 clears;
  - branching off, S clears: the stock order, grades S, no redirect.
  The contact sheets (`runs/*_sheet.png`; S path in SCPH-1001 mode and the
  low-grade run in HLE mode viewed) show MOVIE IM 0 after the 2ND ZONE on
  both paths: before the 4TH ZONE on the S path, before the 3RD on the stock
  path. The summary's first version expected D in the 1ST ZONE too
  (`branch_summary-first.log`). Two shorter HLE runs that log all nine
  record words (`records/`, `probe_records.py`) explain the B: with nothing
  destroyed, the 1ST ZONE's destroy factor and rating are 2048 (0.5) where
  the 2ND ZONE's are 0, both with a time factor of 4096 (1.0). In the S run
  the running-score words of the 1ST, 3RD and 2ND ZONE's records, 0, 36,800
  and 73,600, confirm that order. The runs used `da70e6c0dd92…`, the final
  binary (the later reflow and comment edits rebuilt it byte-identical); only
  the zone-clear manifest's descriptions changed after them.
- Feature-off runs (`routes.sh` / `routes.log`, `routes/`, `probe/`): every
  committed route in all three modes with the documented commands on
  `build-dev` (`da70e6c0dd92…`), 09:39 to 11:31. 65 of the 66 runs passed
  first time. `demo_zone_u4` in LLE OpenBIOS mode stopped at frame 2,678, in
  the intro: the runtime's starvation watchdog reported 25,315,365 us without
  a heartbeat and exited with code 2 (`failed/demo-zone-u4-lle-openbios/`:
  `runtime.log`; `cwd/psx_last_run_report.json`, whose `exit_origin` is
  `starvation_watchdog`; `cwd/starvation_dump.jsonl`). The watchdog allows
  4 s by default (`psxrecomp/runtime/src/starvation_ring.c:61-79`); the
  guest's cycle accounting checks it every 65,536 cycles and exits with
  code 2 (`psx_cycles.c:259-261`, `:324-326`, `:364-367`;
  `starvation_ring.c:255-277`). Userspace across the host had stalled: at
  10:56:09 the journal shows tailscaled's "time jump detected (slept 27s)",
  systemd killing coolercontrold after its 30 s watchdog timeout, and a USB
  hub re-enumerating (`failed/host-journal-10-55.log`). In monotonic time
  (`failed/host-journal-10-55-monotonic.log`) the dump's gap runs from
  528,828.92 s to 528,854.24 s, and the kernel logged a USB disconnect at
  528,837.99 s, inside it, so the kernel kept running. The dump's last ring
  entry is 0.3 ms after the last heartbeat, so the guest did not run during
  the gap, and the watchdog, checked as guest cycles advance, fired only when
  the emulation resumed. So userspace stopped for 25 to 27 s and the runtime
  aborted when it resumed (Derived; the cause of the stall is unknown). With
  both features off, the new hook calls return at once
  (`mod_runtime.cpp:2489-2491`). By then that run's card 1 held a copy of its
  header frame in the write-test frame, where a full run ends with the game's
  test pattern. I copied the attempt into `failed/` at 10:58; `rerun.sh`,
  written later, kept the batch's summaries in `failed/batch-summaries/` and
  ran the same command again (`rerun.log`): PASS, start frame 42, no miss,
  exit 0. With it, all 66
  runs pass (`routes_summary.log`): start frames 14 to 131, 2,052 shots with
  none failed, the largest shot lag 17 frames, no miss, exit 0. In every run
  the overlay instruction count and rows equal change 2's and no `omega.*`
  counter exists (`probe_summary.log`), all 57 replay-mode pairs reach their
  results screens (`clear_time_check.log`), and the card check finds no
  problem (`card_check.log`). The save image and the binary were unchanged
  (`inputs-*.sha256`, `rerun-inputs-*.sha256`), and
  `build-dev/mods/state.toml` names neither new package.

## Phase 5 change 3 changes

- `game.toml`: `[recompiler] mod_instruction_sites = ["0x8002FB2C",
  "0x80071558"]`, with a comment naming both sites and their plugins.
- `generated/`: regenerated. `SCUS_944.49_full_03.c` (two lines) and
  `SCUS_944.49_full_26.c` (one) call `psx_mod_instruction` at the sites, and
  `AOT_STATIC_AUDIT.json` records the new inputs.
- `src/mods/omega_branching.c` (new): the trusted instruction plugin
  `omega.branching` at 0x8002FB2C (expected word 0x2E220011,
  `sltiu $v0, $s1, 17`). It acts only if the script holds the stock scene
  indices at steps 1, 2 and 4. With the step about to run in $s1: after the
  1ST ZONE with grade S and the 2ND ZONE unplayed, it moves to step 4 (the
  3RD ZONE); after the 3RD ZONE with the 2ND unplayed, to step 2; after
  MOVIE IM 0 with the 3RD played, to step 5 (the 4TH ZONE). A zone counts as
  played when its record's grade is 0 to 4. It sets $s0 to match and counts
  each redirect as `omega.branching.redirects`.
- `src/mods/omega_zone_clear.c` (new): the trusted instruction plugin
  `omega.zone-clear` at 0x80071558 (expected word 0x8E02000C,
  `lw $v0, 0xC($s0)`). When the runner's countdown is 0 and the player
  object is in state 3, it sets the countdown to 1, so the runner calls the
  clear routine in that update. With `all-destroyed` it first waits for a
  spawned enemy and copies the spawned count over the destroyed count. It
  counts each clear as `omega.zone-clear.clears`. Its header comment says
  runs have checked it in the 1ST to 4TH ZONE of CAMPAIGN PLAY and names the
  zones it cannot clear and the three where it is untested.
- `mods/preloaded/packages/omega.gameplay.branching/1.0.0/manifest.toml`
  (new): format 7, target `SCUS-94449`, the feature `branching` ("Branching
  Campaign (prototype)", group Gameplay, off by default) and the `[[plugin]]`
  `omega.branching`.
- `mods/preloaded/packages/omega.debug.zone-clear/1.0.0/manifest.toml`
  (new): format 7, target `SCUS-94449`, the hidden feature `zone-clear`
  ("Clear Zones Instantly (testing)", group Debug, off by default) with the
  boolean option `all-destroyed` (default false), and the `[[plugin]]`
  `omega.zone-clear`. Its descriptions claim only zones on the shared
  timeline and name the zones checked.
- `CMakeLists.txt`: both sources added to `EXTRAS_SOURCES`.
- `AGENTS.md`, Mods: the audit's blind spot for instruction-only plugins and
  the hook-site rule; both packages; the feature-on recipe now puts the copy
  under `.cache/` or outside the repository and passes `--out` (change 2's
  review suggestion 1). Routes: what exit code 2 with a starvation dump means,
  and when to run again.
- `docs/MODDING_FEASIBILITY.md`: "The campaign" gains the loop's advance and
  check, the result word and the record write with addresses (re-checked),
  the grade thresholds, and how a zone ends, with how each zone reaches the
  clear routine. Step 1 records the launcher check; step 2 is marked done
  with its results; section 7's unknowns are updated.
- `.agent/HANDOFF.md`: this scope; the change 1 section now says the Phase 3
  change 4 section "still says" the old wording (change 2's suggestion 6);
  Phase 5 change 2 condensed with suggestions 3 to 5 applied; these
  sections; the hypotheses (suggestion 2); the review state; the next
  action.
- Round 2 (after review round 1): the 8TH ZONE's, U4's and U8's own calls to
  the clear routine are recorded in the doc, this file, `AGENTS.md`, the
  plugin's header comment and the package's descriptions, which now claim the
  test clear only for zones on the shared timeline and only as checked in the
  1ST to 4TH ZONE; the doc's record bullet is labelled re-checked, with the
  disassembly's field names; the `mod_runtime.cpp` citation and the
  host-stall wording are corrected; and the review's suggestions are applied
  (review state below).
- Untracked (ignored): the evidence in `.cache/evidence/phase5-3/` (round 2
  added `clear_callers.py`, `clear-callers-first.log`, `spike-excerpt.txt`,
  `failed/host-journal-10-55-monotonic.log`, `review-r1.md` and `r2/`), and
  `phase5-2/review-r1.md`.

## Phase 5 change 3 checks

- `checks-p5-3.sh` / `.log` (staged tree; it computes the index tree in a
  scratch object directory and runs no runtime): all pass. Nothing unstaged
  or untracked, and only the intended paths change. The generated diff is the
  three hook-call lines and the audit's input fields; the shard's C is
  unchanged, and `generated/` equals the index. Both plugins' expected words
  equal the disc's. The handoff's header and its Phase 0 to Phase 4 change 2
  sections equal HEAD. There is no placeholder, doubled blank line, added
  line over 80 columns or local path. The three gates pass, the pins equal
  `framework_pins.txt`, the submodules are clean (`psxrecomp` ignores only
  `overlay_codegen_hash.h`), no tracked file is ignored, and the new files
  are not. Both builds link both plugins and stage both manifests unchanged,
  every input is older than `build-dev`'s binary, the only warnings are in
  `stb_image.h`, and the plugin audit passes (and fails on the framework's
  catalog alone). The staged plugin sources equal their pre-reflow copies
  (`pre-reflow/`) apart from whitespace, and the binaries equal the hashes
  from before the reflow. It prints the framework lines this change relies
  on. Its first run (`checks-p5-3-first.log`) flagged the five long C lines
  and one long handoff line, now reflowed.
  `dis_excerpts.sh`, `branch_summary.py` and `gen_branch_check.py` reproduce
  their outputs. For the feature-off batch it shows the failed run's log,
  report, dump timing and card frame, the journal lines, the watchdog's
  source, the re-run and the unchanged inputs, and `probe_summary.py`,
  `clear_time_check.py` and `card_check.py` reproduce their logs. The three
  route test files pass and leave nothing behind, nothing listens on ports
  4370 to 4389, and `git diff --cached --check` is clean.
- Round 2, `r2/checks-p5-3-r2.sh` / `.log` (staged tree; it rebuilds round
  1's tree from its frozen index entries, both trees in a scratch object
  directory): all pass. Against round 1 only this file, `AGENTS.md`, the
  doc, the zone-clear plugin and its manifest change; `generated/`,
  `game.toml`, `CMakeLists.txt` and the branching files do not. The round-1
  checks above hold again, and also: `clear_callers.py` reproduces
  `clear-callers.log`; the disassembly without its headers equals
  `spike-excerpt.txt`; both plugins' code equals the pre-reflow copies once
  comments and whitespace are removed; the round-2 rebuild compiled only
  `omega_zone_clear.c`, with no warning, and left both binaries
  byte-identical (`r2/binaries-*.sha256`); the framework lines it prints
  include `mod_runtime.cpp:2489-2491`; the journal's lines appear in
  monotonic time; no stale wording from round 1 remains outside the quoted
  findings and a preserved Phase 3 line; every heading has a blank line
  before it; and the commit draft has one placeholder, no line over 72
  columns and no local path.

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
  screens follow them (change 2) and the campaign loop's advance, result word
  and records (change 3, now marked re-checked there). The launcher's Mods
  page lists the unlock package and turns it on (change 3 observations); the
  two packages of change 3 have not been seen there, and the test one is
  hidden.
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
  wording suggestions are applied in this change: four in the doc, one in
  the change 1 section above.
- Phase 5 change 2: round 1 PASS on tree `6a7d573` (staged diff
  `180a2cf5…`) with no findings; commit `9500812`, pushed to the private
  `origin/master`. Report: `phase5-2/review-r1.md`. Its six wording
  suggestions are applied in this change: `--out` and the copy's location in
  `AGENTS.md`'s feature-on recipe; the DEMONSTRATION and per-index scope of
  the unlock claims (hypotheses above); the 64 writes recorded as derived;
  "commonly do not carry" a loose EXE; the `EXTRAS_SOURCES` placement
  reason; "still says" in the change 1 section. Its limitation, the
  launcher, is closed by the check in the change 3 observations.
- Phase 5 change 3, round 1: NEEDS CHANGES on tree `6a643ec` (staged diff
  `f94f48bd…`); report `phase5-3/review-r1.md`. Findings and resolutions:
  - Medium: the 8TH ZONE (`S9.BIN`), U4 and U8 also call the clear routine
    from their own code, which the doc, this file and the cited log missed,
    and the test clear was claimed for every runner zone though it ran only
    in zones 1 to 4. Resolved: `clear_callers.py` gives both counts for every
    `.BIN` and the EXE and checks each call's argument; the doc, this file,
    `AGENTS.md`, the plugin comment and the package descriptions record the
    three zones and limit the claim to the zones run.
  - Low 1: this file said the doc marks the records re-checked, but the doc
    still said "agent", with the agent's field names. Resolved in the doc.
  - Low 2: `mod_runtime.cpp:2488-2490` missed the early return at line 2491.
    Resolved (`:2489-2491`); the round-2 check script prints those lines.
  - Low 3: "the whole host stopped" overstated the evidence (the kernel
    logged a USB disconnect inside the gap), and `AGENTS.md`'s "no guest
    activity after the last heartbeat" missed one ring entry 0.287 ms after
    it. Resolved: userspace stalled, and `AGENTS.md` now asks for a ring that
    ends within a few milliseconds of the last heartbeat.
  - Suggestions adopted: "Its rules read only…"; the same-C claim limited to
    the two EXE sites; "the runtime's exit code 2", and that a gap far above
    4 s means the emulation stopped; where a mod view must go; the 33/272
    figure attributed to change 2's reviewer's probe; the copy into `failed/`
    at 10:58, before `rerun.sh` existed; the spike excerpt saved in the
    evidence; the commit draft aligned with these fixes.
- Phase 5 change 3, round 2: pending delta re-review.

## Next action

After a PASS: commit and push. The next step is the user's choice. Follow-ups
to the prototype: branches into the extra zones (each needs its result
record redirected or protected, see the doc's hazards); a test clear for the
zones that end in their own code (hooks in overlay code), and runs of the
test clear in the other runner zones, the 8TH ZONE, U4 and U8 included; a
committed feature-on route (a runner option for a run directory with its own
`mods/state.toml`); a whole campaign with instant clears, which would also
show whether the spike's post-credits halt happens with every zone loaded.
Or step 3 of section 6, the zone data tools. The branching option can be
tried in the play copy: `play.sh` refreshes `.cache/play/build/` from
`build-dev/`, `mods/bundled/` included, and its Mods page should list
"Branching Campaign (prototype)" under Gameplay.

Play continues from the play copy: `play/play.sh <session dir> <SCPH-1001
dump>` (in `.cache/evidence/phase4-2/`) refreshes `.cache/play/build/` from
`build-dev/`, runs the windowed game there with its own `game.toml` and with
persistent cards in `.cache/play/memcards/`, and watches the debug server. The
play copy's settings still select bilinear filtering; the user's choice,
Nearest, is set in the launcher. Still unreached: CAMPAIGN PLAY zones 5 to 8
and LAST, the ending and credits (the spike reached the ending and credits
only by rewriting the campaign script, and its post-credits halt is
unexplained), TRAINING lessons, ZONE PLAY zones, SAVE REPLAY and LOAD REPLAY.
psxrecomp #719, #720 and #721 are open upstream; any fix arrives through a
reviewed pin bump. Independent changes: harvesting misses with
`psxrecomp/tools/collect_game_misses.py` (none so far); finding why Beetle
reaches screens later than psx-runtime (for example by comparing when each CD
read completes).

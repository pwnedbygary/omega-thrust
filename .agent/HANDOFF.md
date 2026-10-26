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
readability cleanups, each its own small reviewed change. Phase 7, the
user's request, is mouse and keyboard controls like those of modern space
shooters: the mouse steers without a held button, W, A, S and D move, Q held
keeps the mech facing the enemy (the game's SCAN), the left button held is
the lock-on lasers, the right button the machine-gun lasers, and Enter
pauses. It started with a framework fix, one commit on `8077e71` in a fork,
since on Linux the runtime never read `keybinds.ini`.

Current iteration, Phase 7 change 5, round 3: the strafe while Q, the game's
SCAN, is held, which the user chose ("Make WASD strafe while Q is held too, as
its own change"). Invariant: with Mouse Aim on, the keys strafe in two of the
player's three movements, the usual one as before and SCAN's, 0x800334D8,
through a second instruction hook at the same force sum (0x800337CC, listed in
`game.toml`, then a regenerate), along the rotation that the game builds there
from the view's angles, along which its own slide pushes the mech sideways. The
strafe there also pushes the camera's words, its steps have their own counter,
and the mouse keeps the game's own slide. With the feature off nothing changes.
This file also records Phase 6 change 8's round 2 PASS and its commit
`7a05758`, condenses change 8, and corrects Phase 7 change 3's section, which
said that the game has no strafe of its own. Review round 1 found that the
texts left out the slide's pull and the player's third movement, worded the
speed in SCAN as caused by the view's turn, and gave a check of the strafe's
directions that holds only with Invert vertical off. Round 2 corrects the texts
and comments, takes up the review's suggestions, which give the plugin a type
and a new name, and, through `game.toml`'s comment, changes three values of the
static shard's audit; both binaries stay the same. Review round 2 found that
the third movement runs for 6 steps rather than 18 when the boost is a sideways
dash, so round 3 corrects the texts that gave 18 alone, a comment in the plugin
among them, which leaves both binaries the same again, and takes up the
review's five suggestions. Baseline: `7a05758`. Out of scope: what makes
sideways motion faster in SCAN, a strafe in the third movement or one that
pulls as the slide does, the camera's lag at other Strafe speeds, the rest of
the code-quality work, a decompilation and the framework.

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

## Phase 6 change 2 (commit `0292801`)

The audit's steps 2 to 4 for `scripts/zones/zone_data.py` (findings 5, 6
and 8) named what the tool passed as positional tuples or raw numbers:
named tuples `Timeline` (with `slots`), `Part`, `Layout` (with `span`) and
`ZoneEdit`; struct formats and value ranges named once, the ranges checked
with `in_range()`; MIPS opcode, function and register constants and small
decoders; ISO 9660 offsets; terse locals renamed. Round 2 also renamed
`Timeline.call` to `call_at`, `HI_LO` to `MULT_DIV` and the stock `Layout`
in `build()` to `stock_layout`, gave `branch_target()` the argument order of
`jump_target()`, and reworded three comments: the root directory's record,
`is_move()`'s docstring and `branch_target()`'s. One expression was
rewritten: `describe()` takes a `jal`'s target region from the address
after it, as `flow()` does, which agrees with the old one for any file
shorter than 267,255,808 bytes (Derived; the largest has 131,384).
Every output stayed the same: the 142 outputs of
`code-quality/zone-baseline/zone_baseline.sh` equal `baseline-head/` (from
commit `0761991`'s tool; this tool reproduces them, so they stay the
reference), the 61 tests passed unchanged, and `phase6-2/differential.py`
found no difference between HEAD's tool and the new one on 481,061
generated inputs, among them the three parsers at both
edges of every named range they check (it never tries `parse_recipe`'s
`wave >= 0`, `spread > 0` or `pace > 0` at their bounds, which the tests
pin). Of 27 bugs planted in the new names the tests caught 24; the other
three (moves recognised only with `$zero` as the second source, a delay of
2**31 accepted, branch targets one word late) pass HEAD's tests too, and
the differential reports each. Counted per check by change 3's
`phase6-3/gaps_differential.py`, change 2's checks give 2,245 differences
in the move traces, 165 for the delay (11 in `parse`, 154 in
`parse_recipe`) and 3,688 for the branch target (3,654 in `flow`, 34 in
`gate`), and 28 for a fourth bug the tests miss, which review round 1
found: lists of four values taken where three are needed (24 in
`parse_recipe`, 4 in `parse_formations`). `AGENTS.md`'s Beetle oracle
section names a ping reply without a frame number among the reasons a run
fails (change 1's round 3 suggestion 6). `phase5-7/remix_check.py` and
`remix_watch.py` unpack `layout()` into six names, so reuse them with
`0761991`'s tool. Review: round 2 PASS on tree `2eebd73` (staged diff
`54fd5604…`), after round 1 NEEDS CHANGES (see Review and commit state).
The full record is in `git show 0292801:.agent/HANDOFF.md`.

## Phase 6 change 3 (commit `1bc1394`)

The audit's step 5 split `gate()` (43 lines doing three jobs) into
`difficulty_branches()`, which finds each beqz or bnez on a register that
its basic block loaded from the difficulty word, and `reach()`, which walks
the paths through a callback for one value of that word; `gate()` kept its
signature, docstring and answers, and nothing else in the tool changed. The
142 baseline outputs stayed equal to `baseline-head/` (the comparison is in
`phase6-3/checks-p6-3.log`; `baseline.log` there holds only the file
count), the 61 tests passed unchanged, and change 2's differential found no
difference, with change 2's tallies. `phase6-3/differential.py` adds 20,000
programs shaped like wave callbacks to change 2's checks and found no
difference on 542,961 inputs, 61,900 of them `gate()` calls on the new
programs (1,316 answering "only while ... zero", 1,254 "non-zero", 48,036
"only on some paths", 11,294 "every path"). Of 14 bugs planted in the three
functions the tests caught 13; two pairs of them behave the same (review
round 1), so they are 12 distinct bugs. The one the tests miss, a branch on
any word that `loaded()` can trace read as a branch on the difficulty word,
passes HEAD's tests too: the gate test's one case with another word loads
it through `$a0`, which the analysis cannot trace. Change 3's differential
reports 1,173 differences for it, 1,172 from the callback-like programs and
one from change 2's `gate` check. Review: round 1 PASS on tree `10a8d94`
(staged diff `10584f10…`). The full record is in
`git show 1bc1394:.agent/HANDOFF.md`.

## Phase 6 change 4 (commit `2d1b9da`)

Most of the audit's step 6 split `build()` (54 lines) into
`write_timeline()` and `write_formations()`, which each check and write
their part of a dump, and `parse_recipe()` (64 lines, complexity about 39,
the audit's highest) into `check_recipe_header()`, `zone_folder()`,
`check_wave_edits()`, `check_formation_edits()` and `check_edit_values()`.
`parse_recipe()` now returns a new recipe rather than upper-casing each
zone's name in the tables it had just parsed; those tables were its own, so
no caller could see the difference (Derived). Every check kept its order and
message, and change 3's review suggestions gave the `gate()` helpers plainer
names and a comment on the order of `flow()`'s successors. The 142 baseline
outputs stayed equal to `baseline-head/`, the 61 tests passed unchanged, and
change 3's differential found no difference. Until then the comparisons had
given `build()` only unedited dumps, and `parse_recipe()` only one recipe
with every combination of the edge values it tried for a delay, an address
and a move (change 2's range check, 2,002 recipes). `phase6-4/differential.py`
added 50,000 random recipes and 300 random edits of each timeline zone's
dump and found no difference on 597,161 inputs. Its inputs reach every
refusal `parse_recipe()` makes after the TOML is read and every message of
`build()` and its two writers but one: `write_formations()`'s "it has none",
for formations in the dump of a zone that has none, which no test reaches
either (review round 1). Of 35 bugs planted in the split functions, 35
distinct ones (review round 1), the tests caught 33. The other two, a
formation edit without an address left to `expect_keys` (still refused, with
another message) and an address beyond 32 bits accepted by the parser
(refused later by `remix_zone()`), pass HEAD's tests too, and the
differential reports 327 and 642 differences for them. Review: round 1 PASS
on tree `b8ac937` (staged diff `d8707c71…`). The full record is in
`git show 2d1b9da:.agent/HANDOFF.md`.

## Phase 6 change 5 (commit `de447ef`)

The rest of the audit's step 6 (finding 7). HEAD's `package()` wrote both
commands' text and chose between them by its `description` argument: with
none it took exactly one zone, so any other list would have ended in an
uncaught `ValueError` (no caller passed one). Now `package(overlays, *,
image_sha256, header, pkg_id, version, name, description, about)` writes the
manifest around the text it is given and returns the zip;
`dump_package_texts()` and `remix_package_texts()` write each command's
text, and an `Overlay` (a `ZoneEdit` and the span `build()` may change, made
by `zone_overlay()`) gives them the zone's label and region and gives
`package()` the payload and the stock bytes it replaces. From change 4's
review, `write_formations()`'s parameter is named `formations`,
`zone_folder()`'s docstring reads more plainly, and `check_edit_values()`
comes before its caller, as most helpers do. The 142 baseline outputs, 22
packages among them, stayed equal to `baseline-head/`, the 61 tests passed
unchanged, and change 4's differential found no difference. No differential
ran either command before: `phase6-5/differential.py` keeps change 2's to
4's checks, drawing the same random numbers, and runs each command with
HEAD's tool and the new one, comparing the outcome, what it printed and the
package it wrote, on 1,400 package runs (100 random edits of each timeline
zone's dump) and 1,600 remix runs (1,000 random recipes and 600 of the
disc's own waves and formation records); on 600,161 inputs it found no
difference. Of 28 bugs planted in the package code, the tests caught 14.
The other 14 change only text that no test reads (the manifest's comments,
a dump package's description, the feature's description, the final
newline), and planted in HEAD's `package()` they pass HEAD's tests too
(`gaps_at_head.py`). Planted in the new tool, each changes 1 to 22 of the
baseline's 22 packages and makes the differential report 73 to 902
differences (`gaps_differential.py`). Review: round 1 PASS on tree
`68b11f3` (staged diff `28c13876…`). The full record is in
`git show de447ef:.agent/HANDOFF.md`.

## Phase 7 change 1 (commit `56f9da6`)

At `8077e71` the runtime never read `keybinds.ini` on Linux:
`load_input_config()` (windowed runs only) passed argv[0] to
`psx_keybinds_init()`, and `derive_ini_path()`
(`psxrecomp/runtime/src/psx_keybinds.c:180-212`) takes a last path
component without a dot for a directory, so for `Omega_Thrust` it chose
`<executable>/keybinds.ini`. Reported upstream as psxrecomp #752, with a
reproduction (`.cache/evidence/upstream/`). The fix, one commit `898d834` on
branch `omega-thrust/keybinds-beside-exe` from `8077e71` in the fork
pwnedbygary/psxrecomp, passes `psx_keybinds_init()` the directory that
`exe_dir_from_argv()` gives `input.ini`, in all four calls (13 lines added
and 4 removed in `runtime/src/main.cpp`); the branch was pushed to the fork
before this repository's commit, and `.gitmodules` names the fork. Every
line of the fork's `main.cpp` from 4875 on sits nine lines later than at
`8077e71`; this file's earlier sections cite `8077e71`'s numbers.
`keybinds_check.py` (`.cache/evidence/phase7-1/`; a private Xvfb display,
keys from xdotool) failed 4 of its 5 expectations with the old build and
none with the new: the runtime wrote its defaults beside `Omega_Thrust`,
loaded the file, and holding W, bound to Up there, gave Up instead of W's
default R1. Judged from the code and the reviewer's host harness, not run:
under an AppImage the file now sits beside the AppImage, where `input.ini`
already was, and on Windows, where argv[0] ends in `.exe`, it is the same
file as before. The framework's two keybind tests pass when built from the
fork commit; psx-beetle compiles no `main.cpp` and came out byte-identical;
`generate`, the first time with clang 23.1.3, rebuilt the emitters and the
static shard, and only the audit's three hashes changed; all 66 route runs
passed, with the overlay counters of Phase 5 change 3's batch. Review round
1 passed with no findings. Full record: `git show 56f9da6:.agent/HANDOFF.md`.

## Phase 7 change 2 (commit `cc7b83b`)

Mouse Aim, an opt-in mod made from the scratch trial the user played
(`src/mods/omega_mouse_aim.c`, package `omega.enhancement.mouse-aim`), and
`controls/keybinds.ini`, the keyboard layout made for it. The framework's
local mouse policy captures the mouse only while the left button is held
(`psxrecomp/runtime/src/local_mouse_policy.cpp:81-99`) and may move only the
right stick (`psxrecomp/runtime/include/mod_plugins.h:818-819`), while Omega
Boost steers with the left stick, so the plugin puts the game window in
SDL's relative mouse mode itself and drives player 1 through a controller
source, whose sticks replace the player's own (`mod_plugins.h:814-817`). So
a gamepad's sticks do not reach the game while the source is attached. Its
buttons do, through the AND of the source's buttons with the physical pad's
(`psxrecomp/runtime/src/pad_external_input.c:25-26`), and so do the
keyboard's, since keybinds stay live beside a gamepad
(`psxrecomp/runtime/src/main.cpp:5417-5435`). Review round 1 found that
round 1's way of keeping a gamepad's sticks, a presentation policy that
recorded the samples between two calls of the source, failed under the
runtime's default low-latency input, which samples the pad twice a frame;
round 2 dropped it and presents player 1 as analog with
`psx_mod_set_controller_mode_override`, whose values the runtime ties to its
pad modes with `static_assert`s (`main.cpp:1407-1410`). The plugin keeps the
game's TYPE setting (0x800A7E50) at B, so that mouse up flies the mech up,
or at A with Invert vertical; the game saves TYPE and reads it back from the
card at the title screen, so a save made with the feature on keeps it.
Flight is the main loop's state 8 (the campaign loop 0x8002F814), 9 (ZONE
PLAY's loop 0x8002FC30, which `phase5-7/remix_watch.py` names) or 11
(TRAINING, 0x8002FE54), dispatched through the jump table at 0x80012488
(`phase7-2/r2/states.sh`), with the player in play or in a scripted sequence
(state 2, e.g. zone 1's fly-by, set by 0x800341C0). No run has recorded the
state word at 9 or 11, and Mouse Aim has flown in neither, though Phase 5
change 7's runs flew zones started from ZONE PLAY. On a private Xvfb display
with input from xdotool, windowed checks passed every expectation with the
feature off, on, and on with Invert vertical, as did a check of a left
button held through the fly-by and a pause, and one showing that in flight
the game steers by the stick, not the d-pad. Headless runs with the feature
on passed with change 1's overlay counters, and a card saved with it on
differs only in TYPE and its checksum. All 66 feature-off route runs passed
with change 1's overlay counters: with the feature off the runtime never
calls the plugin (`psxrecomp/runtime/src/mod_packages.cpp:3869-3876`,
`mod_runtime.cpp:2176-2179`, `:2189-2192`). Review: round 1 NEEDS CHANGES
(one Medium, one Low), round 2 PASS on tree `2fed384` (staged diff
`657fb328…`). Full record: `git show cc7b83b:.agent/HANDOFF.md`.

## Phase 7 change 3 (commit `ad4fb7e`)

Strafing for Mouse Aim, which the user asked for after playing change 2 on
the desktop (`phase7-2/play-02/`: the 1ST and 2ND ZONE of CAMPAIGN PLAY with
Mouse Aim on, no unknown dispatch or segment miss). Outside SCAN, whose
left-stick slide Phase 7 change 5 measured, the game has no strafe
of its own (the A. Dean FAQ, `phase7-2/r2/faq-5017.txt:802`): boost with a
direction rolls the mech, and only at boost level E does boost move it sideways
instead. With the feature on, the controller source puts only the mouse on
the left stick, which the game steers by, and the keyboard's left-stick keys
(W, A, S, D and the arrows) on the right stick, which it ignores in flight.
An instruction hook at 0x80033044 (`lw $v0, 0x24($s0)`, listed in `game.toml`),
in the player's movement 0x80032D50 where the step's x and y force sums are
stored and the z sum is about to be loaded, before the two drag paths split,
adds a force along the screen's right and down axes: the right stick's push
times Strafe speed's percent (default 50) of the thrust, 0x238E3 a step. It
acts only for the player's object (0x8009C064 equal to $s0), in play, with
the source attached and the pad record (0x8009C590) showing an analog pad
with its right stick outside the deadzone, and drops the z part where the
stage moves the player along z, as the game does for the thrust. The game's
y axis points up: climbing raises y, turning right lowers the yaw and a positive
pitch points the nose down; the camera follows the heading but not the mech's
roll, so for pitch p and yaw y screen right is (-cos y, 0, sin y) and screen
down (-sin p sin y, -cos p, -sin p cos y). Round 1 took the y axis to point
down, so its strafe ran mirrored on both axes, which its checks, measuring
along the hook's own axes, could not see; review round 1 found it. Round 2's
check from one save state (`phase7-3/r2/screen_check.py`) compares each strafe
with the game's own turn or climb, needing no axis convention: on round 1's
build it failed the four direction checks (cosine -0.999), on round 2's all 17
checks passed (+0.999), each strafe moving the mech 52.7 to 55.3 units a frame
without turning it; a headless probe measured 76.5 to 76.8 a frame each way
while cruising at about 160. Replays feed the game's pad buffer, not the record
the hook reads, so a replay of a strafed flight is not expected to play the
strafe back (Derived, not tested). Windowed checks on Xvfb with xdotool passed
every expectation in round 2's re-run, 9 with the feature off and 31 in each
Mouse Aim setting, after a 15 s cruise past zone 1's asteroid base and, before W
and before D, a wait for a steady heading. Two first runs met a push the keys
did not cause: in round 1's, holding D first moved the mech against its own
strafe, probably pushed by the asteroid base, near which the fly-by ends; in
round 2's, a jolt of 4 to 7 degrees after W's release, with both sticks centred,
counted against D in the invert view (`phase7-3/r2/jolt_check.log`). Neither is
traced. In the re-run neither Mouse Aim setting met a jolt, and every wait ended
after 35 to 37 frames except the one before D with the feature off: there W had
pressed the d-pad and turned the mech, so that wait ran its full 5 s
(`phase7-3/r2/mouse_checks.log:8`). W's first sample came 35 frames later than
in the first run in the on view and 47 in the invert view; the waits before W
took 35 and 36 frames, and in the invert view the idle phase before the wait
also ended 11 frames later (`phase6-6/r2/wait_frames.log`). Regenerating for the
hook site added one call to `generated/SCUS_944.49_full_05.c` and changed four
values of `AOT_STATIC_AUDIT.json`; the static shard's C stayed the same. With
the feature off all 66 route runs passed on round 1's build, with change 2's
overlay counters and most-run PCs, and three routes again on round 2's, in HLE
mode; the feature-on routes kept change 2's cards and probes. Review: round 1
NEEDS CHANGES (one High, the mirror), round 2 PASS on tree `c0d721e` (staged
diff `c236c895…`). Full record: `git show ad4fb7e:.agent/HANDOFF.md`.

## Phase 6 change 6 (commit `4694a77`)

Change 6 took up the three suggestions that change 5's review left for
`scripts/zones/zone_data.py` (`phase6-5/review-r1.md`, section 6), each
about names or docstrings: `Overlay`'s flag `formations` became
`has_formations`; in `write_formations()` a dump's formation became
`formation` and the stock record `record`, as `remix_zone()` and
`reshape()` name them; `dump_package_texts()`'s phrase became `edited`;
`Overlay.folder` got a docstring and `remix_package_texts()`'s was reworded.
The tool's syntax tree, with docstrings left out and the renames undone in
those three definitions, equals HEAD's (`phase6-6/ast_compare.py`, which
fails three planted code changes and passes a docstring change). That
comparison cannot see a rename left incomplete, so the tests (9 of the 61
fail on a planted reader of the old name) and searches show it complete.
The 142 baseline outputs stayed byte-identical, and change 5's differential
found no difference in 600,161 inputs. Two of change 5's planted-bug
snippets quote the renamed names (`phase6-5/mutations.py:84` and `:86`,
both also among `phase6-5/gaps_differential.py`'s `GAPS`), so on the
renamed tool those scripts report them missing. Change 6 also condensed
Phase 7 change 3 and took up that change's round 2 suggestions: two in this
file, and the account `phase7-3/r2/screen_check.py` gives of its one shot
per experiment. Review: round 1 NEEDS CHANGES (two Low, in this file: a
second snippet of change 5's that no longer matches, and the boost level E
exception left out of Phase 7 change 3's condensed section), round 2 NEEDS
CHANGES (one Low: an entry said that round 1 re-ran the checks script),
round 3 PASS on tree `8b44ee4` (staged diff `f8fc6233…`). Reports:
`phase6-6/review-r1.md`, `phase6-6/r2/review-r2.md` and
`phase6-6/r3/review-r3.md`; full record: `git show 4694a77:.agent/HANDOFF.md`.

## Phase 6 change 7 (commit `d1f289a`)

The audit's finding 2a (`code-quality/audit-r1.md`, lines 46-49), the first
of its three fixes to `scripts/zones/zone_data.py`: `trace()` read a
register's value back through straight-line code and stopped at jumps and
branches, but not at the words that control can reach other than from the
word before, so a value read for the timeline table or a formation record
could hold on one path into the call and not on another (the audit's probe
`code-quality/probes/probe_join.py`: HEAD's `read_table()` reported the
table at 0x80120040 where one path passed 0x1274). `join_points(code)`
collects the targets of the file's jumps, branches and calls and the word
each call returns to, and `argument()` reads back no further than the last
join point at or before the call: one at the call itself leaves only the
delay slot, one at the delay slot does not count, and entries that only
pointers or the EXE lead to are not known, as the docstrings say. On the
player's disc no output changed: all 113 traced arguments start after their
last join point, `check` rebuilds the 14 zones identically, the 142 baseline
outputs stayed byte-identical, and no word decodes as a coprocessor branch,
which the tool does not model. Change 5's differential against commit
`4694a77`'s tool, with the rule written into it independently
(`phase6-7/reference.py`), found no difference in 600,161 inputs. Four new
tests (65 in all) fail on `4694a77`'s tool and catch all 18 bugs planted in
the new code; of ten gaps planted in the instruction decoding
(`phase6-7/r3/gaps_now.py`), they catch branch targets one word late and
`jalr` left out of `is_call()`, and the next action lists the other eight.
Three evidence scripts still call the old `argument(code, call, reg)`
(`phase5-6/formation_scan.py`, `phase5-6/formation_layout.py` and
`code-quality/join_check.py`) and need `4694a77`'s tool. Review: round 1
NEEDS CHANGES (one Low: the next action still listed two test gaps that the
change closes), round 2 NEEDS CHANGES (one Low: an observation claimed more
planted gaps than were planted), round 3 PASS on tree `15f6f93` (staged diff
`40a72737…`). Reports: `phase6-7/review-r1.md`, `phase6-7/r2/review-r2.md`
and `phase6-7/r3/review-r3.md`; full record:
`git show d1f289a:.agent/HANDOFF.md`.

## Phase 7 change 4 (commit `4899039`)

The user tried change 3's strafe in the play copy and saw nothing happen
(`phase7-3/play-01/`). A headless run of their setup strafed at 76.5 units
a frame (`phase7-3/support/`), but the game's camera followed the mech
exactly, so in open space the strafe barely showed, and the user chose to
make the camera lag behind sideways moves and catch up. The view
(0x80071F78) builds its matrix from the camera block at 0x800A7D18, which
the camera controller 0x800630B4 writes every step: it hangs the camera
0x1400 units behind the player on a damped spring, pushed against the
step's thrust and the player's words +0xBC to +0xC4 and +0xD4 to +0xDC
(0x800632A8 to 0x8006333C). The per-step routine 0x80030558 clears +0xBC
to +0xC4 every step and runs at most one movement: in play, 0x80032414
while +0x140 is above zero, else 0x800334D8 while +0x168 is not zero, whose
0x80031ABC adds the stick's force across the screen to those words and to
the step's force sums (0x80031CCC), else 0x80032D50, which has the strafe
hook and leaves the words at zero. The hook now adds its force to them as
well (`add_to_word()`, `PLAYER_CAMERA_FORCE`). On build-dev `89a60b3e`,
strafing right left the camera up to 1,048 units behind the mech, 764 while
the key stayed down, and back within about 60 frames of its release;
strafing left held it 661 units the other way, and strafing up lowered it
from 2,580 to 1,881 units above the player (`phase7-4/lag_probe.log`; the
shots in `phase7-4/lag/lag_sheet.png` show the mech off the screen's centre
while it strafes). The strafe's force did not change: over the second half
of each strafing phase but one, the mech moved 79.5 to 80.0 units a frame,
as with change 3 (`phase7-4/steady_compare.log`); in the other, strafing
right, it moved 107.9 units a frame, meeting a push of the game's own,
which the run with the feature off met in the same phase. A scan of the EXE
and the 25 zone files (`phase7-4/r3/reader_scan.py`) finds one more routine
that uses the player's words +0xBC to +0xC4, 0x800302D4, which clears them
when the player is made, and no zone file using them through a register
just loaded from the player pointer; the zone files' 417 other loads and
stores at those offsets go through registers that no check traces.
`AGENTS.md`'s Mouse Aim paragraph explains the camera. The builds, the
plugin audit, the strict compiles, the check from one save state (17
checks, cosine +0.999), the windowed checks, the nine feature-on route
runs, a feature-off sample and the four test files passed. The user then
flew it on the desktop in the 1ST ZONE at Strafe speed 80
(`phase7-4/play-01/`: LLE on the SCPH-1001 dump, no unknown dispatch or
segment miss; `phase7-4/play-01/mods-state.toml` is the mod selection that
the session's launch wrote) and reported: "Strafe works great!" Review:
round 1 NEEDS CHANGES (one Low: an observation on the other code using
+0xBC to +0xC4 was wrong about how some of it is reached and missed one
routine), round 2 NEEDS CHANGES (one Low: it claimed a search of the zone
files for routines the scan had not searched for), round 3 PASS on tree
`e0e627a` (staged diff `41868b49…`). Reports: `phase7-4/review-r1.md`,
`phase7-4/r2/review-r2.md` and `phase7-4/r3/review-r3.md`; full record:
`git show 4899039:.agent/HANDOFF.md`.

## Phase 6 change 8 (commit `7a05758`)

The audit's fixes 2b and 2c (`code-quality/audit-r1.md`, lines 50-54), the
second of its fixes to `scripts/zones/zone_data.py`: the timeline's notes
listed the jal instructions up to a callback's first `jr $ra`
(`callback_span()`), while the formation section says which waves start a
formation by the words `flow()` reaches, so the two could disagree: on
commit `4899039`'s tool a callback that branches over an early return to its
call of 0x80057F0C got the note "calls nothing" (`phase6-8/regression.log`).
`describe(code, joins, callback)` now lists each jal that `flow()` reaches,
in address order, leaving out a note that repeats an earlier one; `render()`
finds the join points once a dump; `callback_span()`, `JR_RA` and
`SCAN_LIMIT` are gone; `flow()`'s docstring says that the graph has no node
for a delay slot unless another path leads there; and a comment beside
`COP0` and `COP2` says that no word of the disc's zone files decodes as a
branch on them (three data words decode as branches on COP1, which the
console's CPU does not have). Three new tests (68 in all) fail on
`4899039`'s tool, and six bugs planted in the new code are all caught. No
output from the player's disc changed: `check` rebuilds the 14 timeline
zones identically and the 142 baseline outputs stayed byte-identical.
Change 5's differential found no difference in 635,161 inputs against
`4899039`'s tool with the rule written into it independently
(`phase6-8/reference.py`), and 7,796, all in the notes, against it as it
was. Rendering the 14 zones takes 188 ms against 645 ms before
(`phase6-8/r2/render_timing.log`). Review: round 1 NEEDS CHANGES (three
Lows in this file: two limits that the condensed Phase 7 change 4 dropped,
and the user's Strafe speed cited without evidence), round 2 PASS on tree
`8c158de` (staged diff `354d150c…`). Reports: `phase6-8/review-r1.md` and
`phase6-8/r2/review-r2.md`; full record: `git show 7a05758:.agent/HANDOFF.md`.

## Phase 7 change 5 observations (`.cache/evidence/phase7-5/`)

- While SCAN is held, the per-step routine runs the movement 0x800334D8
  (Phase 7 change 4). It calls 0x80031ABC first, which updates the view's
  angles (+0x60 to +0x68), builds a rotation from them at +0x40
  (0x80078014) and slides the mech with the left stick along that
  rotation's axes: the stick as the game reads it, at +0xB8 and +0xBA
  (0x80030684: the pad buffer's signed bytes shifted left by 5, nothing
  within 0x400 of the centre), times 40, or 80 while the word at 0x800A7EEC
  is set (0x80031B40 to 0x80031BB4), added to the step's sums and to the
  words +0xBC to +0xC4 (0x80031CCC to 0x80031D28). The movement thrusts
  along the view, which the camera follows. From 0x800337CC to its end it
  is the usual movement's code from 0x80033044 on, word for word but for
  seven jumps (`compare_tails.py` / `.log`): the same force sum before the
  same instruction (`lw $v0, 0x24($s0)`), and the same drag.
- The slide does more than push sideways (review round 1). 0x80031ABC then
  passes the same stick force to 0x8003A0E0 (0x80031D2C to 0x80031D44), which
  returns the square of the force's size over 32 r, r being the distance from
  the player's position to the target's, whose x, y and z words start at
  `[[[0x8009C030]+0x38]]` (0x8003A10C to 0x8003A16C), or 0 where the stage
  moves the player along z (`[0x8009C030]+0x4C` set) or names no target (the
  word at `[0x8009C030]+0x38`, or the word it points to, zero). 0x8007897C
  turns that into a force along the angles at `[0x8009C030]+0x24` and `+0x28`,
  which the view's angles ease toward, and it goes to the step's sums alone
  (0x80031D48 to 0x80031D9C): a pull along the view's turn, which neither the
  camera's words nor the strafe get. Where the stage moves the player along z,
  0x80031ABC still adds the sideways force's z part, reading no `+0x4C`, while
  the strafe drops it there, as outside SCAN. In `force_sums-after.log` the
  slides moved the mech ahead at 48.6 to 65.5 units a frame and the strafes at
  12.4 to 13.3. There the pushes of -128 moved it ahead 1.31 times as fast as
  those of 112, and in `force_sums-before.log` 1.25 times (64.2 against 51.5),
  near (128/112) squared, 1.31, as a pull that grows with the square of the
  force would; the distance to the target, which also sets the pull, changes
  from phase to phase (derived).
- The stick's y at +0xBA follows TYPE (review round 1): the game negates it
  where the word at 0x800A7960 is set (0x800306C4 to 0x800306E4), and each
  flight loop copies TYPE (0x800A7E50) into that word (0x8002F8BC, 0x8002FCC4,
  0x8002FEF8). The plugin's TYPE B is 1, so the game negates it under TYPE B,
  which the plugin keeps while Invert vertical is off: pushing the stick up
  then slides the mech up. Under TYPE A, which Invert vertical selects, pushing
  it up slides the mech down, while W still strafes up.
  `phase7-4/r2/key_masks.log` lists 0x800A7960 with the key masks, as L2, whose
  bit the value 1 shares.
- The per-step routine has a third movement, 0x80032414 (0x80032414 to
  0x80032D4C), which it runs while the player's word +0x140 is above zero,
  before it looks at SCAN's +0x168 (0x800311A0 to 0x800311B8 in play, and again
  at 0x80031438 to 0x80031450). A fresh press of a button in the mask at
  0x800A796C, while +0x140 is not above zero and +0x230 and +0x13C are zero,
  calls 0x80032144 (0x80030800 to 0x80030888), and 0x80032414 lowers +0x140 by
  one each step (0x80032428 to 0x80032434) and calls neither of the other
  movements. 0x80032144 stores +0x140 on every path (0x800323A4): 18
  (0x80032398 to 0x8003239C), with a push along the heading (0x8003231C to
  0x8003232C), or 6 (0x80032350 to 0x80032354) while the word at 0x800A7EF4 is
  set and the stick as the game reads it, +0xB8 or +0xBA, is past 0x800 either
  way, more than half way. Then the push runs along the stick instead, one of
  four vectors (0x80012650 to 0x80012674) for each axis pushed, turned by the
  heading (0x8003220C to 0x80032310): a sideways dash (review round 2). With
  the default setup that mask held Triangle and Circle in zone 1
  (`phase7-4/r2/key_masks.log`), the keys that `controls/keybinds.ini` calls
  boost. So for 18 steps after such a press, or 6 after a dash, in SCAN or not,
  neither hook runs and the keys do not strafe (review rounds 1 and 2; read
  from the code, not run). What sets 0x800A7EF4 is not traced; the boost level
  E of the FAQ, with which the mech "quickly moves laterally in the direction
  held down when boost is pressed" instead of rolling
  (`phase7-2/r2/faq-5017.txt:802-803`), fits the dash (a hypothesis).
- Before the change (build-dev `89a60b3e`; `scan_probe.py` and
  `scan_analyze.py`, `scan-before.log`), the keys did nothing while SCAN was
  held: no strafed step, and no movement along the stick beyond SCAN's own.
  The left stick slid the mech along the rotation's axes at 179 to 204 units
  a frame, while the view turned to keep the enemy ahead and rolled, up to
  164 degrees. The rotation's axes are the camera's, roll included: they
  agree with the view's pitch and yaw axes to the cosine of the view's roll,
  which the camera block shares (`scan-before/analysis.log`).
- The framework keeps a plugin's instruction hooks by address
  (`psxrecomp/runtime/src/mod_packages.cpp:1525-1533`) and runs each whose
  expected word is the instruction about to run, passing its address
  (`psxrecomp/runtime/src/mod_runtime.cpp:2489-2504`), so the plugin
  registers a hook at each force sum.
- The drag that both movements end with (0x8003305C to 0x800331A0 and
  0x800332F4 to 0x800333BC, while +0x13C is not above zero): the velocity
  (+0x28 to +0x30) gains the step's sums, then loses 0x199/4096 of itself;
  the sums are cleared, and the position gains the velocity over 4096
  (`dis/usual-tail.dis`). A steady force F so holds the velocity at about
  9.015 F: 80.13 units a frame for a full strafe at the default and 160.26
  for the thrust, against 80.1 and 160.1 to 160.2 measured outside SCAN
  (`force_sums-after.log`). Every sample read the sums as zero
  (`force_sums.py`), so the forces show only in the velocity.
- With Q held, a full strafe at the default settled at about 98 units a frame
  in the headless probe (velocity 98.9 right, 97.2 left, 98.0 up and 97.6 down
  in `force_sums-after.log`; `scan-after.log`), while the view turned to keep
  the enemy ahead (`view_turn.py` / `view_turn-after.log`: the yaw by 107
  degrees while strafing right and 93 left, the pitch by 95 up and 93 down,
  where the yaw and the roll also turned about 152) and the speed ahead fell
  from 160 to about 13. The game's own slide gained in the same proportion
  (derived): 195.7 units a frame where its sideways force, 112 << 5 times 40,
  gives 157.8 under the same drag (1.24 times, the strafe 1.23). In the
  windowed checks the view held still with Q held, and the strafe matched the
  one outside SCAN (`mouse_checks.log`, over holds of a second: to the right
  51.9 and 55.1 units a frame with Q, against 55.5 and 55.9 without, and up
  55.5 and 55.7 against 55.6 and 56.0, with Mouse Aim on and with Invert
  vertical). The higher speed came with the turning view, but the two kinds of
  run also differ in the input's path (the debug server's stick axes against
  keys sent by xdotool), in the length of the hold (about 329 frames against
  about 60), and in the enemy and its distance, which sets the slide's pull; no
  run varied the turn alone, so what causes the higher speed is not
  established. A hypothesis: the speed the mech gains flying at the enemy turns
  sideways as the view follows it.

## Phase 7 change 5 changes

- `src/mods/omega_mouse_aim.c`: `SCAN_FORCE_SUM` (0x800337CC) beside
  `FORCE_SUM`, with the same expected word; `heading_axes()` gives the usual
  movement's screen axes, as before, and `view_axes()` SCAN's, minus the first
  and second columns of the rotation at `PLAYER_VIEW_ROTATION` (read by
  `view_rotation_entry()` and `signed_half()`, `ROTATION_ONE` for 1.0);
  `strafe()` holds what both hooks share and takes the axes, a `ScreenAxes`
  function, and the counter; `strafe_at_force_sum()` counts
  `omega.mouse-aim.strafed-steps` and `strafe_at_scan_force_sum()`
  `omega.mouse-aim.scan-strafed-steps`; the constructor registers both. The
  header says the hooks are in two of the player's three movements; the
  movement comment says what SCAN's movement does, that its slide also pulls
  the mech where the stage names a target and does not move the player along z,
  which the strafe does not, and that the keys do not strafe in the third
  movement, for 18 steps or the 6 of a sideways dash; the camera paragraph says
  that the slide pushes the camera's words with its sideways force.
- `game.toml`: 0x800337CC in `mod_instruction_sites`, and its comment, which
  says the hooks are in two of the player's three movements.
- `generated/`, from the documented `generate`: one call of
  `psx_mod_instruction` before 0x800337CC in `SCUS_944.49_full_05.c`, and
  four values of `generated/AOT_STATIC_AUDIT.json` (`recipe_input_sha256`,
  `game_toml_sha256`, `cache_tag`, `generation_inputs_sha256`); the static
  shard's C stayed the same.
- `AGENTS.md`: the count of hook sites (four), and Mouse Aim's paragraph: the
  hooks in two of the player's three movements, SCAN's movement and axes, what
  its slide does that the strafe does not, the speed in SCAN, the keys during
  the third movement, and the check of the strafe's directions in SCAN, which
  needs Invert vertical off.
- `mods/preloaded/packages/omega.enhancement.mouse-aim/1.0.0/manifest.toml`:
  the feature's description says what the keys and the mouse do in SCAN.
- `.agent/HANDOFF.md`: the scope; Phase 6 change 8 condensed; change 3's
  section corrected; these sections; the hypotheses' Mouse Aim item; the
  review state; the next action.
- Untracked (ignored): `.cache/evidence/phase7-5/`.

## Phase 7 change 5 checks

- `generate.log`: the documented `generate` exited 0 and rebuilt the static
  shard, whose audit records the hash of `game.toml`; the shard's C came
  out the same.
- Builds with the documented commands (`build-dev.log`, `build-release.log`;
  `binaries-before.sha256`, `binaries-after.sha256`): build-dev `89a60b3e`
  to `7c234043`, build-release `2afd4aab` to `3781e02a`, no warnings; beside
  the plugin and `SCUS_944.49_full_05.c` they compiled the shard's files
  again, which `generate` had written anew. GCC and clang compile the
  plugin with strict warnings and no message (`strict_compile.log`), and
  the plugin audit passes in both builds (`plugin-audit.log`).
- `scan_probe.py` on the new build (`scan-after.log`; `scan_analyze.py`'s
  summary in `scan-after/analysis.log`): outside SCAN the strafe settles as
  before (80.1 units a frame, `force_sums-after.log`). With Q held, each key
  now strafes along the rotation's axes, 97.2 to 99.2 units a frame over
  each phase's second half, counted only as SCAN steps (164 to 166 a phase),
  and the camera falls 867 to 890 units behind; the game's slides with the
  left stick ran at 178.0 to 203.0 units a frame, as before (178.7 to 204.2).
- `scan_screen_check.py` (`screen.log`, shots in `screen/`): from one save
  state made with Q held, with Mouse Aim at its defaults (TYPE B), each strafe
  moves the mech the way the game's slide in the same direction does (cosines
  +0.917 to +0.984) and counts only SCAN steps, while the slides count no
  strafed step: 17 checks pass. The strafes right, left and up moved 53.5 to
  55.3 units a frame along their axes; the strafe down moved 69.4 down, with
  22.8 to the right and 30.1 ahead (79.0 a frame in all).
- The windowed checks (`run_mouse_checks.sh`, `mouse_check.py`: change 3's
  round 2 check with phases at its end in which Q is held, alone and with D,
  with W and with the mouse moving right). In the first run
  (`mouse_checks-first.log`) every expectation passed but one in both Mouse
  Aim settings: with Q held the mouse slid the mech the right way, at 18.6
  and 22.6 units a frame along the rotation's axes with no strafed step, but
  under the 25 the check asked, a key's strafe, while the mouse moves the
  stick about half as far, in about half of the frames. The check now asks
  the slide for its direction, at least 10 units a frame (`SLIDE_MOVED`);
  in the re-run (`mouse_checks.log`) every expectation passes, 10 with the
  feature off and 38 in each Mouse Aim setting, and each run loaded its
  copy's `keybinds.ini`.
- The route batch with every feature off (`routes.sh` / `.log`: every
  committed route in the three modes on build-dev `7c234043`, with Phase 5
  change 2's `phase5-2/probe.py` beside each run): all 66 runs pass
  (`routes_summary.log`). Each run's probe (overlay counters, most-run PCs,
  plugin counters, unlock flags) is the same as in Phase 7 change 3's batch
  (`phase7-3/probe/`; its outputs moved to `routes-before/`), but for four
  counters of how far the run had got when the probe sampled it: the frame,
  and the instructions, blocks and native handoffs run (`probe_summary.log`,
  `r2/probe_fields.py` / `.log`). The memcard route's cards are that batch's,
  byte for byte; the card check finds no problem and the unlocked save is
  unchanged (`card_check.log`, `inputs-after-routes.sha256`).
  `clear_time_check.log` finds the results screen in each demonstration
  route; its lists of shots differ from change 3's batch's in 7 of 57
  lines, by one shot at a screen's edge or, in one route, by an early shot
  flagged in another mode.
- The feature-on routes (`feature_on.sh`: Phase 7 change 2's runner, on a
  copy of this build with Mouse Aim on; `feature_on_routes.log`,
  `feature-on/`): all nine runs pass. Against this change's batch
  (`feature_on_compare.log`), card 1 differs only in the TYPE byte and the
  save's checksum, in all three modes, and the plugin counts one attach in
  each title_to_zone1 run and no strafed step. Each run's probe and each
  saved card match Phase 7 change 4's feature-on runs (`phase7-4/feature-on/`).
- Both builds ran again after the manifest's last edit (`build-dev-2.log`,
  `build-release-2.log`): they compiled and linked nothing but staged the
  mod catalog again, and both binaries stayed the same, byte for byte
  (`binaries-after-2.sha256`); each build's staged manifest now equals the
  source. The runs above ran before the rebuild, with the earlier staged
  manifest, which differs from the source only in the feature's description.
- `checks-p7-5.sh` / `.log` (the staged tree; it writes only in a scratch
  directory, with `TMPDIR` there too): only the seven files change, and the
  working tree holds the staged files; no pin, submodule or `CMakeLists.txt`
  changes; it prints how `game.toml`, `generated/`, `AGENTS.md` and the
  manifest differ from HEAD; this file's header, overall paragraph, Phase 0
  to Phase 7 change 2, Phase 6 change 6 to Phase 7 change 4 and review
  entries up to Phase 6 change 8's round 2 equal HEAD's, and it prints the
  changed words of Phase 7 change 3's section, the scope, the hypotheses
  and the next action; no placeholder, doubled blank line, long added line,
  new reflow leftover or local path; every evidence path that the added
  lines cite exists, but for the play copy's `keybinds.ini`; the gates pass
  and the documented `generate` finds nothing to change; the binaries are
  the ones the runs used; the plugin audit and the strict compiles pass; it
  prints the game code the change rests on; it recomputes the probes'
  analyses from their samples and the feature-on comparison, which match
  their logs, and sums up the save-state check, the windowed checks and the
  batch from theirs; the four test files pass, the Beetle driver's within
  three runs; Phase 6 change 8's round 2 report matches session message
  1332; no listener; and no whitespace error. All pass.
- Round 2: `r2/strict_compile.log`; `r2/generate.log` (the documented
  `generate`, after `game.toml`'s comment: `RESULT_STATIC=built`, the static
  shard's C the same, and the audit's `recipe_input_sha256`, `game_toml_sha256`
  and `generation_inputs_sha256` new); `r2/build-dev.log` and
  `r2/build-release.log` (each compiled the shard's files, which `generate` had
  written anew, and the plugin, with no warning): both binaries stayed the
  same, byte for byte (`r2/binaries-after.sha256`), so every run above holds
  for round 2's tree. `r2/probe_fields.py` / `.log` compares every field of the
  batch's 66 probes with change 3's: only the four sampling counters differ.
  `r2/checks-p7-5-r2.sh` / `.log` repeats round 1's checks on the staged tree,
  and also compares the index with round 1's and each file with its round 1
  blob, prints the game code that round 2's observations cite, re-runs
  `r2/probe_fields.py` and matches this change's round 1 report against session
  message 1014. All pass. Its first run (`r2/checks-p7-5-r2-first.log`), on an
  earlier tree, passed as well; its print of the game code showed that a press
  of a boost key needs +0x140 to be not above zero rather than zero, which the
  observations now say.
- Round 3 (`r3/`): `r3/strict_compile.log`; `r3/build-dev.log` and
  `r3/build-release.log` (each compiled the plugin alone, with no warning,
  after its comment's edit): both binaries stayed the same, byte for byte
  (`r3/binaries-after.sha256`), so every run above holds for round 3's tree.
  `r3/checks-p7-5-r3.sh` / `.log` repeats round 2's checks on the staged tree,
  and also compares the index with round 2's and each file with its round 2
  blob, prints the code of 0x80032144 and 0x8003A0E0 that round 3's
  observations cite and the ratios from both force-sum logs, and matches round
  2's report against session message 1466. All pass.

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
- `keybinds.ini` (Phase 7 change 1): with the fork's fix, windowed runs
  write and load it beside the executable. That was shown on a private Xvfb
  display with keys sent by xdotool, not yet on the desktop with a real
  keyboard. A file saved by the launcher's Controls page is untested; its
  source says the launcher and the runtime read and write the same file
  (`recomp-ui/src/consoles/psx/psx_binds.c:32-34`, `:67-69`; `:53-54` covers
  the second binding's syntax). Upstream's own fix for #752 may differ from
  the fork's, so the update that drops the fork's commit must re-run
  `keybinds_check.py`.
- Mouse Aim (Phase 7 changes 2 to 5) was checked on a private Xvfb display
  with input from xdotool, in the 1ST ZONE of CAMPAIGN PLAY, booted HLE with
  OpenBIOS; the strafe and the camera's lag also headless, through the debug
  server's stick axes, in the same zone. The user flew change 2's build,
  without the strafe, on the desktop with a real mouse through the 1ST and
  2ND ZONE, and change 4's, with the strafe and the camera's lag at Strafe
  speed 80, in the 1ST ZONE (`phase7-4/play-01/`, its mod selection in
  `phase7-4/play-01/mods-state.toml`), and reported "Strafe works great!"
  Change 5's strafe while SCAN is held has not been flown on the desktop.
  In play the game runs SCAN's movement while the player's word +0x168 is
  not zero, and the per-step routine sets that word to the held buttons in
  the mask at 0x800A7970 (0x800307B0 to 0x800307E0), which was L1 in zone 1
  with the default setup (`phase7-4/r2/key_masks.py` / `.log`). It reads
  the buttons from the pad buffer at 0x8010A048, where a held button is a
  set bit: in those reads, with none held, its button bytes are 00 00. L1
  is the game's SCAN, held to keep facing the enemy
  (`phase7-2/r2/faq-5017.txt:233-238`), which `controls/keybinds.ini` puts
  on Q. Read from the code, not run: after a press of a boost key, in SCAN or
  not, the game runs its third movement, which has no hook, so the keys do not
  strafe for 18 steps, or for 6 if the boost is a sideways dash, as it is while
  the word at 0x800A7EF4 is set (likely the game's boost level E) and the left
  stick, which the mouse moves, is pushed more than half way; in SCAN the
  strafe adds only the slide's sideways force, not its pull along the view's
  turn; and under Invert vertical (TYPE A), pushing the stick up slides the
  mech down, while W still strafes up. Not yet: what makes sideways motion
  faster in SCAN in the headless run, the strafe and the game's slide alike,
  and whether the view's turn does (change 5's observations); the strafe and
  the camera's lag in other zones and at other Strafe speeds; how
  the strafe meets the stage's limits, which the movement applies after the
  forces, the stages that move the player along z, where it drops its z part
  as the game does for the thrust, and the game's other pushes (two of change
  3's first windowed runs each met one they did not cause: round 1's while D
  was held near zone 1's asteroid base, round 2's as a jolt of 4 to 7 degrees
  after W's release; neither is traced); ZONE PLAY and TRAINING, which the
  plugin counts as flight; losing the window's focus, which should free the
  cursor; the runtime's own save-state and rewind menus, during which the
  cursor may stay captured, since the plugin frees it only for the game's
  pause, outside flight or without focus; CONTROL B; a key setup that moves
  ATTACK off Cross and Square (the plugin presses the setup's first button,
  read from 0x800A7C40); and the d-pad in directions other than up. That a
  saved replay cannot play a strafe back is Derived. While the feature is on
  it also overrides a TYPE chosen in CONTROL SETUPS, and a gamepad's sticks
  neither steer nor strafe in flight, so a gamepad player turns it off.
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
- Phase 6 change 2, round 2: PASS on tree `2eebd73` (staged diff
  `54fd5604…`), from the same reviewer, with no findings: it planted the
  move bug and its mirror image and a recipe delay of -1, for each of which
  the differential reported differences, read the tool's round-2 delta line
  by line, and re-ran the checks script and its own comparison of HEAD's
  tool with the new one. Report: `phase6-2/r2/review-r2.md` (session message
  1023). Commit `0292801`, pushed to `origin/master`. Its three suggestions
  are taken up in change 3 (the change 2 section): "every named range" for
  the parsers' edges; the gaps' differences counted per check
  (`phase6-3/gaps_differential.py`); `branch_target()`'s reworded docstring
  listed.
- Phase 6 change 3, round 1: PASS on tree `10a8d94` (staged diff
  `10584f10…`), from a fresh read-only reviewer, with no findings: it re-ran
  the checks script, compared the two modules' syntax trees, and ran its own
  differential of 1,307,325 inputs (every four-word program built from 12
  instructions, a generator unlike change 3's, and every word of each wave
  callback's flow graph on the disc as the call), which compared `gate()`'s
  answers and, from a copy of HEAD's `gate()`, its branch table and both
  walks' results, finding no difference. Report: `phase6-3/review-r1.md`
  (session message 828). Commit `1bc1394`, pushed to `origin/master`. Its
  six suggestions are taken up in change 4: 1 (the 1,173 differences come
  from this change's differential, 1,172 of them from the new programs) in
  commit `1bc1394`'s message and the condensed change 3; 2 (two pairs of
  the planted bugs behave the same, so they are 12 distinct bugs) in the
  condensed change 3; 3 to 5 (the names `difficulty_is_zero`, `block_start`,
  `successors` and `target`, `reach()`'s docstring, and a comment on
  `flow()`'s order of successors) in the tool; and 6 in this file: the
  condensed change 3 says where the baseline comparison is, and change 4's
  `baseline.log` records it, and the condensed change 2 has its "(Derived)"
  label back. Its third point, that change 1's round 3 entry points to
  change 2's observations, which no longer exist, is left: that entry is a
  record, and commit `0292801` holds those observations.
- Phase 6 change 4, round 1: PASS on tree `b8ac937` (staged diff
  `d8707c71…`), from a fresh read-only reviewer, with no findings: it re-ran
  the tests on the staged and HEAD copies, the baseline, `differential.py`,
  `mutations.py`, `gaps_at_head.py` and the audit's three probes, compared
  the `gate()` helpers' syntax trees with HEAD's once the renames are
  mapped, and ran its own differential of 73,600 comparisons (60,000
  recipes; 10,600 builds of five synthetic zones and the 14 on the disc;
  3,000 runs of the remix steps, half of them mixing the two versions),
  comparing results, and exceptions by class, message and raising line. It
  found no difference beyond the moved lookup of a dump without a timeline
  (the same `KeyError`, raised from another line), and found the 35 planted
  bugs distinct. Report: `phase6-4/review-r1.md` (session message 916).
  Commit `2d1b9da`, pushed to `origin/master`. Its five suggestions are
  taken up in change 5: 1 (the old `parse_recipe()` was 64 lines and its
  loop 44) in commit `2d1b9da`'s message; 2 to 4 (`write_formations()`'s
  parameter named `formations`, so that `edits` keeps to recipes;
  `zone_folder()`'s docstring; `check_edit_values()` before its caller) in
  the tool; and 5 in this file: the condensed change 4 says that change 2's
  range check tried every combination of its edge values in one recipe,
  names the one message of `build()`'s writers that nothing reaches, and
  labels the claim that no caller could see the old rewrite Derived, and
  change 3's round 1 entry names commit `1bc1394`.
- Phase 6 change 5, round 1: PASS on tree `68b11f3` (staged diff
  `28c13876…`), from a fresh read-only reviewer, with no findings: it re-ran
  the checks (27 minutes), compared the syntax trees, ran 20,000 in-process
  cases and 1,200 command runs on synthetic disc images with no difference,
  and reached `write_formations()`'s "it has none" through both tools (the
  same message). Outside the snapshot it found an ignored `__pycache__` under
  `scripts/routes/` that my mouse trial's scripts had written; it is
  deleted, and those scripts now set `sys.dont_write_bytecode`. Report:
  `phase6-5/review-r1.md` (session message 801). Commit `de447ef`, pushed to
  `origin/master`. Its six suggestions: 1 to 3, on this file's wording (the
  planted bugs' figures attributed to the new tool, in their own sentence;
  "No differential ran either command before"; "as most helpers do"), are in
  the condensed change 5; 4 to 6, in the tool (`Overlay.formations` named
  `has_formations`; `write_formations()`'s loop variables and
  `dump_package_texts()`'s local `edits` named for what they hold; a
  docstring for `Overlay.folder`; plainer words in `remix_package_texts()`'s
  docstring), wait for the next `zone_data.py` change.
- Phase 7 change 1, round 1: PASS on tree `9f5e1a3` (staged diff
  `95cad361…`), from a fresh read-only reviewer, with no findings: it re-ran
  `keybinds_check.py` (no expectation failing), the framework's keybind
  tests, `record_pins.sh`, the gates and `test_routes.py`, recomputed the
  route batch from its 66 `result.json` files, and compiled the old and the
  new path code into a host harness (a name without a dot, a dot only in a
  directory's name, a dotted name, a symlink, `APPIMAGE` set, a bare name, a
  Windows path). Report: `phase7-1/review-r1.md` (session message 980). The
  fork's branch was pushed first, then commit `56f9da6` to `origin/master`.
  Outside the snapshot it found in `build-release/` the `input.ini` and
  `keybinds.ini` that the launcher wrote on October 19 (Phase 2); a windowed
  `build-release` run now loads that `keybinds.ini`, which equals the
  launcher's defaults, so they stay. Its seven suggestions: 1 to 3 (never
  delete or force-push a fork branch; what an update to an upstream commit
  that does not fix the issue yet does; `git submodule sync --recursive` for
  older clones; "fixes the same issue") and 7's second point ("does trigger
  a rebuild") are in `AGENTS.md`; 4 (`psx_keybinds.c:180-212`) and 6 (the
  branch pushed before the commit, and what the fix means under an AppImage
  and on Windows) in the condensed change 1; 5 in the scope, as "Q held keeps
  the mech facing the enemy", after the FAQ by A. Dean
  (https://gamefaqs.gamespot.com/ps/198233-omega-boost/faqs/5017, saved in
  `phase7-2/r2/faq-5017.txt`), which says it turns toward the last enemy shot
  at, not the nearest; and 7's first point in the hypotheses.
- Phase 7 change 2, round 1: NEEDS CHANGES on tree `789c9bf` (staged diff
  `918a30bd…`), from a fresh read-only reviewer, with one Medium and one Low
  finding. Report: `phase7-2/review-r1.md` (session message 1376). Medium:
  under the runtime's default low-latency input the plugin threw away player
  1's physical sticks every frame, so a gamepad could not steer while Mouse
  Aim flew, though the scope, `AGENTS.md`, the manifest, the plugin's
  comments and this file said its stick added to the mouse (shown under gdb,
  with a control run and a host harness; the checks could not see it, since
  they ignore gamepads and the plugin added the keyboard's stick keys again).
  Round 2 drops the plugin's sample recording and presentation policy,
  presents player 1 as analog with the mode override, and says throughout
  that a gamepad's sticks do not steer while the feature is on (observations
  above). Low: the observations credited flight states 9 and 11 to the
  scratch trial, whose watch saw only 8; round 2 cites the EXE's state
  dispatch for them (`r2/states.sh`). Its seven suggestions: 1 (0x800341C0
  sets the scripted state), 2 ("all its callbacks"), 3 (the launch press
  lasts four frames so that it is seen even if the game takes longer than
  two frames between reads) and 4 (an empty key setup falls back to the
  game's default one) are in the plugin; 6 (the FAQ's URL, and focus loss
  among the untested items) and 7 (the latency of the keys and the mouse) in
  this file; 5 is left out: resetting the plugin's state at activation
  matters only when a session starts again in the same process, and only a
  netplay match returns there (`psxrecomp/runtime/src/main.cpp:18786-18787`),
  which the launcher offers only to a game of two or more players
  (`:14117-14118`), while Omega Thrust has one (`game.toml`, `players = 1`).
- Phase 7 change 2, round 2: PASS on tree `2fed384` (staged diff
  `657fb328…`), from the same reviewer, with no findings: it traced the mode
  override through the framework at `898d834` (the `static_assert` at
  `main.cpp:1407`, the session start that applies the override, and each
  path that decides how player 1 is presented), recompiled the plugin with
  each build's own command to objects byte-identical to the builds', re-ran
  `r2/checks-p7-2-r2.sh` into scratch, ran its own windowed `mouse_check.py`
  on round 2's binary (none of 23 expectations failing) and reproduced
  `r2/snapshot/`. Report: `phase7-2/r2/review-r2.md` (session message 1976).
  Commit `cc7b83b`, pushed to `origin/master`. Its eight suggestions: 1 to 3
  and 8 are in the condensed change 2 (no run has recorded the state word at
  9 or 11, and Mouse Aim has flown in neither; `phase5-7/remix_watch.py` for
  ZONE PLAY's loop; a gamepad's buttons through `pad_external_input.c:25-26`;
  the `static_assert`s), 4 to 6 in the plugin's comments (change 3), and 7
  in round 1's entry above.
- Phase 7 change 3, round 1: NEEDS CHANGES on tree `c210fe3` (staged diff
  `08e2f094…`), from a fresh read-only reviewer, with one High finding: the
  strafe ran mirrored on both axes (D and the right arrow moved the mech to
  the left of the screen, W and the up arrow down). The reviewer tied the
  screen to the game's own steering from one save state, re-ran
  `phase7-3/checks-p7-3.sh` into scratch (every section passed),
  disassembled the hook's site and the movement, and read the framework's
  hook dispatch. Report: `phase7-3/review-r1.md` (session message 1142).
  Round 2 negates both axes in the plugin and corrects every text that gave
  a direction on round 1's axes. Its suggestion 1, a check tied to the
  screen, is `phase7-3/r2/screen_check.py` and two expectations in
  `phase7-3/r2/mouse_check.py`, both comparing the strafe with the steering;
  suggestion 2 softens the manifest's replay sentence, and `AGENTS.md`'s
  with it.
- Phase 7 change 3, round 2: PASS on tree `c0d721e` (staged diff
  `c236c895…`), no findings, from the same reviewer: it re-ran
  `phase7-3/r2/checks-p7-3-r2.sh` into scratch, reproduced the frozen
  snapshot, and ran its own probe from one save state on round 2's build,
  where each strafe moved the mech the way its key points and the game's own
  turn and climb, measured the same way, confirmed the measurement. Report:
  `phase7-3/r2/review-r2.md` (session message 1550). Commit `ad4fb7e`,
  pushed. Its three suggestions: 1, W's delay after the first windowed run,
  35 frames in the on view and 47 in the invert view, is in change 3's
  condensed section; 2, naming both pushes that the first windowed runs met,
  is in the hypotheses' Mouse Aim item; 3, the save-state check's one shot,
  is in that script (see Phase 6 change 6).
- Phase 6 change 6, round 1: NEEDS CHANGES on tree `5424877` (staged diff
  `6a090484…`), two Low findings, both in this file. The fresh reviewer
  found the tool's change to be exactly the stated renames and docstrings
  (its own reversal of the renames, token by token, gave HEAD's file byte
  for byte) and re-ran the four test files, the baseline, the differential,
  the help texts, the probes, the syntax-tree comparison and its planted
  cases, the gates and the pins, but not the checks script itself. Low 1:
  the observation on change 5's evidence named one snippet that no longer
  matches the tool (`phase6-5/mutations.py:84`); there are two, the other at
  line 86 quoting `edits`, and `phase6-5/gaps_differential.py` plants both.
  Low 2: the condensed Phase 7 change 3 section dropped the boost level E
  exception that the full record and its FAQ give. Report:
  `phase6-6/review-r1.md` (session message 745). Round 2 corrects both. Of
  its six suggestions, 1 (the commit draft's count of renamed locals and its
  deferred line) went into the draft; 2 (the five experiments that take a
  shot, and a short line in `phase7-3/r2/screen_check.py`'s docstring), 3
  (the waits, W's delay and the HLE routes) and 5 (what shows the rename
  complete) into change 6's full sections and that script; 4 (the temporary
  directory of change 5's differential) into round 2's checks and the bullet
  on round 1's checks; 6 (one meaning for `formation` and `record` across
  the module) is left for a later naming pass.
- Phase 6 change 6, round 2: NEEDS CHANGES on tree `8e3dcf2` (staged diff
  `16534a38…`), one Low finding, in this file: the round 1 entry said that
  the reviewer re-ran the checks script, which its report names only in a
  suggestion. The same reviewer confirmed that both round 1 findings are
  resolved and that suggestions 2 to 5 landed, recomputing the snippet
  counts, W's delays and the waits independently, and that the tool is
  round 1's byte for byte. Report: `phase6-6/r2/review-r2.md` (session
  message 1014). Round 3 corrects the entry, which now names what round 1
  re-ran. Both of round 2's suggestions are applied in Phase 7 change 3's
  condensed section: the `phase7-3/r2/` base of three paths, and why the
  wait before D ran its 5 s with the feature off.
- Phase 6 change 6, round 3: PASS on tree `8b44ee4` (staged diff
  `f8fc6233…`), no findings, from the same reviewer. With its own word-level
  diff of the delta and its comparison of this file's sections with HEAD's,
  it confirmed round 2's finding fixed and both of round 2's suggestions
  applied, and it read the evidence they rest on. By that round's rule it
  ran no tests, baseline or differential; the tool was the blob it had
  tested in rounds 1 and 2. Report: `phase6-6/r3/review-r3.md` (session
  message 1183). Commit `4694a77`, pushed. Its one suggestion, to spell out
  the evidence directory in the paths of the entries for Phase 7 change 3
  and change 6, is applied in those entries (Phase 6 change 7).
- Phase 6 change 7, round 1: NEEDS CHANGES on tree `ff94e7b` (staged diff
  `dd9cb039…`), one Low finding, in this file: the next action still listed
  two test gaps that this change closes, branch targets one word late and
  `jalr` in `is_call()`, and counted the bugs that `differential.py` reports
  by that list. The fresh reviewer confirmed the rule and its tests: it
  worked out the expectations by hand, saw exactly the new cases fail on
  HEAD's tool, found no mismatch between its own decoder of join points and
  the tool on 200,000 random programs, and reproduced the baseline, the
  mutations, both differentials and the disc windows. Report:
  `phase6-7/review-r1.md` (session message 880). Round 2 corrects the list
  and the count (`phase6-7/r2/gaps_now.py`). Of its five suggestions, 1 (the
  target of each kind of conditional branch in the join-point test), 3
  (`join_points()`'s docstring) and 4 (change 6's verdicts in its condensed
  section) are applied; 2 and 5 are left for later changes, as the next
  action says.
- Phase 6 change 7, round 2: NEEDS CHANGES on tree `58ada63` (staged diff
  `66188d42…`), one Low finding, in this file: the observation on the gaps
  said that `r2/gaps_now.py` planted every gap the next action listed in the
  instruction decoding, but it planted six of ten; the same reviewer planted
  the other four, in `destination()`, itself, and neither version's tests
  catch them. It confirmed round 1's finding resolved, suggestions 1, 3 and 4
  applied, and the tool's code round 1's but for one docstring; it re-ran the
  tests on both tools, `r2/mutations.py` (all 18 caught) and
  `r2/gaps_now.py`, rebuilt the baseline, ran its round 1 fuzz again (600,000
  arguments, no mismatch) and compared the four regenerated logs with round
  1's. Report: `phase6-7/r2/review-r2.md` (session message 1231). Round 3
  plants all ten in `r3/gaps_now.py` and corrects the observation and
  `r2/gaps_now.py`'s docstring. Of its four suggestions, 1 (naming the tests
  that branch targets one word late fail), 3 (`join_counts.log` reproduces
  but for its times) and 4 (a short line in the next action, reflowed) are
  applied; 2 (that `join_points()`'s docstring could say that coprocessor
  branches are not modelled) goes with the next fix, as the next action says.
- Phase 6 change 7, round 3: PASS on tree `15f6f93` (staged diff
  `40a72737…`), no findings, from the same reviewer: it confirmed round 2's
  finding resolved, three of its suggestions applied and the fourth deferred
  with a reason, and that round 3 changed only this file, the tool and the
  tests being round 2's blobs byte for byte. Report:
  `phase6-7/r3/review-r3.md` (session message 1432). Commit `d1f289a`,
  pushed. Its one suggestion, a wording in the round 3 checks bullet, lapsed
  with that bullet when Phase 7 change 4 condensed change 7.
- Phase 7 change 4, round 1: NEEDS CHANGES on tree `78a618a` (staged diff
  `f5d4afcd…`), one Low finding, from a fresh read-only reviewer: the
  observation on the other code using offsets +0xBC to +0xC4 said that
  0x80041D34 and its neighbours got their object from an update reached
  through a pointer, 0x80045168, and left open whether it was ever the
  player, while the EXE shows that the routine starts at 0x80045160 and that
  0x80043DA8 calls it, so the object is player+0x24C; the observation also
  missed 0x8004EEC0 and misdescribed 0x8007D784's read. The code and the
  observation's conclusion stood. The reviewer re-ran
  `phase7-4/checks-p7-4.sh` into scratch (as logged; the Beetle driver's
  tests passed on their second run), reproduced the snapshot, and read the
  EXE and the 25 zone files with its own disassembler. Report:
  `phase7-4/review-r1.md` (session message 887). Round 2 rewrites the
  observation from `phase7-4/r2/reader_scan.py`, which saves the scan (its
  suggestion 3), and takes up its suggestions 1 (the fourth observation's
  cases), 2 (what sets +0x168, in the hypotheses) and 4 (a wording in the
  next action), and 7 in round 2's checks script. Suggestion 5, to name
  +0xD4 to +0xDC in the plugin's comment, is left: the comment names the
  words the plugin writes, and the observations name all three. Suggestion
  6, a run at Strafe speed 100, goes to the user's trial.
- Phase 7 change 4, round 2: NEEDS CHANGES on tree `8f839b2` (staged diff
  `0580ef27…`), one new Low finding, from the same reviewer: the rewritten
  observation's last sentence said that no zone file names any of the
  routines it names, citing the scan's part 3, which searched for only nine
  of them, and zone files call two of the others: 0x8006000C (20 files) and
  0x8004EEC0 (S4, S8, U4 and U7). None names the routines that use those
  offsets in an object they are given, so the conclusion stood; round 1's
  finding is resolved. The reviewer re-ran `phase7-4/r2/checks-p7-4-r2.sh`
  into scratch (as logged), checked the rewritten observations with its own
  disassembler and dataflow check, and searched the zone files itself.
  Report: `phase7-4/r2/review-r2.md` (session message 1296). Round 3 widens
  the scan's part 3 to every routine the fourth and fifth observations name,
  rewrites the sentence from it, and takes up the three suggestions:
  0x8004FF84 is named, checked with a dataflow script of its own
  (`phase7-4/r3/reach.py`); so are the routines that only lui pairs name;
  and the hypotheses say how the pad buffer holds a held button and that the
  left stick fills +0xB8 and +0xBA when the pad is analog.
- Phase 7 change 4, round 3: PASS on tree `e0e627a` (staged diff
  `41868b49…`), no findings, from the same reviewer: round 2's finding is
  resolved, and round 3's other statements hold against the EXE. It re-ran
  `phase7-4/r3/checks-p7-4-r3.sh` into scratch (as logged), and checked the
  widened scan and `phase7-4/r3/reach.py` against a search and a dataflow
  check of its own. Report: `phase7-4/r3/review-r3.md` (session message
  1562). Commit `4899039`, pushed. Of its four nonblocking suggestions, the
  three on wordings in change 4's sections lapsed when Phase 6 change 8
  condensed them. The fourth, that `phase7-4/r3/reach.py` does not count
  calls among the control that comes from elsewhere, is recorded here: the
  reviewer's own search, which counted calls, found no branch, jump or call
  in code (from 0x800243E4 up) that enters either routine past its first
  word.
- Phase 6 change 8, round 1: NEEDS CHANGES on tree `ea12b59` (staged diff
  `20384365…`), three Low findings in this file, from a fresh read-only
  reviewer, which found nothing to fix in the tool or the tests. The
  condensed Phase 7 change 4 said that the scan finds no zone file using the
  player's words +0xBC to +0xC4 through the player pointer, while the scan
  follows only a register just loaded from it and leaves 417 accesses
  untraced; it gave the second half of every strafing phase as 79.5 to 80.0
  units a frame, while `phase7-4/steady_compare.log` has the right phase at
  107.9; and it, the hypotheses and the next action gave the user's Strafe
  speed as 80, which nothing in `phase7-4/play-01/` recorded. The reviewer
  re-ran `phase6-8/checks-p6-8.sh` into scratch (as logged), read the rule,
  re-derived the new tests' expectations by hand, counted the coprocessor
  branches its own way, and checked the condensed section against HEAD's
  sections and the reports. Report: `phase6-8/review-r1.md` (session message
  920). Round 2 restores the two qualifiers, saves the session's mod
  selection as `phase7-4/play-01/mods-state.toml` and cites it, and takes up
  all eight suggestions: `zone()` builds callback A from `FORMATION_CALL`;
  `flow()`'s docstring covers every path to a delay slot; `describe()`'s
  says which notes it leaves out; one comment beside `COP0` and `COP2` holds
  the fact about the disc; the first observation says what `regression.log`
  shows and where the rest is; Phase 7 change 4's round 3 entry says "in
  code"; the timing script prints the load; and the commit's deferred list
  names the camera's lag at other Strafe speeds.
- Phase 6 change 8, round 2: PASS on tree `8c158de` (staged diff
  `354d150c…`), no findings, from the same reviewer: round 1's three
  findings are resolved. It re-ran `phase6-8/r2/checks-p6-8-r2.sh` into
  scratch (as logged), compared round 1's and round 2's tool token by token
  without comments and docstrings, and checked the saved mod selection's
  times and round 2's wordings against their sources. Report:
  `phase6-8/r2/review-r2.md` (session message 1332). Commit `7a05758`,
  pushed. Of its three nonblocking suggestions, the two on wordings in this
  file lapsed when Phase 7 change 5 rewrote the scope and condensed change
  8; the third, the copy time in `phase7-4/play-01/mods-state.txt`, was
  corrected outside the snapshot (00:59:48, not about 01:10).
- Phase 7 change 5, round 1: NEEDS CHANGES on tree `4254954` (staged diff
  `ca055f78…`), from a fresh read-only reviewer, with four Low findings, all
  in the texts; it found the plugin, the new hook site, `game.toml`'s list and
  `generated/` correct. Low 1: the record of SCAN's slide left out its pull
  along the view's turn (0x8003A0E0), which the strafe does not add, and its z
  part on stages that move the player along z. Low 2: the texts said the player
  has two movements; there are three, and the third, 0x80032414, which runs for
  18 steps after a boost key's press, has no hook. Low 3: the speed in SCAN was
  worded as caused by the turning view, which the runs show only to come with
  it. Low 4: `AGENTS.md`'s check of the strafe's directions in SCAN holds only
  with Invert vertical off. The reviewer re-ran `phase7-5/checks-p7-5.sh` into
  scratch (as logged), disassembled the code with a tool of its own and derived
  the drag and the speeds again. Report: `phase7-5/review-r1.md` (session
  message 1014). Round 2 checks each finding against the code (the
  observations), corrects the texts, `game.toml`'s comment among them, and
  takes up the eight suggestions: the angles of the view's turn named (1), 55.7
  (2), the four sampling counters (3), "moved the mech sideways" (4), the
  save-state figures (5), a type and a name in the plugin (7);
  `force_sums.py`'s docstring (6) is corrected in the evidence, and Engram's
  record of the module split (8) outside the repository.
- Phase 7 change 5, round 2: NEEDS CHANGES on tree `99b2616` (staged diff
  `fa8dc9d1…`), from the same reviewer, with one new Low, from its own round 1:
  the third movement runs for 18 steps or for 6, not always 18 as round 1's
  report said and round 2 wrote into `AGENTS.md`, the plugin's comment and this
  file. 0x80032144 stores 6 while the word at 0x800A7EF4 is set and the stick
  is pushed more than half way, which makes the boost a sideways dash (likely
  boost level E). Round 1's four findings are resolved. The reviewer rebuilt
  round 2's delta from round 1's blobs, re-ran `phase7-5/r2/checks-p7-5-r2.sh`
  into scratch (as logged), hashed both binaries, and disassembled every path
  through 0x80032144 and every access to 0x800A7EF4 at a fixed address, in the
  EXE and the scene files, with a tool of its own. Report:
  `phase7-5/r2/review-r2.md` (session message 1466). Round 3 checks the finding
  against the code (the observations), corrects each text that gave 18 alone,
  and takes up the five suggestions: the pull's condition that the stage names
  a target, in `AGENTS.md` and the plugin (1); where the target's position is
  (2); the TYPE wording the right way round (3); both logs' ratios (4); and the
  checks script's print of 0x80032350 (5).
- Phase 7 change 5, round 3: pending delta re-review.

## Next action

After a PASS: commit and push, then the user's trial of the strafe while Q
is held. The play copy (`play/play.sh <session dir> <SCPH-1001 dump>` in
`.cache/evidence/phase4-2/`) refreshes from `build-dev/`; its
`mods/state.toml` enabled Mouse Aim at Strafe speed 80 for the user's trial
of change 4 (`phase7-4/play-01/mods-state.toml`), and its `keybinds.ini` is
change 3's `controls/keybinds.ini` (`phase7-3/playcopy-keybinds.sha256`).
Mouse Aim then waits on the user's choices: the camera's lag at other Strafe
speeds (at 100 the push is twice the default's, and the lag there is not
measured); in SCAN, whether the strafe should also pull the mech along the
view's turn, as the game's slide does, and whether it should keep the higher
speed it showed in the headless run, whose cause is not traced; and whether the
keys should strafe in the third movement too, for the 18 steps after a boost
key's press, or the 6 of a sideways dash. With Mouse Aim
on, a gamepad's sticks neither steer nor strafe in flight, while a
gamepad's buttons and the keyboard's work (`pad_external_input.c:25-26`,
`main.cpp:5417-5435`).
Then the rest of the code-quality work the user chose
(`.cache/evidence/code-quality/audit-r1.md`; its section 4 gives the order
and section 5 what must not change), each step its own reviewed change, and
each `zone_data.py` step proven against the baseline in
`code-quality/zone-baseline/` and with `phase6-5/differential.py`: the
zone tool's last fix, a traceback on a malformed directory record (the
audit's probe in `code-quality/probes/` reproduces it), then modules for
the disc reader and the MIPS analysis, as the user chose; the route-script
hang (below), which the user placed just before the next step; one module
for what the two route scripts share, with smaller `main()` functions and
with `ping_frame` refusing a JSON `true` (change 1's round 3 suggestion 1),
then every route in the three runtime modes and the two Beetle modes; test
helpers (the driver tests' fake psx-beetle runs its frames on a free 300 Hz
clock, so while the host is busy a test now and then fails with a late
event, see change 1; the fake could wait for the driver except in the tests
about lateness, `test_output_directory_rules` should print the driver's
output when a run fails, `mutation_compare.py` could match catches by
reason, and `test_zone_data.py` misses two bugs that change 2 planted (moves
recognised only with `$zero` as the second source, a delay of 2**31
accepted) and other bugs that change 2's review round 1 found: lists of four
values taken where three are needed (by its reading a `struct.error`
traceback, not run), the low edge of 16-bit signed fields and the high edges
of 16- and 32-bit unsigned ones, a record size without its pointers, the
destinations of `cfc`, `mfc2`, `lui` and `lwr`, `or` moves, `jalr` in
`control()`, and the order of `blez` and `bgtz`; one that change 3 planted,
a branch on a register loaded from a word other than the difficulty word
that `loaded()` can trace; two that change 4 planted, a recipe's formation
edit without an address, which `expect_keys` then refuses with another
message, and a recipe address beyond 32 bits, which the parser accepts; the
14 that change 5 planted in a package manifest's text, which no test reads;
and `write_formations()`'s refusal "it has none", which no test reaches;
`differential.py` reports the first three bugs and the last 17); names for
the C plugins' registers (the same object code). For new zones (the doc's
section 6, step 5), the candidates: a plugin that gives index 23 a
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

A decompilation was only discussed, and the user has not chosen to start
one; the estimate and Gran Turismo 2's compiler recipe are in Engram (topics
omega-thrust/decomp-feasibility and omega-thrust/decomp-gt2-toolchain).

One of change 7's round 1 suggestions is still open: the trace could also
stop at the word after an unconditional jump's delay slot (`j`, `jr`, `b`),
which control cannot reach from the word before (suggestion 5; no window on
the disc crosses one).

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
7 started, SAVE REPLAY and LOAD REPLAY. psxrecomp #719, #720, #721 and #752
are open upstream; any fix arrives through a reviewed pin bump, and the
update that brings upstream's own fix for #752 drops the fork's commit
(`AGENTS.md`, "Pins"). Independent changes: harvesting misses with
`psxrecomp/tools/collect_game_misses.py` (none so far); finding why Beetle
reaches screens later than psx-runtime (for example by comparing when each
CD read completes).

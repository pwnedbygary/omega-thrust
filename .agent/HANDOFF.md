# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison. Phase 5, at the user's
request, is modding: unlocks, branching, new levels, and later perhaps a fan
sequel or remake that borrows Colony Wars' free-roaming structure.

Current iteration, Phase 5 change 6 (the user's choice: decode how the 1ST,
2ND, 3RD and 6TH ZONE place their enemies, so a remix can move them, not
only retime waves), round 4. Invariant: `zone_data.py` finds every record
the zone passes to 0x80057F0C, with its numbers of steps and members, and
refuses records it cannot trace, counts outside 1 to 32767, parts outside
the file or unaligned, one record passed with two sets of counts, and parts
that overlap each other or the table. Dumps (format 2) give each record's
position, angles, steps (turn, speed, ticks, flags) and member offsets, with
notes naming the waves that start it, when a call does not run on every
path through its callback (a control-flow analysis of the callback: which
value of the difficulty word runs it, where that word decides, else "only
on some paths"; on the disc, five calls run on only one value of the word),
and the units; `build` writes them in place, keeping each record's address
and counts and the members' padding, and still reads format 1 dumps, which
keep the stock formations. `package` covers every byte `build` may write in
one overlay, from the first to the last, and its feature and payload are
named `remix`. The decoded format is re-checked against the EXE's formation
code and in the running game: with a scratch remix of the 1ST ZONE (wave 1's
formation moved and its member offsets doubled; wave 2's first step twice as
fast for half the ticks) installed in a copy of `build-dev`, in all three
boot modes, the formation tasks in RAM move and place their members as the
edits predict, next to runs with the feature off, and the precompiled code
keeps running. What the members are is code, one spawn function per zone.
The tests cover the formation reader, dump, build and package, the analysis on
every branch kind it follows and on six callback shapes where a looser rule
would give a wrong note (round 3's finding), and output paths that are not
valid UTF-8 for `build` and `package` (change 5's round-3 suggestion), and fail
when bugs are planted. `AGENTS.md` and the doc record the format; this file
records change 5's PASS and commit `bdd413f` and condenses change 5. Baseline:
`bdd413f`. Out of scope: other enemies in a formation (code); the ten timeline
zones without formations; a committed remix or route; Beetle (it runs no mods);
plugins, hook sites and regenerating; runner, driver, framework and submodule
changes; play sessions; CI, packaging.

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

## Phase 5 change 6 observations (`.cache/evidence/phase5-6/`)

- The EXE's formation code, disassembled from the disc (`mips_dis.py` reads
  the EXE and the zone files through the tool's disc reader and writes
  nothing). 0x80057F0C, called with the parent task, the record and the
  counts of steps and members, starts a task of 0x50 bytes under the parent
  (update 0x80058300; destructor 0x80058534, which frees the member slots it
  allocates, members times 12 bytes); keeps the record's two addresses and
  both counts; puts the centre at the record's position plus the player's
  (+0x34 to +0x3C of the object at [0x8009C064]); builds the rotation
  matrix from the angles (0x80078014) and writes each member's slot,
  centre + R × offset (0x80079BD0, GTE MVMVA: 8-byte offsets in, three
  words out); and links the centre into the list at [0x8009C030] + 0x34
  (0x8003B7A8). Step flag 0x8000 and, at the start only, 0x4000 set two
  halfwords of that node. The update (0x80058300 to 0x80058530) counts the
  timer down; below zero it starts the next step with its ticks, or after
  the last step unlinks the node (0x8003B7D8) and clears its own update
  word; it adds the step's turns to the angles, moves the centre by speed
  along the heading (0x8007897C), and rebuilds the matrix and the slots;
  with no member left it unlinks and stops, and with no child left it
  clears its update word. The sine table at 0x80018338 is read with an
  angle's top 13 bits (a full turn is 2^32). The matrix has -sin(a0) at
  m[1][2] and cos(a0) sin(a1) at m[0][2], and the heading is (cos a0 sin a1,
  -sin a0, cos a0 cos a1): angle 1 yaw, 0 pitch, 2 roll (Derived).
- The records (`formation_scan.py` / `.log`, `formation_layout.py` /
  `.log`): 33 calls in 30 wave callbacks pass 33 records (the 1ST ZONE 5,
  the 2ND 3, the 3RD 15, the 6TH 10), each with its own constant counts. On
  the disc each formation is its steps, its members and its record, in that
  order, with no overlap and no reference from elsewhere in the file; in the
  2ND, 3RD and 6TH ZONE two words after each record repeat its counts, and
  nothing reads them. Every call lies in a timeline callback (the dump's
  notes). Five calls run on only one value of the difficulty word,
  0x800A7C34 (round 1's Medium finding): the 3RD ZONE's wave-17 callback
  reads it before its prologue (lw at 0x80137170), tests it after (beqz at
  0x80137188), and starts 0x8012227C, 0x80122320 and 0x801223C4 while it is
  non-zero, then jumps past the last call (0x80137240), which starts
  0x8012248C while it is zero; the 6TH ZONE's wave-10 callback (beqz at
  0x80133EAC) starts 0x80121F50 only while it is non-zero. The word was 0 in
  all 2,829 samples of change 3's campaign runs (`phase5-3/runs/*-state.log`),
  1,646 of them in zones 1 to 5 (`r4/difficulty_samples.log`), and the OPTION
  screen offers NORMAL, the default, and HARD (the `menus` route's
  `13-option.png`). Because both callbacks read the word before their
  prologue, the scan's search for one took them for functions nothing
  references.
- The members: each zone spawns every member of every formation with one
  function (0x8012C05C, 0x80131A84, 0x80134F38, 0x8012A134), as a child task
  of the formation, adding one to 0x800A794A (spawned). The 1ST ZONE's
  member update reads its slot and the formation's angles, tests step flag
  bit 1 while the difficulty word is zero and bit 0 while it is non-zero
  before a 1 in 16 chance a tick of calling 0x8012BD74, which starts a
  moving task (a shot, inference), and on a kill counts the formation's
  remaining members down, adds one to 0x800A794C (destroyed) and 100 to the
  score. All four zones' member code counts the remaining members down on
  a kill (0x8012C3A4, 0x80131DC8, 0x80135498, 0x8012A48C). The 6TH ZONE's
  member update tests bits 0 and 1, and the 2ND ZONE's bit 0; the 3RD
  ZONE's has no such test in the same pattern. The task sweep (0x8007A360)
  calls the destructor of a node whose update word is zero and clears its
  children's update words on one pass, and unlinks and frees the node on
  the next.
- Static variants (`variant_guard.py`, change 5's script over every range
  `build` may write; `variant_guard-all.log`): in each of the fourteen
  timeline zones no matching variant has a code range over any of them,
  and the lowest byte a matching variant guards is the end of the last one
  in nine zones and later in five; all 1,391 of the 1ST ZONE's variants
  match the remixed file (`variant_guard-remix6.log`).
- The remix (`make_remix6.py`, written to `.cache/zones/remix6/`): wave 1's
  record, 0x80121E6C, at position [20480, -10240, 74240] instead of [0, 0,
  74240], its five member offsets doubled; wave 2's, 0x80121F18, with its
  first step at speed 512 for 15 ticks instead of 256 for 30. The built file
  differs from the stock one at 16 bytes, 0x1E45 to 0x1E9C; the package's
  868-byte overlay starts at offset 230,014,432 (sector 112,308 times 2048
  plus 0x1DE0). The final tool rebuilds the dump and the package byte for
  byte.
- Runs (`formation_runs.sh` / `.log`, 20:40 to 20:45; a scratch copy of
  `build-dev` (`da70e6c0…`) with the package unpacked into `mods/installed/`
  and its own `mods/state.toml`, feature on or off; port 4373; change 5's
  route `remix_s1.json`, 50 steps and 11,286 frames: boot to CAMPAIGN PLAY,
  start the 1ST ZONE, 16 times 300 neutral frames with a shot, two Cross
  presses): all six runs passed (start frames 23 to 119, no miss, exit 0),
  the inputs' hashes did not change, and nothing was left listening. A
  read-only watcher (`formation_watch.py`) read all of RAM about once a
  second (the runner, every formation task, the member update words) and
  between those read each of the runner's children, about 1,450 formation
  samples a run. `formation_compare.py` / `.log`, every check passes in
  every mode: wave 1's centre minus the stock one is exactly (20480, -10240,
  0) at each of the 248 to 257 step states both runs sampled; in the steps
  that do not turn (0 and 4; 151 to 161 states) each member's offset from the
  centre member is twice the stock one, on - 2 × off being 0 or 1; through
  its first step (9 to 15 samples, timers 14 to 0) wave 2 moves 512 units a
  tick along -z from z = 170,317, where the stock formation also starts and
  moves 256 a tick for 30 ticks, and at each later step state both runs
  sampled (197 to 204) its centre and angles equal the stock formation's;
  the formations tick 0.497 to 0.499 times a frame; each of the five was
  last seen in its last step with all its members as children, and the
  member update words equalled the formations' member children at every
  scan, but for the children of formations gone since the scan before, and
  were 0 at the end. Every run interpreted 1,309 overlay instructions in
  seven rows, with 396 static CRC misses and 1,334 variant misses, on and
  off alike (change 5's probe). Screenshots at the same route frames differ
  where wave 1 flies (`wave1-on-off.png`, batch 1; qualitative only).
- Three earlier batches are kept. `batch1/`: an older watcher, with scans
  once a second, then every 0.2 s; the tool was edited during it, so its
  inputs' hashes differ (its package equals the final one); the final
  comparison passes on it (`batch1/formation_compare-final.log`).
  `batch2/`: a watcher that polled only the formations its scans had found,
  and a scan took longer than wave 2's 15-tick first step, so it has 0 or 1
  samples of that step a run, which fails the comparison's two-sample rule;
  its other checks pass (`batch2/formation_compare-final.log`). `batch3/`:
  the final watcher, before a change to the tool that only rewrapped long
  lines; every check passes (`batch3/formation_compare.log`). All eighteen
  of their runs passed.

## Phase 5 change 6 changes

- `scripts/zones/zone_data.py`: `read_formations` (a `Formation` per record:
  address, steps' address and count, members' address and count, the calls
  that pass it) and `layout` (the table and formations, with every range
  `build` may write checked for overlaps); `callback_span`, which `describe`
  now shares; dumps of format 2 with a `[[formations]]` entry per record
  after the timeline (notes: which waves start it, where its parts are, the
  angles and turns in degrees) and a header on the format; `parse` reads
  format 1 or 2 and checks the formations' keys and ranges (positions and
  turns and speeds 32-bit, angles 0 to 0xFFFFFFFF, ticks and flags 16-bit
  unsigned, members 16-bit); `build` writes each listed record's position
  and angles, steps and member offsets in place and refuses a missing,
  unknown or repeated record or other counts; `package` takes its overlay
  from the first range `build` may write to the last, and names its feature
  and payload `remix` (`<zone>.remix.bin`); `list` gives each zone's number
  of formations; the docstring and help describe formations.
- `scripts/zones/test_zone_data.py`: the synthetic zone holds the record
  its callback passes (4 steps, 5 members, one member's padding 7); ten
  formation tests (the reader and its refusals, overlaps, the dump, edits
  in place, a format 1 dump, what `build` and the parser refuse); the
  package tests check the wider overlay, a zone with no formation (the
  table alone) and edits across sectors with the formation moved past the
  first sector; `build` and `package` with an output path that is not valid
  UTF-8 (change 5's round-3 suggestion); on the player's disc, the four
  zones' formation counts and the unedited S1 package across two sectors.
  46 tests in round 1, 48 after round 2, 49 after round 3; round 4 adds
  six cases to one of them.
- `AGENTS.md`: Zone data describes the formations, what `build` keeps and
  may change, that the members' kind is code, and the wider `remix`
  overlay.
- `docs/MODDING_FEASIBILITY.md`: a "Formations" subsection in section 2
  (the format and its behaviour, re-checked); the intro, the brief answer
  and steps 3 and 4 of section 6 mark the formation parts done, with the
  runs; section 7 asks about the flags instead of the format.
- `.agent/HANDOFF.md`: this scope; change 5 condensed; these sections; the
  hypotheses; the review state; the next action.
- Round 2 (review round 1's one Medium and three Low, `review-r1.md`): the
  dump's notes name a `beqz` or `bnez` before a formation call that can
  skip it, and for one on the difficulty word which value runs the call
  (`gate`, replaced in round 3); on the disc that flags exactly the five
  calls the review found. The doc, `AGENTS.md` and this file name them and
  their condition and no longer say that a callback starts four formations.
  Counts must be 1 to 32767, so a negative count is refused as a count. New
  tests: an unaligned record, zero steps, a negative count, steps that leave
  the file only at 20 bytes a step, the gate's three cases (non-zero; zero,
  with a jump over the call; a branch on another word) and a formation part
  before the table, as on the disc; nine more mutations, 76 in all. The
  doc's wave 2 sentence states the result; this file keeps change 5's
  interpreter limitation and says "all seven rows". The review's seven
  suggestions are adopted: the flag and shot readings labelled as
  inferences; all four zones' kill paths; the dump's flags sentence names
  the zones whose code tests the low bits; the two tests above;
  `formation_compare.py` prints each formation's last sample; a negative
  count's message; the commit draft. `mutations.py` and
  `formation_compare.py` were rerun in place; round 1's results are in
  `checks-p5-6.log`.
- Round 3 (review round 2's two Low, `r2/review-r2.md`): round 2's `gate`
  rules gave way to a control-flow analysis of the callback (`flow`,
  `loaded`, `gate`). It follows every MIPS I branch kind, `j`, and calls
  that return (`jal`, `jalr`, `bltzal`, `bgezal`); `jr`, and indices outside
  the file, end a path. A conditional branch goes both ways, except a
  `beqz` or `bnez` on a register that its basic block loaded from the
  difficulty word, which goes the way the word sends it. The note names the
  value that runs the call when, with the word zero and with it non-zero,
  every path runs the call on one and none reaches it on the other, and says
  "only on some paths through its callback" otherwise. A call is attributed
  to every wave whose callback can reach it (round 2 stopped at the
  callback's first `jr $ra`). On the disc all 14 dumps are byte-identical
  to round 2's. The gate test has twelve cases (`beqz` and `bnez` past the
  call and to it, a load of another word, a two-register `bne`, `bltz`,
  `blez`, an early return, a test of what a call returned, a short-circuit
  OR, a branch to the call); against round 2's tool, cases 4 to 10 fail
  (`r3/test_regression.sh` / `.log`), case 4 only because round 2 gave the
  same note in other words (`r4/case4_wording.sh` / `.log`). The refusals
  add a count of 0x8000, and a player's-disc test pins the five notes.
  Round 2's four gate mutations went with its code; 13 new ones target the
  analysis and the count bound, 85 in all, each caught (`r3/mutations.log`).
  Its six suggestions are adopted: "reads it before its prologue"; the
  difficulty word's evidence (2,829 samples of change 3's logs, 1,646 of
  them in zones 1 to 5, and the OPTION screen, here and in the doc); the
  player's-disc test; a note per callback when several reach a call; the
  0x8000 test; the commit draft's wording.
- Round 4 (review round 3's one Low, `r3/review-r3.md`): the gate test gains
  six cases where a looser rule would give a wrong note: the word decides
  only together with `$a0`, for each value of the word; `$v0` holds the
  word on one path into a join and 5 on the other; an `lw`'s base differs
  on the two paths into its block; a `beqz` on the word leads to a tail
  jump out of the file; a `bgezal`, which is a call, comes before the call.
  Six matching mutations (the review's five, the definite rule's check
  counted once for each value), 91 in all: round 3's tests let all six
  through (`r4/survive_r3.py` / `.log`), and round 4's catch each with the
  case written for it (`r4/mutations.log`, `r4/subtest_check.py` / `.log`).
  The tool is unchanged. Of the review's five suggestions, two are adopted:
  the sample count (`r4/difficulty_samples.py` / `.log`, here and in the
  doc) and case 4's note above. The other three, resolving branches whose
  outcome is fixed, treating a `jr` other than `jr $ra` as a path the
  analysis cannot follow, and carrying the word across joins and delay
  slots, would change the analysis but no note on the disc (hypotheses), so
  they are deferred.
- Untracked (ignored): the evidence in `.cache/evidence/phase5-6/`, the
  remix dump and package in `.cache/zones/remix6/`.

## Phase 5 change 6 checks

- Round 1, `mutations.py` (change 5's script: the mutations whose code this
  change rewrote now target the new code, and 23 more for the formations):
  the unmodified copy passed, and all 67 planted bugs were caught.
- Round 1, `checks-p5-6.sh` / `.log` (staged tree; it computes the index
  tree in a scratch object directory, writes the tests', packages', remix's
  and mutations' files only to scratch, and runs no runtime): all pass. Nothing
  is unstaged or untracked, and only the five intended paths change. The
  handoff's header and its Phase 0 to Phase 5 change 4 sections equal HEAD.
  There is no placeholder, doubled blank line, heading without a blank line
  before it, added Markdown line over 80 columns, short line left by a
  reflow that HEAD does not have, stale wording or local path, and the
  Python files' longest lines stay within HEAD's. The three gates pass, the
  pins equal `framework_pins.txt`, the submodules are clean (`psxrecomp`
  ignores only `overlay_codegen_hash.h`), no tracked file is ignored, the
  tool and its tests are not, and packages and dumps are ignored anywhere.
  pyflakes is clean. On the disc, `check` rebuilds all 14 zones identically
  and `list` gives 5, 3, 15 and 10 formations; the scan, layout and
  disassembly logs reproduce; `make_remix6.py` reproduces the remix dump
  and `package` the same `.psxmod`, whose `disc_sha256` equals the `.bin`'s;
  `variant_guard.py` reproduces both logs. The tool's 46 tests pass, the
  three player's-disc tests included; `mutations.py` reproduces its log, 67
  of 67 planted bugs caught; the three route test files pass; nothing is
  left behind, and no `__pycache__` appears. The formation runs' log shows
  six passes and unchanged inputs (the tool hashed then is the staged one);
  `formation_compare.py` reproduces its log; every probe shows 1,309
  overlay instructions in seven rows; `build-dev/mods/state.toml` enables
  nothing. Nothing listens on ports 4370 to 4389, and `git diff --cached
  --check` is clean.
- Round 2, `r2/checks-p5-6-r2.sh` / `.log` (round 1's script, plus the delta
  from round 1's tree, which it rebuilds from the frozen index entries as
  `8b81d1d`, the dump's notes in all four zones and the tool the runs
  hashed): all pass. Nothing is unstaged or untracked, and only the five
  intended paths change, against HEAD and against round 1's tree. The
  handoff's header and its Phase 0 to Phase 5 change 4 sections equal HEAD.
  There is no placeholder, doubled blank line, heading without a blank line
  before it, added Markdown line over 80 columns, short line left by a
  reflow that HEAD does not have, stale wording (round 1's included) or
  local path, and the Python files' longest lines stay within HEAD's. The
  gates, pins, submodules and ignore rules are as in round 1, and pyflakes
  is clean. On the disc, `check` rebuilds all 14 zones identically and
  `list` gives 5, 3, 15 and 10 formations; the dump's notes name exactly
  five calls a branch can skip, all on the difficulty word: the 3RD ZONE's
  0x8013719C, 0x801371D8 and 0x80137214 (non-zero) and 0x80137258 (zero),
  and the 6TH ZONE's 0x80133EC0 (non-zero). The scan, layout and disassembly
  logs, the remix dump, the `.psxmod` (`62824c08…`) and both
  `variant_guard.py` logs reproduce. The tool's 48 tests pass;
  `mutations.py` reproduces its log, 76 of 76 planted bugs caught; the three
  route test files pass; nothing is left behind. The runs hashed round 1's
  tool (`bec15132…`); the staged one differs only in the dump's notes and
  the count check, and builds the same package byte for byte.
  `formation_compare.py` reproduces its log, each formation's last sample in
  its last step with all its members; every probe shows 1,309 overlay
  instructions in seven rows; `build-dev/mods/state.toml` enables nothing.
  Nothing listens on ports 4370 to 4389, and `git diff --cached --check` is
  clean.
- Round 3, `r3/checks-p5-6-r3.sh` / `.log` (round 2's script, plus the delta
  from round 2's tree, which it rebuilds from the frozen index entries as
  `fe799fe`, every timeline zone's dump compared with round 2's tool, and
  round 3's tests run against round 2's tool): all pass. Nothing is
  unstaged or untracked, and only the five intended paths change. The
  handoff's header and its Phase 0 to Phase 5 change 4 sections equal HEAD,
  and there is no placeholder, doubled blank line, heading without a blank
  line before it, added Markdown line over 80 columns, new short line left
  by a reflow, stale wording (rounds 1 to 3) or local path. The gates, pins,
  submodules and ignore rules are as before, and pyflakes is clean. On the
  disc, `check` rebuilds all 14 zones identically; all 14 dumps are
  byte-identical to round 2's tool's, so the notes name the same five
  calls; the scan, layout and disassembly logs, the remix dump, the
  `.psxmod` (`62824c08…`) and both `variant_guard.py` logs reproduce. The
  tool's 49 tests pass, the four player's-disc tests included;
  `mutations.py` catches the same 85 mutations as `r3/mutations.log`;
  `test_regression.sh` reproduces its log; the three route test files pass,
  and nothing is left behind. `formation_compare.py` reproduces its log,
  `build-dev/mods/state.toml` enables nothing, nothing listens on ports
  4370 to 4389, and `git diff --cached --check` is clean. The script's first
  run (`r3/checks-p5-6-r3-first.log`) found the mutation log different at
  one line: which tests catch the mutation that stamps zip entries with the
  current time depends on the clock (`test_package_names_and_versions` sees
  it only when its two packages fall in different 2-second DOS time slots;
  `test_package_puts_the_built_bytes_on_the_disc` always does), so the
  script now compares which mutations are caught and prints the lists that
  differ.
- Round 4, `r4/checks-p5-6-r4.sh` / `.log` (round 3's script, with the delta
  from round 3's tree, which it rebuilds from the frozen index entries as
  `f944f75`; the tool and `AGENTS.md` unchanged since round 3; round 4's
  evidence; and round 3's regression run pinned to round 3's test file,
  `r4/test_regression_r3.sh`, since `r3/test_regression.sh` copies the
  current one): all pass. Nothing is unstaged or untracked, and only the
  five intended paths change. The handoff's header and its Phase 0 to Phase
  5 change 4 sections equal HEAD, and there is no placeholder, doubled blank
  line, heading without a blank line before it, added Markdown line over 80
  columns, new short line left by a reflow, stale wording (rounds 1 to 4) or
  local path. The gates, pins, submodules and ignore rules are as before,
  and pyflakes is clean. On the disc, `check` rebuilds all 14 zones
  identically and the notes name the same five calls; the scan, layout and
  disassembly logs, the remix dump, the `.psxmod` (`62824c08…`) and both
  `variant_guard.py` logs reproduce, and so do `difficulty_samples.py`,
  `callback_inventory.py`, `case4_wording.sh`, `subtest_check.py` and
  `survive_r3.py`. The tool's 49 tests pass; `mutations.py` catches the same
  91 mutations as `r4/mutations.log`; the pinned regression run reproduces
  `r3/test_regression.log`; the three route test files pass, and nothing is
  left behind. `formation_compare.py` reproduces its log,
  `build-dev/mods/state.toml` enables nothing, nothing listens on ports
  4370 to 4389, and `git diff --cached --check` is clean.

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
  (change 6), all marked re-checked there. The launcher's Mods page lists
  the unlock package and turns it on (change 3); the two packages of change
  3 have not been seen there, and the test one is hidden.
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
- Zone data tool (changes 4 to 6): the game reads the tables the tool
  decodes, in the DEMONSTRATION replays of the fourteen zones, in HLE mode
  only (change 4). Edits have run in the 1ST ZONE only, in CAMPAIGN PLAY with
  no input, in all three boot modes: a retimed table (change 5) and two
  edited formations, an overlay that crosses a sector boundary (change 6).
  Other zones' remixes, "clear" waves, formations edited in the 2ND, 3RD or
  6TH ZONE, remixes played by hand, the launcher's install of a package and
  play in the play copy are untested. That edits up to a table's end, which
  covers every formation part, keep the static shard's variants valid is
  derived for all fourteen zones from their ranges; edits after the table
  are unknown. At run time it is seen in the 1ST ZONE only, and only change
  5's LLE SCPH-1001 "on" run shows that zone running nothing in the
  interpreter (in its other five runs the count's last step, up to 371
  instructions, falls between two samples). A remix runs only from the
  image its package names: a CHD of the same disc should hash
  the same (the runtime hashes its decoded sectors), but that is untested.
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
  unconditional `b` over an early return before the call gives "only on
  some paths" for a call that always runs; a call reached only through a
  `jr` jump table is attributed to code outside the table's callbacks, and
  a branch on the word to such a `jr` that can return to the call gets a
  definite note; where the word decides through a `bgtz`, a join or a load
  in a delay slot, the note says "only on some paths". None of these shapes
  is in the four zones: the 30 callbacks that reach the 33 calls use only
  `beq` and `bne` against zero, `j`, `jal` and `jr $ra`
  (`r4/callback_inventory.py` / `.log`), and the reviewer's own
  path-sensitive model, which follows the word through joins and delay
  slots and resolves branches whose outcome is fixed, agrees with every
  note. Fixing them is deferred.

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
- Phase 5 change 6, round 4: pending delta re-review.

## Next action

After a PASS: commit and push. The next step is the user's choice. A remix
can be tried in the play copy: dump a zone, edit its timeline or its
formations, `zone_data.py package` it, install the `.psxmod` on the
launcher's Mods page (or unpack it into
`.cache/play/build/mods/installed/<id>/<version>/`), enable it under Remix
and play that zone in CAMPAIGN PLAY or ZONE PLAY. For zone data, the
candidates: how the ten timeline zones without formations place their
enemies (their own overlay code, zone by zone); other enemies in a
formation, which is code (a plugin, or new code in the zone file); and a
remix pack worth playing. A committed remix route would need a runner option
for a run directory with an installed package, and the package built from
the player's disc. Follow-ups to the branching prototype stay open: branches
into the extra zones (each needs its result record redirected or protected,
see the doc's hazards); a test clear for the zones that end in their own
code, and runs of it in the other runner zones; a committed feature-on route
(a runner option for a run directory with its own `mods/state.toml`); a
whole campaign with instant clears, which would also show whether the
spike's post-credits halt happens with every zone loaded. The branching
option can be tried in the play copy: `play.sh` refreshes
`.cache/play/build/` from `build-dev/`, `mods/bundled/` included, and its
Mods page should list "Branching Campaign (prototype)" under Gameplay.

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

# Handoff — Omega Thrust

## Scope

Overall: recompile Omega Boost (USA, SCUS-94449) with psxrecomp nightly
`8077e71`, playable through the whole game, then compare against the Beetle
oracle. Phases: 0 inputs, 1 scaffold, 2 generate + build + smoke, 3 discovery
cycles through the whole game, 4 Beetle comparison. Phase 5, at the user's
request, is modding: unlocks, branching, new levels, and later perhaps a fan
sequel or remake that borrows Colony Wars' free-roaming structure.

Current iteration, Phase 5 change 5 (the first playable remix the user
chose: step 4 of `docs/MODDING_FEASIBILITY.md` section 6, limited to the wave
timeline), round 3. Invariant: `zone_data.py package <dump>` builds the zone
file as `build` does and writes a `.psxmod` (a zip with `manifest.toml` at
its root) whose one feature, `timeline`, off by default, is a `disc_user`
overlay of the stock table's slots at the zone file's sector times 2048 plus
the table's offset, so a shorter table also zeroes the slots it leaves. The
manifest targets SCUS-94449 with the sha256 of the disc image's data file,
which the runtime compares with the image it mounts, and guards the overlay
with the stock bytes' sha256, which the runtime checks before launch. The
package refuses what `build` refuses, ids and versions the framework would
reject, a `--name` that is not valid UTF-8, and outputs in the repository
outside `.cache/`; `*.psxmod` is ignored. With a scratch remix of the 1ST
ZONE packaged and installed in a copy of `build-dev`, in all three boot
modes, the game loads the remixed table, the zone ends with no input and
shows its results, and the campaign goes on to the 2ND ZONE; with the
feature off the stock table loads and the zone does not end in the same
frames. The zone's precompiled code keeps running: in none of the fourteen
zones does a matching static variant guard a byte before the table's end,
the 1ST ZONE's variants all match the remixed file, and the runs interpret
as much overlay code as the stock route, in seven rows that all exist
before the zone file loads. The tests cover the package (a shorter table
and one across two sectors among them), the table reader's loop bound
(change 4's review) and output paths that are not valid UTF-8, which the
tool prints escaped, and fail when bugs are planted. `AGENTS.md` documents
the command; the doc records step 4's state and change 4's two wording
suggestions; this file records change 4's PASS and commit `b19fbe4`,
condenses change 4 and applies its other two suggestions. Baseline:
`b19fbe4`. Out of scope: formation edits; a committed remix or route (a
remix holds disc data, and a route would need a runner option for an
installed package); Beetle (it runs no mods); plugins, hook sites and
regenerating; runner, driver, framework and submodule changes; play
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

## Phase 5 change 5 observations (`.cache/evidence/phase5-5/`)

- Disc overlays (`psxrecomp/docs/MOD_PACKAGES.md`, "Feature manifest" and
  "Native operations"): an `[[overlay]]` names its feature, a target
  (`disc_user`, whose offset is the sector times 2048 plus the byte, or
  `disc_raw`, the sector times 2352 plus the byte; `mod_runtime.cpp:271-282`),
  an offset, a file in the package and its sha256, and optionally
  `expected_sha256` over the stock range; every `[[target]]` of a package
  with overlays needs an exact `disc_sha256`. The runtime copies the part of
  the payload that falls in each sector the CD path reads, raw Mode 2 Form 1
  sectors through their user-data window (`mod_runtime.cpp:2547-2626`). At
  launch it hashes the stock range under each overlay and refuses to start
  on a mismatch (`:1628-1640`), and it matches `disc_sha256` against
  `sha256_file` of the mounted image (`mod_packages.cpp:673-687`;
  `mod_runtime.cpp:349-400`). That hashes the image's data: for a cue sheet
  the data file it names, for a CHD its decoded raw sectors. A `.psxmod`
  is a zip with `manifest.toml` at its root; installing one refuses a
  version already installed (`mod_packages.cpp:2908-2976`); entries may be
  stored or deflated (`:376`); the version must be semantic (`:1741`).
- First attempt: the package named the cue sheet's own sha256, and the
  runtime refused to launch ("cannot launch with selected mods: package
  does not target this game/image"; that run's outputs were overwritten by
  the next, not saved). The probe then waited for its 30-minute deadline;
  it now gives up after 180 s without a runtime.
- Static variant guards: a variant runs only while the CRC-32 of the live
  RAM over its code ranges equals its compiled CRC (`overlay_loader.c`,
  `range_candidate_matches` and `ov_ranges_crc`). `variant_guard.py`
  recomputes it for the shard's 34,846 variants: for each of the fourteen
  timeline zones, the variants that match the stock file share one function
  prefix (the 1ST ZONE 1,391), and none has a code range over the zone's
  table or starting anywhere before the table's end: the lowest byte a
  matching variant guards is the table's end in nine zones and later in the
  other five (`variant_guard-all.log`; round 2 added the second count). All
  1,391 also match the remixed 1ST ZONE (`variant_guard-s1.log`). The
  matches themselves show that the CRC is zlib's.
- The remix (`make_remix.py`, written to `.cache/zones/remix/`): the 1ST
  ZONE's first four stock waves at 60 ticks each, then the end entry, the
  last five slots zeroed. Its package's 80-byte overlay sits at offset
  230,015,220 (sector 112,308 times 2048 plus 0x20F4); `disc_sha256` equals
  `sha256sum` of the `.bin` (`fb84ce3e…`).
- Runs (`remix_runs.sh` / `.log`, 15:44 to 15:49; a scratch copy of
  `build-dev` (`da70e6c0…`) with the package unpacked into
  `mods/installed/` and its own `mods/state.toml`; port 4373; route
  `remix_s1.json`, 50 steps and 11,286 frames: boot to CAMPAIGN PLAY, start
  the 1ST ZONE, 16 times 300 neutral frames with a shot, two Cross presses):
  all six runs passed (start frames 46 to 121, no miss, exit 0), the inputs'
  hashes did not change, and nothing was left listening. With the feature
  on, in every mode (`summary.log`), the remixed table was in RAM whenever
  the 1ST ZONE was in use, the player's state became 6 (cleared) by route
  frame 6,803 to 6,962, the zone's record read 333 clear frames, 15 spawned,
  0 destroyed and grade 2, and the 2ND ZONE loaded by route frame 7,924 to
  8,068. The screens show COMPLETED with CLEAR TIME 0:11.10, DESTROY RATIO
  0% (0/15), RANK B (50pts) and SCORE BONUS 12800, then "2ND ZONE"
  (`remix-compare_sheet.png`); 11.1 s agrees with (4 x 60 + 90) ticks at
  0.493 ticks per frame (Derived). With the feature off, the stock table
  loaded and the zone neither ended nor wrote its record; at the same point
  the stock zone shows its asteroid base. `summary-first.log` is the summary's
  first output: it took a zeroed or reset record as written and a boot-time
  sample whose scene word happened to read 5 as the 1ST ZONE.
- Precompiled code: every run interpreted 1,309 overlay instructions in seven
  rows, one per address, as change 3's stock title_to_zone1 run did. The
  probes keep only the five largest rows; those match that run by address
  and count (`same_point.log`), and the other two hold the remaining 15.
  Earlier samples, taken while those two were still among the five largest,
  name 0x80126160 (seen with 9 instructions) in all six runs and 0x801261AC
  in the LLE SCPH-1001 "on" run (`r2/pc_rows.py` / `.log`; round 1 said all
  seven addresses matched). In every run all seven rows existed from route
  frame 5,651 to 5,789 on, while the briefing's file (scene 25) was loaded,
  and no count ever fell, so the zone added no row. In the LLE SCPH-1001 "on"
  run the count was final at route frame 5,961, still in the briefing, so
  that remixed zone ran nothing in the interpreter; in the other five runs
  the last step, 42 to 371 instructions (3% to 28% of the count;
  `r3/last_step.log`), falls between a briefing sample and the first sample
  with the 1ST ZONE's file loaded (`insn_timing.log`). At the same point in the
  zone, the "on" runs had 9 more static CRC misses and variant misses than
  the "off" runs in every mode (356 and 347; 1,294 and 1,285), with no
  interpreted instruction more (hypothesis: the remix's other code path
  checks other files' variants at shared addresses).

## Phase 5 change 5 changes

- `scripts/zones/zone_data.py`: the `package` command (`--id`, default
  `omega.remix.<zone>`; `--name`, default "<zone> Remix"; `--version`,
  default 1.0.0; `--out`, default `.cache/zones/<id>-<version>.psxmod`), as
  in `AGENTS.md`, Zone data; `Disc.image_sha256` hashes the data file;
  `load_dump`, shared by `build` and `package`; the docstring describes
  packages. Ids follow the framework's rule, versions are three numbers
  without leading zeros (a subset of what the framework accepts), manifest
  strings use JSON's escapes, which are valid TOML, and the archive's
  entries are stored with fixed times, so the same input gives the same
  bytes.
- `scripts/zones/test_zone_data.py`: five tests more. One applies a
  package's payload to the synthetic image at the declared offset and reads
  the zone file back through the tool's disc reader: it equals the file
  `build` writes; it also checks the manifest's fields and hashes. Others
  cover ids, names with quotes, versions (and the same bytes twice), output
  in the repository, what `build` refuses, and a table that runs to the end
  of the file (change 4's round-2 suggestion: the read loop's bound). On the
  player's disc, an unedited package's payload equals the bytes at its
  offset in the `.bin`.
- `.gitignore`: `*.psxmod`, named in the header.
- `AGENTS.md`: the never-commit list names the packages; Zone data gains the
  `package` command and a paragraph on the package, its hashes, the
  precompiled code and playing one headless.
- `docs/MODDING_FEASIBILITY.md`: the intro, the brief answer and section 6
  mark step 4's timeline part done; step 4 records the runs and the shard
  result. Change 4's round-2 suggestions for the doc: 0x80063C5C's 17
  entries are across the fourteen zones, and "timing and placement are data
  in the `.BIN`" is limited to the zones it covers.
- `.agent/HANDOFF.md`: this scope; change 4 condensed (its round-2
  suggestions: the 17-entry count in its section, the short line gone with
  the condensed sections, the mutation bound in the review state); these
  sections; the hypotheses; the review state; the next action.
- Round 2 (review round 1's three Low findings, `review-r1.md`): the doc's
  step 4 says edits up to a table's end keep the variants valid, with the
  reason, and gives the interpreter result as above, labelled Derived;
  section 7 asks only about data after the table. A new test packages a
  table one wave shorter: its payload covers all four stock slots, and the
  zone file read back holds a zero slot. The suggestions adopted: the package
  test checks the zip entries' fixed times and the feature's group; manifest
  strings escape U+007F, and a `--name` that is not valid UTF-8 is refused
  with a one-line error (both tested; the remix's package is unchanged); a
  table across a sector boundary packages and reads back like any other (the
  tool's side only: the runtime lists an overlay under every sector it
  touches and copies each sector's part, `mod_runtime.cpp:271-282` and
  `:2613-2628`, but no run has played such a package); the end-of-file test
  adds a table ending 4 bytes before the file's end; `AGENTS.md` gives the
  default id in lowercase and says that with the feature on the runtime
  refuses any other image; this file's `disc_raw` offsets count 2352-byte
  sectors, and it closes the deferred naming of the last two interpreted
  title_to_zone1 PCs. Evidence: `variant_guard.py` also counts variants
  starting before a table's end, `r2/pc_rows.py`, and six more mutations in
  `mutations.py`.
- Round 3 (review round 2's one Low, `r2/review-r2.md`): the doc gives the
  count's last step in the other two remix runs, 98 and 371 instructions
  (`r3/last_step.py` / `.log`), instead of "the last few instructions". Its
  four suggestions adopted: the sector-crossing test's table moved to
  0xFF0-0x1010, in the file's second and third sectors, with the expected
  offset derived from the synthetic image's layout, so it now catches an
  offset that drops the table's sector within the file; the tool prints
  paths that are not valid UTF-8 escaped (`sys.stdout` with
  `backslashreplace`, for `dump`, `build` and `package`), where it wrote the
  file and then failed with a traceback, and a test covers it; the scope's
  one-word line is gone; and the framework's TOML parser, toml11, which the
  runtime reads manifests with (`mod_packages.cpp:1691`), parses both a
  default and an escaped manifest to the exact name bytes and rejects a raw
  U+007F (`r3/toml11_check.py` / `.cpp` / `.log`). Two mutations more in
  `mutations.py`.
- Untracked (ignored): the evidence in `.cache/evidence/phase5-5/`, the
  remix dump in `.cache/zones/remix/` and its package.

## Phase 5 change 5 checks

- Round 1, `checks-p5-5.sh` / `.log` (staged tree; it computes the index
  tree in a scratch object directory, writes the tests', the package's and
  the remix's files only to scratch, and runs no runtime): all pass. Nothing
  is unstaged or untracked, and only the six intended paths change. The
  handoff's header and its Phase 0 to Phase 5 change 3 sections equal HEAD.
  There is no placeholder, doubled blank line, heading without a blank line
  before it, added Markdown line over 80 columns, local path or stale
  wording, and the Python files' longest lines stay within HEAD's (97 and
  102). The three gates pass, the pins equal `framework_pins.txt`, the
  submodules are clean (`psxrecomp` ignores only `overlay_codegen_hash.h`),
  no tracked file is ignored, the tool and its tests are not, and packages
  and dumps are ignored anywhere. pyflakes is clean. On the disc, `check`
  rebuilds all 14 tables identically; `make_remix.py` reproduces the remix
  dump and `package` the same `.psxmod`, byte for byte, whose `disc_sha256`
  equals the `.bin`'s sha256; `variant_guard.py` reproduces both logs. The
  tool's 30 tests pass, the two player's-disc tests included;
  `mutations.py` reproduces its log, with 36 of 36 planted bugs caught; the
  three route test files pass; nothing is left behind, and no `__pycache__`
  appears. The remix runs' log shows six passes and unchanged inputs (the
  tool hashed then is the staged one); `summarize.py`, `same_point.py` and
  `insn_timing.py` reproduce their logs; `build-dev/mods/state.toml`
  enables nothing. Nothing listens on ports 4370 to 4389, and `git diff
  --cached --check` is clean. The host's Python is now 3.14.8, where
  `AGENTS.md` records 3.14.7.
- Round 2, `r2/checks-p5-5-r2.sh` / `.log` (staged tree, as round 1; it also
  rebuilds round 1's tree from its frozen index entries and shows the
  delta): all pass. Round 1's checks hold again, with these changes: the
  stale-wording list adds the phrases round 1's findings named; the tool's
  33 tests pass, and `mutations.py` catches all 42 planted bugs, each of the
  six new ones by the test written for it (`r2/mutations.log`); the staged
  tool, which differs from the one the remix runs hashed only in the
  U+007F escape and the `--name` check, builds their package byte for byte;
  `all_packages.py` shows every unedited package equal to the disc, U1's
  across two sectors (`r2/all_packages.log`); `variant_guard.py` reproduces
  both logs, now with no matching variant starting before any table's end;
  `pc_rows.py` reproduces its log, and the remix route plays
  `title_to_zone1`'s input for that route's 7,674 frames.
- Round 3, `r3/checks-p5-5-r3.sh` / `.log` (staged tree, as round 2; the
  delta is from round 2's tree, rebuilt from its frozen index entries): all
  pass. Round 2's checks hold again, with these changes: the stale-wording
  list adds "the last few instructions", which now appears only where this
  file quotes it (three lines); the tool's 34 tests pass, and
  `mutations.py` catches all 44 planted bugs, the two new ones by the tests
  written for them (`r3/mutations.log`); the staged tool still builds the
  remix runs' package byte for byte; `last_step.py` and `toml11_check.py`
  reproduce their logs.

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
  and records (change 3) and the wave timeline (change 4), all marked
  re-checked there. The launcher's Mods page lists the unlock package and
  turns it on (change 3); the two packages of change 3 have not been seen
  there, and the test one is hidden.
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
- Zone data tool (change 4): the game reads the tables the tool decodes, in
  the DEMONSTRATION replays of the fourteen zones, in HLE mode only (change 4).
  An edited table has run in one zone only: the 1ST ZONE's scratch remix,
  in CAMPAIGN PLAY with no input, in all three boot modes (change 5). Other
  zones' remixes, remixes with "clear" waves, remixes played by hand, the
  launcher's install of a package and play in the play copy are untested.
  That edits up to a table's end keep the static shard's variants valid is
  derived for all fourteen zones from their ranges; edits after the table
  are unknown. At run time it is seen in the 1ST ZONE only, and only the LLE
  SCPH-1001 "on" run shows that zone running nothing in the interpreter (in
  the others the count's last step, up to 371 instructions, falls between
  two samples). A remix runs
  only from the image its package names: a CHD of the same disc should hash
  the same (the runtime hashes its decoded sectors), but that is untested.
  The 8TH ZONE's table has no end entry: if its last wave were ever cleared
  before the zone's own code ends the zone, the runner would take the debug
  string after the table as an entry (Derived; never seen). A table across
  a sector boundary (U1's) has packaged correctly, but no such package has
  run in the game. The formation records' steps and second
  table, and what the callbacks' two counts mean, are not decoded, nor how
  the waves of the ten timeline zones that never call 0x80057F0C place
  their enemies.

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
- Phase 5 change 5: round 1 NEEDS CHANGES on tree `f3967fd` (staged diff
  `355db600…`; three Low: the doc called data-only edits re-checked though
  only the table was checked, and section 7 still listed the question; the
  interpreter comparison named seven addresses where the probes keep five
  rows, and rested on equal counts rather than on when they grew; no test
  packaged a shorter table, so sizing the overlay from the built table went
  uncaught). Report: `phase5-5/review-r1.md`. All three are resolved and its
  eight suggestions adopted (changes, round 2).
- Phase 5 change 5, round 2: NEEDS CHANGES on tree `85d92ee` (staged diff
  `7e1674ae…`; one Low: the doc's "the last few instructions" understated
  the count's last step, up to 371 instructions), after confirming round 1's
  three findings and eight suggestions resolved. Report:
  `phase5-5/r2/review-r2.md`. Resolved in round 3, which also adopts its
  four suggestions (changes, round 3).
- Phase 5 change 5, round 3: pending delta re-review.

## Next action

After a PASS: commit and push. The next step is the user's choice. A remix
can be tried in the play copy: dump a zone, edit it, `zone_data.py package`
it, install the `.psxmod` on the launcher's Mods page (or unpack it into
`.cache/play/build/mods/installed/<id>/<version>/`), enable it under Remix
and play that zone in CAMPAIGN PLAY or ZONE PLAY. For zone data: decode how
waves place their enemies. In the 1ST, 2ND, 3RD and 6TH ZONE that is the
formation records passed to 0x80057F0C (the steps that word 0 points to,
the second table, the two counts; through 0x80057F0C, its update 0x80058300
and the per-member spawn functions); the other ten timeline zones go
through their own overlay code, which needs reading zone by zone. A remix
pack worth playing, and a committed remix route (it would need a runner
option for a run directory with an installed package, and the package
built from the player's disc), are later steps.
Follow-ups to the branching prototype stay open: branches into the extra
zones (each needs its result record redirected or protected, see the doc's
hazards); a test clear for the zones that end in their own code, and runs
of it in the other runner zones; a committed feature-on route (a runner
option for a run directory with its own `mods/state.toml`); a whole campaign
with instant clears, which would also show whether the spike's post-credits
halt happens with every zone loaded. The branching option can be tried in
the play copy: `play.sh` refreshes `.cache/play/build/` from `build-dev/`,
`mods/bundled/` included, and its Mods page should list "Branching Campaign
(prototype)" under Gameplay.

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

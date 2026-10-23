# Modding feasibility

Research done on 2026-10-20 into modding Omega Boost through this
recompilation: unlocks, a branching campaign, remixed and new zones, missions
in the style of the Colony Wars series, and a possible fan sequel or remake.
Steps 1 and 2 of the recommended path (section 6) are now implemented, the
wave timeline and formation parts of steps 3 and 4, and step 4's first remix
pack, and step 5's spike has run in scratch; nothing else here is. The
evidence (scripts, logs and saved web pages) is in
`.cache/evidence/mod-research/`, which is ignored and exists only on the
machine that did the research; evidence file names below are relative to
it.

Labels: Observation (seen in source, disc files or command output), Derived
(worked out from named observations), Reference (external pages), Hypothesis,
Unknown. "Agent" marks a research agent's static analysis of the disc;
"re-checked" marks a claim checked again against the disc or the pinned
source.

## The answer in brief

| Goal | Verdict |
|---|---|
| Unlocks | Easy |
| Branching campaign | Medium |
| Remixed zones | Medium, after tooling |
| New zones | Hard |
| Colony Wars-style missions on Omega Boost's combat | Hard, long-term |
| Free flight through a world | Remake scale |
| Fan sequel or remake | Depends on the route (section 6) |

- Unlocks: a plugin writes the game's unlock flags (done: section 6, step 1),
  or a guarded EXE patch edits the unlock-rule table. A new kind of unlock
  condition needs EXE and TITLE.BIN code changes.
- Branching campaign: a plugin hook in the campaign loop picks the next step
  from the finished zone's results, which are in RAM when the loop resumes
  (prototype done: section 6, step 2). The script has no condition field,
  and a branch must keep the scene entry pointer and the result slots
  consistent. A test option that clears zones instantly lets scripted runs
  reach each branch without live play.
- Remixed zones: edit a zone's wave timeline and formation tables, which are
  data inside its `.BIN`, and ship them as same-size disc overlays. Both are
  decoded, and a tool turns them into editable text and back (section 6,
  step 3) and packages the edits as a mod the game loads, with the zone's
  precompiled code still running (step 4). A remix recipe, which holds only
  edits, builds one mod for several zones (step 4's first pack, Crossfire).
  What a formation's members are is the zone's code, the ten timeline zones
  without formations start their waves through their own code, not yet read,
  and a same-size overlay cannot make a file longer, though a package can
  give a zone a new file in new sectors (step 5; a longer file is untested).
- New zones: a new `.BIN` linked at 0x80120000 against the EXE's fixed
  addresses, plus models, textures and sound. The plumbing works (section 6,
  step 5): the game finds a new file through a directory record a package
  adds, with its sectors in the disc's empty postgap or appended after the
  disc by a plugin. A cut scene index (23, P2) loads, starts and ends a zone
  after a few data patches, but only on psx-runtime: with no name of its
  own, its name lookup reads a word at a misaligned address, which Beetle
  and the console's CPU treat as an exception (Derived). It also lacks the
  rest of a zone's place in the game: its result record lands on settings,
  it has no results screen or music, and the tables it reaches are sized for
  the existing zones. Writing the zone itself needs a MIPS toolchain and a
  map of the EXE functions that zones call.
- Colony Wars-style missions: a plugin mission layer reads text mission files
  shaped like Colony Wars' and drives the game's own wave engine, with a
  branching mission graph and a hub. Objectives, the hub screen and the
  mission graph are all new code, and the framework has no menu API.
- Free flight: replace the movement, enemy spawning, camera and streaming
  code, or build in a new engine. Omega Boost's design leaves out distance and
  terrain on purpose, and the PS1's limits remain.

The recomp is a good base for an "Omega Boost+": unlock options, a branching
campaign, remixed zones and, with more reverse engineering, new zones built
from the game's own engine code. Colony Wars-style free roaming is a different
design. Omega Boost's designer kept distance, terrain and travel out on
purpose, and Colony Wars' own "free roaming" is bounded mission arenas linked
by mission outcomes. A realistic hybrid therefore takes Colony Wars' mission
structure (arenas with objectives, a branching mission graph, a hub) and wraps
it around Omega Boost's combat. Real travel through open space means
replacing the core of the engine, which is remake-scale work.

## 1. What the recomp lets a mod do (psxrecomp `8077e71`)

Checked against the pinned source (`framework-check.txt`).

- Mod packages carry no native code. In this repository a package is a
  directory, `mods/preloaded/packages/<id>/<version>/manifest.toml`, which the
  build stages into `<exe>/mods/bundled/`; players install `.psxmod` archives
  (`psxrecomp/docs/MOD_PACKAGES.md:15-37`). A package can hold:
  - guarded, equal-length patches to the boot EXE, applied once before its
    entry point, which can change the game's code as well as its data
    (`psxrecomp/docs/AOT_SHARDING.md:138-139`);
  - guarded, equal-length patches to disc sectors, and file-backed disc
    overlays that need an exact disc hash;
  - launcher options, player-selected resource files (checked by size and
    SHA-256), and requirements on other packages.

  It cannot load native code or select arbitrary symbols
  (`MOD_PACKAGES.md:954-957`), and the manifest format has no expression
  language (`:290-291`).
- Game-owned plugins are C code in this repository, compiled into
  `Omega_Thrust`, registered before `main()` (`PSX_MOD_CONSTRUCTOR`,
  `psxrecomp/runtime/include/mod_plugins.h:890-908`) and switched on by a
  package. They can:
  - hook or replace game functions;
  - run before chosen instructions (these hooks may change registers and
    memory, but not the PC);
  - read and write guest memory, and call game functions;
  - put data into RAM the way a CD DMA would, and read disc files;
  - append sectors after the end of the disc from a verified resource;
  - use extra memory and inject input.
- Linking (`plugin-linking.log`, `cmake-repeat-keyword.log`):
  - Tomba2Recomp, MegaManX4Recomp and MegaManX6Recomp pass their plugin
    sources from `src/mods/` as `EXTRAS_SOURCES`.
  - Here they would go into `psxrecomp_add_game_runtime` as `EXTRAS_SOURCES`,
    above `GEN_FULL_GLOB`. The function forwards keywords it does not parse
    (`psxrecomp/runtime/runtime.cmake:2527-2547`, `:2727`) ahead of its own
    `EXTRAS_SOURCES` (`:2750`), and CMake 4.4.4 keeps the values of both
    (tested).
  - Native code reaches a hook only at sites listed in `game.toml`
    (`[recompiler] mod_function_entry_funcs` and `mod_instruction_sites`, as
    Tomba2Recomp lists them), so adding a site changes `generated/`, which is
    then regenerated and committed (Derived).
- Cost:
  - Changed game code runs in the interpreter, which a framework comment puts
    at about 300 ns per instruction
    (`psxrecomp/runtime/include/dirty_ram_interp.h:118-119`).
  - The committed overlay shard selects compiled code by a CRC of the live
    bytes.
  - A package's static declarative edits (equal-length EXE patches,
    `disc_user` patches and file-backed overlays) can be listed in
    `aot/overlays.json` and compiled ahead of time; `replace_from`, `fields`,
    `when_integer` and `disc_raw` operations cannot
    (`psxrecomp/docs/AOT_SHARDING.md:136-166`).
- Persistence:
  - A mod's own memory is saved only in save states
    (`psxrecomp/runtime/include/mod_memory.h:55-62`).
  - The player's option values and resource paths persist in
    `mods/state.toml` (`MOD_PACKAGES.md:27`, `:865`). A plugin can read them
    (`psxrecomp/runtime/include/mod_plugins.h:309-343`) but has no call that
    changes them; its write calls target guest memory: RAM (`:121-171`), SPU
    RAM (`:178`) and VRAM (`:184`).
  - So progress a mod adds during play, such as a branch the player took,
    belongs in bytes the game itself saves (Derived).
- Rules: per-game shims are "the legitimate tool of the *enhancement* phase"
  once the faithful core is proven (`psxrecomp/CLAUDE.md:33-38`), and title
  mod code lives in the game repository. The route suite and the Beetle oracle
  can show that the stock game is unchanged while a mod is off.
- Precedents (Reference; README lines saved in `precedents.log`):
  - [MegaManX6Recomp][mmx6] preloads "15 package families with 203
    independently configurable, default-disabled feature rows", adapted from
    acediez's Mega Man X6 Tweaks, a project with a Romhacking.net thread,
    whose author "explicitly granted permission".
  - [MegaManX4Recomp][mmx4] has an X + Zero co-op mod.
  - [Tomba2Recomp][tomba2] has a Debug Menu, withheld from its bundled
    catalog because it "causes severe slowdown".
  - None of the packages the framework agent surveyed adds a new level.

## 2. How Omega Boost is put together

Mostly from the internals agent. Its table dump reproduces from the disc
(`internals/tables.txt` against `internals/tables-rerun.txt`: only the save
file paths differ, `internals/tables-rerun.diff`), and `verify_internals.py`
/ `.log` re-checks the scene tables, the campaign script and the save
checksums independently.

### Scenes and files

- Every scene has an index:
  - 0 is the boot-time COMMON set.
  - 1 to 40 follow the debug name list at 0x80097F20: T0, T1, Z1 to Z9 (disc
    directories S1 to S6 and S8 to S10), U1 to U9, V5, TRAINING, P2, BRIEFING1
    and 2, SOUND_TEST, P0, seven MOVIE entries, CARD, VIEW_MODEL, G0, gallery,
    title and logo (re-checked).
  - Parallel tables give each index a `.BIN`, texture and model files for each
    of 7 languages (this disc has only AMERICAN), and a sound bank.
- Missing from the disc: the `.BIN`s of T0, T1, P2, SOUND_TEST, P0, CARD,
  VIEW_MODEL, G0 and gallery (re-checked), plus their data files.
  - P2 looks like a cut zone (Derived): it has S2's sound bank, its own
    rating parameters (slot 20, near the 6TH ZONE's; see the zone slots
    below), and four checks in the EXE count it among the zones: index - 3
    below 19, or index 23 (on the scene index at 0x8002FD94 and 0x8003001C,
    and on the word at 0x8009C7D0 at 0x8002E658 and 0x8002FAF0; re-checked
    in Phase 5 change 8, evidence in `.cache/evidence/phase5-8/`).
  - Retail code never enters the gallery (state 12) or the debug scene select
    (state 13): no store writes 12 or 13 to the state word (agent).
- The loader (0x800759CC) works as follows (agent; the branch at 0x80075AEC
  and the two data addresses re-checked in the disassembly):
  - It loads the `.BIN` at 0x80120000.
  - Textures (OMT: a count plus standard TIM images) go just past the `.BIN`,
    at its end plus 16 rounded down to a multiple of 16 (0x80075BE0 to
    0x80075BFC), and on to VRAM. Models (OMD: relocatable records) then load
    at the same address.
  - A scene without a `.BIN` puts its data at 0x80120000 (0x80075AF4 to
    0x80075B00). These are the four instructions that `aot/overlays.json`
    checks.
- Files are found by name at load time through the PsyQ libds library
  (DsSearchFile at 0x80080794, re-checked in Phase 5 change 8). The
  loader's steps pass a path from the scene's table entry to 0x80080384 (by
  its use, DsReadFile: it takes the path and a load address) and poll it;
  the `.BIN` step goes back to its first step when a read fails (0x80075C30
  to 0x80075C4C), so a missing file stalls the load (Derived). DsSearchFile
  re-reads the path table when a media counter changes (0x8007E5C8 against
  0x80098CC8), finds each directory of the path in it, and caches one
  directory at a time: 0x80080DFC reads only that directory's first sector,
  into 0x80111040, keeps its records at 0x8010F440 (24 bytes each:
  position, size, name) until it meets an empty record, has 64 or reaches
  the sector's end, and reads again only when another directory is asked
  for (its number is at 0x80098CC4). A name matches on its first 12
  characters, version included (0x80080A74 calls a compare with a limit of
  12). The agent also read a limit of 128 directories (not re-checked). The
  root directory has 108 bytes free and each scene directory about 1,660;
  the S1 directory, at LBA 112307, has 1,668 after its five records
  (`.cache/evidence/phase5-8/disc_layout.log`).
- After loading, a switch (0x8002AD70) jumps through a table of 42 words at
  0x800123E0, one per scene index, to a case that calls the scene's init
  (re-checked; the list of inits is in `internals/tables-rerun.txt`).
  - The init relocates the scene's models and stores its entry function at
    0x800A7940; the play loops call the overlay through that pointer.
  - Indices 0, 1, 2, 23, 27, 35 to 37 and 41 have no case: their entries
    point at the switch's exit, 0x8002AFA8 (re-checked), so supplying the
    missing files of 1, 2, 23, 27 or 35 to 37 alone would not make them
    run. SOUND_TEST (26) and the gallery (38) have init addresses, but only
    the unreachable states 13 and 12 load them (agent).
  - The generated code reads the table from RAM and resumes at the case it
    names, so changing one word gives an index another index's init (step
    5's spike, section 6).
- The EXE turns a scene index into a zone slot, index - 3, keeping it only
  if it is below 21, at 15 places (re-checked in the code around the 42
  references to the index that a scan finds, 30 loads, 2 stores and 10 that
  form its address: `.cache/evidence/phase5-8/xref.log`). Slots 0 to 8 are
  the campaign zones, 9 to 18 U1 to U9 and V5, 19 TRAINING and 20 P2; any
  other index gets slot -1.
  - The tables of the rating's time and destroy parameters (0x800136C8 and
    0x80013770, a pair of words a slot) have all 21 entries, as does a jump
    table at 0x80014258 indexed by the slot. P2's pairs are [7200, 14400]
    and [4096, 819], near the 6TH ZONE's [7500, 14400] and [4096, 819];
    TRAINING's are zeros. The time pairs look like clear times in the
    record's unit, 1/30 s (P2's would be 4:00 and 8:00).
  - The zone names (0x80097E48: for each slot a pointer to seven strings,
    one per language) have 20 entries, so slot 20 takes the next word, 9,
    the first of the unlock rules' tables (0x80097E98), as its pointer. The
    title card (0x80054B34) and the pause screen (0x80038BFC) both load the
    word at that pointer plus 4 times the language index (0x80054DF0,
    0x80038DE0), and 9 plus a multiple of 4 is never a multiple of 4.
    psx-runtime's load copies the four bytes without checking alignment
    (`psxrecomp/runtime/include/psx_cyc.h:253-255`). Beetle raises an
    address error exception for such a load (beetle-psx
    `mednafen/psx/cpu.cpp:2377-2382`, as `scripts/build_beetle.sh` builds
    it), as the console's MIPS R3000A does (Derived; run on neither).
  - Music is started only for indexes 3 to 11: 0x80056FCC jumps through a
    9-entry table (0x80014688) to `0x80076ABC("\OBBGM2.XA;1", channel, ...)`,
    channels 0 to 6, with the 7TH ZONE on channel 1 and the 8TH ZONE's entry
    starting none.
- A zone `.BIN` holds an id word, debug strings, then data tables (formations,
  paths, the wave timeline), then code (agent):
  - S1: 8.5 KB of data, then about 45 KB of code in about 55 functions.
  - U1: 2.2 KB of data, then 5.6 KB of code.
  - Overlays call EXE functions at fixed addresses with no import table: S1
    calls 56 of them, TITLE 77.
- The wave timeline (re-checked in Phase 5 change 4: the EXE's runner and
  task code, the tables on the disc, and the runner in the running game;
  evidence in `.cache/evidence/phase5-4/`):
  - Fourteen zones pass a table to the runner's constructor (0x80071624):
    the 1ST to 4TH and 6TH to 8TH ZONE, U1 to U4 and U6 to U8. The 5TH
    ZONE, the LAST ZONE, U5, U9 and V5 have no runner.
  - An entry is 8 bytes: a callback in the zone's code, which starts a wave,
    and a delay. The constructor runs entry 0 at once, without checking it.
    The runner ticks about once every two frames (0.493 ticks per frame over
    the timed entries sampled in twelve zones' replays; U1 and U8 gave
    none), and moves to the next entry when the delay runs out, or as soon
    as it has no child task left: the tasks the wave callbacks create are
    its children. A delay of -100 waits only for that. A callback of 0 is
    the end entry: 90 ticks later the runner calls the clear routine and
    removes itself.
  - The 1ST ZONE's table has five timed waves and four of -100, as the agent
    found. U1 to U4 and U6 have two waves, U7 three and U8 one. The 8TH
    ZONE's table has no end entry: its three entries run into a debug
    string. In the replays (HLE mode) the runner reached the end entry in
    eleven zones; in the 8TH ZONE, U4 and U8 it was still waiting at its
    last wave when the zone ended, through its own code (Derived), so the
    8TH ZONE's runner never read past its table.
  - The callbacks start their waves through EXE or overlay code. Only the
    1ST, 2ND, 3RD and 6TH ZONE's files call 0x80057F0C: 38 of the 121
    entries (30 of the 95 distinct callbacks) pass it a formation record
    from the zone's data and two counts, then call an overlay function once
    per member ("Formations" below). The commonest other call, 0x80063C5C
    (17 entries across the fourteen zones, 11 of them in the ten without the
    formation call), starts a timer task under the runner, which counts a
    word down each tick (update 0x80063D04).

  So in the fourteen zones with a timeline, wave timing is data in the
  `.BIN`, and so is placement in the four with the formation call; behaviour
  is `.BIN` code calling the EXE, and the model and texture files hold only
  models and textures (agent, Derived).

### Formations

Re-checked in Phase 5 change 6: the EXE's formation code, the four zones'
callbacks and member code, the records on the disc, and the formation tasks
in the running game (evidence in `.cache/evidence/phase5-6/`).

- 30 wave callbacks in the 1ST, 2ND, 3RD and 6TH ZONE pass 0x80057F0C 33
  records (5, 3, 15 and 10), each its own. Five start on only one value of the
  difficulty word, 0x800A7C34, which the zone handler sets: the 3RD ZONE's
  wave-17 callback starts 0x8012227C, 0x80122320 and 0x801223C4 while the word
  is non-zero and 0x8012248C while it is zero, and the 6TH ZONE's wave-10
  callback starts 0x80121F50 only while it is non-zero; the dump's notes say
  so. The word was 0 in all 2,829 samples of change 3's campaign runs, 1,646 of
  them in zones 1 to 5, and the OPTION screen offers NORMAL, the default, and
  HARD (the `menus` route's `13-option.png`), so non-zero is presumably HARD
  (inference). The call takes the parent task, the record and, as instruction
  immediates in the callback, its numbers of steps and members. It starts a
  task of 0x50 bytes under the parent (update 0x80058300; its destructor,
  0x80058534, frees the member positions it allocates), puts the formation's
  centre at the player's position (player object +0x34 to +0x3C) plus the
  record's, and adds the centre to a list at [0x8009C030] + 0x34 (0x8003B7A8;
  0x8003B7D8 removes it).
- A record is eight words: the address of its steps, the address of its
  members, a position added to the player's (x, y, z), and three 32-bit
  binary angles (2^32 is a full turn; the sine table at 0x80018338 is read
  with the top 13 bits). The rotation matrix (0x80078014) has
  -sin(angle 0) at m[1][2] and cos(angle 0) sin(angle 1) at m[0][2], and the
  heading (0x8007897C) is speed times (cos a0 sin a1, -sin a0, cos a0 cos
  a1): angle 1 is yaw, angle 0 pitch, angle 2 roll (Derived).
- A step is 20 bytes: three turns added to the angles at every task tick,
  a speed (units a tick along the heading), a tick count and flags. The
  timer starts at step 0's ticks and counts down once a tick; when it goes
  below zero the next step starts with its own ticks, so step 0 runs for
  ticks ticks and each later step for ticks + 1. After the last step the
  task clears its update word and ends, and the task sweep (0x8007A360)
  clears its children's update words, so the members still flying go with
  it, as the running game shows.
- A member is an (x, y, z) offset of 16-bit values plus a halfword the code
  does not read. At every tick the formation writes each member's slot,
  centre + floor(R * offset / 4096) (GTE MVMVA, 0x80079BD0), and the 1ST
  ZONE's member update reads its slot and the formation's angles. In all
  four zones' member code (0x8012C3A4, 0x80131DC8, 0x80135498 and
  0x8012A48C) a member killed counts the formation's remaining members
  down; at zero the formation stops moving and ends once its children are
  gone.
- Flags: the EXE reads 0x8000 at each step and 0x4000 at the start only,
  setting fields of the centre's list node; what they do is unknown. Three
  zones' enemy code reads the low bits: the 1ST ZONE's member update
  (0x8012C3DC to 0x8012C540) calls 0x8012BD74, which starts a moving task (a
  shot, inference), with a 1 in 16 chance a tick while bit 1 is set and the
  difficulty word is zero, or bit 0 while it is non-zero; the 6TH ZONE's
  member update also tests bits 0 and 1, and the 2ND ZONE's bit 0, in code
  not read further.
- What the members are is code. Each zone spawns every member of every
  formation with one function of its own (the 1ST ZONE 0x8012C05C, the 2ND
  0x80131A84, the 3RD 0x80134F38, the 6TH 0x8012A134), which its callbacks
  call once per member after 0x80057F0C; the record names no enemy, and only
  one zone file is in memory at a time. Data edits can move a formation,
  reshape it and change its path, and the timeline can choose which
  formation each wave starts.
- On the disc each formation is its steps, its members and its record, in
  that order, with no overlap and no reference from elsewhere in the file
  (`formation_layout.log`). In the 2ND, 3RD and 6TH ZONE two words after
  each record repeat its counts; nothing reads them.

### The campaign

- The script at 0x8001232C has 17 entries of {kind, scene index}, each step
  with its own kind value, 1 to 17 (re-checked). The steps are BRIEFING1, Z1,
  Z2, MOVIE IM 0, Z3, Z4, MOVIE IM 1, Z5, BRIEFING2, Z6, MOVIE IM 2, Z7, Z8,
  MOVIE IM 3, Z9, MOVIE ENDING and MOVIE STAFFROLL.
  - The kind selects a briefing, zone or movie handler.
  - The script has no condition field and no difficulty.
- The loop (0x8002F814) keeps the script pointer in $s0 and the step in $s1,
  and the limit of 17 is an immediate in its code (re-checked). After a step
  whose result word is 0 or 1, it adds 8 to $s0 (0x8002FA94 or 0x8002FAB0)
  and 1 to $s1 (0x8002FB28), then loops while $s1 is below 17 (0x8002FB2C to
  0x8002FB30). The branching prototype hooks that check (section 6).
- A zone step sets the current scene index (0x800A7C30) and difficulty
  (0x800A7C34), then runs the zone loop. After each step, the result word
  0x800A7954 decides what follows: 0 or 1 the next step, 2 game over, 5 back
  to the title (re-checked, 0x8002FA78 to 0x8002FABC).
- Zone results go to records of 0x24 bytes at 0x800A7AA8 + (index - 3) x
  0x24, of which the campaign loop initialises nine at its start
  (re-checked). The results code writes a zone's record only while
  0x800A7950 is 0 (0x800466B4 to 0x80046740, re-checked); the agent reads
  that as campaign mode only. In order, the record's nine words hold: the
  clear time in 1/30 s (333 for a CLEAR TIME of 0:11.10, change 5's remix
  run); a time factor; the enemies spawned and destroyed (the halfwords at
  0x800A794A and 0x800A794C); the destroy ratio; a destroy factor; the
  rating; the grade; and the score at 0x8009C048. The factors and the rating
  are 4.12 fixed point.
  - Campaign-wide fields follow at +0x148: pilot rank, continues left and
    others (agent).
  - AP is the mean of the nine ratings, computed after the campaign or a game
    over (agent).
  - The rating is the destroy factor times the time factor. The grade is 0 for
    a rating of 0xE67 or more (90%), 1 from 0xB34 (70%), 2 from 0x667 (40%),
    3 from 0x334 (20%) and 4 below that (0x80046614 to 0x8004665C). The
    campaign starts every record's grade at 6. Results screens showed RANK S
    at 98 and 100 points, A at 79 and C at 37, so 0 to 4 are S, A, B, C and D
    (Derived).
  - The destroy factor depends on the zone. Cleared quickly with nothing
    destroyed, the 1ST ZONE's record held a destroy factor and rating of 0.5
    (grade B) and the 2ND ZONE's 0 (grade D), both with a time factor of 1.0
    (`.cache/evidence/phase5-3/records/`).
- A zone ends through the clear routine 0x80034104, called with the player
  object (pointer at 0x8009C064), which it moves from state 3, in play, to 6
  (7 in scene indices 9 and 10). Calls to it, counted in every scene `.BIN`
  and the EXE (`.cache/evidence/phase5-3/clear_callers.py` and
  `clear-callers.log`, re-checked):
  - Zones 1 to 4, 6 and 7, U1 to U3, U6 and U7 have no call of their own and
    reach it through the shared wave timeline runner (one constructor call
    each; constructor 0x80071624, update 0x80071544, which holds the EXE's
    only call): an end entry (callback 0) starts a countdown of 90 runner
    ticks, about 3 s at one tick every two frames (see "Scenes and files"),
    and the routine runs when it ends.
  - The 8TH ZONE, U4 and U8 have the runner and also call the routine from
    their own code (one, two and one calls).
  - The 5TH ZONE, the LAST ZONE, U5, U9 and V5 have no runner and call it
    from their own code (one call each).
  - Every call passes the player pointer, and no file has a `j` to the
    routine or a data word holding its address.
- Hazards (Derived from the record layout):
  - There are only nine result records of 0x24 bytes each, indexed by the
    scene index minus 3. A U-zone or V5 played inside the campaign would write
    its record past them, unless a plugin redirects it:
    - U1 (index 12) over the campaign-wide fields at +0x148;
    - U2 to U4 (13 to 15) into the 64-byte game-state block at 0x800A7C30
      (+0x188), which holds the scene index and difficulty (agent; the
      DEMONSTRATION entries in `internals/tables-rerun.txt` have its shape);
    - U5 to V5 (16 to 21) over 0x800A7C7C to 0x800A7D53, whose use is not
      mapped.
    - TRAINING (22) over 0x800A7D54 to 0x800A7D77, and P2 (23, slot 20) over
      0x800A7D78 to 0x800A7D9B: six words the game changes during play, then
      the first three words of a settings block at 0x800A7D90 (the 1ST
      ZONE's code tests its first word; the second is the ZONE PLAY list's
      selection; 0x800A7DB4 is the language index). The spike saw this in
      CAMPAIGN PLAY: the record's rating and grade, 0 and 4 (D), replaced
      the block's first two words, 1 and 3 (section 6, step 5).
    - Any other index takes slot -1, 0x800A7A84 (re-checked in the record
      write).
  - In the spike, rewriting the step skipped every zone, and after the credits
    the game called BRIEFING1's stale entry and stopped. Any branch must keep
    the entry pointer and result slots consistent with the steps it skips or
    adds.

### Unlocks and the save

- The flags (agent; layout re-checked on both card images):
  - A = 0x800A7E20[20] holds the zone flags; A[i] is scene index i + 3 (Z1 to
    Z9, U1 to U9, V5).
  - B = 0x800A7E34[20] holds the boost-level flags.
  - The NORMAL and HARD clear flags are at 0x800A7E48 and 0x800A7E4C.
- The save:
  - The flags are saved at card block +0x200 to +0x30F, with a checksum at
    +0x310: the 32-bit sum of those 68 words. It holds on both images: fresh
    0x02EA3CEB, unlocked 0x09F244F2 (`verify_internals.log`).
  - The fresh save has A[0] and B[0]. The GameFAQs save has A[0..18] and
    B[0..12] and no clear flags.
- Boost levels (Derived): a level is a value from 0 to 13, and ZONE PLAY
  needs B[value] (agent).
  - The DEMONSTRATION entries' level values match the LEVEL label the zone
    list showed for each of the 13 zones the unlocked-save routes select, in
    all three boot modes (`level_labels.sh`, `level-labels/`): value 0 showed
    LEVEL 1 (V5), 3 showed 4 (U4), 4 showed 5 (U5, U7), 6 and 7 showed 7 and
    8 (zones 7 and 8), 8 showed 9 (LAST, U2, U6, U8, U9), 10 showed B (U1)
    and 12 showed D (U3).
  - Thunder2's "Boost Level E" code writes 3 to 0x800A7EC8 and 13 to
    0x800A7EE0 (`gamehacking-codes.txt`). That 0x800A7EE0 holds the boost
    level in play is an inference.
  - So values 0 to 8 are levels 1 to 9 and 9 to 13 are levels A to E, and
    B[9] to B[13] unlock levels A to E. ViperByte's codes on the same site
    name B[0] "Level 2" up to B[12] "Level E", one level off.
- The unlock rules (0x8006398C, tables at 0x80097E98; agent, from the table
  dump):
  - Each campaign zone with a result record unlocks the zone and the boost
    level of the same number: A[0..n-1] and B[0..n-1].
  - More than 0x13C67F frames of play time (about 6 hours) sets A[0] to
    A[19] except A[9] (U1), and B[0] to B[14] except B[10] (level B).
  - The other rules depend on AP, the difficulty cleared and continues:
    - AP 50 or more: U3. AP 60 or more: U2, U5, V5 and level A.
    - NORMAL cleared: U8 and level C; also with AP 90: level D; also with no
      continues: U9; with no continues and AP 90: U4.
    - HARD cleared: U6 and level E; also with AP 90: level B; also with no
      continues: U7; with no continues and AP 90: U1.
- TITLE.BIN has a 14-input code that sets every zone, level and clear flag
  (agent; the sequence is not decoded). The rules cannot produce the
  "Gamesharked" save (agent, Derived: it has U1's and level B's flags, which
  need a HARD clear, but no clear flag).
- Cheat codes (gamehacking.org, saved in `gamehacking-codes.txt`):
  - One set of authors' zone and level codes use the same addresses as above.
  - Another author's codes are consistently 0x2F0 higher (Hypothesis: they
    are for another release of the game).
  - Also useful as a RAM map: "Debug Display" at 0x800A7EA4 (what it shows is
    unknown), boost level, energy, timers.

## 3. Colony Wars (web and the user's discs)

From the Colony Wars agent. The disc claims were spot-checked on Colony Wars
disc 1 (`cw_check.py` / `.log`).

- Developers (Reference, [Game Developer][cw-dev]):
  - Psygnosis' Liverpool team made Colony Wars (1997) and Vengeance (1998).
  - The Leeds studio made Red Sun (2000) from the same code. Red Sun's first
    file is `LEEDS.STX` (agent).
- A mission is a bounded arena in a star system, defined by a text script in
  the `GAME.RSC` archive (agent):
  - Sections: CLASSES, NAMES, OBJECTS, TASKLISTS, TASKS and OBJECTIVES.
  - Objects include boundaries, waypoints, hoops, mine fields and jump gates.
  - Objective conditions include ships destroyed, a time limit, ships docked
    and "player through jump gate".
  - The in-flight code overlay parses the scripts at run time.
  - Spot check on disc 1: 81 scripts.
- Branching: each objective outcome has an `ENDING` line naming the next act
  and mission, or one of five campaign endings, codes 91 to 95. The spot check
  found 186 lines, codes 91 to 95, and one missing target (`1_0`).
  - Corrections from the spot check: three scripts are never targeted (0_1,
    0_7, 1_4), so "0_1 is the entry point" is a hypothesis. CLASSES and
    TASKLISTS appear 78 times for 81 scripts.
  - Vengeance adds a field for multi-part missions and a code 99 (Hypothesis:
    the campaign is lost).
  - Red Sun has no `ENDING` lines. It uses five hubs whose plot missions gate
    progress, script flags, a mission board, money and upgrade slots (agent,
    Derived).
- Flight: per-ship text tables give each axis (speed, roll, pitch, heading,
  afterburner) a maximum rate plus acceleration and deceleration. That is an
  arcade rate model, not Newtonian physics (agent).
- The contrast with Omega Boost: in a [Time Extension interview][te] published
  on 2026-02-23 (`time-extension-article.txt`; the date is in
  `time-extension-date.log`), designer Yuji Yasuhara names "distance,
  mass, terrain, and coordinates" as constraints he "tried to eliminate ... as
  much as possible":
  - "no matter where the player is, enemies appear from the surrounding
    area";
  - there is no terrain, and not even buildings;
  - L1 always returns the mech to an upright posture;
  - the core concept needs movement across a spherical surface with spherical
    linear interpolation;
  - the mech's motion comes from angular velocity and inertia, with no joint
    animation.

  In Omega Boost, "free" means free orientation around the current wave, not
  travel. Yasuhara also says he tried to make a sequel and it "didn't come
  together".

## 4. Prior art and scale

- Omega Boost (`prior-art.log`):
  - A second psxrecomp port exists: [omegakatana92/Omega-Boost-Recomp][okb],
    GPL-3.0, created 2026-09-02 and last pushed 2026-09-03, 1 star. Its README
    says "Complete / Playable" (not verified).
  - Its psxrecomp submodule is commit `001ea947` (2026-09-01, from a fork),
    831 commits behind this repository's pin. It has no committed generated C
    and no mods.
  - Otherwise there are cheat codes, and documentation of the IKI movie format
    ([jPSXdec][jpsxdec], PSX-SPX). The agent found no format documentation,
    decompilation, level editor or remake.
- Colony Wars:
  - A psxrecomp port of Red Sun,
    [alexbeavs-ps1-ports/colony-wars-red-sun-recomp][cwrs]: GPL-3.0, 7 stars,
    with a `mods/` directory (`prior-art.log`).
  - [VengeanceRipper][vr] (2020) extracts Vengeance's archive and converts its
    models.
  - [Colony Wars: Redux][redux] is a Unity demo of three Vengeance levels,
    stalled since 2021.
- Recompilation modding elsewhere (Reference): N64Recomp mods
  (Zelda64Recompiled 1.2, Thunderstore) hook and replace functions, but none
  adds levels. New content comes from decompilation and reimplementation
  projects: OpenGOAL's custom levels, Severed Chains and REDRIVER2.
- Scale (agent, from the GitHub and GitLab APIs): OpenGOAL has 75 commit
  authors since 2020, Ship of Harkinian 190 since 2022, OpenRCT2 761 since
  2014, and OpenMW's AUTHORS file lists 256 programmers since 2008. One-person
  psxrecomp mod sets such as the MegaManX6 adaptation are the scale of steps 1
  to 4 below.

## 5. Rights (public facts, not legal advice)

- Ownership:
  - Sony Interactive Entertainment holds Omega Boost: Sony Computer
    Entertainment published it, and Polyphony Digital is a Sony studio
    ([Wikipedia][ob-wiki]).
  - Colony Wars came from Psygnosis, which Sony bought in 1993; Sony closed
    the studio, by then SCE Studio Liverpool, in 2012
    ([Game Developer][liverpool]), and renewed the Psygnosis trademark through
    2031 ([VGC][psygnosis-tm]).
- Sony has left these online: own-disc reimplementations that ship no assets
  (OpenGOAL, Severed Chains), the [wipEout rewrite][wipeout], and the two
  psxrecomp ports above.
- Sony has acted against Bloodborne fan projects: Bloodborne Kart had to drop
  the Bloodborne name in 2024 ([Nightmare Kart][nk]), and in 2025 a DMCA
  notice hit the 60 fps patch page ([Siliconera][dmca]) and a copyright claim
  hit a video about a fan demake ([PSU][demake]).
- psxrecomp is PolyForm Noncommercial, so a fan project built on it cannot be
  sold.
- A posture that fits what has been tolerated (Derived):
  - ship code and data diffs only, and require the player's disc;
  - keep the "Omega Thrust" name and no Sony logos;
  - never bundle Colony Wars assets. Read them from the player's own disc, if
    used at all; psxrecomp can verify a second disc as a resource. Mixing two
    Sony properties raises exposure.

## 6. Recommended path

Each step is its own reviewed change, verified with routes. Steps 1 to 4 stay
inside this repository and add no game data. Steps 1 and 2 are done (Phase 5
changes 2 and 3), the timeline and formation parts of steps 3 and 4 (changes
4 to 6), a first remix pack (change 7), and step 5's spike (change 8).

1. Mod plumbing, small. Done: the package `omega.cheat.unlock-all` ("Unlock
   All Zones and Boost Levels", off by default) and its plugin
   `omega.unlock-all` (`src/mods/omega_unlock_all.c`) set A[0..18] and
   B[0..13] at every VBlank while the feature is on (`AGENTS.md`, Mods).
   - With it on, ZONE PLAY shows every zone and level OPENED and every
     DEMONSTRATION entry SELECT OK. A save made then holds those flags with a
     correct checksum, and loading it with the feature off, on psx-runtime
     and on psx-beetle, opens the same (scratch routes: psx-runtime in its
     three boot modes, psx-beetle in its two; the evidence is in
     `.cache/evidence/phase5-2/`).
   - With it off, the plugin writes nothing, the game's own save is
     unchanged, and every committed route still passes in all three modes.
   - This proves the build wiring, the package catalog and the plugin
     registration. The launcher's Mods page lists the package under Cheats,
     unticked. Ticking it and pressing PLAY wrote the selection to
     `mods/state.toml`, and the game then ran with A[0..18] and B[0..13] set
     (the launcher driven on a private X display from a copy of the build;
     `.cache/evidence/phase5-3/launcher/`).
2. Branching prototype, medium. Done (Phase 5 change 3).
   - The package `omega.gameplay.branching` ("Branching Campaign
     (prototype)", off by default) runs an instruction plugin at the step
     check (0x8002FB2C). An S on the 1ST ZONE leads to the 3RD ZONE, then
     back to the 2ND ZONE and MOVIE IM 0, and on to the 4TH ZONE; any other
     grade keeps the stock order. Every zone is played once, so all nine
     records are written, and the rules read only the records.
   - The hidden test package `omega.debug.zone-clear` hooks the shared
     timeline runner (0x80071558). It ends a zone through the game's own
     clear path once the player is in play; runs have checked it in the 1ST
     to 4TH ZONE of CAMPAIGN PLAY. With nothing destroyed the zone grades low
     (D in zones 2 to 4, B in the 1ST ZONE), and S when every spawned enemy
     is counted as destroyed. It does not reach the 5TH ZONE, the LAST ZONE,
     U5, U9 or V5, and it is untested in the 8TH ZONE, U4 and U8, which also
     call the clear routine from their own code.
   - Results: scripted runs with the test clear on (a scratch route, in all
     three boot modes; `.cache/evidence/phase5-3/`) played the 1ST, 3RD and
     2ND ZONE, MOVIE IM 0, then the 4TH and 5TH ZONE when the 1ST ZONE graded
     S, and the stock order when it graded B; with the branching feature off
     the order stayed stock. With both features off, every committed route
     still passes in all three modes with the same overlay interpreter counts
     as before, and neither plugin redirects or clears anything.
   - Next for branching: extra zones as branch targets need their result
     records redirected or protected (hazards above), and a campaign run to
     its end under a branch.
3. Zone data tools, medium. Python tools that read the player's disc: decode
   each zone's timeline and formation tables, extract the textures (standard
   TIMs), export models for viewing, and list sound banks.
   - The timeline part is done (Phase 5 change 4).
     `scripts/zones/zone_data.py` writes the wave timeline of each of the
     fourteen zones with the shared runner as TOML and builds the zone file
     back from it: byte-identical when unedited, edits written in place
     (`AGENTS.md`, Zone data). A read-only watch of the game during those
     zones' DEMONSTRATION replays (HLE mode) shows the runner reading the
     tables the tool finds, with their delays.
   - The formation part is done (Phase 5 change 6): dumps of the 1ST, 2ND,
     3RD and 6TH ZONE also give each formation record's position, angles,
     steps and member offsets ("Formations" above), and build writes them in
     place, keeping each record's address and its numbers of steps and
     members.
   - Still to do: textures, models and sound banks.
4. Remix pack, medium to large. Edited timelines and formations for existing
   zones as same-size disc overlays, guarded by the stock hashes; a guarded
   EXE patch adjusts rating thresholds if needed.
   - The timeline part is done (Phase 5 change 5). `zone_data.py package`
     turns an edited dump into a `.psxmod` whose one feature, off by
     default, puts the edited table on the disc as a `disc_user` overlay,
     guarded by the disc image's sha256 and the stock bytes' sha256
     (`AGENTS.md`, Zone data). Scripted runs used a scratch remix of the
     1ST ZONE: its first four waves, 60 ticks apart, then the end entry.
     With the package installed and on, in all three boot modes, the game
     loaded the remixed table, the zone ended with no input after CLEAR
     TIME 0:11.10 (15 enemies spawned, none destroyed, rank B), and the
     campaign went on to the 2ND ZONE; with the feature off, the stock zone
     was still running at the same frames.
   - Edits up to the end of a zone's table keep the static shard's variants
     valid (Derived from the variants' code ranges). A variant runs only
     while the CRC of its own code ranges matches (`overlay_loader.c`), and
     in each of the fourteen zones with a timeline no matching variant
     guards a byte before the table's end, so an edit to the table or to
     the data before it leaves all of them valid (the 1,391 for the 1ST
     ZONE match the remixed file too).
   - The remix runs interpreted as much overlay code as the stock
     boot-to-zone-1 route: 1,309 instructions in seven rows, one per
     address. The five largest rows match that route's by address and
     count, and the other two hold the remaining 15; the probes keep only
     five rows, so earlier samples name those two, 0x80126160 in every run
     and 0x801261AC in one. All seven rows existed while the briefing's file
     was loaded, so the remixed zone added none. In the LLE SCPH-1001 remix
     run the count was already final then, so that zone ran nothing in the
     interpreter. In the other two remix runs the count's last step, 98 and
     371 instructions (7% and 28% of it), falls between a sample with the
     briefing loaded and one with the zone file loaded, so the samples
     cannot tell whether those ran before the load or after it (Derived from
     the probe samples).
   - Formation edits run in the game (Phase 5 change 6). The package's one
     overlay now covers every byte build may write, the table and the
     formation parts with the stock bytes between them. A scratch remix of
     the 1ST ZONE moved wave 1's formation by (20480, -10240, 0) and doubled
     its member offsets, and gave wave 2's first step speed 512 for 15 ticks
     (stock: 256 for 30). Played in CAMPAIGN PLAY with no input in all three
     boot modes, next to the same runs with the feature off, a read-only
     watch of the formation tasks found wave 1's centre exactly (20480,
     -10240, 0) from the stock one at every step state both runs sampled
     (248 to 257), and its members' slots twice as far from it as the stock
     ones, give or take the transform's one-unit floor, in the steps that do
     not turn. Wave 2 moved 512 units a tick, for at most 15 ticks, from the
     same start as the stock formation, then had the stock formation's
     centre and angles at every later step state both runs sampled (197 to
     204). The 868-byte overlay crosses a sector boundary. The formations
     ticked once every two frames (0.497 to 0.499 times a frame), each ended
     after its last step with all its members, and the members' update words
     went with it at the next sweep. The zone's precompiled code kept running:
     in none of the fourteen timeline zones does a matching static variant
     guard a byte build may write, all 1,391 of the 1ST ZONE's match the
     remixed file, and every run interpreted 1,309 overlay instructions in
     seven rows, as the stock route does.
   - A first remix pack (Phase 5 change 7). A remix recipe holds only edits,
     so it is kept in the repository, and `zone_data.py remix` applies it to
     the zones on the player's disc with build's rules and writes one
     `.psxmod` whose feature carries an overlay for each zone (`AGENTS.md`,
     Zone data). The first recipe, `scripts/zones/remixes/crossfire.toml`
     ("Omega Remix: Crossfire"), edits the 1ST, 2ND, 3RD and 6TH ZONE: the
     opening waves come sooner (in the 1ST ZONE 90 ticks apart instead of
     150); seven formations come at the player from behind, three cut
     across just behind it, four that came from behind come from ahead; and
     some fly wider (spread up to 1.5) or faster (pace up to 2). A formation
     starts at the player's position plus its record's position, and the
     player flies on at about 320 units a tick, so yaw 180 alone leaves a
     formation that came from ahead far behind a player it cannot catch: in
     the recipe's first version, 8 of the 14 turned formations never came
     within 26,000 units. The recipe now also moves those nearer and speeds
     some up, with values from a flight model that matches the runs to
     within 2,512 units. Scripted runs started each zone from ZONE PLAY with
     no input, unlock-all on so the list offers every zone, with the pack on
     and off in all three boot modes: all 24 passed with no miss. In every
     run the bytes build may write were in RAM as the file in use (the
     pack's or the stock one) once the zone's runner existed, the runner
     read each new entry's delay from that file, and every formation's start
     angles, member spacing, speed in steps that do not turn, tick counts
     and start position (from the player's position at its start,
     interpolated) matched that file; checked against the other file, every
     run fails. Every formation the recipe moves started on the side the
     recipe says and came within 387 to 5,040 units of the player. No
     matching static variant guards a byte the pack writes, and every run
     interpreted the same 12 overlay instructions, in one row, so the zones
     ran from the precompiled code. Whether the pack plays well is for play
     by hand.
   - Still to do: rating thresholds, other enemies in a formation (code: a
     plugin, or new code in the zone), and checking a remix against
     psx-beetle, which runs no mods and would need a patched disc image.
5. A new zone, large. The spike is done (Phase 5 change 8): it asked
   whether the game finds a file added to the disc, whether a mod can load
   and start a scene index that has no zone, and where that zone's results
   go. It ran in scratch and committed no game data or code (evidence in
   `.cache/evidence/phase5-8/`). The new file was the 1ST ZONE's `.BIN` with
   change 5's short timeline, which ends the zone by itself after four
   waves, so its sha256 told it apart from the stock file. Scripted runs
   played CAMPAIGN PLAY with no input, three cases in all three boot modes,
   and all passed with no miss.
   - The game finds a new file. A package added a record for `P2.BIN;1` to
     the 1ST ZONE's directory sector, right after its five records (the
     directory cache stops at the first empty record), as an equal-length
     patch of free space, and changed the 1ST ZONE's path string in the EXE
     to `\S1\P2.BIN;1`. The file's sectors went either into the disc's
     postgap (case A: 150 zero Form 2 sectors after the last file, from LBA
     247561, which a `disc_raw` overlay rewrote as data sectors) or after
     the disc (case B: a scratch plugin passed a verified resource to
     `psx_mod_append_disc_extent`, and the sectors began at LBA 247711, the
     image's sector count). Both times the game listed the record, loaded
     the new file as the 1ST ZONE, played and cleared it, wrote the 1ST
     ZONE's result record as change 5's remix did (clear time 333, 0:11.10;
     15 spawned, none destroyed; grade B), and went on to the 2ND ZONE.
   - On psx-runtime, a cut scene index starts with data patches alone. Case
     C kept case A's postgap file and directory record and gave index 23
     (P2, a cut zone with no files and no init case) the new file with seven
     more equal-length patches and no plugin: its `.BIN` path names the new
     file and its OMT, OMD and sound bank paths the 1ST ZONE's files; its
     word in the post-load switch's table (0x800123E0) points at the 1ST
     ZONE's case (the init at 0x80122310, right for this file because it is
     the 1ST ZONE's code); and the campaign's first zone step names index
     23 instead of 3. The game loaded the file as index 23, played and
     cleared the zone, and went on to the 2ND ZONE.
   - What index 23 lacks is the rest of a zone's place in the game:
     - A name. Its title card reads only "ZONE", and the pause panel's zone
       line shows only "ZO" at the screen's edge, where the 1ST ZONE shows
       "1ST ZONE": slot 20 has no entry in the name table, and both screens
       load a word at a misaligned address instead (see "Scenes and
       files"). psx-runtime reads it from low RAM without complaint; Beetle,
       and very likely a console, would take an address error exception at
       the title card, and what follows is unknown (a hang is likely). So
       case C's results are psx-runtime results (Derived; case C did not
       run on Beetle, which runs no mods), and a new zone at index 23 must
       be given a name. A data patch cannot do that without changing the
       first word of the unlock rules' tables, which slot 20 takes as its
       name pointer.
     - No results panel appeared after the clear; the cause is not traced.
     - No music starts for it: the music code starts music only for indexes
       3 to 11 (Derived from the code; the runs' sound was not checked).
     - Its result record went to slot 20 and replaced the first three words
       of the settings block at 0x800A7D90, (1, 3, 0), with (0, 4, 0). The
       second word is the ZONE PLAY list's selection, a scene index: TITLE
       moves it down and up (0x8012A428, 0x8012A640), checks that zone's
       unlock flag (0x8012AACC) and, in its mode 3, sets it to the current
       scene index (0x8012D4DC to 0x8012D51C); ZONE PLAY's loop starts the
       zone it names (0x8002FC50). So playing index 23 moved the list's
       selection to the 2ND ZONE (index 4), and the player still chooses
       the zone (Derived, untested).
     - The 1ST ZONE's record kept the values the campaign loop starts it
       with (grade 6, as for a zone not yet played).
   - The EXE patches changed no code the build runs: the runtime's
     text-mismatch counters equal the stock runs' in each boot mode.
   - Limits. The postgap's 150 sectors hold 307,200 bytes: room for any
     zone's `.BIN` (the largest, the 4TH ZONE's, is 114,232 bytes) and for
     all the files of some extra zones, whose directories hold only a
     `.BIN`, OMT and OMD because they use another zone's sound bank: the
     sound-bank table at 0x800984E0 gives U1 the 1ST ZONE's bank, U3 the
     3RD's, U4 the 4TH's and U7 the 7TH's (directory S8; `tables-rerun.txt`
     in `.cache/evidence/mod-research/internals/`). U1's files total
     173,844 bytes, U7's 246,296, U3's 262,724 and U4's 281,164, and U1's
     with a sound bank the size of the 1ST ZONE's, 246,714 (`r2/dir_totals.log`
     in `.cache/evidence/phase5-8/`). A campaign zone does not fit: every S
     directory holds at least 525,806 bytes (the 1ST ZONE's `.BIN`, OMT,
     OMD and sound bank). Appended sectors have room, but need a plugin
     compiled into the build and a file the player selects in the launcher
     (a verified resource; its path is kept in `mods/state.toml`). The
     written data sectors carry zero error detection and correction bytes;
     psx-runtime read them without complaint, while Beetle or a console
     might not (Hypothesis). psx-beetle runs no mods, so none of this was
     checked against it. A longer zone file, a whole new zone with its own
     data, and the other indexes whose files are missing (1, 2, 26, 27 and
     35 to 38, which all get slot -1 and so a record just before the
     table) were not tried.

   So a new zone can be loaded and started, on psx-runtime. Making it a full
   zone, and one that can run on Beetle and a console, needs a plugin that
   gives it a name (without one, its name lookup is the misaligned load
   above), keeps its result record from overwriting other data (by
   redirecting or protecting the record write at 0x800466B4), and gives it
   a results screen and music. The alternative is to reuse an existing
   zone's slot and path, as case A did, which keeps all of those. Either
   way, the zone itself is then built by cloning an existing zone's code
   with new tables, which needs a MIPS toolchain and a map of the EXE
   functions that zones call.
6. Colony Wars-style layer, large; research spike first.
   - Mission files modelled on Colony Wars' scripts (arena, waves, objectives,
     outcomes leading to the next mission).
   - Objectives judged from RAM state.
   - A mission graph in place of the 17-step script, and a hub screen.
7. Decide the remake route. There are two:
   - Stay in the recomp and replace systems one function at a time with
     readable native C through function filters, using the routes and Beetle
     as the regression oracle. It ships code only, but the PS1's limits remain.
   - Build in a new engine, either decoding assets from the player's disc or
     making new art. This allows open flight and modern rendering, and is far
     larger.

## 7. Unknowns

- From step 5's spike: why index 23's zone shows no results panel after its
  clear; what Beetle and a console do after its misaligned name load (an
  address error exception, Derived; what the exception handler then does
  was not traced); what the first word of the settings block at 0x800A7D90
  does (the 1ST ZONE's code tests it); whether a zone file longer than the
  stock one still fits, since its OMT and OMD load right after it; and
  whether Beetle or a console reads data sectors whose error correction
  bytes are zero.
- The TITLE 14-input unlock code; what "Debug Display" shows.
- What A[19] and B[14] unlock: the play-time rule sets them, but no zone or
  level label shows them.
- How results, AP and the unlock rules behave with more or fewer than nine
  campaign zones.
- How the 5TH ZONE, the LAST ZONE, U5, U9 and V5 decide when to call the
  clear routine, and when the 8TH ZONE, U4 and U8 call it from their own
  code as well as through the runner.
- The OMD record format in detail; what the formation flags 0x4000 and
  0x8000 do (the EXE sets fields of the centre's node in the list at
  [0x8009C030] + 0x34), and what the low flag bits do outside the 1ST ZONE;
  and how the waves of the ten timeline zones that never call 0x80057F0C
  place their enemies.
- What the 8TH ZONE's runner does if its last wave is ever cleared before
  the zone ends: with no end entry, it would take the debug string after the
  table as an entry and call it (Derived; never seen).
- Whether edits to a zone's data after its table keep the static shard's
  variants in use; no matching variant guards a byte before the table's end
  (step 4).
- Whether the spike's crash after the credits also happens in genuine play. A
  full play-through answers it.

[mmx6]: https://github.com/mstan/MegaManX6Recomp
[mmx4]: https://github.com/mstan/MegaManX4Recomp
[tomba2]: https://github.com/mstan/Tomba2Recomp
[cw-dev]: https://www.gamedeveloper.com/audio/how-i-colony-wars-i-came-to-be
[te]: https://www.timeextension.com/features/the-making-of-omega-boost-layzners-movement-was-burned-into-my-imagination-how-yuji-yasuhara-created-a-ps1-mecha-classic
[okb]: https://github.com/omegakatana92/Omega-Boost-Recomp
[jpsxdec]: https://github.com/m35/jpsxdec
[cwrs]: https://github.com/alexbeavs-ps1-ports/colony-wars-red-sun-recomp
[vr]: https://github.com/suXinjke/VengeanceRipper
[redux]: https://colony-wars-redux.itch.io/colony-wars-redux
[ob-wiki]: https://en.wikipedia.org/wiki/Omega_Boost
[liverpool]: https://www.gamedeveloper.com/business/sony-closes-i-wipeout-i-s-studio-liverpool
[psygnosis-tm]: https://www.videogameschronicle.com/news/sony-has-renewed-the-psygnosis-trademark-and-logo/
[wipeout]: https://phoboslab.org/log/2023/08/rewriting-wipeout
[nk]: https://en.wikipedia.org/wiki/Nightmare_Kart
[dmca]: https://www.siliconera.com/bloodborne-60fps-patch-pulled-over-sony-dmca-takedown/
[demake]: https://www.psu.com/news/bloodborne-psx-demake-copyright-sony-working-on-remake-says-modder/

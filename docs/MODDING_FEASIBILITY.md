# Modding feasibility

Research done on 2026-10-20 into modding Omega Boost through this
recompilation: unlocks, a branching campaign, remixed and new zones, missions
in the style of the Colony Wars series, and a possible fan sequel or remake.
Step 1 of the recommended path (section 6) is now implemented; nothing else
here is. The evidence (scripts, logs and saved web pages) is in
`.cache/evidence/mod-research/`, which is ignored and exists only on the
machine that did the research; evidence file names below are relative to it.

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
  from the finished zone's results, which are in RAM when the loop resumes.
  The script has no condition field, a branch must keep the scene entry
  pointer and the result slots consistent, and testing needs campaign play.
- Remixed zones: edit a zone's wave timeline and formation tables, which are
  data inside its `.BIN`, and ship them as same-size disc overlays. The
  formats are not decoded yet, and files cannot grow.
- New zones: a new `.BIN` linked at 0x80120000 against the EXE's fixed
  addresses, plus models, textures and sound; a plugin adds its load case and
  result slot. The spare scene slots have no load case that retail code
  reaches, the tables have fixed sizes, and it needs a MIPS toolchain and a
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
  - P2 looks like a cut zone (Derived): it has S2's sound bank and its own
    rating thresholds (slot 20).
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
  (DsSearchFile at 0x80080794, agent). It reads the path table and the first
  sector of the target directory: at most 128 directories, and 64 files in
  each. The root directory has 108 bytes free and each scene directory about
  1,660.
- After loading, a switch (0x8002AD70) calls a fixed init address for each
  scene index (agent; the list is in `internals/tables-rerun.txt`).
  - The init relocates the scene's models and stores its entry function at
    0x800A7940; the play loops call the overlay through that pointer.
  - Indices 1, 2, 23, 27 and 35 to 37 have no case, so supplying their files
    alone would not make them run (agent, Derived). SOUND_TEST (26) and the
    gallery (38) have init addresses, but only the unreachable states 13 and
    12 load them (agent).
- A zone `.BIN` holds an id word, debug strings, then data tables (formations,
  paths, the wave timeline), then code (agent):
  - S1: 8.5 KB of data, then about 45 KB of code in about 55 functions.
  - U1: 2.2 KB of data, then 5.6 KB of code.
  - Overlays call EXE functions at fixed addresses with no import table: S1
    calls 56 of them, TITLE 77.
- The wave timeline is a table of {callback, delay} entries that EXE code runs
  (agent):
  - A delay of -100 waits until the wave is destroyed, and a null callback ends
    the zone.
  - S1 has five timed waves and four wait-for-clear entries; U1 has one
    encounter.

  So timing and placement are data in the `.BIN`, behaviour is `.BIN` code
  calling the EXE, and the model and texture files hold only models and
  textures (agent, Derived).

### The campaign

- The script at 0x8001232C has 17 entries of {kind, scene index}, each step
  with its own kind value, 1 to 17 (re-checked). The steps are BRIEFING1, Z1,
  Z2, MOVIE IM 0, Z3, Z4, MOVIE IM 1, Z5, BRIEFING2, Z6, MOVIE IM 2, Z7, Z8,
  MOVIE IM 3, Z9, MOVIE ENDING and MOVIE STAFFROLL.
  - The kind selects a briefing, zone or movie handler.
  - The script has no condition field and no difficulty.
- The loop (0x8002F814) keeps the script pointer and step only in registers;
  the limit of 17 is an immediate in its code (agent; consistent with the
  earlier spike that rewrote them).
- A zone step sets the current scene index (0x800A7C30) and difficulty
  (0x800A7C34), then runs the zone loop. After each step, the result word
  0x800A7954 decides what follows: 0 or 1 the next step, 2 game over, 5 back
  to the title (agent).
- Zone results are kept only in campaign mode, at 0x800A7AA8 + (index - 3) x
  0x24 (agent). Each record holds the clear time, time score, enemies,
  enemies destroyed, destroy ratio and score, combined rating, grade and
  score.
  - Campaign-wide fields follow at +0x148: pilot rank, continues left and
    others.
  - AP is the mean of the nine ratings, computed after the campaign or a game
    over.
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
inside this repository and add no game data. Step 1 is done (Phase 5 change
2).

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
     registration. The launcher's Mods page lists bundled packages
     (`MOD_PACKAGES.md`); seeing this one there is left to a play session.
2. Branching prototype, medium.
   - An instruction hook at the campaign loop's step advance chooses the next
     step by a rule on the finished zone's result record, for example its
     grade.
   - A debug-only option that ends the current zone as cleared lets routes
     test each branch without live play.
3. Zone data tools, medium. Python tools that read the player's disc: decode
   each zone's timeline and formation tables, extract the textures (standard
   TIMs), export models for viewing, and list sound banks.
4. Remix pack, medium to large. Edited timelines and formations for existing
   zones as same-size disc overlays, guarded by the stock hashes; a guarded
   EXE patch adjusts rating thresholds if needed.
   - Hypothesis: data-only edits keep the static shard valid, because its
     guard covers code bytes. Test it.
5. A new zone in a spare slot, large. Spike these three unknowns first:
   - whether the game's DsSearchFile finds a file whose directory record (in
     a directory sector's free space, an equal-length patch) points into
     appended sectors;
   - a plugin load case and init for the new index;
   - result and rating slots for it.

   Then build the zone by cloning an existing zone's code with new tables.
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

- Whether new files can be added through a patched directory sector plus
  appended sectors (step 5).
- The TITLE 14-input unlock code; what "Debug Display" shows.
- What A[19] and B[14] unlock: the play-time rule sets them, but no zone or
  level label shows them.
- How results, AP and the unlock rules behave with more or fewer than nine
  campaign zones.
- The OMD record format in detail; the formation table format.
- Whether data-only edits keep the static shard's compiled variants in use.
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

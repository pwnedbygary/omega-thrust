#!/usr/bin/env python3
"""Turn a zone's wave timeline into editable text and back, byte for byte.

A zone file, <DIR>/<DIR>.BIN on the player's disc, loads whole at 0x80120000.
A zone that uses the game's shared wave timeline passes the table's address
to the runner's constructor (0x80071624) in $a1. The constructor starts entry
0 at once; the runner (0x80071544) then moves through the table, one entry at
a time. An entry is two words: a callback in the zone's code, which starts a
wave, and a delay. The next entry starts when the delay has run out, counted
in runner ticks (about one every two frames), or as soon as the runner has no
child task left (the tasks the wave callbacks create are its children). A
delay of -100, written "clear" here, waits only for that. A callback of 0 is
the end entry: 90 ticks later the runner calls the zone clear routine
(0x80034104).

Some callbacks start a formation: they pass 0x80057F0C a record of eight
words and two counts, its steps and its members, as instruction immediates.
The record holds its steps' address, its members' address, a position added
to the player's (x, y, z) and three binary angles (pitch, yaw, roll; 2**32 is
a full turn). A step is 20 bytes: three turns added to the angles at every
task tick, a speed along the heading, a tick count and flags. A member is a
16-bit (x, y, z) offset from the formation's centre, turned with it.

  zone_data.py list                     the disc's zone files and their tables
  zone_data.py dump <zone> [--out F]    write a zone's table and formations as TOML
  zone_data.py build <file> [--out F]   write the zone file with the edits
  zone_data.py check                    dump and rebuild every zone; the bytes
                                        must come out identical
  zone_data.py package <file> [--id I] [--name N] [--version V] [--out F]
                                        write a mod package that makes the game
                                        load the edits
  zone_data.py remix <recipe> [--out F]
                                        write one package that makes the game
                                        load a remix recipe's edits of zones

A dump names the size and sha256 of the zone file it was read from, and build
reads that file from the disc again and refuses any other. Build writes the
edits in place: the edited waves and the end entry must fit in the stock
table's slots, and slots left over become zero words. A wave may use only the
callbacks of the stock table, and the first entry must be a wave, because the
constructor calls entry 0's callback without checking it. A formation keeps
its address, its number of steps and its number of members. Dumps and zone
files hold data from the disc, so they go under .cache/ (default
.cache/zones/) or outside the repository, never elsewhere in it.

A package is a .psxmod: a zip with manifest.toml at its root, which the
launcher's Mods page installs. Its one feature, off by default, puts the
edited bytes on the disc in place of the stock ones (a disc_user overlay at
the zone file's sector times 2048 plus the offset of the first byte build may
change, to the last, covering the table and every formation part), so the
game reads them when it loads the zone. The manifest names the sha256 of the
data file that the cue sheet given with --disc names, which is what the
runtime hashes when it mounts that cue, so the package applies only to that
disc image; and the sha256 of the stock bytes it replaces, which the runtime
checks before launch. The overlay holds data from the disc, so the same rule
about where to write applies.

A remix recipe holds only edits, never data from the disc, so it may be kept
in the repository (scripts/zones/remixes/). It names the package (id, version,
name, description) and, for each zone it edits, a new timeline, new formation
values or both. The timeline names the stock table's waves by number, 0 first
as in a dump, each with a delay: ticks, "clear", or "stock" for the wave's
own. A formation, named by its record's address, may take spread, a factor
above 0 for its members' offsets; pace, a factor above 0 for its steps'
speeds and turns that also divides each step's duration, so it flies the same
path faster (a pace that would leave a first step no ticks is refused); yaw,
degrees that turn its position and heading about the vertical axis through
the player's position when it starts (the yaw angle is the outermost of the
three, so the whole flight turns, but the player keeps flying on: one turned
to start behind reaches the player only if it is faster); and move, added to
its position after yaw. Values are rounded to the nearest integer, ties to
even. remix reads each zone from the disc, applies the edits with build's
rules and writes one package (default .cache/zones/<id>-<version>.psxmod)
whose feature carries an overlay for each zone.
"""
import argparse
import collections
import hashlib
import io
import json
import math
import re
import struct
import sys
import textwrap
import tomllib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DISC = REPO / "disc" / "Omega Boost (USA).cue"
OUT_DIR = REPO / ".cache" / "zones"
BASE = 0x80120000         # every zone file loads whole at this address
RUNNER_NEW = 0x80071624   # the timeline runner's constructor; $a1 = the table
CLEAR_ROUTINE = 0x80034104
FORMATION = 0x80057F0C    # the call wave callbacks use to start a formation
DIFFICULTY = 0x800A7C34   # the zone handler's copy of the difficulty (0 on NORMAL)
WAIT = -100               # a delay that waits only for the runner's children
FORMAT = 2                # dumps of format 1 have no formations
REMIX = 1                 # the format of remix recipes
EDITS = {"spread", "pace", "yaw", "move"}  # what a recipe may do to a formation
GAME_ID = "SCUS-94449"    # game.toml [game] id, which packages target
SECTOR, HEADER, USER = 2352, 24, 2048  # MODE2/2352 form 1 sectors
LABELS = {"S1": "1ST ZONE", "S2": "2ND ZONE", "S3": "3RD ZONE", "S4": "4TH ZONE",
          "S5": "5TH ZONE", "S6": "6TH ZONE", "S8": "7TH ZONE", "S9": "8TH ZONE",
          "S10": "LAST ZONE"}

# The game's records, little-endian.
ENTRY = struct.Struct("<Ii")          # a timeline entry: callback, delay
POINTERS = struct.Struct("<2I")       # a formation record: its steps' and members' addresses
PLACEMENT = struct.Struct("<3i3I")    # then position (x, y, z) and angles (pitch, yaw, roll)
STEP_FIELDS = struct.Struct("<4iHH")  # a step: turn (pitch, yaw, roll), speed, ticks, flags
OFFSET = struct.Struct("<3h")         # a member: x, y, z, then a halfword of padding
STEP, MEMBER = STEP_FIELDS.size, 8    # bytes in a formation step and member
RECORD = POINTERS.size + PLACEMENT.size  # bytes in a formation record
MAX_COUNT = 0x7FFF        # steps and members come as positive 16-bit immediates
FULL_TURN = 2**32         # a full turn in binary angle units

# The values a field can hold, both ends included.
S16, U16 = (-0x8000, 0x7FFF), (0, 0xFFFF)
S32, U32 = (-2**31, 2**31 - 1), (0, 2**32 - 1)
TICK_COUNT = (0, 2**31 - 1)  # a delay in ticks: a signed word, not negative

# MIPS I (R3000A) encodings that the code analysis reads.
SPECIAL, REGIMM, J, JAL, BEQ, BNE, BLEZ, BGTZ = range(8)  # opcodes 0 to 7
BRANCHES = (REGIMM, BEQ, BNE, BLEZ, BGTZ)  # the conditional branches
ADDIU, ORI, LUI, LW = 0x09, 0x0D, 0x0F, 0x23
IMMEDIATE_OPS, LOADS = range(0x08, 0x10), range(0x20, 0x27)  # these write rt
COP0, COP2 = 0x10, 0x12
COP_MOVES = (0, 2)        # rs of mfc and cfc, coprocessor ops that write rt
JR, JALR = 0x08, 0x09     # SPECIAL functions that jump through a register
ADDU, OR = 0x21, 0x25     # SPECIAL functions that move when one source is $zero
MULT_DIV = range(0x18, 0x1C)  # SPECIAL functions mult to divu, which write no rd
LINK = 0x10               # REGIMM's rt bit for bltzal and bgezal, which link
ZERO, A1, A2, A3, RA = 0, 5, 6, 7, 31  # registers
JR_RA = 0x03E00008        # jr $ra
SCAN_LIMIT = 256          # the most words of a callback its notes read

# ISO 9660: the primary volume descriptor, and the fields of a directory record.
PVD_SECTOR, PVD_MAGIC, PVD_ROOT = 16, b"\x01CD001", slice(156, 190)  # the root directory's record
DIR_FLAGS, DIR_NAME_LENGTH, DIR_NAME = 25, 32, 33  # byte 0 is the record's length
DIR_EXTENT, DIR_SIZE = slice(2, 6), slice(10, 14)  # the little-endian copies
IS_DIRECTORY = 2          # the flag of a directory
SELF_AND_PARENT = (b"\x00", b"\x01")  # the names of the "." and ".." records


class ZoneError(Exception):
    pass


class NoTimeline(ZoneError):
    pass


Formation = collections.namedtuple(
    "Formation", "address steps_at steps members_at members calls")


class Timeline(collections.namedtuple("Timeline", "call_at address waves end")):
    """A zone's wave table: the address of the call that passes it to the
    runner, its address, its waves as (callback, delay) pairs, and its end
    entry's delay, or None if it has no end entry."""
    __slots__ = ()

    @property
    def slots(self):
        """The table's 8-byte entries in place, the end entry included."""
        return len(self.waves) + (self.end is not None)


# A byte range that build may write: its first address, the address after its
# last byte, and what it holds.
Part = collections.namedtuple("Part", "start stop label")


class Layout(collections.namedtuple("Layout", "timeline formations parts")):
    """A zone's Timeline, its Formations, and the Parts build may write,
    sorted by address and never overlapping."""
    __slots__ = ()

    @property
    def span(self):
        """The file offsets of the first byte build may write and of the byte
        after the last: the parts never overlap, so the first part starts the
        span and the last ends it."""
        return self.parts[0].start - BASE, self.parts[-1].stop - BASE


# A zone that a package edits: its zone file's path on the disc and first
# sector, and the file's stock and built bytes.
ZoneEdit = collections.namedtuple("ZoneEdit", "path lba stock built")


class Disc:
    """A one-track MODE2/2352 cue/bin image, read through its ISO 9660 tree."""

    def __init__(self, cue):
        cue = Path(cue)
        try:
            text = cue.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            raise ZoneError(f"cannot read {cue}: {exc}")
        names = re.findall(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', text, re.M)
        if len(names) != 1 or not re.search(r"^\s*TRACK\s+01\s+MODE2/2352\s*$",
                                            text, re.M):
            raise ZoneError(f"{cue}: expected one FILE with TRACK 01 MODE2/2352")
        self.bin = cue.parent / names[0]

    def sectors(self, lba, count):
        data = bytearray()
        try:
            with self.bin.open("rb") as f:
                for n in range(lba, lba + count):
                    f.seek(n * SECTOR + HEADER)
                    chunk = f.read(USER)
                    if len(chunk) != USER:
                        raise ZoneError(f"{self.bin}: no sector {n}")
                    data += chunk
        except OSError as exc:
            raise ZoneError(f"cannot read {self.bin}: {exc}")
        return bytes(data)

    def directory(self, lba, size):
        """(name, lba, size, is_dir) for each record but '.' and '..'."""
        data = self.sectors(lba, -(-size // USER))
        for start in range(0, len(data), USER):
            pos = start
            while pos < start + USER and (length := data[pos]):  # a record starts with its length
                rec = data[pos:pos + length]
                name = rec[DIR_NAME:DIR_NAME + rec[DIR_NAME_LENGTH]]
                if name not in SELF_AND_PARENT:
                    yield (name.decode("ascii"), little_endian(rec[DIR_EXTENT]),
                           little_endian(rec[DIR_SIZE]), bool(rec[DIR_FLAGS] & IS_DIRECTORY))
                pos += length

    def zone_files(self):
        """{"S1/S1.BIN": (lba, size), ...}: each directory's file named after it."""
        pvd = self.sectors(PVD_SECTOR, 1)
        if not pvd.startswith(PVD_MAGIC):
            raise ZoneError(f"{self.bin}: no ISO 9660 volume")
        root = pvd[PVD_ROOT]
        found = {}
        for name, lba, size, is_dir in self.directory(little_endian(root[DIR_EXTENT]),
                                                      little_endian(root[DIR_SIZE])):
            if is_dir:
                for fname, flba, fsize, fdir in self.directory(lba, size):
                    if not fdir and fname.split(";")[0] == f"{name}.BIN":
                        found[f"{name}/{name}.BIN"] = (flba, fsize)
        return found

    def read(self, lba, size):
        return self.sectors(lba, -(-size // USER))[:size]

    def image_sha256(self):
        """The sha256 of the data file, which the runtime matches against a
        package's disc_sha256 when it mounts the cue (mod_runtime.cpp sha256_file)."""
        digest = hashlib.sha256()
        try:
            with self.bin.open("rb") as f:
                while chunk := f.read(1 << 20):
                    digest.update(chunk)
        except OSError as exc:
            raise ZoneError(f"cannot read {self.bin}: {exc}")
        return digest.hexdigest()


def words(blob):
    return struct.unpack_from(f"<{len(blob) // 4}I", blob)


def little_endian(field):
    return int.from_bytes(field, "little")


def jal(target):
    return (JAL << 26) | (target & 0x0FFFFFFF) >> 2


def sx16(value):
    return value - 0x10000 if value & 0x8000 else value


def sx32(value):
    return value - 2**32 if value & 0x80000000 else value


def opcode(word):
    return word >> 26


def rs(word):
    return (word >> 21) & 31


def rt(word):
    return (word >> 16) & 31


def rd(word):
    return (word >> 11) & 31


def funct(word):
    return word & 0x3F


def immediate(word):
    return word & 0xFFFF


def address_of(index):
    """The address of a zone file's word index, as loaded."""
    return BASE + 4 * index


def index_of(address):
    """The word index of an address in a zone file, as loaded."""
    return (address - BASE) // 4


def jump_target(word, address):
    """Where the j or jal at address goes, within the region of the word after it."""
    return ((address + 4) & 0xF0000000) | (word & 0x03FFFFFF) << 2


def branch_target(word, index):
    """Where the branch at word index goes when taken, as a word index."""
    return index + 1 + sx16(immediate(word))


def is_call(word):
    """True for jal, jalr, bltzal and bgezal, which come back after their delay slot."""
    op = opcode(word)
    if op == SPECIAL:
        return funct(word) == JALR
    return op == JAL or (op == REGIMM and (rt(word) & LINK) != 0)


def is_move(word):
    """True for `move rd, rs`: an `addu` or an `or` with $zero as one source."""
    return opcode(word) == SPECIAL and funct(word) in (ADDU, OR) and ZERO in (rs(word), rt(word))


def control(word):
    """True for jumps and branches, whose delay slots end straight-line code."""
    op = opcode(word)
    return REGIMM <= op <= BGTZ or (op == SPECIAL and funct(word) in (JR, JALR))


def destination(word):
    """The register an instruction writes, if any (common MIPS I forms)."""
    op = opcode(word)
    if op == SPECIAL:
        return None if funct(word) == JR or funct(word) in MULT_DIV else rd(word)
    if op in IMMEDIATE_OPS or op in LOADS:
        return rt(word)
    if op in (COP0, COP2) and rs(word) in COP_MOVES:  # mfc0, mfc2, cfc2
        return rt(word)
    return RA if op == JAL else None


def trace(seq, index, reg, steps=32):
    """Value of reg after seq[index], from straight-line lui/addiu/ori/move code."""
    while reg != ZERO and index >= 0 and steps > 0:
        word = seq[index]
        op = opcode(word)
        if op == LUI and rt(word) == reg:
            return immediate(word) << 16
        if op in (ADDIU, ORI) and rt(word) == reg:
            base = trace(seq, index - 1, rs(word), steps - 1)
            if base is None:
                return None
            if op == ADDIU:
                return (base + sx16(immediate(word))) & 0xFFFFFFFF
            return base | immediate(word)
        if is_move(word) and rd(word) == reg:
            reg = rs(word) or rt(word)
        elif destination(word) == reg or control(word):
            return None
        index -= 1
        steps -= 1
    return 0 if reg == ZERO else None


def argument(code, call, reg):
    """Register reg as the function called by the jal at code[call] receives it."""
    seq = code[:call] + code[call + 1:call + 2]  # the delay slot runs before the call
    return trace(seq, len(seq) - 1, reg)


def read_table(blob):
    """The zone's Timeline: the address of the call that passes the table, the
    table's address, its [(callback, delay)] waves, and its end delay or None."""
    code = words(blob)
    calls = [i for i, word in enumerate(code) if word == jal(RUNNER_NEW)]
    if not calls:
        raise NoTimeline(f"no shared wave timeline: nothing calls 0x{RUNNER_NEW:08X}")
    if len(calls) > 1:
        raise ZoneError(f"{len(calls)} calls to 0x{RUNNER_NEW:08X}; expected one")
    address = argument(code, calls[0], A1)
    if (address is None or address % 4
            or not BASE <= address <= BASE + len(blob) - ENTRY.size):
        raise ZoneError("cannot trace the table address passed at "
                        f"0x{address_of(calls[0]):08X}")
    waves, end, offset = [], None, address - BASE
    while offset + ENTRY.size <= len(blob):
        callback, delay = ENTRY.unpack_from(blob, offset)
        if callback == 0:
            end = delay
            break
        if callback % 4 or not BASE <= callback < BASE + len(blob):
            break  # no end entry: the table runs into other data
        waves.append((callback, delay))
        offset += ENTRY.size
    if not waves:
        raise ZoneError(f"the table at 0x{address:08X} does not start with a wave")
    return Timeline(address_of(calls[0]), address, waves, end)


def read_formations(blob):
    """A Formation for every record the zone passes to 0x80057F0C, by address."""
    code = words(blob)
    found = {}
    for index, word in enumerate(code):
        if word != jal(FORMATION):
            continue
        at = address_of(index)
        record, steps, members = (argument(code, index, reg) for reg in (A1, A2, A3))
        if record is None or steps is None or members is None:
            raise ZoneError(f"cannot trace the formation record and counts passed at 0x{at:08X}")
        if not (0 < steps <= MAX_COUNT and 0 < members <= MAX_COUNT):
            raise ZoneError(f"the call at 0x{at:08X} starts a formation with {sx32(steps)} steps"
                            f" and {sx32(members)} members")
        if record % 4 or not BASE <= record <= BASE + len(blob) - RECORD:
            raise ZoneError(f"the formation record 0x{record:08X} passed at 0x{at:08X} is not"
                            " in the file")
        counts = found.setdefault(record, [steps, members, []])
        if counts[:2] != [steps, members]:
            raise ZoneError(f"the formation record 0x{record:08X} is passed with {counts[0]}"
                            f" steps and {counts[1]} members, and at 0x{at:08X} with {steps}"
                            f" and {members}")
        counts[2].append(at)
    formations = []
    for record in sorted(found):
        steps, members, calls = found[record]
        steps_at, members_at = POINTERS.unpack_from(blob, record - BASE)
        for part, start, size in (("steps", steps_at, STEP * steps),
                                  ("members", members_at, MEMBER * members)):
            if start % 4 or not BASE <= start <= BASE + len(blob) - size:
                raise ZoneError(f"the {part} of the formation record 0x{record:08X}, at"
                                f" 0x{start:08X}, are not in the file")
        formations.append(Formation(record, steps_at, steps, members_at, members, calls))
    return formations


def layout(blob):
    """The zone's Layout: read_table's Timeline, read_formations' records, and
    the Parts build may write: the table's slots and each formation's record,
    steps and members. They must not overlap, since build writes each in
    place."""
    timeline = read_table(blob)
    formations = read_formations(blob)
    parts = [Part(timeline.address, timeline.address + ENTRY.size * timeline.slots,
                  "the table")]
    for formation in formations:
        name = f"0x{formation.address:08X}"
        parts += [Part(formation.address, formation.address + RECORD,
                       f"formation record {name}"),
                  Part(formation.steps_at, formation.steps_at + STEP * formation.steps,
                       f"the steps of {name}"),
                  Part(formation.members_at, formation.members_at + MEMBER * formation.members,
                       f"the members of {name}")]
    parts.sort()
    for before, after in zip(parts, parts[1:]):  # sorted by start: neighbours suffice
        if after.start < before.stop:
            raise ZoneError(f"{before.label} and {after.label} overlap")
    return Layout(timeline, formations, parts)


def callback_span(code, callback):
    """Word indices of a callback's code up to its first `jr $ra` and delay slot,
    whose calls the timeline's notes list."""
    start = index_of(callback)
    for i in range(start + 1, min(len(code), start + SCAN_LIMIT)):
        if code[i - 1] == JR_RA:
            return range(start, i + 1)
    return range(start, min(len(code), start + SCAN_LIMIT))


def flow(code, entry):
    """{word index: where control goes next} for the code reached from word
    entry. A jump or branch runs its delay slot, then goes to its target and,
    if conditional, to the word after the slot; a call (jal, jalr, bltzal,
    bgezal) returns to the word after its slot; jr, and indices outside the
    file, end a path."""
    graph, todo = {}, [entry]
    while todo:
        i = todo.pop()
        while 0 <= i < len(code) and i not in graph:
            word = code[i]
            op = opcode(word)
            if op == SPECIAL and funct(word) == JR:
                graph[i] = []
            elif op == J:
                graph[i] = [index_of(jump_target(word, address_of(i)))]
            elif is_call(word):
                graph[i] = [i + 2]
            elif op in BRANCHES:
                graph[i] = [branch_target(word, i), i + 2]
            else:
                graph[i] = [i + 1]
                i += 1
                continue
            todo += graph[i]
            break
    return graph


def loaded(code, start, index, reg):
    """The address of the word reg holds at word index, if an lw from word start
    on wrote reg last and the code from start to it gives the address."""
    for i in range(index - 1, start - 1, -1):
        if destination(code[i]) == reg:
            if opcode(code[i]) != LW:
                return None
            base = trace(code[start:i], i - 1 - start, rs(code[i]))
            return None if base is None else (base + sx16(immediate(code[i]))) & 0xFFFFFFFF
    return None


def gate(code, entry, call):
    """When the callback whose code starts at word entry runs the instruction at
    word call: None if on every path, "only while the difficulty word ... is
    zero" (or "non-zero") if that word decides it, else "only on some paths".
    The paths are flow()'s. A conditional branch goes both ways, except a beqz
    or bnez on a register that its basic block loaded from the difficulty
    word: that goes the way the word sends it, once with the word zero and
    once non-zero."""
    graph = flow(code, entry)
    starts = {entry} | {n for i, nxt in graph.items() if control(code[i]) for n in nxt}
    zero = {}  # the branches on the difficulty word: whether taken while it is zero
    for i in graph:
        word = code[i]
        if opcode(word) in (BEQ, BNE) and rt(word) == ZERO and rs(word) != ZERO:
            start = max((s for s in starts if s <= i), default=i)
            if loaded(code, start, i, rs(word)) == DIFFICULTY:
                zero[i] = opcode(word) == BEQ
    found = []
    for value in (0, 1):
        ran = left = False
        todo, seen = [entry], set()
        while todo:
            i = todo.pop()
            if i in seen:
                continue
            seen.add(i)
            if i == call:  # this path runs it; only paths that avoid it go on
                ran = True
                continue
            nxt = graph.get(i, [])
            if i in zero:
                nxt = nxt[:1] if zero[i] == (value == 0) else nxt[1:]
            left = left or not nxt
            todo += nxt
        found.append((ran, left))
    (ran0, left0), (ran1, left1) = found
    if not (left0 or left1):
        return None
    if ran0 and not left0 and not ran1:
        return f"only while the difficulty word (0x{DIFFICULTY:08X}) is zero"
    if ran1 and not left1 and not ran0:
        return f"only while the difficulty word (0x{DIFFICULTY:08X}) is non-zero"
    return "only on some paths through its callback"


def describe(blob, callback):
    """The calls a callback makes before its first `jr $ra`."""
    code = words(blob)
    notes = []
    for i in callback_span(code, callback):
        if opcode(code[i]) == JAL:
            target = jump_target(code[i], address_of(i))
            note = f"0x{target:08X}"
            if target == FORMATION:
                args = (argument(code, i, reg) for reg in (A1, A2, A3))
                note += "(" + ", ".join("?" if a is None else f"0x{a:08X}" if a > 0xFFFF
                                        else str(a) for a in args) + ")"
            if note not in notes:
                notes.append(note)
    return "calls " + ", ".join(notes) if notes else "calls nothing"


def delay_text(delay):
    return '"clear"' if delay == WAIT else str(delay)


def comment(text):
    return textwrap.wrap(text, 76, initial_indent="# ", subsequent_indent="# ")


def listing(numbers):
    text = [str(n) for n in numbers]
    return text[0] if len(text) == 1 else ", ".join(text[:-1]) + " and " + text[-1]


def degrees(value):
    return f"{value * 360 / FULL_TURN:g}"


FORMATION_NOTES = comment(
    f"Formations. 0x{FORMATION:08X} starts a formation at the player's position plus"
    " `position` (x, y, z), headed by `angles`: pitch, yaw and roll as 32-bit binary"
    " angles (0x40000000 is 90 degrees). At every task tick, about 30 a second, a step"
    " adds its `turn` to the angles and moves the formation `speed` units along its"
    " heading: the first step for `ticks` ticks, each later one for `ticks` + 1. After"
    " the last step the formation ends, and the members still flying go with it."
    " `members` place each member around the formation's centre, turned with it. The"
    " formation reads `flags` 0x4000 and 0x8000, and enemy code may test the low bits"
    " (the 1ST, 2ND and 6TH ZONE's does). The code that passes a record fixes its"
    " numbers of steps and members, so edits must keep them; which enemy each member"
    " is, is also the zone's code.")


def render_formation(blob, code, formation, users):
    """The [[formations]] entry of one record."""
    lines = ["", "[[formations]]"]
    for at in formation.calls:
        starters = []
        for callback, waves in users.get(at, {}).items():
            when = gate(code, index_of(callback), index_of(at))
            starters.append(f"wave{'s' * (len(waves) > 1)} {listing(waves)}"
                            f" (callback 0x{callback:08X})" + (f", {when}" if when else ""))
        how = "; ".join(starters) or "code outside this table's callbacks"
        lines += comment(f"Started at 0x{at:08X} by {how}, with {formation.steps} steps and"
                         f" {formation.members} members. Its steps are at"
                         f" 0x{formation.steps_at:08X}, its members at"
                         f" 0x{formation.members_at:08X}.")
    offset = formation.address - BASE
    placement = PLACEMENT.unpack_from(blob, offset + POINTERS.size)
    position, angles = placement[:3], placement[3:]
    lines += [f"address = 0x{formation.address:08X}  # file offset 0x{offset:X}",
              f"position = [{', '.join(map(str, position))}]",
              f"angles = [{', '.join(f'0x{a:08X}' for a in angles)}]  # degrees: "
              + ", ".join(degrees(a) for a in angles),
              "steps = ["]
    for m in range(formation.steps):
        *turn, speed, ticks, flags = STEP_FIELDS.unpack_from(
            blob, formation.steps_at - BASE + STEP * m)
        turns = [f"{axis} {degrees(t)}" for axis, t in zip(("pitch", "yaw", "roll"), turn) if t]
        lines.append(f"  {{ turn = [{', '.join(map(str, turn))}], speed = {speed},"
                     f" ticks = {ticks}, flags = 0x{flags:04X} }},"
                     + (f"  # {', '.join(turns)} (degrees a tick)" if turns else ""))
    lines.append("]")
    lines.append("members = [")
    for m in range(formation.members):
        x, y, z = OFFSET.unpack_from(blob, formation.members_at - BASE + MEMBER * m)
        lines.append(f"  [{x}, {y}, {z}],")
    lines.append("]")
    return lines


def render(path, blob):
    """The TOML dump of a zone file's timeline and formations."""
    timeline, formations, _ = layout(blob)
    folder = path.split("/")[0]
    label = f", the {LABELS[folder]}" if folder in LABELS else ""
    code = words(blob)
    own = code.count(jal(CLEAR_ROUTINE))
    entries = [f"{{ callback = 0x{callback:08X}, delay = {delay_text(delay)} }},"
               for callback, delay in timeline.waves]
    width = max(len(e) for e in entries)
    what = "Wave timeline and formations" if formations else "Wave timeline"
    lines = [
        *comment(f"{what} of {path}{label}, read from the player's disc by"
                 " scripts/zones/zone_data.py. It holds data from the disc, so keep it out"
                 " of the repository. Edit it, then write the zone file with"),
        "#   python3 scripts/zones/zone_data.py build <this file> --out <zone file>",
        f"format = {FORMAT}",
        f'file = "{path}"',
        f"size = {len(blob)}",
        f'sha256 = "{hashlib.sha256(blob).hexdigest()}"',
        "",
        "[timeline]",
        f"# The zone passes this table to 0x{RUNNER_NEW:08X} at 0x{timeline.call_at:08X}. Entry 0",
        "# starts with the zone. Each later one starts when the previous delay has",
        "# run out, in runner ticks of about two frames, or as soon as the runner",
        "# has no child task left (the tasks the waves create are its children);",
        "# \"clear\" waits only for that. After the end entry the runner waits 90",
        "# ticks, then the zone is cleared. Edits must keep a wave first, use only",
        "# the callbacks listed here, and fit in the slots, end entry included. The",
        f"# notes list each callback's calls (for 0x{FORMATION:08X}, its formation",
        "# record and two counts).",
    ]
    if own:
        lines.append(f"# This zone also calls the clear routine from its own code ({own}"
                     f" call{'s' if own > 1 else ''}), so it can end before its table does.")
    lines += [
        f"address = 0x{timeline.address:08X}  # file offset 0x{timeline.address - BASE:X}",
        f"slots = {timeline.slots}  # 8-byte entries in place, the end entry included",
        "waves = [",
        *(f"  {entry:<{width}}  # {describe(blob, callback)}"
          for entry, (callback, _) in zip(entries, timeline.waves)),
        "]",
    ]
    if timeline.end is None:
        lines.append("end = false  # no end entry: the stock table runs into other data")
    else:
        lines.append(f"end = {timeline.end}  # the end entry's second word, which the runner"
                     " never reads")
    if formations:
        users = {}
        for n, (callback, _) in enumerate(timeline.waves):  # every word the callback can reach
            for i in flow(code, index_of(callback)):
                users.setdefault(address_of(i), {}).setdefault(callback, []).append(n)
        lines += ["", *FORMATION_NOTES]
        for formation in formations:
            lines += render_formation(blob, code, formation, users)
    return "\n".join(lines) + "\n"


def expect_keys(table, keys, where):
    if not isinstance(table, dict):
        raise ZoneError(f"{where}: expected a table")
    missing, extra = keys - table.keys(), table.keys() - keys
    if missing or extra:
        raise ZoneError(f"{where}: " + "; ".join(
            part for part in (missing and "missing " + ", ".join(sorted(missing)),
                              extra and "unknown " + ", ".join(sorted(extra))) if part))


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def in_range(value, bounds):
    """True for an integer, not a bool, from bounds' low to its high, both included."""
    low, high = bounds
    return integer(value) and low <= value <= high


def integers(value, count, bounds):
    return (isinstance(value, list) and len(value) == count
            and all(in_range(v, bounds) for v in value))


def parse_formations(formations, source):
    if not isinstance(formations, list):
        raise ZoneError(f"{source}: formations must be a list")
    for n, formation in enumerate(formations):
        where = f"{source} formation {n}"
        expect_keys(formation, {"address", "position", "angles", "steps", "members"}, where)
        if not integer(formation["address"]):
            raise ZoneError(f"{where}: address must be an integer")
        if not integers(formation["position"], 3, S32):
            raise ZoneError(f"{where}: position must be three 32-bit integers")
        if not integers(formation["angles"], 3, U32):
            raise ZoneError(f"{where}: angles must be three integers from 0 to 0xFFFFFFFF")
        if not isinstance(formation["steps"], list) or not isinstance(formation["members"], list):
            raise ZoneError(f"{where}: steps and members must be lists")
        for m, step in enumerate(formation["steps"]):
            expect_keys(step, {"turn", "speed", "ticks", "flags"}, f"{where} step {m}")
            if not (integers(step["turn"], 3, S32) and in_range(step["speed"], S32)):
                raise ZoneError(f"{where} step {m}: turn must be three 32-bit integers, and"
                                " speed one")
            if not (in_range(step["ticks"], U16) and in_range(step["flags"], U16)):
                raise ZoneError(f"{where} step {m}: ticks and flags must be from 0 to 65535")
        for m, member in enumerate(formation["members"]):
            if not integers(member, 3, S16):
                raise ZoneError(f"{where} member {m}: must be three integers from -32768"
                                " to 32767")


def parse(text, source):
    """Read and check a dump's values."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ZoneError(f"{source}: {exc}")
    if "format" in doc and not (integer(doc["format"]) and doc["format"] in (1, FORMAT)):
        raise ZoneError(f"{source}: format must be 1 or {FORMAT}")
    keys = {"format", "file", "size", "sha256", "timeline"}
    if doc.get("format") == FORMAT and "formations" in doc:
        keys.add("formations")  # optional: a dump without them keeps the stock ones
    expect_keys(doc, keys, source)
    if not (isinstance(doc["file"], str) and re.fullmatch(r"([A-Z0-9]+)/\1\.BIN", doc["file"])):
        raise ZoneError(f"{source}: file must name a zone file such as \"S1/S1.BIN\"")
    if not integer(doc["size"]) or not (isinstance(doc["sha256"], str)
                                        and re.fullmatch(r"[0-9a-f]{64}", doc["sha256"])):
        raise ZoneError(f"{source}: size must be an integer and sha256 64 hex digits")
    timeline = doc["timeline"]
    expect_keys(timeline, {"address", "slots", "waves", "end"}, f"{source} [timeline]")
    if not integer(timeline["address"]) or not integer(timeline["slots"]):
        raise ZoneError(f"{source}: address and slots must be integers")
    if not isinstance(timeline["waves"], list):
        raise ZoneError(f"{source}: waves must be a list")
    for n, wave in enumerate(timeline["waves"]):
        expect_keys(wave, {"callback", "delay"}, f"{source} wave {n}")
        delay = wave["delay"]
        if not integer(wave["callback"]):
            raise ZoneError(f"{source} wave {n}: callback must be an address")
        if delay != "clear" and not in_range(delay, TICK_COUNT):
            raise ZoneError(f"{source} wave {n}: delay must be a tick count of 0 or more,"
                            " or \"clear\"")
    end = timeline["end"]
    if end is not False and not in_range(end, S32):
        raise ZoneError(f"{source}: end must be a 32-bit integer or false")
    if "formations" in doc:
        parse_formations(doc["formations"], source)
    return doc


def build(blob, doc, source):
    """The zone file with the dump's table and formations written in place."""
    if len(blob) != doc["size"] or hashlib.sha256(blob).hexdigest() != doc["sha256"]:
        raise ZoneError(f"{source}: {doc['file']} on this disc is not the file the dump"
                        " was read from")
    stock_layout = layout(blob)
    stock = stock_layout.timeline
    timeline = doc["timeline"]
    if timeline["address"] != stock.address or timeline["slots"] != stock.slots:
        raise ZoneError(f"{source}: address and slots must stay 0x{stock.address:08X} and"
                        f" {stock.slots}")
    allowed = {callback for callback, _ in stock.waves}
    entries = []
    for n, wave in enumerate(timeline["waves"]):
        if wave["callback"] not in allowed:
            raise ZoneError(f"{source} wave {n}: 0x{wave['callback']:08X} is not one of"
                            " this table's callbacks")
        entries.append((wave["callback"], WAIT if wave["delay"] == "clear" else wave["delay"]))
    if not entries:
        raise ZoneError(f"{source}: needs a wave first; the constructor calls entry 0"
                        " without checking it")
    if timeline["end"] is False:
        if stock.end is not None or len(entries) != stock.slots:
            raise ZoneError(f"{source}: end = false fits only a stock table without an end"
                            " entry, with every slot used")
    else:
        entries.append((0, timeline["end"]))
        if len(entries) > stock.slots:
            raise ZoneError(f"{source}: {len(entries)} entries with the end entry; this table"
                            f" has {stock.slots} slots")
    out = bytearray(blob)
    for n in range(stock.slots):
        ENTRY.pack_into(out, stock.address - BASE + ENTRY.size * n,
                        *(entries[n] if n < len(entries) else (0, 0)))
    if "formations" in doc:
        stock_formations = {formation.address: formation for formation in stock_layout.formations}
        if sorted(edit["address"] for edit in doc["formations"]) != sorted(stock_formations):
            raise ZoneError(f"{source}: formations must list each of this zone's records once: "
                            + (", ".join(f"0x{a:08X}" for a in sorted(stock_formations))
                               or "it has none"))
        for edit in doc["formations"]:
            formation = stock_formations[edit["address"]]
            if len(edit["steps"]) != formation.steps or len(edit["members"]) != formation.members:
                raise ZoneError(f"{source}: formation 0x{formation.address:08X} must keep"
                                f" {formation.steps} steps and {formation.members} members,"
                                " which the code that passes it fixes")
            PLACEMENT.pack_into(out, formation.address - BASE + POINTERS.size,
                                *edit["position"], *edit["angles"])
            for m, step in enumerate(edit["steps"]):
                STEP_FIELDS.pack_into(out, formation.steps_at - BASE + STEP * m, *step["turn"],
                                      step["speed"], step["ticks"], step["flags"])
            for m, member in enumerate(edit["members"]):
                OFFSET.pack_into(out, formation.members_at - BASE + MEMBER * m, *member)
    return bytes(out)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an integer beyond float range
        return False


def parse_recipe(text, source):
    """Read and check a remix recipe's values."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ZoneError(f"{source}: {exc}")
    expect_keys(doc, {"format", "id", "version", "name", "description", "zones"}, source)
    if not (integer(doc["format"]) and doc["format"] == REMIX):
        raise ZoneError(f"{source}: format must be {REMIX}")
    for key in ("id", "version", "name", "description"):
        if not isinstance(doc[key], str):
            raise ZoneError(f"{source}: {key} must be a string")
    if not doc["name"]:
        raise ZoneError(f"{source}: name must not be empty; the framework refuses a package or"
                        " feature without a name")
    check_package(doc["id"], doc["version"], f"{source}: id", f"{source}: version")
    if not isinstance(doc["zones"], list) or not doc["zones"]:
        raise ZoneError(f"{source}: zones must list at least one zone")
    seen = set()
    for n, edits in enumerate(doc["zones"]):
        where = f"{source} zone {n}"
        if not isinstance(edits, dict):
            raise ZoneError(f"{where}: expected a table")
        expect_keys(edits, {"zone"} | (edits.keys() & {"waves", "formations"}), where)
        if not (isinstance(edits["zone"], str) and re.fullmatch(r"[A-Za-z0-9]+", edits["zone"])):
            raise ZoneError(f'{where}: zone must name a zone\'s folder, such as "S1"')
        edits["zone"] = edits["zone"].upper()
        if edits["zone"] in seen:
            raise ZoneError(f"{source}: zone {edits['zone']} is listed twice")
        seen.add(edits["zone"])
        where = f"{source} zone {edits['zone']}"
        if not isinstance(edits.get("waves", []), list):
            raise ZoneError(f"{where}: waves must be a list")
        for m, wave in enumerate(edits.get("waves", [])):
            expect_keys(wave, {"wave", "delay"}, f"{where} wave {m}")
            if not (integer(wave["wave"]) and wave["wave"] >= 0):
                raise ZoneError(f"{where} wave {m}: wave must be a stock wave's number, 0 or more")
            delay = wave["delay"]
            if delay not in ("clear", "stock") and not in_range(delay, TICK_COUNT):
                raise ZoneError(f'{where} wave {m}: delay must be a tick count of 0 or more,'
                                ' "clear" or "stock"')
        if not isinstance(edits.get("formations", []), list):
            raise ZoneError(f"{where}: formations must be a list")
        addresses = set()
        for m, edit in enumerate(edits.get("formations", [])):
            at = f"{where} formation {m}"
            if not isinstance(edit, dict) or "address" not in edit:
                raise ZoneError(f"{at}: expected a table with an address")
            expect_keys(edit, {"address"} | (edit.keys() & EDITS), at)
            if not in_range(edit["address"], U32):
                raise ZoneError(f"{at}: address must be an address")
            if edit["address"] in addresses:
                raise ZoneError(f"{where}: formation 0x{edit['address']:08X} is listed twice")
            addresses.add(edit["address"])
            at = f"{where} formation 0x{edit['address']:08X}"
            if "spread" in edit and not (number(edit["spread"]) and edit["spread"] > 0):
                raise ZoneError(f"{at}: spread must be a number above 0")
            if "pace" in edit and not (number(edit["pace"]) and edit["pace"] > 0):
                raise ZoneError(f"{at}: pace must be a number above 0")
            if "yaw" in edit and not number(edit["yaw"]):
                raise ZoneError(f"{at}: yaw must be a number of degrees")
            if "move" in edit and not integers(edit["move"], 3, S32):
                raise ZoneError(f"{at}: move must be three 32-bit integers")
    return doc


def reshape(formation, edit, where):
    """A formation's values, as a dump gives them, with a recipe's edits, in
    place: spread scales the members' offsets; pace multiplies the steps'
    speeds and turns and divides their durations (the first step lasts ticks
    ticks, a later one ticks + 1); yaw turns the position, and the yaw angle,
    about the vertical axis through the player's position when the formation
    starts; move is then added to the position."""
    try:
        if "spread" in edit:
            formation["members"] = [[round(c * edit["spread"]) for c in member]
                                    for member in formation["members"]]
            for m, member in enumerate(formation["members"]):
                if not integers(member, 3, S16):
                    raise ZoneError(f"{where}: spread {edit['spread']} gives member {m} the offset"
                                    f" {member}, beyond -32768 to 32767")
        if "pace" in edit:
            pace = edit["pace"]
            for n, step in enumerate(formation["steps"]):
                later = 1 if n else 0
                step["turn"] = [round(t * pace) for t in step["turn"]]
                step["speed"] = round(step["speed"] * pace)
                ticks = max(0, round((step["ticks"] + later) / pace) - later)
                if step["ticks"] and not ticks and not later:
                    raise ZoneError(f"{where}: pace {pace} leaves step 0 no ticks; what the game"
                                    " does with a first step of 0 ticks is unknown")
                step["ticks"] = ticks
                if not (integers(step["turn"], 3, S32) and in_range(step["speed"], S32)
                        and in_range(step["ticks"], U16)):
                    raise ZoneError(f"{where}: pace {pace} gives step {n} a turn, speed or tick"
                                    " count beyond its field")
        if "yaw" in edit:
            x, y, z = formation["position"]
            cos, sin = math.cos(math.radians(edit["yaw"])), math.sin(math.radians(edit["yaw"]))
            formation["position"] = [round(x * cos + z * sin), y, round(z * cos - x * sin)]
            turn = round(edit["yaw"] * FULL_TURN / 360)
            formation["angles"][1] = (formation["angles"][1] + turn) % FULL_TURN
    except OverflowError:
        raise ZoneError(f"{where}: the edits give values beyond the record's fields")
    if "move" in edit:
        formation["position"] = [p + d for p, d in zip(formation["position"], edit["move"])]
    if not integers(formation["position"], 3, S32):
        raise ZoneError(f"{where}: the edits give the position {formation['position']},"
                        " beyond 32-bit integers")


def remix_zone(doc, edits, where):
    """A zone's dump, read into doc, with a recipe's edits of that zone."""
    stock = doc["timeline"]["waves"]
    if "waves" in edits:
        waves = []
        for m, wave in enumerate(edits["waves"]):
            if wave["wave"] >= len(stock):
                raise ZoneError(f"{where} wave {m}: the stock table has waves 0 to"
                                f" {len(stock) - 1}")
            old = stock[wave["wave"]]
            waves.append({"callback": old["callback"],
                          "delay": old["delay"] if wave["delay"] == "stock" else wave["delay"]})
        doc["timeline"]["waves"] = waves
    records = {formation["address"]: formation for formation in doc.get("formations", [])}
    for edit in edits.get("formations", []):
        if edit["address"] not in records:
            raise ZoneError(f"{where}: no formation record 0x{edit['address']:08X}; this zone's"
                            " records: " + (", ".join(f"0x{a:08X}" for a in sorted(records))
                                            or "none"))
        reshape(records[edit["address"]], edit, f"{where} formation 0x{edit['address']:08X}")


def output_path(path):
    """Resolve an output path, refusing the repository outside .cache/."""
    resolved = Path(path).resolve()
    if resolved.is_relative_to(REPO) and not resolved.is_relative_to(REPO / ".cache"):
        raise ZoneError(f"{path}: zone data comes from the disc; write it under .cache/ or"
                        " outside the repository")
    return resolved


def write(out, data):
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    except OSError as exc:
        raise ZoneError(f"cannot write {out}: {exc}")


def valid_id(value):
    """The framework's rule for package and feature ids (mod_packages.cpp)."""
    return (len(value) <= 96 and re.fullmatch(r"[a-z0-9._-]+", value) is not None
            and not value.startswith(".") and not value.endswith("."))


def check_package(pkg_id, version, id_label="--id", version_label="--version"):
    if not valid_id(pkg_id):
        raise ZoneError(f"{id_label} {pkg_id}: use lowercase letters, digits, '.', '-' and '_',"
                        " at most 96 characters, not starting or ending with '.'")
    if not re.fullmatch(r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2}", version):
        raise ZoneError(f"{version_label} {version}: use three numbers, such as 1.0.0")


def toml_string(value):
    """JSON's escapes are valid TOML, but TOML also forbids a raw U+007F."""
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007F")


def package(zones, image, image_sha256, pkg_id, version, name, description=None):
    """manifest.toml and the overlay files, as (name, bytes): for each
    ZoneEdit, the built file from the first byte build may change to the last,
    put on the disc in place of the stock bytes. Without a description the
    package holds one zone, and that zone's edits describe it."""
    overlays, members, spans, labels, formations = [], [], [], [], False
    for zone in zones:
        stock_layout = layout(zone.stock)
        start, stop = stock_layout.span
        folder = zone.path.split("/")[0]
        member, payload = f"{folder}.remix.bin", zone.built[start:stop]
        members.append((member, payload))
        spans.append(f"{zone.path}, bytes 0x{start:X} to 0x{stop - 1:X}")
        labels.append(f"the {LABELS.get(folder, folder)}")
        formations = formations or bool(stock_layout.formations)
        overlays += [
            "",
            "[[overlay]]",
            'feature = "remix"',
            'target = "disc_user"',
            f"offset = {zone.lba * USER + start}  # sector {zone.lba} * 2048 + 0x{start:X}",
            f"file = {toml_string(member)}",
            f"sha256 = {toml_string(hashlib.sha256(payload).hexdigest())}",
            f"expected_sha256 = {toml_string(hashlib.sha256(zone.stock[start:stop]).hexdigest())}"]
    disc_note = (f"Built for one disc image, {image.name}; the game must be started from that"
                 " image.")
    if description is None:
        [zone] = zones
        edits = "an edited wave timeline" + (" and formations" if formations else "")
        header = [f"# Built by scripts/zones/zone_data.py from {zone.path} on the player's disc.",
                  f"# {members[0][0]} holds data from that disc: keep this package out of the",
                  "# repository."]
        about = f"Off by default. While on, {labels[0]} plays {edits} ({spans[0]}). {disc_note}"
        description = f"{edits[0].upper()}{edits[1:]} for {labels[0]}."
    else:
        header = comment(
            "Built by scripts/zones/zone_data.py from a remix recipe and"
            f" {listing([zone.path for zone in zones])} on the player's disc."
            f" {listing([member for member, _ in members])} hold{'s' * (len(members) == 1)}"
            " data from that disc: keep this package out of the repository.")
        about = (f"Off by default. While on, the game reads this remix's edits of"
                 f" {listing(labels)} ({'; '.join(spans)}). {disc_note}")
    return "\n".join([
        *header,
        "format_version = 7",
        f"id = {toml_string(pkg_id)}",
        f"version = {toml_string(version)}",
        f"name = {toml_string(name)}",
        'author = "zone_data.py"',
        f"description = {toml_string(description)}",
        'resolver = "declarative"',
        'save_compatibility = "shared"',
        "",
        "# The runtime hashes the disc image it mounts (the data file a cue sheet",
        f"# names); the overlay{'s apply' if len(zones) > 1 else ' applies'} only when that is"
        " this one.",
        "[[target]]",
        f"game_id = {toml_string(GAME_ID)}",
        f"disc_sha256 = {toml_string(image_sha256)}",
        "",
        "[[feature]]",
        'id = "remix"',
        f"name = {toml_string(name)}",
        f"description = {toml_string(about)}",
        'group = "Remix"',
        "default_enabled = false",
        *overlays,
        ""]), members


def archive(members):
    """A zip with stored entries and fixed times: the same input, the same bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return buf.getvalue()


def load_dump(source):
    try:
        text = source.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise ZoneError(f"cannot read {source}: {exc}")
    return parse(text, source)


def zone_blob(disc, files, path):
    if path not in files:
        raise ZoneError(f"{path} is not on the disc")
    return disc.read(*files[path])


def zone_path(files, zone):
    name = zone.upper().split("/")[0]
    path = f"{name}/{name}.BIN"
    if path not in files:
        raise ZoneError(f"no zone file {path}; zone files: "
                        + ", ".join(p.split("/")[0] for p in sorted(files)))
    return path


def cmd_list(disc, files, _args):
    for path in sorted(files):
        blob = zone_blob(disc, files, path)
        folder = path.split("/")[0]
        try:
            timeline, formations, _ = layout(blob)
        except ZoneError as exc:
            status = str(exc)
        else:
            wave_count = len(timeline.waves)
            clear = sum(1 for _, delay in timeline.waves if delay == WAIT)
            status = (f"table 0x{timeline.address:08X}, {wave_count} wave{'s' * (wave_count != 1)}"
                      f" ({clear} clear), "
                      + ("an end entry" if timeline.end is not None else "no end entry")
                      + f", {timeline.slots} slots")
            if formations:
                count = len(formations)
                status += f", {count} formation{'s' * (count != 1)}"
        print(f"{path:<16} {LABELS.get(folder, ''):<9} {len(blob):>6} bytes  {status}")
    return 0


def cmd_dump(disc, files, args):
    path = zone_path(files, args.zone)
    text = render(path, zone_blob(disc, files, path))
    if args.out == "-":
        sys.stdout.write(text)
        return 0
    out = output_path(args.out or OUT_DIR / f"{path.split('/')[0]}.zone.toml")
    write(out, text.encode())
    print(f"wrote {out}")
    return 0


def cmd_build(disc, files, args):
    source = Path(args.file)
    doc = load_dump(source)
    path = doc["file"]
    stock = zone_blob(disc, files, path)
    out = output_path(args.out or OUT_DIR / path.split("/")[1])
    built = build(stock, doc, source)
    changed = [n for n in range(len(stock)) if stock[n] != built[n]]
    write(out, built)
    span = (f"bytes 0x{changed[0]:X} to 0x{changed[-1]:X} differ from the stock file"
            if changed else "identical to the stock file")
    print(f"wrote {out}: {span}; sha256 {hashlib.sha256(built).hexdigest()}")
    return 0


def cmd_check(disc, files, _args):
    checked = same = 0
    for path in sorted(files):
        blob = zone_blob(disc, files, path)
        try:
            built = build(blob, parse(render(path, blob), path), path)
        except NoTimeline:
            continue
        except ZoneError as exc:
            built = None
            print(f"{path}: {exc}")
        checked += 1
        same += built == blob
        if built is not None:
            print(f"{path}: {'identical' if built == blob else 'DIFFERS'}"
                  " after a dump and a build")
    print(f"zone files with a timeline: {checked}, rebuilt identical: {same}")
    return 0 if checked and same == checked else 1


def cmd_package(disc, files, args):
    source = Path(args.file)
    doc = load_dump(source)
    path = doc["file"]
    stock = zone_blob(disc, files, path)
    built = build(stock, doc, source)
    folder = path.split("/")[0]
    pkg_id = args.id or f"omega.remix.{folder.lower()}"
    check_package(pkg_id, args.version)
    name = args.name or f"{LABELS.get(folder, folder)} Remix"
    try:
        name.encode()
    except UnicodeEncodeError:
        raise ZoneError(f"--name {name!r} is not valid UTF-8 text")
    out = output_path(args.out or OUT_DIR / f"{pkg_id}-{args.version}.psxmod")
    manifest, members = package([ZoneEdit(path, files[path][0], stock, built)], disc.bin,
                                disc.image_sha256(), pkg_id, args.version, name)
    write(out, archive([("manifest.toml", manifest.encode()), *members]))
    [(member, payload)] = members
    same = " (the stock bytes)" if built == stock else ""
    print(f"wrote {out}: {pkg_id} {args.version}, {member} replaces {len(payload)} bytes"
          f" of {path}{same}; it applies only to a game started from {disc.bin}")
    return 0


def cmd_remix(disc, files, args):
    source = Path(args.file)
    try:
        text = source.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise ZoneError(f"cannot read {source}: {exc}")
    recipe = parse_recipe(text, source)
    zones = []
    for edits in recipe["zones"]:
        where = f"{source} zone {edits['zone']}"
        try:
            path = zone_path(files, edits["zone"])
            stock = zone_blob(disc, files, path)
            doc = parse(render(path, stock), path)
        except ZoneError as exc:
            raise ZoneError(f"{where}: {exc}")
        remix_zone(doc, edits, where)
        zones.append(ZoneEdit(path, files[path][0], stock, build(stock, doc, where)))
    out = output_path(args.out or OUT_DIR / f"{recipe['id']}-{recipe['version']}.psxmod")
    manifest, members = package(zones, disc.bin, disc.image_sha256(), recipe["id"],
                                recipe["version"], recipe["name"], recipe["description"])
    write(out, archive([("manifest.toml", manifest.encode()), *members]))
    for zone, (member, payload) in zip(zones, members):
        changed = sum(a != b for a, b in zip(zone.stock, zone.built))
        print(f"{zone.path}: {member} replaces {len(payload)} bytes, {changed} of them changed")
    print(f"wrote {out}: {recipe['id']} {recipe['version']},"
          f" {len(zones)} zone{'s' * (len(zones) != 1)}; it applies only to a game started"
          f" from {disc.bin}")
    return 0


def main():
    sys.stdout.reconfigure(errors="backslashreplace")  # paths may hold bytes that are not UTF-8
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--disc", type=Path, default=DISC,
                        help="the game's cue sheet (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="the disc's zone files and their tables")
    dump = sub.add_parser("dump", help="write a zone's table and formations as TOML")
    dump.add_argument("zone", help="the zone's folder on the disc, such as S1 or U4")
    dump.add_argument("--out", help="output file, or - for stdout"
                      " (default: .cache/zones/<zone>.zone.toml)")
    build_cmd = sub.add_parser("build", help="write the zone file with the edits")
    build_cmd.add_argument("file", help="a dump, edited")
    build_cmd.add_argument("--out", help="the zone file to write"
                           " (default: .cache/zones/<zone>.BIN)")
    sub.add_parser("check", help="dump and rebuild every zone; the bytes must match")
    pkg = sub.add_parser("package", help="write a .psxmod that loads the edits")
    pkg.add_argument("file", help="a dump, edited")
    pkg.add_argument("--id", help="package id (default: omega.remix.<zone>)")
    pkg.add_argument("--name", help="name on the Mods page (default: <zone> Remix)")
    pkg.add_argument("--version", default="1.0.0", help="package version (default: %(default)s)")
    pkg.add_argument("--out", help="the package to write"
                     " (default: .cache/zones/<id>-<version>.psxmod)")
    remix = sub.add_parser("remix", help="write one .psxmod that loads a remix recipe's edits")
    remix.add_argument("file", help="a remix recipe, such as scripts/zones/remixes/crossfire.toml")
    remix.add_argument("--out", help="the package to write"
                       " (default: .cache/zones/<id>-<version>.psxmod)")
    args = parser.parse_args()
    commands = {"list": cmd_list, "dump": cmd_dump, "build": cmd_build, "check": cmd_check,
                "package": cmd_package, "remix": cmd_remix}
    try:
        disc = Disc(args.disc)
        return commands[args.command](disc, disc.zone_files(), args)
    except ZoneError as exc:
        print(f"zone_data.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

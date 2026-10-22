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
"""
import argparse
import collections
import hashlib
import io
import json
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
STEP, MEMBER, RECORD = 20, 8, 32  # bytes in a formation step, member and record
DIFFICULTY = 0x800A7C34   # the zone handler's copy of the difficulty (0 on NORMAL)
WAIT = -100               # a delay that waits only for the runner's children
FORMAT = 2                # dumps of format 1 have no formations
GAME_ID = "SCUS-94449"    # game.toml [game] id, which packages target
SECTOR, HEADER, USER = 2352, 24, 2048  # MODE2/2352 form 1 sectors
LABELS = {"S1": "1ST ZONE", "S2": "2ND ZONE", "S3": "3RD ZONE", "S4": "4TH ZONE",
          "S5": "5TH ZONE", "S6": "6TH ZONE", "S8": "7TH ZONE", "S9": "8TH ZONE",
          "S10": "LAST ZONE"}


class ZoneError(Exception):
    pass


class NoTimeline(ZoneError):
    pass


Formation = collections.namedtuple(
    "Formation", "address steps_at steps members_at members calls")


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
            while pos < start + USER and data[pos]:
                rec = data[pos:pos + data[pos]]
                name = rec[33:33 + rec[32]]
                if name not in (b"\x00", b"\x01"):
                    yield (name.decode("ascii"), int.from_bytes(rec[2:6], "little"),
                           int.from_bytes(rec[10:14], "little"), bool(rec[25] & 2))
                pos += rec[0]

    def zone_files(self):
        """{"S1/S1.BIN": (lba, size), ...}: each directory's file named after it."""
        pvd = self.sectors(16, 1)
        if pvd[:6] != b"\x01CD001":
            raise ZoneError(f"{self.bin}: no ISO 9660 volume")
        root = pvd[156:190]
        found = {}
        for name, lba, size, is_dir in self.directory(
                int.from_bytes(root[2:6], "little"), int.from_bytes(root[10:14], "little")):
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


def jal(target):
    return 0x0C000000 | (target & 0x0FFFFFFF) >> 2


def sx16(value):
    return value - 0x10000 if value & 0x8000 else value


def sx32(value):
    return value - 2**32 if value & 0x80000000 else value


def control(word):
    """True for jumps and branches, whose delay slots end straight-line code."""
    op = word >> 26
    return 1 <= op <= 7 or (op == 0 and word & 0x3F in (0x08, 0x09))


def destination(word):
    """The register an instruction writes, if any (common MIPS I forms)."""
    op = word >> 26
    if op == 0:
        return (word >> 11) & 31 if word & 0x3F not in (0x08, 0x18, 0x19, 0x1A, 0x1B) else None
    if 0x08 <= op <= 0x0F or 0x20 <= op <= 0x26:
        return (word >> 16) & 31
    if op in (0x10, 0x12) and (word >> 21) & 31 in (0, 2):  # mfc0, mfc2, cfc2
        return (word >> 16) & 31
    return 31 if op == 3 else None


def trace(seq, k, reg, steps=32):
    """Value of reg after seq[k], from straight-line lui/addiu/ori/move code."""
    while reg and k >= 0 and steps > 0:
        word = seq[k]
        op, rs, rt, imm = word >> 26, (word >> 21) & 31, (word >> 16) & 31, word & 0xFFFF
        if op == 0x0F and rt == reg:
            return imm << 16
        if op in (0x09, 0x0D) and rt == reg:
            base = trace(seq, k - 1, rs, steps - 1)
            if base is None:
                return None
            return (base + sx16(imm)) & 0xFFFFFFFF if op == 0x09 else base | imm
        if (op == 0 and word & 0x3F in (0x21, 0x25) and (word >> 11) & 31 == reg
                and 0 in (rs, rt)):
            reg = rs or rt
        elif destination(word) == reg or control(word):
            return None
        k -= 1
        steps -= 1
    return 0 if reg == 0 else None


def argument(ws, call, reg):
    """Register reg as the function called by the jal at ws[call] receives it."""
    seq = ws[:call] + ws[call + 1:call + 2]  # the delay slot runs before the call
    return trace(seq, len(seq) - 1, reg)


def read_table(blob):
    """(call address, table address, [(callback, delay)], end delay or None)."""
    ws = words(blob)
    calls = [i for i, w in enumerate(ws) if w == jal(RUNNER_NEW)]
    if not calls:
        raise NoTimeline(f"no shared wave timeline: nothing calls 0x{RUNNER_NEW:08X}")
    if len(calls) > 1:
        raise ZoneError(f"{len(calls)} calls to 0x{RUNNER_NEW:08X}; expected one")
    address = argument(ws, calls[0], 5)
    if address is None or address % 4 or not BASE <= address < BASE + len(blob) - 7:
        raise ZoneError("cannot trace the table address passed at "
                        f"0x{BASE + 4 * calls[0]:08X}")
    waves, end, off = [], None, address - BASE
    while off + 8 <= len(blob):
        callback, delay = struct.unpack_from("<Ii", blob, off)
        if callback == 0:
            end = delay
            break
        if callback % 4 or not BASE <= callback < BASE + len(blob):
            break  # no end entry: the table runs into other data
        waves.append((callback, delay))
        off += 8
    if not waves:
        raise ZoneError(f"the table at 0x{address:08X} does not start with a wave")
    return BASE + 4 * calls[0], address, waves, end


def read_formations(blob):
    """A Formation for every record the zone passes to 0x80057F0C, by address."""
    ws = words(blob)
    found = {}
    for k, word in enumerate(ws):
        if word != jal(FORMATION):
            continue
        at = BASE + 4 * k
        rec, steps, members = (argument(ws, k, reg) for reg in (5, 6, 7))
        if rec is None or steps is None or members is None:
            raise ZoneError(f"cannot trace the formation record and counts passed at 0x{at:08X}")
        if not (0 < steps < 0x8000 and 0 < members < 0x8000):
            raise ZoneError(f"the call at 0x{at:08X} starts a formation with {sx32(steps)} steps"
                            f" and {sx32(members)} members")
        if rec % 4 or not BASE <= rec <= BASE + len(blob) - RECORD:
            raise ZoneError(f"the formation record 0x{rec:08X} passed at 0x{at:08X} is not in"
                            " the file")
        counts = found.setdefault(rec, [steps, members, []])
        if counts[:2] != [steps, members]:
            raise ZoneError(f"the formation record 0x{rec:08X} is passed with {counts[0]} steps"
                            f" and {counts[1]} members, and at 0x{at:08X} with {steps} and"
                            f" {members}")
        counts[2].append(at)
    formations = []
    for rec in sorted(found):
        steps, members, calls = found[rec]
        steps_at, members_at = struct.unpack_from("<2I", blob, rec - BASE)
        for part, start, size in (("steps", steps_at, STEP * steps),
                                  ("members", members_at, MEMBER * members)):
            if start % 4 or not BASE <= start <= BASE + len(blob) - size:
                raise ZoneError(f"the {part} of the formation record 0x{rec:08X}, at"
                                f" 0x{start:08X}, are not in the file")
        formations.append(Formation(rec, steps_at, steps, members_at, members, calls))
    return formations


def layout(blob):
    """read_table, read_formations, and the byte ranges build may write: the
    table's slots and each formation's record, steps and members. They must
    not overlap, since build writes each in place."""
    call, address, waves, end = read_table(blob)
    formations = read_formations(blob)
    ranges = [(address, address + 8 * (len(waves) + (end is not None)), "the table")]
    for f in formations:
        ranges += [(f.address, f.address + RECORD, f"formation record 0x{f.address:08X}"),
                   (f.steps_at, f.steps_at + STEP * f.steps, f"the steps of 0x{f.address:08X}"),
                   (f.members_at, f.members_at + MEMBER * f.members,
                    f"the members of 0x{f.address:08X}")]
    ranges.sort()
    for before, after in zip(ranges, ranges[1:]):  # sorted by start: neighbours suffice
        if after[0] < before[1]:
            raise ZoneError(f"{before[2]} and {after[2]} overlap")
    return call, address, waves, end, formations, ranges


def callback_span(ws, callback):
    """Word indices of a callback's code up to its first `jr $ra` and delay slot,
    whose calls the timeline's notes list."""
    start = (callback - BASE) // 4
    for k in range(start + 1, min(len(ws), start + 256)):
        if ws[k - 1] == 0x03E00008:
            return range(start, k + 1)
    return range(start, min(len(ws), start + 256))


def flow(ws, entry):
    """{word index: where control goes next} for the code reached from word
    entry. A jump or branch runs its delay slot, then goes to its target and,
    if conditional, to the word after the slot; a call (jal, jalr, bltzal,
    bgezal) returns to the word after its slot; jr, and indices outside the
    file, end a path."""
    graph, todo = {}, [entry]
    while todo:
        i = todo.pop()
        while 0 <= i < len(ws) and i not in graph:
            word = ws[i]
            op, rt, funct = word >> 26, (word >> 16) & 31, word & 0x3F
            if op == 0 and funct == 0x08:  # jr
                graph[i] = []
            elif op == 0x02:  # j
                target = ((BASE + 4 * i + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
                graph[i] = [(target - BASE) >> 2]
            elif op == 0x03 or (op == 0 and funct == 0x09) or (op == 0x01 and rt & 0x10):
                graph[i] = [i + 2]
            elif op in (0x01, 0x04, 0x05, 0x06, 0x07):  # conditional branches
                graph[i] = [i + 1 + sx16(word & 0xFFFF), i + 2]
            else:
                graph[i] = [i + 1]
                i += 1
                continue
            todo += graph[i]
            break
    return graph


def loaded(ws, start, j, reg):
    """The address of the word reg holds at word j, if an lw from word start on
    wrote reg last and the code from start to it gives the address."""
    for i in range(j - 1, start - 1, -1):
        if destination(ws[i]) == reg:
            if ws[i] >> 26 != 0x23:  # lw
                return None
            base = trace(ws[start:i], i - 1 - start, (ws[i] >> 21) & 31)
            return None if base is None else (base + sx16(ws[i] & 0xFFFF)) & 0xFFFFFFFF
    return None


def gate(ws, entry, k):
    """When the callback whose code starts at word entry runs the instruction at
    word k: None if on every path, "only while the difficulty word ... is zero"
    (or "non-zero") if that word decides it, else "only on some paths". The
    paths are flow()'s. A conditional branch goes both ways, except a beqz or
    bnez on a register that its basic block loaded from the difficulty word:
    that goes the way the word sends it, once with the word zero and once
    non-zero."""
    graph = flow(ws, entry)
    starts = {entry} | {n for i, nxt in graph.items() if control(ws[i]) for n in nxt}
    zero = {}  # the branches on the difficulty word: whether taken while it is zero
    for i in graph:
        op, rs, rt = ws[i] >> 26, (ws[i] >> 21) & 31, (ws[i] >> 16) & 31
        if op in (0x04, 0x05) and rt == 0 and rs:
            start = max((s for s in starts if s <= i), default=i)
            if loaded(ws, start, i, rs) == DIFFICULTY:
                zero[i] = op == 0x04
    found = []
    for value in (0, 1):
        ran = left = False
        todo, seen = [entry], set()
        while todo:
            i = todo.pop()
            if i in seen:
                continue
            seen.add(i)
            if i == k:  # this path runs it; only paths that avoid it go on
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
    ws = words(blob)
    notes = []
    for k in callback_span(ws, callback):
        if ws[k] >> 26 == 3:
            target = (BASE & 0xF0000000) | (ws[k] & 0x03FFFFFF) << 2
            note = f"0x{target:08X}"
            if target == FORMATION:
                args = (argument(ws, k, reg) for reg in (5, 6, 7))
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
    return f"{value * 360 / 2**32:g}"


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


def render_formation(blob, ws, f, users):
    """The [[formations]] entry of one record."""
    lines = ["", "[[formations]]"]
    for at in f.calls:
        parts = []
        for cb, n in users.get(at, {}).items():
            when = gate(ws, (cb - BASE) // 4, (at - BASE) // 4)
            parts.append(f"wave{'s' * (len(n) > 1)} {listing(n)} (callback 0x{cb:08X})"
                         + (f", {when}" if when else ""))
        how = "; ".join(parts) or "code outside this table's callbacks"
        lines += comment(f"Started at 0x{at:08X} by {how}, with {f.steps} steps and"
                         f" {f.members} members. Its steps are at 0x{f.steps_at:08X}, its"
                         f" members at 0x{f.members_at:08X}.")
    position = struct.unpack_from("<3i", blob, f.address - BASE + 8)
    angles = struct.unpack_from("<3I", blob, f.address - BASE + 20)
    lines += [f"address = 0x{f.address:08X}  # file offset 0x{f.address - BASE:X}",
              f"position = [{', '.join(map(str, position))}]",
              f"angles = [{', '.join(f'0x{a:08X}' for a in angles)}]  # degrees: "
              + ", ".join(degrees(a) for a in angles),
              "steps = ["]
    for m in range(f.steps):
        at = f.steps_at - BASE + STEP * m
        *turn, speed, ticks, flags = struct.unpack_from("<4iHH", blob, at)
        turns = [f"{axis} {degrees(t)}" for axis, t in zip(("pitch", "yaw", "roll"), turn) if t]
        lines.append(f"  {{ turn = [{', '.join(map(str, turn))}], speed = {speed},"
                     f" ticks = {ticks}, flags = 0x{flags:04X} }},"
                     + (f"  # {', '.join(turns)} (degrees a tick)" if turns else ""))
    lines.append("]")
    lines.append("members = [")
    for m in range(f.members):
        x, y, z = struct.unpack_from("<3h", blob, f.members_at - BASE + MEMBER * m)
        lines.append(f"  [{x}, {y}, {z}],")
    lines.append("]")
    return lines


def render(path, blob):
    """The TOML dump of a zone file's timeline and formations."""
    call, address, waves, end, formations, _ = layout(blob)
    slots = len(waves) + (end is not None)
    folder = path.split("/")[0]
    label = f", the {LABELS[folder]}" if folder in LABELS else ""
    ws = words(blob)
    own = ws.count(jal(CLEAR_ROUTINE))
    entries = [f"{{ callback = 0x{cb:08X}, delay = {delay_text(d)} }}," for cb, d in waves]
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
        f"# The zone passes this table to 0x{RUNNER_NEW:08X} at 0x{call:08X}. Entry 0",
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
        f"address = 0x{address:08X}  # file offset 0x{address - BASE:X}",
        f"slots = {slots}  # 8-byte entries in place, the end entry included",
        "waves = [",
        *(f"  {e:<{width}}  # {describe(blob, cb)}" for e, (cb, _) in zip(entries, waves)),
        "]",
    ]
    if end is None:
        lines.append("end = false  # no end entry: the stock table runs into other data")
    else:
        lines.append(f"end = {end}  # the end entry's second word, which the runner never reads")
    if formations:
        users = {}
        for n, (cb, _) in enumerate(waves):  # every word the callback can reach
            for k in flow(ws, (cb - BASE) // 4):
                users.setdefault(BASE + 4 * k, {}).setdefault(cb, []).append(n)
        lines += ["", *FORMATION_NOTES]
        for f in formations:
            lines += render_formation(blob, ws, f, users)
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


def integers(value, count, low, high):
    return (isinstance(value, list) and len(value) == count
            and all(integer(v) and low <= v <= high for v in value))


def parse_formations(formations, source):
    if not isinstance(formations, list):
        raise ZoneError(f"{source}: formations must be a list")
    for n, f in enumerate(formations):
        where = f"{source} formation {n}"
        expect_keys(f, {"address", "position", "angles", "steps", "members"}, where)
        if not integer(f["address"]):
            raise ZoneError(f"{where}: address must be an integer")
        if not integers(f["position"], 3, -2**31, 2**31 - 1):
            raise ZoneError(f"{where}: position must be three 32-bit integers")
        if not integers(f["angles"], 3, 0, 2**32 - 1):
            raise ZoneError(f"{where}: angles must be three integers from 0 to 0xFFFFFFFF")
        if not isinstance(f["steps"], list) or not isinstance(f["members"], list):
            raise ZoneError(f"{where}: steps and members must be lists")
        for m, step in enumerate(f["steps"]):
            expect_keys(step, {"turn", "speed", "ticks", "flags"}, f"{where} step {m}")
            if not (integers(step["turn"], 3, -2**31, 2**31 - 1)
                    and integers([step["speed"]], 1, -2**31, 2**31 - 1)):
                raise ZoneError(f"{where} step {m}: turn must be three 32-bit integers, and"
                                " speed one")
            if not integers([step["ticks"], step["flags"]], 2, 0, 0xFFFF):
                raise ZoneError(f"{where} step {m}: ticks and flags must be from 0 to 65535")
        for m, member in enumerate(f["members"]):
            if not integers(member, 3, -0x8000, 0x7FFF):
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
        if delay != "clear" and not (integer(delay) and 0 <= delay < 2**31):
            raise ZoneError(f"{source} wave {n}: delay must be a tick count of 0 or more,"
                            " or \"clear\"")
    end = timeline["end"]
    if end is not False and not (integer(end) and -2**31 <= end < 2**31):
        raise ZoneError(f"{source}: end must be a 32-bit integer or false")
    if "formations" in doc:
        parse_formations(doc["formations"], source)
    return doc


def build(blob, doc, source):
    """The zone file with the dump's table and formations written in place."""
    if len(blob) != doc["size"] or hashlib.sha256(blob).hexdigest() != doc["sha256"]:
        raise ZoneError(f"{source}: {doc['file']} on this disc is not the file the dump"
                        " was read from")
    _, address, stock, stock_end, formations, _ = layout(blob)
    slots = len(stock) + (stock_end is not None)
    timeline = doc["timeline"]
    if timeline["address"] != address or timeline["slots"] != slots:
        raise ZoneError(f"{source}: address and slots must stay 0x{address:08X} and {slots}")
    allowed = {callback for callback, _ in stock}
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
        if stock_end is not None or len(entries) != slots:
            raise ZoneError(f"{source}: end = false fits only a stock table without an end"
                            " entry, with every slot used")
    else:
        entries.append((0, timeline["end"]))
        if len(entries) > slots:
            raise ZoneError(f"{source}: {len(entries)} entries with the end entry; this table"
                            f" has {slots} slots")
    out = bytearray(blob)
    for n in range(slots):
        struct.pack_into("<Ii", out, address - BASE + 8 * n,
                         *(entries[n] if n < len(entries) else (0, 0)))
    if "formations" in doc:
        stock_formations = {f.address: f for f in formations}
        if sorted(f["address"] for f in doc["formations"]) != sorted(stock_formations):
            raise ZoneError(f"{source}: formations must list each of this zone's records once: "
                            + (", ".join(f"0x{a:08X}" for a in sorted(stock_formations))
                               or "it has none"))
        for edit in doc["formations"]:
            f = stock_formations[edit["address"]]
            if len(edit["steps"]) != f.steps or len(edit["members"]) != f.members:
                raise ZoneError(f"{source}: formation 0x{f.address:08X} must keep {f.steps}"
                                f" steps and {f.members} members, which the code that passes"
                                " it fixes")
            struct.pack_into("<3i3I", out, f.address - BASE + 8, *edit["position"],
                             *edit["angles"])
            for m, step in enumerate(edit["steps"]):
                struct.pack_into("<4iHH", out, f.steps_at - BASE + STEP * m, *step["turn"],
                                 step["speed"], step["ticks"], step["flags"])
            for m, member in enumerate(edit["members"]):
                struct.pack_into("<3h", out, f.members_at - BASE + MEMBER * m, *member)
    return bytes(out)


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


def toml_string(value):
    """JSON's escapes are valid TOML, but TOML also forbids a raw U+007F."""
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007F")


def package(stock, built, path, lba, image, image_sha256, pkg_id, version, name):
    """manifest.toml, the overlay file's name and its bytes: the built file
    from the first byte build may change to the last, put on the disc in place
    of the stock bytes."""
    *_, formations, ranges = layout(stock)
    start, stop = ranges[0][0] - BASE, ranges[-1][1] - BASE
    payload = built[start:stop]
    folder = path.split("/")[0]
    member = f"{folder}.remix.bin"
    label = LABELS.get(folder, folder)
    edits = "an edited wave timeline" + (" and formations" if formations else "")
    about = (f"Off by default. While on, the {label} plays {edits} ({path}, bytes"
             f" 0x{start:X} to 0x{stop - 1:X}). Built for one disc image, {image.name};"
             " the game must be started from that image.")
    return "\n".join([
        f"# Built by scripts/zones/zone_data.py from {path} on the player's disc.",
        f"# {member} holds data from that disc: keep this package out of the",
        "# repository.",
        "format_version = 7",
        f"id = {toml_string(pkg_id)}",
        f"version = {toml_string(version)}",
        f"name = {toml_string(name)}",
        'author = "zone_data.py"',
        f"description = {toml_string(f'{edits[0].upper()}{edits[1:]} for the {label}.')}",
        'resolver = "declarative"',
        'save_compatibility = "shared"',
        "",
        "# The runtime hashes the disc image it mounts (the data file a cue sheet",
        "# names); the overlay applies only when that is this one.",
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
        "",
        "[[overlay]]",
        'feature = "remix"',
        'target = "disc_user"',
        f"offset = {lba * USER + start}  # sector {lba} * 2048 + 0x{start:X}",
        f"file = {toml_string(member)}",
        f"sha256 = {toml_string(hashlib.sha256(payload).hexdigest())}",
        f"expected_sha256 = {toml_string(hashlib.sha256(stock[start:stop]).hexdigest())}",
        ""]), member, payload


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
            _, address, waves, end, formations, _ = layout(blob)
        except ZoneError as exc:
            status = str(exc)
        else:
            clear = sum(1 for _, d in waves if d == WAIT)
            status = (f"table 0x{address:08X}, {len(waves)} wave{'s' * (len(waves) != 1)}"
                      f" ({clear} clear), "
                      + ("an end entry" if end is not None else "no end entry")
                      + f", {len(waves) + (end is not None)} slots")
            if formations:
                status += f", {len(formations)} formation{'s' * (len(formations) != 1)}"
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
    if not valid_id(pkg_id):
        raise ZoneError(f"--id {pkg_id}: use lowercase letters, digits, '.', '-' and '_',"
                        " at most 96 characters, not starting or ending with '.'")
    if not re.fullmatch(r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2}", args.version):
        raise ZoneError(f"--version {args.version}: use three numbers, such as 1.0.0")
    name = args.name or f"{LABELS.get(folder, folder)} Remix"
    try:
        name.encode()
    except UnicodeEncodeError:
        raise ZoneError(f"--name {name!r} is not valid UTF-8 text")
    out = output_path(args.out or OUT_DIR / f"{pkg_id}-{args.version}.psxmod")
    manifest, member, payload = package(stock, built, path, files[path][0], disc.bin,
                                        disc.image_sha256(), pkg_id, args.version, name)
    write(out, archive([("manifest.toml", manifest.encode()), (member, payload)]))
    same = " (the stock bytes)" if built == stock else ""
    print(f"wrote {out}: {pkg_id} {args.version}, {member} replaces {len(payload)} bytes"
          f" of {path}{same}; it applies only to a game started from {disc.bin}")
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
    args = parser.parse_args()
    commands = {"list": cmd_list, "dump": cmd_dump, "build": cmd_build, "check": cmd_check,
                "package": cmd_package}
    try:
        disc = Disc(args.disc)
        return commands[args.command](disc, disc.zone_files(), args)
    except ZoneError as exc:
        print(f"zone_data.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

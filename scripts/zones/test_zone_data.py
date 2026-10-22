#!/usr/bin/env python3
"""Tests for zone_data.py on synthetic zone files and a synthetic disc image.

The PlayersDisc tests also use the player's disc when disc/ holds it. The
temporary directory (TMPDIR) must be outside the repository, where the tool
may write. Run: python3 -B scripts/zones/test_zone_data.py
"""
import hashlib
import re
import struct
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zone_data  # noqa: E402

TOOL = HERE / "zone_data.py"
REPO = HERE.parents[1]
DISC = REPO / "disc" / "Omega Boost (USA).cue"
BASE = 0x80120000
JR_RA = 0x03E00008
RUNNER_NEW, FORMATION, CLEAR_ROUTINE = 0x80071624, 0x80057F0C, 0x80034104  # from the EXE
A, B, C = BASE + 0xC0, BASE + 0x100, BASE + 0x140  # the synthetic wave callbacks
TABLE = BASE + 0x40
STOCK = [(A, 150), (B, -100), (C, 60)]
# The formation record that callback A passes to 0x80057F0C at +0xD0, with 4
# steps and 5 members: eight words, then 20-byte steps, 8-byte members.
RECORD, STEPS_AT, MEMBERS_AT = BASE + 0x190, BASE + 0x1B0, BASE + 0x168
POSITION, ANGLES = (100, -200, 74240), (0, 0x80000000, 0xC0000000)
STEPS = [(0, 0, 0, 256, 30, 0), (0, 0, 11930464, 256, 30, 1), (-47721858, 0, 0, 384, 90, 2),
         (0, -11930464, 0, 768, 150, 0x8000)]
MEMBERS = [(-5120, 0, 5120, 0), (-2560, 2560, 2560, 7), (0, 0, 0, 0), (2560, 2560, 2560, 0),
           (5120, 0, 5120, 0)]  # the fourth value is padding the game does not read


def i_type(op, rs, rt, imm):
    return op << 26 | rs << 21 | rt << 16 | imm & 0xFFFF


def jal(target):
    return 0x0C000000 | (target & 0x0FFFFFFF) >> 2


def jump(target):
    return 0x08000000 | (target & 0x0FFFFFFF) >> 2


def lui(rt, imm):
    return i_type(0x0F, 0, rt, imm)


def addiu(rt, rs, imm):
    return i_type(0x09, rs, rt, imm)


LOADS = {  # code at +0x80 that passes $a1 to the constructor
    "lui and addiu": [lui(5, 0x8012), jal(RUNNER_NEW), addiu(5, 5, TABLE - BASE)],
    "lui and ori": [lui(5, 0x8012), i_type(0x0D, 5, 5, TABLE - BASE), jal(RUNNER_NEW), 0],
    "a load": [lui(5, 0x8012), addiu(5, 5, TABLE - BASE), i_type(0x23, 4, 5, 0),
               jal(RUNNER_NEW), 0],
    "a branch before the call": [lui(5, 0x8012), addiu(5, 5, TABLE - BASE),
                                 i_type(0x05, 4, 0, 2), 0, jal(RUNNER_NEW), 0],
    "the file's last word": [lui(5, 0x8012), jal(RUNNER_NEW), addiu(5, 5, 0x1FC)],
}


def zone(entries=STOCK, end=-100, after=(), calls=1, load="lui and addiu", own_clear=False):
    """A 512-byte zone file: table at +0x40, init at +0x80, callbacks A, B, C,
    and the formation record callback A passes, with its members and steps."""
    ws = [0] * 128
    ws[0] = 0x1E
    k = 16
    for callback, delay in entries:
        ws[k:k + 2] = [callback, delay & 0xFFFFFFFF]
        k += 2
    if end is not None:
        ws[k:k + 2] = [0, end & 0xFFFFFFFF]
        k += 2
    ws[k:k + len(after)] = after
    code = LOADS[load] + [JR_RA, 0]
    ws[32:32 + len(code)] = code
    if calls == 2:
        ws[38:40] = [jal(RUNNER_NEW), 0]
    if own_clear:
        ws[40:42] = [jal(CLEAR_ROUTINE), 0]
    ws[48:56] = [addiu(29, 29, -0x20), lui(5, 0x8012), addiu(5, 5, 0x190), addiu(6, 0, 4),
                 jal(FORMATION), addiu(7, 0, 5), JR_RA, addiu(29, 29, 0x20)]
    ws[64:69] = [addiu(29, 29, -0x18), jal(0x80063C5C), addiu(5, 0, 150), JR_RA,
                 addiu(29, 29, 0x18)]
    ws[80:82] = [JR_RA, 0]
    blob = bytearray(struct.pack("<128I", *ws))
    struct.pack_into("<2I3i3I", blob, RECORD - BASE, STEPS_AT, MEMBERS_AT, *POSITION, *ANGLES)
    for n, step in enumerate(STEPS):
        struct.pack_into("<4iHH", blob, STEPS_AT - BASE + 20 * n, *step)
    for n, member in enumerate(MEMBERS):
        struct.pack_into("<4h", blob, MEMBERS_AT - BASE + 8 * n, *member)
    return bytes(blob)


def entries_at(blob, count):
    return [struct.unpack_from("<Ii", blob, TABLE - BASE + 8 * n) for n in range(count)]


def dumped(blob, path="S1/S1.BIN"):
    return zone_data.parse(zone_data.render(path, blob), "test")


def record(name, lba, size, is_dir):
    raw = name if isinstance(name, bytes) else name.encode()
    rec = bytearray(33 + len(raw) + (1 - len(raw) % 2))
    rec[0] = len(rec)
    rec[2:6] = lba.to_bytes(4, "little")
    rec[10:14] = size.to_bytes(4, "little")
    rec[25] = 2 if is_dir else 0
    rec[32] = len(raw)
    rec[33:33 + len(raw)] = raw
    return bytes(rec)


def image(files):
    """A MODE2/2352 image with a root directory holding <NAME>/<NAME>.BIN files."""
    sectors, lba = {}, 19 + len(files)
    root = record(b"\x00", 18, 2048, True) + record(b"\x01", 18, 2048, True)
    for n, name in enumerate(sorted(files)):
        data = files[name]
        root += record(name, 19 + n, 2048, True)
        sectors[19 + n] = (record(b"\x00", 19 + n, 2048, True) + record(b"\x01", 18, 2048, True)
                           + record(f"{name}.BIN;1", lba, len(data), False))
        for k in range(0, len(data), 2048):
            sectors[lba + k // 2048] = data[k:k + 2048]
        lba += -(-len(data) // 2048)
    sectors[18] = root
    sectors[16] = b"\x01CD001\x01".ljust(156, b"\x00") + record(b"\x00", 18, 2048, True)
    return b"".join(bytes(24) + sectors.get(n, b"").ljust(2048, b"\x00") + bytes(280)
                    for n in range(lba))


class Tables(unittest.TestCase):
    def test_finds_the_table_the_zone_passes_to_the_runner(self):
        self.assertEqual(zone_data.read_table(zone()), (BASE + 0x84, TABLE, STOCK, -100))

    def test_a_table_without_an_end_entry_stops_at_other_data(self):
        blob = zone(end=None, after=[0x64342528, 0x00000A29])
        self.assertEqual(zone_data.read_table(blob)[2:], (STOCK, None))

    def test_a_table_that_runs_to_the_end_of_the_file_stops_there(self):
        for at in (0x1F0, 0x1EC):  # its last entry ends at the file's end, or 4 bytes before
            with self.subTest(at=hex(at)):
                blob = bytearray(zone(load="the file's last word"))
                struct.pack_into("<I", blob, 0x88, addiu(5, 5, at))  # the call's delay slot
                struct.pack_into("<4I", blob, at, A, 150, B, 60)
                self.assertEqual(zone_data.read_table(bytes(blob))[1:],
                                 (BASE + at, [(A, 150), (B, 60)], None))

    def test_traces_lui_and_ori(self):
        self.assertEqual(zone_data.read_table(zone(load="lui and ori"))[1:], (TABLE, STOCK, -100))

    def test_files_it_cannot_read(self):
        no_call = bytearray(zone())
        no_call[0x84:0x88] = bytes(4)
        with self.assertRaises(zone_data.NoTimeline):
            zone_data.read_table(bytes(no_call))
        cases = [(zone(calls=2), "2 calls"), (zone(load="a load"), "cannot trace"),
                 (zone(load="a branch before the call"), "cannot trace"),
                 (zone(load="the file's last word"), "cannot trace"),
                 (zone(entries=[]), "does not start with a wave")]
        for n, (blob, message) in enumerate(cases):
            with self.subTest(case=n, message=message):
                with self.assertRaisesRegex(zone_data.ZoneError, message):
                    zone_data.read_table(blob)

    def test_notes_list_each_callbacks_calls(self):
        blob = zone()
        self.assertEqual(zone_data.describe(blob, A), "calls 0x80057F0C(0x80120190, 4, 5)")
        self.assertEqual(zone_data.describe(blob, B), "calls 0x80063C5C")
        self.assertEqual(zone_data.describe(blob, C), "calls nothing")

    def test_the_dump_notes_a_zone_that_also_ends_through_its_own_code(self):
        self.assertIn("own code (1 call)", zone_data.render("U4/U4.BIN", zone(own_clear=True)))
        self.assertNotIn("own code", zone_data.render("U4/U4.BIN", zone()))


class RoundTrip(unittest.TestCase):
    def test_an_unedited_dump_rebuilds_the_same_bytes(self):
        for blob in (zone(), zone(end=None, after=[0x64342528])):
            self.assertEqual(zone_data.build(blob, dumped(blob), "test"), blob)

    def test_edits_in_the_text_land_in_the_table(self):
        blob = zone()
        text = zone_data.render("S1/S1.BIN", blob)
        edited = (text.replace("delay = 150 }", "delay = 300 }")
                  .replace('delay = "clear" }', "delay = 0 }").replace("end = -100", "end = 7"))
        built = zone_data.build(blob, zone_data.parse(edited, "test"), "test")
        self.assertEqual(entries_at(built, 4), [(A, 300), (B, 0), (C, 60), (0, 7)])
        self.assertEqual(built[:TABLE - BASE], blob[:TABLE - BASE])
        self.assertEqual(built[TABLE - BASE + 32:], blob[TABLE - BASE + 32:])

    def test_reordered_and_repeated_waves(self):
        blob = zone()
        doc = dumped(blob)
        doc["timeline"]["waves"] = [{"callback": C, "delay": 10}, {"callback": C, "delay": "clear"},
                                    {"callback": A, "delay": 20}]
        built = zone_data.build(blob, doc, "test")
        self.assertEqual(entries_at(built, 4), [(C, 10), (C, -100), (A, 20), (0, -100)])

    def test_slots_left_over_become_zero_words(self):
        blob = zone()
        doc = dumped(blob)
        doc["timeline"]["waves"] = [{"callback": B, "delay": 5}]
        built = zone_data.build(blob, doc, "test")
        self.assertEqual(entries_at(built, 4), [(B, 5), (0, -100), (0, 0), (0, 0)])
        self.assertEqual(zone_data.read_table(built)[2:], ([(B, 5)], -100))

    def test_a_table_without_an_end_entry_can_take_one_in_place_of_a_wave(self):
        blob = zone(end=None, after=[0x64342528])
        doc = dumped(blob)
        self.assertIs(doc["timeline"]["end"], False)
        doc["timeline"]["waves"].pop()
        doc["timeline"]["end"] = -100
        built = zone_data.build(blob, doc, "test")
        self.assertEqual(entries_at(built, 3), [(A, 150), (B, -100), (0, -100)])


class Refusals(unittest.TestCase):
    def refuse(self, blob, doc, message):
        with self.assertRaisesRegex(zone_data.ZoneError, message):
            zone_data.build(blob, doc, "test")

    def test_another_stock_file(self):
        doc = dumped(zone())
        self.refuse(zone(entries=[(A, 151), (B, -100), (C, 60)]), doc, "not the file")

    def test_edits_the_table_cannot_take(self):
        blob = zone()
        cases = [
            ("not one of this table's callbacks", [{"callback": A + 4, "delay": 1}]),
            ("not one of this table's callbacks", [{"callback": 0, "delay": 1}]),
            ("4 slots", [{"callback": A, "delay": 1}] * 4),
            ("needs a wave first", []),
        ]
        for n, (message, waves) in enumerate(cases):
            with self.subTest(case=n, message=message):
                doc = dumped(blob)
                doc["timeline"]["waves"] = waves
                self.refuse(blob, doc, message)
        doc = dumped(blob)
        doc["timeline"]["address"] += 8
        self.refuse(blob, doc, "must stay")
        doc = dumped(blob)
        doc["timeline"]["end"] = False
        self.refuse(blob, doc, "end = false")

    def test_end_false_cannot_replace_a_stock_end_entry(self):
        blob = zone()  # three waves and an end entry: four slots
        doc = dumped(blob)
        doc["timeline"]["waves"] = [{"callback": A, "delay": 1}] * 4
        doc["timeline"]["end"] = False
        self.refuse(blob, doc, "end = false")

    def test_end_false_needs_every_slot(self):
        blob = zone(end=None, after=[0x64342528])
        doc = dumped(blob)
        doc["timeline"]["waves"].pop()
        self.refuse(blob, doc, "end = false")

    def test_text_the_parser_rejects(self):
        text = zone_data.render("S1/S1.BIN", zone())
        cases = [
            ("format must be 1 or 2", text.replace("format = 2", "format = 3")),
            ("format must be 1 or 2", text.replace("format = 2", "format = true")),
            ("unknown formations", text.replace("format = 2", "format = 1")),
            ("unknown dealy", text.replace("delay = 150", "dealy = 150")),
            ("unknown speed", text.replace("delay = 150 }", "delay = 150, speed = 2 }")),
            ("missing slots", text.replace("slots = ", "# slots = ")),
            ("tick count", text.replace("delay = 150", "delay = -1")),
            ("callback must be an address", text.replace("callback = 0x801200C0", "callback = true")),
            ("32-bit integer or false", text.replace("end = -100", "end = true")),
            ("32-bit integer or false", text.replace("end = -100", "end = 2147483648")),
            ("zone file", text.replace('file = "S1/S1.BIN"', 'file = "S1/S2.BIN"')),
            ("line 1", "format = = 1\n" + text),
        ]
        for n, (message, edited) in enumerate(cases):
            with self.subTest(case=n, message=message):
                self.assertNotEqual(edited, text)
                with self.assertRaisesRegex(zone_data.ZoneError, message):
                    zone_data.parse(edited, "test")


def comments(text):
    """A dump's comment lines joined, so wrapped sentences read as one."""
    return " ".join(line[2:] for line in text.splitlines() if line.startswith("# "))


def patched(*writes):
    """zone() with (offset, word) pairs written over it."""
    blob = bytearray(zone())
    for offset, word in writes:
        struct.pack_into("<I", blob, offset, word)
    return bytes(blob)


class Formations(unittest.TestCase):
    def test_finds_the_record_a_callback_passes(self):
        self.assertEqual(zone_data.read_formations(zone()),
                         [zone_data.Formation(RECORD, STEPS_AT, 4, MEMBERS_AT, 5, [BASE + 0xD0])])

    def test_one_record_passed_by_two_calls(self):
        second = [lui(5, 0x8012), addiu(5, 5, 0x190), addiu(6, 0, 4), jal(FORMATION), addiu(7, 0, 5)]
        blob = patched(*((0x150 + 4 * n, w) for n, w in enumerate(second)))
        [f] = zone_data.read_formations(blob)
        self.assertEqual(f.calls, [BASE + 0xD0, BASE + 0x15C])
        second[2] = addiu(6, 0, 3)
        blob = patched(*((0x150 + 4 * n, w) for n, w in enumerate(second)))
        with self.assertRaisesRegex(zone_data.ZoneError, "passed with 4 steps and 5 members, and"
                                    " at 0x8012015C with 3 and 5"):
            zone_data.read_formations(blob)

    def test_the_dump_shows_the_record(self):
        text = zone_data.render("S1/S1.BIN", zone())
        [f] = zone_data.parse(text, "test")["formations"]
        self.assertEqual(f, {"address": RECORD, "position": list(POSITION), "angles": list(ANGLES),
                             "steps": [{"turn": list(s[:3]), "speed": s[3], "ticks": s[4],
                                        "flags": s[5]} for s in STEPS],
                             "members": [list(m[:3]) for m in MEMBERS]})
        notes = comments(text)
        self.assertIn("Started at 0x801200D0 by wave 0 (callback 0x801200C0), with 4 steps and 5"
                      " members. Its steps are at 0x801201B0, its members at 0x80120168.", notes)
        self.assertIn("angles = [0x00000000, 0x80000000, 0xC0000000]  # degrees: 0, 180, 270", text)
        self.assertIn("# roll 1 (degrees a tick)", text)
        self.assertIn("# pitch -4 (degrees a tick)", text)

    def test_edits_land_in_place(self):
        blob = zone()
        doc = dumped(blob)
        f = doc["formations"][0]
        f["position"] = [-1, 2**31 - 1, -2**31]
        f["angles"] = [0xFFFFFFFF, 0, 0x40000000]
        f["steps"][3] = {"turn": [1, -2, 3], "speed": -5, "ticks": 65535, "flags": 0x4001}
        f["members"][1] = [32767, -32768, 1]
        expected = bytearray(blob)
        # Position at +8 and angles at +0x14 of the record; step 3 at 60 bytes in;
        # member 1 at 8 bytes in, its padding (7) untouched.
        expected[0x198:0x1B0] = bytes.fromhex("ffffffff ffffff7f 00000080 ffffffff 00000000"
                                              " 00000040")
        expected[0x1EC:0x200] = bytes.fromhex("01000000 feffffff 03000000 fbffffff ffff 0140")
        expected[0x170:0x176] = bytes.fromhex("ff7f 0080 0100")
        self.assertEqual(zone_data.build(blob, doc, "test"), bytes(expected))
        self.assertEqual(expected[0x176:0x178], b"\x07\x00")

    def test_an_unedited_formation_rebuilds_the_same_bytes(self):
        blob = zone()
        self.assertEqual(zone_data.build(blob, dumped(blob), "test"), blob)

    def test_a_dump_of_format_1_keeps_the_stock_formations(self):
        blob = zone()
        text = zone_data.render("S1/S1.BIN", blob)
        old = text[:text.index("\n# Formations.")].replace("format = 2", "format = 1") + "\n"
        doc = zone_data.parse(old.replace("delay = 150 }", "delay = 7 }"), "test")
        built = zone_data.build(blob, doc, "test")
        self.assertEqual(entries_at(built, 1), [(A, 7)])
        self.assertEqual(built[0x60:], blob[0x60:])

    def test_edits_build_refuses(self):
        blob = zone()
        cases = [
            ("must keep 4 steps and 5 members", lambda f: f["steps"].pop()),
            ("must keep 4 steps and 5 members", lambda f: f["steps"].append(f["steps"][0])),
            ("must keep 4 steps and 5 members", lambda f: f["members"].append([0, 0, 0])),
            ("each of this zone's records once: 0x80120190", lambda f: f.update(address=RECORD + 4)),
        ]
        for n, (message, change) in enumerate(cases):
            with self.subTest(case=n, message=message):
                doc = dumped(blob)
                change(doc["formations"][0])
                with self.assertRaisesRegex(zone_data.ZoneError, message):
                    zone_data.build(blob, doc, "test")
        for formations in ([], [dumped(blob)["formations"][0]] * 2):
            with self.subTest(formations=len(formations)):
                doc = dumped(blob)
                doc["formations"] = formations
                with self.assertRaisesRegex(zone_data.ZoneError, "records once"):
                    zone_data.build(blob, doc, "test")

    def test_values_the_parser_rejects(self):
        text = zone_data.render("S1/S1.BIN", zone())
        cases = [
            ("position must be three 32-bit", "74240]", "2147483648]"),
            ("position must be three 32-bit", "position = [100, -200, 74240]", "position = [1, 2]"),
            ("angles must be three integers from 0 to 0xFFFFFFFF", "[0x00000000,", "[-1,"),
            ("angles must be three integers", "0xC0000000]", "0x100000000]"),
            ("step 0: turn must be three 32-bit integers", "[0, 0, 0], speed = 256",
             "[0, 0], speed = 256"),
            ("step 0: turn must be three 32-bit integers", "[0, 0, 0], speed = 256",
             "[0, 0, 2147483648], speed = 256"),
            ("step 3: turn must be three 32-bit integers, and speed one", "speed = 768",
             "speed = 7.5"),
            ("step 3: turn must be three 32-bit integers, and speed one", "speed = 768",
             "speed = -2147483649"),
            ("step 3: ticks and flags must be from 0 to 65535", "ticks = 150", "ticks = 65536"),
            ("step 3: ticks and flags", "flags = 0x8000", "flags = -1"),
            ("step 3: unknown pace", "speed = 768,", "speed = 768, pace = 1,"),
            ("member 1: must be three integers from -32768 to 32767", "[-2560, 2560, 2560]",
             "[-2560, 2560, 32768]"),
            ("member 0: must be three integers", "[-5120, 0, 5120]", "[-5120, 0]"),
            ("address must be an integer", "address = 0x80120190", 'address = "0x80120190"'),
            ("missing members", "\nmembers = [", "\nmembers_ = ["),
        ]
        for n, (message, old, new) in enumerate(cases):
            with self.subTest(case=n, message=message):
                self.assertEqual(text.count(old), 1)
                with self.assertRaisesRegex(zone_data.ZoneError, message):
                    zone_data.parse(text.replace(old, new), "test")
        base = text[:text.index("\n# Formations.")]
        with self.assertRaisesRegex(zone_data.ZoneError, "formations must be a list"):
            zone_data.parse(base.replace("\n[timeline]", "\nformations = 3\n[timeline]"), "test")

    def test_formations_it_cannot_read(self):
        cases = [
            ("cannot trace the formation record and counts passed at 0x801200D0",
             [(0xC8, i_type(0x23, 4, 5, 0))]),  # lw $a1, 0($a0)
            ("the call at 0x801200D0 starts a formation with 4 steps and 0 members",
             [(0xD4, addiu(7, 0, 0))]),
            ("the formation record 0x801201F0 passed at 0x801200D0 is not in the file",
             [(0xC8, addiu(5, 5, 0x1F0))]),
            ("the steps of the formation record 0x80120190, at 0x801201F0, are not in the file",
             [(0x190, BASE + 0x1F0)]),
            ("the members of the formation record 0x80120190, at 0x8012016A, are not in the file",
             [(0x194, MEMBERS_AT + 2)]),
            ("the formation record 0x80120192 passed at 0x801200D0 is not in the file",
             [(0xC8, addiu(5, 5, 0x192))]),
            ("the call at 0x801200D0 starts a formation with 0 steps and 5 members",
             [(0xCC, addiu(6, 0, 0))]),
            ("the call at 0x801200D0 starts a formation with 4 steps and -1 members",
             [(0xD4, addiu(7, 0, -1))]),
            ("the call at 0x801200D0 starts a formation with 32768 steps and 5 members",
             [(0xCC, i_type(0x0D, 0, 6, 0x8000))]),  # ori $a2, $zero, 0x8000
            # Four 20-byte steps from 0x1C0 end at 0x210, past the file's end.
            ("the steps of the formation record 0x80120190, at 0x801201C0, are not in the file",
             [(0x190, BASE + 0x1C0)]),
        ]
        for n, (message, writes) in enumerate(cases):
            with self.subTest(case=n, message=message):
                with self.assertRaisesRegex(zone_data.ZoneError, re.escape(message)):
                    zone_data.read_formations(patched(*writes))

    def test_the_dump_says_when_a_call_runs(self):
        word = [lui(2, 0x800A), i_type(0x23, 2, 2, 0x7C34)]  # lw $v0, 0x7C34($v0)
        call = [lui(5, 0x8012), addiu(5, 5, 0x190), addiu(6, 0, 4), jal(FORMATION),
                addiu(7, 0, 5)]
        sp, ret = addiu(29, 29, -0x20), [JR_RA, addiu(29, 29, 0x20)]

        def past(op, rt=0, load=word):  # the branch at 0xCC can jump past the call at 0xE0
            return load + [sp, i_type(op, 2, rt, 6), 0] + call + ret

        def to(op):  # the branch at 0xCC jumps to the call at 0xE8, and a j jumps past it
            return word + [sp, i_type(op, 2, 0, 3), 0, jump(BASE + 0xF0), 0] + call + ret

        zero = "only while the difficulty word (0x800A7C34) is zero"
        nonzero = "only while the difficulty word (0x800A7C34) is non-zero"
        some = "only on some paths through its callback"
        cases = [  # (the call's offset, when it runs, callback A's code at 0xC0)
            (0xE0, nonzero, past(0x04)),  # beqz
            (0xE0, zero, past(0x05)),  # bnez
            (0xE8, zero, to(0x04)),
            (0xE8, nonzero, to(0x05)),
            (0xE0, some, past(0x04, load=[lui(2, 0x800A), i_type(0x23, 4, 2, 0x10)])),
            (0xE0, some, past(0x05, rt=3)),  # bne $v0, $v1
            (0xE0, some, past(0x01)),  # bltz
            (0xE0, some, past(0x06)),  # blez
            # beqz over an early return; beqz on what a call returns in $v0; beqz on
            # the word or bnez on $a0 to the call; a branch to the call.
            (0xE8, zero, word + [sp, i_type(0x04, 2, 0, 3), 0] + ret + call + ret),
            (0xE8, some, word + [sp, jal(0x80063C5C), 0, i_type(0x04, 2, 0, 6), 0] + call + ret),
            (0xF0, some, word + [sp, i_type(0x04, 2, 0, 5), 0, i_type(0x05, 4, 0, 3), 0,
                                 jump(BASE + 0xF8), 0] + call + ret),
            (0xD8, None, [sp, i_type(0x05, 4, 0, 1), 0] + call + ret),
            # The word decides only together with $a0, either way; $v0 holds the word on
            # one path into a join and 5 on the other; the lw's base differs on two
            # paths into its block; beqz on the word to a tail jump out of the file; a
            # bgezal, which is a call, before the call.
            (0xE8, some, word + [sp, i_type(0x05, 2, 0, 8), 0, i_type(0x04, 4, 0, 6), 0]
             + call + ret),
            (0xE8, some, word + [sp, i_type(0x04, 2, 0, 8), 0, i_type(0x04, 4, 0, 6), 0]
             + call + ret),
            (0xEC, some, [sp, addiu(2, 0, 5), i_type(0x04, 4, 0, 3), 0] + word
             + [i_type(0x05, 2, 0, 6), 0] + call + ret),
            (0xEC, some, [sp, lui(2, 0x1234), i_type(0x04, 4, 0, 2), 0, lui(2, 0x800A),
                          i_type(0x23, 2, 2, 0x7C34), i_type(0x05, 2, 0, 6), 0] + call + ret),
            (0xE0, nonzero, word + [sp, i_type(0x04, 2, 0, 8), 0] + call + ret
             + [jump(0x80040000), addiu(29, 29, 0x20)]),
            (0xD8, None, [sp, i_type(0x01, 4, 0x11, 8), 0] + call + ret + ret),
            (0xE0, some, word + [sp, i_type(0x07, 4, 0, 6), 0] + call + ret),  # bgtz $a0
        ]
        for n, (at, when, code) in enumerate(cases):
            with self.subTest(case=n, when=when):
                self.assertLessEqual(len(code), 16)  # callback B starts at 0x100
                blob = patched(*((0xC0 + 4 * i, w) for i, w in enumerate(code)))
                self.assertIn(f"Started at 0x{BASE + at:08X} by wave 0 (callback 0x801200C0), "
                              + (f"{when}, " if when else "") + "with 4 steps",
                              comments(zone_data.render("S1/S1.BIN", blob)))

    def test_parts_that_overlap(self):
        cases = [("the members of 0x80120190 and formation record 0x80120190 overlap",
                  [(0x194, RECORD - 8)]),
                 ("the table and the members of 0x80120190 overlap", [(0x194, TABLE + 0x18)])]
        for n, (message, writes) in enumerate(cases):
            with self.subTest(case=n, message=message):
                with self.assertRaisesRegex(zone_data.ZoneError, message):
                    zone_data.layout(patched(*writes))


RECIPE = """\
format = 1
id = "test.remix"
version = "1.2.3"
name = "Test Remix"
description = "Edits of two synthetic zones."

[[zones]]
zone = "s1"
waves = [{ wave = 2, delay = 10 }, { wave = 0, delay = "stock" }, { wave = 1, delay = "stock" }]

[[zones.formations]]
address = 0x80120190
spread = 2
pace = 1.5
yaw = 90
move = [1, 2, 3]

[[zones]]
zone = "U4"
waves = [{ wave = 0, delay = 5 }]
"""


class Remix(unittest.TestCase):
    def remixed(self, text=RECIPE):
        """The synthetic S1 with the recipe's first zone's edits."""
        recipe = zone_data.parse_recipe(text, "test")
        blob = zone()
        doc = dumped(blob)
        zone_data.remix_zone(doc, recipe["zones"][0], "test")
        return zone_data.build(blob, doc, "test")

    def test_a_recipe_edits_the_timeline_and_a_formation(self):
        built = self.remixed()
        # Stock waves 2, 0 and 1: C with a new delay, then A and B with their own.
        self.assertEqual(entries_at(built, 4), [(C, 10), (A, 150), (B, -100), (0, -100)])
        # yaw 90 turns (100, -200, 74240) to (74240, -200, -100) and adds
        # 0x40000000 to the yaw angle; move then adds (1, 2, 3).
        self.assertEqual(struct.unpack_from("<3i3I", built, RECORD - BASE + 8),
                         (74241, -198, -97, 0, 0xC0000000, 0xC0000000))
        # pace 1.5 multiplies speeds and turns by 1.5 and divides durations by it:
        # the first step lasts its ticks (30 -> 20), a later one ticks + 1 (31,
        # 91 and 151 -> 21, 61 and 101, so ticks 20, 60 and 100).
        self.assertEqual([struct.unpack_from("<4iHH", built, STEPS_AT - BASE + 20 * n)
                          for n in range(4)],
                         [(0, 0, 0, 384, 20, 0), (0, 0, 17895696, 384, 20, 1),
                          (-71582787, 0, 0, 576, 60, 2), (0, -17895696, 0, 1152, 100, 0x8000)])
        # spread 2 doubles each member's offset and leaves the padding (7) alone.
        self.assertEqual([struct.unpack_from("<4h", built, MEMBERS_AT - BASE + 8 * n)
                          for n in range(5)],
                         [(-10240, 0, 10240, 0), (-5120, 5120, 5120, 7), (0, 0, 0, 0),
                          (5120, 5120, 5120, 0), (10240, 0, 10240, 0)])
        changed = {n for n, (a, b) in enumerate(zip(zone(), built)) if a != b}
        # The table, the members, and the record's position, angles and steps.
        self.assertLessEqual(changed, set(range(0x40, 0x60)) | set(range(0x168, 0x190))
                             | set(range(0x198, 0x200)))

    def test_a_slower_pace(self):
        # pace 0.5 halves speeds and turns and doubles durations: the first step
        # lasts its ticks (30 -> 60), a later one ticks + 1 (31, 91 and 151 ->
        # 62, 182 and 302, so ticks 61, 181 and 301).
        built = self.remixed(RECIPE.replace("spread = 2\n", "").replace("pace = 1.5", "pace = 0.5"))
        self.assertEqual([struct.unpack_from("<4iHH", built, STEPS_AT - BASE + 20 * n)
                          for n in range(4)],
                         [(0, 0, 0, 128, 60, 0), (0, 0, 5965232, 128, 61, 1),
                          (-23860929, 0, 0, 192, 181, 2), (0, -5965232, 0, 384, 301, 0x8000)])
        self.assertEqual(built[MEMBERS_AT - BASE:RECORD - BASE],
                         zone()[MEMBERS_AT - BASE:RECORD - BASE])  # no spread

    def test_a_fast_pace_keeps_a_later_step_one_tick_long(self):
        # Step 0 lasts its 4 ticks: 4 / 3 -> 1. Step 1 lasts ticks + 1 = 1 tick:
        # 1 / 3 rounds to 0, but a later step lasts at least one tick, ticks 0.
        f = {"position": [0, 0, 0], "angles": [0, 0, 0], "members": [[0, 0, 0]],
             "steps": [{"turn": [0, 0, 0], "speed": 2, "ticks": 4, "flags": 0},
                       {"turn": [0, 0, 0], "speed": 2, "ticks": 0, "flags": 0}]}
        zone_data.reshape(f, {"pace": 3}, "test")
        self.assertEqual([(s["speed"], s["ticks"]) for s in f["steps"]], [(6, 1), (6, 0)])

    def test_a_wave_can_wait_for_a_clear(self):
        built = self.remixed(RECIPE.replace("{ wave = 2, delay = 10 }",
                                            '{ wave = 2, delay = "clear" }'))
        self.assertEqual(entries_at(built, 4), [(C, -100), (A, 150), (B, -100), (0, -100)])

    def test_spread_rounds_to_the_nearest_unit(self):
        # 5120 * 1.0001 = 5120.512 -> 5121 (and -5121); 2560 * 1.0001 = 2560.256 -> 2560.
        built = self.remixed(RECIPE.replace("spread = 2", "spread = 1.0001"))
        self.assertEqual([struct.unpack_from("<4h", built, MEMBERS_AT - BASE + 8 * n)
                          for n in range(5)],
                         [(-5121, 0, 5121, 0), (-2560, 2560, 2560, 7), (0, 0, 0, 0),
                          (2560, 2560, 2560, 0), (5121, 0, 5121, 0)])

    def test_yaw_turns_about_the_player(self):
        cases = [(180, (-100, -200, -74240), 0), (270, (-74240, -200, 100), 0x40000000),
                 (-90, (-74240, -200, 100), 0x40000000), (360, (100, -200, 74240), 0x80000000)]
        for yaw, position, angle in cases:
            with self.subTest(yaw=yaw):
                text = (RECIPE.replace("spread = 2\npace = 1.5\n", "")
                        .replace("yaw = 90", f"yaw = {yaw}").replace("[1, 2, 3]", "[0, 0, 0]"))
                built = self.remixed(text)
                self.assertEqual(struct.unpack_from("<3i3I", built, RECORD - BASE + 8),
                                 (*position, 0, angle, 0xC0000000))
                self.assertEqual(built[STEPS_AT - BASE:], zone()[STEPS_AT - BASE:])

    def test_recipes_the_parser_rejects(self):
        cases = [
            ("format must be 1", "format = 1", "format = 2"),
            ("missing description", 'description = "Edits of two synthetic zones."\n', ""),
            ("unknown colour", "format = 1\n", 'format = 1\ncolour = "red"\n'),
            ("id Test.Remix: use lowercase", 'id = "test.remix"', 'id = "Test.Remix"'),
            ("version 1.2: use three numbers", 'version = "1.2.3"', 'version = "1.2"'),
            ("name must be a string", 'name = "Test Remix"', "name = 3"),
            ("name must not be empty", 'name = "Test Remix"', 'name = ""'),
            ("zone must name a zone's folder", 'zone = "s1"', 'zone = "S 1"'),
            ("zone S1 is listed twice", 'zone = "U4"', 'zone = "S1"'),
            ("waves must be a list", "waves = [{ wave = 0, delay = 5 }]", "waves = 5"),
            ("wave must be a stock wave's number", "{ wave = 2, delay = 10 }",
             "{ wave = -1, delay = 10 }"),
            ("delay must be a tick count", "{ wave = 2, delay = 10 }", "{ wave = 2, delay = -1 }"),
            ("delay must be a tick count", "{ wave = 2, delay = 10 }",
             '{ wave = 2, delay = "soon" }'),
            ("unknown when", "{ wave = 2, delay = 10 }", "{ wave = 2, delay = 10, when = 1 }"),
            ("address must be an address", "address = 0x80120190", 'address = "0x80120190"'),
            ("formation 0x80120190 is listed twice", "move = [1, 2, 3]\n",
             "move = [1, 2, 3]\n\n[[zones.formations]]\naddress = 0x80120190\nyaw = 1\n"),
            ("spread must be a number above 0", "spread = 2", "spread = true"),
            ("spread must be a number above 0", "spread = 2", "spread = nan"),
            ("spread must be a number above 0", "spread = 2", "spread = 0"),
            ("spread must be a number above 0", "spread = 2", "spread = -2"),
            # 2**1024 is the first integer beyond float range.
            ("spread must be a number above 0", "spread = 2", f"spread = {2**1024}"),
            ("pace must be a number above 0", "pace = 1.5", "pace = 0"),
            ("pace must be a number above 0", "pace = 1.5", "pace = -1.5"),
            ("pace must be a number above 0", "pace = 1.5", f"pace = {2**1024}"),
            ("yaw must be a number of degrees", "yaw = 90", 'yaw = "90"'),
            ("yaw must be a number of degrees", "yaw = 90", "yaw = inf"),
            ("yaw must be a number of degrees", "yaw = 90", f"yaw = {-2**1024}"),
            ("move must be three 32-bit integers", "move = [1, 2, 3]", "move = [1, 2]"),
            ("unknown scale", "spread = 2", "scale = 2"),
            ("line 1", "format = 1", "format = = 1"),
        ]
        for n, (message, old, new) in enumerate(cases):
            with self.subTest(case=n, message=message):
                self.assertEqual(RECIPE.count(old), 1)
                with self.assertRaisesRegex(zone_data.ZoneError, re.escape(message)):
                    zone_data.parse_recipe(RECIPE.replace(old, new), "test")
        with self.assertRaisesRegex(zone_data.ZoneError, "at least one zone"):
            zone_data.parse_recipe(RECIPE[:RECIPE.index("[[zones]]")] + "zones = []\n", "test")

    def test_edits_the_zone_cannot_take(self):
        stock = '{ wave = 1, delay = "stock" }]'
        cases = [
            ("the stock table has waves 0 to 2", "{ wave = 2, delay = 10 }",
             "{ wave = 3, delay = 10 }"),
            ("no formation record 0x80120194; this zone's records: 0x80120190",
             "address = 0x80120190", "address = 0x80120194"),
            ("spread 7 gives member 0 the offset [-35840, 0, 35840], beyond -32768 to 32767",
             "spread = 2", "spread = 7"),
            ("pace 1e-06 gives step 0 a turn, speed or tick count beyond its field",
             "pace = 1.5", "pace = 1e-6"),
            ("the edits give values beyond the record's fields", "pace = 1.5", "pace = 1e308"),
            # Step 0 lasts 30 ticks; 30 / 61 rounds to 0.
            ("pace 61 leaves step 0 no ticks", "pace = 1.5", "pace = 61"),
            ("beyond 32-bit integers", "move = [1, 2, 3]", "move = [2147483647, 0, 0]"),
            ("5 entries with the end entry; this table has 4 slots", stock,
             '{ wave = 1, delay = "stock" }, { wave = 0, delay = 1 }]'),
            ("needs a wave first", f"waves = [{{ wave = 2, delay = 10 }}, {{ wave = 0, delay ="
             f' "stock" }}, {stock}', "waves = []"),
        ]
        for n, (message, old, new) in enumerate(cases):
            with self.subTest(case=n, message=message):
                self.assertEqual(RECIPE.count(old), 1)
                with self.assertRaisesRegex(zone_data.ZoneError, re.escape(message)):
                    self.remixed(RECIPE.replace(old, new))

    def test_the_committed_recipes_parse(self):
        recipes = sorted((HERE / "remixes").glob("*.toml"))
        self.assertTrue(recipes)
        for path in recipes:
            with self.subTest(recipe=path.name):
                recipe = zone_data.parse_recipe(path.read_text(), path)
                self.assertTrue(recipe["id"].startswith("omega.remix."))


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.files = {"S1": zone(), "TITLE": bytes(600), "U4": zone(own_clear=True)}
        (self.dir / "t.bin").write_bytes(image(self.files))
        self.cue = self.dir / "t.cue"
        self.cue.write_text('FILE "t.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')

    def run_tool(self, *args, cue=None):
        return subprocess.run([sys.executable, "-B", str(TOOL), "--disc", str(cue or self.cue),
                               *map(str, args)], capture_output=True, text=True, cwd=self.dir)

    def test_list_and_check(self):
        listing = self.run_tool("list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("S1/S1.BIN", listing.stdout)
        self.assertIn("table 0x80120040, 3 waves (1 clear), an end entry, 4 slots, 1 formation\n",
                      listing.stdout)
        self.assertIn("TITLE/TITLE.BIN", listing.stdout)
        self.assertIn("no shared wave timeline", listing.stdout)
        check = self.run_tool("check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("zone files with a timeline: 2, rebuilt identical: 2", check.stdout)

    def test_check_fails_on_a_table_it_cannot_trace(self):
        (self.dir / "t.bin").write_bytes(image({"S1": zone(load="a load")}))
        check = self.run_tool("check")
        self.assertEqual(check.returncode, 1)
        self.assertIn("S1/S1.BIN: cannot trace", check.stdout)

    def test_dump_edit_build(self):
        dump = self.dir / "S1.zone.toml"
        result = self.run_tool("dump", "s1", "--out", dump)
        self.assertEqual(result.returncode, 0, result.stderr)
        dump.write_text(dump.read_text().replace("delay = 60 }", "delay = 90 }"))
        out = self.dir / "S1.BIN"
        result = self.run_tool("build", dump, "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        built = out.read_bytes()
        self.assertEqual(entries_at(built, 4), [(A, 150), (B, -100), (C, 90), (0, -100)])
        self.assertIn(f"sha256 {hashlib.sha256(built).hexdigest()}", result.stdout)
        stdout = self.run_tool("dump", "S1", "--out", "-")
        self.assertEqual(stdout.stdout, zone_data.render("S1/S1.BIN", self.files["S1"]))

    def test_outputs_stay_out_of_the_repository(self):
        inside = REPO / "scripts" / "zones" / "refused.zone.toml"
        result = self.run_tool("dump", "S1", "--out", inside)
        self.assertEqual(result.returncode, 1)
        self.assertIn("under .cache/ or outside the repository", result.stderr)
        self.assertFalse(inside.exists())
        dump = self.dir / "S1.zone.toml"
        self.assertEqual(self.run_tool("dump", "S1", "--out", dump).returncode, 0)
        result = self.run_tool("build", dump, "--out", REPO / "refused.BIN")
        self.assertEqual(result.returncode, 1)
        self.assertIn("under .cache/ or outside the repository", result.stderr)
        self.assertFalse((REPO / "refused.BIN").exists())

    def test_outputs_may_go_under_dot_cache(self):
        path = REPO / ".cache" / "zones" / "S1.zone.toml"
        self.assertEqual(zone_data.output_path(path), path.resolve())

    def test_an_output_that_cannot_be_written(self):
        result = self.run_tool("dump", "S1", "--out", self.dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot write", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_disc_without_an_iso_volume(self):
        data = bytearray((self.dir / "t.bin").read_bytes())
        data[16 * 2352 + 24:16 * 2352 + 30] = bytes(6)  # the primary volume descriptor's id
        (self.dir / "t.bin").write_bytes(bytes(data))
        result = self.run_tool("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no ISO 9660 volume", result.stderr)

    def package(self, *args, edit=("delay = 60 }", "delay = 90 }"), more=()):
        dump = self.dir / "S1.zone.toml"
        self.assertEqual(self.run_tool("dump", "S1", "--out", dump).returncode, 0)
        text = dump.read_text()
        for old, new in (edit, *more):
            self.assertIn(old, text)
            text = text.replace(old, new)
        dump.write_text(text)
        out = self.dir / "s1.psxmod"
        return self.run_tool("package", dump, "--out", out, *args), dump, out

    def overlay_of(self, out):
        with zipfile.ZipFile(out) as z:
            [overlay] = tomllib.loads(z.read("manifest.toml").decode())["overlay"]
            return overlay, z.read(overlay["file"])

    def read_back(self, overlay, payload):
        """S1 read from the synthetic disc with the overlay applied: the runtime
        copies the payload over the user data at the offset."""
        image = (self.dir / "t.bin").read_bytes()
        patched = bytearray(image)
        for n, byte in enumerate(payload):
            lba, pos = divmod(overlay["offset"] + n, 2048)
            patched[lba * 2352 + 24 + pos] = byte
        (self.dir / "t.bin").write_bytes(bytes(patched))
        try:
            disc = zone_data.Disc(self.cue)
            return zone_data.zone_blob(disc, disc.zone_files(), "S1/S1.BIN")
        finally:
            (self.dir / "t.bin").write_bytes(image)

    def built(self, dump):
        out = self.dir / "S1.BIN"
        self.assertEqual(self.run_tool("build", dump, "--out", out).returncode, 0)
        return out.read_bytes()

    def test_package_puts_the_built_bytes_on_the_disc(self):
        result, dump, out = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(out) as z:
            self.assertEqual([(i.filename, i.compress_type, i.date_time) for i in z.infolist()],
                             [("manifest.toml", 0, (1980, 1, 1, 0, 0, 0)),
                              ("S1.remix.bin", 0, (1980, 1, 1, 0, 0, 0))])
            manifest = tomllib.loads(z.read("manifest.toml").decode())
        image = (self.dir / "t.bin").read_bytes()
        self.assertEqual((manifest["format_version"], manifest["id"], manifest["version"],
                          manifest["name"]), (7, "omega.remix.s1", "1.0.0", "1ST ZONE Remix"))
        self.assertEqual(manifest["target"], [{"game_id": "SCUS-94449",
                                               "disc_sha256": hashlib.sha256(image).hexdigest()}])
        [feature] = manifest["feature"]
        self.assertEqual((feature["id"], feature["group"], feature["default_enabled"]),
                         ("remix", "Remix", False))
        overlay, payload = self.overlay_of(out)
        self.assertEqual((overlay["feature"], overlay["target"], overlay["file"]),
                         ("remix", "disc_user", "S1.remix.bin"))
        self.assertEqual(overlay["sha256"], hashlib.sha256(payload).hexdigest())
        # From the table at 0x40 to the end of the formation's steps at 0x200.
        lba = 19 + len(self.files)  # image() puts the first file, S1, after the directories
        self.assertEqual((overlay["offset"], len(payload)), (lba * 2048 + 0x40, 0x1C0))
        self.assertEqual(overlay["expected_sha256"],
                         hashlib.sha256(self.files["S1"][0x40:0x200]).hexdigest())
        built = self.built(dump)
        self.assertEqual(self.read_back(overlay, payload), built)
        self.assertEqual(entries_at(built, 4), [(A, 150), (B, -100), (C, 90), (0, -100)])

    def test_package_of_a_shorter_table_covers_every_stock_slot(self):
        result, dump, out = self.package(edit=(f"{{ callback = 0x{C:08X}, delay = 60 }},", ""))
        self.assertEqual(result.returncode, 0, result.stderr)
        overlay, payload = self.overlay_of(out)
        # No stock entry may stay on the disc after the new end entry.
        self.assertEqual(struct.unpack_from("<IiIiIiIi", payload), (A, 150, B, -100, 0, -100, 0, 0))
        self.assertEqual(overlay["expected_sha256"],
                         hashlib.sha256(self.files["S1"][0x40:0x200]).hexdigest())
        self.assertEqual(self.read_back(overlay, payload), self.built(dump))

    def test_package_of_edits_across_sectors(self):
        blob = bytearray(zone()) + bytes(6144 - 512)
        struct.pack_into("<I", blob, 0x88, addiu(5, 5, 0xFF0))  # the table at 0xFF0 to 0x1010
        struct.pack_into("<IiIiIiIi", blob, 0xFF0, A, 150, B, -100, C, 60, 0, -100)
        # The formation moved to the third sector: its record at 0x1100, then its
        # steps at 0x1120 and its members at 0x1170, to 0x1198.
        struct.pack_into("<I", blob, 0xC8, addiu(5, 5, 0x1100))
        blob[0x1100:0x1120] = blob[0x190:0x1B0]
        struct.pack_into("<2I", blob, 0x1100, BASE + 0x1120, BASE + 0x1170)
        blob[0x1120:0x1170] = blob[0x1B0:0x200]
        blob[0x1170:0x1198] = blob[0x168:0x190]
        self.files["S1"] = bytes(blob)
        (self.dir / "t.bin").write_bytes(image(self.files))
        result, dump, out = self.package(more=[("position = [100,", "position = [-7,")])
        self.assertEqual(result.returncode, 0, result.stderr)
        overlay, payload = self.overlay_of(out)
        lba = 19 + len(self.files)
        # From the table at 0xFF0, in the file's second sector, to the members' end.
        self.assertEqual((overlay["offset"], len(payload)), (lba * 2048 + 0xFF0, 0x1198 - 0xFF0))
        self.assertEqual(overlay["expected_sha256"],
                         hashlib.sha256(self.files["S1"][0xFF0:0x1198]).hexdigest())
        built = self.built(dump)
        self.assertEqual(struct.unpack_from("<i", built, 0x1004), (90,))  # wave C's delay
        self.assertEqual(struct.unpack_from("<i", built, 0x1108), (-7,))  # the record's x
        self.assertEqual(self.read_back(overlay, payload), built)

    def test_package_of_a_part_before_the_table(self):
        blob = bytearray(zone())  # on the disc the formations precede the tables
        blob[0x10:0x38] = blob[0x168:0x190]  # the members moved to 0x10, before the table
        struct.pack_into("<I", blob, 0x194, BASE + 0x10)
        self.files["S1"] = bytes(blob)
        (self.dir / "t.bin").write_bytes(image(self.files))
        result, dump, out = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        overlay, payload = self.overlay_of(out)
        lba = 19 + len(self.files)
        self.assertEqual((overlay["offset"], len(payload)), (lba * 2048 + 0x10, 0x200 - 0x10))
        self.assertEqual(overlay["expected_sha256"],
                         hashlib.sha256(self.files["S1"][0x10:0x200]).hexdigest())
        self.assertEqual(self.read_back(overlay, payload), self.built(dump))

    def test_package_of_a_zone_without_formations(self):
        self.files["S1"] = patched((0xD0, 0))  # callback A no longer calls 0x80057F0C
        (self.dir / "t.bin").write_bytes(image(self.files))
        result, dump, out = self.package(edit=(f"{{ callback = 0x{C:08X}, delay = 60 }},", ""))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("[[formations]]", dump.read_text())
        overlay, payload = self.overlay_of(out)
        lba = 19 + len(self.files)
        self.assertEqual((overlay["offset"], len(payload)), (lba * 2048 + 0x40, 32))
        self.assertEqual(struct.unpack("<IiIiIiIi", payload), (A, 150, B, -100, 0, -100, 0, 0))
        self.assertEqual(self.read_back(overlay, payload), self.built(dump))

    def test_an_output_path_that_is_not_utf8(self):
        out = self.dir / "\udcff.zone.toml"  # a byte that is not UTF-8
        result = self.run_tool("dump", "S1", "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\\udcff.zone.toml", result.stdout)
        self.assertTrue(out.exists())
        for command, name in (("build", "\udcff.BIN"), ("package", "\udcff.psxmod")):
            with self.subTest(command=command):
                result = self.run_tool(command, out, "--out", self.dir / name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"\\udcff.{name.split('.')[1]}", result.stdout)
                self.assertTrue((self.dir / name).exists())

    def test_package_names_and_versions(self):
        result, _, out = self.package("--id", "my.remix-1", "--name", 'A "quoted" name',
                                      "--version", "2.10.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(out) as z:
            manifest = tomllib.loads(z.read("manifest.toml").decode())
        self.assertEqual((manifest["id"], manifest["name"], manifest["version"]),
                         ("my.remix-1", 'A "quoted" name', "2.10.0"))
        first = out.read_bytes()
        self.package("--id", "my.remix-1", "--name", 'A "quoted" name', "--version", "2.10.0")
        self.assertEqual(out.read_bytes(), first)  # the same input, the same bytes
        for args, message in ((("--id", "Omega.Remix"), "--id Omega.Remix"),
                              (("--id", "remix."), "--id remix."),
                              (("--id", "x" * 97), "at most 96"),
                              (("--version", "1.0"), "--version 1.0"),
                              (("--version", "1.02.0"), "--version 1.02.0")):
            with self.subTest(args=args):
                out.unlink(missing_ok=True)
                result, _, out = self.package(*args)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertFalse(out.exists())
        result = self.run_tool("package", self.dir / "S1.zone.toml", "--out",
                               REPO / "refused.psxmod")
        self.assertEqual(result.returncode, 1)
        self.assertIn("under .cache/ or outside the repository", result.stderr)
        self.assertFalse((REPO / "refused.psxmod").exists())

    def test_package_name_text(self):
        name = "Back\\slash, \x7f and \u00e9"
        result, _, out = self.package("--name", name)
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(out) as z:
            manifest = tomllib.loads(z.read("manifest.toml").decode())
        self.assertEqual((manifest["name"], manifest["feature"][0]["name"]), (name, name))
        out.unlink()
        result, _, out = self.package("--name", "\udcff")  # a byte that is not UTF-8 in argv
        self.assertEqual(result.returncode, 1)
        self.assertIn("--name '\\udcff' is not valid UTF-8 text", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(out.exists())

    def test_package_refuses_what_build_refuses(self):
        result, _, out = self.package(edit=(f"0x{C:08X}", "0x80120004"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("not one of this table's callbacks", result.stderr)
        self.assertFalse(out.exists())

    def recipe(self, text=RECIPE):
        path = self.dir / "test.remix.toml"
        path.write_text(text)
        return path

    def read_back_all(self, overlays, payloads, names):
        """The named zones read from the synthetic disc with every overlay applied."""
        image = (self.dir / "t.bin").read_bytes()
        patched = bytearray(image)
        for overlay in overlays:
            for n, byte in enumerate(payloads[overlay["file"]]):
                lba, pos = divmod(overlay["offset"] + n, 2048)
                patched[lba * 2352 + 24 + pos] = byte
        (self.dir / "t.bin").write_bytes(bytes(patched))
        try:
            disc = zone_data.Disc(self.cue)
            files = disc.zone_files()
            return [zone_data.zone_blob(disc, files, f"{name}/{name}.BIN") for name in names]
        finally:
            (self.dir / "t.bin").write_bytes(image)

    def test_remix_writes_one_package_for_every_zone(self):
        out = self.dir / "remix.psxmod"
        result = self.run_tool("remix", self.recipe(), "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S1/S1.BIN: S1.remix.bin replaces 448 bytes", result.stdout)
        self.assertIn("test.remix 1.2.3, 2 zones", result.stdout)
        with zipfile.ZipFile(out) as z:
            self.assertEqual([(i.filename, i.compress_type, i.date_time) for i in z.infolist()],
                             [(name, 0, (1980, 1, 1, 0, 0, 0))
                              for name in ("manifest.toml", "S1.remix.bin", "U4.remix.bin")])
            manifest = tomllib.loads(z.read("manifest.toml").decode())
            payloads = {o["file"]: z.read(o["file"]) for o in manifest["overlay"]}
        image = (self.dir / "t.bin").read_bytes()
        self.assertEqual((manifest["id"], manifest["version"], manifest["name"],
                          manifest["description"]),
                         ("test.remix", "1.2.3", "Test Remix", "Edits of two synthetic zones."))
        self.assertEqual(manifest["target"], [{"game_id": "SCUS-94449",
                                               "disc_sha256": hashlib.sha256(image).hexdigest()}])
        [feature] = manifest["feature"]
        self.assertEqual((feature["id"], feature["name"], feature["group"],
                          feature["default_enabled"]), ("remix", "Test Remix", "Remix", False))
        # image() puts S1, TITLE and U4 at sectors 22, 23 and 24; each overlay runs
        # from the table at 0x40 to the end of the formation's steps at 0x200.
        self.assertEqual([(o["feature"], o["target"], o["file"], o["offset"])
                          for o in manifest["overlay"]],
                         [("remix", "disc_user", "S1.remix.bin", 22 * 2048 + 0x40),
                          ("remix", "disc_user", "U4.remix.bin", 24 * 2048 + 0x40)])
        for overlay in manifest["overlay"]:
            name = overlay["file"].split(".")[0]
            self.assertEqual(overlay["sha256"], hashlib.sha256(payloads[overlay["file"]]).hexdigest())
            self.assertEqual(overlay["expected_sha256"],
                             hashlib.sha256(self.files[name][0x40:0x200]).hexdigest())
        s1, u4 = self.read_back_all(manifest["overlay"], payloads, ("S1", "U4"))
        self.assertEqual(entries_at(s1, 4), [(C, 10), (A, 150), (B, -100), (0, -100)])
        self.assertEqual(struct.unpack_from("<3i", s1, RECORD - BASE + 8), (74241, -198, -97))
        self.assertEqual(entries_at(u4, 4), [(A, 5), (0, -100), (0, 0), (0, 0)])
        self.assertEqual(u4[0x60:], self.files["U4"][0x60:])  # no formation edits for U4
        first = out.read_bytes()
        self.assertEqual(self.run_tool("remix", self.recipe(), "--out", out).returncode, 0)
        self.assertEqual(out.read_bytes(), first)  # the same input, the same bytes

    def test_remix_refusals(self):
        out = self.dir / "remix.psxmod"
        cases = [
            ('zone = "U4"', 'zone = "TITLE"', "zone TITLE: no shared wave timeline"),
            ('zone = "U4"', 'zone = "S7"', "zone S7: no zone file S7/S7.BIN"),
            ("{ wave = 2, delay = 10 }", "{ wave = 3, delay = 10 }",
             "zone S1 wave 0: the stock table has waves 0 to 2"),
            ("format = 1", "format = 2", "format must be 1"),
        ]
        for old, new, message in cases:
            with self.subTest(message=message):
                result = self.run_tool("remix", self.recipe(RECIPE.replace(old, new)), "--out", out)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(out.exists())
        result = self.run_tool("remix", self.recipe(), "--out", REPO / "refused.psxmod")
        self.assertEqual(result.returncode, 1)
        self.assertIn("under .cache/ or outside the repository", result.stderr)
        self.assertFalse((REPO / "refused.psxmod").exists())
        result = self.run_tool("remix", self.dir / "missing.toml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read", result.stderr)

    def test_bad_discs_and_zones(self):
        missing = self.run_tool("list", cue=self.dir / "missing.cue")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("cannot read", missing.stderr)
        mode1 = self.dir / "m.cue"
        mode1.write_text('FILE "t.bin" BINARY\n  TRACK 01 MODE1/2048\n')
        self.assertIn("TRACK 01 MODE2/2352", self.run_tool("list", cue=mode1).stderr)
        unknown = self.run_tool("dump", "S7")
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("no zone file S7/S7.BIN", unknown.stderr)
        no_table = self.run_tool("dump", "TITLE", "--out", "-")
        self.assertEqual(no_table.returncode, 1)
        self.assertIn("no shared wave timeline", no_table.stderr)


@unittest.skipUnless(DISC.exists(), "the player's disc is not in disc/")
class PlayersDisc(unittest.TestCase):
    def test_every_timeline_on_the_disc_round_trips(self):
        result = subprocess.run([sys.executable, "-B", str(TOOL), "check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("zone files with a timeline: 14, rebuilt identical: 14", result.stdout)

    def test_an_unedited_package_overlays_the_stock_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            dump, out = Path(tmp) / "S1.zone.toml", Path(tmp) / "s1.psxmod"
            for args in (("dump", "S1", "--out", dump), ("package", dump, "--out", out)):
                result = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(out) as z:
                [overlay] = tomllib.loads(z.read("manifest.toml").decode())["overlay"]
                payload = z.read("S1.remix.bin")
        # From the first formation's steps at 0x1DE0 to the end of the table at
        # 0x20F4 (80 bytes): the user data of two sectors.
        lba, pos = divmod(overlay["offset"], 2048)
        self.assertEqual((pos, len(payload)), (0x1DE0 % 2048, 0x2144 - 0x1DE0))
        with open(DISC.parent / "Omega Boost (USA).bin", "rb") as f:
            data = b""
            for n in (lba, lba + 1):
                f.seek(n * 2352 + 24)
                data += f.read(2048)
        self.assertEqual(data[pos:pos + len(payload)], payload)

    def test_the_four_zones_that_start_formations(self):
        result = subprocess.run([sys.executable, "-B", str(TOOL), "list"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Change 4's review counted 5, 3, 15 and 10 calls to 0x80057F0C in these
        # files, each passing its own record.
        found = dict(re.findall(r"^(\S+)/\S+ .*, (\d+) formations?$", result.stdout, re.M))
        self.assertEqual(found, {"S1": "5", "S2": "3", "S3": "15", "S6": "10"})

    def test_the_calls_that_run_on_one_difficulty(self):
        # Change 6's review found these five reading the code (round 1) and with
        # its own control-flow analysis of all 33 calls (round 2).
        found = {}
        for zone in ("S1", "S2", "S3", "S6"):
            result = subprocess.run([sys.executable, "-B", str(TOOL), "dump", zone, "--out", "-"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            notes = comments(result.stdout)
            self.assertNotIn("only on some paths", notes)
            found.update(re.findall(r"Started at (0x[0-9A-F]{8}) by [^,]*, only while the"
                                    r" difficulty word \(0x800A7C34\) is (zero|non-zero)", notes))
        self.assertEqual(found, {"0x8013719C": "non-zero", "0x801371D8": "non-zero",
                                 "0x80137214": "non-zero", "0x80137258": "zero",
                                 "0x80133EC0": "non-zero"})

    def test_the_committed_remixes_build(self):
        image = DISC.parent / "Omega Boost (USA).bin"
        for recipe in sorted((HERE / "remixes").glob("*.toml")):
            with self.subTest(recipe=recipe.name), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "remix.psxmod"
                result = subprocess.run([sys.executable, "-B", str(TOOL), "remix", str(recipe),
                                         "--out", str(out)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                zones = [z["zone"].upper() for z in tomllib.loads(recipe.read_text())["zones"]]
                with zipfile.ZipFile(out) as z:
                    manifest = tomllib.loads(z.read("manifest.toml").decode())
                    payloads = [z.read(o["file"]) for o in manifest["overlay"]]
                self.assertEqual([o["file"] for o in manifest["overlay"]],
                                 [f"{zone}.remix.bin" for zone in zones])
                with open(image, "rb") as f:  # each overlay replaces what the disc holds there
                    for overlay, payload in zip(manifest["overlay"], payloads):
                        lba, pos = divmod(overlay["offset"], 2048)
                        data = b""
                        for n in range(lba, lba + -(-(pos + len(payload)) // 2048)):
                            f.seek(n * 2352 + 24)
                            data += f.read(2048)
                        self.assertEqual(hashlib.sha256(data[pos:pos + len(payload)]).hexdigest(),
                                         overlay["expected_sha256"])


if __name__ == "__main__":
    unittest.main()

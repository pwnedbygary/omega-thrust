#!/usr/bin/env python3
"""Tests for zone_data.py on synthetic zone files and a synthetic disc image.

The last two tests also use the player's disc when disc/ holds it. The
temporary directory (TMPDIR) must be outside the repository, where the tool
may write. Run: python3 -B scripts/zones/test_zone_data.py
"""
import hashlib
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


def i_type(op, rs, rt, imm):
    return op << 26 | rs << 21 | rt << 16 | imm & 0xFFFF


def jal(target):
    return 0x0C000000 | (target & 0x0FFFFFFF) >> 2


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
    """A 512-byte zone file: table at +0x40, init at +0x80, callbacks A, B, C."""
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
    return struct.pack("<128I", *ws)


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
            ("format must be 1", text.replace("format = 1", "format = 2")),
            ("format must be 1", text.replace("format = 1", "format = true")),
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
        self.assertIn("table 0x80120040, 3 waves (1 clear), an end entry, 4 slots", listing.stdout)
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

    def package(self, *args, edit=("delay = 60 }", "delay = 90 }")):
        dump = self.dir / "S1.zone.toml"
        self.assertEqual(self.run_tool("dump", "S1", "--out", dump).returncode, 0)
        dump.write_text(dump.read_text().replace(*edit))
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

    def test_package_puts_the_built_table_on_the_disc(self):
        result, dump, out = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(out) as z:
            self.assertEqual([(i.filename, i.compress_type, i.date_time) for i in z.infolist()],
                             [("manifest.toml", 0, (1980, 1, 1, 0, 0, 0)),
                              ("S1.timeline.bin", 0, (1980, 1, 1, 0, 0, 0))])
            manifest = tomllib.loads(z.read("manifest.toml").decode())
        image = (self.dir / "t.bin").read_bytes()
        self.assertEqual((manifest["format_version"], manifest["id"], manifest["version"],
                          manifest["name"]), (7, "omega.remix.s1", "1.0.0", "1ST ZONE Remix"))
        self.assertEqual(manifest["target"], [{"game_id": "SCUS-94449",
                                               "disc_sha256": hashlib.sha256(image).hexdigest()}])
        [feature] = manifest["feature"]
        self.assertEqual((feature["id"], feature["group"], feature["default_enabled"]),
                         ("timeline", "Remix", False))
        overlay, payload = self.overlay_of(out)
        self.assertEqual((overlay["feature"], overlay["target"], overlay["file"]),
                         ("timeline", "disc_user", "S1.timeline.bin"))
        self.assertEqual(overlay["sha256"], hashlib.sha256(payload).hexdigest())
        stock_table = self.files["S1"][TABLE - BASE:TABLE - BASE + 32]
        self.assertEqual(overlay["expected_sha256"], hashlib.sha256(stock_table).hexdigest())
        built = self.built(dump)
        self.assertEqual(self.read_back(overlay, payload), built)
        self.assertEqual(entries_at(built, 4), [(A, 150), (B, -100), (C, 90), (0, -100)])

    def test_package_of_a_shorter_table_covers_every_stock_slot(self):
        result, dump, out = self.package(edit=(f"{{ callback = 0x{C:08X}, delay = 60 }},", ""))
        self.assertEqual(result.returncode, 0, result.stderr)
        overlay, payload = self.overlay_of(out)
        # No stock entry may stay on the disc after the new end entry.
        self.assertEqual(struct.unpack("<IiIiIiIi", payload), (A, 150, B, -100, 0, -100, 0, 0))
        stock_table = self.files["S1"][TABLE - BASE:TABLE - BASE + 32]
        self.assertEqual(overlay["expected_sha256"], hashlib.sha256(stock_table).hexdigest())
        self.assertEqual(self.read_back(overlay, payload), self.built(dump))

    def test_package_of_a_table_across_two_sectors(self):
        blob = bytearray(zone()) + bytes(6144 - 512)
        struct.pack_into("<I", blob, 0x88, addiu(5, 5, 0xFF0))  # the table at 0xFF0 to 0x1010
        struct.pack_into("<IiIiIiIi", blob, 0xFF0, A, 150, B, -100, C, 60, 0, -100)
        self.files["S1"] = bytes(blob)
        (self.dir / "t.bin").write_bytes(image(self.files))
        result, dump, out = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        overlay, payload = self.overlay_of(out)
        lba = 19 + len(self.files)  # image() puts the first file, S1, after the directories
        self.assertEqual((overlay["offset"], len(payload)), (lba * 2048 + 0xFF0, 32))
        self.assertEqual(overlay["expected_sha256"],
                         hashlib.sha256(self.files["S1"][0xFF0:0x1010]).hexdigest())
        self.assertEqual(self.read_back(overlay, payload), self.built(dump))

    def test_an_output_path_that_is_not_utf8(self):
        out = self.dir / "\udcff.zone.toml"  # a byte that is not UTF-8
        result = self.run_tool("dump", "S1", "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\\udcff.zone.toml", result.stdout)
        self.assertTrue(out.exists())

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
                payload = z.read("S1.timeline.bin")
        lba, pos = divmod(overlay["offset"], 2048)
        self.assertEqual(pos, 0x20F4 % 2048)
        with open(DISC.parent / "Omega Boost (USA).bin", "rb") as f:
            f.seek(lba * 2352 + 24 + pos)
            self.assertEqual(f.read(len(payload)), payload)  # in one sector: 0xF4 + 80 < 2048
        self.assertEqual(len(payload), 80)


if __name__ == "__main__":
    unittest.main()

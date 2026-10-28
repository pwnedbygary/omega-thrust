#!/usr/bin/env python3
"""Tests for beetle_route.py against a fake psx-beetle; no build, disc or BIOS needed.

Linux only (reads /proc). Run: python3 -B scripts/routes/test_beetle_route.py
"""
import contextlib
import hashlib
import json
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from functools import reduce
from operator import xor
from pathlib import Path

DRIVER = Path(__file__).resolve().with_name("beetle_route.py")
SIGNAL_IN_POLL = DRIVER.with_name("signal_in_poll.py")
NEUTRAL, START, CROSS = 65535, 65527, 49151
# Beetle's card files for the disc "Omega Boost (USA).cue": its base name, then ".<slot>.mcr"
CARDS = ["Omega Boost (USA).0.mcr", "Omega Boost (USA).1.mcr"]
# Step 0 starts on frame 300 (--start 300): the shot "a" and the Start press both
# fall on frame 420, the shot "b" and the Cross press on 486, the shot "c" on 490,
# and the route ends on 520.
SHORT = [{"frames": 120, "buttons": NEUTRAL, "shot": "a"},
         {"frames": 6, "buttons": START},
         {"frames": 60, "buttons": NEUTRAL, "shot": "b"},
         {"frames": 4, "buttons": CROSS, "shot": "c"},
         {"frames": 30, "buttons": NEUTRAL}]
# The signal actions that a terminal leaves a program with. An agent's shell may
# start the tests with SIGINT and SIGHUP ignored, and a script keeps an ignored
# signal ignored.
TERMINAL = {signal.SIGINT: signal.default_int_handler, signal.SIGTERM: signal.SIG_DFL,
            signal.SIGHUP: signal.SIG_DFL}


@contextlib.contextmanager
def inherited_signals(actions):
    """Takes these signal actions in the test process for the block, so that the
    processes it starts begin with them: SIG_IGN stays, and a handler becomes the
    default action."""
    previous = {sig: signal.signal(sig, action) for sig, action in actions.items()}
    try:
        yield
    finally:
        for sig, action in previous.items():
            signal.signal(sig, action)


def small_files():
    """Keeps every file that the process writes under 64 KiB, half a memory card.
    Python ignores SIGXFSZ, so a larger write fails with OSError (File too large)."""
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024, 64 * 1024))


# A frame loop in psx-beetle's order (psxrecomp/runtime/src/beetle_main.cpp:226-233):
# read the debug connection and handle every complete request line, take the pad
# override, run the frame. Replies and startup lines copy
# psxrecomp/runtime/src/beetle_debug_server.c and beetle_libretro.cpp. Memory cards
# follow beetle-psx (libretro.cpp, mednafen/psx/frontio.cpp): read from
# "<disc name>.<slot>.mcr" at startup. Beetle saves a changed card about two
# emulated seconds after the game's last write to it, and on exit if it changed
# since; the fake saves only on exit.
FAKE = r'''
import hashlib, json, os, signal, socket, sys, threading, time

argv = sys.argv[1:]
bios, port = argv[0], int(argv[argv.index("--port") + 1])
behavior = os.environ.get("FAKE_BEHAVIOR", "normal")
state = os.environ["FAKE_STATE"]
with open(os.path.join(state, "pids"), "a") as f:
    f.write(f"{os.getpid()}\n")
parent, born = os.getppid(), time.monotonic()
signal.signal(signal.SIGTERM, lambda *_: os._exit(2 if behavior == "badexit" else 0))


def watchdog():
    # Exit when the driver goes away or after 120 s, so no fake outlives its test.
    while os.getppid() == parent and time.monotonic() - born < 120:
        time.sleep(0.2)
    os._exit(4)


threading.Thread(target=watchdog, daemon=True).start()


def note(name, text):
    with open(os.path.join(state, name), "a") as f:
        f.write(text + "\n")


print(f"psx-beetle: loading BIOS from {bios}", flush=True)
found = os.path.join(os.path.dirname(bios), "scph5501.bin")
if behavior != "fallback" and os.path.exists(found):
    with open(found, "rb") as f:
        sha1 = hashlib.sha1(f.read()).hexdigest().upper()
    if behavior == "othersha":
        sha1 = "BFD08F9D5C3DEF7B5B3662F9EC44AF316F95AADA"
    print(f"Firmware found but has invalid SHA1: {found}", flush=True)
    print("Expected SHA1: 0555C6FAE8906F3F09BAF5988F00E55F88E9F30B", flush=True)
    print(f"Obtained SHA1: {sha1}", flush=True)
disc = argv[argv.index("--disc") + 1]
stem = "dummy" if behavior == "othername" else os.path.splitext(os.path.basename(disc))[0]
cards, loaded = {}, {}
for slot in (1, 2):
    name = f"dummy.{slot - 1}.mcr"  # the warn-only check, of files Beetle does not load
    if os.path.exists(name):
        with open(name, "rb") as f:
            data = f.read()
        ok = "OK" if len(data) == 131072 and data[:2] == b"MC" else "INVALID"
        magic = "".join(chr(b) if b else "?" for b in data[:2])
        print(f"[psx-beetle] memcard slot {slot}: {name} size={len(data)} magic={magic} {ok}",
              flush=True)
    else:
        print(f"[psx-beetle] WARNING: {name} missing — slot {slot} will be blank", flush=True)
    try:
        with open(f"{stem}.{slot - 1}.mcr", "rb") as f:
            cards[slot] = f.read()
        loaded[slot] = hashlib.sha256(cards[slot]).hexdigest()
    except FileNotFoundError:
        cards[slot], loaded[slot] = bytes(131072), "missing"
with open(os.path.join(state, "cards.json"), "w") as f:
    json.dump(loaded, f)
# Real runs rewrite card 1's write-test frame, so Beetle saves that card.
cards[1] = cards[1][:0x1F80] + b"\x11" * 4 + bytes(124) + cards[1][0x2000:]


def save_and_exit(*_):
    with open(f"{stem}.0.mcr", "wb") as f:
        f.write(cards[1])
    os._exit(2 if behavior == "badexit" else 0)


# psx-beetle quits on SIGINT and SIGTERM: SDL turns them into SDL_QUIT, which its
# frame loop takes first (psxrecomp/runtime/src/beetle_main.cpp:208-221).
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, save_and_exit)

if behavior == "slowstart":  # no listening line for 2 s
    time.sleep(2)
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port))
srv.listen(1)
srv.setblocking(False)
if behavior == "foreign":
    print(f"[beetle-dbg] bind({port}) failed", flush=True)
else:
    print(f"[beetle-dbg] listening on 127.0.0.1:{port}", flush=True)

client, buf, held, frame, override, remaining = None, b"", [], 0, -1, 0


def handle(req, with_event):
    global override, remaining
    cmd = req["cmd"]
    note("requests.log", cmd)
    reply = {"id": req["id"], "ok": True}
    # pingfail fails the ping sent with a press or screenshot, lonepingfail one sent alone.
    if cmd == "ping" and behavior == ("pingfail" if with_event else "lonepingfail"):
        reply = {"id": req["id"], "ok": False, "error": "busy"}
    elif cmd == "ping":
        reply.update(backend="beetle", port=port, frame=frame, guest_cycles=0)
        # noframe, nullframe and trueframe answer the ping sent with a press or screenshot
        # without a frame, with a null one or with true; lonenoframe, lonenullframe and
        # lonetrueframe do so for one sent alone.
        if behavior == ("noframe" if with_event else "lonenoframe"):
            del reply["frame"]
        elif behavior == ("nullframe" if with_event else "lonenullframe"):
            reply["frame"] = None
        elif behavior == ("trueframe" if with_event else "lonetrueframe"):
            reply["frame"] = True
        elif behavior == "signalatend" and frame >= 520:  # SHORT's end with --start 300
            os.kill(parent, getattr(signal, os.environ.get("FAKE_SIGNAL", "SIGTERM")))
        elif behavior == "groupsignal" and frame >= 350:  # in SHORT's first step
            # As a terminal signals its foreground process group: the driver and this
            # fake. psx-beetle's frame loop takes SDL's quit before it answers the ping,
            # and SIGHUP kills it.
            os.killpg(0, getattr(signal, os.environ["FAKE_SIGNAL"]))
            save_and_exit()
    elif cmd == "press":
        override, remaining = req["buttons"], req.get("frames", 2)
    elif cmd == "screenshot" and behavior == "noshot":
        reply = {"id": req["id"], "ok": False, "error": "no frame"}
    elif cmd == "screenshot":
        with open(req["path"], "wb") as f:
            f.write(b"fake")
        note("shots.log", f"{frame} {os.path.basename(req['path'])}")
        reply.update(path=req["path"], width=350, height=240)
    else:
        reply = {"id": req["id"], "ok": False, "error": "unknown command"}
    if behavior == "notobject":  # every reply, so the run's first ping
        reply = [reply]
    client.sendall((json.dumps(reply) + "\n").encode())


next_t = time.monotonic()
while True:
    if client is None:
        try:
            client, _ = srv.accept()
            client.setblocking(False)
        except BlockingIOError:
            pass
    if client is not None:
        try:
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    client.close()
                    client = None
                    break
                buf += chunk
        except BlockingIOError:
            pass
    lines = []
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        lines.append(line)
    if behavior == "late":  # handle each request one frame late, like a slow driver
        lines, held = held, lines
    requests = [json.loads(line) for line in lines]
    with_event = any(req["cmd"] in ("press", "screenshot") for req in requests)
    for req in requests:
        if client is not None:
            handle(req, with_event)
    pad = override if override >= 0 else 0xFFFF
    if override >= 0 and remaining > 0:
        remaining -= 1
        if remaining == 0:
            override = -1
    if pad != 0xFFFF:
        note("inputs.log", f"{frame} {pad}")
    if not (behavior == "frozen" and frame >= 400):
        frame += 1
    if behavior == "exit" and frame == 450:
        os._exit(3)
    next_t += 1 / 300
    time.sleep(max(0.0, next_t - time.monotonic()))
'''


def formatted_blank(card):
    """Check a card against the PS1 memory card layout in psx-spx (Memory Card Data Format)."""
    frames = [card[i:i + 128] for i in range(0, 8192, 128)]
    return (len(card) == 128 * 1024 and frames[0][:2] == b"MC"
            and all(reduce(xor, f) == 0 for f in frames[:36])
            and all(f[0] == 0xA0 and f[8:10] == b"\xff\xff" for f in frames[1:16])
            and all(f[:4] == b"\xff" * 4 and f[8:10] == b"\xff\xff" for f in frames[16:36])
            and frames[63] == frames[0] and set(card[8192:]) == {0xFF})


class BeetleRouteTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="beetle_route_test.")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.repo = self.dir / "repo"
        bios_dir = self.repo / "psxrecomp" / "bios"
        bios_dir.mkdir(parents=True)
        (self.repo / "disc").mkdir()
        (self.repo / "disc" / "Omega Boost (USA).cue").write_text("")
        self.openbios = bios_dir / "openbios.bin"
        self.openbios.write_bytes(b"open" * 1024)
        self.scph = self.dir / "scph1001.bin"
        self.scph.write_bytes(b"1001" * 1024)
        for profile, image in (("OpenBIOS.toml", self.openbios), ("SCPH1001.toml", self.scph)):
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            (bios_dir / profile).write_text(f'[program]\n[program.image]\nsha256 = "{digest}"\n')
        self.state = self.dir / "state"
        self.state.mkdir()
        self.fake = self.dir / "fake_beetle"
        self.fake.write_text(f"#!{sys.executable}\n{FAKE}")
        self.fake.chmod(0o755)
        self.out = self.dir / "out"
        self.addCleanup(self.kill_fakes)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

    def fake_pids(self):
        try:
            pids = [int(pid) for pid in (self.state / "pids").read_text().split()]
        except (OSError, ValueError):
            return []
        alive = []
        for pid in pids:
            try:
                cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
            except OSError:
                continue
            if str(self.fake).encode() in cmdline:
                alive.append(pid)
        return alive

    def kill_fakes(self):
        for pid in self.fake_pids():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def reset(self):
        shutil.rmtree(self.state)
        self.state.mkdir()
        shutil.rmtree(self.out, ignore_errors=True)

    def route(self, steps=SHORT, name="t", file="route.json", **extra):
        path = self.dir / file
        path.write_text(json.dumps({"name": name, "steps": steps, **extra}))
        return path

    def command(self, route, *extra):
        return [sys.executable, "-B", str(DRIVER), str(route), "--repo", str(self.repo),
                "--binary", str(self.fake), "--port", str(self.port), "--start", "300",
                "--out", str(self.out), *extra]

    def env(self, extra=None):
        base = {k: v for k, v in os.environ.items() if not k.startswith("FAKE_")}
        return {**base, "FAKE_STATE": str(self.state), **(extra or {})}

    def run_driver(self, route, *extra, behavior=None):
        env = self.env({"FAKE_BEHAVIOR": behavior} if behavior else None)
        return subprocess.run(self.command(route, *extra), env=env, capture_output=True,
                              text=True, timeout=60)

    def result(self):
        return json.loads((self.out / "result.json").read_text())

    def failures(self):
        return " | ".join(self.result()["failures"])

    def log(self, name):
        path = self.state / name
        return path.read_text().splitlines() if path.exists() else []

    def started(self):
        return (self.state / "pids").exists()

    def test_pass_lands_every_press_and_shot_on_its_frame(self):
        proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = self.result()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([(p["step"], p["nominal_frame"], p["frame"]) for p in result["presses"]],
                         [(1, 420, 420), (3, 486, 486)])
        self.assertEqual([(r["shot"], r["nominal_frame"], r["frame"]) for r in result["records"]],
                         [("a", 420, 420), ("b", 486, 486), ("c", 490, 490)])
        held = [tuple(map(int, line.split())) for line in self.log("inputs.log")]
        self.assertEqual(held, [(f, START) for f in range(420, 426)]
                         + [(f, CROSS) for f in range(486, 490)])
        self.assertEqual(self.log("shots.log"), ["420 00-a.png", "486 01-b.png", "490 02-c.png"])
        self.assertGreaterEqual(result["end_frame"], 520)
        link = self.out / "system" / "scph5501.bin"
        self.assertEqual(link.resolve(), self.openbios.resolve())
        self.assertEqual(result["bios_sha256"], hashlib.sha256(self.openbios.read_bytes()).hexdigest())
        self.assertIsNone(result["card1_sha256"])
        self.assertEqual(sorted(os.listdir(self.out / "cwd")), CARDS)
        card2 = (self.out / "cwd" / CARDS[1]).read_bytes()  # unchanged, so not saved
        self.assertTrue(formatted_blank(card2))
        blank = hashlib.sha256(card2).hexdigest()
        self.assertEqual(json.loads((self.state / "cards.json").read_text()),
                         {"1": blank, "2": blank})
        self.assertEqual(self.fake_pids(), [])

    def test_scph1001_mode_links_the_given_dump(self):
        proc = self.run_driver(self.route(), "--mode", "lle-scph1001", "--bios", str(self.scph))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual((self.out / "system" / "scph5501.bin").resolve(), self.scph.resolve())
        self.assertEqual(self.result()["bios_sha256"],
                         hashlib.sha256(self.scph.read_bytes()).hexdigest())

    def test_card1_image_is_preloaded(self):
        image = self.dir / "save.mcd"
        image.write_bytes((b"MC" + bytes(range(256)) * 512)[:128 * 1024])
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        proc = self.run_driver(self.route(card1_sha256=digest), "--card1", str(image))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads((self.state / "cards.json").read_text())["1"], digest)
        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), digest)
        self.assertNotEqual((self.out / "cwd" / CARDS[0]).read_bytes(), image.read_bytes())
        self.assertEqual(self.result()["card1_sha256"], digest)

    def test_cards_beetle_does_not_load_fail_the_run(self):
        proc = self.run_driver(self.route(), behavior="othername")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("psx-beetle wrote dummy.0.mcr in cwd/", self.failures())
        self.assertEqual(json.loads((self.state / "cards.json").read_text()),
                         {"1": "missing", "2": "missing"})

    def test_arguments_are_checked_before_launch(self):
        image = self.dir / "save.mcd"
        image.write_bytes(bytes(128 * 1024))
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        short = self.dir / "short.mcd"
        short.write_bytes(bytes(1000))
        other = self.dir / "other.bin"
        other.write_bytes(b"other" * 100)
        cases = [
            ("a route that declares card1_sha256, without --card1",
             {"card1_sha256": digest}, []),
            ("--card1 with another hash", {"card1_sha256": "0" * 64}, ["--card1", str(image)]),
            ("an image of the wrong size", {"card1_sha256": hashlib.sha256(bytes(1000)).hexdigest()},
             ["--card1", str(short)]),
            ("--card1 for a route without card1_sha256", {}, ["--card1", str(image)]),
            ("lle-scph1001 without --bios", {}, ["--mode", "lle-scph1001"]),
            ("--bios with lle-openbios", {}, ["--bios", str(self.scph)]),
            ("a --bios that is not the profile's image", {},
             ["--mode", "lle-scph1001", "--bios", str(other)]),
            ("a route with a bad name", {"name": "../x"}, []),
            ("--start 0", {}, ["--start", "0"]),
        ]
        if os.geteuid() != 0:  # root can read a mode-000 file
            unreadable = self.dir / "unreadable.mcd"
            unreadable.write_bytes(bytes(128 * 1024))
            unreadable.chmod(0)
            cases.append(("an unreadable image", {"card1_sha256": digest},
                          ["--card1", str(unreadable)]))
            # The driver hashes psx-beetle before it makes the output directory.
            execute_only = self.dir / "fake_beetle_execute_only"
            shutil.copy(self.fake, execute_only)
            execute_only.chmod(0o111)
            cases.append(("a psx-beetle that may be run but not read", {},
                          ["--binary", str(execute_only)]))
        for label, fields, extra in cases:
            with self.subTest(label):
                self.reset()
                proc = self.run_driver(self.route(**fields), *extra)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertFalse(self.started())
                self.assertFalse(self.out.exists())
        with self.subTest("an OpenBIOS image that is not the profile's"):
            self.reset()
            self.openbios.write_bytes(b"changed")
            proc = self.run_driver(self.route())
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("needs", proc.stderr)
            self.assertFalse(self.started())

    def test_beetle_must_report_the_bios(self):
        for behavior in ("fallback", "othersha"):
            with self.subTest(behavior):
                self.reset()
                proc = self.run_driver(self.route(), behavior=behavior)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertIn("may have booted its own OpenBIOS", self.failures())
                self.assertNotIn("press", self.log("requests.log"))
                self.assertEqual(self.fake_pids(), [])

    def test_late_input_fails_the_run(self):
        proc = self.run_driver(self.route(), behavior="late")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(self.failures(), "too late to land|landed on frame")

    def test_a_failed_ping_sent_alone_fails_the_run(self):
        proc = self.run_driver(self.route(), behavior="lonepingfail")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(self.failures(), "ping failed: busy")
        self.assertIn("FAIL: ping failed: busy", proc.stdout)
        self.assertEqual(self.log("requests.log"), ["ping"])  # the run stops at its first ping

    def test_a_failed_ping_sent_with_an_event_fails_the_run(self):
        proc = self.run_driver(self.route(), behavior="pingfail")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(self.failures(), "ping failed: busy")
        self.assertIn("FAIL: ping failed: busy", proc.stdout)

    def test_a_ping_reply_without_a_frame_fails_the_run(self):
        press_only = [{"frames": 120, "buttons": NEUTRAL}, {"frames": 6, "buttons": START},
                      {"frames": 30, "buttons": NEUTRAL}]
        # A run's first ping goes alone; press_only's first event is a press with no shot,
        # and SHORT's first event holds a shot and a press. A frame of true is no frame
        # number, though Python counts it as the int 1.
        for case, behavior, steps in (
                ("sent alone, no frame", "lonenoframe", SHORT),
                ("sent alone, null frame", "lonenullframe", SHORT),
                ("sent alone, frame true", "lonetrueframe", SHORT),
                ("sent with only a press, no frame", "noframe", press_only),
                ("sent with only a press, null frame", "nullframe", press_only),
                ("sent with only a press, frame true", "trueframe", press_only),
                ("sent with a shot, no frame", "noframe", SHORT),
                ("sent with a shot, null frame", "nullframe", SHORT),
                ("sent with a shot, frame true", "trueframe", SHORT)):
            with self.subTest(case):
                self.reset()
                # A driver that took true for frame 1 could wait for frame 419 until
                # --timeout; 5 s keeps that failure short, and the fake gets there in 1.4 s.
                proc = self.run_driver(self.route(steps), "--timeout", "5", behavior=behavior)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertRegex(self.failures(), r"^ping reply \{.*\} has no frame number$")
                self.assertIn("FAIL: ping reply", proc.stdout)

    def test_a_reply_that_is_not_a_json_object_fails_the_run(self):
        proc = self.run_driver(self.route(), behavior="notobject")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertRegex(self.failures(), r"^reply to ping is not a JSON object: \[\{.*\}\]$")
        self.assertEqual(self.fake_pids(), [])

    def test_a_failure_after_the_checks_leaves_a_directory_the_next_run_reuses(self):
        # A file size limit below a card's fails the write of Beetle's first card,
        # which the driver makes after it has marked the directory as its own.
        run = subprocess.run(self.command(self.route()), env=self.env(), preexec_fn=small_files,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("File too large", run.stderr)
        self.assertFalse(self.started())
        self.assertEqual(self.result()["status"], "running")
        proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    @unittest.skipIf(os.geteuid() == 0, "root can delete from a read-only directory")
    def test_a_failure_while_clearing_an_earlier_run_keeps_its_marker(self):
        # A directory that lists its entries in creation order, as btrfs and tmpfs do,
        # lists the driver's marker before cwd/, so clearing in that order would delete
        # the marker before failing on cwd/locked.
        self.assertEqual(self.run_driver(self.route()).returncode, 0)
        locked = self.out / "cwd" / "locked"
        locked.mkdir()
        (locked / "file").write_text("the driver cannot delete this")
        locked.chmod(0o555)
        proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("PermissionError", proc.stderr)
        self.assertEqual(self.result()["status"], "PASS")  # the earlier run's record
        locked.chmod(0o755)
        proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_exit_during_the_route_fails(self):
        proc = self.run_driver(self.route(), behavior="exit")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("exited during the route (3)", self.failures())

    def test_timeout_applies_while_frames_stall(self):
        t0 = time.monotonic()
        proc = self.run_driver(self.route(), "--timeout", "2", behavior="frozen")
        self.assertLess(time.monotonic() - t0, 20)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("timed out after 2 s at frame 400", self.failures())
        self.assertEqual(self.fake_pids(), [])

    def test_failed_screenshot_is_recorded(self):
        proc = self.run_driver(self.route(), behavior="noshot")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual({r["screenshot"]["error"] for r in self.result()["records"]}, {"no frame"})

    def test_exit_code_after_sigterm_must_be_zero(self):
        proc = self.run_driver(self.route(), behavior="badexit")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("psx-beetle exit code 2", self.failures())

    def test_busy_port_is_refused(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", self.port))
            sock.listen(1)
            proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("already accepts connections", proc.stderr)
        self.assertFalse(self.started())

    def test_a_server_that_is_not_beetle_s_is_not_driven(self):
        proc = self.run_driver(self.route(), behavior="foreign")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("could not bind", self.failures())
        self.assertEqual(self.log("requests.log"), [])

    def test_output_directory_rules(self):
        self.out.mkdir()
        (self.out / "notes.txt").write_text("keep")
        proc = self.run_driver(self.route())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to use", proc.stderr)
        (self.out / "notes.txt").unlink()
        self.assertEqual(self.run_driver(self.route()).returncode, 0)
        (self.out / "keep.txt").write_text("keep")
        (self.out / "100-stale.png").write_bytes(b"old")
        self.assertEqual(self.run_driver(self.route()).returncode, 0)
        self.assertTrue((self.out / "keep.txt").exists())
        self.assertFalse((self.out / "100-stale.png").exists())

    def test_sigterm_stops_beetle(self):
        steps = [{"frames": 6000, "buttons": NEUTRAL, "shot": "a"}]
        proc = subprocess.Popen(self.command(self.route(steps)), env=self.env(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while "ping" not in self.log("requests.log") and time.monotonic() < deadline:
                time.sleep(0.05)
            proc.send_signal(signal.SIGTERM)
            proc.communicate(timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("driver stopped: SystemExit: stopped by SIGTERM", self.failures())
        self.assertEqual(self.result()["records"], [])
        self.assertEqual(self.fake_pids(), [])

    def test_a_signal_inside_poll_stops_beetle(self):
        # signal_in_poll.py sends the signal right after Popen.poll() has taken
        # psx-beetle's waitpid lock; the driver must still stop it, before it connects.
        route = self.route()
        env = self.env({"FAKE_BEHAVIOR": "slowstart"})
        for name, returncode in (("SIGTERM", 1), ("SIGHUP", 1), ("SIGINT", -signal.SIGINT)):
            with self.subTest(name):
                self.reset()
                # python3 -B signal_in_poll.py <name> beetle_route.py <the driver's arguments>
                cmd = self.command(route)
                cmd[2:2] = [str(SIGNAL_IN_POLL), name]
                run = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, returncode, run.stderr)
                self.assertIn(f"stopped by {name}", self.failures())
                self.assertNotIn("ping", self.log("requests.log"))
                self.assertEqual(self.fake_pids(), [])

    def test_a_signal_as_the_route_ends_fails_the_run(self):
        proc = self.run_driver(self.route(), behavior="signalatend")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("stopped by SIGTERM", self.failures())
        self.assertEqual(self.fake_pids(), [])

    def test_a_signal_to_the_process_group_stops_beetle(self):
        # A terminal sends Ctrl-C and a hang-up to its whole foreground process group,
        # so psx-beetle gets them too, and its exit fails the ping that the driver is
        # waiting for. The driver runs in a session of its own, and the fake signals
        # that group on frame 350 and exits as psx-beetle would: the driver must record
        # the signal, not psx-beetle's exit.
        route = self.route()
        for name, returncode in (("SIGTERM", 1), ("SIGHUP", 1), ("SIGINT", -signal.SIGINT)):
            with self.subTest(name):
                self.reset()
                env = self.env({"FAKE_BEHAVIOR": "groupsignal", "FAKE_SIGNAL": name})
                with inherited_signals(TERMINAL):
                    run = subprocess.run(self.command(route), env=env, start_new_session=True,
                                         capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, returncode, run.stdout + run.stderr)
                self.assertRegex(self.failures(), rf"^driver stopped: \w+: stopped by {name}")
                self.assertNotIn("exited during the route", self.failures())
                self.assertEqual(self.fake_pids(), [])

    def test_a_signal_ignored_at_start_stays_ignored(self):
        # nohup starts a program with SIGHUP ignored; the driver must leave it so.
        env = self.env({"FAKE_BEHAVIOR": "signalatend", "FAKE_SIGNAL": "SIGHUP"})
        with inherited_signals({signal.SIGHUP: signal.SIG_IGN}):
            run = subprocess.run(self.command(self.route()), env=env, capture_output=True,
                                 text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.result()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

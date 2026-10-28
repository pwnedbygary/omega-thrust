#!/usr/bin/env python3
"""Tests for run_route.py against a fake runtime; no build, disc or BIOS needed.

Linux only (reads /proc). Run: python3 -B scripts/routes/test_run_route.py
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
from pathlib import Path

RUNNER = Path(__file__).resolve().with_name("run_route.py")
SIGNAL_IN_POLL = RUNNER.with_name("signal_in_poll.py")
SHORT = [{"frames": 60, "buttons": 65535, "shot": "a"},
         {"frames": 6, "buttons": 65527},
         {"frames": 60, "buttons": 65535, "shot": "b"}]
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


# Replies use the shapes of psxrecomp/runtime/src/debug_server.c; the startup
# lines copy the runtime's LISTENING / bind FAILED and bios_boot banner formats.
FAKE = r'''
import hashlib, json, os, signal, socket, sys, threading, time

argv = sys.argv[1:]
port = int(argv[argv.index("--debug-port") + 1])
behavior = os.environ.get("FAKE_BEHAVIOR", "normal")
misses = int(os.environ.get("FAKE_MISSES", "0"))
state = os.environ["FAKE_STATE"]
with open(os.path.join(state, "pids"), "a") as f:
    f.write(f"{os.getpid()}\n")
parent, born = os.getppid(), time.monotonic()
card = os.path.join(argv[argv.index("--memcard-dir") + 1], "card1.mcd")
seen = "none"
if os.path.exists(card):
    with open(card, "r+b") as f:
        seen = hashlib.sha256(f.read()).hexdigest()
        # Real runs rewrite the card's write-test frame (offset 0x1F80).
        f.seek(0x1F80)
        f.write(b"\x11" * 4 + bytes(124))
with open(os.path.join(state, "card1"), "w") as f:
    f.write(seen)


def watchdog():
    # Exit when the runner goes away (a hung runner is killed by the test's
    # timeout) or after 120 s, so no fake outlives its test.
    while os.getppid() == parent and time.monotonic() - born < 120:
        time.sleep(0.2)
    os._exit(4)


threading.Thread(target=watchdog, daemon=True).start()
# psx-runtime exits with status 0 on SIGINT and SIGTERM
# (psxrecomp/runtime/src/crash_trace.c:909-915, 955-956), and SIGHUP kills it.
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: os._exit(0))


def env_on(name, default):
    value = os.environ.get(name)
    return default if value is None else value[:1] not in ("", "0")


skip = env_on("PSX_BIOS_HLE", True) and not env_on("PSX_BIOS_HLE_KEEP_INTRO", False)
image = "SCPH-1001" if "--bios" in argv and os.environ.get("FAKE_BIOS_VALID") == "1" else "OPENBIOS"
if behavior == "slowstart":  # no LISTENING line for 2 s
    time.sleep(2)
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port))
srv.listen(16)
if behavior == "foreign":
    print(f"psxrecomp: debug server bind({port}) FAILED", flush=True)
else:
    print(f"psxrecomp: debug server LISTENING on 127.0.0.1:{port}", flush=True)
print("psxrecomp: bios_backend=LLE (recompiled BIOS)  bios_boot="
      + ("HLE (shell skipped)" if skip else "LLE (real intro)") + f"  image={image}", flush=True)
t0, steps, start, lock = time.monotonic(), [], None, threading.Lock()


def frame():
    return int((time.monotonic() - t0) * 600)


def status():
    if start is None:
        return {"active": False, "steps": len(steps), "index": 0, "remaining": 0}
    elapsed, end = frame() - start, 0
    for i, step in enumerate(steps):
        end += step["frames"]
        if elapsed < end:
            return {"active": True, "steps": len(steps), "index": i, "remaining": end - elapsed}
    return {"active": False, "steps": len(steps), "index": len(steps), "remaining": 0}


def broken(cmd, reply):
    """reply as the behaviors that break it send it: without a value the runner reads,
    with that value of another type, or not a JSON object at all."""
    if cmd == "input_route_start" and behavior == "nostartframe":
        del reply["start_frame"]
    elif cmd == "input_route_start" and behavior == "truestartframe":
        reply["start_frame"] = True
    elif cmd == "input_route_start" and behavior == "notobject":
        return [reply]
    elif cmd == "input_route_status" and behavior == "noindex":
        del reply["index"]
    elif cmd == "input_route_status" and behavior == "noremaining":
        del reply["remaining"]
    elif cmd == "input_route_status" and behavior == "intactive":
        reply["active"] = int(reply["active"])
    elif cmd == "frame" and behavior == "textframe":
        reply["frame"] = "x"
    return reply


def handle(conn):
    global start
    with conn:
        line = conn.makefile().readline()
        if not line:
            return
        req = json.loads(line)
        cmd = req["cmd"]
        with lock, open(os.path.join(state, "requests.log"), "a") as f:
            f.write(cmd + "\n")
        reply = {"id": req["id"], "ok": True}
        if cmd == "frame":
            reply["frame"] = frame()
        elif cmd == "input_route_append":
            steps.append(req)
            reply["steps"] = len(steps)
        elif cmd == "input_route_start" and behavior == "groupsignal":
            # As a terminal signals its foreground process group: the runner and this
            # fake, which exits as psx-runtime would (above), so the request gets no
            # reply.
            os.killpg(0, getattr(signal, os.environ["FAKE_SIGNAL"]))
            os._exit(0)
        elif cmd == "input_route_start":
            start = frame()
            reply.update(steps=len(steps), start_frame=start)
        elif cmd == "input_route_status" and behavior == "wedge":
            time.sleep(30)
            return
        elif cmd == "input_route_status" and behavior == "teardown":
            reply = {"id": req["id"], "ok": False, "err": "emu busy or frozen"}
            threading.Timer(0.3, os._exit, (3,)).start()
        elif cmd == "input_route_status":
            reply.update(status())
        elif cmd == "screenshot" and behavior == "noshot":
            reply = {"id": req["id"], "ok": False, "error": "display disabled"}
        elif cmd == "screenshot":
            with open(req["path"], "wb") as f:
                f.write(b"fake")
        elif cmd == "dispatch_stats":
            reply.update(miss_total=misses, segment_miss_total=0)
        elif cmd == "unknown_dispatch_log":
            reply["total"] = misses
            if behavior == "signalatend" and start is not None and not status()["active"]:
                # As the runner records the route's end: SIGTERM, or FAKE_SIGNAL's signal.
                os.kill(parent, getattr(signal, os.environ.get("FAKE_SIGNAL", "SIGTERM")))
        elif cmd == "segment_misses":
            reply["total"] = 0
        conn.sendall((json.dumps(broken(cmd, reply)) + "\n").encode())
        if cmd == "quit":
            os._exit(0)


while True:
    conn, _ = srv.accept()
    threading.Thread(target=handle, args=(conn,), daemon=True).start()
'''


class RunRouteTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="run_route_test.")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.repo = self.dir / "repo"
        (self.repo / "disc").mkdir(parents=True)
        (self.repo / "game.toml").write_text("")
        (self.repo / "disc" / "Omega Boost (USA).cue").write_text("")
        self.state = self.dir / "state"
        self.state.mkdir()
        self.fake = self.dir / "fake_runtime"
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

    def route(self, steps, name="t", file="route.json", **extra):
        path = self.dir / file
        path.write_text(json.dumps({"name": name, "steps": steps, **extra}))
        return path

    def command(self, route, *extra, out=True, binary=None):
        cmd = [sys.executable, "-B", str(RUNNER), str(route), "--repo", str(self.repo),
               "--binary", str(binary or self.fake), "--port", str(self.port), *extra]
        return cmd + (["--out", str(self.out)] if out else [])

    def env(self, extra=None):
        base = {k: v for k, v in os.environ.items() if not k.startswith("FAKE_")}
        return {**base, "FAKE_STATE": str(self.state), **(extra or {})}

    def run_runner(self, route, *extra, env=None, out=True, binary=None):
        return subprocess.run(self.command(route, *extra, out=out, binary=binary),
                              env=self.env(env), capture_output=True, text=True, timeout=60)

    def result(self):
        return json.loads((self.out / "result.json").read_text())

    def failures(self):
        return " | ".join(self.result()["failures"])

    def requests(self):
        log = self.state / "requests.log"
        return log.read_text().split() if log.exists() else []

    def started(self):
        return (self.state / "pids").exists()

    def reset(self):
        self.kill_fakes()
        for path in self.state.iterdir():
            path.unlink()
        shutil.rmtree(self.out, ignore_errors=True)
        shutil.rmtree(self.repo / ".cache", ignore_errors=True)

    def test_pass_records_shots_after_their_steps(self):
        run = self.run_runner(self.route(SHORT))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = self.result()
        self.assertEqual((result["status"], result["failures"]), ("PASS", []))
        self.assertEqual(result["boot"], {"bios_boot": "HLE", "image": "OPENBIOS"})
        shots = [rec for rec in result["records"] if rec["step"] is not None]
        self.assertEqual([rec["shot"] for rec in shots], ["a", "b"])
        start = result["start_frame"]
        self.assertEqual([rec["nominal_frame"] for rec in shots], [start + 60, start + 126])
        for rec in shots:
            self.assertGreaterEqual(rec["frame"]["frame"], rec["nominal_frame"])
        self.assertTrue((self.out / "00-a.png").is_file())
        self.assertTrue((self.out / "01-b.png").is_file())
        self.assertEqual(self.requests()[-1], "quit")
        self.assertIsNone(result["card1_sha256"])
        self.assertEqual((self.state / "card1").read_text(), "none")

    def test_bad_routes_are_rejected_before_launch(self):
        cases = {
            "name escaping the output root": {"name": "../../escaped", "steps": SHORT},
            "absolute name": {"name": str(self.dir / "abs"), "steps": SHORT},
            "non-string name": {"name": 5, "steps": SHORT},
            "frames above the server's int": {"steps": [{"frames": 2**31, "buttons": 65535}]},
            "frames that would wrap to 1": {"steps": [{"frames": 2**32 + 1, "buttons": 65535}]},
            "card1_sha256 that is not lowercase hex": {"steps": SHORT, "card1_sha256": "AB" * 32},
        }
        for label, data in cases.items():
            with self.subTest(label):
                self.reset()
                path = self.dir / "bad.json"
                path.write_text(json.dumps(data))
                run = self.run_runner(path, out=False)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertFalse(self.started())
                self.assertFalse((self.repo / ".cache").exists())
        self.assertFalse((self.repo / "escaped").exists())
        self.assertFalse((self.dir / "abs").exists())

    def test_unknown_non_empty_out_dir_is_left_alone(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("user file")
        (self.out / "sub").mkdir()
        run = self.run_runner(self.route(SHORT))
        self.assertEqual(run.returncode, 1)
        self.assertIn("refusing", run.stderr)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["keep.txt", "sub"])
        self.assertFalse(self.started())

    def test_runner_out_dir_is_reused_removing_only_runner_files(self):
        self.assertEqual(self.run_runner(self.route(SHORT)).returncode, 0)
        (self.out / "notes.txt").write_text("keep")
        (self.out / "07-stale.png").write_bytes(b"x")
        (self.out / "100-stale.png").write_bytes(b"x")
        run = self.run_runner(self.route(SHORT))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue((self.out / "notes.txt").is_file())
        self.assertFalse((self.out / "07-stale.png").exists())
        self.assertFalse((self.out / "100-stale.png").exists())

    def test_bios_arguments_are_checked_before_launch(self):
        bios = self.dir / "bios.bin"
        bios.write_bytes(bytes(16))
        cases = {
            "scph without --bios": ["--mode", "lle-scph1001"],
            "scph with a missing file": ["--mode", "lle-scph1001", "--bios", str(self.dir / "no.bin")],
            "--bios in an OpenBIOS mode": ["--mode", "lle-openbios", "--bios", str(bios)],
        }
        for label, extra in cases.items():
            with self.subTest(label):
                self.reset()
                run = self.run_runner(self.route(SHORT), *extra)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertFalse(self.started())

    def test_card1_image_is_preloaded(self):
        image = bytes(range(256)) * 512
        digest = hashlib.sha256(image).hexdigest()
        card = self.dir / "card.mcd"
        card.write_bytes(image)
        run = self.run_runner(self.route(SHORT, card1_sha256=digest), "--card1", str(card))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual((self.state / "card1").read_text(), digest)
        self.assertEqual(self.result()["card1_sha256"], digest)
        written = image[:0x1F80] + b"\x11" * 4 + bytes(124) + image[0x2000:]
        self.assertEqual((self.out / "memcards" / "card1.mcd").read_bytes(), written)
        self.assertEqual(card.read_bytes(), image)

    def test_card1_arguments_are_checked_before_launch(self):
        image = bytes(range(256)) * 512
        good, other, short = self.dir / "good.mcd", self.dir / "other.mcd", self.dir / "short.mcd"
        good.write_bytes(image)
        other.write_bytes(image[:-1] + b"\x00")
        short.write_bytes(image[:1000])
        needs = self.route(SHORT, file="needs.json", card1_sha256=hashlib.sha256(image).hexdigest())
        cases = {
            "declared but no --card1": (needs, []),
            "--card1 names a missing file": (needs, ["--card1", str(self.dir / "none.mcd")]),
            "--card1 with another hash": (needs, ["--card1", str(other)]),
            "an image of the wrong size": (
                self.route(SHORT, file="short.json",
                           card1_sha256=hashlib.sha256(image[:1000]).hexdigest()),
                ["--card1", str(short)]),
            "--card1 for a route without card1_sha256": (self.route(SHORT, file="plain.json"),
                                                         ["--card1", str(good)]),
        }
        if os.geteuid() != 0:  # root can read a mode-000 file
            unreadable = self.dir / "unreadable.mcd"
            unreadable.write_bytes(image)
            unreadable.chmod(0)
            cases["an unreadable image"] = (needs, ["--card1", str(unreadable)])
        for label, (route, extra) in cases.items():
            with self.subTest(label):
                self.reset()
                run = self.run_runner(route, *extra)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertFalse(self.started())
                self.assertFalse(self.out.exists())
        self.assertEqual(good.read_bytes(), image)

    def test_inherited_bios_env_cannot_change_the_mode(self):
        run = self.run_runner(self.route(SHORT), "--mode", "hle-openbios",
                              env={"PSX_BIOS_HLE": "0", "PSX_BIOS_HLE_KEEP_INTRO": "1"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.result()["boot"], {"bios_boot": "HLE", "image": "OPENBIOS"})

    def test_boot_banner_must_match_the_mode(self):
        bios = self.dir / "bios.bin"
        bios.write_bytes(bytes(16))
        run = self.run_runner(self.route(SHORT), "--mode", "lle-scph1001", "--bios", str(bios))
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("image=OPENBIOS", self.failures())
        self.assertNotIn("input_route_start", self.requests())
        run = self.run_runner(self.route(SHORT), "--mode", "lle-scph1001", "--bios", str(bios),
                              env={"FAKE_BIOS_VALID": "1"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_port_already_in_use_is_refused(self):
        with socket.socket() as srv:
            srv.bind(("127.0.0.1", self.port))
            srv.listen(4)
            run = self.run_runner(self.route(SHORT))
            srv.settimeout(0.2)
            data = b""
            try:
                while True:
                    conn, _ = srv.accept()
                    with conn:
                        conn.settimeout(0.5)
                        data += conn.recv(4096)
            except OSError:
                pass
        self.assertEqual(run.returncode, 1)
        self.assertIn(f"127.0.0.1:{self.port}", run.stderr)
        self.assertEqual(data, b"")
        self.assertFalse(self.started())

    def test_server_without_our_listening_line_is_not_driven(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": "foreign"})
        self.assertEqual(run.returncode, 1)
        self.assertIn("could not bind", self.failures())
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.fake_pids(), [])

    def test_timeout_applies_while_status_requests_hang(self):
        began = time.monotonic()
        run = self.run_runner(self.route(SHORT), "--timeout", "2", env={"FAKE_BEHAVIOR": "wedge"})
        self.assertEqual(run.returncode, 1)
        self.assertLess(time.monotonic() - began, 20)
        self.assertIn("timed out", self.failures())

    def test_error_status_reply_is_recorded(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": "teardown"})
        self.assertEqual(run.returncode, 1)
        self.assertNotIn("Traceback", run.stderr)
        self.assertIn("exited during the route (3)", self.failures())

    def test_a_reply_without_what_the_runner_reads_fails_the_run(self):
        # Each behavior breaks one reply: a value that the runner reads is missing, or
        # of another type (Python counts a JSON true as an int), or the reply is not a
        # JSON object at all.
        for behavior, failure in (
                ("nostartframe", r"input_route_start reply \{.*\} has no integer start_frame"),
                ("truestartframe", r"input_route_start reply \{.*\} has no integer start_frame"),
                ("notobject", r"input_route_start failed: reply to input_route_start is not a "
                              r"JSON object: \[\{.*\}\]"),
                ("noindex", r"input_route_status reply \{.*\} has no integer index"),
                ("noremaining", r"input_route_status reply \{.*\} has no integer remaining"),
                ("intactive", r"input_route_status reply \{.*\} has no boolean active")):
            with self.subTest(behavior):
                self.reset()
                run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": behavior})
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertRegex(self.failures(), f"^{failure}$")
                self.assertEqual(self.fake_pids(), [])

    def test_a_frame_reply_without_a_frame_count_is_recorded_as_it_came(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": "textframe"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertEqual({rec["frame"]["frame"] for rec in self.result()["records"]}, {"x"})
        self.assertIn("frame x  unknown-dispatch", run.stdout)

    def test_a_failure_after_the_checks_leaves_a_directory_the_next_run_reuses(self):
        # A file size limit below a card's fails the copy of --card1 into memcards/,
        # which the runner makes after it has marked the directory as its own.
        image = bytes(range(256)) * 512
        card = self.dir / "card.mcd"
        card.write_bytes(image)
        route = self.route(SHORT, card1_sha256=hashlib.sha256(image).hexdigest())
        run = subprocess.run(self.command(route, "--card1", str(card)), env=self.env(),
                             preexec_fn=small_files, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("File too large", run.stderr)
        self.assertFalse(self.started())
        self.assertEqual(self.result()["status"], "running")
        run = self.run_runner(route, "--card1", str(card))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    @unittest.skipIf(os.geteuid() == 0, "root can delete from a read-only directory")
    def test_a_failure_while_clearing_an_earlier_run_keeps_its_marker(self):
        # A directory that lists its entries in creation order, as btrfs and tmpfs do,
        # lists the runner's marker before cwd/, so clearing in that order would delete
        # the marker before failing on cwd/locked.
        self.assertEqual(self.run_runner(self.route(SHORT)).returncode, 0)
        locked = self.out / "cwd" / "locked"
        locked.mkdir()
        (locked / "file").write_text("the runner cannot delete this")
        locked.chmod(0o555)
        run = self.run_runner(self.route(SHORT))
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("PermissionError", run.stderr)
        self.assertEqual(self.result()["status"], "PASS")  # the earlier run's record
        locked.chmod(0o755)
        run = self.run_runner(self.route(SHORT))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_failed_screenshot_is_recorded_without_failing(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": "noshot"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("no png (display disabled)", run.stdout)
        self.assertFalse((self.out / "00-a.png").exists())

    def test_misses_fail_the_run(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_MISSES": "2"})
        self.assertEqual(run.returncode, 1)
        self.assertIn("unknown-dispatch 2", self.failures())

    def test_missing_binary_is_reported_before_launch(self):
        run = self.run_runner(self.route(SHORT), binary=self.dir / "missing")
        self.assertEqual(run.returncode, 1)
        self.assertIn("not found", run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertFalse(self.out.exists())

    def test_sigterm_stops_the_runtime(self):
        cmd = self.command(self.route([{"frames": 10**7, "buttons": 65535}]))
        runner = subprocess.Popen(cmd, env=self.env(), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while "input_route_start" not in self.requests():
                self.assertLess(time.monotonic(), deadline, "the route never started")
                time.sleep(0.1)
            runner.send_signal(signal.SIGTERM)
            runner.communicate(timeout=40)
        finally:
            if runner.poll() is None:
                runner.kill()
                runner.wait()
        self.assertEqual(runner.returncode, 1)
        self.assertEqual(self.fake_pids(), [])
        self.assertIn("SIGTERM", self.failures())

    def test_a_signal_inside_poll_stops_the_runtime(self):
        # signal_in_poll.py sends the signal right after Popen.poll() has taken the
        # runtime's waitpid lock; the runner must still stop it, before the route starts.
        route = self.route(SHORT)
        for name, returncode in (("SIGTERM", 1), ("SIGHUP", 1), ("SIGINT", -signal.SIGINT)):
            with self.subTest(name):
                self.reset()
                # python3 -B signal_in_poll.py <name> run_route.py <the runner's arguments>
                cmd = self.command(route)
                cmd[2:2] = [str(SIGNAL_IN_POLL), name]
                run = subprocess.run(cmd, env=self.env({"FAKE_BEHAVIOR": "slowstart"}),
                                     capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, returncode, run.stderr)
                self.assertIn(f"stopped by {name}", self.failures())
                self.assertNotIn("input_route_start", self.requests())
                self.assertEqual(self.fake_pids(), [])

    def test_a_signal_as_the_route_ends_fails_the_run(self):
        run = self.run_runner(self.route(SHORT), env={"FAKE_BEHAVIOR": "signalatend"})
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertIn("stopped by SIGTERM", self.failures())
        self.assertEqual(self.fake_pids(), [])

    def test_a_signal_to_the_process_group_stops_the_runtime(self):
        # A terminal sends Ctrl-C and a hang-up to its whole foreground process group,
        # so the runtime gets them too, and its exit can fail a request before the
        # runner's next check. The runner runs in a session of its own, and the fake
        # signals that group when asked to start the route, then exits without a reply:
        # the runner must record the signal, not the failed request.
        route = self.route(SHORT)
        for name, returncode in (("SIGTERM", 1), ("SIGHUP", 1), ("SIGINT", -signal.SIGINT)):
            with self.subTest(name):
                self.reset()
                env = self.env({"FAKE_BEHAVIOR": "groupsignal", "FAKE_SIGNAL": name})
                with inherited_signals(TERMINAL):
                    run = subprocess.run(self.command(route), env=env, start_new_session=True,
                                         capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, returncode, run.stderr)
                self.assertRegex(self.failures(), rf"^runner stopped: \w+: stopped by {name}")
                self.assertNotIn("input_route_start failed", self.failures())
                self.assertEqual(self.fake_pids(), [])

    def test_a_signal_ignored_at_start_stays_ignored(self):
        # nohup starts a program with SIGHUP ignored; the runner must leave it so.
        with inherited_signals({signal.SIGHUP: signal.SIG_IGN}):
            run = self.run_runner(self.route(SHORT),
                                  env={"FAKE_BEHAVIOR": "signalatend", "FAKE_SIGNAL": "SIGHUP"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.result()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

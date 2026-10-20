#!/usr/bin/env python3
"""Tests for run_route.py against a fake runtime; no build, disc or BIOS needed.

Linux only (reads /proc). Run: python3 -B scripts/routes/test_run_route.py
"""
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().with_name("run_route.py")
SHORT = [{"frames": 60, "buttons": 65535, "shot": "a"},
         {"frames": 6, "buttons": 65527},
         {"frames": 60, "buttons": 65535, "shot": "b"}]

# Replies use the shapes of psxrecomp/runtime/src/debug_server.c; the startup
# lines copy the runtime's LISTENING / bind FAILED and bios_boot banner formats.
FAKE = r'''
import json, os, socket, sys, threading, time

argv = sys.argv[1:]
port = int(argv[argv.index("--debug-port") + 1])
behavior = os.environ.get("FAKE_BEHAVIOR", "normal")
misses = int(os.environ.get("FAKE_MISSES", "0"))
state = os.environ["FAKE_STATE"]
with open(os.path.join(state, "pids"), "a") as f:
    f.write(f"{os.getpid()}\n")
parent, born = os.getppid(), time.monotonic()


def watchdog():
    # Exit when the runner goes away (a hung runner is killed by the test's
    # timeout) or after 120 s, so no fake outlives its test.
    while os.getppid() == parent and time.monotonic() - born < 120:
        time.sleep(0.2)
    os._exit(4)


threading.Thread(target=watchdog, daemon=True).start()


def env_on(name, default):
    value = os.environ.get(name)
    return default if value is None else value[:1] not in ("", "0")


skip = env_on("PSX_BIOS_HLE", True) and not env_on("PSX_BIOS_HLE_KEEP_INTRO", False)
image = "SCPH-1001" if "--bios" in argv and os.environ.get("FAKE_BIOS_VALID") == "1" else "OPENBIOS"
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
        elif cmd == "segment_misses":
            reply["total"] = 0
        conn.sendall((json.dumps(reply) + "\n").encode())
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

    def route(self, steps, name="t"):
        path = self.dir / "route.json"
        path.write_text(json.dumps({"name": name, "steps": steps}))
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

    def test_bad_routes_are_rejected_before_launch(self):
        cases = {
            "name escaping the output root": {"name": "../../escaped", "steps": SHORT},
            "absolute name": {"name": str(self.dir / "abs"), "steps": SHORT},
            "non-string name": {"name": 5, "steps": SHORT},
            "frames above the server's int": {"steps": [{"frames": 2**31, "buttons": 65535}]},
            "frames that would wrap to 1": {"steps": [{"frames": 2**32 + 1, "buttons": 65535}]},
        }
        for label, data in cases.items():
            with self.subTest(label):
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
                run = self.run_runner(self.route(SHORT), *extra)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertFalse(self.started())

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


if __name__ == "__main__":
    unittest.main()

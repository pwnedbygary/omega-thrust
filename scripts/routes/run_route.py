#!/usr/bin/env python3
"""Play an input route against the headless dev runtime and record evidence.

A route is a JSON file in the format of psxrecomp/tools/perf_routes:
{"name", "title", "notes", "steps": [{"frames", "buttons"}, ...]}, where
buttons is the inverted PS1 pad word (0 = pressed, 65535 = neutral). Steps may
add "note" (free text) and "shot" (a screenshot name). The runtime plays the
steps itself, one step frame per runtime frame (input_route_* debug commands),
so input timing is frame-exact relative to the route's start frame. The runner
takes each shot after its step has ended, a few frames late, and records the
frame it read just before the screenshot.

A route may declare "card1_sha256", the sha256 of a raw 128 KiB memory card
image it needs in slot 1, such as a save that opens more of the game. It then
runs only with --card1 naming an image with that hash, which the runner copies
into memcards/card1.mcd before the runtime starts; otherwise both cards start
blank.

The run fails unless the runtime boots in the requested mode, plays the whole
route, reports no unknown-dispatch or segment miss, and exits 0 after `quit`.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

MODES = {  # PSX_BIOS_HLE value, then the boot banner's bios_boot and image
    "hle-openbios": ("1", "HLE", "OPENBIOS"),
    "lle-openbios": ("0", "LLE", "OPENBIOS"),
    "lle-scph1001": ("0", "LLE", "SCPH-1001"),
}
DISC = "disc/Omega Boost (USA).cue"
RUNNER = "scripts/routes/run_route.py"
MAX_FRAMES = 2**31 - 1  # the debug server parses frames with (int)strtol
CARD_SIZE = 128 * 1024
NAME = re.compile(r"[A-Za-z0-9_-]+")
SHA256 = re.compile(r"[0-9a-f]{64}")
OUTPUTS = ("cwd", "memcards", "runtime.log", "result.json")
SHOT_FILE = re.compile(r"\d{2,}-[A-Za-z0-9_-]+\.png")
BANNER = re.compile(r"bios_boot=(HLE|LLE) .*?image=(\S+)")


class RouteError(Exception):
    pass


def ask(port, cmd, **params):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall((json.dumps({"id": 1, "cmd": cmd, **params}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = sock.recv(1 << 16)
            if not chunk:
                break
            buf += chunk
    if not buf:
        raise OSError(f"empty reply to {cmd}")
    return json.loads(buf)


def query(port, cmd, **params):
    try:
        return ask(port, cmd, **params)
    except (OSError, ValueError) as exc:
        return {"ok": False, "err": str(exc)}


def reason(reply):
    return reply.get("error") or reply.get("err") or reply


def must(port, cmd, **params):
    reply = query(port, cmd, **params)
    if not reply.get("ok"):
        raise RouteError(f"{cmd} failed: {reason(reply)}")
    return reply


def is_int(value, lo, hi):
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def load_route(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"{path}: cannot read route: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: a route must be a JSON object")
    name = data.get("name", path.stem)
    if not (isinstance(name, str) and NAME.fullmatch(name)):
        raise SystemExit(f"{path}: name {name!r} must be ASCII letters, digits, '-' or '_'")
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 4096:
        raise SystemExit(f"{path}: route needs a steps list of 1..4096 entries")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise SystemExit(f"{path}: steps[{i}] must be an object")
        shot = step.get("shot")
        if not is_int(step.get("frames"), 1, MAX_FRAMES):
            raise SystemExit(f"{path}: steps[{i}].frames must be 1..{MAX_FRAMES}")
        if not is_int(step.get("buttons"), 0, 0xFFFF):
            raise SystemExit(f"{path}: steps[{i}].buttons must be 0..65535")
        if shot is not None and not (isinstance(shot, str) and NAME.fullmatch(shot)):
            raise SystemExit(f"{path}: steps[{i}].shot must be ASCII letters, digits, '-' or '_'")
    card1 = data.get("card1_sha256")
    if card1 is not None and not (isinstance(card1, str) and SHA256.fullmatch(card1)):
        raise SystemExit(f"{path}: card1_sha256 must be 64 lowercase hex digits")
    return name, steps, card1


def port_answers(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
        return True
    except OSError:
        return False


def is_runner_dir(out):
    try:
        return json.loads((out / "result.json").read_text()).get("runner") == RUNNER
    except (OSError, ValueError, AttributeError):
        return False


def prepare_out(out):
    if out.exists() and not out.is_dir():
        raise SystemExit(f"--out {out} is not a directory")
    entries = list(out.iterdir()) if out.exists() else []
    if entries and not is_runner_dir(out):
        raise SystemExit(f"refusing to use {out}: it is not empty and has no result.json "
                         f"written by {RUNNER}")
    for entry in entries:
        if entry.name not in OUTPUTS and not SHOT_FILE.fullmatch(entry.name):
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    (out / "cwd").mkdir(parents=True)
    (out / "memcards").mkdir()


def own_server(log_path, port):
    return f"debug server LISTENING on 127.0.0.1:{port}\n" in log_path.read_text(errors="replace")


def wait_for_boot(proc, port, log_path):
    deadline = time.monotonic() + 60
    while True:
        if proc.poll() is not None:
            raise RouteError(f"runtime exited during startup ({proc.returncode}); see runtime.log")
        text = log_path.read_text(errors="replace")
        if f"debug server bind({port}) FAILED" in text:
            raise RouteError(f"the runtime could not bind 127.0.0.1:{port}")
        banner = BANNER.search(text)
        if own_server(log_path, port) and banner and query(port, "frame").get("ok"):
            return banner.groups()
        if time.monotonic() > deadline:
            raise RouteError("no debug server, boot banner and frame reply within 60 s")
        time.sleep(0.2)


def evidence(port, png=None):
    rec = {"frame": query(port, "frame")}
    if png:
        rec["screenshot"] = query(port, "screenshot", path=str(png))
    for cmd in ("dispatch_stats", "segment_misses", "unknown_dispatch_log"):
        rec[cmd] = query(port, cmd)
    return rec


def play(port, proc, steps, out, result, timeout):
    must(port, "clear_input")
    must(port, "input_route_clear")
    for step in steps:
        must(port, "input_route_append", frames=step["frames"], buttons=step["buttons"])
    start = must(port, "input_route_start")["start_frame"]
    ends, total = [], start
    for step in steps:
        total += step["frames"]
        ends.append(total)
    result.update(start_frame=start, nominal_end_frame=total)

    records = result["records"]
    pending = [i for i, step in enumerate(steps) if step.get("shot")]
    deadline = time.monotonic() + timeout
    status, last_err = None, None
    while True:
        if proc.poll() is not None:
            raise RouteError(f"runtime exited during the route ({proc.returncode}); "
                             "see runtime.log and cwd/psx_last_run_report.json")
        if time.monotonic() > deadline:
            raise RouteError(f"route timed out after {timeout:g} s; last status {status}, "
                             f"last error {last_err}")
        reply = query(port, "input_route_status")
        if not reply.get("ok"):
            last_err = reason(reply)
            time.sleep(0.05)
            continue
        status = reply
        while pending and (status["index"] > pending[0] or not status["active"]):
            i = pending.pop(0)
            png = out / f"{len(records):02d}-{steps[i]['shot']}.png"
            records.append({"step": i, "shot": steps[i]["shot"], "nominal_frame": ends[i],
                            **evidence(port, png)})
        if not status["active"]:
            break
        time.sleep(0.05)
    if status["index"] != len(steps) or status["remaining"] != 0:
        raise RouteError(f"route stopped early: {status}")
    records.append({"step": None, "shot": "final", **evidence(port)})


def stop(proc, port, log_path, failures):
    if proc is None:
        return None
    if proc.poll() is None:
        if own_server(log_path, port):
            query(port, "quit")
            try:
                return proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                failures.append("runtime did not exit within 30 s of quit; killed")
        proc.kill()
    return proc.wait()


def finish(out, result, failures):
    for rec in result["records"]:
        d = rec["dispatch_stats"]
        counts = (d.get("miss_total"), d.get("segment_miss_total"))
        if None in counts:
            failures.append(f"miss counters unavailable at {rec['shot']}")
        elif any(counts):
            failures.append(f"misses at {rec['shot']}: unknown-dispatch {counts[0]}, "
                            f"segment {counts[1]}")
    if result["exit_code"] != 0:
        failures.append(f"runtime exit code {result['exit_code']}")
    result.update(status="FAIL" if failures else "PASS", failures=failures)
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")

    for rec in result["records"]:
        frame = rec["frame"].get("frame")
        late = "" if rec["step"] is None or frame is None else f" ({frame - rec['nominal_frame']:+d})"
        shot = rec.get("screenshot")
        png = "" if shot is None else " png" if shot.get("ok") else f" no png ({reason(shot)})"
        d = rec["dispatch_stats"]
        print(f"{rec['shot']:>16}  frame {frame}{late}  unknown-dispatch "
              f"{d.get('miss_total')} segment {d.get('segment_miss_total')}{png}")
    boot = result.get("boot", {})
    print(f"{result['route']} {result['mode']}: bios_boot={boot.get('bios_boot')} "
          f"image={boot.get('image')} start_frame {result.get('start_frame')} "
          f"exit {result['exit_code']} {result['status']}")
    for f in failures:
        print(f"  FAIL: {f}")


def stop_on_signal(signum, _frame):
    raise SystemExit(f"stopped by {signal.Signals(signum).name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("route", type=Path)
    ap.add_argument("--mode", choices=MODES, default="hle-openbios")
    ap.add_argument("--bios", type=Path, help="SCPH-1001 v2.2 dump (lle-scph1001 only)")
    ap.add_argument("--card1", type=Path,
                    help="raw 128 KiB memory card image for slot 1 (only for routes that "
                         "declare card1_sha256, and required by them)")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--binary", type=Path, help="default: <repo>/build-dev/Omega_Thrust")
    ap.add_argument("--port", type=int, default=4370)
    ap.add_argument("--out", type=Path,
                    help="default: <repo>/.cache/routes/<route name>/<mode>; must be new, "
                         "empty, or an earlier output of this runner")
    ap.add_argument("--timeout", type=float, default=900.0, help="wall seconds for the route")
    args = ap.parse_args()

    repo = args.repo.resolve()
    name, steps, want_card1 = load_route(args.route)
    hle, want_boot, want_image = MODES[args.mode]
    if args.mode == "lle-scph1001" and not (args.bios and args.bios.is_file()):
        raise SystemExit("--mode lle-scph1001 needs --bios naming an existing SCPH-1001 v2.2 dump")
    if args.mode != "lle-scph1001" and args.bios:
        raise SystemExit("--bios applies only to --mode lle-scph1001")
    card1 = None
    if want_card1:
        if not (args.card1 and args.card1.is_file()):
            raise SystemExit(f"{args.route}: needs --card1 naming the memory card image with "
                             f"sha256 {want_card1}")
        need = f"the route needs a {CARD_SIZE}-byte image with sha256 {want_card1}"
        try:
            size = args.card1.stat().st_size
            if size != CARD_SIZE:
                raise SystemExit(f"{args.card1}: {size} bytes; {need}")
            card1 = args.card1.read_bytes()
        except OSError as exc:
            raise SystemExit(f"{args.card1}: cannot read it ({exc.strerror}); {need}")
        got = hashlib.sha256(card1).hexdigest()
        if len(card1) != CARD_SIZE or got != want_card1:
            raise SystemExit(f"{args.card1}: {len(card1)} bytes, sha256 {got}; {need}")
    elif args.card1:
        raise SystemExit("--card1 applies only to routes that declare card1_sha256")
    if not 1 <= args.port <= 65535 or args.timeout <= 0:
        raise SystemExit("--port must be 1..65535 and --timeout positive")
    binary = (args.binary or repo / "build-dev" / "Omega_Thrust").resolve()
    for path in (binary, repo / "game.toml", repo / DISC):
        if not path.is_file():
            raise SystemExit(f"{path}: not found")
    if not os.access(binary, os.X_OK):
        raise SystemExit(f"{binary}: not executable")
    if port_answers(args.port):
        raise SystemExit(f"127.0.0.1:{args.port} already accepts connections; "
                         "stop that process or choose another --port")
    out = (args.out or repo / ".cache" / "routes" / name / args.mode).resolve()
    prepare_out(out)
    if card1 is not None:
        (out / "memcards" / "card1.mcd").write_bytes(card1)

    result = {"runner": RUNNER, "route": name, "mode": args.mode, "card1_sha256": want_card1,
              "status": "running", "records": []}
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    env = dict(os.environ)
    env.pop("APPIMAGE", None)
    env.pop("PSX_BIOS_HLE_KEEP_INTRO", None)
    env["PSX_BIOS_HLE"] = hle
    cmd = [str(binary), "--headless", "--game", str(repo / "game.toml"),
           "--disc", str(repo / DISC), "--memcard-dir", str(out / "memcards"),
           "--debug-port", str(args.port)]
    if args.bios:
        cmd += ["--bios", str(args.bios.resolve())]
    handled = [s for s in (signal.SIGTERM, signal.SIGHUP) if signal.getsignal(s) == signal.SIG_DFL]
    for sig in handled:
        signal.signal(sig, stop_on_signal)

    log_path = out / "runtime.log"
    failures, proc = [], None
    try:
        with open(log_path, "wb") as log:
            try:
                proc = subprocess.Popen(cmd, cwd=out / "cwd", env=env, stdout=log,
                                        stderr=subprocess.STDOUT)
            except OSError as exc:
                raise RouteError(f"cannot start {binary}: {exc}")
        boot, image = wait_for_boot(proc, args.port, log_path)
        result["boot"] = {"bios_boot": boot, "image": image}
        if (boot, image) != (want_boot, want_image):
            raise RouteError(f"runtime booted bios_boot={boot} image={image}; --mode {args.mode} "
                             f"needs bios_boot={want_boot} image={want_image}")
        play(args.port, proc, steps, out, result, args.timeout)
    except RouteError as exc:
        failures.append(str(exc))
    except BaseException as exc:
        failures.append(f"runner stopped: {type(exc).__name__}: {exc}")
        raise
    finally:
        for sig in handled:
            signal.signal(sig, signal.SIG_IGN)
        result["exit_code"] = stop(proc, args.port, log_path, failures)
        finish(out, result, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Play an input route on psx-beetle, the framework's Beetle PSX oracle.

Routes use run_route.py's format. psx-beetle has no input_route_* commands, but
it reads its debug server once per frame, just before it runs the frame, and
`press {buttons, frames}` holds a pad word for exactly that many frames from the
frame about to run. So the driver keeps one connection open and follows the
frame count with `ping`. When a step that is not neutral starts on the next
frame, it sends the press and a `ping` together: Beetle handles both before that
frame, so the ping reports the frame the press starts on, and a press that
starts later than its route frame fails the run. A shot is taken the same way
when its step has ended, so it shows the step's last frame. Step 0 starts on
frame --start (the pad is neutral before it), so a run gets the same input on
the same frames every time. The driver has only the time Beetle takes to run
one frame to answer each ping, about 3 ms on average when unpaced, so a host
that holds it back longer makes an event land a frame late and fails the run;
run it again, or use --paced, which gives every frame 1/59.94 s.

--mode lle-openbios boots the framework's OpenBIOS (psxrecomp/bios/openbios.bin)
and --mode lle-scph1001 the SCPH-1001 dump named by --bios; each image must have
the sha256 in its framework profile (psxrecomp/bios/OpenBIOS.toml or
SCPH1001.toml). Beetle always runs the BIOS itself; it has no HLE boot. With
this US disc it loads scph5501.bin from the directory of the BIOS path it is
given, and without one it quietly boots its own OpenBIOS build, so the driver
links <out>/system/scph5501.bin to the image and fails the run unless Beetle's
log reports that file with the image's SHA-1. Both memory cards start as
formatted blank cards, as psx-runtime formats a missing card. A route that
declares "card1_sha256" needs --card1, as with run_route.py, and slot 1 then
starts as a copy of that image. Beetle reads the cards from its working
directory under the disc's name, "<disc name>.0.mcr" and "<disc name>.1.mcr".
It saves a card the game changed back to that file about two emulated seconds
after the game's last write to it, and on exit if it changed since, so the
files can change during the run; the "dummy.*.mcr" lines in its log come from
a separate check of files it does not load. The driver writes the cards under
those names, and fails the run if psx-beetle writes any other file there,
which would mean it used other cards.

The run fails unless psx-beetle stays up, every press and shot lands on its
frame and the route ends within --timeout. psx-beetle has no quit command, so
the driver then stops it with SIGTERM and expects exit code 0. Linux only: the
driver sets TCP_QUICKACK (see Beetle.reply).
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
import tomllib
from functools import reduce
from operator import xor
from pathlib import Path

sys.dont_write_bytecode = True  # importing run_route must not add __pycache__ to the repository
from run_route import (CARD_SIZE, DISC, SHOT_FILE, RouteError, load_route,  # noqa: E402
                       port_answers, reason)

MODES = {  # BIOS image (lle-scph1001 takes --bios), then the profile with its sha256
    "lle-openbios": ("psxrecomp/bios/openbios.bin", "psxrecomp/bios/OpenBIOS.toml"),
    "lle-scph1001": (None, "psxrecomp/bios/SCPH1001.toml"),
}
DRIVER = "scripts/routes/beetle_route.py"
NEUTRAL = 0xFFFF
FRAME_SIZE = 128
OUTPUTS = ("cwd", "system", "beetle.log", "result.json")
OBTAINED = re.compile(r"Obtained SHA1: ([0-9A-Fa-f]{40})")


def blank_card():
    card = bytearray(b"\xff" * CARD_SIZE)
    for index in range(64):
        frame = bytearray(FRAME_SIZE)
        if index == 0:
            frame[0:2] = b"MC"
        elif index <= 15:  # directory: a free entry with no next block
            frame[0] = 0xA0
            frame[8:10] = b"\xff\xff"
        elif index <= 35:  # broken-frame list: an unused entry
            frame[0:4] = b"\xff" * 4
            frame[8:10] = b"\xff\xff"
        frame[127] = reduce(xor, frame[:127])
        card[index * FRAME_SIZE:(index + 1) * FRAME_SIZE] = frame
    card[63 * FRAME_SIZE:64 * FRAME_SIZE] = card[:FRAME_SIZE]  # the write-test frame
    return bytes(card)


def profile_sha256(path):
    try:
        return tomllib.loads(path.read_text())["program"]["image"]["sha256"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"{path}: cannot read [program.image] sha256 ({exc})")


def read_card1(path, want):
    if not (path and path.is_file()):
        raise SystemExit(f"the route needs --card1 naming the memory card image with sha256 {want}")
    need = f"the route needs a {CARD_SIZE}-byte image with sha256 {want}"
    try:
        size = path.stat().st_size
        if size != CARD_SIZE:
            raise SystemExit(f"{path}: {size} bytes; {need}")
        card = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"{path}: cannot read it ({exc.strerror}); {need}")
    got = hashlib.sha256(card).hexdigest()
    if len(card) != CARD_SIZE or got != want:
        raise SystemExit(f"{path}: {len(card)} bytes, sha256 {got}; {need}")
    return card


def is_driver_dir(out):
    try:
        return json.loads((out / "result.json").read_text()).get("driver") == DRIVER
    except (OSError, ValueError, AttributeError):
        return False


def prepare_out(out):
    if out.exists() and not out.is_dir():
        raise SystemExit(f"--out {out} is not a directory")
    entries = list(out.iterdir()) if out.exists() else []
    if entries and not is_driver_dir(out):
        raise SystemExit(f"refusing to use {out}: it is not empty and has no result.json "
                         f"written by {DRIVER}")
    for entry in entries:
        if entry.name not in OUTPUTS and not SHOT_FILE.fullmatch(entry.name):
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    (out / "cwd").mkdir(parents=True)
    (out / "system").mkdir()


class Beetle:
    """One connection to psx-beetle's debug server, kept open for the whole run."""

    def __init__(self, port, proc):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.proc = proc
        self.buf = b""

    def close(self):
        self.sock.close()

    def gone(self):
        try:
            code = self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            return RouteError("psx-beetle closed the debug connection")
        return RouteError(f"psx-beetle exited during the route ({code}); see beetle.log")

    def send(self, *cmds):
        try:
            self.sock.sendall("".join(json.dumps({"id": i, **cmd}) + "\n"
                                      for i, cmd in enumerate(cmds)).encode())
            return [self.reply(i, cmd) for i, cmd in enumerate(cmds)]
        except ConnectionError:
            raise self.gone()

    def reply(self, i, cmd):
        while b"\n" not in self.buf:
            # psx-beetle sends each reply on its own, and Nagle holds the next one until
            # the last is acknowledged, so acknowledge at once (Linux resets this flag).
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
            chunk = self.sock.recv(1 << 16)
            if not chunk:
                raise self.gone()
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        reply = json.loads(line)
        if reply.get("id") != i:
            raise RouteError(f"reply {reply} does not answer {cmd['cmd']}")
        return reply

    def frame(self):
        reply = self.send({"cmd": "ping"})[0]
        if not reply.get("ok"):
            raise RouteError(f"ping failed: {reason(reply)}")
        return reply["frame"]


def wait_for_boot(proc, port, log_path, link, sha1):
    deadline = time.monotonic() + 60
    while True:
        if proc.poll() is not None:
            raise RouteError(f"psx-beetle exited during startup ({proc.returncode}); see beetle.log")
        text = log_path.read_text(errors="replace")
        if f"[beetle-dbg] bind({port}) failed" in text:
            raise RouteError(f"psx-beetle could not bind 127.0.0.1:{port}")
        if f"[beetle-dbg] listening on 127.0.0.1:{port}\n" in text:
            break
        if time.monotonic() > deadline:
            raise RouteError("no debug server within 60 s")
        time.sleep(0.1)
    obtained = OBTAINED.search(text)
    if not (f"Firmware found but has invalid SHA1: {link}\n" in text and obtained
            and obtained.group(1).lower() == sha1):
        raise RouteError(f"beetle.log does not report {link} with SHA-1 {sha1}; psx-beetle may "
                         "have booted its own OpenBIOS")


def schedule(steps, start):
    events, frame = {}, start
    for i, step in enumerate(steps):
        if step["buttons"] != NEUTRAL:
            events.setdefault(frame, []).append(("press", i))
        frame += step["frames"]
        if step.get("shot"):
            events.setdefault(frame, []).append(("shot", i))
    return events, frame


def play(beetle, proc, steps, start, out, result, timeout):
    events, end = schedule(steps, start)
    result.update(start_frame=start, nominal_end_frame=end)
    deadline = time.monotonic() + timeout
    frame = beetle.frame()
    first = min(events, default=end)
    if frame >= first - 1:
        raise RouteError(f"psx-beetle was at frame {frame} when the driver connected, too late "
                         f"for the route's first input or shot on frame {first}; raise --start")

    def advance(target):
        nonlocal frame
        while frame < target:
            if proc.poll() is not None:
                raise RouteError(f"psx-beetle exited during the route ({proc.returncode}); "
                                 "see beetle.log")
            if time.monotonic() > deadline:
                raise RouteError(f"route timed out after {timeout:g} s at frame {frame}")
            frame = beetle.frame()

    for at in sorted(events):
        kind, i = events[at][0]
        advance(at - 1)
        if frame != at - 1:
            raise RouteError(f"the driver saw frame {frame} but not {at - 1}, too late to land "
                             f"step {i}'s {kind} on frame {at}")
        cmds = []
        for kind, i in events[at]:
            if kind == "press":
                cmds.append({"cmd": "press", "buttons": steps[i]["buttons"],
                             "frames": steps[i]["frames"]})
            else:
                png = out / f"{len(result['records']):02d}-{steps[i]['shot']}.png"
                cmds.append({"cmd": "screenshot", "path": str(png)})
        replies = beetle.send(*cmds, {"cmd": "ping"})
        frame = replies[-1].get("frame")
        for (kind, i), reply in zip(events[at], replies):
            if kind == "press":
                result["presses"].append({"step": i, "nominal_frame": at, "frame": frame})
                if not reply.get("ok"):
                    raise RouteError(f"press for step {i} failed: {reason(reply)}")
            else:
                result["records"].append({"step": i, "shot": steps[i]["shot"],
                                          "nominal_frame": at, "frame": frame,
                                          "screenshot": reply})
        if frame != at:
            kind, i = events[at][0]
            raise RouteError(f"step {i}'s {kind} landed on frame {frame}, route frame {at}")
    advance(end)
    result["end_frame"] = frame


def stop(proc, failures):
    if proc is None:
        return None
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            return proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            failures.append("psx-beetle did not exit within 10 s of SIGTERM; killed")
            proc.kill()
    return proc.wait()


def finish(out, result, failures):
    if result["exit_code"] not in (0, None):
        failures.append(f"psx-beetle exit code {result['exit_code']}")
    result.update(status="FAIL" if failures else "PASS", failures=failures)
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")

    for rec in result["records"]:
        shot = rec["screenshot"]
        png = " png" if shot.get("ok") else f" no png ({reason(shot)})"
        print(f"{rec['shot']:>16}  frame {rec['frame']} ({rec['frame'] - rec['nominal_frame']:+d})"
              f"{png}")
    late = [p for p in result["presses"] if p["frame"] != p["nominal_frame"]]
    print(f"{result['route']} {result['mode']}: start_frame {result.get('start_frame')} "
          f"presses {len(result['presses'])} ({len(late)} off their frame) "
          f"exit {result['exit_code']} {result['status']}")
    for f in failures:
        print(f"  FAIL: {f}")


def stop_on_signal(signum, _frame):
    raise SystemExit(f"stopped by {signal.Signals(signum).name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("route", type=Path)
    ap.add_argument("--mode", choices=MODES, default="lle-openbios")
    ap.add_argument("--bios", type=Path, help="SCPH-1001 v2.2 dump (lle-scph1001 only)")
    ap.add_argument("--card1", type=Path,
                    help="raw 128 KiB memory card image for slot 1 (only for routes that "
                         "declare card1_sha256, and required by them)")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--binary", type=Path, help="default: <repo>/.cache/beetle/build/psx-beetle")
    ap.add_argument("--port", type=int, default=4382)
    ap.add_argument("--start", type=int, default=60, help="frame on which step 0 starts")
    ap.add_argument("--paced", action="store_true",
                    help="run at the console's 59.94 Hz instead of as fast as possible")
    ap.add_argument("--out", type=Path,
                    help="default: <repo>/.cache/beetle-routes/<route name>/<mode>; must be new, "
                         "empty, or an earlier output of this driver")
    ap.add_argument("--timeout", type=float, default=900.0, help="wall seconds for the route")
    args = ap.parse_args()

    repo = args.repo.resolve()
    name, steps, want_card1 = load_route(args.route)
    image, profile = MODES[args.mode]
    if args.mode == "lle-scph1001":
        if not (args.bios and args.bios.is_file()):
            raise SystemExit("--mode lle-scph1001 needs --bios naming an existing SCPH-1001 v2.2 dump")
        bios = args.bios.resolve()
    elif args.bios:
        raise SystemExit("--bios applies only to --mode lle-scph1001")
    else:
        bios = repo / image
    want_bios = profile_sha256(repo / profile)
    try:
        bios_bytes = bios.read_bytes()
    except OSError as exc:
        raise SystemExit(f"{bios}: cannot read it ({exc.strerror})")
    got = hashlib.sha256(bios_bytes).hexdigest()
    if got != want_bios:
        raise SystemExit(f"{bios}: sha256 {got}; {profile} needs {want_bios}")
    card1 = None
    if want_card1:
        card1 = read_card1(args.card1, want_card1)
    elif args.card1:
        raise SystemExit("--card1 applies only to routes that declare card1_sha256")
    if not 1 <= args.port <= 65535 or args.timeout <= 0 or args.start < 1:
        raise SystemExit("--port must be 1..65535, --timeout positive and --start at least 1")
    binary = (args.binary or repo / ".cache" / "beetle" / "build" / "psx-beetle").resolve()
    for path in (binary, repo / DISC):
        if not path.is_file():
            raise SystemExit(f"{path}: not found")
    if not os.access(binary, os.X_OK):
        raise SystemExit(f"{binary}: not executable")
    if port_answers(args.port):
        raise SystemExit(f"127.0.0.1:{args.port} already accepts connections; "
                         "stop that process or choose another --port")
    out = (args.out or repo / ".cache" / "beetle-routes" / name / args.mode).resolve()
    prepare_out(out)
    blank = blank_card()
    # The names Beetle loads and saves (beetle-psx libretro.cpp MDFN_MakeFName, MDFNMKF_SAV)
    cards = [f"{Path(DISC).stem}.{slot}.mcr" for slot in (0, 1)]
    (out / "cwd" / cards[0]).write_bytes(blank if card1 is None else card1)
    (out / "cwd" / cards[1]).write_bytes(blank)
    link = out / "system" / "scph5501.bin"
    link.symlink_to(bios)

    result = {"driver": DRIVER, "route": name, "mode": args.mode,
              "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "bios_sha256": want_bios, "card1_sha256": want_card1, "paced": args.paced,
              "status": "running", "presses": [], "records": []}
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    env = dict(os.environ)
    env.pop("APPIMAGE", None)
    env.update(SDL_VIDEODRIVER="dummy", SDL_RENDER_DRIVER="software")
    if args.paced:
        env.pop("PSX_BEETLE_UNPACED", None)
    else:
        env["PSX_BEETLE_UNPACED"] = "1"
    cmd = [str(binary), str(link), "--disc", str(repo / DISC), "--port", str(args.port)]
    handled = [s for s in (signal.SIGTERM, signal.SIGHUP) if signal.getsignal(s) == signal.SIG_DFL]
    for sig in handled:
        signal.signal(sig, stop_on_signal)

    log_path = out / "beetle.log"
    failures, proc, beetle = [], None, None
    try:
        with open(log_path, "wb") as log:
            try:
                proc = subprocess.Popen(cmd, cwd=out / "cwd", env=env, stdout=log,
                                        stderr=subprocess.STDOUT)
            except OSError as exc:
                raise RouteError(f"cannot start {binary}: {exc}")
        wait_for_boot(proc, args.port, log_path, link, hashlib.sha1(bios_bytes).hexdigest())
        try:
            beetle = Beetle(args.port, proc)
            play(beetle, proc, steps, args.start, out, result, args.timeout)
        except (OSError, ValueError) as exc:
            raise RouteError(f"debug connection failed: {type(exc).__name__}: {exc}")
    except RouteError as exc:
        failures.append(str(exc))
    except BaseException as exc:
        failures.append(f"driver stopped: {type(exc).__name__}: {exc}")
        raise
    finally:
        for sig in handled:
            signal.signal(sig, signal.SIG_IGN)
        if beetle is not None:
            beetle.close()
        result["exit_code"] = stop(proc, failures)
        strays = sorted(set(os.listdir(out / "cwd")) - set(cards))
        if strays:
            failures.append(f"psx-beetle wrote {', '.join(strays)} in cwd/, where only its memory "
                            f"cards {cards[0]} and {cards[1]} belong; it did not use those cards")
        finish(out, result, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

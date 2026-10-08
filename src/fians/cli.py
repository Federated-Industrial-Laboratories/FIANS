# SPDX-License-Identifier: Apache-2.0
"""Configure, render, inspect or stop local speech; write WAV output and return nonzero on failure."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from . import __version__
from .common import chunks, exchange, state_dir
from . import models, playback


def worker_running():
    with (state_dir() / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def lifecycle(operation, *, startup_locked=False):
    if operation == "stop" and not startup_locked:
        with (state_dir() / "start.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return lifecycle(operation, startup_locked=True)
    deadline = time.monotonic() + 120
    while True:
        try:
            reply = exchange({"op": operation}, timeout=1 if operation == "status" else 240)
            break
        except (FileNotFoundError, ConnectionRefusedError):
            if not worker_running():
                return {"ok": True, "state": "stopped"}
            if operation == "status":
                return {"ok": True, "state": "starting"}
            if time.monotonic() >= deadline:
                raise RuntimeError("Worker is still starting; shutdown did not complete.")
            time.sleep(0.2)
        except socket.timeout:
            if operation == "status":
                return {"ok": True, "state": "busy"}
            raise RuntimeError("Worker did not finish its active request; shutdown did not complete.")
    if operation == "stop":
        deadline = time.monotonic() + 15
        while worker_running():
            if time.monotonic() >= deadline:
                raise RuntimeError("Worker acknowledged stop but has not exited.")
            time.sleep(0.1)
        reply["state"] = "stopped"
    return reply


def start():
    state = state_dir()
    with (state / "start.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (state / "worker.lock").open("a") as worker_lock:
            try:
                fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if (state / "worker.sock").exists():
                    return
                raise RuntimeError("Voice worker is starting or stopping; retry shortly.")
        with (state / "worker.log").open("ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "fians.worker"],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True,
            )
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Voice worker failed to start. See {state / 'worker.log'}")
            try:
                exchange({"op": "status"}, timeout=1)
                return
            except (OSError, RuntimeError):
                time.sleep(0.2)
        process.terminate()
        raise RuntimeError(f"Voice worker startup timed out. See {state / 'worker.log'}")


def write_audio(path, data, force):
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".voice-", delete=False) as output:
        temporary = Path(output.name)
        output.write(data)
    try:
        if force:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"FIANS {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("configure", help="Verify and select an existing Nano model directory.")
    setup.add_argument("--model", type=Path, required=True)
    render = sub.add_parser("render", help="Render text to a WAV; read stdin when --text is absent.")
    render.add_argument("--text")
    render.add_argument("--output", "-o", type=Path, required=True)
    render.add_argument("--force", action="store_true")
    render.add_argument("--timeout", type=float, default=240)
    speak = sub.add_parser("speak", help="Queue text for local playback; read stdin when --text is absent.")
    speak.add_argument("--text")
    speak.add_argument("--volume", type=float, default=os.environ.get("FIANS_VOLUME", "0.3"))
    speak.add_argument("--timeout", type=float, default=240)
    sub.add_parser("status", help="Report worker state without starting it.")
    sub.add_parser("stop", help="Release the resident CPU model after the current request.")
    model_parser = sub.add_parser("models", help="Explicitly install or verify the pinned base model.")
    actions = model_parser.add_subparsers(dest="model_action", required=True)
    install = actions.add_parser("install", help="Download pinned files, or register a verified local directory.")
    install.add_argument("--from-dir", type=Path)
    actions.add_parser("verify", help="Verify all configured model files against the manifest.")
    args = parser.parse_args()
    try:
        if args.command == "configure":
            with (state_dir() / "start.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                lifecycle("stop", startup_locked=True)
                print(json.dumps(models.install(args.model)))
        elif args.command == "models":
            if args.model_action == "verify":
                print(json.dumps(models.verify()))
            else:
                with (state_dir() / "start.lock").open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    lifecycle("stop", startup_locked=True)
                    print(json.dumps(models.install(args.from_dir)))
        elif args.command in ("render", "speak"):
            text = args.text if args.text is not None else sys.stdin.read(16001)
            chunks(text)
            if args.command == "render" and args.output.exists() and not args.force:
                raise ValueError("Output exists; select another path or use --force.")
            if not 1 <= args.timeout <= 900:
                raise ValueError("Timeout must be between 1 and 900 seconds.")
            if args.command == "speak":
                playback.check_volume(args.volume)
                with playback.queue():
                    start()
                    reply = exchange({"op": "render", "text": text}, timeout=args.timeout)
                    with tempfile.TemporaryDirectory(prefix="speak-", dir=state_dir()) as temporary:
                        output = Path(temporary) / "voice.wav"
                        write_audio(output, base64.b64decode(reply.pop("audio"), validate=True), False)
                        playback.play(output, args.volume)
                print(json.dumps({"played": True, **reply}))
            else:
                start()
                reply = exchange({"op": "render", "text": text}, timeout=args.timeout)
                write_audio(args.output, base64.b64decode(reply.pop("audio"), validate=True), args.force)
                print(json.dumps({"output": str(args.output), **reply}))
        else:
            print(json.dumps(lifecycle(args.command)))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"fians: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

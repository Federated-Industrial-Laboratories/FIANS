#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Install a pinned, private FIANS runtime without changing system Python."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shlex
import shutil
import subprocess
import sys


SOURCE = Path(__file__).resolve().parents[1]
MARKER = ".fians-install.json"
FILTERS = {"rubberband", "chorus", "afir", "loudnorm"}


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def installation_lock(prefix):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    path = prefix.with_name("." + prefix.name + ".fians-install.lock")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another FIANS installation is using this runtime directory.") from error
        yield
    finally:
        os.close(fd)


def read_marker(prefix):
    if prefix.is_symlink():
        raise ValueError("The runtime prefix must not be a symbolic link.")
    path = prefix / MARKER
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError("The ownership marker must not be a symbolic link.")
    marker = json.loads(path.read_text())
    if marker.get("schema") != 1 or marker.get("prefix") != str(prefix):
        raise ValueError("The FIANS ownership marker does not match this prefix.")
    if not isinstance(marker.get("token"), str) or len(marker["token"]) != 32:
        raise ValueError("The FIANS ownership marker is invalid.")
    return marker


def check_launcher(path, marker):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not marker or marker.get("launcher") != str(path):
        raise ValueError(f"Refusing to replace an unmanaged launcher: {path}")
    if marker.get("launcher_sha256") != digest(path):
        raise ValueError(f"The managed launcher was changed; preserve or remove it first: {path}")


def save_marker(prefix, marker):
    temporary = prefix / (MARKER + ".tmp")
    temporary.write_text(json.dumps(marker, indent=2) + "\n")
    temporary.replace(prefix / MARKER)


def check_platform(python):
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("This runtime lock supports Linux x86_64 only.")
    version = run([python, "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
                  capture_output=True, text=True).stdout.strip()
    if version != "3.12":
        raise ValueError(f"Python 3.12 is required; selected interpreter reports {version}.")
    if not shutil.which("ffmpeg"):
        raise ValueError("FFmpeg is required, including rubberband, chorus, afir and loudnorm filters.")
    filters = run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    available = {line.split()[1] for line in filters.splitlines() if len(line.split()) >= 2}
    missing = FILTERS - available
    if missing:
        raise ValueError("FFmpeg is missing filters: " + ", ".join(sorted(missing)))


def parse_args(argv=None):
    home = Path.home()
    data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=data / "fians/runtime",
                        help="Private runtime directory (default: XDG data directory/fians/runtime)")
    parser.add_argument("--bin-dir", type=Path, default=home / ".local/bin",
                        help="Launcher directory (default: ~/.local/bin)")
    parser.add_argument("--python", default="python3.12", help="Python 3.12 interpreter")
    parser.add_argument("--model-from", type=Path, help="Import verified existing model files")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--update", action="store_true", help="Update an existing managed runtime")
    action.add_argument("--uninstall", action="store_true",
                        help="Remove the managed runtime and launcher; retain data and model files")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    raw_prefix = args.prefix.expanduser().absolute()
    if raw_prefix.is_symlink():
        raise ValueError("The runtime prefix must not be a symbolic link.")
    prefix = raw_prefix.resolve()
    launcher = args.bin_dir.expanduser().resolve() / "fians"
    existing = read_marker(prefix) if args.update or args.uninstall else None
    default_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "fians"
    saved_data = existing.get("data", default_data) if existing else default_data
    data = Path(os.environ.get("FIANS_HOME", saved_data)).expanduser().resolve()
    if prefix in {Path("/"), Path.home(), data} or prefix in SOURCE.parents:
        raise ValueError("The runtime must use its own directory, separate from source and data.")
    if SOURCE == prefix or prefix in launcher.parents or prefix in data.parents:
        raise ValueError("The launcher and data must remain outside the runtime directory.")
    if not args.uninstall:
        data.mkdir(mode=0o700, parents=True, exist_ok=True)
        if data.stat().st_mode & 0o077:
            raise ValueError(f"The FIANS data directory must be private (mode 0700): {data}")
    with installation_lock(prefix):
        return install_runtime(args, prefix, launcher, data)


def install_runtime(args, prefix, launcher, data):
    marker = read_marker(prefix)
    if args.update or args.uninstall:
        if not marker:
            raise ValueError("No managed FIANS installation exists at this prefix.")
        if marker.get("launcher") != str(launcher):
            raise ValueError("Use the same --bin-dir as the existing installation.")
    elif marker or (prefix.exists() and any(prefix.iterdir())):
        raise ValueError("The runtime directory is not empty. Use --update for a managed installation.")
    check_launcher(launcher, marker)
    environment = dict(os.environ, FIANS_HOME=str(data))
    if marker and marker.get("state") == "ready" and (args.update or args.uninstall):
        homes = {str(data), marker.get("data", str(data))}
        for home in sorted(homes):
            run([prefix / "bin/fians", "stop"], env=dict(environment, FIANS_HOME=home))
    if args.uninstall:
        if launcher.exists():
            launcher.unlink()
        shutil.rmtree(prefix)
        print(f"Removed the FIANS runtime. Data and models remain in {data}")
        return 0

    check_platform(args.python)
    prefix.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = marker or {"schema": 1, "prefix": str(prefix), "launcher": str(launcher),
                        "token": secrets.token_hex(16)}
    marker["data"] = str(data)
    marker["state"] = "installing"
    save_marker(prefix, marker)
    run([args.python, "-m", "venv", prefix])
    os.environ["PATH"] = str(prefix / "bin") + os.pathsep + os.environ.get("PATH", "")
    python = prefix / "bin/python"
    pip = [python, "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check"]
    run(pip + ["--require-hashes", "--no-deps", "-r", SOURCE / "packaging/bootstrap.lock"])
    run(pip + ["--require-hashes", "--no-deps", "--no-build-isolation", "-r",
               SOURCE / "packaging/runtime-linux-x86_64-py312.lock"])
    run(pip + ["--no-deps", "--no-build-isolation", "--force-reinstall", SOURCE])
    run([python, "-m", "pip", "check"])
    run([python, "-c", "import torch, torchaudio; from chatterbox.tts_turbo import ChatterboxTurboTTS; "
         "import fians; assert torch.__version__ == torchaudio.__version__ == '2.6.0+cpu'; "
         "assert torch.version.cuda is None; print('FIANS CPU runtime imports passed.')"])
    if args.model_from:
        run([prefix / "bin/fians", "models", "install", "--from-dir", args.model_from.resolve()],
            env=environment)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    body = ("#!/bin/sh\n# FIANS managed launcher: " + marker["token"] + "\n"
            'if [ -z "${FIANS_HOME:-}" ]; then\n  FIANS_HOME=' + shlex.quote(str(data)) + "\nfi\n"
            "export FIANS_HOME\n"
            "exec " + shlex.quote(str(prefix / "bin/fians")) + ' "$@"\n')
    temporary = launcher.with_name(".fians-launcher-" + marker["token"])
    temporary.write_text(body)
    temporary.chmod(0o755)
    temporary.replace(launcher)
    marker.update(state="ready", launcher_sha256=digest(launcher))
    save_marker(prefix, marker)
    print(f"Installed FIANS: {launcher}")
    if not args.model_from:
        print(f"Install model files explicitly: {shlex.quote(str(launcher))} models install")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"FIANS installation failed: {error}", file=sys.stderr)
        sys.exit(1)

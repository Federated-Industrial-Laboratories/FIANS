# SPDX-License-Identifier: Apache-2.0
"""Own private paths, bounded text and local IPC; raise on invalid inputs."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile

LIMIT = 2000


def assets():
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "models/manifest.json").is_file():
        return checkout
    installed = Path(sys.prefix) / "share/fians"
    if not (installed / "models/manifest.json").is_file():
        raise ValueError("FIANS voice assets are missing; reinstall the package.")
    return installed


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError(f"Directory must be owned by this user and private: {path}")
    return path


def home_dir():
    default = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "fians"
    return private_dir(Path(os.environ.get("FIANS_HOME", str(default))).absolute())


def state_dir():
    key = hashlib.sha256(str(home_dir()).encode()).hexdigest()[:12]
    return private_dir(Path(f"/tmp/fians-{os.getuid()}-{key}"))


def config():
    manifest = json.loads((assets() / "models/manifest.json").read_text())
    path = home_dir() / "config.json"
    if path.exists():
        data = json.loads(path.read_text())
        if not isinstance(data.get("model"), str) or not Path(data["model"]).is_absolute():
            raise ValueError("Configured model path must be absolute.")
        return data
    return {"model": str(home_dir() / "models" / manifest["revision"])}


def save_config(data):
    with tempfile.NamedTemporaryFile(mode="w", dir=home_dir(), prefix=".config-", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, home_dir() / "config.json")
    finally:
        temporary.unlink(missing_ok=True)


def chunks(text):
    if not isinstance(text, str):
        raise ValueError("Speech must be text.")
    text = " ".join(text.split())
    if not text or len(text) > LIMIT:
        raise ValueError(f"Supply 1-{LIMIT} characters of speech.")
    result = []
    while len(text) > 240:
        endings = list(re.finditer(r"[.!?;:]\s+", text[:241]))
        cut = endings[-1].end() if endings else text.rfind(" ", 0, 241)
        if cut <= 0:
            raise ValueError("A word exceeds the 240-character segment limit.")
        result.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        result.append(text)
    return result


def exchange(request, timeout=240):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(state_dir() / "worker.sock"))
        connection.sendall(json.dumps(request, ensure_ascii=False).encode() + b"\n")
        with connection.makefile("rb") as stream:
            line = stream.readline(32 * 1024 * 1024)
        if not line.endswith(b"\n"):
            raise RuntimeError("Voice worker closed without a complete response.")
        reply = json.loads(line)
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error", "Voice worker failed."))
        return reply

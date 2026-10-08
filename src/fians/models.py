# SPDX-License-Identifier: Apache-2.0
"""Install or verify pinned model files; perform network I/O only on explicit installation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from .common import assets, config, home_dir, save_config


def manifest():
    data = json.loads((assets() / "models/manifest.json").read_text())
    if len(data["revision"]) != 40 or not all(c in "0123456789abcdef" for c in data["revision"]):
        raise ValueError("Model revision must be a full commit hash.")
    for name, info in data["files"].items():
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Model manifest has an unsafe filename.")
        if info["size"] <= 0 or len(info["sha256"]) != 64:
            raise ValueError("Model manifest has invalid file metadata.")
    return data


def valid(path, info):
    if not path.is_file() or path.stat().st_size != info["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == info["sha256"]


def verify(directory=None):
    directory = Path(directory or config()["model"])
    data = manifest()
    # Upstream loaders can auto-discover unlisted tokenizer/configuration files.
    metadata = {".cache", ".git", ".gitattributes"}
    if directory.is_dir():
        extra = sorted(path.name for path in directory.iterdir()
                       if path.name not in data["files"] and path.name not in metadata)
        if extra:
            raise ValueError("Unverified model directory entries: " + ", ".join(extra)
                             + ". Use only the selected Nano file set.")
    failed = [name for name, info in data["files"].items() if not valid(directory / name, info)]
    if failed:
        raise ValueError("Missing or invalid model files: " + ", ".join(failed) + ". Run fians models install.")
    return {"repository": data["repository"], "revision": data["revision"],
            "directory": str(directory), "files_verified": len(data["files"])}


def install(source=None):
    if source is not None:
        directory = Path(source).resolve()
        result = verify(directory)
        save_config({"model": str(directory)})
        return {**result, "downloaded": 0}
    data = manifest()
    directory = home_dir() / "models" / data["revision"]
    directory.mkdir(parents=True, exist_ok=True)
    count = 0
    for name, info in data["files"].items():
        target = directory / name
        if valid(target, info):
            continue
        url = ("https://huggingface.co/" + data["repository"] + "/resolve/" + data["revision"]
               + "/" + urllib.parse.quote(name, safe=""))
        request = urllib.request.Request(url, headers={"User-Agent": "FIANS/0.1.0"})
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".download-", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                digest = hashlib.sha256()
                total = 0
                with urllib.request.urlopen(request, timeout=60) as response:
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > info["size"]:
                            raise ValueError(f"Download exceeded the expected size: {name}")
                        stream.write(block)
                        digest.update(block)
                if total != info["size"] or digest.hexdigest() != info["sha256"]:
                    raise ValueError(f"Model download failed verification: {name}")
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        count += 1
    result = verify(directory)
    save_config({"model": str(directory)})
    return {**result, "downloaded": count}

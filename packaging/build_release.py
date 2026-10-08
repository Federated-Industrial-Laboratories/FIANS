#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a source archive and wheel without model weights or local state."""

import argparse
import gzip
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]
FILES = {"README.md", "LICENSE", "NOTICE", "NOTICE.md", "CHANGELOG.md", "CONTRIBUTING.md",
         "SECURITY.md", "CODE_OF_CONDUCT.md", "pyproject.toml", "MANIFEST.in", "install.sh",
         ".gitignore", ".gitattributes"}
DIRECTORIES = {"src", "voices", "docs", "assets", "packaging", "tests", "notices", ".github"}
EXCLUDED = {"__pycache__", ".venv", "venv", ".git", ".pytest_cache", ".mypy_cache"}
WEIGHT_SUFFIXES = {".safetensors", ".pt", ".pth", ".onnx", ".ckpt", ".bin"}


def source_files(root=ROOT):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED or part.endswith(".egg-info") for part in relative.parts):
            continue
        if (relative.parts[0] not in DIRECTORIES and str(relative) not in FILES
                and str(relative) != "models/manifest.json"):
            continue
        if path.is_symlink():
            raise ValueError(f"Source distributions must not contain symbolic links: {relative}")
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.suffix in WEIGHT_SUFFIXES or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError(f"Large model files do not belong in the source distribution: {relative}")
        yield path, relative


def source_archive(destination, version, epoch, root=ROOT):
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path, relative in source_files(root):
                    content = path.read_bytes()
                    info = tarfile.TarInfo(f"fians-{version}/{relative.as_posix()}")
                    info.size = len(content)
                    info.mtime = epoch
                    info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                    archive.addfile(info, io.BytesIO(content))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Empty output directory")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("The output directory must be empty.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800"))
    if epoch < 315532800:
        parser.error("SOURCE_DATE_EPOCH must be 315532800 or later for wheel timestamps.")
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = str(epoch)
    with tempfile.TemporaryDirectory(prefix="fians-release-") as temporary:
        staging = Path(temporary)
        # Build from the same selected files as the source archive.
        selected = staging / "source"
        for path, relative in source_files():
            target = selected / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            target.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)
        subprocess.run([os.sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                        "--no-cache-dir", "--wheel-dir", str(staging / "wheel"), str(selected)],
                       check=True, env=environment)
        wheels = list((staging / "wheel").glob("fians-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("Expected exactly one FIANS wheel.")
        shutil.copyfile(wheels[0], output / wheels[0].name)
        source_archive(output / f"fians-{version}.tar.gz", version, epoch, selected)
    sums = []
    for path in sorted(output.iterdir()):
        sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"Built source, wheel and SHA256SUMS in {output}")


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
"""Queue local WAV playback at an explicit volume; return nonzero on player failure."""
from contextlib import contextmanager
import fcntl
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from .common import state_dir


@contextmanager
def queue():
    with (state_dir() / "playback.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def check_volume(volume):
    if not math.isfinite(volume) or not 0 <= volume <= 1:
        raise ValueError("Volume must be between 0 and 1.")


def play(path, volume):
    check_volume(volume)
    if player := shutil.which("pw-play"):
        command = [player, "--volume", str(volume), str(path)]
    elif player := shutil.which("paplay"):
        command = [player, "--volume", str(round(volume * 65536)), str(path)]
    elif player := shutil.which("aplay"):
        with tempfile.TemporaryDirectory(prefix="play-", dir=state_dir()) as temporary:
            adjusted = Path(temporary) / "voice.wav"
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
                            "-i", str(path), "-af", f"volume={volume}", str(adjusted)], check=True, timeout=45)
            subprocess.run([player, str(adjusted)], check=True, timeout=240)
        return
    else:
        raise RuntimeError("No audio player found; install pw-play, paplay or aplay, or use fians render.")
    subprocess.run(command, check=True, timeout=240)

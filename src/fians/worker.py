# SPDX-License-Identifier: Apache-2.0
"""Serve local CPU speech through a private Unix socket; release the model after five idle minutes."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import tempfile

from .common import assets, chunks, config, state_dir
from .models import verify


def main():
    os.umask(0o077)
    state = state_dir()
    lock = (state / "worker.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ[name] = "4"
    os.environ.update(HF_HOME=str(state / "hf-cache"), HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                      HF_HUB_DISABLE_TELEMETRY="1", NUMBA_CACHE_DIR=str(state / "numba-cache"))
    import numpy as np
    import soundfile as sf
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    reference = assets() / "voices/praetor/reference.wav"
    preset = assets() / "voices/praetor/preset.json"
    fingerprint = hashlib.sha256(reference.read_bytes() + preset.read_bytes()).hexdigest()
    verify()
    with torch.inference_mode():
        model = ChatterboxTurboTTS.from_local(config()["model"], device="cpu", nano=True)
        model.prepare_conditionals(str(reference), exaggeration=0.0, norm_loudness=True)

    address = state / "worker.sock"
    address.unlink(missing_ok=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(address))
            server.listen(8)
            server.settimeout(300)
            print("Praetor voice ready; CPU, four threads, five-minute idle timeout.", flush=True)
            while True:
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    return
                stop = False
                with connection:
                    connection.settimeout(10)
                    try:
                        with connection.makefile("rb") as stream:
                            line = stream.readline(16384)
                        if not line.endswith(b"\n"):
                            raise ValueError("Request is too large or incomplete.")
                        request = json.loads(line)
                        op = request.get("op")
                        if op in ("status", "stop"):
                            stop = op == "stop"
                            reply = {"ok": True, "state": "stopping" if stop else "ready",
                                     "pid": os.getpid(), "voice_sha256": fingerprint}
                        elif op == "render":
                            pieces = chunks(request["text"])
                            if hashlib.sha256(reference.read_bytes() + preset.read_bytes()).hexdigest() != fingerprint:
                                raise ValueError("Voice assets changed; stop the worker before rendering again.")
                            audio = []
                            for piece in pieces:
                                random.seed(42)
                                np.random.seed(42)
                                torch.manual_seed(42)
                                with torch.inference_mode():
                                    samples = model.generate(piece).squeeze().cpu().numpy()
                                if not samples.size or not np.isfinite(samples).all():
                                    raise ValueError("Speech output is empty or non-finite.")
                                if audio:
                                    audio.append(np.zeros(round(model.sr * 0.15)))
                                audio.append(samples)
                            with tempfile.TemporaryDirectory(prefix="render-", dir=state) as temporary:
                                dry, treated = Path(temporary) / "dry.wav", Path(temporary) / "voice.wav"
                                sf.write(dry, np.concatenate(audio), model.sr, subtype="PCM_16")
                                subprocess.run([sys.executable, "-m", "fians.effects", "--input", str(dry),
                                                "--output", str(treated), "--preset", str(preset)],
                                               check=True, stdout=subprocess.DEVNULL, timeout=45)
                                info = json.loads(treated.with_suffix(".json").read_text())["audio"]
                                reply = {"ok": True, "audio": base64.b64encode(treated.read_bytes()).decode(),
                                         "voice_sha256": fingerprint, "segments": len(pieces), "format": info}
                        else:
                            raise ValueError("Unknown voice request.")
                    except Exception as error:
                        reply = {"ok": False, "error": str(error)}
                    try:
                        connection.sendall(json.dumps(reply).encode() + b"\n")
                    except (BrokenPipeError, ConnectionResetError, socket.timeout):
                        pass
                if stop:
                    return
    finally:
        address.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Apply a saved voice treatment; inputs: WAV and JSON preset; outputs: WAV and receipt; exit 0 on success.
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import wave

import numpy as np

from .common import assets


def reverb_impulse(preset, rate):
    """Build a deterministic, diffuse impulse with a separate reflection onset."""
    count = round(preset["reverb_tail_seconds"] * rate)
    delay = round(preset["reverb_predelay_ms"] * rate / 1000)
    time = np.arange(count) / rate
    noise = np.random.default_rng(42).standard_normal(count)
    frequencies = np.fft.rfftfreq(count, 1 / rate)
    colour = (frequencies / np.sqrt(frequencies ** 2 + 260 ** 2)
              / np.sqrt(1 + (frequencies / preset["reverb_lowpass_hz"]) ** 6))
    diffuse = np.fft.irfft(np.fft.rfft(noise) * colour, n=count)
    diffuse *= np.exp(-np.log(1000) * time / preset["reverb_decay_seconds"])
    diffuse *= 1 - np.exp(-time / 0.012)
    diffuse *= np.minimum(1, np.maximum(0, (count - 1 - np.arange(count)) / (0.08 * rate)))
    diffuse /= np.linalg.norm(diffuse)
    impulse = np.zeros(count)
    impulse[delay:] = diffuse[:count - delay]
    for offset, gain in ((0.007, 0.12), (0.023, -0.09), (0.047, 0.07), (0.081, -0.05)):
        impulse[delay + round(offset * rate)] += gain
    return impulse.astype("<f4")


def wav_info(path):
    with wave.open(str(path)) as stream:
        info = {"sample_rate": stream.getframerate(), "channels": stream.getnchannels(),
                "frames": stream.getnframes(), "sample_width": stream.getsampwidth()}
        data = stream.readframes(info["frames"])
    if info["sample_width"] != 2 or not info["frames"]:
        raise ValueError("Expected a nonempty PCM16 WAV.")
    if len(data) != info["frames"] * info["channels"] * 2:
        raise ValueError("Audio has an incomplete frame payload.")
    samples = np.frombuffer(data, dtype="<i2").astype(np.float64) / 32768.0
    info.update(seconds=info["frames"] / info["sample_rate"],
                peak=float(np.abs(samples).max()), rms=float(np.sqrt(np.mean(samples ** 2))),
                clipped_samples=int(np.count_nonzero(np.abs(samples) >= 32767 / 32768)))
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preset", type=Path, default=assets() / "voices/praetor/preset.json")
    parser.add_argument("--semitones", type=float, help="Override the duplicate track pitch.")
    parser.add_argument("--dry", action="store_true", help="Create a loudness-matched dry audition.")
    args = parser.parse_args()
    receipt_path = args.output.with_suffix(".json")
    if args.output.exists() or receipt_path.exists():
        parser.error("Output already exists; choose a new filename to preserve it.")
    preset = json.loads(args.preset.read_text())
    if args.semitones is not None:
        preset["duplicate_semitones"] = args.semitones
    for key, value in preset.items():
        if key != "description" and (not isinstance(value, (float, int)) or not math.isfinite(value)):
            parser.error(f"Preset value {key} must be a finite number.")
    if not -12 <= preset["duplicate_semitones"] <= 12:
        parser.error("Duplicate pitch must be within one octave.")
    reverb = not args.dry and preset.get("reverb_gain", 0) > 0
    if reverb and not (0 < preset["reverb_decay_seconds"] <= preset["reverb_tail_seconds"] <= 10
                       and 0 <= preset["reverb_predelay_ms"] <= 100
                       and preset["reverb_tail_seconds"] > 0.2
                       and preset["reverb_lowpass_hz"] > 0):
        parser.error("Reverb requires a positive decay, sufficient tail, and 0-100 ms predelay.")
    source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    original = wav_info(args.input)
    tail_frames = round(preset["reverb_tail_seconds"] * original["sample_rate"]) if reverb else 0
    output_frames = original["frames"] + tail_frames
    pitch = 2 ** (preset["duplicate_semitones"] / 12)
    normalise = f"loudnorm=I={preset['output_lufs']}:TP={preset['true_peak_db']}:LRA=11"
    finish = (f"{normalise},aresample={original['sample_rate']},apad,"
              f"atrim=end_sample={output_frames}[out]")
    modulation = ""
    if not args.dry and preset.get("chorus_gain", 0) > 0:
        modulation = (
            f"chorus=in_gain=1:out_gain=0.8:delays=18|29:"
            f"decays={preset['chorus_gain']}|{preset['chorus_gain'] * 0.8}:"
            "speeds=0.29|0.43:depths=0.65|0.9,"
        )
    space = ""
    if reverb:
        space = (
            f"apad=pad_len={tail_frames},asplit=2[direct][send];"
            "[send][1:a]afir=gtype=none:dry=1:wet=1:irfmt=mono[room];"
            f"[room]volume={preset['reverb_gain']}[wet];"
            "[direct][wet]amix=inputs=2:duration=longest:normalize=0,"
        )
    if args.dry:
        graph = f"[0:a]{finish}"
    else:
        graph = (
            f"[0:a]highpass=f={preset['highpass_hz']},lowpass=f={preset['lowpass_hz']},"
            f"equalizer=f={preset['body_eq_hz']}:t=q:w=0.8:g={preset['body_eq_db']},"
            f"equalizer=f={preset['presence_eq_hz']}:t=q:w=0.9:g={preset['presence_eq_db']},"
            "asplit=3[body][double][robot];"
            f"[body]volume={preset['dry_gain']}[a];"
            f"[double]rubberband=tempo=1:pitch={pitch:.12f}:formant=shifted:"
            f"pitchq=quality:transients=smooth,volume={preset['duplicate_gain']}[b];"
            f"[robot]aeval='val(0)*sin(2*PI*{preset['robot_frequency_hz']}*t)',"
            f"volume={preset['robot_gain']}[c];"
            "[a][b][c]amix=inputs=3:duration=longest:normalize=0,"
            f"volume={preset['distortion_drive']},asoftclip=type=tanh:"
            f"threshold={preset['distortion_threshold']}:output=0.9:oversample=2,"
            + modulation + space + finish
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    impulse_hash = None
    with tempfile.TemporaryDirectory(prefix="voice-effects-") as temporary:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(args.input)]
        if reverb:
            impulse = reverb_impulse(preset, original["sample_rate"]).tobytes()
            impulse_hash = hashlib.sha256(impulse).hexdigest()
            impulse_path = Path(temporary) / "reverb.f32"
            impulse_path.write_bytes(impulse)
            command += ["-f", "f32le", "-ar", str(original["sample_rate"]), "-ac", "1", "-i", str(impulse_path)]
        command += ["-filter_complex_threads", "2", "-filter_complex", graph, "-map", "[out]",
                    "-ar", str(original["sample_rate"]), "-ac", "1", "-c:a", "pcm_s16le", str(args.output)]
        subprocess.run(command, check=True)
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != source_hash:
        raise ValueError("Input changed while the effect was being rendered.")
    rendered = wav_info(args.output)
    if rendered["rms"] <= 1e-5 or rendered["clipped_samples"]:
        raise ValueError("Rendered audio is silent or clipped.")
    if rendered["frames"] != output_frames:
        raise ValueError("Treatment unexpectedly changed the audio duration.")
    receipt = {"input": str(args.input), "input_sha256": source_hash,
               "output": str(args.output), "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
               "mode": "dry audition" if args.dry else "voice treatment",
               "preset": preset, "duplicate_pitch_ratio": pitch,
               "reverb_impulse_sha256": impulse_hash, "tail_frames": tail_frames,
               "filter_graph": graph, "audio": rendered}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "mode": receipt["mode"], "audio": rendered}))


if __name__ == "__main__":
    main()

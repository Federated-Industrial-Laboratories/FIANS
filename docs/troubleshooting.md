# Troubleshooting

[Documentation](README.md) | [Installation](install.md) | [Operation](operations.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Installation and weights](#installation-and-weights)
- [Startup and requests](#startup-and-requests)
- [Playback and voice quality](#playback-and-voice-quality)
- [Useful diagnostics](#useful-diagnostics)

## Installation and weights

| Symptom | Action |
| --- | --- |
| Python version or virtual environment check fails | Supply Python 3.12 with `--python`; install its `venv` support through the operating system. |
| FFmpeg filter is missing | Install a build with `rubberband`, `chorus`, `afir` and `loudnorm`. |
| Installer preserves an existing prefix or launcher | Use an unused destination, or `--update` for a managed FIANS runtime. |
| No model is configured | Run `fians models install` or register an existing directory with `--from-dir`. |
| Model verification fails | Compare the named file with the pinned manifest; restore or reinstall the correct file. |
| Weights were moved | Stop the worker, register the new directory, then run `models verify`. |

Do not resolve a hash failure by editing the expected digest to match an unknown
download. The hashes and revision select the supported base model together.

## Startup and requests

```sh
fians status
fians models verify
```

The first request loads the model and can take longer than later requests.
`starting` indicates startup is in progress; `busy` indicates that status could not
complete while the worker was occupied. `ready` means it answered a status request.

If a request times out, let the active generation finish or use `fians stop` to
wait for shutdown. Do not issue repeated renders while the original is still
running. Increase `--timeout` within its 1 to 900 second range for longer text.

For a startup failure, inspect the worker diagnostic log at the path in the error.
Missing Python packages, unavailable model files and FFmpeg failures require
different fixes. A stopped worker after five idle minutes is expected behavior.

If voice files changed, stop and restart the worker. If a request is rejected for
length, shorten the text or split it into separate application messages. A single
word or identifier cannot exceed the 240-character segment limit.

## Playback and voice quality

Render a WAV first to distinguish synthesis from playback:

```sh
fians render --text 'The system is ready.' --output diagnostic.wav
```

If the WAV exists and decodes but playback fails, check the current desktop audio
session, output device and volume. A headless machine can render without playing.
The CLI does not select or provision an audio device.

For unclear words, shorten sentences and spell out abbreviations or numbers.
Generative speech is not guaranteed to reproduce every input word exactly.
The reference conditions the underlying voice; reverb and modulation come from
the preset. Adding those effects to the reference is not the supported way to
strengthen the final treatment.

## Useful diagnostics

Include the FIANS version, Python version, operating system, failed command,
exit status and relevant error when reporting a problem. Include the voice
fingerprint and model verification result for a voice or weight issue.

Keep private narration, local account paths and unrelated log contents out of
reports. Reproduce the issue with a short non-sensitive sentence where possible.
See [security reporting](../SECURITY.md) for vulnerabilities.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Architecture](architecture.md) | [Next: Packaging and releases](releases.md)

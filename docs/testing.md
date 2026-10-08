# Testing

[Documentation](README.md) | [Contributing](../CONTRIBUTING.md) | [Releases](releases.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Application contracts](#application-contracts)
- [Installed runtime](#installed-runtime)
- [Voice checks](#voice-checks)
- [Continuous integration](#continuous-integration)

## Application contracts

From the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

These checks use the standard library and do not download or load Nano weights.
They exercise application boundaries such as text validation, output preservation,
model verification and worker lifecycle. They do not establish audible voice
quality or compatibility of the full inference dependency set.

Run a focused regression for a changed contract, then the applicable suite before
delivery. Add checks for meaningful behavior and actual defects. Changes confined
to prose or static artwork need link and rendering checks rather than inference.

## Installed runtime

Version 0.1.0 was checked on Linux x86-64 with Python 3.12 and the locked CPU
Torch/TorchAudio 2.6.0 pair. Clean installation, managed update, dependency
consistency, source-independent invocation, short and segmented speech, desktop
playback, output preservation and worker shutdown passed. This does not establish
support for other platforms or Python versions.

Use a separate managed installation and application home for qualification. Check
the complete dependency installation, then register the pinned local model files.
Run dependency consistency checks with the installed interpreter.

```sh
fians --version
fians models verify
fians render --text 'The connection is secure.' --output short.wav
fians status
fians speak --text 'The next report is ready.' --volume 0.3
fians stop
```

Also render a paragraph long enough to use multiple segments. Confirm mono 24 kHz
PCM16 output, nonempty finite audio, preserved existing output without `--force`,
and clean worker shutdown. Check source-independent operation after installation.

Cold startup, active generation and idle shutdown are different lifecycle states.
A shutdown regression should cover the state affected by the change. Keep real
inference runs bounded and release the worker after each qualification sequence.

## Voice checks

Listen to a short announcement and a longer passage. Check speaker resemblance,
intelligibility, missing or repeated words, doubling balance and reverb clarity.
Waveform or timing statistics alone cannot establish these qualities.

Preserve model, runtime and voice identities with any comparison. Output can change
with numerical libraries even when the text and seed are fixed. Do not describe
a different dependency environment as reproducing a previously checked waveform
without comparing the actual output.

## Continuous integration

The [Checks workflow](../.github/workflows/checks.yml) runs lightweight application
contracts and documentation checks. It does not download model weights, exercise
desktop playback or publish artifacts. A passing CI run does not establish the
full installed audio workflow.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Packaging and releases](releases.md) | [Next: Dependencies](dependencies.md)

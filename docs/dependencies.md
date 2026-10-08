# Dependencies and notices

[Documentation](README.md) | [Model storage](models.md) | [NOTICE](../NOTICE)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Pinned components](#pinned-components)
- [Runtime and system tools](#runtime-and-system-tools)
- [Notices](#notices)

## Pinned components

| Component | Revision | Purpose |
| --- | --- | --- |
| [Chatterbox](https://github.com/resemble-ai/chatterbox/tree/5de7a54aa4e5e2baadb0182dde554908b48b85c2) | `5de7a54aa4e5e2baadb0182dde554908b48b85c2` | Local Nano speech generation. |
| [Perth](https://github.com/resemble-ai/Perth/tree/ff1c8ac55a976971245cdd53c18d6131ca00d993) | `ff1c8ac55a976971245cdd53c18d6131ca00d993` | Upstream audio watermarking. |
| [Chatterbox Nano weights](https://huggingface.co/ResembleAI/chatterbox-nano/tree/71ccd1d0081b430592cea481f4307e764e07bc64) | `71ccd1d0081b430592cea481f4307e764e07bc64` | Unchanged base-model parameters and tokenizer files. |

The model manifest records the selected weight files and their hashes. The
installation dependency specification fixes the runtime choices. Dependency
updates require an installed speech check in addition to application contracts.

The retained upstream model card describes the wider Chatterbox family. Use
[installation](install.md) and [operation](operations.md) for FIANS requirements
and supported commands. Upstream performance figures are not FIANS measurements.

## Runtime and system tools

Python 3.12 hosts the application and model. The installer provides a private CPU
runtime with PyTorch and TorchAudio 2.6.0. The hashed specifications in
[packaging](../packaging/) pin the bootstrap and runtime dependencies. Other
inference dependencies include numerical, audio, tokenizer and model-loading libraries.

FFmpeg performs the sound treatment. Its build must provide Rubber Band pitch
shifting, chorus, convolution and loudness filters. FFmpeg and Rubber Band remain
separately installed system dependencies with their own applicable licences.
Playback uses the first available player: `pw-play`, `paplay`, then `aplay`.
It requires an accessible audio session or ALSA output for the current user.

The installed runtime is separate from the model cache. No hosted synthesis SDK
or API key is required to render speech.

## Notices

FIANS application code and its authored effect preset use Apache-2.0. Chatterbox
and Perth retain their MIT notices. The retained Nano model card declares MIT
for the weights. Other dependencies keep their own licences.

See the [application licence](../LICENSE), [NOTICE](../NOTICE) and the retained
component texts under [notices](../notices/). The supplied synthetic reference is
identified in [Praetor metadata](../voices/praetor/voice.json). It is conditioning
audio, not a newly trained checkpoint or a built-in upstream speaker.

The Perth watermark remains enabled. Distribution packages must preserve the
component notices that apply to their contents.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Testing](testing.md) | [Documentation index](README.md)

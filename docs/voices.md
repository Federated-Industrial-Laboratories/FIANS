# Praetor voice

[Documentation](README.md) | [Model storage](models.md) | [Dependencies](dependencies.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Voice profile](#voice-profile)
- [Sound treatment](#sound-treatment)
- [Changing the treatment](#changing-the-treatment)
- [Voice and model identity](#voice-and-model-identity)

## Voice profile

Praetor is a measured synthetic English voice with a restrained, spacious sound.
Its profile combines a clean 10.24-second reference with an independent effects
preset. Chatterbox Nano uses the reference to condition the generated speaker.

| File | Purpose |
| --- | --- |
| [reference.wav](../voices/praetor/reference.wav) | Clean mono reference supplied with the voice profile. |
| [preset.json](../voices/praetor/preset.json) | Pitch, chorus, equalization, distortion and reverb settings. |
| [voice.json](../voices/praetor/voice.json) | Voice identity, asset hashes and component metadata. |

The profile is about 0.49 MB. It contains no separately trained model weights.
The much larger base model is unchanged upstream Chatterbox Nano. Longer reference
audio is not a substitute for the independent effects stage.

## Sound treatment

The clean generated voice remains the main layer. A quieter copy sits two
semitones below it. Gentle chorus and diffuse reverb add space without periodic
ring modulation. Equalization and light distortion complete the treatment.

| Setting | Praetor value |
| --- | --- |
| Main gain | 0.85 |
| Duplicate pitch and gain | -2 semitones, 0.48 |
| Chorus gain | 0.22 |
| Reverb gain | 0.32 |
| Reverb predelay | 28 ms |
| Reverb decay setting | 1.8 seconds |
| Distortion drive | 1.55 |
| Loudness target | -20 LUFS |
| True peak target | -2 dBTP |

Gain values are linear mix settings, not decibels. Reverb adds a tail beyond the
dry speech. Desktop playback volume is a separate control and does not change
the saved voice preset.

## Changing the treatment

The supplied preset defines the Praetor profile. Changes should produce a new
profile identity rather than silently altering a distributed Praetor package.
Preserve the clean reference and apply effects after synthesis.

For local development, stop the worker before editing profile files. Restart it
with the next speech request. Keep the voice metadata hashes consistent with the
new assets, and test both a short announcement and a longer passage by listening.

There is one bundled profile in this version. The CLI does not provide a voice
library, arbitrary reference upload or profile selection interface.

## Voice and model identity

The voice fingerprint identifies the loaded reference and preset. The model
manifest identifies the base weights separately. Preserve both when comparing
outputs or reporting a defect.

The upstream Perth watermark remains enabled. The application code and authored
effect preset use Apache-2.0; upstream components retain their notices. The
synthetic reference is supplied with the profile and described in its metadata.
See [component notices](dependencies.md#notices).

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Operation](operations.md) | [Next: Model storage](models.md)

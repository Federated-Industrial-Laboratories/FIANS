<p align="center"><a href="../README.md"><img src="../.github/assets/icon.svg" width="44" alt="FIANS"></a></p>

# Documentation

Install and operate FIANS for local English narration with the Praetor voice.
The command controls a private CPU worker. Model installation is explicit;
speech generation uses local model and voice files.

[Project README](../README.md) | [Security](../SECURITY.md) | [Contributing](../CONTRIBUTING.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Start here

1. Read the [requirements](install.md#requirements) and install the runtime.
2. [Install or register the base weights](models.md#install-the-pinned-model).
3. [Render a WAV and test playback](operations.md#render-and-play).
4. Read the [Praetor voice guide](voices.md) before changing its assets.
5. Add FIANS to a tool using the [integration guide](integration.md).

## Manual library

| Order | Manual | Subject |
| --- | --- | --- |
| 01 | [Installation](install.md) | Prerequisites, source installation, updates and removal. |
| 02 | [Operation](operations.md) | Text input, WAV output, playback, worker state and shutdown. |
| 03 | [Praetor voice](voices.md) | Reference, sound treatment and quality boundaries. |
| 04 | [Model storage](models.md) | Pinned weights, verification, existing directories and offline use. |
| 05 | [Integration](integration.md) | Shell and Python callers, volume and failure handling. |
| 06 | [Architecture](architecture.md) | Processing stages, worker ownership and local state. |
| 07 | [Troubleshooting](troubleshooting.md) | Installation, audio, timeout and model failures. |
| 08 | [Packaging and releases](releases.md) | Source and wheel builds, storage policy and distribution. |
| 09 | [Testing](testing.md) | Lightweight contracts, installer checks and real speech qualification. |
| 10 | [Dependencies](dependencies.md) | Engine revisions, system tools and component notices. |

## Terms

| Term | Meaning |
| --- | --- |
| FIANS | The narration command, worker and distribution tools. |
| Praetor | The supplied voice profile: clean reference, effects and metadata. |
| Base model | The unchanged Chatterbox Nano weights used for speech generation. |
| Reference | A short clean recording used to condition the generated speaker. |
| Preset | The settings applied after speech generation. |
| Worker | A private local process that retains the loaded model between requests. |
| Model manifest | A fixed upstream revision and hashes for the required weight files. |
| Voice fingerprint | A digest that identifies the loaded reference and preset. |

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[First manual: Installation](install.md) | [Project README](../README.md)

# Model storage

[Documentation](README.md) | [Praetor voice](voices.md) | [Packaging](releases.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Pinned model](#pinned-model)
- [Install the pinned model](#install-the-pinned-model)
- [Reuse an existing directory](#reuse-an-existing-directory)
- [Offline operation and transfer](#offline-operation-and-transfer)
- [Distribution boundaries](#distribution-boundaries)

## Pinned model

FIANS uses [ResembleAI/chatterbox-nano](https://huggingface.co/ResembleAI/chatterbox-nano/tree/71ccd1d0081b430592cea481f4307e764e07bc64)
at revision `71ccd1d0081b430592cea481f4307e764e07bc64`.
The [model manifest](../models/manifest.json) selects ten files, totaling about
1.94 GB, and records their individual SHA256 hashes.

Neither a moving branch name nor the latest model release selects installed
weights. A model change requires an intentional manifest update and a real speech
check. The Praetor reference and effects remain separate from these base weights.

## Install the pinned model

```sh
fians models install
fians models verify
```

The install command downloads the selected revision and verifies the required
files before registering the model. A failed verification is an error. Incomplete
or mismatched weights cannot become a usable configuration.

Model installation is the explicit network step. Rendering does not silently
download missing files or substitute another model. Use `models verify` to check
the registered files after a copy, restore or storage fault.

## Reuse an existing directory

```sh
fians models install --from-dir /path/to/chatterbox-nano
```

The directory must contain all files from the manifest with matching hashes.
After verification, FIANS registers its absolute path without copying the weights.
Unlisted files such as `conds.pt` or `tokenizer.json` are rejected because upstream
loaders can discover and consume them. The directory must contain the manifest's
file set; only inert `.cache`, `.git` and `.gitattributes` metadata are exempt.
FIANS verifies the configured weights again when its worker starts.

The compatibility alias has the same purpose:

```sh
fians configure --model /path/to/chatterbox-nano
```

Stop any active worker before moving registered weights. Register the new path
and verify it before generating more speech. Keep externally registered model
directories immutable while a worker is active.

## Offline operation and transfer

An offline machine needs the installed Python runtime, required system tools,
voice profile and all model files. Copying weights alone does not install the
Python or operating system dependencies.

On the destination, register the copied directory with `--from-dir`, then run
`models verify`. Once the runtime and files are available, `render` and `speak`
use local inference. No hosted synthesis account or API key is required.

## Distribution boundaries

| Material | Distribution location |
| --- | --- |
| FIANS code, documentation and Praetor profile | GitHub source repository. |
| Base weights | Pinned upstream Hugging Face repository. |
| Source archives, wheels and checksums | Release assets when published. |
| Optional complete offline model packs | Separate release assets or a future dedicated model repository. |

Do not commit base weights, Python environments or inference caches to Git.
There is no FIANS Hugging Face mirror in the initial distribution. Availability
of a future mirror does not change the required manifest hashes.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Praetor voice](voices.md) | [Next: Integration](integration.md)

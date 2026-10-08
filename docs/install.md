# Installation

[Documentation](README.md) | [Model storage](models.md) | [Troubleshooting](troubleshooting.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Requirements](#requirements)
- [Install from source](#install-from-source)
- [Choose installation paths](#choose-installation-paths)
- [Update and remove](#update-and-remove)

## Requirements

| Component | Requirement |
| --- | --- |
| Platform | Linux x86-64 with glibc 2.28 or later. |
| Python | Python 3.12 with the `venv` module. |
| Sound processing | FFmpeg with `rubberband`, `chorus`, `afir` and `loudnorm` filters. |
| Playback | A working audio session and `pw-play`, `paplay` or `aplay`. |
| Storage | About 1.94 GB for base weights and 1.8 GB for the runtime, plus installation working space. |
| Network | Required for initial dependency and model downloads; not for speech generation. |

The runtime uses the CPU with four inference threads. A GPU is not required.
Other operating systems, Python versions and processor architectures are outside
the current support target. The initial request loads the weights into memory.
Runtime size and peak memory depend on the installed dependency builds and text.

Install system packages through the operating system package manager. The FIANS
installer does not request sudo or modify system Python. Check filter availability:

```sh
ffmpeg -filters
python3.12 -m venv --help
```

## Install from source

Obtain a trusted source checkout and run these commands from its root:

```sh
./install.sh
~/.local/bin/fians models install
~/.local/bin/fians models verify
~/.local/bin/fians render --text 'The system is ready.' --output voice.wav
```

The installer creates a private virtual environment and installs FIANS into it.
The launcher works independently of the checkout. Model weights are a separate,
explicit download. See [model storage](models.md) for the exact revision and hashes.

To reuse weights already on disk:

```sh
./install.sh --model-from /path/to/chatterbox-nano
```

FIANS verifies the required files before registering that directory. It does not
copy them. Keep the registered directory available for later requests.

Add the default launcher directory to PATH if it is not already present:

```sh
export PATH="$HOME/.local/bin:$PATH"
fians --version
fians speak --text 'Narration is ready.' --volume 0.3
```

## Choose installation paths

```sh
./install.sh --python /usr/bin/python3.12 \
  --prefix /path/to/private-runtime --bin-dir /path/to/bin
```

The default runtime is `${XDG_DATA_HOME:-$HOME/.local/share}/fians/runtime`.
The default launcher is `~/.local/bin/fians`.
`FIANS_HOME` selects application data and model storage; it defaults to
`${XDG_DATA_HOME:-$HOME/.local/share}/fians`. Set it consistently for model setup
and direct Python invocations when using a custom location. The managed launcher
remembers the location selected during installation. An explicit `FIANS_HOME`
overrides that default.

An existing unrelated prefix or launcher is preserved. Use an unused path or the
explicit update procedure for a managed FIANS installation.

## Update and remove

Stop the worker before updating its runtime:

```sh
fians stop
./install.sh --update
fians --version
fians models verify
```

Supply the same `--prefix` and `--bin-dir` values when updating a custom location.
Updates and removal retain the saved data location unless `FIANS_HOME` overrides it.
Check the [changelog](../CHANGELOG.md) for model or voice changes before updating.
An application update does not imply that a new model revision is required.

```sh
fians stop
./install.sh --uninstall
```

Removal deletes the managed runtime and its matching launcher. Application data,
downloaded models, externally registered weights and rendered WAVs remain.
Remove those separately only when no other application needs them.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Documentation](README.md) | [Next: Operation](operations.md)

# Packaging and releases

[Documentation](README.md) | [Model storage](models.md) | [Testing](testing.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Distribution layout](#distribution-layout)
- [Build packages](#build-packages)
- [Verify and install](#verify-and-install)
- [Prepare a release](#prepare-a-release)

## Distribution layout

The Git repository contains source, manuals, vector artwork, the Praetor profile
and a model manifest. Base weights remain in the pinned upstream Hugging Face
repository. They are not part of the source archive or wheel.

| Artifact | Contents |
| --- | --- |
| Source archive | Application source, installer, documentation, profile and build tools. |
| Python wheel | Installable application and its voice and manifest data. |
| `SHA256SUMS` | Digests of the generated distribution artifacts. |

The wheel is not a self-contained inference runtime. The installer creates the
Python environment from the supplied dependency specification. FFmpeg and desktop
playback remain system dependencies. A complete offline deployment must provide
all these parts as well as the verified weights.

## Build packages

From the repository root:

```sh
python3.12 packaging/build_release.py --output /path/to/dist
```

The output directory must be empty. The builder needs Python 3.12, pip, setuptools
and wheel. Use the installed FIANS runtime's Python, or the versions pinned in
[bootstrap.lock](../packaging/bootstrap.lock), for repeatable builds.
`SOURCE_DATE_EPOCH` can set reproducible archive timestamps
and must be at least `315532800` (1980-01-01).

The builder creates the source archive, wheel and checksums. Keep generated
artifacts outside version control. Do not include virtual environments, cached
downloads, worker state, rendered private narration or credentials.

Building a package does not publish it or create a release tag. Source and wheel
artifacts are suitable for a checked GitHub Release when one is explicitly made.
No separate FIANS model mirror is required by the initial distribution.

## Verify and install

In a downloaded artifact directory:

```sh
sha256sum -c SHA256SUMS
```

Obtain the archive and checksum list from the same trusted release. Checksums
detect byte changes; they do not replace trust in the release source. Extract
the source archive, inspect its README, and follow [installation](install.md).

Register existing weights after an application install to avoid another large
download. An application runtime, model directory and Praetor profile have separate
identities and upgrade considerations.

## Prepare a release

Run the affected contracts and a clean dependency installation. Verify model
hashes and render real short and segmented narration from the installed package.
Check playback, status, shutdown, output preservation and the resulting sound.

Update the version, badges, changelog and component notices together. If any voice
asset or weight changes, update its identity and validate speech again. State the
platforms actually checked; source-only CI is not proof of a working audio runtime.

Retain upstream licence texts with redistributions. See
[dependencies](dependencies.md) for component revisions and notices.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Troubleshooting](troubleshooting.md) | [Next: Testing](testing.md)

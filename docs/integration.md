# Integration

[Documentation](README.md) | [Operation](operations.md) | [Architecture](architecture.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Command interface](#command-interface)
- [Shell narration](#shell-narration)
- [Python callers](#python-callers)
- [Application responsibilities](#application-responsibilities)

## Command interface

Use the installed `fians` command as the application boundary. Render a file when
the caller owns playback; use `speak` for simple desktop narration. Text sent on
standard input avoids exposing it as a process argument.

```sh
printf '%s' 'The report is ready.' | fians render --output report.wav
printf '%s' 'The report is ready.' | fians speak --volume 0.3
```

Commands return nonzero on failure. Inspect the exit code before using an output.
`render` reports the output path, audio information and voice fingerprint as JSON.
Never assume a successful request after a client timeout; the worker may still be
generating the audio.

## Shell narration

A script can retain its existing queue and volume controls while replacing the
speech command:

```sh
#!/bin/sh
set -eu
printf '%s' "$*" | fians speak --volume "${FIANS_VOLUME:-0.3}"
```

Use an absolute executable path in launchers where PATH differs from an interactive
shell. The managed launcher remembers the application home selected at installation.
Set `FIANS_HOME` to override it, or when invoking the package directly with Python.

For narration with caller-owned playback, write into a private temporary directory,
check the render result, play the WAV, and remove the directory. Keep any existing
priority and interruption policy in that caller. A failed FIANS request returns
an error; it does not silently switch to another voice engine.

## Python callers

Use an argument array and standard input. Do not interpolate text into a shell
command:

```python
import json
import subprocess
from pathlib import Path

output = Path("report.wav").absolute()
result = subprocess.run(
    ["fians", "render", "--output", str(output), "--timeout", "300"],
    input="The next report is ready.",
    text=True,
    capture_output=True,
    check=True,
    timeout=480,
)
receipt = json.loads(result.stdout)
print(receipt["output"])
```

The outer process timeout also covers worker startup. Keep it longer than the
requested speech response timeout. Handle `CalledProcessError` and `TimeoutExpired`
in the application. An existing output path needs an explicit replacement policy;
add `--force` only when replacement is intended.

## Application responsibilities

FIANS serializes synthesis requests and queues its own `speak` playback. The caller
owns application-level priority, deduplication, external playback overlap and saved
output retention. FIANS has no persistent job queue, HTTP service or remote
authentication protocol.

The Unix socket is an internal transport, not a stable public API. Use the command
interface instead of connecting to it directly. `status` and `stop` support
application lifecycle management without importing the model runtime.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Model storage](models.md) | [Next: Architecture](architecture.md)

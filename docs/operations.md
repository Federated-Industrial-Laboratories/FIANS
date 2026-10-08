# Operation

[Documentation](README.md) | [Integration](integration.md) | [Troubleshooting](troubleshooting.md)

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

## Contents

- [Render and play](#render-and-play)
- [Text and output](#text-and-output)
- [Worker lifecycle](#worker-lifecycle)
- [Timeouts and queues](#timeouts-and-queues)

## Render and play

```sh
fians render --text 'The system is ready.' --output voice.wav
fians speak --text 'The next report is ready.' --volume 0.3
printf '%s' 'All systems are available.' | fians render --output report.wav
```

`render` writes a mono 24 kHz PCM16 WAV. It reports the output details and voice
fingerprint as JSON. Existing output is preserved unless `--force` is supplied.
The parent output directory is created when needed.

`speak` generates speech and plays it in the current audio session. Its default
volume is 0.3, within the supported range of 0 to 1. Use `--volume` for an
individual request or `FIANS_VOLUME` for a caller-wide default. Rendering does
not require an active desktop audio device.

## Text and output

Supply `--text` or send text on standard input. Whitespace is normalized.
Input must contain 1 to 2,000 characters after normalization. Long input is split
at sentence or word boundaries into segments of at most 240 characters. Avoid
unbroken identifiers that exceed that segment limit.

Spell out uncommon abbreviations, units and ambiguous numbers when pronunciation
matters. Praetor is English speech. Express tone through wording and punctuation;
the FIANS interface does not expose emotional tags or model steering controls.

Generated speech can omit, repeat or pronounce text unexpectedly. Listen to
important announcements before distributing the WAV. Identical inputs use a fixed
seed, but bitwise output identity across runtime versions is not guaranteed.

## Worker lifecycle

```sh
fians status
fians stop
```

`status` reports `stopped`, `starting`, `busy` or `ready`. It does not start a
worker. The first speech request starts one and loads the model and reference.
Later requests reuse it. Requests are processed sequentially. `speak` also queues
playback so concurrent FIANS speech commands do not play over each other.

The worker uses a private Unix socket, four CPU threads and no TCP listener.
It exits after 300 idle seconds, releasing the resident model. `stop` waits for
startup or the current generation and reports success after the worker exits.
It does not immediately cancel an active generation.

Stop the worker before changing model configuration or voice files. Voice changes
are detected during a running worker and require a restart. See
[the voice guide](voices.md#changing-the-treatment) for the supported asset layout.

## Timeouts and queues

`render` and `speak` use a 240-second response timeout. Select a value from 1 to
900 seconds with `--timeout`:

```sh
fians render --text 'The system is ready.' --output voice.wav --timeout 300
```

This response timeout excludes worker startup, waiting for the playback lock and
audio playback. A caller that needs an overall deadline must set a process timeout.

A timed-out or interrupted client can leave its active generation finishing.
Later requests wait behind it. Check status before retrying to avoid an unnecessary
duplicate request. A playback failure does not mean generation failed.

Keep application narration short and apply any priority, cancellation or overlap
policy in the caller. FIANS provides no persistent job history or streaming output.

<p align="center"><img src="../.github/assets/divider.svg" width="720" alt=""></p>

[Previous: Installation](install.md) | [Next: Praetor voice](voices.md)

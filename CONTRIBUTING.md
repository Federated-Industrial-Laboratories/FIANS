# Contributing

FIANS provides a small local narration interface with a stable Praetor voice
profile. Keep changes focused on a complete user workflow and document its
observable behavior.

## Development

Read [architecture](docs/architecture.md) and [testing](docs/testing.md). Use a
separate application home for development so model and worker configuration do
not affect an installed copy. Preserve existing voice assets and output files.

Application contracts run without the inference runtime:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

Changes to dependencies, synthesis or sound treatment also require installed
runtime and listening checks. Do not use timing measurements as a substitute for
voice quality. Stop the worker when a bounded runtime check finishes.

## Changes and review

Use a focused branch and pull request. Explain the problem, resulting behavior
and relevant validation. Include a regression for an actual defect or an important
contract. Update the affected manual and changelog when behavior changes.

Keep base weights, virtual environments, downloaded caches and generated private
speech out of Git. Change model revisions and hashes deliberately. Preserve
upstream notices and the supplied profile identity when repackaging unchanged
assets. Follow [packaging](docs/releases.md) for distribution changes.

Use plain professional English and no emojis in repository text. README artwork,
badges and manual navigation are local assets; keep their style and links consistent.

## Security issues

Follow [SECURITY.md](SECURITY.md) for vulnerabilities. Do not include private
narration, credentials or unrelated local state in issues or pull requests.

#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install or remove a private FIANS runtime; see --help for options.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$root/packaging/install.py" "$@"

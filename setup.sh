#!/usr/bin/env bash
# Startpunkt vom Repository-Stamm aus, auch wenn das aktuelle Verzeichnis anders ist.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec bash "$ROOT/scripts/setup.sh" "$@"

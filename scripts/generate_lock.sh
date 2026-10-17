#!/usr/bin/env bash
set -euo pipefail
uv lock
echo "Generated verified dependency resolution: uv.lock"

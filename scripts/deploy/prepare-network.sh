#!/usr/bin/env bash
# Create the external bridge only if absent. Shared with other Soorin products.
set -euo pipefail
network="${SOORIN_STT_NETWORK:-soorin-ai}"
if docker network inspect "$network" >/dev/null 2>&1; then
  printf 'Docker network exists: %s\n' "$network"
else
  docker network create --driver bridge --attachable "$network"
fi

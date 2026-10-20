#!/usr/bin/env bash
# Validate deployment prerequisites without printing .env credentials.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'PRE-FLIGHT FAILED: %s\n' "$*" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || fail "Docker is not installed"
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"
[[ -f .env ]] || fail "Create .env from .env.example and configure it"
# Never source .env as executable shell code.
read_value() { sed -n "s/^$1=//p" .env | tail -n 1 | tr -d '\r"\047'; }
model="$(read_value STT_MODEL)"
[[ "${model:-shenava-koochik}" == "shenava-koochik" ]] || fail "This deployment profile expects STT_MODEL=shenava-koochik"
for asset in model.onnx tokens.txt .soorin-model.json; do
  [[ -s "models/downloads/shenava-koochik/$asset" ]] || fail "Missing model artifact: $asset"
done
if [[ "$(read_value APP_ENV)" == "production" ]]; then
  key="$(read_value APP_API_KEY)"
  [[ ${#key} -ge 24 && "$key" != "REPLACE_WITH_SECRET_MANAGER_VALUE" ]] || fail "Set a strong APP_API_KEY (at least 24 characters)"
fi
docker compose --env-file .env -f deploy/compose.yaml config --quiet || fail "Invalid Compose configuration"
echo "Preflight passed. Runtime model hashes are checked again during startup."
echo "Run scripts/deploy/prepare-network.sh before docker compose up."

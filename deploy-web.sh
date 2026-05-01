#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.deploy.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  echo "Create it with: OPALSTACK_TARGET='user@server:/path/to/public_html/games/hangperson/'"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -z "${OPALSTACK_TARGET:-}" ]]; then
  echo "OPALSTACK_TARGET is not set in $ENV_FILE"
  exit 1
fi

cd "$ROOT_DIR/web"
npm run build
rsync -avz --delete dist/ "$OPALSTACK_TARGET"

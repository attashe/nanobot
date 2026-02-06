#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

echo "=== Quick import check ==="
python -c "from lib.config.schema import Config; print('OK')"
echo "=== Done ==="

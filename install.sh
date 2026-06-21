#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod +x "$SCRIPT_DIR/pseudo_hunter.py"
sudo ln -sf "$SCRIPT_DIR/pseudo_hunter.py" /usr/local/bin/pseudohunter

echo "PseudoHunter installed. Run it with: pseudohunter"

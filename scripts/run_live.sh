#!/usr/bin/env bash
set -euo pipefail
cd /Users/mini4/.openclaw/workspace/okx-onchainos-contest-bot
source .venv/bin/activate
exec okx-contest-bot --live

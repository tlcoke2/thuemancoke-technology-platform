#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$ROOT/backend"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  [ -f .env ] || cp .env.example .env
  uvicorn app.main:app --reload --port 8000
) &

(
  cd "$ROOT/frontend"
  npm install
  [ -f .env ] || cp .env.example .env
  npm run dev
) &

wait

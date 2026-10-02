#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 build_ui.py
python3 /Users/macdenix/.claude/skills/foquito/scripts/foquito.py index.html --contexto contexto-tutor.md --desde-json explicaciones.json --proveedor groq --modelos 'openai/gpt-oss-120b:8000' --local
python3 integrate_tutor.py
python3 refine_tutor.py
python3 refine_final.py
python3 ground_ui_facts.py
python3 fix_tooltip.py
node review_payload.cjs
node review_no_key.cjs
node review_ui_facts.cjs

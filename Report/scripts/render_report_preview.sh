#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL_DIR="$ROOT_DIR/preview_tool"
INPUT_DOCX="${1:-$ROOT_DIR/Neo-MoFox_Academic_Report_Typeset.docx}"
OUTPUT_DIR="${2:-$ROOT_DIR/preview_pages}"
PAGES_ARG="${3:-}"

cd "$TOOL_DIR"

if [[ -n "$PAGES_ARG" ]]; then
  node render_docx_preview.mjs "$INPUT_DOCX" "$OUTPUT_DIR" "$PAGES_ARG"
else
  node render_docx_preview.mjs "$INPUT_DOCX" "$OUTPUT_DIR"
fi

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAPTER_DIR="$ROOT_DIR/docs/chapters"
FILTER_FILE="$ROOT_DIR/filters/docx_academic.lua"
METADATA_FILE="$ROOT_DIR/docx_metadata.yaml"
REFERENCE_DOC="$ROOT_DIR/academic_reference.docx"
POSTPROCESS_SCRIPT="$ROOT_DIR/scripts/postprocess_academic_docx.py"
OUTPUT_DOC="${1:-$ROOT_DIR/Neo-MoFox_Academic_Report_Typeset.docx}"
RESOURCE_PATH="$ROOT_DIR/docs:$CHAPTER_DIR:$ROOT_DIR/docs/figures"

mapfile -t CHAPTERS < <(find "$CHAPTER_DIR" -maxdepth 1 -name '*.md' | sort)

if [[ ${#CHAPTERS[@]} -eq 0 ]]; then
  echo "No chapters found in $CHAPTER_DIR" >&2
  exit 1
fi

pandoc \
  --standalone \
  --toc \
  --metadata-file="$METADATA_FILE" \
  --lua-filter="$FILTER_FILE" \
  --reference-doc="$REFERENCE_DOC" \
  --resource-path="$RESOURCE_PATH" \
  --output="$OUTPUT_DOC" \
  "${CHAPTERS[@]}"

python "$POSTPROCESS_SCRIPT" "$OUTPUT_DOC"

echo "Wrote $OUTPUT_DOC"

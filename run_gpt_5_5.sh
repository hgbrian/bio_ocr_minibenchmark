#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs/gpt_5_5
for i in 1 2 3 4 5 6; do
  img=$(ls images/image${i}.* | head -1)
  echo "=== image${i} ($img) ==="
  codex exec -m gpt-5.5 -i "$img" \
    -o "outputs/gpt_5_5/image${i}.txt" \
    "Transcribe the text in the image verbatim. Output ONLY the transcribed text — no markdown, no code fences, no commentary, no preamble." >/dev/null
  wc -c "outputs/gpt_5_5/image${i}.txt"
done

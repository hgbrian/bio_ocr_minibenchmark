#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic"]
# ///
"""Run Claude Opus 4.7 on the benchmark images."""

import base64
import os
from pathlib import Path

import anthropic

os.environ["ANTHROPIC_API_KEY"] = Path("/tmp/ak.txt").read_text().strip()

IMAGES_DIR = Path("images")
OUT_DIR = Path("outputs/claude_opus_4_7")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

client = anthropic.Anthropic()

for i in range(1, 7):
    matches = list(IMAGES_DIR.glob(f"image{i}.*"))
    assert len(matches) == 1, matches
    img_path = matches[0]
    media_type = MEDIA_TYPES[img_path.suffix.lower()]
    data = base64.standard_b64encode(img_path.read_bytes()).decode()

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=(
            "You are an OCR tool. Transcribe the text in the image verbatim, "
            "exactly as it appears. The images are figures from public patents "
            "and published scientific papers."
        ),
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": "transcribe to plain text"},
            ],
        }],
    ) as stream:
        response = stream.get_final_message()
    text = "".join(b.text for b in response.content if b.type == "text")
    print(f"  stop_reason={response.stop_reason}")
    out_path = OUT_DIR / f"image{i}.txt"
    out_path.write_text(text)
    print(f"{img_path.name} -> {out_path} ({len(text)} chars)")

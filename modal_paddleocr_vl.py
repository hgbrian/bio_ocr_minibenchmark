# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "modal>=1.0",
# ]
# ///
"""PaddleOCR-VL-1.5 OCR inference on Modal.

Processes benchmark images and outputs OCR results.
"""

import os
from pathlib import Path

from modal import App, Image

GPU = os.environ.get("GPU", "A10G")
TIMEOUT = int(os.environ.get("TIMEOUT", 15))
MODEL_NAME = "PaddlePaddle/PaddleOCR-VL-1.5"


def download_model():
    from transformers import AutoProcessor, AutoModelForImageTextToText

    AutoModelForImageTextToText.from_pretrained(MODEL_NAME)
    AutoProcessor.from_pretrained(MODEL_NAME)


image = (
    Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers>=5.0.0",
        "accelerate",
        "Pillow",
    )
    .run_function(download_model, gpu=GPU)
)

app = App("paddleocr_vl", image=image)


@app.function(timeout=TIMEOUT * 60, gpu=GPU)
def ocr_image(image_name: str, image_bytes: bytes) -> tuple[str, str]:
    """Run OCR on a single image and return (image_name, ocr_text)."""
    import io
    import numpy as np
    import torch
    from PIL import Image as PILImage
    from transformers import AutoProcessor, AutoModelForImageTextToText

    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
    ).to("cuda").eval()
    processor = AutoProcessor.from_pretrained(MODEL_NAME)

    image = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")

    max_pixels = 1280 * 28 * 28

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "OCR:"},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        images_kwargs={
            "size": {
                "shortest_edge": processor.image_processor.min_pixels,
                "longest_edge": max_pixels,
            }
        },
    )

    # Ensure all tensors are on GPU and properly typed
    processed_inputs = {}
    for k, v in inputs.items():
        if isinstance(v, torch.Tensor):
            processed_inputs[k] = v.to(model.device)
        elif hasattr(v, "__array__"):
            # Convert numpy arrays to tensors
            processed_inputs[k] = torch.from_numpy(v).to(model.device)
        else:
            processed_inputs[k] = v
    inputs = processed_inputs

    outputs = model.generate(**inputs, max_new_tokens=2048)
    result = processor.decode(outputs[0][inputs["input_ids"].shape[-1] : -1])

    print(f"Processed {image_name}: {len(result)} chars")
    return (image_name, result)


@app.local_entrypoint()
def main(
    images_dir: str = "./images",
    out_dir: str = "./outputs/paddleocr_vl_1_5",
):
    images_path = Path(images_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    image_files = sorted(images_path.glob("image*.png")) + sorted(
        images_path.glob("image*.jpg")
    )

    if not image_files:
        print(f"No images found in {images_path}")
        return

    print(f"Processing {len(image_files)} images...")

    inputs = []
    for img_file in image_files:
        image_bytes = img_file.read_bytes()
        inputs.append((img_file.stem, image_bytes))

    results = list(ocr_image.starmap(inputs))

    for image_name, ocr_text in results:
        output_file = out_path / f"{image_name}.txt"
        output_file.write_text(ocr_text)
        print(f"Saved {output_file}")

    print(f"\nDone. Results saved to {out_path}")

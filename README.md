# Biological Data OCR Mini-benchmark
There is a fairly common problem of extracting biological data,
specifially amino acid and nucleotide sequences,
from images embedded in PDFs.
There is often no plain text equivalent given, so manual copying or OCR is necessary.

I found that there was not an obvious tool to do this OCR.
I thought the latest DL models would work, or the latest traditional OCR.
I found that nothing worked for me, hence I made this small benchmark.

## Benchmark
There are six images in the benchmark.
Five were taken from four PDFs (details in `benchmark_metadata.yaml`).
The remaining one is synthetic—I just typed some sequence into Google Docs.

<table>
  <tr>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image1.png" width="200"/></td>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image2.jpg" width="200"/></td>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image3.jpg" width="200"/></td>
  </tr>
  <tr>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image4.png" width="200"/></td>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image5.png" width="200"/></td>
    <td><img src="https://github.com/hgbrian/bio_ocr_minibenchmark/blob/main/images/image6.png" width="200"/></td>
  </tr>
</table>

To run
```
uv run benchmark.py
```

## Prompt
For chat interfaces I pasted in the image and typed "transcribe to plain text".
This occasionally failed, and I had to switch to "transcribe to ascii text".
I did not include that failure mode in the benchmark.

## Evaluation
Evaluation is a little tricky.
OCR tools seem to often add whitespace, or get newlines wrong.
It's unclear how much to penalize this.

A Python script (`benchmark.py`) checks that after removing all whitespace including newlines,
and boilerplate in the case of EasyOCR,
the text matches exactly.

## Results
Here are the current results from running `benchmark.py`.

The current winner is Gemini 3 (3/6 correct).


| Model                        | image1 | image2 | image3 | image4 | image5 | image6 |
| :--------------------------- | :----: | :----: | :----: | :----: | :----: | :----: |
| Gemini 2.5 Pro Preview 05-06 |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Claude Sonnet 3.7            |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Claude Opus 4                |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Google Translate             |   ❌   |   ❌   |   ❌   |   ❌   |   ✅   |   ❌   |
| Le Chat                      |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| EasyOCR                      |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ✅   |
| OlmOCR                       |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Reducto                      |   ✅   |   ❌   |   ❌   |   ❌   |   ❌   |   ✅  |
| RedNote dots.ocr             |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌  |
| Tesseract.js                 |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ✅  |
| Gemini 3 Pro Preview         |   ❌   |   ✅   |   ❌   |   ✅   |   ✅   |   ❌  |
| PaddleOCR-VL-1.5             |   ❌   |   ✅   |   ❌   |   x   |   x   |   ❌  |

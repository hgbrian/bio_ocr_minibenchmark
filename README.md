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
Five were taken from four PDFs (details in `benchmark.csv`).
The remaining one is synthetic—I just typed some sequence into Google Docs.

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

A Python script (`generate_results.py`) checks that each "word" in the answer txt
is present in the output of the tool.
This is fairly lenient.

## Results
Here are the current results from running `generate_results.py`.

| Model                        | image1 | image2 | image3 | image4 | image5 | image6 |
| :--------------------------- | :----: | :----: | :----: | :----: | :----: | :----: |
| Gemini 2.5 Pro Preview 05-06 |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Claude Sonnet 3.7            |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Claude Opus 4                |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| Google Translate             |   ❌   |   ❌   |   ❌   |   ❌   |   ✅   |   ❌   |
| Le Chat                      |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |
| EasyOCR                      |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ✅   |
| OlmOCR                       |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |   ❌   |

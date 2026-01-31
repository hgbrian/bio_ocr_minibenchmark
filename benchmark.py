#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "polars",
#     "pyyaml",
# ]
# ///
"""
OCR Benchmark Evaluation Script (YAML-driven, CWD-relative paths)

This script evaluates OCR outputs against ground truth data.
It reads benchmark configuration from 'benchmark_metadata.yaml' (expected in CWD),
processes OCR and truth files, and generates:
1. Per-file match status with detailed explanations for mismatches.
2. A summary of matches for each OCR program.
3. A pivot table (matrix) showing match status (✅/❌/etc.) for each Program vs. Image.
4. A detailed report of all mismatches and errors.
5. A final accuracy summary per OCR program.

Requirements:
  - Python 3.8+
  - PyYAML: `pip install PyYAML` (or your preferred package manager)
  - Polars: `pip install polars`

To Run:
  1. Ensure `benchmark_metadata.yaml` is configured correctly in the current working directory.
  2. Ensure `outputs/` and `answers/` directories (or paths specified in YAML relative to CWD)
     are populated in the current working directory.
  3. Execute: `python your_script_name.py`
"""

import re
from pathlib import Path
import polars as pl
import yaml
from difflib2 import sndiff
from dataclasses import dataclass


def load_benchmark_config(config_path="benchmark_metadata.yaml"):
    """Loads the benchmark configuration from a YAML file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(
            f"Error: Configuration file '{config_path}' not found in the current working directory."
        )
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{config_path}': {e}")
        return None


def remove_filename_prefix(line_text):
    """Removes the 'path/to/file.txt:' or 'path/to/file.txt|' prefix from a line."""
    return re.sub(r"^.+?\.txt[:|]\s*", "", line_text).strip()


def clean_text_for_direct_comparison(raw_lines, is_ocr_output=False):
    """
    Processes raw lines into a single string with all spaces removed,
    suitable for direct comparison.
    """
    all_processed_line_segments = []

    for line_orig in raw_lines:
        line_content = line_orig.strip()

        if not line_content:
            continue

        temp_no_space_for_junk_check = re.sub(r"\s+", "", line_content).lower()
        junk_phrases = [
            "notextualcontentdetected",
            "unabletorespond",
            "failedtoproduce",
        ]
        is_separator_line = (
            line_content == "---"
            or line_content.startswith("---")
            or line_content == "|---|---|"
        )

        if (
            any(
                jp in temp_no_space_for_junk_check
                for jp in junk_phrases
                if temp_no_space_for_junk_check
            )
            or is_separator_line
        ):
            continue

        current_segment = ""
        parts = line_content.split("|")
        stripped_parts = [p.strip() for p in parts if p.strip()]

        if not stripped_parts:
            if line_content and not all(c in " |" for c in line_content):
                current_segment = line_content
            else:
                continue
        elif len(stripped_parts) == 1 and len(parts) == 1:
            current_segment = stripped_parts[0]
        else:
            is_last_part_confidence = False
            if is_ocr_output and len(stripped_parts) > 0:
                try:
                    float(stripped_parts[-1])
                    if len(stripped_parts) > 1:
                        is_last_part_confidence = True
                except ValueError:
                    pass

            if is_last_part_confidence:
                current_segment = "".join(stripped_parts[:-1])
            else:
                current_segment = "".join(stripped_parts)

        if current_segment:
            current_segment = re.sub(r"^\s+", "", current_segment)
            current_segment = current_segment.replace("`", "")
            all_processed_line_segments.append(current_segment)

    full_text_blob = "".join(all_processed_line_segments)
    final_string_no_spaces = re.sub(r"\s+", "", full_text_blob)

    return final_string_no_spaces

@dataclass
class Comparison:
    score: float = -1
    diff: str = ''
    truth: str = ''

    def __str__(self):
        if self.score == 1.0:
            return "Operands match"
        elif self.score > 0.7:
            return f"Similarity:{self.score}\n{self.diff}"
        else:
            return f"Similarity:{self.score}"


def main():
    config = load_benchmark_config()  # Assumes benchmark_metadata.yaml is in CWD
    if not config:
        return

    ocr_programs_metadata = config.get("ocr_programs", {})
    images_metadata = config.get("images", {})

    # Base directory for OCR outputs (relative to CWD)
    outputs_base_dir = Path("outputs")
    answers_base_dir = Path("answers")  # Base directory for answers

    if not outputs_base_dir.exists():
        print(f"Error: Outputs base directory '{outputs_base_dir}' not found in CWD.")
        print(
            "Please create it or ensure your benchmark_metadata.yaml paths are correct."
        )
        return

    if not answers_base_dir.exists():
        print(f"Error: Answers base directory '{answers_base_dir}' not found in CWD.")
        return

    all_results_long = []
    all_image_keys = sorted(list(images_metadata.keys()))
    detailed_mismatches = []

    # Iterate through OCR programs defined in YAML
    for program_key, program_meta in ocr_programs_metadata.items():
        model_name_display = program_meta.get("name", program_key)
        model_outputs_dir = outputs_base_dir / program_key

        print(f"\n--- Evaluating Model: {model_name_display} (key: {program_key}) ---")

        if not model_outputs_dir.exists():
            print(
                f"  Output directory not found for {model_name_display}: {model_outputs_dir}. Skipping."
            )
            for image_key in all_image_keys:
                all_results_long.append(
                    {
                        "Model": model_name_display,
                        "Image": image_key,
                        "MatchStatus": "NP",  # Not Processed
                    }
                )
            continue

        model_match_count = 0
        model_match_partial = 0
        model_total_comparable = 0

        # Iterate through images defined in YAML
        for image_key, image_meta in images_metadata.items():
            ocr_file_path = model_outputs_dir / f"{image_key}.txt"

            # Get primary ground truth path from YAML
            primary_ground_truth_path_str = image_meta.get("ground_truth")
            if not primary_ground_truth_path_str:
                print(
                    f"  ❓ {image_key}: Ground truth path not defined in YAML. Skipping."
                )
                all_results_long.append(
                    {
                        "Model": model_name_display,
                        "Image": image_key,
                        "MatchStatus": "❓GT",
                    }
                )
                continue

            primary_truth_file_path = Path(primary_ground_truth_path_str)

            # Construct paths for alternate truth files
            # Assumes alt files are in the same directory as the primary truth file,
            # and named like image1_alt1.txt, image1_alt2.txt etc.
            truth_file_dir = primary_truth_file_path.parent
            truth_file_stem = primary_truth_file_path.stem  # e.g., "image1"
            truth_file_suffix = primary_truth_file_path.suffix  # e.g., ".txt"

            possible_truth_paths = [primary_truth_file_path]
            # Look for _altN.txt files
            alt_truth_files = sorted(
                list(truth_file_dir.glob(f"{truth_file_stem}_alt*{truth_file_suffix}"))
            )
            possible_truth_paths.extend(alt_truth_files)

            # Filter to only existing truth paths
            existing_truth_paths = [p for p in possible_truth_paths if p.exists()]

            reason_for_status = ""
            ocr_preview_on_mismatch = ""
            truth_preview_on_mismatch = (
                ""  # This will show preview against primary if all alts also mismatch
            )
            match_status_symbol = "-"

            if not ocr_file_path.exists():
                print(
                    f"  ❓ {image_key}: OCR output file not found: {ocr_file_path}. Assuming no output."
                )
                match_status_symbol = "NF"
                reason_for_status = "OCR output file not found"
            elif not existing_truth_paths:  # No primary or alt truth files found
                print(
                    f"  ❓ {image_key}: No ground truth files (primary or alts) found. Primary expected at: {primary_truth_file_path}. Skipping."
                )
                match_status_symbol = "❓T_ALL"  # All truth files missing
                reason_for_status = (
                    "All truth files (primary and alts) not found on disk"
                )
            else:
                model_total_comparable += 1
                score = 0.0
                final_ocr_string = ""
                try:
                    with open(ocr_file_path, "r", encoding="utf-8") as f_ocr:
                        raw_ocr_lines = f_ocr.readlines()
                    final_ocr_string = clean_text_for_direct_comparison(
                        raw_ocr_lines, is_ocr_output=True
                    )
                except Exception as e:
                    match_status_symbol = "ERR_OCR"
                    reason_for_status = f"OCR File Read/Process Error: {e}"
                    print(f"    ERR_OCR {image_key}: {reason_for_status}")
                    detailed_mismatches.append(
                        {
                            "Model": model_name_display,
                            "Image": image_key,
                            "Status": "Error_OCR",
                            "Reason": reason_for_status,
                            "OCR_Cleaned": "N/A",
                            "Truth_Cleaned": "N/A",
                        }
                    )
                    all_results_long.append(
                        {
                            "Model": model_name_display,
                            "Image": image_key,
                            "MatchStatus": match_status_symbol,
                        }
                    )
                    continue  # Skip to next image if OCR can't be processed

                point_awarded = False
                matched_alt_truth_path = None
                scores = []

                for current_truth_path_to_check in existing_truth_paths:
                    try:
                        with open(
                            current_truth_path_to_check, "r", encoding="utf-8"
                        ) as f_truth:
                            raw_truth_lines = f_truth.readlines()
                        current_final_truth_string = clean_text_for_direct_comparison(
                            raw_truth_lines, is_ocr_output=False
                        )
                        if final_ocr_string == current_final_truth_string:
                            point_awarded = True
                            matched_alt_truth_path = current_truth_path_to_check
                            scores.append(Comparison(1.0))
                            break  # Found a match with an alt (or primary)
                        else:
                            scores.append(Comparison(*sndiff(current_final_truth_string, final_ocr_string), current_final_truth_string))
                    except Exception as e:
                        print(
                            f"    WARN {image_key}: Error reading/processing truth file {current_truth_path_to_check}: {e}"
                        )
                        # Continue to try other alt truths if available

                if point_awarded:
                    match_status_symbol = "✅"
                    reason_for_status = "Exact Match"
                    if matched_alt_truth_path != primary_truth_file_path:
                        reason_for_status += f"(with {matched_alt_truth_path.name})"
                    model_match_count += 1  
                    print(f"  ✅ {image_key}: {reason_for_status}")
                else:
                    # Mismatch logic (compare against primary for detailed diff if no alts matched)
                    best = Comparison(float("nan"), "(not attempted)", "(not used)")
                    if len(scores) > 0:
                        best = max(scores, key=lambda x:x.score)
                    
                    if best.score != best.score:
                        match_status_symbol = "❔"
                        reason_for_status = "(not attempted)"
                    elif best.score > 0.7:
                        match_status_symbol = "❌"
                        reason_for_status = "(good effort)"
                    else:
                        match_status_symbol = "💣"
                        reason_for_status = "(terrible)"

                    if best.score > 0:
                        model_match_partial += best.score
                        score = best.score

                    
                    print(f"  {match_status_symbol} {image_key}: {reason_for_status}")

                    detailed_mismatches.append(
                        {
                            "Model": model_name_display,
                            "Image": image_key,
                            "Status": "Mismatch",
                            "Reason": reason_for_status,
                            "OCR_Cleaned": final_ocr_string,
                            "Truth_Cleaned": best.truth,  # Show primary for diff
                            # "OCR_Preview": ocr_preview_on_mismatch,
                            # "Truth_Preview": truth_preview_on_mismatch,
                            "Score": best.score,
                            "Diff": best.diff
                        }
                    )

            all_results_long.append(
                {
                    "Model": model_name_display,
                    "Image": image_key,
                    "MatchStatus": match_status_symbol,
                    "Score": score,
                }
            )

        if model_total_comparable > 0:
            accuracy = (model_match_count / model_total_comparable) * 100

            print(
                f"  Model {model_name_display} Summary: {model_match_count}/{model_total_comparable} matched ({accuracy:.2f}%)."
            )
            if model_total_comparable > model_match_count:
                fuzz = (model_match_partial / (model_total_comparable - model_match_count))
            print(f"  Mistakes are on average {fuzz:.2f}% correct.")
        elif any(img_meta.get("ground_truth") for img_meta in images_metadata.values()):
            print(
                f"  Model {model_name_display} Summary: No comparable images processed (check OCR output files or truth files)."
            )

    if not all_results_long:
        print("No results to process into a table.")
        return

    pl.Config.set_tbl_rows(20)   # That will be enough for a while
    print("\n" + "=" * 30 + " Detailed Match Matrix " + "=" * 30)
    df_long = pl.DataFrame(all_results_long)

    if df_long.height > 0:
        try:
            df_pivot = df_long.pivot(index="Model", on="Image", values="MatchStatus")

            present_cols = df_pivot.columns
            for img_key_col in all_image_keys:
                if img_key_col not in present_cols:
                    df_pivot = df_pivot.with_columns(pl.lit("-").alias(img_key_col))

            final_column_order = ["Model"] + all_image_keys
            df_pivot = df_pivot.select(final_column_order)

            for col_name in df_pivot.columns:
                if col_name != "Model":
                    df_pivot = df_pivot.with_columns(pl.col(col_name).fill_null("-"))
            print(df_pivot)

        except Exception as e:
            print(f"Error creating pivot table: {e}")
            print("Showing long format results instead:")
            print(df_long.sort(["Model", "Image"]))
    else:
        print("No data to pivot for the matrix display.")

    if detailed_mismatches:
        print("\n" + "=" * 30 + " Detailed Mismatch/Error Report " + "=" * 30)
        df_mismatches = pl.DataFrame(detailed_mismatches)
        mismatch_cols_order = [
            "Model",
            "Image",
            "Status",
            "Reason",
            "Score",
            "Diff",
        ]
        final_mismatch_cols = []
        for col in mismatch_cols_order:
            if col in df_mismatches.columns:
                final_mismatch_cols.append(col)
        if final_mismatch_cols:
            print(df_mismatches.select(final_mismatch_cols))
        else:
            print("No columns to display in mismatch report.")

    print("\n" + "=" * 30 + " Summary Per Model (Accuracy) " + "=" * 30)
    if df_long.height > 0:
        df_for_accuracy = df_long.filter(pl.col("MatchStatus").is_in(["✅", "❌", "💣", "❔"]))

        if df_for_accuracy.height > 0:
            summary_df = (
                df_for_accuracy.group_by("Model")
                .agg(
                    (pl.col("MatchStatus") == "✅").sum().alias("Points"),
                    (pl.col("MatchStatus").is_in(["❌", "💣", "❔"])).sum().alias("Fails"),
                    pl.col("Score").sum().alias("Partials"),
                    pl.len().alias("TotalComparableImages"),
                )
                .with_columns(
                    (pl.col("Points") / pl.col("TotalComparableImages") * 100)
                    .round(2)
                    .alias("Exact (%)"),
                    (pl.col("Partials") / pl.col("TotalComparableImages"))
                    .round(2)
                    .alias("Fuzz Acc (%)")
                )
                .with_columns(
                    (pl.col("Exact (%)")+pl.col("Fuzz Acc (%)")).alias("Total Acc (%)")
                )
                .drop("Partials")
                .sort("Exact (%)", descending=True)
            )
            print(summary_df)
        else:
            print(
                "No comparable images (all had missing truth or errors) to calculate accuracy."
            )
    else:
        print("No data for summary.")


if __name__ == "__main__":
    main()

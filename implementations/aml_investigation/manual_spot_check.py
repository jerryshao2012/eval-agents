#!/usr/bin/env python3
"""Create a manual review template from evaluated cases.

This script reads the output cases from JSONL, extracts a random sample of
successful runs, and formats them alongside the narrative pattern quality rubric
to facilitate manual validation.
"""

import json
import random
import sys
from pathlib import Path

# Add aieng-eval-agents to path if needed
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if (ROOT_DIR / "aieng-eval-agents").exists() and str(ROOT_DIR / "aieng-eval-agents") not in sys.path:
    sys.path.append(str(ROOT_DIR / "aieng-eval-agents"))

from aieng.agent_evals.aml_investigation.data import CaseRecord


def generate_spot_check(
    output_path: Path,
    report_path: Path,
    num_samples: int = 5,
    seed: int = 42,
) -> None:
    """Generate a spot check markdown report from evaluated cases."""
    if not output_path.exists():
        print(f"Error: Output file not found at {output_path}")
        return

    records: list[CaseRecord] = []
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(CaseRecord.model_validate_json(stripped))
            except Exception as e:
                print(f"Warning: skipped invalid row: {e}")

    # Keep only cases with output
    evaluated = [r for r in records if r.output is not None]
    if not evaluated:
        print("Error: No evaluated cases found with agent output.")
        return

    print(f"Found {len(evaluated)} evaluated cases.")
    
    # Sample cases
    random.seed(seed)
    sample_size = min(num_samples, len(evaluated))
    sampled_records = random.sample(evaluated, sample_size)
    print(f"Sampled {sample_size} cases for manual check.")

    # Load the rubric to append it for reference
    rubric_path = Path(__file__).parent / "rubrics" / "narrative_pattern_quality.md"
    rubric_content = ""
    if rubric_path.exists():
        rubric_content = rubric_path.read_text(encoding="utf-8")

    # Generate Markdown Report
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# AML Investigation Narrative Spot-Check Report\n\n")
        f.write("Use this document to manually score the agent's reasoning and pattern descriptions against the rubric below.\n\n")
        
        if rubric_content:
            f.write("## Reference Rubric\n\n")
            f.write(rubric_content)
            f.write("\n\n---\n\n")

        f.write("## Sample Cases for Review\n\n")
        for i, record in enumerate(sampled_records, start=1):
            inp = record.input
            expected = record.expected_output
            actual = record.output
            assert actual is not None

            f.write(f"### [Spot-Check {i}] Case ID: `{inp.case_id}`\n\n")
            f.write("#### Case Context\n")
            f.write(f"- **Seed Txn ID**: `{inp.seed_transaction_id}`\n")
            f.write(f"- **Trigger Label (Alert Hint)**: `{inp.trigger_label}`\n")
            f.write(f"- **Ground Truth Verdict**: `is_laundering = {expected.is_laundering}` (Typology: `{expected.pattern_type}`)\n")
            f.write(f"- **Agent Verdict**: `is_laundering = {actual.is_laundering}` (Typology: `{actual.pattern_type}`)\n\n")

            f.write("#### Agent Narrative & Reasoning\n")
            f.write(f"```text\n{actual.summary_narrative}\n```\n\n")

            f.write("#### Agent Typology Description\n")
            f.write(f"```text\n{actual.pattern_description}\n```\n\n")

            f.write("#### Manual Grading Table\n\n")
            f.write("| Criterion | Score (1-5) | Evidence / Notes |\n")
            f.write("| --- | --- | --- |\n")
            f.write("| `summary_narrative_quality` | | |\n")
            f.write("| `pattern_description_quality` | | |\n")
            f.write("| `benign_hypothesis_quality` | | |\n\n")
            f.write("---\n\n")

    print(f"✅ Manual review template written to {report_path}")


if __name__ == "__main__":
    import click

    @click.command()
    @click.option(
        "--output-path",
        type=click.Path(path_type=Path),
        default=Path("implementations/aml_investigation/data/aml_cases_with_output.jsonl"),
        help="Path to evaluated JSONL cases.",
    )
    @click.option(
        "--report-path",
        type=click.Path(path_type=Path),
        default=Path("implementations/aml_investigation/manual_spot_check_report.md"),
        help="Path to save the generated spot-check markdown template.",
    )
    @click.option(
        "--num-samples",
        type=int,
        default=5,
        help="Number of cases to sample.",
    )
    @click.option(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling reproducibility.",
    )
    def cli(output_path: Path, report_path: Path, num_samples: int, seed: int) -> None:
        generate_spot_check(output_path, report_path, num_samples, seed)

    cli()

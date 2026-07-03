"""Evaluate the AML investigation agent.

This script uploads the AML investigation dataset to Langfuse, runs the evaluation
experiment with item-level and trace-level evaluators, and displays the results
in the console. The evaluation includes deterministic grading based on known ground
truth, as well as LLM-based assessments of narrative quality and trace groundedness.

Example
-------
$ uv run --env-file .env implementations/aml_investigation/evaluate.py \
    --dataset-path implementations/aml_investigation/data/aml_cases.jsonl \
    --dataset-name AML-investigation
"""

import asyncio
import logging
import sys
from functools import partial
from pathlib import Path
from typing import Any

import click
from rich.logging import RichHandler

# Add aieng-eval-agents to sys.path if not already there to support running without installation
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if (ROOT_DIR / "aieng-eval-agents").exists() and str(ROOT_DIR / "aieng-eval-agents") not in sys.path:
    sys.path.append(str(ROOT_DIR / "aieng-eval-agents"))

from aieng.agent_evals.aml_investigation.agent import create_aml_investigation_agent
from aieng.agent_evals.aml_investigation.graders import (
    item_level_deterministic_grader,
    run_level_grader,
    trace_deterministic_grader,
)
from aieng.agent_evals.aml_investigation.task import AmlInvestigationTask
from aieng.agent_evals.db_manager import DbManager
from aieng.agent_evals.display import create_console, display_info, display_metrics_table
from aieng.agent_evals.evaluation import TraceWaitConfig, Evaluation
from aieng.agent_evals.evaluation.experiment import run_experiment_with_trace_evals
from aieng.agent_evals.evaluation.graders import (
    create_llm_as_judge_evaluator,
    create_trace_groundedness_evaluator,
)
from aieng.agent_evals.evaluation.graders.config import LLMRequestConfig
from aieng.agent_evals.langfuse import upload_dataset_to_langfuse

logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler(show_path=False)], force=True)

# Silence verbose INFO logs from Google ADK
logging.getLogger("google_adk").setLevel(logging.WARNING)

def _get_val(obj, key):
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key)
    return None

def seed_transaction_flagged_grader(
    input: Any,  # noqa: A002
    output: Any,
    expected_output: Any,
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> list[Evaluation]:
    from typing import Any
    del expected_output, metadata, kwargs

    predicted_is_laundering = _get_val(output, "is_laundering")
    predicted_ids_str = _get_val(output, "flagged_transaction_ids") or ""
    predicted_ids = {
        token.strip()
        for token in str(predicted_ids_str).split(",")
        if token.strip()
    }
    seed_id = _get_val(input, "seed_transaction_id")

    applicable = predicted_is_laundering is True
    passed = (seed_id in predicted_ids) if applicable else True

    return [
        Evaluation(
            name="seed_transaction_flagged",
            value=1.0 if passed else 0.0,
            metadata={"applicable": applicable, "seed_transaction_id": seed_id},
        )
    ]



logger = logging.getLogger(__name__)

@click.command()
@click.option(
    "--dataset-path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="Path to the dataset JSONL file.",
)
@click.option("--dataset-name", type=str, required=True, help="Name of the dataset to upload to Langfuse.")
@click.option(
    "--agent-timeout",
    type=click.IntRange(min=1, max_open=True),
    default=300,
    help="Timeout in seconds for the AML investigation agent.",
)
@click.option(
    "--llm-judge-timeout",
    type=click.IntRange(min=1, max_open=True),
    default=120,
    help="Timeout in seconds for LLM judge evaluations.",
)
@click.option(
    "--llm-judge-retries",
    type=click.IntRange(min=0, max_open=True),
    default=3,
    help="Number of retry attempts for LLM judge evaluations in case of failures.",
)
@click.option(
    "--max-concurrent-cases",
    type=click.IntRange(min=1, max=10),
    default=5,
    help="Maximum number of concurrent cases to process during evaluation.",
)
@click.option(
    "--max-concurrent-traces",
    type=click.IntRange(min=1, max=10),
    default=10,
    help="Maximum number of concurrent traces to process during evaluation.",
)
@click.option(
    "--max-trace-wait-time",
    type=click.IntRange(min=1, max_open=True),
    default=300,
    help="Maximum time in seconds to wait for trace data to be ready during evaluation.",
)
@click.option(
    "--mask-trigger",
    is_flag=True,
    help="Mask the trigger_label passed to the agent with UNKNOWN.",
)
@click.option(
    "--deterministic-only",
    is_flag=True,
    help="Only run deterministic evaluations, bypassing LLM-as-a-judge.",
)
def cli(
        dataset_path: str,
        dataset_name: str,
        llm_judge_timeout: int,
        llm_judge_retries: int,
        agent_timeout: int,
        max_concurrent_cases: int,
        max_concurrent_traces: int,
        max_trace_wait_time: int,
        mask_trigger: bool,
        deterministic_only: bool,
) -> None:
    """Evaluate AML Investigation agent on a given dataset.

    Parameters
    ----------
    dataset_path : str
        Path to the dataset JSONL file containing AML cases.
    dataset_name : str
        Name of the dataset to upload to Langfuse for evaluation.
    llm_judge_timeout : int
        Timeout in seconds for LLM-based judge evaluations.
    llm_judge_retries : int
        Number of retry attempts for LLM judge evaluations in case of failures.
    agent_timeout : int
        Timeout in seconds for the AML investigation agent to complete each case.
    max_concurrent_cases : int
        Maximum number of concurrent cases to process during evaluation.
    max_concurrent_traces : int
        Maximum number of concurrent traces to process during evaluation.
    max_trace_wait_time : int
        Maximum time in seconds to wait for trace data to be ready during evaluation.
    mask_trigger : bool
        Whether to mask the trigger label in case input.
    deterministic_only : bool
        Whether to skip LLM judge evaluations and run deterministic metrics only.
    """
    # Create console for rich formatted output
    console = create_console(force_jupyter=False)

    # Upload dataset to Langfuse
    asyncio.run(upload_dataset_to_langfuse(dataset_path, dataset_name))

    # Define graders/evaluators
    evaluators = [item_level_deterministic_grader, seed_transaction_flagged_grader]
    if not deterministic_only:
        # Item-level LLM-as-a-judge evaluator assesses the quality of the agent's
        # narrative output based on a rubric.
        narrative_quality_evaluator = create_llm_as_judge_evaluator(
            name="narrative_quality",
            rubric_markdown="implementations/aml_investigation/rubrics/narrative_pattern_quality.md",
            model_config=LLMRequestConfig(timeout_sec=llm_judge_timeout, retry_max_attempts=llm_judge_retries),
        )
        benign_hypothesis_evaluator = create_llm_as_judge_evaluator(
            name="benign_hypothesis_quality",
            rubric_markdown="implementations/aml_investigation/rubrics/benign_hypothesis_quality.md",
            model_config=LLMRequestConfig(timeout_sec=llm_judge_timeout, retry_max_attempts=llm_judge_retries),
        )
        evaluators.extend([narrative_quality_evaluator, benign_hypothesis_evaluator])

    # Trace-level graders assess the correctness of tool use and the groundedness
    # of the agent's response based on trace data.
    db_policy = DbManager().aml_db().policy
    deterministic_trace_grader = partial(trace_deterministic_grader, db_policy=db_policy)
    trace_evaluators = [deterministic_trace_grader]
    if not deterministic_only:
        trace_groundedness_evaluator = create_trace_groundedness_evaluator(
            model_config=LLMRequestConfig(timeout_sec=llm_judge_timeout, retry_max_attempts=llm_judge_retries)
        )
        trace_evaluators.append(trace_groundedness_evaluator)

    agent = create_aml_investigation_agent(timeout_sec=agent_timeout)
    results = run_experiment_with_trace_evals(
        dataset_name=dataset_name,
        name="AML Investigation Evaluation",
        task=AmlInvestigationTask(agent=agent, mask_trigger_label=mask_trigger),
        evaluators=evaluators,
        trace_evaluators=trace_evaluators,
        run_evaluators=[run_level_grader],
        max_concurrency=max_concurrent_cases,
        trace_max_concurrency=max_concurrent_traces,
        trace_wait=TraceWaitConfig(max_wait_sec=max_trace_wait_time),
    )

    # Display item-level results
    console.print("\n[bold cyan]📋 Item-Level Results[/bold cyan]\n")
    for idx, item_result in enumerate(results.experiment.item_results, start=1):
        item_metrics = {eval_.name: eval_.value for eval_ in item_result.evaluations}
        # Try to get item ID from metadata, fall back to index
        item_id = f"Item {idx}"
        try:
            item = item_result.item
            if item and isinstance(item, dict):
                metadata = item.get("metadata", {})
                if metadata and isinstance(metadata, dict):
                    item_id = metadata.get("id", item_id)
            elif item and hasattr(item, "metadata"):
                metadata = getattr(item, "metadata", None)
                if metadata and isinstance(metadata, dict):
                    item_id = metadata.get("id", item_id)
        except Exception:
            pass  # Keep default item_id

        display_metrics_table(
            metrics=item_metrics,
            title=str(item_id),
            console=console,
        )

    # Display run-level metrics
    if hasattr(results.experiment, "run_evaluations") and results.experiment.run_evaluations:
        console.print("\n[bold green]📊 Run-Level Metrics[/bold green]\n")
        run_metrics = {eval_.name: eval_.value for eval_ in results.experiment.run_evaluations}
        display_metrics_table(metrics=run_metrics, title="Aggregate Performance", console=console)

    # Display trace evaluation summary
    if results.trace_evaluations:
        console.print("\n[bold magenta]🔍 Trace Evaluation Summary[/bold magenta]\n")
        trace_summary: dict[str, float | int | str] = {
            "Successful Traces": len(results.trace_evaluations.evaluations_by_trace_id),
            "Skipped Traces": len(results.trace_evaluations.skipped_trace_ids),
            "Failed Traces": len(results.trace_evaluations.failed_trace_ids),
        }
        display_metrics_table(metrics=trace_summary, title="Trace Processing", console=console)

    # Display slice-based reporting
    import collections
    from rich.table import Table

    console.print("\n[bold yellow]🍰 Slice-Based Performance Reporting[/bold yellow]\n")

    pattern_slices = collections.defaultdict(list)
    trigger_slices = collections.defaultdict(list)

    for item_result in results.experiment.item_results:
        is_laundering_eval = next((e for e in item_result.evaluations if e.name == "is_laundering_correct"), None)
        if not is_laundering_eval or not is_laundering_eval.metadata:
            continue

        expected = is_laundering_eval.metadata.get("expected")
        actual = is_laundering_eval.metadata.get("actual")

        item_obj = item_result.item
        pattern_type = "UNKNOWN"
        trigger_label = "UNKNOWN"
        
        def _extract_field(obj, key):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get(key)
            if hasattr(obj, key):
                return getattr(obj, key)
            return None

        if item_obj:
            inp = _extract_field(item_obj, "input")
            expected_out = _extract_field(item_obj, "expected_output")
            
            p_type = _extract_field(expected_out, "pattern_type")
            t_label = _extract_field(inp, "trigger_label")
            
            if p_type:
                pattern_type = p_type
            if t_label:
                trigger_label = t_label

        if hasattr(pattern_type, "name"):
            pattern_type = getattr(pattern_type, "name")
        if hasattr(trigger_label, "name"):
            trigger_label = getattr(trigger_label, "name")

        pattern_slices[str(pattern_type)].append((expected, actual))
        trigger_slices[str(trigger_label)].append((expected, actual))

    def display_slice_table(slices, title):
        table = Table(title=title)
        table.add_column("Slice Key", justify="left", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("TP/FP/FN/TN", justify="center")
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1", justify="right")

        for name, pairs in sorted(slices.items()):
            tp = fp = fn = tn = 0
            for exp_, act_ in pairs:
                if exp_ and act_:
                    tp += 1
                elif (not exp_) and act_:
                    fp += 1
                elif exp_ and (not act_):
                    fn += 1
                else:
                    tn += 1
            prec = float(tp) / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = float(tp) / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2.0 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            table.add_row(
                name,
                str(len(pairs)),
                f"{tp}/{fp}/{fn}/{tn}",
                f"{prec:.2f}",
                f"{rec:.2f}",
                f"{f1:.2f}"
            )
        console.print(table)
        console.print("")

    display_slice_table(pattern_slices, "Performance by Ground-Truth Typology")
    display_slice_table(trigger_slices, "Performance by Trigger Label")

    display_info("Evaluation complete! Results have been uploaded to Langfuse.", console=console)


if __name__ == "__main__":
    cli()

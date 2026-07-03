# Implementation Plan - AML Investigation Day 3 Experiments

This plan outlines the steps to execute two high-value experiments and a manual validation workflow for the AML Investigation Agent, focusing on deterministic metrics and avoiding LLM-as-a-judge APIs.

## User Review Required

> [!IMPORTANT]
> - We will modify the codebase to support stratified/balanced case sampling to guarantee all 9 typologies (8 laundering typologies + NONE) are represented.
> - We will add an option to mask the `trigger_label` input in the agent task to run the exploitability study.
> - LLM-as-a-judge components (`narrative_quality` and `trace_groundedness`) will be bypassed to save API cost and speed up runs, relying on deterministic metrics.

## Proposed Changes

We will introduce changes to the dataset generation code to balance typologies, update the task wrapper to allow masking, and run the comparative evaluation.

---

### [Component 1: Stratified Case Generation (Experiment A)]

#### [MODIFY] [cases.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/data/cases.py)
Update `build_cases` to support stratified sampling of the 8 laundering typologies. Instead of a simple slice from shuffled attempts, it will group the attempts by their `pattern_type` and sample an equal number of cases from each typology to guarantee complete representation and balance.

#### [RUN COMMAND] Generate Larger, Balanced Dataset
Run the CLI to generate a balanced case file (e.g. 5 cases for each of the 8 typologies, plus matching normal/false-positive/false-negative cases).

---

### [Component 2: Trigger Label Masking & Deterministic Evaluation (Experiment B)]

#### [MODIFY] [task.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/task.py)
Add a `mask_trigger_label` boolean parameter to `AmlInvestigationTask`. When `True`, the `trigger_label` in the input passed to the agent is replaced with `"UNKNOWN"`.

#### [MODIFY] [evaluate.py](evaluate.py)
Modify the evaluation script to:
1. Accept a `--mask-trigger` CLI option.
2. Accept a `--deterministic-only` CLI option that disables `narrative_quality_evaluator` and `trace_groundedness_evaluator` (bypassing LLM-as-a-judge).

---

### [Component 3: Manual Judge Validation Workflow]

#### [NEW] [manual_spot_check.py](manual_spot_check.py)
Create a quick utility script to extract a random sample of 5-10 completed cases from the output JSONL file, print their `summary_narrative` and `pattern_description` alongside the rubric in [narrative_pattern_quality.md](rubrics/narrative_pattern_quality.md), and provide a simple markdown template for manual scoring.

## Verification Plan

### Automated Tests
- Run `evaluate.py` twice on the newly balanced dataset:
  1. Baseline run (intact trigger labels, deterministic metrics only):
     ```bash
     uv run --env-file .env implementations/aml_investigation/evaluate.py --dataset-path implementations/aml_investigation/data/aml_cases.jsonl --dataset-name AML-balanced-baseline --deterministic-only
     ```
  2. Exploitability run (masked trigger labels, deterministic metrics only):
     ```bash
     uv run --env-file .env implementations/aml_investigation/evaluate.py --dataset-path implementations/aml_investigation/data/aml_cases.jsonl --dataset-name AML-balanced-masked --deterministic-only --mask-trigger
     ```
- Compare F1-scores, precision, recall, and macro-F1 of pattern types between both runs.

### Manual Verification
- Execute the spot-check utility to generate a review template for manual evaluation of the narrative quality.

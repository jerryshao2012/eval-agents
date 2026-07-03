# Implementation Plan - AML Investigation Day 3 Experiments & Enhancements

This plan outlines the steps to execute Day 3 experiments, implement new domain metrics, and upgrade the agent's graph-traversal capabilities.

## User Review Required

> [!IMPORTANT]
> - We will implement a new counterparty graph traversal tool (`get_counterparty_graph`) to prevent the agent from burning its query budget on raw SQL calls.
> - We will add new metrics: a deterministic `seed_transaction_flagged` metric and an LLM-judge-based `benign_hypothesis_quality` metric.
> - We will implement slice-based reporting (slicing performance by ground-truth typology and trigger label) in the evaluation script.

---

## Proposed Changes

### [Component 1: Stratified Case Generation (Experiment A)] (Completed)
- **Modify** `cases.py`: Updated `build_cases` to sample laundering typologies using a stratified/balanced method.
- **Run CLI**: Generated a balanced dataset of 72 cases.

### [Component 2: Trigger Label Masking (Experiment B)] (Completed)
- **Modify** `task.py` and `evaluate.py`: Added support for masking `trigger_label` with `"UNKNOWN"`.

---

### [Component 3: Graph Tooling Upgrade]

#### [NEW] [graph.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/tools/graph.py)
Implement a graph traversal tool:
```python
def get_counterparty_graph(account_id: str, direction: str = "both", max_depth: int = 2) -> str:
    """Traverse the transaction history to build a counterparty graph up to max_depth.
    Returns a list of nodes and edges with transaction counts and total volume.
    """
```

#### [MODIFY] [agent.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/agent.py)
- Register `get_counterparty_graph` in the agent's toolset.
- Update the system instructions (`ANALYST_PROMPT`) to explain how to use the graph tool for multi-hop investigations (e.g. STACK, CYCLE, GATHER-SCATTER).

---

### [Component 4: New Domain Metrics & Slice-Based Reporting]

#### [NEW] [benign_hypothesis_quality.md](rubrics/benign_hypothesis_quality.md)
Create a scoring rubric for benign justification.

#### [MODIFY] [evaluate.py](evaluate.py)
- Add `seed_transaction_flagged_grader` to the item-level evaluators.
- Add `benign_hypothesis_quality` (LLM-as-a-judge) evaluator.
- Add slice-based reporting at the end of the evaluation script (slicing F1/precision/recall by ground-truth typology and trigger label).

---

### [Component 5: Manual Judge Validation Workflow] (Completed)
- Created `manual_spot_check.py` to extract random narrative samples and generate review reports.

## Verification Plan

### Automated Tests
- Run baseline and masked evaluations with the new metrics and tools enabled:
  ```bash
  uv run --env-file .env implementations/aml_investigation/evaluate.py --dataset-path implementations/aml_investigation/data/aml_cases.jsonl --dataset-name AML-enhanced --deterministic-only
  ```
- Verify that the slice-based reporting output matches the typologies and trigger labels.

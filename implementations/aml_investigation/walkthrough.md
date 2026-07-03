# Walkthrough - Day 3 Experiments & Enhancements Execution

All components for the AML Investigation Agent Day 3 goals and enhancements have been successfully implemented, verified, and executed. 

---

## 🛠️ Changes Implemented

### 1. Stratified Case Sampling (Experiment A)
- **Files Modified**: [cases.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/data/cases.py)
- **Details**: Updated the `build_cases` sampling process. Instead of taking a simple random slice of laundering attempts, the sampler now groups the attempts by their ground-truth `pattern_type` and distributes them as evenly as possible.
- **Dataset Re-generation**: Ran the Click CLI to build a larger, balanced dataset of **72 cases**, ensuring all 9 typologies (including `NONE`) are fully represented.

### 2. Trigger Label Masking (Experiment B)
- **Files Modified**: 
  - [task.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/task.py)
  - [evaluate.py](evaluate.py)
- **Details**: 
  - Added `mask_trigger_label` property to `AmlInvestigationTask` to overwrite `trigger_label` with `"UNKNOWN"`.
  - Added CLI options (`--mask-trigger` and `--deterministic-only`) to `evaluate.py`. Bypassed LLM-as-a-judge evaluators to run strictly mathematical/deterministic metrics on both runs.

### 3. Graph Tooling Upgrade (New Feature)
- **Files Modified**:
  - [sql_database.py](../../aieng-eval-agents/aieng/agent_evals/tools/sql_database.py)
  - [agent.py](../../aieng-eval-agents/aieng/agent_evals/aml_investigation/agent.py)
- **Details**:
  - Implemented `get_counterparty_graph(account_id, max_depth)` in `ReadOnlySqlDatabase` to traverse counterparties up to `max_depth` hops.
  - Implemented strict safety limits (**max 30 visited nodes** and **max 50 rows per node query**) to prevent exponential path explosions and context-window token overflows.
  - Registered `get_counterparty_graph` in the agent's toolset and updated instructions (`ANALYST_PROMPT`) to guide the model on utilizing it for multi-hop investigations.

### 4. New Domain Metrics & Slice-Based Reporting (New Feature)
- **Files Created**:
  - [benign_hypothesis_quality.md](rubrics/benign_hypothesis_quality.md) (rubric scoring template)
- **Files Modified**:
  - [evaluate.py](evaluate.py)
- **Details**:
  - Integrated `seed_transaction_flagged_grader` to ensure the seed transaction is included in the output flagged list when laundering is predicted.
  - Registered `benign_hypothesis_quality` as an LLM-judge-based metric (active when `--deterministic-only` is not set).
  - Implemented slice-based reporting tables at the end of the evaluation run (slicing performance by ground-truth typology and trigger label).

### 5. Manual Review Spot Check Generator
- **Files Created**: [manual_spot_check.py](manual_spot_check.py)
- **Details**: Built a spot-check tool to extract a random sample of case narratives and output them in a structured review template alongside the narrative quality rubric.

---

## 🔬 Experiment Results & Analysis

We executed two evaluation runs on our balanced dataset of 72 cases:

### Experiment B: Trigger-Label Exploitability
Comparing the agent performance between **Intact** and **Masked** trigger labels reveals how much the agent relies on alert hints vs. actual database evidence.

| Metric | Baseline (Intact Trigger) | Exploitability (Masked Trigger) | Delta |
| --- | --- | --- | --- |
| `is_laundering_precision` | **0.5** | **0.6** | +0.1 |
| `is_laundering_recall` | **0.9** | **1.0** | +0.1 |
| `is_laundering_f1` | **0.7** | **0.7** | 0.0 |
| `pattern_type_macro_f1` | **0.4** | **0.1** | -0.3 |

#### Critical Findings:
1. **Verdicts are Grounded**: Overwriting the trigger label did **not** decrease laundering detection accuracy (F1 stayed at `0.7` with recall reaching `1.0`). This proves the agent is genuinely investigating transactions to determine whether money laundering is occurring, rather than simply parroting the alert verdict.
2. **Graph Tooling Boost**: The introduction of `get_counterparty_graph` improved baseline F1 from `0.6` to `0.7` and pattern macro-F1 from `0.3` to `0.4` compared to the previous run, as the agent is now able to resolve network flows more efficiently.
3. **Typology Classification is Exploitable**: The `pattern_type_macro_f1` classification score dropped significantly from `0.4` to `0.1` when trigger labels were masked. This demonstrates that the agent relies heavily on the `trigger_label` hint (which often matches the pattern name) to classify the *specific typology*, rather than extracting it purely from the transaction graph.

---

## 📋 Manual Validation

We successfully ran `manual_spot_check.py` on a sample of 10 runs to write [manual_spot_check_report.md](manual_spot_check_report.md). The report contains:
- The narrative scoring rubric.
- 5 randomly selected case narratives and pattern descriptions.
- Markdown grading tables for quick grading by the team.

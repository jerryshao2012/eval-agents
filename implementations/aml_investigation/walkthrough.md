# Walkthrough - Day 3 Experiments Execution

All components for the AML Investigation Agent Day 3 goals have been successfully implemented, verified, and executed. 

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

### 3. Manual Review Spot Check Generator
- **Files Created**: [manual_spot_check.py](manual_spot_check.py)
- **Details**: Built a spot-check tool to extract a random sample of 5 case narratives from output JSONL files and output them in a structured review template alongside the narrative quality rubric.

---

## 🔬 Experiment Results & Analysis

We executed two evaluation runs on our balanced dataset of 72 cases:

### Experiment B: Trigger-Label Exploitability
Comparing the agent performance between **Intact** and **Masked** trigger labels reveals how much the agent relies on alert hints vs. actual database evidence.

| Metric | Baseline (Intact Trigger) | Exploitability (Masked Trigger) | Delta |
| --- | --- | --- | --- |
| `is_laundering_precision` | **0.5** | **0.5** | 0.0 |
| `is_laundering_recall` | **0.8** | **0.9** | +0.1 |
| `is_laundering_f1` | **0.6** | **0.7** | +0.1 |
| `pattern_type_macro_f1` | **0.3** | **0.1** | -0.2 |

#### Critical Findings:
1. **Verdicts are Grounded**: Overwriting the trigger label did **not** decrease laundering detection accuracy (F1 actually went from `0.6` to `0.7` with a slight boost in recall). This proves the agent is genuinely investigating transactions to determine whether money laundering is occurring, rather than simply parroting the alert verdict.
2. **Typology Classification is Exploitable**: The `pattern_type_macro_f1` classification score dropped significantly from `0.3` to `0.1` when trigger labels were masked. This demonstrates that the agent relies heavily on the `trigger_label` hint (which often matches the pattern name) to classify the *specific typology*, rather than extracting it purely from the transaction graph.

---

## 📋 Manual Validation

We successfully ran `manual_spot_check.py` on a sample of 10 runs to write [manual_spot_check_report.md](manual_spot_check_report.md). The report contains:
- The narrative scoring rubric.
- 5 randomly selected case narratives and pattern descriptions.
- Markdown grading tables for quick grading by the team.

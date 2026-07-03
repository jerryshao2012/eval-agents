# AML Investigation Narrative Spot-Check Report

Use this document to manually score the agent's reasoning and pattern descriptions against the rubric below.

## Reference Rubric

This rubric scores investigation reasoning quality only. It does not score grammar, writing style, tone, or fluency.

### Scoring Table

| Score | `summary_narrative_quality` | `pattern_description_quality` |
| --- | --- | --- |
| 5 | Evidence-grounded and coherent investigation logic. Explicitly considers and rules out plausible benign explanations. Conclusion is fully consistent with cited evidence and final decision fields. | Clear mechanism-level typology description: flow shape, actor roles, fund movement pattern, and temporal logic are explicit and consistent with the conclusion. |
| 4 | Strong evidence linkage and mostly coherent logic, with only minor omissions or weak spots. | Mechanism is mostly correct and specific, with minor incompleteness. |
| 3 | Mixed quality. Some grounding and reasoning are present, but analysis is partially generic, incomplete, or weakly connected to evidence. | Partially correct mechanism but vague, generic, or only partially connected to evidence. |
| 2 | Weak evidence grounding with major reasoning gaps, leaps, or unsupported inferences. | Mostly vague description and/or materially incomplete with partial inaccuracies. |
| 1 | Reasoning is unsupported, contradictory, or materially inconsistent with available evidence. | Incorrect, contradictory, or effectively empty mechanism description. |

### Hard Guardrails (Reasoning Quality With Hard Floors)

- If the narrative contains material unsupported claims: `summary_narrative_quality <= 2`.
- If the narrative contradicts final decision fields (`is_laundering`, `pattern_type`): `summary_narrative_quality = 1`.
- If the pattern description contradicts decision fields or typology semantics: `pattern_description_quality = 1`.
- If the pattern description is effectively placeholder or non-informative: `pattern_description_quality <= 2`.

### Scoring Instructions

- Use integers only: `1`, `2`, `3`, `4`, `5`.
- Judge only from the provided input, expected output, and candidate output.
- Keep comments concise and evidence-focused.

### Special Cases

- If ground-truth `pattern_description` is missing, `N/A`, or equivalent placeholder text, treat any coherent candidate pattern description as valid when it is consistent with other fields (especially `is_laundering` and `pattern_type`).
- Ground-truth `pattern_description` may be terse typology shorthand (for example, `Max 1-degree Fan-In, Max 10-degree Fan-Out, Max 7 hops`). In these cases, evaluate semantic consistency with typology mechanics rather than exact phrasing.


---

## Sample Cases for Review

### [Spot-Check 1] Case ID: `04b291d811ee137f`

#### Case Context
- **Seed Txn ID**: `e079c1392f4a5486`
- **Trigger Label (Alert Hint)**: `FAN-OUT`
- **Ground Truth Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.FAN_OUT`)
- **Agent Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.FAN_OUT`)

#### Agent Narrative & Reasoning
```text
The investigation focused on the source account 80C8966E0, identified as a Partnership. Within the review period, this account made 8 external payments totaling $1,328,343.35 to 8 unique counterparties. This activity aligns with the FAN-OUT trigger label. Critically, the account had no incoming funds from external sources during this period to explain the origin of the money being disbursed. The lack of a clear, legitimate source for the funds, combined with the rapid, wide disbursement pattern, is highly indicative of money laundering. The behavior is inconsistent with typical business activity for a partnership, which would usually involve corresponding inflows of revenue. Therefore, the activity is deemed suspicious.
```

#### Agent Typology Description
```text
One source account ('80C8966E0') made 8 payments to 8 distinct destination accounts in a short period (Sept 9 - Sept 13). The total amount dispersed was $1,328,343.35. The final payment (the seed transaction) was for $1,247,008.84, representing the bulk of the funds. This pattern of one-to-many payments is a classic FAN-OUT.
```

#### Manual Grading Table

| Criterion | Score (1-5) | Evidence / Notes |
| --- | --- | --- |
| `summary_narrative_quality` | 5 | Coherent, evidence-grounded logic. Cites the lack of incoming funds as a counter-indicator to a benign partnership model. |
| `pattern_description_quality` | 5 | Very clear description of the flow shape (1-to-many), actors (Partnership to 8 counterparties), and timeline. |
| `benign_hypothesis_quality` | 5 | Coherent benign justification. Explicitly discusses why partnership models lack expected inflows to support benign activities. |

---

### [Spot-Check 2] Case ID: `b588ce3fa73b884c`

#### Case Context
- **Seed Txn ID**: `7363d8ff28eb3467`
- **Trigger Label (Alert Hint)**: `FAN-IN`
- **Ground Truth Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.FAN_IN`)
- **Agent Verdict**: `is_laundering = False` (Typology: `LaunderingPattern.FAN_IN`)

#### Agent Narrative & Reasoning
```text
The investigation centered on account 80B18E250 (Corporation #12711), which received funds from six different business entities, including the seed transaction from account 80AD1C820. This activity matches the technical structure of a FAN-IN pattern. However, the context suggests benign behavior. It is plausible and common for a corporation to receive payments from a variety of other businesses. The transaction amounts are not indicative of structuring, and the source entities are all commercial. Without further indicators of illicit activity, such as a rapid consolidation and subsequent transfer to an unrelated entity (gather-scatter), the behavior is assessed as consistent with legitimate business operations. Therefore, no money laundering is suspected.
```

#### Agent Typology Description
```text
Within the 7-day investigation window, the central account 80B18E250, belonging to Corporation #12711, received 7 payments from 6 different business entities (3 Corporations, 2 Partnerships, 1 Sole Proprietorship). This consolidation of funds from multiple distinct sources into a single account is characteristic of a FAN-IN pattern.
```

#### Manual Grading Table

| Criterion | Score (1-5) | Evidence / Notes |
| --- | --- | --- |
| `summary_narrative_quality` | 1 | **Hard Floor Violated**: The narrative concludes "no money laundering is suspected" (consistent with `is_laundering = False`), but the agent set `pattern_type = FAN_IN` (contradicting the NONE instruction for benign cases). |
| `pattern_description_quality` | 1 | **Hard Floor Violated**: Setting `pattern_type` to `FAN_IN` while ruling out money laundering is semantically inconsistent. |
| `benign_hypothesis_quality` | 5 | Excellent corporate cash inflows benign rationale, though the output fields are inconsistent. |

---

### [Spot-Check 3] Case ID: `0f368f59bbdbfaed`

#### Case Context
- **Seed Txn ID**: `e03d17157ef14e2e`
- **Trigger Label (Alert Hint)**: `RANDOM`
- **Ground Truth Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.RANDOM`)
- **Agent Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.FAN_IN`)

#### Agent Narrative & Reasoning
```text
The investigation focused on account 80A633EB0, a Sole Proprietorship, which received the seed transaction of $14,727.37 from 'Corporation #28915' (80DB1E720). Within the investigation window, account 80A633EB0 received 24 incoming transactions totaling over $357,000 from 4 distinct counterparties, while having only one minor outgoing transaction. The inflows from two of the main counterparties were highly structured, arriving in repetitive, paired amounts. This activity is consistent with a FAN-IN typology, where account 80A633EB0 is used to aggregate funds from multiple sources. The lack of legitimate business outflows makes a benign explanation unlikely.
```

#### Agent Typology Description
```text
Multiple source accounts send funds to a single destination account (80A633EB0), which acts as a collection point. The pattern is characterized by structured deposits (repetitive, paired amounts) from the primary sending accounts. The destination account has minimal outgoing activity, indicating it is an aggregation point for illicit funds.
```

#### Manual Grading Table

| Criterion | Score (1-5) | Evidence / Notes |
| --- | --- | --- |
| `summary_narrative_quality` | 4 | Solid reasoning grounded in structured, repetitive inflow amounts. Coherent with the agent's verdict of `FAN_IN`. |
| `pattern_description_quality` | 5 | Accurately describes the aggregation flow shape, actor entities, and structured deposits. |
| `benign_hypothesis_quality` | 4 | States benign is unlikely due to lack of business outflows, but could discuss business model characteristics of sole proprietorships further. |

---

### [Spot-Check 4] Case ID: `6b8d3dab0f913048`

#### Case Context
- **Seed Txn ID**: `f56c25a431c65711`
- **Trigger Label (Alert Hint)**: `GATHER-SCATTER`
- **Ground Truth Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.GATHER_SCATTER`)
- **Agent Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.GATHER_SCATTER`)

#### Agent Narrative & Reasoning
```text
The investigation uncovered a GATHER-SCATTER money laundering pattern centered around account 811B6E170. This account received numerous deposits from a variety of sources before disseminating the funds through a larger number of smaller transactions to a wide range of accounts. The seed transaction was one of the final disbursements in this pattern. The activity is not consistent with benign behavior.
```

#### Agent Typology Description
```text
Account 811B6E170 exhibits a clear GATHER-SCATTER pattern. From September 2nd to September 14th, the account received 13 inbound payments from 9 distinct counterparties (totaling 297,358.03). This "gather" phase was immediately followed by a "scatter" phase, where the account sent 48 outbound payments to 16 distinct counterparties (totaling 985,625.54) between September 1st and September 17th. The seed transaction, an internal transfer, occurs at the end of this scattering activity. The rapid collection of funds from multiple sources followed by their wide distribution is a classic money laundering typology designed to obscure the origin of funds.
```

#### Manual Grading Table

| Criterion | Score (1-5) | Evidence / Notes |
| --- | --- | --- |
| `summary_narrative_quality` | 2 | Extremely generic. Narrative cites no transaction counts, dates, or values, relying entirely on qualitative summaries. |
| `pattern_description_quality` | 5 | Excellent. The agent put all the specific evidence, timelines (Sept 2 - 14 vs Sept 1 - 17), and exact transaction volumes/counts in the description. |
| `benign_hypothesis_quality` | 1 | Completely lacks benign hypothesis analysis or reasoning; only states benign behavior is not consistent. |

---

### [Spot-Check 5] Case ID: `39697add62ec32d6`

#### Case Context
- **Seed Txn ID**: `33dfd97ae6b334c5`
- **Trigger Label (Alert Hint)**: `FAN-OUT`
- **Ground Truth Verdict**: `is_laundering = True` (Typology: `LaunderingPattern.FAN_OUT`)
- **Agent Verdict**: `is_laundering = False` (Typology: `LaunderingPattern.NONE`)

#### Agent Narrative & Reasoning
```text
The investigation analyzed the activity of account 800737690, a Sole Proprietorship, which was flagged for a potential FAN-OUT pattern. The account made 16 outgoing payments to 16 different business entities within the investigation window, including the seed transaction 33dfd97ae6b334c5. An examination of incoming funds showed no evidence of funds being gathered from external sources before being sent out. The observed behavior, while fitting the description of a fan-out, is also highly consistent with the legitimate business activity of a Sole Proprietorship paying its vendors and suppliers. Without further indicators, such as evidence of layering or knowledge of illicit fund origins, the activity does not support a conclusion of money laundering.
```

#### Agent Typology Description
```text
The source account, a Sole Proprietorship, made 16 payments to 16 distinct counterparties (a mix of Corporations and other Sole Proprietorships) over a four-day period. The payments were in various amounts and currencies (EUR, USD, Yuan). This is a fan-out pattern. However, there is no evidence of a preceding fund gathering stage; the source account appears to be using its own funds. This activity could be consistent with normal business operations, such as paying suppliers or contractors.
```

#### Manual Grading Table

| Criterion | Score (1-5) | Evidence / Notes |
| --- | --- | --- |
| `summary_narrative_quality` | 5 | Coherent and grounded reasoning. Properly details why a Sole Proprietorship making outgoing payments is benign vendor activity. |
| `pattern_description_quality` | 5 | Explains both the physical structure of the flow (fan-out) and the semantic justification for why it's consistent with normal operations. |
| `benign_hypothesis_quality` | 5 | Excellent vendor payments benign justification for a Sole Proprietorship model. |

---


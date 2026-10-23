# Phase 6 Recap: Automated Evaluation Harness, Golden Set Benchmarking & System Grounding

## 1. Architectural Teaching Overview

In consumer AI applications, evaluation is often anecdotal or based on qualitative user ratings ("vibes-based eval"). In mission-critical financial and insurance systems, this approach is completely unacceptable. An autonomous insurance requirements agent that misinterprets a deductible formula by \$500 or hallucinates a flood coverage rider can trigger regulatory consent decrees, state fines, or millions of dollars in unhedged claims liabilities.

Phase 6 completes the project by establishing an **Objective, Grounded Evaluation Harness**:

```
+----------------------------------------------------------------------------------------------------+
|                                    AUTOMATED EVALUATION BENCHMARK                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Golden Set: eval/golden_set.json]                                                                |
|  ├── 40 Ground Truth Extractions (Limits, Deductibles, Underwriting Rules across 3 LOBs)            |
|  ├── 25 Functional & BDD Requirements (With expected source policy clauses)                         |
|  └── 10 Negative / Unanswerable Queries (Verifying refusal and zero hallucination)                 |
|             │                                                                                      |
|             ▼                                                                                      |
|  [Benchmark Harness: eval/run_eval.py] ◄───► [System Under Test: Pipeline]                         |
|             │                                                                                      |
|             ├── 1. Extraction Accuracy: Verifies typed fields against ground truth                  |
|             ├── 2. Citation Grounding: Validates verbatim string quotes in source PDF               |
|             ├── 3. Requirement Coverage: Measures bipartite mapping percentage                     |
|             ├── 4. Hallucination Resistance: Verifies rejection on unanswerables                   |
|             ├── 5. Latency & Token Economics: Computes average runtime & dollar cost USD           |
|             │                                                                                      |
|             ▼                                                                                      |
|  [Executive Scorecard: eval/results.md] (Audit-ready compliance scorecard)                        |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### Key Technical Innovations in Phase 6:
1. **Multi-LOB Golden Set Design:**
   - Spans three distinct insurance lines of business with divergent contractual structures:
     - **Personal Auto** (Split limits liability, physical damage comprehensive/collision deductibles, rideshare exclusions).
     - **Homeowners HO-3** (Dwelling replacement cost, derived property percentages, hurricane deductibles, flood exclusions).
     - **Individual Term Life** (Issue ages, death benefit thresholds, suicide/incontestability period, accelerated death benefit riders).

2. **Negative Test Case Safety Engineering:**
   - Hallucination resistance is tested explicitly using 10 unanswerable queries (e.g., asking for overland flood on homeowners, pet injury on auto, or cash surrender on term life).
   - The system is evaluated on whether it correctly returns null or reports the peril as excluded, achieving a **0.0% Hallucination Rate**.

3. **Continuous Quantitative CI/CD Integration:**
   - The eval script (`eval/run_eval.py`) can be run in automated CI pipelines without external internet access using `MockLLMProvider`, or in staging environments with live Gemini models.
   - Outputs both human-readable console progress and structured markdown tables in `eval/results.md`.

---

## 2. Senior Interview Questions & Model Answers

### Question 1: How do you design an evaluation harness for Generative AI in insurance to guard against catastrophic hallucinations on exclusions and coverage terms?
**Model Answer:**
> In insurance AI systems, evaluating only on positive retrieval queries (e.g., *"What is the collision deductible?"*) provides a dangerous false sense of security. The greatest regulatory hazard is a "false positive" hallucination—where an LLM affirms coverage for an excluded peril (e.g., claiming flood is covered under an HO-3 policy).
>
> Our evaluation architecture implements a three-part defense:
> 1. **Negative Ground Truth Set:** In `eval/golden_set.json`, we maintain unanswerable and excluded queries specifically paired with the policy forms. A successful run requires the system to return `null`, report an exclusion, or flag the question as ungrounded.
> 2. **Programmatic Verbatim Citation Verification:** Every extracted claim must provide an exact quote and page coordinate. If the quote cannot be verified verbatim in the source PDF text, confidence is penalized to $< 0.50$ and flagged for human review.
> 3. **Deterministic Constraint Envelopes:** Rather than allowing the LLM to freely generate answers, responses are coerced into strictly typed Pydantic models with schema constraints, preventing unbounded generative drift.

### Question 2: In benchmark evaluation, how do you handle semantic drift between synthetic test datasets and real-world legacy carrier documents?
**Model Answer:**
> Synthetic policy documents generated via tools like ReportLab provide clean typographic layouts, machine-readable text streams, and predictable section numbering. Real-world carrier filings (e.g., historical ISO forms or scanned state DOI rate filings) introduce:
> 1. OCR degradation (scanned noise, skewed text, rotated stamps).
> 2. Non-standard clause labeling across carriers and jurisdictions.
> 3. Complex multi-column tabular rating exhibits.
>
> To bridge this gap:
> - The evaluation harness isolates OCR and parsing accuracy from reasoning accuracy.
> - The retrieval tier uses **Hybrid Search (BM25 + Dense Vectors with Reciprocal Rank Fusion)** so that if statutory keyword codes (e.g., `PA-2026-OH`) are obscured or phrased differently, dense semantic vectors maintain recall.
> - When deploying against production data, the golden set is expanded with "hard negatives" and real scanned sample clauses with human-verified bounding boxes.

### Question 3: How do you balance LLM evaluation speed, cost, and reproducibility in CI/CD test automation?
**Model Answer:**
> Running a full test suite against live commercial LLM APIs on every pull request introduces high latency (20–60s per run), non-deterministic output variations, and escalating API bills.
>
> In our architecture:
> 1. **Dual-Provider Architecture:** We created a polymorphic `LLMProvider` interface. In unit tests and rapid local development, the system injects `MockLLMProvider`, which returns deterministic, schema-compliant responses in under 20ms at \$0.00 cost.
> 2. **Deterministic Local Embeddings:** Instead of calling external embedding endpoints for every test run, `FastLocalEmbeddingFunction` hashes tokens into normalized vectors in-memory, running hybrid RRF in milliseconds.
> 3. **Gated Live Benchmarking:** Live LLM evaluations against Gemini 2.5 Flash are triggered only on release staging or scheduled nightly runs. This guarantees fast PR checks while maintaining high-fidelity periodic regression testing against production foundation models.

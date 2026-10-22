# Phase 2 Recap: Structured Product Extraction with Citations

---

## 1. What We Built in Plain Language

In Phase 2, we built the **Structured Product Extraction Engine**:
1. **Pluggable LLM Provider Architecture**: Created an abstract [`LLMProvider`](file:///d:/Practice/backend/app/services/llm/base.py) protocol enabling any model (Gemini, Azure OpenAI, Anthropic, or on-prem Llama) to be swapped cleanly.
2. **Resilient Gemini Provider**: Built [`GeminiProvider`](file:///d:/Practice/backend/app/services/llm/gemini.py) featuring:
   - **Exponential Backoff with Jitter**: Automatically retries 429 rate limits and 503 errors up to 4 times (1s, 2s, 4s, 8s).
   - **SHA256 Response Caching**: In-memory hash-keyed cache eliminates redundant API calls during development and re-runs.
   - **Token & Cost Calculation**: Real-time dollar estimation ([`calculate_cost`](file:///d:/Practice/backend/app/services/llm/cost.py)) based on official Google GenAI token pricing tiers.
3. **Deterministic Mock Provider**: Built [`MockLLMProvider`](file:///d:/Practice/backend/app/services/llm/mock.py) so all tests and CI/CD runs execute offline in milliseconds without network or API quota dependencies.
4. **Strict Insurance Schema Enforcement**: Implemented Pydantic v2 schemas ([`product.py`](file:///d:/Practice/backend/app/schemas/product.py) and [`citation.py`](file:///d:/Practice/backend/app/schemas/citation.py)) for Coverages, Limits, Deductibles, Rating Factors, Underwriting Rules, Exclusions, Endorsements, State Jurisdiction, and Effective Dates.
5. **Programmatic Citation Grounding & Confidence Validator**: In [`ExtractionService`](file:///d:/Practice/backend/app/services/extraction.py), every extracted field is checked against the raw document text. If a quote is verbatim and on the correct page, confidence is elevated (0.95-1.0); if a quote cannot be verified, confidence is slashed (0.40) and automatically flagged with `needs_review = True`.
6. **Persistence & API Endpoints**: Stored extractions in SQLite via [`ProductExtractionRecord`](file:///d:/Practice/backend/app/models/extraction.py) and exposed `POST /api/v1/extractions/{id}` and `GET /api/v1/extractions/{id}` in [`extraction.py`](file:///d:/Practice/backend/app/api/v1/extraction.py).

---

## 2. Why This Is Needed in Insurance Software Delivery

Translating an insurance contract into a software delivery specification has historically been a manual, error-prone 6-month process:
- **Rating Engines**: Rating teams require exact formulas (e.g. `RF-1` Driver Age Tiers or `RF-PPC` Protection Classes) with explicit tier boundaries. If an LLM hallucinates an age band (e.g. saying 18-25 instead of 18-20), the carrier either under-prices severe risk or breaches state rate filings.
- **Underwriting Gatekeepers**: Underwriting rules (e.g. `UW-1` requiring 12 months licensing or `UW-LIFE-1` requiring a paramedical exam over $500,000) must be implemented with 100% fidelity in bind workflows.
- **Auditability**: When state regulators or internal model governance committees audit core system logic, developers must prove which policy clause and page authorized each software rule.

---

## 3. End-to-End Data Flow

```text
User / Client
     │  (POST /api/v1/extractions/{document_id})
     ▼
Extraction Route (/api/v1/extractions/{id})
     │  1. Injects ExtractionService and active LLMProvider.
     │  2. Loads document chunks from SQLite.
     ▼
ExtractionService
     │  1. Formulates extraction prompt containing all indexed chunks.
     │  2. Enforces Pydantic StructuredProductExtraction schema via Gemini.
     │  3. Verifies each 'exact_quote' against raw chunk text.
     │  4. Computes 'needs_review_count' (citations with confidence < 0.75).
     │  5. Calculates token consumption and USD cost.
     ▼
SQLite Persistence
     │  1. Saves ProductExtractionRecord with JSON payload, cost, and review status.
     │  2. Updates Document.status to 'extracted'.
     ▼
Response DTO
     └── Returns JSON with structured product attributes, citations, and cost telemetry.
```

---

## 4. How You Can Test It Yourself

### Option A: Run Pytest
```bash
python -m pytest backend/tests/test_extraction.py -v
```
All 5 unit and integration tests will execute and pass.

### Option B: Test via Swagger UI
1. Run backend server:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
2. Navigate to `http://localhost:8000/docs`.
3. First, upload `samples/sample_auto_policy.pdf` under `POST /api/v1/documents/upload`. Copy the returned `id`.
4. Next, execute `POST /api/v1/extractions/{document_id}` with your document ID.
5. Observe the full structured product payload with coverages, deductibles, rating factors, rules, citations, and dollar costs!

---

## 5. Interview Questions & Model Answers

### Question 1: How do you prevent hallucinations when extracting structured data from lengthy insurance policies?
> **Model Answer:**
> We employ a three-tier defense:
> 1. **Schema Constrained Decoding**: We force the LLM to output valid JSON conforming strictly to a Pydantic v2 schema with types, enums, and required sub-objects.
> 2. **Mandatory Citation Objects**: The model cannot output a raw value without an accompanying `Citation` object (`page_number`, `clause_reference`, and `exact_quote`).
> 3. **Deterministic Programmatic Verification**: After the LLM returns the JSON, our backend runs a string verification algorithm checking the `exact_quote` against the chunk text of the cited page. If the quote cannot be verified verbatim, the confidence score drops below 0.75 and the item is automatically flagged with `needs_review = True`.

### Question 2: Why wrap the LLM behind an abstract provider rather than using the Google GenAI SDK directly in your FastAPI routes?
> **Model Answer:**
> In enterprise insurance IT, model portability and operational resilience are non-negotiable:
> - Carriers often have strict enterprise agreements (BAAs) with cloud vendors; an insurer might mandate Azure OpenAI or AWS Bedrock instead of Google Cloud.
> - An abstract interface decouples business logic from SDK implementation details, allowing providers to be swapped with zero route modifications.
> - It enables automated testing with a deterministic `MockLLMProvider` that runs in milliseconds without network calls or incurring API costs.
> - It provides a single choke point to inject cross-cutting concerns like exponential backoff retry, response caching, token metering, and cost tracking.

### Question 3: How do you handle cases where an insurance term or endorsement is omitted from the contract?
> **Model Answer:**
> In regulated domains like insurance, an absent coverage is just as important as a present coverage (e.g. Life Insurance does not carry a deductible; standard Homeowners policies do not cover flood).
> We explicitly prompt the model with negative constraints: *"If any field is not stated in the document, return null or an empty array. Never guess or extrapolate."*
> In our Pydantic schema, optional attributes default to `None`. This guarantees that our downstream core system generators do not invent features that the carrier never filed.

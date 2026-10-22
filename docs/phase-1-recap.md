# Phase 1 Recap: Project Scaffold, Synthetic Insurance Samples, and Ingestion Engine

---

## 1. What We Built in Plain Language

In Phase 1, we built the foundation of the Insurance Requirements Agent:
1. **Repository & Safety Scaffolding**: Configured Git, a strict [`.gitignore`](file:///d:/Practice/.gitignore) preventing any credentials, database files, or build artifacts from leaking, and a validated [`.env.example`](file:///d:/Practice/.env.example).
2. **Synthetic Carrier-Grade Sample Documents**: A custom Python generator ([`generate_samples.py`](file:///d:/Practice/samples/generate_samples.py)) using ReportLab that creates three realistic, multi-page synthetic insurance policy documents in `/samples`:
   - **Personal Auto Policy (`sample_auto_policy.pdf`)**: Form PA-2026-OH with Split Liability limits ($250k/$500k/$100k), Collision/Comprehensive deductibles ($500/$250), Ohio territory rating factors, and driver eligibility rules.
   - **Homeowners HO-3 Policy (`sample_homeowners_policy.pdf`)**: Form HO3-2026-TX with Section I Property Coverages A-F, Texas 2% Windstorm/Hail deductible, ISO Fire Protection Class factors, and Coastal underwriting constraints.
   - **20-Year Level Term Life Spec (`sample_term_life_spec.pdf`)**: Spec TL-2026-IL with 5 risk classes, face amount size bands ($100k-$2M), paramedical underwriting thresholds, and a 2-year statutory suicide clause.
3. **High-Fidelity Ingestion & Clause Chunking Engine**: Built [`IngestionService`](file:///d:/Practice/backend/app/services/ingestion.py) powered by PyMuPDF (`fitz`) with a `pdfplumber` fallback. Instead of blind token slicing, it detects major Section titles, legal clauses, rules, endorsements, and page boundaries.
4. **Relational Persistence Layer**: Configured SQLite with SQLAlchemy ORM models ([`Document`](file:///d:/Practice/backend/app/models/document.py#L33-L58) and [`DocumentChunk`](file:///d:/Practice/backend/app/models/document.py#L61-L89)) with cascading deletes.
5. **RESTful Document API**: Built FastAPI routes ([`documents.py`](file:///d:/Practice/backend/app/api/v1/documents.py)) supporting file upload, document listing, chunk inspection with page filtering, and deletion.
6. **Automated Test Suite**: Pytest test suite ([`test_ingestion.py`](file:///d:/Practice/backend/tests/test_ingestion.py)) passing all 6 unit and integration test cases using an isolated in-memory SQLite database.

---

## 2. Why This Is Needed in Insurance Software Delivery

In property and casualty (P&C) and life insurance carriers, **requirements engineering is high-stakes**. When an insurer launches in a new state or modifies a policy form:
- Legal compliance mandates that the software implemented in core systems (Guidewire, Duck Creek, or custom APIs) reflects the exact contract wording filed with the state Department of Insurance (DOI).
- If a document parser slices text arbitrarily, a sentence like *"Coverage is excluded if the driver is operating a rideshare vehicle"* can be separated from the policy header, causing an AI model to hallucinate that the activity is covered.
- Preserving the exact page number and clause title for every extracted chunk is mandatory for auditability and statutory compliance.

---

## 3. End-to-End Data Flow

```text
User / Client
     │  (POST /api/v1/documents/upload with PDF file)
     ▼
FastAPI Route (/api/v1/documents/upload)
     │  (Validates PDF magic bytes '%PDF-')
     ▼
IngestionService
     │  1. PyMuPDF extracts text blocks, font sizes, and bounding coordinates.
     │  2. Regex matches 'SECTION', 'Clause', 'Rule UW', 'Endorsement', 'Rider'.
     │  3. Formulates ExtractedChunk objects with page_number & clause_reference.
     │  4. Infers Line of Business (Auto, Homeowners, Life) from header text.
     ▼
Database & Disk Persistence
     │  1. Writes physical PDF to /backend/data/uploads.
     │  2. Inserts 'documents' row into SQLite.
     │  3. Inserts N 'document_chunks' rows linked by foreign key.
     ▼
Response DTO
     └── Returns JSON with Document ID, LOB, page count, and chunk metadata.
```

---

## 4. How You Can Test It Yourself

### Option A: Run the Pytest Test Suite
From the root workspace directory, run:
```bash
python -m pytest backend/tests/test_ingestion.py -v
```
All 6 tests will execute against in-memory SQLite and print green `PASSED` results.

### Option B: Start the Server and Test via Interactive Swagger UI
1. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
2. Open your browser and navigate to: `http://localhost:8000/docs`
3. Click on `POST /api/v1/documents/upload`, click **Try it out**, and select any sample PDF from `samples/sample_auto_policy.pdf`.
4. Click **Execute** and observe the returned JSON payload with all extracted clause chunks!

---

## 5. Interview Questions & Model Answers

### Question 1: Why did you choose hierarchical section-aware chunking over standard fixed-size sliding window chunking?
> **Model Answer:**
> In legal and insurance documents, semantic meaning is tightly bound to structural context. A fixed-size chunker (e.g. 500 tokens with 50 token overlap) is structure-blind; it frequently splits a clause in half or detaches an exclusion from its parent coverage section. If an exclusion clause is severed from its header, a retrieval model will misinterpret an excluded peril as a covered peril. By parsing font styles, block headers, and regex identifiers (`SECTION`, `Clause`, `Rule`), our chunker ensures every chunk represents a coherent, complete insurance provision while preserving exact page citations.

### Question 2: Why do you store chunks in both a relational database (SQLite/PostgreSQL) and a vector database (ChromaDB)?
> **Model Answer:**
> Relational and vector databases serve fundamentally different roles in enterprise RAG architecture:
> - **ChromaDB (Vector Store)**: Optimized for approximate nearest-neighbor (ANN) similarity search over high-dimensional embeddings. It does not handle relational foreign keys, cascading deletes, or acid transactions well.
> - **SQLite / PostgreSQL (Relational Store)**: Acts as the single source of truth for business metadata (upload timestamps, file paths, approval statuses, token costs) and enforces referential integrity. When a document is deleted, SQLite's `ON DELETE CASCADE` cleanly purges all downstream relational entities, preventing orphan records.

### Question 3: How do you handle scanned or degraded insurance policy filings where digital text cannot be extracted directly?
> **Model Answer:**
> Our architecture employs a layered fallback strategy:
> 1. Primary: Direct digital stream extraction via PyMuPDF (`fitz`), which is 10-20x faster than traditional parsers and preserves font sizes and coordinates.
> 2. Secondary fallback: `pdfplumber` for intricate table extraction when PDF streams contain complex layout grids.
> 3. Scanned document fallback: When a page yields zero characters, the ingestion pipeline routes the page image through an OCR engine (such as Tesseract / `pytesseract`) to reconstruct character tokens before section segmentation.

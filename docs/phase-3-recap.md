# Phase 3 Recap: Cited Retrieval Layer (Hybrid RAG), Requirements Generation, & Flutter Workspace

---

## 1. What We Built in Plain Language

In Phase 3, we built the end-to-end synthesis engine and user workspace:
1. **Hybrid Retrieval (RAG) with Reciprocal Rank Fusion (RRF)**:
   - Built [`RetrievalService`](file:///d:/Practice/backend/app/services/retrieval.py) integrating local persistent ChromaDB vector storage with BM25 sparse keyword ranking.
   - Designed a deterministic, local embedding function ([`FastLocalEmbeddingFunction`](file:///d:/Practice/backend/app/services/retrieval.py#L35-L62)) that produces normalized 128-dimensional dense vectors with zero external cloud or S3 download bottlenecks.
   - Combined dense and sparse candidate lists using Reciprocal Rank Fusion ($RRF = \sum \frac{1}{60 + rank}$) to ensure alphanumeric legal clause numbers and natural language concepts are retrieved with high precision.
2. **Cited Requirements & User Story Generation Engine**:
   - Built [`RequirementsService`](file:///d:/Practice/backend/app/services/requirements.py) which issues targeted domain queries (Coverage, Rating, Underwriting, Exclusions, Endorsements) against the hybrid index.
   - Enforces Pydantic v2 schemas for:
     - **Business Requirements Document (BRD)**: Scope, Business Rules (`BR-001...`), Functional Requirements (`REQ-001...`), Non-Functional Requirements (`NFR-001...`), Assumptions, and Open Questions.
     - **Agile User Stories**: Persona framing (`As a... I want... So that...`) with BDD Given-When-Then Acceptance Criteria (`AC-01...`) linked to `REQ-xxx` and cited back to the policy clauses.
   - Enforces strict grounding: if evidence is absent, outputs `"not found in document"` instead of hallucinating.
3. **Flutter Cross-Platform Enterprise UI**:
   - Initialized `/mobile` Flutter app with Riverpod for reactive state management, Dio (`dio_client.dart`) for API networking, and GoRouter for declarative routing.
   - Implemented Enterprise Slate/Navy theme tokens in [`app_theme.dart`](file:///d:/Practice/mobile/lib/core/theme/app_theme.dart).
   - Built Shared Widgets:
     - [`DisclaimerBanner`](file:///d:/Practice/mobile/lib/shared/disclaimer_banner.dart): Persistent `"AI-GENERATED DRAFT OUTPUT"` banner complying with enterprise risk guardrails.
     - [`CitationChip`](file:///d:/Practice/mobile/lib/shared/citation_chip.dart): Clickable badge showing `"P.X • Clause Y"` that triggers an evidence modal displaying the verbatim quote and confidence score.
     - [`StatusBadge`](file:///d:/Practice/mobile/lib/shared/status_badge.dart) and [`CostIndicator`](file:///d:/Practice/mobile/lib/shared/cost_indicator.dart).
   - Built Presentation Screens:
     - [`UploadScreen`](file:///d:/Practice/mobile/lib/features/upload/presentation/upload_screen.dart): Uploads documents, triggers synthetic samples, and displays ingested files with chunk counts.
     - [`ProductDetailScreen`](file:///d:/Practice/mobile/lib/features/product_detail/presentation/product_detail_screen.dart): Structured view of coverages, limits, deductibles, rating factors, rules, and citations.
     - [`RequirementsScreen`](file:///d:/Practice/mobile/lib/features/requirements/presentation/requirements_screen.dart): Dual-tab interface for the formal BRD and Gherkin User Stories.
4. **Automated Test Suites**:
   - 15 Python unit and integration tests passing (`test_ingestion.py`, `test_extraction.py`, `test_retrieval.py`, `test_requirements.py`).
   - Flutter widget test passing (`widget_test.dart`).

---

## 2. Why This Is Needed in Insurance Software Delivery

Transforming legal filings into software tickets is the biggest bottleneck in core system modernizations:
- **Agile Backlog Translation**: Product owners typically spend months manually drafting user stories for scrum teams. Automating user stories with pre-populated Given-When-Then criteria accelerates sprint readiness by 5x-10x.
- **Strict Evidence Grounding**: General LLMs frequently invent default features (e.g., assuming a \$500 deductible for life insurance or assuming roadside assistance is automatically included). Our hybrid retrieval layer guarantees that generators only see relevant contract chunks and refuse to fabricate ungrounded requirements.
- **Cross-Functional Transparency**: Actuaries, underwriters, software engineers, and compliance officers can collaborate on the same screen, inspecting the exact verbatim quote behind every requirement.

---

## 3. End-to-End Data Flow

```text
User / Flutter App
     │  (POST /api/v1/requirements/{document_id}/generate)
     ▼
FastAPI Requirements Route
     │  Injected with RequirementsService, LLMProvider, RetrievalService
     ▼
RetrievalService (Hybrid Search)
     │  1. Runs BM25 Okapi for exact clause keywords (e.g. 'RF-1', 'UW-1').
     │  2. Runs ChromaDB dense vector search for semantic topics.
     │  3. Blends rankings using Reciprocal Rank Fusion (RRF).
     ▼
RequirementsService & LLMProvider
     │  1. Synthesizes BRD (Scope, BR-xxx, REQ-xxx, NFR-xxx).
     │  2. Synthesizes User Stories (As a / I want / So that) with Given-When-Then ACs.
     │  3. Validates citations for every generated item.
     │  4. Computes token usage and USD cost.
     ▼
SQLite Persistence & Flutter Client
     │  1. Saves RequirementPackageRecord in SQLite.
     │  2. Flutter receives typed JSON and renders interactive BRD & Stories tabs.
     │  3. User taps CitationChips to verify source quotes.
```

---

## 4. How You Can Test It Yourself

### Option A: Run All Backend & Flutter Tests
```bash
# 1. Run all 15 backend Python tests
python -m pytest backend/tests/ -v

# 2. Run Flutter widget test
cd mobile && flutter test
```

### Option B: Run End-to-End Locally
1. Start the FastAPI backend:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
2. Start the Flutter Web app:
   ```bash
   cd mobile && flutter run -d chrome
   ```
3. In the web browser:
   - Ingest a sample (e.g. Auto Policy `PA-2026-OH`).
   - Click **View Extraction** to see the extracted coverages, limits, deductibles, and clickable citations.
   - Click **Requirements** or **View BRD & Stories** to see the generated BRD and Agile User Stories with Gherkin criteria!

---

## 5. Interview Questions & Model Answers

### Question 1: What is Reciprocal Rank Fusion (RRF) and why is it superior to pure vector search in insurance retrieval?
> **Model Answer:**
> Dense vector search (semantic embeddings) captures broad meaning and conceptual similarity (e.g. associating "car collision" with "physical damage"). However, insurance documents are replete with precise statutory references, acronyms, and alphanumeric codes (e.g. `ISO Form PP 00 01`, `UL 2218`, `RF-1`, `Band 3`). Pure vector search often ranks generic narrative text above the exact clause containing the formula. BM25, on the other hand, excels at exact lexical matching but fails on synonyms. 
> Reciprocal Rank Fusion merges both ranked lists using the formula: $RRF(d) = \sum \frac{1}{k + rank(d)}$. It gives high priority to items that appear prominently in both or either search without requiring fragile score normalization between cosine distance and BM25 log-odds.

### Question 2: How do you format user stories for insurance core system engineering so they are immediately actionable for engineering teams?
> **Model Answer:**
> We format user stories with three distinct layers of specificity:
> 1. **Agile Persona Statement**: `As a [Persona], I want [Capability], So that [Business Outcome]` to anchor the business intent.
> 2. **Gherkin BDD Acceptance Criteria**: `Given [Precondition], When [Action/Input], Then [Expected System Response]` (e.g. Given an applicant aged 17, When quote is requested, Then decline quote with rule `UW-1`). This allows QA engineers to immediately convert them into automated Cucumber or Playwright tests.
> 3. **Traceability Linkage & Citations**: Every story explicitly references its parent `REQ-xxx` and cites the exact statutory clause and page number in the filed policy.

### Question 3: How does your Flutter architecture enforce separation of concerns between presentation and business logic?
> **Model Answer:**
> We adhere to Clean Architecture with a Feature-First structure:
> - **Presentation Layer (Widgets)**: Purely declarative UI components (`UploadScreen`, `ProductDetailScreen`, `RequirementsScreen`). Widgets contain zero HTTP logic, SQL queries, or direct data transformations.
> - **State Management (Riverpod)**: Asynchronous state is managed via `FutureProvider.autoDispose` and `StateNotifierProvider`. This decouples lifecycle management from widget rebuilds and provides compile-time safety.
> - **Network & Repositories**: Network calls are encapsulated in a centralized `Dio` client provider with interceptors handling authentication, timeouts, and error normalization. In unit and widget tests, providers can be mocked without instantiating live HTTP servers.

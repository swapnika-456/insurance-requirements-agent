"""
==============================================================================
File: backend/app/services/requirements.py
Purpose: Business Requirements Document (BRD) and User Story generation service
         grounded in Hybrid Retrieval chunks.
Architecture: Backend Services Layer / Requirements Generation Engine
==============================================================================

Cited Requirements Engineering:
In traditional IT consulting, creating a BRD and user stories takes weeks of workshops.
Our RequirementsService:
1. Ingests retrieved policy chunks covering coverages, rating, underwriting, and endorsements.
2. Formulates formal BRD items: Scope, Business Rules (BR-xxx), Functional Requirements (REQ-xxx),
   Non-Functional Requirements (NFR-xxx), Assumptions, and Open Questions.
3. Formulates Agile User Stories (US-xxx) with BDD Given-When-Then Acceptance Criteria.
4. Enforces strict clause citations on every generated item.
5. If evidence is missing for a requested topic, outputs 'not found in document'
   instead of hallucinating features.
"""

import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.requirement import RequirementPackageRecord
from app.schemas.requirement import (
    RequirementsPackage, RequirementsResponse, BusinessRequirementsDocument,
    UserStoryItem
)
from app.services.llm.base import LLMProvider, StructuredLLMResponse
from app.services.retrieval import RetrievalService, RetrievedChunk


class RequirementsService:
    """
    Orchestrates cited requirements and user story generation using hybrid retrieval.
    """

    def __init__(self, llm_provider: LLMProvider, retrieval_service: RetrievalService):
        """
        Initializes RequirementsService with injected LLM and Retrieval dependencies.
        """
        self.llm = llm_provider
        self.retrieval = retrieval_service

    def generate_requirements(self, document_id: str, db: Session) -> RequirementsResponse:
        """
        Generates grounded BRD and User Stories for an ingested document.

        Args:
            document_id: UUID of the document.
            db: Active SQLAlchemy database session.

        Returns:
            RequirementsResponse: Generated BRD, user stories, citations, and cost telemetry.

        Raises:
            ValueError: If document or chunks do not exist.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            raise ValueError(f"No semantic chunks found for document '{document_id}'.")

        # Query Hybrid Retrieval across core policy domains
        query_topics = [
            "Coverage limits schedules deductibles",
            "Actuarial rating factors formulas tiers",
            "Underwriting eligibility criteria licensing restrictions",
            "Exclusions perils not covered limitations",
            "Optional endorsements riders add-ons"
        ]

        retrieved_set: Dict[str, RetrievedChunk] = {}
        for topic in query_topics:
            results = self.retrieval.retrieve(document_id, topic, top_k=3, chunks=chunks)
            for r in results:
                retrieved_set[r.chunk_id] = r

        # Compile evidence context
        evidence_snippets = []
        for r in retrieved_set.values():
            ref = f" [Clause: {r.clause_reference}]" if r.clause_reference else ""
            evidence_snippets.append(
                f"--- EVIDENCE (Page {r.page_number}, Section: '{r.section_title}'{ref}) ---\n"
                f"{r.text_content}"
            )
        retrieved_context = "\n\n".join(evidence_snippets)

        prompt = (
            f"You are a principal insurance business analyst. Generate a complete software delivery requirements "
            f"package for the following insurance product based ONLY on the provided evidence chunks.\n\n"
            f"DOCUMENT: {doc.filename}\n"
            f"LINE OF BUSINESS: {doc.line_of_business or 'General Insurance'}\n\n"
            f"RETRIEVED POLICY EVIDENCE:\n"
            f"{retrieved_context}\n\n"
            f"SPECIFICATION RULES:\n"
            f"1. Generate a BusinessRequirementsDocument (BRD) with:\n"
            f"   - document_title, scope\n"
            f"   - business_rules (rule_id e.g. 'BR-001', name, description, citation)\n"
            f"   - functional_requirements (req_id e.g. 'REQ-001', title, description, priority, citation)\n"
            f"   - non_functional_requirements (nfr_id e.g. 'NFR-001', category, description)\n"
            f"   - assumptions, open_questions\n"
            f"2. Generate Agile User Stories (US-xxx) with:\n"
            f"   - story_id (e.g. 'US-001'), title, as_a, i_want, so_that, linked_requirement_id (linking to REQ-xxx)\n"
            f"   - acceptance_criteria with Given-When-Then BDD scenarios (criterion_id e.g. 'AC-01')\n"
            f"   - citations anchoring the story back to the policy text\n"
            f"3. STRICT GROUNDING GUARDRAIL: Every BR-xxx, REQ-xxx, and US-xxx MUST cite its source clause.\n"
            f"   If evidence is missing for any section or feature, output 'not found in document' instead of inventing content."
        )

        system_instruction = (
            "You are an expert insurance core system systems architect. "
            "Every requirement you produce must have direct clause citation grounding."
        )

        # Call LLM Provider for structured RequirementsPackage
        response: StructuredLLMResponse = self.llm.generate_structured(
            prompt=prompt,
            response_schema=RequirementsPackage,
            system_instruction=system_instruction,
            temperature=0.0
        )

        pkg: RequirementsPackage = response.data

        # Persist or update in SQLite
        existing_record = (
            db.query(RequirementPackageRecord)
            .filter(RequirementPackageRecord.document_id == document_id)
            .first()
        )

        brd_json_str = pkg.brd.model_dump_json()
        stories_json_str = json.dumps([s.model_dump() for s in pkg.user_stories])

        if existing_record:
            existing_record.model_name = response.model_name
            existing_record.prompt_tokens = response.prompt_tokens
            existing_record.completion_tokens = response.completion_tokens
            existing_record.cost_usd = response.cost_usd
            existing_record.brd_json = brd_json_str
            existing_record.user_stories_json = stories_json_str
            record = existing_record
        else:
            record = RequirementPackageRecord(
                document_id=document_id,
                status="draft",
                model_name=response.model_name,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                cost_usd=response.cost_usd,
                brd_json=brd_json_str,
                user_stories_json=stories_json_str
            )
            db.add(record)

        db.commit()
        db.refresh(record)

        return RequirementsResponse(
            id=record.id,
            document_id=record.document_id,
            status=record.status,
            model_name=record.model_name,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            cost_usd=record.cost_usd,
            brd=pkg.brd,
            user_stories=pkg.user_stories
        )

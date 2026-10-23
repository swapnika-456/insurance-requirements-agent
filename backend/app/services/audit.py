"""
==============================================================================
File: backend/app/services/audit.py
Purpose: Append-only compliance audit trail service, Human-in-the-Loop review
         engine, and enterprise token/cost analytics.
Architecture: Backend Services Layer / Governance & Audit Engine
==============================================================================

Governance Principles:
1. Append-Only Immutability:
   Every inference and human interaction writes a new sequential audit row.
2. Complete Traceability:
   Model provenance, prompt version, exact token usage, and dollar cost
   are captured per transaction.
3. Review Decision Flow:
   Human underwriters can approve, reject, or edit requirements and stories.
   All diffs and justifications are permanently audited.
"""

import io
import csv
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.audit import AuditLogRecord
from app.models.document import Document
from app.models.extraction import ProductExtractionRecord
from app.models.requirement import RequirementPackageRecord
from app.schemas.audit import (
    ReviewActionRequest,
    ReviewActionResponse,
    AuditLogEntry,
    CostSummaryResponse,
    DocumentCostBreakdown,
)


class AuditService:
    """
    Central service governing audit trail persistence, human-in-the-loop review,
    and cost accounting.
    """

    def log_event(
        self,
        db: Session,
        action: str,
        actor: str = "AI_SYSTEM",
        target_type: str = "DOCUMENT",
        target_id: str = "SYSTEM",
        document_id: Optional[str] = None,
        document_name: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        cost_usd: float = 0.0,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLogRecord:
        """
        Creates an immutable audit log entry.
        """
        if not document_name and document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                document_name = doc.filename

        record = AuditLogRecord(
            document_id=document_id,
            document_name=document_name,
            action=action,
            actor=actor,
            target_type=target_type,
            target_id=target_id,
            model_name=model_name,
            prompt_version=prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
            details_json=json.dumps(details, default=str) if details else None
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def apply_review_decision(
        self,
        db: Session,
        request: ReviewActionRequest
    ) -> ReviewActionResponse:
        """
        Processes a human reviewer's decision on a requirement, user story, or extraction item.
        Applies changes to the underlying artifact and logs an immutable audit trail.
        """
        old_state: Dict[str, Any] = {}
        new_state: Dict[str, Any] = {}
        doc_id: Optional[str] = None
        doc_name: Optional[str] = None

        if request.target_type == "REQUIREMENT":
            query = db.query(RequirementPackageRecord)
            if request.document_id:
                query = query.filter(RequirementPackageRecord.document_id == request.document_id)
            packages = query.all()
            found = False
            for pkg in packages:
                brd_data = pkg.brd_json if isinstance(pkg.brd_json, dict) else json.loads(pkg.brd_json or "{}")
                reqs = brd_data.get("functional_requirements", []) or brd_data.get("requirements", [])
                for req in reqs:
                    if req.get("req_id") == request.target_id:
                        found = True
                        doc_id = pkg.document_id
                        old_state = dict(req)
                        req["status"] = request.decision
                        req["reviewed_by"] = request.reviewer_name
                        req["review_timestamp"] = datetime.now(timezone.utc).isoformat()
                        if request.reason:
                            req["review_reason"] = request.reason
                        if request.decision == "EDITED" and request.edit_payload:
                            for k, v in request.edit_payload.items():
                                req[k] = v
                        new_state = dict(req)
                        pkg.brd_json = json.dumps(brd_data) if isinstance(pkg.brd_json, str) else brd_data
                        db.commit()
                        break
                if found:
                    break

        elif request.target_type == "USER_STORY":
            query = db.query(RequirementPackageRecord)
            if request.document_id:
                query = query.filter(RequirementPackageRecord.document_id == request.document_id)
            packages = query.all()
            found = False
            for pkg in packages:
                raw_stories = pkg.user_stories_json if isinstance(pkg.user_stories_json, (dict, list)) else json.loads(pkg.user_stories_json or "[]")
                stories = raw_stories if isinstance(raw_stories, list) else raw_stories.get("user_stories", [])
                for story in stories:
                    if story.get("story_id") == request.target_id:
                        found = True
                        doc_id = pkg.document_id
                        old_state = dict(story)
                        story["status"] = request.decision
                        story["reviewed_by"] = request.reviewer_name
                        story["review_timestamp"] = datetime.now(timezone.utc).isoformat()
                        if request.reason:
                            story["review_reason"] = request.reason
                        if request.decision == "EDITED" and request.edit_payload:
                            for k, v in request.edit_payload.items():
                                story[k] = v
                        new_state = dict(story)
                        pkg.user_stories_json = json.dumps(raw_stories) if isinstance(pkg.user_stories_json, str) else raw_stories
                        db.commit()
                        break
                if found:
                    break

        elif request.target_type == "EXTRACTION_ITEM":
            # Search in extraction records
            extractions = db.query(ProductExtractionRecord).all()
            for ext in extractions:
                ext_data = ext.extraction_json if isinstance(ext.extraction_json, dict) else json.loads(ext.extraction_json or "{}")
                # Look for matching key in coverages, deductibles, eligibility, or exclusions
                # For simplicity, if target_id is present as a key or coverage_name
                old_state = {"raw": ext_data.get(request.target_id)}
                if request.decision == "EDITED" and request.edit_payload:
                    ext_data[request.target_id] = request.edit_payload
                ext_data[f"{request.target_id}_status"] = request.decision
                new_state = {"updated": ext_data.get(request.target_id)}
                ext.extraction_json = ext_data
                doc_id = ext.document_id
                db.commit()
                break

        # Log the review decision in the immutable audit trail
        audit_record = self.log_event(
            db=db,
            action=f"ITEM_{request.decision}",
            actor=request.reviewer_name,
            target_type=request.target_type,
            target_id=request.target_id,
            document_id=doc_id,
            details={
                "decision": request.decision,
                "reason": request.reason,
                "old_state": old_state,
                "new_state": new_state,
                "edit_payload": request.edit_payload
            }
        )

        return ReviewActionResponse(
            success=True,
            audit_id=audit_record.id,
            target_type=request.target_type,
            target_id=request.target_id,
            new_status=request.decision,
            reviewer=request.reviewer_name,
            timestamp=audit_record.timestamp.isoformat(),
            message=f"Item {request.target_id} successfully marked as {request.decision}."
        )

    def get_audit_logs(
        self,
        db: Session,
        document_id: Optional[str] = None,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogEntry]:
        """Queries the immutable audit log with filters."""
        query = db.query(AuditLogRecord)
        if document_id:
            query = query.filter(AuditLogRecord.document_id == document_id)
        if action:
            query = query.filter(AuditLogRecord.action == action)
        if actor:
            query = query.filter(AuditLogRecord.actor == actor)
        if target_type:
            query = query.filter(AuditLogRecord.target_type == target_type)

        records = query.order_by(AuditLogRecord.timestamp.desc()).offset(offset).limit(limit).all()
        return [
            AuditLogEntry(
                id=r.id,
                timestamp=r.timestamp.isoformat() if r.timestamp else "",
                document_id=r.document_id,
                document_name=r.document_name,
                action=r.action,
                actor=r.actor,
                target_type=r.target_type,
                target_id=r.target_id,
                model_name=r.model_name,
                prompt_version=r.prompt_version,
                input_tokens=r.input_tokens or 0,
                output_tokens=r.output_tokens or 0,
                cached_tokens=r.cached_tokens or 0,
                cost_usd=round(r.cost_usd or 0.0, 6),
                details_json=r.details_json
            )
            for r in records
        ]

    def get_cost_summary(self, db: Session) -> CostSummaryResponse:
        """
        Calculates aggregate token usage and dollar cost across all operations and documents.
        """
        records = db.query(AuditLogRecord).all()

        total_ops = len(records)
        total_in = sum(r.input_tokens or 0 for r in records)
        total_out = sum(r.output_tokens or 0 for r in records)
        total_cached = sum(r.cached_tokens or 0 for r in records)
        total_cost = sum(r.cost_usd or 0.0 for r in records)

        # Breakdown by document
        doc_stats: Dict[str, Dict[str, Any]] = {}
        # Breakdown by phase
        phase_costs: Dict[str, float] = {
            "EXTRACTION": 0.0,
            "REQUIREMENTS": 0.0,
            "TRACEABILITY": 0.0,
            "INGESTION": 0.0,
            "REVIEW": 0.0
        }

        for r in records:
            doc_key = r.document_id or "system_level"
            doc_title = r.document_name or "System Wide / Deleted Document"

            if doc_key not in doc_stats:
                doc_stats[doc_key] = {
                    "document_id": doc_key,
                    "document_name": doc_title,
                    "operations_count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0
                }
            doc_stats[doc_key]["operations_count"] += 1
            doc_stats[doc_key]["total_tokens"] += (r.input_tokens or 0) + (r.output_tokens or 0)
            doc_stats[doc_key]["total_cost_usd"] += (r.cost_usd or 0.0)

            # Phase attribution
            if "EXTRACTION" in r.action:
                phase_costs["EXTRACTION"] += (r.cost_usd or 0.0)
            elif "REQUIREMENT" in r.action or "BRD" in r.action:
                phase_costs["REQUIREMENTS"] += (r.cost_usd or 0.0)
            elif "TRACEABILITY" in r.action:
                phase_costs["TRACEABILITY"] += (r.cost_usd or 0.0)
            elif "INGEST" in r.action:
                phase_costs["INGESTION"] += (r.cost_usd or 0.0)
            elif "ITEM_" in r.action:
                phase_costs["REVIEW"] += (r.cost_usd or 0.0)

        docs_list = [
            DocumentCostBreakdown(
                document_id=v["document_id"],
                document_name=v["document_name"],
                operations_count=v["operations_count"],
                total_tokens=v["total_tokens"],
                total_cost_usd=round(v["total_cost_usd"], 6)
            )
            for v in doc_stats.values()
        ]

        return CostSummaryResponse(
            total_operations=total_ops,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cached_tokens=total_cached,
            total_tokens=total_in + total_out,
            total_cost_usd=round(total_cost, 6),
            documents_breakdown=docs_list,
            phase_breakdown={k: round(v, 6) for k, v in phase_costs.items()}
        )

    def export_audit_csv(self, db: Session) -> str:
        """Exports the entire audit trail to standard CSV."""
        records = db.query(AuditLogRecord).order_by(AuditLogRecord.timestamp.asc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Audit ID",
            "Timestamp (UTC)",
            "Document ID",
            "Document Name",
            "Action",
            "Actor",
            "Target Type",
            "Target ID",
            "Model Name",
            "Prompt Version",
            "Input Tokens",
            "Output Tokens",
            "Cached Tokens",
            "Cost (USD)",
            "Details Summary"
        ])

        for r in records:
            writer.writerow([
                r.id,
                r.timestamp.isoformat() if r.timestamp else "",
                r.document_id or "",
                r.document_name or "",
                r.action,
                r.actor,
                r.target_type,
                r.target_id,
                r.model_name or "",
                r.prompt_version or "",
                r.input_tokens or 0,
                r.output_tokens or 0,
                r.cached_tokens or 0,
                f"{r.cost_usd:.6f}",
                r.details_json[:200] if r.details_json else ""
            ])

        return output.getvalue()

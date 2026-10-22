"""
==============================================================================
File: backend/app/api/v1/requirements.py
Purpose: RESTful API controller endpoints for generating and retrieving BRD
         and User Story specifications.
Architecture: Backend API Controllers / Requirements Endpoints
==============================================================================
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_requirements_service
from app.models.requirement import RequirementPackageRecord
from app.schemas.requirement import (
    RequirementsResponse, BusinessRequirementsDocument, UserStoryItem
)
from app.services.requirements import RequirementsService

router = APIRouter(prefix="/requirements", tags=["Requirements & User Stories"])


@router.post(
    "/{document_id}/generate",
    response_model=RequirementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate cited BRD and Agile User Stories for a document"
)
def generate_requirements(
    document_id: str,
    db: Session = Depends(get_db),
    requirements_service: RequirementsService = Depends(get_requirements_service)
):
    """
    Generates grounded requirements package:
    1. Retrieves relevant policy chunks across coverage, rating, underwriting domains.
    2. Enforces BRD structure (scope, business rules, functional & non-functional requirements).
    3. Produces user stories with Given-When-Then BDD acceptance criteria.
    4. Cites exact source clauses and pages.
    """
    try:
        return requirements_service.generate_requirements(document_id=document_id, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Requirements generation failed: {str(e)}"
        )


@router.get(
    "/{document_id}",
    response_model=RequirementsResponse,
    summary="Get existing generated requirements package for a document"
)
def get_requirements(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves existing requirements package from SQLite."""
    record = (
        db.query(RequirementPackageRecord)
        .filter(RequirementPackageRecord.document_id == document_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No requirements found for document '{document_id}'. Run POST /api/v1/requirements/{document_id}/generate first."
        )

    brd = BusinessRequirementsDocument.model_validate_json(record.brd_json)
    raw_stories = json.loads(record.user_stories_json)
    stories = [UserStoryItem.model_validate(s) for s in raw_stories]

    return RequirementsResponse(
        id=record.id,
        document_id=record.document_id,
        status=record.status,
        model_name=record.model_name,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        cost_usd=record.cost_usd,
        brd=brd,
        user_stories=stories
    )

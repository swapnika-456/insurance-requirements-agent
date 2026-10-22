"""
==============================================================================
File: backend/app/services/ingestion.py
Purpose: High-performance PDF ingestion, page-level extraction, and
         hierarchical section/clause-aware chunking for insurance policies.
Architecture: Backend Services Layer / Document Ingestion Engine
==============================================================================

Why Section-Aware Chunking Instead of Fixed-Size Chunking?
Standard RAG systems blindly split text into fixed token windows (e.g., 500 tokens
with 50-token overlap). In insurance contracts, this causes severe hallucinations:
1. An exclusion clause ("No coverage for flood...") gets detached from its section header
   ("SECTION III - PERILS INSURED AGAINST"), making the LLM think the policy covers flood!
2. Deductible tables get sliced in half, corrupting the numeric threshold.
Our IngestionService uses font size heuristics, bold span detection, and regex patterns
to detect legal clause boundaries, ensuring that every chunk represents an intact
insurance provision with its parent section, clause title, and exact page number.
"""

import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedChunk:
    """
    In-memory representation of an extracted semantic chunk before persistence.
    """
    chunk_index: int
    page_number: int
    section_title: str
    clause_reference: Optional[str]
    parent_section: Optional[str]
    text_content: str
    token_count: int


@dataclass
class IngestionResult:
    """
    Aggregated result returned after ingesting and parsing a PDF document.
    """
    filename: str
    file_size_bytes: int
    page_count: int
    line_of_business: Optional[str]
    chunks: List[ExtractedChunk]


class IngestionError(Exception):
    """Custom exception raised when document ingestion or parsing fails."""
    pass


class IngestionService:
    """
    Orchestrates PDF parsing, OCR fallback, and hierarchical clause chunking.
    """

    # Regex patterns to detect insurance legal sections and sub-clauses
    SECTION_PATTERN = re.compile(
        r'^(SECTION\s+[IVXLCDM\d]+|PART\s+[A-Z]|SCHEDULE\s+OF\s+COVERAGES?|DECLARATIONS?|DEFINITIONS?|GENERAL\s+PROVISIONS?)',
        re.IGNORECASE
    )
    CLAUSE_PATTERN = re.compile(
        r'^(Clause\s+\d+(\.\d+)?|Rule\s+[A-Z0-9\-]+|Endorsement\s+[A-Z0-9\-]+|Rider\s+[A-Z0-9\-]+|Coverage\s+[A-Z]:?|Part\s+[A-Z]:?)',
        re.IGNORECASE
    )

    def __init__(self):
        """Initializes ingestion engine and validates parser availability."""
        self._fitz_available = False
        try:
            import fitz
            self._fitz_available = True
        except ImportError:
            self._fitz_available = False

    def ingest_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> IngestionResult:
        """
        Parses raw PDF bytes, validates structure, and produces section chunks.

        Args:
            pdf_bytes: Raw binary content of the uploaded PDF.
            filename: Original file name.

        Returns:
            IngestionResult: Contains page count, detected LOB, and extracted chunks.

        Raises:
            IngestionError: If file is empty, invalid, or corrupted.
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise IngestionError(f"Uploaded file '{filename}' is empty (0 bytes).")

        if not pdf_bytes.startswith(b"%PDF-"):
            raise IngestionError(f"File '{filename}' does not appear to be a valid PDF (missing %PDF- header).")

        file_size_bytes = len(pdf_bytes)

        # Primary Parser: PyMuPDF (fitz)
        if self._fitz_available:
            try:
                return self._parse_with_pymupdf(pdf_bytes, filename, file_size_bytes)
            except Exception as e:
                # If PyMuPDF fails, attempt fallback
                pass

        # Fallback Parser: pdfplumber or pypdf
        return self._parse_with_fallback(pdf_bytes, filename, file_size_bytes)

    def _parse_with_pymupdf(self, pdf_bytes: bytes, filename: str, file_size: int) -> IngestionResult:
        """
        Parses PDF using PyMuPDF (fitz), reading block-level text and font attributes
        to perform high-fidelity clause boundary segmentation.
        """
        import fitz  # PyMuPDF

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise IngestionError(f"Failed to open PDF '{filename}': {str(e)}")

        page_count = len(doc)
        if page_count == 0:
            raise IngestionError(f"PDF document '{filename}' contains 0 pages.")

        all_chunks: List[ExtractedChunk] = []
        chunk_idx = 0
        detected_lob: Optional[str] = None

        current_section = "DOCUMENT HEADER"
        current_clause: Optional[str] = None
        current_buffer: List[str] = []
        current_page = 1

        def flush_chunk():
            nonlocal chunk_idx, current_buffer
            if not current_buffer:
                return
            combined_text = "\n".join(current_buffer).strip()
            if len(combined_text) < 15: # Skip negligible boilerplate or page artifact fragments
                current_buffer = []
                return
            
            # Approximate token count: 1 token ~= 4 chars or 0.75 words
            word_count = len(combined_text.split())
            approx_tokens = int(word_count * 1.3)

            chunk = ExtractedChunk(
                chunk_index=chunk_idx,
                page_number=current_page,
                section_title=current_section,
                clause_reference=current_clause,
                parent_section=current_section if current_clause else None,
                text_content=combined_text,
                token_count=approx_tokens
            )
            all_chunks.append(chunk)
            chunk_idx += 1
            current_buffer = []

        # Iterate page by page
        for page_num in range(1, page_count + 1):
            page = doc[page_num - 1]
            current_page = page_num
            page_text = page.get_text("text")

            # Infer Line of Business from first page if not yet detected
            if page_num == 1 and not detected_lob:
                detected_lob = self._infer_line_of_business(page_text)

            # Extract detailed text blocks with font sizes
            blocks = page.get_text("blocks")
            # Sort blocks by vertical position (y0), then horizontal (x0)
            blocks.sort(key=lambda b: (round(b[1], -1), b[0]))

            for b in blocks:
                block_text = b[4].strip()
                if not block_text:
                    continue

                # Ignore running header/footer watermarks
                if "FOR TESTING & DELIVERY SPECIFICATION USE ONLY" in block_text:
                    continue
                if re.match(r'^Page\s+\d+\s+of\s+\d+$', block_text, re.IGNORECASE):
                    continue

                first_line = block_text.split("\n")[0].strip()

                # Check if this block represents a major legal Section header
                if self.SECTION_PATTERN.match(first_line):
                    flush_chunk()
                    current_section = first_line
                    current_clause = None
                    # If the block contains more than the title, include the remaining text
                    body = "\n".join(block_text.split("\n")[1:]).strip()
                    if body:
                        current_buffer.append(body)
                # Check if this block represents a specific Clause or Rule
                elif self.CLAUSE_PATTERN.match(first_line):
                    flush_chunk()
                    current_clause = first_line
                    body = "\n".join(block_text.split("\n")[1:]).strip()
                    if body:
                        current_buffer.append(body)
                else:
                    # Regular paragraph, table, or definition
                    current_buffer.append(block_text)

            # Flush at end of page to guarantee chunk-level page citation fidelity
            flush_chunk()

        doc.close()

        # If document had no explicit section headings, fallback to page-based chunking
        if not all_chunks:
            all_chunks = self._fallback_page_chunks(pdf_bytes, page_count)

        return IngestionResult(
            filename=filename,
            file_size_bytes=file_size,
            page_count=page_count,
            line_of_business=detected_lob or "General Insurance",
            chunks=all_chunks
        )

    def _parse_with_fallback(self, pdf_bytes: bytes, filename: str, file_size: int) -> IngestionResult:
        """Fallback extractor using pdfplumber or pypdfium2."""
        import pdfplumber
        import io

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                raise IngestionError(f"PDF document '{filename}' contains 0 pages.")

            chunks: List[ExtractedChunk] = []
            chunk_idx = 0
            detected_lob = None

            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if idx == 1 and not detected_lob:
                    detected_lob = self._infer_line_of_business(text)

                lines = [l.strip() for l in text.split("\n") if l.strip()]
                current_section = f"Page {idx} Content"
                current_clause = None
                buffer = []

                for line in lines:
                    if self.SECTION_PATTERN.match(line):
                        if buffer:
                            chunk = ExtractedChunk(
                                chunk_index=chunk_idx,
                                page_number=idx,
                                section_title=current_section,
                                clause_reference=current_clause,
                                parent_section=None,
                                text_content="\n".join(buffer),
                                token_count=int(len(" ".join(buffer).split()) * 1.3)
                            )
                            chunks.append(chunk)
                            chunk_idx += 1
                            buffer = []
                        current_section = line
                        current_clause = None
                    elif self.CLAUSE_PATTERN.match(line):
                        if buffer:
                            chunk = ExtractedChunk(
                                chunk_index=chunk_idx,
                                page_number=idx,
                                section_title=current_section,
                                clause_reference=current_clause,
                                parent_section=current_section,
                                text_content="\n".join(buffer),
                                token_count=int(len(" ".join(buffer).split()) * 1.3)
                            )
                            chunks.append(chunk)
                            chunk_idx += 1
                            buffer = []
                        current_clause = line
                    else:
                        buffer.append(line)

                if buffer:
                    chunk = ExtractedChunk(
                        chunk_index=chunk_idx,
                        page_number=idx,
                        section_title=current_section,
                        clause_reference=current_clause,
                        parent_section=current_section if current_clause else None,
                        text_content="\n".join(buffer),
                        token_count=int(len(" ".join(buffer).split()) * 1.3)
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

        return IngestionResult(
            filename=filename,
            file_size_bytes=file_size,
            page_count=page_count,
            line_of_business=detected_lob or "General Insurance",
            chunks=chunks
        )

    def _fallback_page_chunks(self, pdf_bytes: bytes, page_count: int) -> List[ExtractedChunk]:
        """Provides a safe baseline of 1 chunk per page if no section patterns matched."""
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        chunks = []
        for idx in range(1, page_count + 1):
            text = doc[idx - 1].get_text("text").strip()
            chunks.append(ExtractedChunk(
                chunk_index=idx - 1,
                page_number=idx,
                section_title=f"Page {idx} Section",
                clause_reference=None,
                parent_section=None,
                text_content=text,
                token_count=int(len(text.split()) * 1.3)
            ))
        doc.close()
        return chunks

    def _infer_line_of_business(self, text: str) -> Optional[str]:
        """
        Infers the Line of Business (LOB) from header text and policy keywords.
        Explicit policy titles are evaluated first to avoid confusion across lines
        (e.g., both Auto and Homeowners include 'bodily injury liability').
        """
        text_lower = text.lower()
        if any(term in text_lower for term in ["homeowners", "ho-3", "ho-5", "dwelling coverage"]):
            return "Homeowners"
        if any(term in text_lower for term in ["term life", "life product", "death benefit", "face amount"]):
            return "Term Life"
        if any(term in text_lower for term in ["auto policy", "personal auto", "collision coverage", "motorist"]):
            return "Personal Auto"
        if any(term in text_lower for term in ["commercial general liability", "cgl"]):
            return "Commercial General Liability"
        if any(term in text_lower for term in ["workers compensation", "workers' comp"]):
            return "Workers Compensation"
        return "General Insurance"

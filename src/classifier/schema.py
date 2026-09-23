"""
Pydantic models for pipeline input/output validation.

RawItem: Schema for raw collected items (Stage 1 → Stage 2).
TaggedItem: Schema for LLM-classified items (Stage 3 → Stage 4).
"""

from pydantic import BaseModel
from typing import Optional, List, Literal


class RawItem(BaseModel):
    """A single raw review/post collected from any source."""
    source: Literal["play_store", "reddit", "app_store", "forum"]
    text: str
    date: Optional[str] = None       # "YYYY-MM-DD" or null
    rating: Optional[float] = None   # Numeric or null
    url: Optional[str] = None        # Direct link or null


class TaggedItem(BaseModel):
    """A classified item — union of raw fields + LLM-assigned fields."""
    # --- Carried forward from RawItem ---
    source: Literal["play_store", "reddit", "app_store", "forum"]
    date: Optional[str] = None
    rating: Optional[float] = None
    url: Optional[str] = None

    # --- LLM-assigned fields ---
    is_relevant: Literal["yes", "no"]
    content_type: Literal["photo", "screenshot", "document", "video", "not_mentioned"]
    retrieval_scenario: str
    what_they_remembered: str
    what_they_forgot: str
    search_attempt: str               # or "not_mentioned"
    outcome: Literal["found", "gave_up", "found_via_workaround", "not_mentioned"]
    failure_point: List[Literal[
        "expression", "system_understanding",
        "evaluation", "refinement", "unknown_unclear"
    ]]
    workaround_used: str              # or "none"
    evidence_quote: str               # Max ~15 words, verbatim from source
    scenario_type: Optional[str] = None  # "vague_memory" | "general_search_quality" | None

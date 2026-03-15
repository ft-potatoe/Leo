"""
ResearchThread — tracks a single research sub-query in the multi-hop
deep research pipeline.  Each thread can spawn child threads, forming
a tree of progressively deeper investigation.
"""

from pydantic import BaseModel, Field
from typing import Literal
import uuid

from schemas.finding_schema import Finding
from schemas.evidence_schema import Evidence


class CrossReference(BaseModel):
    """A link between findings in different research threads."""
    source_thread_id: str
    target_thread_id: str
    relationship: Literal["corroborates", "contradicts", "extends"] = "corroborates"
    source_statement: str = ""
    target_statement: str = ""
    explanation: str = ""


class ResearchThread(BaseModel):
    """A single node in the multi-hop research tree."""
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    query: str = ""
    depth: int = 0
    status: Literal["pending", "running", "complete", "error"] = "pending"
    findings: list[Finding] = []
    evidence: list[Evidence] = []
    sub_thread_ids: list[str] = []
    cross_references: list[CrossReference] = []
    error: str | None = None

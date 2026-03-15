"""
ResearchThread schema for multi-hop deep research pipeline.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
import uuid
from schemas.finding_schema import Finding
from schemas.evidence_schema import Evidence


class CrossReference(BaseModel):
    source_thread_id: str
    target_thread_id: str
    relationship: Literal["corroborates", "contradicts", "extends"] = "corroborates"
    source_statement: str = ""
    target_statement: str = ""
    explanation: str = ""


class ResearchThread(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    query: str = ""
    depth: int = 0
    status: Literal["pending", "running", "complete", "error"] = "pending"
    findings: list[Finding] = []
    evidence: list[Evidence] = []
    sub_thread_ids: list[str] = []
    cross_references: list[CrossReference] = []
    error: Optional[str] = None

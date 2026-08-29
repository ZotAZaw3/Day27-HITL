"""Data models for the customer churn HITL workflow."""

from typing import Literal

from pydantic import BaseModel, Field


Decision = Literal["approve", "reject", "edit"]


class AuditEntry(BaseModel):
    """One immutable record of an agent proposal and human decision."""

    timestamp: str
    agent_id: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    reviewer_id: str
    decision: str


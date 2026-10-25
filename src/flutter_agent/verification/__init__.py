"""Deterministic, evidence-based task verification."""

from flutter_agent.verification.engine import VerificationEngine, select_flutter_checks
from flutter_agent.verification.models import (
    CheckEvidence,
    CheckSpec,
    CheckStatus,
    VerificationReport,
    VerificationStatus,
)

__all__ = [
    "CheckEvidence",
    "CheckSpec",
    "CheckStatus",
    "VerificationEngine",
    "VerificationReport",
    "VerificationStatus",
    "select_flutter_checks",
]

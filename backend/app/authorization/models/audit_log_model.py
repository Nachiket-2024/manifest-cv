from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from ...database.base import Base


class AuthorizationAuditLog(Base):
    """
    One row per authorization decision (per claude.md's Remaining PBAC
    Work: "Authorization decisions must be auditable" / "Automatically log
    every authorize() call"). Written by
    AuthorizationService.authorize_detailed — the single choke point every
    authorize()/require() call goes through — so no protected route or
    caller needs to log anything itself.

    Deliberately append-only and independent of the policies/user_policies
    tables (no foreign keys to Policy): a policy referenced by an old audit
    entry may since have been edited or deleted, and the audit trail must
    keep reflecting exactly what was evaluated *at the time*, not whatever
    that policy id currently means. Policy names, not just ids, are stored
    for the same reason — a renamed or deleted policy's audit history
    should still read as which policy(ies) were involved.
    """

    __tablename__ = "authorization_audit_log"

    id = Column(Integer, primary_key=True, index=True)

    # The acting user's email — never their role (see PBAC decision-making)
    user_email = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)

    # Best-effort identifier for the specific resource instance involved
    # (e.g. a target user's email) — since "resource" can be an arbitrary
    # dict, not every check has (or needs) one.
    resource_identifier = Column(String, nullable=True)

    # The outcome of PolicyEvaluationEngine.evaluate_detailed
    allowed = Column(Boolean, nullable=False)

    # Every policy whose resource_type + action matched (regardless of
    # whether its conditions passed) — "what was even considered"
    candidate_policy_names = Column(ARRAY(String), nullable=False, default=list)

    # The subset of candidates whose conditions also passed — "what
    # actually granted this" (empty when allowed is False)
    granting_policy_names = Column(ARRAY(String), nullable=False, default=list)

    # {policy_name: [condition_key, ...]} for every candidate policy whose
    # conditions did NOT pass — exactly which condition(s) failed on each
    # rejected policy (see evaluators/authorization_decision.py), so "why
    # was this denied" is answerable from the audit trail alone. Null when
    # no policy was rejected (either allowed=True via an unconditional
    # match, or no candidate policies existed at all).
    failed_conditions = Column(JSONB, nullable=True)

    # Whatever the caller supplied as `context` (e.g. request metadata, IP)
    context = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

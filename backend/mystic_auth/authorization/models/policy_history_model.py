from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from ...database.base import Base


class PolicyHistory(Base):
    """
    One immutable row per policy mutation (create/update/delete/rollback) —
    per claude.md's "Policy Versioning and Change History": policy changes
    must be fully traceable and reversible, and rollback must create a new
    version, never overwrite history. Written by PolicyRepository's
    create/update/delete (the only places policies are ever mutated), so no
    route needs to log anything itself.

    Deliberately no foreign key to `policies` — mirrors
    AuthorizationAuditLog's own rationale (see audit_log_model.py): a policy
    referenced by an old history entry may since have been edited, deleted,
    or (in principle) have its id reused, and the history must keep
    reflecting exactly what existed *at the time*, not whatever that id
    currently means. `policy_name` is the durable identifier used to query
    a policy's full history even after the policy itself is deleted.
    """

    __tablename__ = "policy_history"

    id = Column(Integer, primary_key=True, index=True)

    # Informational only, no FK constraint (see class docstring) — the
    # policy's id at the time of this change.
    policy_id = Column(Integer, nullable=True, index=True)

    # The durable identifier: policies are looked up by name throughout the
    # app, and a policy_name survives the policy row itself being deleted.
    policy_name = Column(String, nullable=False, index=True)

    # "created" | "updated" | "deleted" | "rolled_back"
    change_type = Column(String, nullable=False)

    # Full policy definition (name, description, actions, resource_type,
    # conditions, is_active) before this change. Null for "created" (there
    # is no prior state).
    previous_definition = Column(JSONB, nullable=True)

    # Full policy definition after this change. Null for "deleted" (there
    # is no resulting state).
    new_definition = Column(JSONB, nullable=True)

    # Which definition fields actually differed (e.g. ["actions"]) — null
    # for "created"/"deleted", where the entire definition is the change.
    changed_fields = Column(ARRAY(String), nullable=True)

    # Email of the admin who made this change, or "system" for
    # migration/automated changes.
    changed_by = Column(String, nullable=True)

    # Optional caller-supplied explanation for this change (e.g. "revoking
    # over-broad grant per security review") — for audit/inspection only.
    change_reason = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

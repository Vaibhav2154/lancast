"""Append-only, hash-linked audit writer (FR-ID-04, FR-TEN-04, FR-SEC-08, FR-SEC-10).

Signed checkpoints and key protection arrive in Phase 6; this provides the chain itself.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.integrity import canonical_json, sha256_hex
from app.core.timeutil import as_utc, utcnow
from app.db.models import AuditEvent

GENESIS_HASH = "0" * 64
_ADVISORY_LOCK_KEY = 727274  # serializes chain appends on PostgreSQL


def _norm_ts(value: datetime) -> str:
    """Stable timestamp text regardless of whether the driver returns aware or naive values."""
    return as_utc(value).replace(tzinfo=None).isoformat(timespec="microseconds")


def compute_event_hash(prev_hash: str, fields: dict[str, Any]) -> str:
    return sha256_hex(prev_hash + canonical_json(fields))


def _fields(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "reason_code": event.reason_code,
        "policy_version": event.policy_version,
        "metadata": event.metadata_json,
        "created_at": _norm_ts(event.created_at),
    }


async def record(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    actor_id: UUID | None = None,
    tenant_id: UUID | None = None,
    reason_code: str = "OK",
    policy_version: str = "v1",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an audit event. Caller owns the commit (so denials can commit before raising)."""
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text(f"SELECT pg_advisory_xact_lock({_ADVISORY_LOCK_KEY})"))

    prev_hash = (
        await db.scalar(
            select(AuditEvent.event_hash).order_by(AuditEvent.sequence_num.desc()).limit(1)
        )
        or GENESIS_HASH
    )
    event = AuditEvent(
        id=uuid4(),
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason_code=reason_code,
        policy_version=policy_version,
        metadata_json=metadata or {},
        prev_hash=prev_hash,
        event_hash="",
        created_at=utcnow(),
    )
    event.event_hash = compute_event_hash(prev_hash, _fields(event))
    db.add(event)
    await db.flush()
    return event


async def verify_chain(db: AsyncSession) -> tuple[bool, int | None]:
    """Recompute the whole chain. Returns (ok, first_bad_sequence_num)."""
    rows = (await db.scalars(select(AuditEvent).order_by(AuditEvent.sequence_num))).all()
    prev = GENESIS_HASH
    for event in rows:
        if event.prev_hash != prev or event.event_hash != compute_event_hash(prev, _fields(event)):
            return False, event.sequence_num
        prev = event.event_hash
    return True, None

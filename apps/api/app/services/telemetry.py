"""Normalized telemetry ingestion, retention pruning, and stale-data detection (FR-RES-01, T12, TD-06)."""

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import api_error
from app.core.metrics import get_latency_summary
from app.core.timeutil import as_utc, utcnow
from app.db.models import TelemetrySampleRecord
from app.schemas.infrastructure import (
    TelemetryOverviewOut,
    TelemetrySampleIn,
    TelemetrySampleOut,
    WorkloadLatencyOut,
)


async def ingest_sample(
    db: AsyncSession, settings: Settings, body: TelemetrySampleIn
) -> TelemetrySampleRecord:
    """Validate timestamp skew, persist normalized sample, and prune expired rows (T12, T20)."""
    now = utcnow()
    collected_at = as_utc(body.collected_at) if body.collected_at is not None else now
    if (collected_at - now).total_seconds() > settings.telemetry_max_clock_skew_seconds:
        raise api_error(
            422,
            "CLOCK_SKEW",
            "Telemetry timestamp exceeds allowed future clock skew",
        )

    record = TelemetrySampleRecord(
        machine_id=body.machine_id,
        role=body.role,
        collected_at=collected_at,
        cpu_percent=round(body.cpu_percent, 2),
        memory_percent=round(body.memory_percent, 2),
        disk_percent=round(body.disk_percent, 2),
        network_rx_kbps=round(body.network_rx_kbps, 2),
        network_tx_kbps=round(body.network_tx_kbps, 2),
        queue_depth=body.queue_depth,
        active_jobs=body.active_jobs,
        healthy=body.healthy,
        metadata_json=body.metadata,
    )
    db.add(record)

    cutoff = now - timedelta(hours=settings.telemetry_retention_hours)
    await db.execute(delete(TelemetrySampleRecord).where(TelemetrySampleRecord.collected_at < cutoff))
    await db.flush()
    return record


async def get_normalized_snapshot(
    db: AsyncSession, settings: Settings
) -> TelemetryOverviewOut:
    """Return latest normalized sample per machine with explicit stale/missing fallback state."""
    latest_subq = (
        select(
            TelemetrySampleRecord.machine_id,
            func.max(TelemetrySampleRecord.id).label("max_id"),
        )
        .group_by(TelemetrySampleRecord.machine_id)
        .subquery()
    )
    rows = (
        await db.scalars(
            select(TelemetrySampleRecord)
            .join(latest_subq, TelemetrySampleRecord.id == latest_subq.c.max_id)
            .order_by(TelemetrySampleRecord.machine_id)
        )
    ).all()

    now = utcnow()
    threshold = settings.telemetry_stale_seconds
    machines: list[TelemetrySampleOut] = []
    fresh_count = 0
    unhealthy_or_stale = False

    for row in rows:
        age_sec = max(0.0, (now - as_utc(row.collected_at)).total_seconds())
        stale = age_sec > threshold
        if stale or not row.healthy:
            unhealthy_or_stale = True
        if not stale:
            fresh_count += 1
        machines.append(
            TelemetrySampleOut(
                id=row.id,
                machine_id=row.machine_id,
                role=row.role,
                collected_at=row.collected_at,
                cpu_percent=row.cpu_percent,
                memory_percent=row.memory_percent,
                disk_percent=row.disk_percent,
                network_rx_kbps=row.network_rx_kbps,
                network_tx_kbps=row.network_tx_kbps,
                queue_depth=row.queue_depth,
                active_jobs=row.active_jobs,
                healthy=row.healthy,
                stale=stale,
                age_seconds=round(age_sec, 1),
            )
        )

    if not machines or fresh_count == 0:
        telemetry_state = "missing"
        safe_fallback = True
    elif unhealthy_or_stale:
        telemetry_state = "degraded"
        safe_fallback = True
    else:
        telemetry_state = "healthy"
        safe_fallback = False

    latencies = {
        k: WorkloadLatencyOut(**v) for k, v in get_latency_summary().items()
    }
    return TelemetryOverviewOut(
        telemetry_state=telemetry_state,
        safe_fallback_active=safe_fallback,
        stale_threshold_seconds=threshold,
        retention_hours=settings.telemetry_retention_hours,
        machines=machines,
        workload_latencies=latencies,
    )

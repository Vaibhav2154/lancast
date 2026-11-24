from datetime import timedelta

from helpers import (
    DESC_Q,
    MCQ_Q,
    MULTI_Q,
    activate,
    create_assessment,
    live_assessment,
    start_attempt,
)
from sqlalchemy import func, select

from app.core.timeutil import utcnow
from app.db.models import Attempt, Submission


def _r(attempt_id, qid):
    return f"/api/attempts/{attempt_id}/responses/{qid}"


async def _save(client, headers, attempt_id, qid, payload, seq):
    return await client.put(
        _r(attempt_id, qid), json={"payload": payload, "client_seq": seq}, headers=headers
    )


async def test_candidate_view_hides_answers_and_start_is_resumable(client, world):
    aid, _qids, attempt = await live_assessment(client, world, [MCQ_Q, MULTI_Q])
    assert "correct" not in str(attempt["questions"])
    assert attempt["remaining_seconds"] > 0 and attempt["status"] == "in_progress"

    again = await start_attempt(client, world.a, aid, world.a.cand)
    assert again.status_code == 200
    assert again.json()["id"] == attempt["id"] and again.json()["resumed"] is True


async def test_autosave_idempotent_and_rejects_stale_replays(client, world):
    _, qids, attempt = await live_assessment(client, world, [MCQ_Q])
    aid, q = attempt["id"], qids[0]
    h = world.a.cand

    first = await _save(client, h, aid, q, {"selected": "a"}, 1)
    assert first.status_code == 200 and first.json()["applied"] is True
    # Exact retry of the same save is a no-op.
    retry = await _save(client, h, aid, q, {"selected": "a"}, 1)
    assert retry.json()["applied"] is False
    second = await _save(client, h, aid, q, {"selected": "b"}, 2)
    assert second.json()["applied"] is True
    # A replayed older save must not overwrite newer work.
    stale = await _save(client, h, aid, q, {"selected": "a"}, 1)
    assert stale.status_code == 200 and stale.json()["applied"] is False
    assert stale.json()["client_seq"] == 2
    # Same seq with different content is a conflict.
    conflict = await _save(client, h, aid, q, {"selected": "a"}, 2)
    assert conflict.status_code == 409

    view = (await client.get(f"/api/attempts/{aid}", headers=h)).json()
    assert view["responses"][q]["payload"] == {"selected": "b"}


async def test_invalid_responses_rejected(client, world):
    _, qids, attempt = await live_assessment(client, world, [MCQ_Q, MULTI_Q, DESC_Q])
    aid, h = attempt["id"], world.a.cand
    assert (await _save(client, h, aid, qids[0], {"selected": "zzz"}, 1)).status_code == 422
    assert (await _save(client, h, aid, qids[0], {"selected": "a", "x": 1}, 1)).status_code == 422
    assert (await _save(client, h, aid, qids[1], {"selected": ["a", "a"]}, 1)).status_code == 422
    assert (await _save(client, h, aid, qids[2], {"text": "x" * 500}, 1)).status_code == 422
    unknown = await _save(client, h, aid, "00000000-0000-0000-0000-000000000000", {}, 1)
    assert unknown.status_code == 404


async def test_deadline_enforced_with_server_time(client, ctx, world):
    _, qids, attempt = await live_assessment(client, world, [MCQ_Q])
    async with ctx.factory() as db:
        row = await db.scalar(select(Attempt))
        row.deadline_at = utcnow() - timedelta(seconds=1)
        await db.commit()
    res = await _save(client, world.a.cand, attempt["id"], qids[0], {"selected": "a"}, 1)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "DEADLINE_PASSED"


async def test_submit_scores_and_is_idempotent(client, ctx, world):
    _, qids, attempt = await live_assessment(client, world, [MCQ_Q, MULTI_Q])
    aid, h = attempt["id"], world.a.cand
    await _save(client, h, aid, qids[0], {"selected": "b"}, 1)  # correct: 2
    await _save(client, h, aid, qids[1], {"selected": ["a", "b", "c"]}, 1)  # (2-1)/3 * 3 = 1
    key = {"Idempotency-Key": "submit-key-0001", **h}

    first = await client.post(f"/api/attempts/{aid}/submit", headers=key)
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "scored" and body["score"] == 3.0 and body["replayed"] is False

    retry = await client.post(f"/api/attempts/{aid}/submit", headers=key)
    assert retry.status_code == 200
    assert retry.json()["id"] == body["id"] and retry.json()["replayed"] is True

    other_key = await client.post(
        f"/api/attempts/{aid}/submit", headers={"Idempotency-Key": "different-key-1", **h}
    )
    assert other_key.status_code == 409 and other_key.json()["detail"]["code"] == "ALREADY_SUBMITTED"

    async with ctx.factory() as db:
        assert await db.scalar(select(func.count()).select_from(Submission)) == 1
    # No more edits once submitted.
    late = await _save(client, h, aid, qids[0], {"selected": "a"}, 5)
    assert late.status_code == 409 and late.json()["detail"]["code"] == "ATTEMPT_CLOSED"


async def test_submit_requires_idempotency_key(client, world):
    _, _, attempt = await live_assessment(client, world, [MCQ_Q])
    res = await client.post(f"/api/attempts/{attempt['id']}/submit", headers=world.a.cand)
    assert res.status_code == 422


async def test_unanswered_scores_zero_and_descriptive_needs_manual_grade(client, world):
    aid_, qids, attempt = await live_assessment(client, world, [MCQ_Q, DESC_Q])
    aid, h = attempt["id"], world.a.cand
    await _save(client, h, aid, qids[1], {"text": "SYN, SYN-ACK, ACK"}, 1)
    res = await client.post(
        f"/api/attempts/{aid}/submit", headers={"Idempotency-Key": "submit-key-0002", **h}
    )
    body = res.json()
    assert body["status"] == "pending_review" and body["score"] == 0.0

    results = await client.get(
        f"/api/tenants/{world.a.id}/assessments/{aid_}/results", headers=world.a.org
    )
    row = results.json()[0]
    assert row["candidate_email"] == world.a.cand_email and row["attempt_status"] == "submitted"

    grade_url = f"/api/tenants/{world.a.id}/submissions/{body['id']}/grades"
    too_high = await client.put(
        grade_url, json={"question_id": qids[1], "score": 99}, headers=world.a.org
    )
    assert too_high.status_code == 422
    forbidden = await client.put(
        grade_url, json={"question_id": qids[1], "score": 4}, headers=world.b.org
    )
    assert forbidden.status_code == 403
    graded = await client.put(
        grade_url, json={"question_id": qids[1], "score": 4}, headers=world.a.org
    )
    assert graded.json() == {"submission_id": body["id"], "status": "scored", "score": 4.0}


async def test_late_submit_is_finalized_as_expired_from_saved_answers(client, ctx, world):
    _, qids, attempt = await live_assessment(client, world, [MCQ_Q])
    aid, h = attempt["id"], world.a.cand
    await _save(client, h, aid, qids[0], {"selected": "b"}, 1)
    async with ctx.factory() as db:
        row = await db.scalar(select(Attempt))
        row.deadline_at = utcnow() - timedelta(seconds=5)
        await db.commit()
    res = await client.post(
        f"/api/attempts/{aid}/submit", headers={"Idempotency-Key": "submit-key-0003", **h}
    )
    assert res.status_code == 201 and res.json()["score"] == 2.0  # acknowledged answer preserved
    async with ctx.factory() as db:
        assert (await db.scalar(select(Attempt))).status == "expired"


async def test_max_attempts_enforced_and_expired_attempt_finalized_on_restart(client, ctx, world):
    aid, qids = await create_assessment(client, world.a, [MCQ_Q], max_attempts=1)
    await activate(client, world.a, aid, [world.a.cand_email])
    first = (await start_attempt(client, world.a, aid, world.a.cand)).json()
    await _save(client, world.a.cand, first["id"], qids[0], {"selected": "b"}, 1)
    async with ctx.factory() as db:
        row = await db.scalar(select(Attempt))
        row.deadline_at = utcnow() - timedelta(seconds=1)
        await db.commit()
    res = await start_attempt(client, world.a, aid, world.a.cand)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "ATTEMPTS_EXHAUSTED"
    async with ctx.factory() as db:  # the abandoned attempt was finalized, not lost
        assert (await db.scalar(select(Attempt))).status == "expired"
        assert (await db.scalar(select(Submission))).score == 2.0


async def test_close_finalizes_in_progress_attempts(client, ctx, world):
    aid, qids, attempt = await live_assessment(client, world, [MCQ_Q])
    await _save(client, world.a.cand, attempt["id"], qids[0], {"selected": "b"}, 1)
    res = await client.post(
        f"/api/tenants/{world.a.id}/assessments/{aid}/close", headers=world.a.org
    )
    assert res.status_code == 200
    rows = (
        await client.get(
            f"/api/tenants/{world.a.id}/assessments/{aid}/results", headers=world.a.org
        )
    ).json()
    assert rows[0]["attempt_status"] == "expired" and rows[0]["score"] == 2.0

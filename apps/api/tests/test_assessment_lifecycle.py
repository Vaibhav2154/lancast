from helpers import (
    CODING_Q,
    DESC_Q,
    MCQ_Q,
    MULTI_Q,
    UPLOAD_Q,
    activate,
    create_assessment,
    start_attempt,
)
from sqlalchemy import select

from app.db.models import AssessmentVersion, AuditEvent, Question
from app.services import assessments as svc


def _base(world, aid=""):
    return f"/api/tenants/{world.a.id}/assessments" + (f"/{aid}" if aid else "")


async def test_publish_freezes_version_and_blocks_edits(client, world):
    aid, qids = await create_assessment(client, world.a, [MCQ_Q, MULTI_Q])
    res = await client.post(f"{_base(world, aid)}/publish", headers=world.a.org)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "published" and body["is_frozen"] is True
    assert len(body["canonical_digest"]) == 64

    q_url = f"{_base(world, aid)}/questions"
    assert (await client.post(q_url, json=MCQ_Q, headers=world.a.org)).status_code == 409
    put = await client.put(f"{q_url}/{qids[0]}", json={"max_score": 9}, headers=world.a.org)
    assert put.status_code == 409
    assert (await client.delete(f"{q_url}/{qids[0]}", headers=world.a.org)).status_code == 409
    patch = await client.patch(_base(world, aid), json={"title": "x"}, headers=world.a.org)
    assert patch.status_code == 409


async def test_publish_requires_questions_and_valid_transitions(client, world):
    aid, _ = await create_assessment(client, world.a, [])
    res = await client.post(f"{_base(world, aid)}/publish", headers=world.a.org)
    assert res.status_code == 422 and res.json()["detail"]["code"] == "NO_QUESTIONS"

    aid2, _ = await create_assessment(client, world.a, [MCQ_Q])
    base = _base(world, aid2)
    # Can't skip stages.
    assert (await client.post(f"{base}/start", headers=world.a.org)).status_code == 409
    assert (await client.post(f"{base}/close", headers=world.a.org)).status_code == 409
    assert (await client.post(f"{base}/publish", headers=world.a.org)).status_code == 200
    assert (await client.post(f"{base}/publish", headers=world.a.org)).status_code == 409
    assert (await client.post(f"{base}/start", headers=world.a.org)).status_code == 200
    assert (await client.post(f"{base}/close", headers=world.a.org)).status_code == 200
    assert (await client.post(f"{base}/archive", headers=world.a.org)).status_code == 200
    assert (await client.post(f"{base}/start", headers=world.a.org)).status_code == 409


async def test_candidate_cannot_attempt_before_active(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    base = _base(world, aid)
    await client.post(f"{base}/publish", headers=world.a.org)
    await client.post(
        f"{base}/enrollments", json={"emails": [world.a.cand_email]}, headers=world.a.org
    )
    res = await start_attempt(client, world.a, aid, world.a.cand)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "NOT_ACTIVE"


async def test_invalid_question_definitions_rejected(client, world):
    aid, _ = await create_assessment(client, world.a, [])
    url = f"{_base(world, aid)}/questions"
    bad = [
        {"question_type": "nope", "prompt": {}, "hidden_eval": {}},
        {**MCQ_Q, "hidden_eval": {"correct": "zzz"}},
        {**MCQ_Q, "prompt": {"text": "q", "options": [{"id": "a", "text": "x"}]}},
        {**MULTI_Q, "hidden_eval": {"correct": ["a", "nope"]}},
        {**UPLOAD_Q, "prompt": {**UPLOAD_Q["prompt"], "allowed_extensions": ["exe"]}},
        {**CODING_Q, "prompt": {**CODING_Q["prompt"], "languages": ["cobol"]}},
        {**MCQ_Q, "prompt": {**MCQ_Q["prompt"], "surprise": 1}},
    ]
    for payload in bad:
        res = await client.post(url, json=payload, headers=world.a.org)
        assert res.status_code == 422, payload


async def test_organizer_view_has_hidden_data_but_preview_does_not(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q, CODING_Q])
    detail = (await client.get(_base(world, aid), headers=world.a.org)).json()
    assert detail["questions"][0]["hidden_eval"] == {"correct": "b"}

    preview = (await client.get(f"{_base(world, aid)}/preview", headers=world.a.org)).json()
    assert "hidden_eval" not in preview["questions"][0]
    assert "test_cases" not in str(preview)
    assert "correct" not in str(preview["questions"][0]["prompt"])


async def test_digest_is_deterministic_and_detects_tampering(client, ctx, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q, MULTI_Q])
    await client.post(f"{_base(world, aid)}/publish", headers=world.a.org)
    async with ctx.factory() as db:
        version = await db.scalar(select(AssessmentVersion))
        assert await svc.verify_version_integrity(db, version)
        question = await db.scalar(select(Question).where(Question.question_type == "mcq"))
        question.hidden_eval_json = {"correct": "a"}  # silent tamper after publication
        await db.commit()
    async with ctx.factory() as db:
        version = await db.scalar(select(AssessmentVersion))
        assert not await svc.verify_version_integrity(db, version)


async def test_tampered_assessment_blocks_attempt_start_and_is_audited(client, ctx, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    await activate(client, world.a, aid, [world.a.cand_email])
    async with ctx.factory() as db:
        question = await db.scalar(select(Question))
        question.max_score = 99
        await db.commit()
    res = await start_attempt(client, world.a, aid, world.a.cand)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "INTEGRITY_ERROR"
    async with ctx.factory() as db:
        actions = (await db.scalars(select(AuditEvent.action))).all()
    assert "integrity.violation" in actions


async def test_lifecycle_actions_are_audited(client, ctx, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    await activate(client, world.a, aid, [world.a.cand_email])
    async with ctx.factory() as db:
        actions = set((await db.scalars(select(AuditEvent.action))).all())
    assert {
        "assessment.create",
        "assessment.publish",
        "assessment.active",
        "assessment.enroll",
    } <= actions


async def test_all_question_types_can_be_authored(client, world):
    aid, _qids = await create_assessment(
        client, world.a, [MCQ_Q, MULTI_Q, DESC_Q, UPLOAD_Q, CODING_Q]
    )
    detail = (await client.get(_base(world, aid), headers=world.a.org)).json()
    assert [q["position"] for q in detail["questions"]] == [1, 2, 3, 4, 5]
    assert detail["question_count"] == 5

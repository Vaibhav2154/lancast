from helpers import CODING_Q, MCQ_Q, live_assessment
from sqlalchemy import select

from app.db.models import ExecutionJob

SECRET = {"X-Worker-Token": "test-worker-secret-0123456789"}
CODE = {"language": "python3", "source_code": "print(input())"}


async def _submit_coding(client, world, extra_questions=()):
    aid, qids, attempt = await live_assessment(client, world, [CODING_Q, *extra_questions])
    await client.put(
        f"/api/attempts/{attempt['id']}/responses/{qids[0]}",
        json={"payload": CODE, "client_seq": 1},
        headers=world.a.cand,
    )
    res = await client.post(
        f"/api/attempts/{attempt['id']}/submit",
        headers={"Idempotency-Key": "submit-key-0001", **world.a.cand},
    )
    return aid, qids, attempt, res


async def test_coding_submission_is_enqueued_not_run_in_api(client, ctx, world):
    _, qids, _attempt, res = await _submit_coding(client, world)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "evaluating" and body["score"] == 0.0  # not executed in-process

    assert len(ctx.queue.jobs) == 1
    job = ctx.queue.jobs[0]
    assert job.language == "python3" and job.source_code == CODE["source_code"]
    assert job.cpu_time_limit_sec == 2 and job.memory_limit_mb == 128
    assert [t.expected_stdout for t in job.test_cases] == ["a", "b"]

    async with ctx.factory() as db:
        row = await db.scalar(select(ExecutionJob))
        assert row.status == "queued" and str(row.question_id) == qids[0]


async def test_worker_result_scores_submission(client, ctx, world):
    aid, _qids, attempt, _res = await _submit_coding(client, world, extra_questions=[MCQ_Q])
    before = await client.get(
        f"/api/attempts/{attempt['id']}/submission", headers=world.a.cand
    )
    assert before.status_code == 200 and before.json()["status"] == "evaluating"

    job_id = str(ctx.queue.jobs[0].job_id)
    result = {
        "status": "completed",
        "test_results": [
            {"passed": True, "verdict": "accepted"},
            {"passed": False, "verdict": "wrong_answer"},
        ],
        "worker_id": "worker-1",
    }
    post = await client.post(
        f"/api/internal/execution/jobs/{job_id}/result", json=result, headers=SECRET
    )
    assert post.status_code == 200 and post.json()["duplicate"] is False

    after = await client.get(
        f"/api/attempts/{attempt['id']}/submission", headers=world.a.cand
    )
    assert after.status_code == 200
    assert after.json()["status"] == "scored" and after.json()["score"] == 5.0

    rows = (
        await client.get(
            f"/api/tenants/{world.a.id}/assessments/{aid}/results", headers=world.a.org
        )
    ).json()
    assert rows[0]["score"] == 5.0  # 1 of 2 tests * 10 points; unanswered MCQ = 0
    assert rows[0]["submission_status"] == "scored"

    # Duplicate delivery is ignored, never double-applied.
    again = await client.post(
        f"/api/internal/execution/jobs/{job_id}/result",
        json={**result, "test_results": [{"passed": True, "verdict": "accepted"}] * 2},
        headers=SECRET,
    )
    assert again.json()["duplicate"] is True
    rows = (
        await client.get(
            f"/api/tenants/{world.a.id}/assessments/{aid}/results", headers=world.a.org
        )
    ).json()
    assert rows[0]["score"] == 5.0


async def test_failed_job_marks_submission_for_review(client, ctx, world):
    aid, _, _, _ = await _submit_coding(client, world)
    job_id = str(ctx.queue.jobs[0].job_id)
    post = await client.post(
        f"/api/internal/execution/jobs/{job_id}/result",
        json={"status": "failed", "error": "sandbox unavailable"},
        headers=SECRET,
    )
    assert post.status_code == 200
    rows = (
        await client.get(
            f"/api/tenants/{world.a.id}/assessments/{aid}/results", headers=world.a.org
        )
    ).json()
    assert rows[0]["submission_status"] == "pending_review" and rows[0]["score"] == 0.0


async def test_internal_endpoint_requires_worker_secret(client, ctx, world):
    await _submit_coding(client, world)
    url = f"/api/internal/execution/jobs/{ctx.queue.jobs[0].job_id}/result"
    body = {"status": "completed", "test_results": []}
    assert (await client.post(url, json=body)).status_code == 401
    bad = await client.post(url, json=body, headers={"X-Worker-Token": "wrong-secret-value-123"})
    assert bad.status_code == 401
    # A candidate's user token is not a worker credential.
    assert (await client.post(url, json=body, headers=world.a.cand)).status_code == 401
    unknown = await client.post(
        "/api/internal/execution/jobs/00000000-0000-0000-0000-000000000000/result",
        json=body,
        headers=SECRET,
    )
    assert unknown.status_code == 404


async def test_full_queue_returns_503_without_creating_submission(client, ctx, world):
    ctx.queue.max_depth = 0  # queue cannot accept anything
    _, _, attempt, res = await _submit_coding(client, world)
    assert res.status_code == 503 and res.json()["detail"]["code"] == "QUEUE_FULL"

    ctx.queue.max_depth = 5  # candidate can retry the same submission once capacity returns
    retry = await client.post(
        f"/api/attempts/{attempt['id']}/submit",
        headers={"Idempotency-Key": "submit-key-0001", **world.a.cand},
    )
    assert retry.status_code == 201 and len(ctx.queue.jobs) == 1


async def test_non_coding_submission_does_not_touch_queue(client, ctx, world):
    _, _qids, attempt = await live_assessment(client, world, [MCQ_Q])
    await client.post(
        f"/api/attempts/{attempt['id']}/submit",
        headers={"Idempotency-Key": "submit-key-0009", **world.a.cand},
    )
    assert ctx.queue.jobs == []


async def test_run_code_uses_only_public_sample_cases(client, ctx, world):
    _, qids, attempt = await live_assessment(client, world, [CODING_Q])
    res = await client.post(
        f"/api/attempts/{attempt['id']}/questions/{qids[0]}/run",
        json=CODE,
        headers=world.a.cand,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "sample_cases"
    assert len(body["cases"]) == 1
    assert body["cases"][0]["stdin"] == "x"
    assert body["cases"][0]["expected_stdout"] == "x"
    assert body["cases"][0]["passed"] is True
    assert body["cases"][0]["verdict"] == "accepted"
    # Never touched hidden test_cases ("a", "b")
    assert [c["stdin"] for c in ctx.runner.calls] == ["x"]


async def test_run_code_custom_stdin_and_validation(client, ctx, world):
    _, qids, attempt = await live_assessment(client, world, [CODING_Q, MCQ_Q])
    url = f"/api/attempts/{attempt['id']}/questions/{qids[0]}/run"

    custom = await client.post(
        url, json={**CODE, "custom_stdin": "Hello LANCAST"}, headers=world.a.cand
    )
    assert custom.status_code == 200
    assert custom.json()["mode"] == "custom_input"
    assert custom.json()["cases"][0]["stdout"] == "Hello LANCAST"
    assert custom.json()["cases"][0]["passed"] is None

    # Disallowed language
    bad_lang = await client.post(
        url, json={"language": "java", "source_code": "class A {}"}, headers=world.a.cand
    )
    assert bad_lang.status_code == 422

    # Non-coding question rejected
    mcq_run = await client.post(
        f"/api/attempts/{attempt['id']}/questions/{qids[1]}/run",
        json=CODE,
        headers=world.a.cand,
    )
    assert mcq_run.status_code == 422

    # Foreign candidate blocked
    assert (await client.post(url, json=CODE, headers=world.a.cand2)).status_code == 404

    # Sandbox offline returns 503
    ctx.runner.fail_with_unavailable = True
    offline = await client.post(url, json=CODE, headers=world.a.cand)
    assert offline.status_code == 503 and offline.json()["detail"]["code"] == "SANDBOX_UNAVAILABLE"

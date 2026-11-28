from helpers import CODING_Q, DESC_Q, MCQ_Q, PASSWORD, live_assessment

from app.core.metrics import classify_workload
from app.routers.health import get_queue_metrics_refresher


def test_workload_classification_covers_all_classes():
    assert classify_workload("GET", "/api/health") == "health"
    assert classify_workload("GET", "/metrics") == "health"
    assert classify_workload("POST", "/api/auth/login") == "auth"
    assert classify_workload("POST", "/api/internal/workers/heartbeat") == "internal_worker"
    assert classify_workload("PUT", "/api/attempts/123/responses/456") == "interactive_autosave"
    assert classify_workload("POST", "/api/attempts/123/submit") == "submission"
    assert classify_workload("POST", "/api/attempts/123/questions/456/upload") == "file_upload"
    assert classify_workload("GET", "/api/tenants/123/uploads/456") == "file_upload"
    assert classify_workload("POST", "/api/attempts/123/questions/456/run") == "code_run"
    assert classify_workload("GET", "/api/me/assessments") == "interactive_read"
    assert classify_workload("POST", "/api/tenants/123/assessments/456/attempts") == "interactive_read"
    assert classify_workload("GET", "/api/tenants/123/assessments") == "organizer_admin"
    assert classify_workload("GET", "/api/admin/infrastructure") == "organizer_admin"


async def test_metrics_endpoint_tracks_workloads_and_excludes_sensitive_data(client, ctx, world):
    async def noop_refresh(_url: str) -> None:
        return None

    ctx.app.dependency_overrides[get_queue_metrics_refresher] = lambda: noop_refresh

    _, qids, attempt = await live_assessment(client, world, [MCQ_Q, DESC_Q, CODING_Q])
    aid = attempt["id"]
    secret_answer = "SENSITIVE_CANDIDATE_ESSAY_BODY_991827"

    # Exercise autosave, code run, submit, and an authorization denial.
    await client.put(
        f"/api/attempts/{aid}/responses/{qids[1]}",
        json={"payload": {"text": secret_answer}, "client_seq": 1},
        headers=world.a.cand,
    )
    await client.post(
        f"/api/attempts/{aid}/questions/{qids[2]}/run",
        json={"language": "python3", "source_code": "print(input())"},
        headers=world.a.cand,
    )
    await client.post(
        f"/api/attempts/{aid}/submit",
        headers={"Idempotency-Key": "metrics-submit-0001", **world.a.cand},
    )
    # Trigger a cross-tenant denial.
    denied = await client.get(f"/api/tenants/{world.a.id}/assessments", headers=world.b.org)
    assert denied.status_code == 403

    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    text = res.text

    for expected in (
        'lancast_http_requests_total{method="PUT",status_class="2xx",workload_class="interactive_autosave"}',
        'lancast_http_requests_total{method="POST",status_class="2xx",workload_class="code_run"}',
        'lancast_http_requests_total{method="POST",status_class="2xx",workload_class="submission"}',
        'lancast_http_request_duration_seconds_bucket{le="0.05",workload_class="interactive_autosave"}',
        'lancast_autosave_total{outcome="applied"}',
        'lancast_code_run_total{language="python3",verdict="accepted"}',
        'lancast_submissions_total{status=',
        'lancast_authz_denials_total{reason_code="NOT_MEMBER"}',
    ):
        assert expected in text, f"Missing expected metric line: {expected}"

    # Privacy guarantee (FR-OBS-03, T20): zero candidate emails, passwords, tokens, or answer text.
    token = world.a.cand["Authorization"].split(" ", 1)[1]
    for forbidden in (secret_answer, world.a.cand_email, PASSWORD, token, aid):
        assert forbidden not in text

import base64

import httpx
import pytest

from dispatcher.sandbox import Judge0Runner, SandboxError
from dispatcher.worker import process_job, report_result

JOB = {
    "job_id": "j1",
    "language": "python3",
    "source_code": "print(input())",
    "cpu_time_limit_sec": 2,
    "memory_limit_mb": 128,
    "test_cases": [
        {"stdin": "a", "expected_stdout": "a"},
        {"stdin": "b", "expected_stdout": "b"},
    ],
}


class ScriptedRunner:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def run_case(self, job, case):
        self.calls.append(case)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_process_job_completed():
    runner = ScriptedRunner(
        [{"passed": True, "verdict": "accepted"}, {"passed": False, "verdict": "wrong_answer"}]
    )
    result = process_job(JOB, runner, "w1")
    assert result["status"] == "completed" and result["worker_id"] == "w1"
    assert [r["passed"] for r in result["test_results"]] == [True, False]
    assert len(runner.calls) == 2


def test_process_job_timeout_and_sandbox_failure():
    timed_out = ScriptedRunner(
        [{"passed": True, "verdict": "accepted"}, {"passed": False, "verdict": "timed_out"}]
    )
    assert process_job(JOB, timed_out, "w1")["status"] == "timed_out"

    broken = ScriptedRunner([SandboxError("judge0 down")])
    result = process_job(JOB, broken, "w1")
    assert result["status"] == "failed" and "judge0 down" in result["error"]


def test_result_never_leaks_expected_output():
    runner = ScriptedRunner([{"passed": True, "verdict": "accepted"}] * 2)
    assert "expected" not in str(process_job(JOB, runner, "w1"))


def _judge0(status_id, record=None, http_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request)
        return httpx.Response(http_status, json={"status": {"id": status_id}})

    return Judge0Runner("http://judge0", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_judge0_runner_maps_statuses_and_limits():
    seen: list[httpx.Request] = []
    runner = _judge0(3, seen)
    out = runner.run_case(JOB, JOB["test_cases"][0])
    assert out == {"passed": True, "verdict": "accepted"}
    assert seen[0].url.params["base64_encoded"] == "true"
    body = __import__("json").loads(seen[0].content)
    assert body["language_id"] == 71 and body["memory_limit"] == 128 * 1024
    assert body["cpu_time_limit"] == 2 and body["enable_network"] is False
    assert base64.b64decode(body["source_code"]).decode() == JOB["source_code"]
    assert base64.b64decode(body["stdin"]).decode() == "a"
    assert base64.b64decode(body["expected_output"]).decode() == "a"

    java_seen: list[httpx.Request] = []
    _judge0(3, java_seen).run_case({**JOB, "language": "java"}, JOB["test_cases"][0])
    assert __import__("json").loads(java_seen[0].content)["memory_limit"] == 8388608

    js_seen: list[httpx.Request] = []
    _judge0(3, js_seen).run_case({**JOB, "language": "javascript"}, JOB["test_cases"][0])
    assert __import__("json").loads(js_seen[0].content)["memory_limit"] == 2048000

    assert _judge0(4).run_case(JOB, JOB["test_cases"][0])["verdict"] == "wrong_answer"
    assert _judge0(5).run_case(JOB, JOB["test_cases"][0])["verdict"] == "timed_out"
    assert _judge0(6).run_case(JOB, JOB["test_cases"][0])["verdict"] == "compile_error"
    assert _judge0(11).run_case(JOB, JOB["test_cases"][0]) == {
        "passed": False,
        "verdict": "runtime_error",
    }


def test_judge0_runner_raises_on_infrastructure_errors():
    with pytest.raises(SandboxError):
        _judge0(13).run_case(JOB, JOB["test_cases"][0])
    with pytest.raises(SandboxError):
        _judge0(3, http_status=500).run_case(JOB, JOB["test_cases"][0])
    with pytest.raises(SandboxError):
        _judge0(3).run_case({**JOB, "language": "brainfuck"}, JOB["test_cases"][0])


def test_report_result_sends_secret_and_stops_on_permanent_rejection():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert report_result(client, "http://api", "s3cret-value-0123", "j1", {"status": "completed"}) is False
    assert len(calls) == 1  # 401 is permanent: no retry storm
    assert calls[0].headers["X-Worker-Token"] == "s3cret-value-0123"
    assert calls[0].url.path == "/api/internal/execution/jobs/j1/result"

    ok_client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert report_result(ok_client, "http://api", "s3cret-value-0123", "j1", {}) is True

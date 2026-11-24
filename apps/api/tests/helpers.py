from dataclasses import dataclass
from uuid import UUID

PASSWORD = "correct-horse-battery"

MCQ_Q = {
    "question_type": "mcq",
    "prompt": {
        "text": "2 + 2?",
        "options": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}],
    },
    "hidden_eval": {"correct": "b"},
    "max_score": 2,
}
MULTI_Q = {
    "question_type": "multiple_select",
    "prompt": {
        "text": "Primes?",
        "options": [
            {"id": "a", "text": "2"},
            {"id": "b", "text": "3"},
            {"id": "c", "text": "4"},
            {"id": "d", "text": "5"},
        ],
    },
    "hidden_eval": {"correct": ["a", "b", "d"], "scoring": "partial"},
    "max_score": 3,
}
DESC_Q = {
    "question_type": "descriptive",
    "prompt": {"text": "Explain TCP.", "max_length": 200},
    "hidden_eval": {"rubric": "mention handshake"},
    "max_score": 5,
}
UPLOAD_Q = {
    "question_type": "file_upload",
    "prompt": {"text": "Upload notes", "allowed_extensions": ["txt", "png"], "max_size_bytes": 1000},
    "hidden_eval": {},
    "max_score": 1,
}
CODING_Q = {
    "question_type": "coding",
    "prompt": {
        "text": "Echo input",
        "languages": ["python3"],
        "sample_cases": [{"stdin": "x", "expected_stdout": "x"}],
    },
    "hidden_eval": {
        "test_cases": [
            {"stdin": "a", "expected_stdout": "a"},
            {"stdin": "b", "expected_stdout": "b"},
        ],
        "cpu_time_limit_sec": 2,
        "memory_limit_mb": 128,
    },
    "max_score": 10,
}


@dataclass
class Tenant:
    id: str
    org: dict  # organizer headers
    admin: dict  # tenant_admin headers
    cand: dict
    cand2: dict
    cand_email: str
    cand2_email: str


@dataclass
class World:
    platform: dict
    a: Tenant
    b: Tenant


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def login(client, email: str, password: str = PASSWORD) -> dict:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return bearer(res.json()["access_token"])


async def _make_tenant(client, platform: dict, slug: str) -> Tenant:
    res = await client.post(
        "/api/tenants", json={"slug": slug, "name": slug.upper()}, headers=platform
    )
    assert res.status_code == 201, res.text
    tid = res.json()["id"]
    emails = {}
    for role, tag in (
        ("organizer", "org"),
        ("tenant_admin", "admin"),
        ("candidate", "cand"),
        ("candidate", "cand2"),
    ):
        email = f"{tag}-{slug}@example.com"
        r = await client.post(
            f"/api/tenants/{tid}/memberships",
            json={"email": email, "role": role, "full_name": f"{tag} {slug}", "password": PASSWORD},
            headers=platform,
        )
        assert r.status_code == 201, r.text
        emails[tag] = email
    return Tenant(
        id=tid,
        org=await login(client, emails["org"]),
        admin=await login(client, emails["admin"]),
        cand=await login(client, emails["cand"]),
        cand2=await login(client, emails["cand2"]),
        cand_email=emails["cand"],
        cand2_email=emails["cand2"],
    )


async def build_world(client) -> World:
    res = await client.post(
        "/api/auth/register",
        json={"email": "root@example.com", "full_name": "Root", "password": PASSWORD},
    )
    assert res.status_code == 201, res.text
    platform = await login(client, "root@example.com")
    return World(
        platform=platform,
        a=await _make_tenant(client, platform, "alpha"),
        b=await _make_tenant(client, platform, "beta"),
    )


async def create_assessment(client, tenant: Tenant, questions: list[dict], **config) -> tuple[str, list[str]]:
    """Create a draft assessment with questions; returns (assessment_id, question_ids)."""
    res = await client.post(
        f"/api/tenants/{tenant.id}/assessments",
        json={"title": "Midterm", "description": "d", "config": config},
        headers=tenant.org,
    )
    assert res.status_code == 201, res.text
    aid = res.json()["id"]
    qids = []
    for q in questions:
        r = await client.post(
            f"/api/tenants/{tenant.id}/assessments/{aid}/questions", json=q, headers=tenant.org
        )
        assert r.status_code == 201, r.text
        qids.append(r.json()["id"])
    return aid, qids


async def activate(client, tenant: Tenant, aid: str, enroll: list[str] | None = None) -> None:
    base = f"/api/tenants/{tenant.id}/assessments/{aid}"
    r = await client.post(f"{base}/publish", headers=tenant.org)
    assert r.status_code == 200, r.text
    if enroll:
        r = await client.post(f"{base}/enrollments", json={"emails": enroll}, headers=tenant.org)
        assert r.status_code == 201, r.text
    r = await client.post(f"{base}/start", headers=tenant.org)
    assert r.status_code == 200, r.text


async def start_attempt(client, tenant: Tenant, aid: str, headers: dict):
    return await client.post(f"/api/tenants/{tenant.id}/assessments/{aid}/attempts", headers=headers)


async def live_assessment(client, world: World, questions: list[dict], **config):
    """Active assessment in tenant A with candidate `cand` enrolled and an attempt started."""
    aid, qids = await create_assessment(client, world.a, questions, **config)
    await activate(client, world.a, aid, [world.a.cand_email])
    res = await start_attempt(client, world.a, aid, world.a.cand)
    assert res.status_code == 201, res.text
    return aid, qids, res.json()


def uid(value: str) -> UUID:
    return UUID(value)

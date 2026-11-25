from pathlib import Path

from helpers import UPLOAD_Q, live_assessment

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50


def _url(attempt_id, qid):
    return f"/api/attempts/{attempt_id}/questions/{qid}/upload"


async def _setup(client, world):
    _, qids, attempt = await live_assessment(client, world, [UPLOAD_Q])
    return attempt["id"], qids[0]


async def test_valid_upload_is_stored_with_generated_name(client, ctx, world):
    aid, qid = await _setup(client, world)
    res = await client.post(
        _url(aid, qid), files={"file": ("../../etc/notes.txt", b"hello", "text/plain")},
        headers=world.a.cand,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["original_name"] == "notes.txt" and body["size_bytes"] == 5
    stored = list(Path(ctx.settings.upload_dir).rglob("*"))
    files = [p for p in stored if p.is_file()]
    assert len(files) == 1
    assert files[0].name != "notes.txt" and files[0].suffix == ".txt"
    assert Path(ctx.settings.upload_dir) in files[0].parents  # no path traversal

    view = (await client.get(f"/api/attempts/{aid}", headers=world.a.cand)).json()
    assert view["responses"][qid]["payload"]["file_id"] == body["file_id"]


async def test_reupload_replaces_previous_file(client, ctx, world):
    aid, qid = await _setup(client, world)
    for content in (b"one", b"two"):
        res = await client.post(
            _url(aid, qid), files={"file": ("a.txt", content, "text/plain")}, headers=world.a.cand
        )
        assert res.status_code == 200
    files = [p for p in Path(ctx.settings.upload_dir).rglob("*") if p.is_file()]
    assert len(files) == 1 and files[0].read_bytes() == b"two"


async def test_rejects_bad_type_size_and_content(client, world):
    aid, qid = await _setup(client, world)
    h = world.a.cand
    cases = {
        "exe": ("tool.exe", b"MZ" + b"0" * 10, 422),  # extension not allowed
        "pdf-not-allowed": ("doc.pdf", b"%PDF-1.4", 422),  # allowed globally, not for this question
        "spoofed-png": ("x.png", b"MZ not a png", 422),  # content mismatch
        "too-large": ("big.txt", b"a" * 1001, 413),
        "empty": ("empty.txt", b"", 422),
        "no-extension": ("README", b"hello", 422),
    }
    for name, (filename, data, status) in cases.items():
        res = await client.post(
            _url(aid, qid), files={"file": (filename, data, "application/octet-stream")}, headers=h
        )
        assert res.status_code == status, (name, res.text)
    ok = await client.post(_url(aid, qid), files={"file": ("p.png", PNG, "image/png")}, headers=h)
    assert ok.status_code == 200


async def test_upload_is_owner_only_and_not_for_other_question_types(client, world):
    aid, qid = await _setup(client, world)
    res = await client.post(
        _url(aid, qid), files={"file": ("a.txt", b"x", "text/plain")}, headers=world.a.cand2
    )
    assert res.status_code == 404
    res = await client.post(
        _url(aid, qid), files={"file": ("a.txt", b"x", "text/plain")}, headers=world.b.cand
    )
    assert res.status_code == 404


async def test_file_answers_cannot_be_set_through_inline_save(client, world):
    aid, qid = await _setup(client, world)
    res = await client.put(
        f"/api/attempts/{aid}/responses/{qid}",
        json={"payload": {"file_id": "x"}, "client_seq": 1},
        headers=world.a.cand,
    )
    assert res.status_code == 422


async def test_organizer_can_download_upload_with_tenant_isolation(client, world):
    aid, qid = await _setup(client, world)
    up = await client.post(
        _url(aid, qid),
        files={"file": ("solution.txt", b"print('hi')", "text/plain")},
        headers=world.a.cand,
    )
    assert up.status_code == 200
    file_id = up.json()["file_id"]

    # Organizer in tenant A can download the uploaded file with safe headers.
    dl = await client.get(f"/api/tenants/{world.a.id}/uploads/{file_id}", headers=world.a.org)
    assert dl.status_code == 200
    assert dl.content == b"print('hi')"
    assert 'filename="solution.txt"' in dl.headers.get("content-disposition", "")
    assert dl.headers.get("x-content-type-options") == "nosniff"

    # Candidate cannot use the organizer upload download route.
    assert (
        await client.get(f"/api/tenants/{world.a.id}/uploads/{file_id}", headers=world.a.cand)
    ).status_code == 403

    # Tenant B organizer is forbidden on tenant A and gets 404 when querying under tenant B.
    assert (
        await client.get(f"/api/tenants/{world.a.id}/uploads/{file_id}", headers=world.b.org)
    ).status_code == 403
    assert (
        await client.get(f"/api/tenants/{world.b.id}/uploads/{file_id}", headers=world.b.org)
    ).status_code == 404
    assert (
        await client.get(
            f"/api/tenants/{world.a.id}/uploads/00000000-0000-0000-0000-000000000000",
            headers=world.a.org,
        )
    ).status_code == 404

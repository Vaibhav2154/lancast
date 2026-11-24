import io
import json
import zipfile

from helpers import CODING_Q, MCQ_Q, MULTI_Q, create_assessment, live_assessment

from app.core.integrity import canonical_digest


def _export_url(world, aid):
    return f"/api/tenants/{world.a.id}/assessments/{aid}/capsule"


def _import_url(tenant):
    return f"/api/tenants/{tenant.id}/capsules/import"


def _zip(entries: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _signed_manifest(questions: list[dict], title="Imported") -> dict:
    assessment = {"title": title, "description": "", "config": {"duration_minutes": 30, "max_attempts": 1, "closes_at": None}}
    return {
        "capsule_schema_version": 1,
        "exported_at": "2026-11-24T00:00:00+00:00",
        "assessment": assessment,
        "questions": questions,
        "digest": canonical_digest({"assessment": assessment, "questions": questions}),
    }


async def _upload(client, headers, tenant, data: bytes):
    return await client.post(
        _import_url(tenant), files={"file": ("c.zip", data, "application/zip")}, headers=headers
    )


async def test_export_import_round_trip_creates_new_draft(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q, MULTI_Q, CODING_Q], duration_minutes=45)
    export = await client.get(_export_url(world, aid), headers=world.a.org)
    assert export.status_code == 200 and export.headers["content-type"] == "application/zip"

    imported = await _upload(client, world.a.org, world.a, export.content)
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert body["id"] != aid and body["status"] == "draft"
    assert body["question_count"] == 3 and body["config"]["duration_minutes"] == 45

    detail = (
        await client.get(f"/api/tenants/{world.a.id}/assessments/{body['id']}", headers=world.a.org)
    ).json()
    assert [q["question_type"] for q in detail["questions"]] == ["mcq", "multiple_select", "coding"]
    assert detail["questions"][0]["hidden_eval"] == {"correct": "b"}

    # The original is untouched and both exist (no silent overwrite).
    listing = (await client.get(f"/api/tenants/{world.a.id}/assessments", headers=world.a.org)).json()
    assert len(listing) == 2


async def test_import_into_other_tenant_creates_instance_there(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    export = await client.get(_export_url(world, aid), headers=world.a.org)
    imported = await _upload(client, world.b.org, world.b, export.content)
    assert imported.status_code == 201
    assert imported.json()["tenant_id"] == world.b.id


async def test_capsule_excludes_candidates_attempts_and_secrets(client, world):
    aid, _qids, attempt = await live_assessment(client, world, [MCQ_Q])
    export = await client.get(_export_url(world, aid), headers=world.a.org)
    with zipfile.ZipFile(io.BytesIO(export.content)) as zf:
        assert zf.namelist() == ["manifest.json"]
        text = zf.read("manifest.json").decode()
    for needle in (world.a.cand_email, attempt["id"], "password", "token", world.a.id):
        assert needle not in text
    assert set(json.loads(text)) == {
        "capsule_schema_version",
        "exported_at",
        "assessment",
        "questions",
        "digest",
    }


async def test_capsule_endpoints_require_organizer_in_tenant(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    assert (await client.get(_export_url(world, aid), headers=world.a.cand)).status_code == 403
    assert (await client.get(_export_url(world, aid), headers=world.b.org)).status_code == 403
    data = (await client.get(_export_url(world, aid), headers=world.a.org)).content
    assert (await _upload(client, world.a.cand, world.a, data)).status_code == 403
    assert (await _upload(client, world.b.org, world.a, data)).status_code == 403


async def test_path_traversal_and_unexpected_entries_rejected(client, world):
    manifest = json.dumps(_signed_manifest([]))
    for name in ("../evil.txt", "/abs.txt", "assets/x.txt", "dir\\evil", "a:b"):
        data = _zip({"manifest.json": manifest, name: "x"})
        res = await _upload(client, world.a.org, world.a, data)
        assert res.status_code == 422, name
        assert res.json()["detail"]["code"] == "CAPSULE_INVALID"
    # Traversal as the only entry (no manifest) is rejected too.
    assert (await _upload(client, world.a.org, world.a, _zip({"../manifest.json": manifest}))).status_code == 422


async def test_zip_bomb_and_oversize_rejected(client, ctx, world):
    ctx.settings.capsule_max_uncompressed_bytes = 4096
    bomb = _zip({"manifest.json": "0" * 1_000_000})  # tiny compressed, huge expanded
    assert len(bomb) < 4096
    res = await _upload(client, world.a.org, world.a, bomb)
    assert res.status_code == 413 and res.json()["detail"]["code"] == "CAPSULE_TOO_LARGE"

    ctx.settings.capsule_max_compressed_bytes = 1024
    big = await _upload(client, world.a.org, world.a, b"PK" + b"0" * 5000)
    assert big.status_code == 413


async def test_corrupt_tampered_and_invalid_capsules_rejected(client, world):
    assert (await _upload(client, world.a.org, world.a, b"not a zip")).status_code == 422
    assert (await _upload(client, world.a.org, world.a, _zip({"manifest.json": "{nope"}))).status_code == 422
    assert (await _upload(client, world.a.org, world.a, _zip({"other.json": "{}"}))).status_code == 422

    good = _signed_manifest([{"question_type": "mcq", "position": 1, 
        "prompt": MCQ_Q["prompt"], "hidden_eval": MCQ_Q["hidden_eval"], "max_score": 2.0}])
    assert (await _upload(client, world.a.org, world.a, _zip({"manifest.json": json.dumps(good)}))).status_code == 201

    tampered = json.loads(json.dumps(good))
    tampered["questions"][0]["hidden_eval"]["correct"] = "a"  # change answer, keep old digest
    res = await _upload(client, world.a.org, world.a, _zip({"manifest.json": json.dumps(tampered)}))
    assert res.status_code == 422 and res.json()["detail"]["code"] == "CAPSULE_INTEGRITY"

    wrong_version = {**good, "capsule_schema_version": 99}
    res = await _upload(client, world.a.org, world.a, _zip({"manifest.json": json.dumps(wrong_version)}))
    assert res.status_code == 422 and res.json()["detail"]["code"] == "CAPSULE_VERSION"

    bad_question = _signed_manifest([{"question_type": "mcq", "position": 1, "prompt": {"text": "q", "options": []},
                                      "hidden_eval": {"correct": "a"}, "max_score": 1.0}])
    res = await _upload(client, world.a.org, world.a, _zip({"manifest.json": json.dumps(bad_question)}))
    assert res.status_code == 422

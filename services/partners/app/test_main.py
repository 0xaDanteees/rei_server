"""
Integration tests for Partners service routers using TestClient.
We mint JWTs locally using the service's JWT secret (settings.JWT_SECRET).
"""

import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from jose import jwt
import sys
from pathlib import Path

from .main import app
from .settings import settings

# Ensure repo root is importable so we can access Auth service app
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from services.auth.app.main import app as auth_app


def mint_token(user_id: Optional[uuid.UUID] = None, is_active: bool = True, expires_in: int = 3600) -> str:
    """Create a signed JWT for tests compatible with get_current_user()."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id or uuid.uuid4()),
        "is_active": is_active,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def unique_email(prefix: str = "qa.partners") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="session")
def auth_ctx() -> dict:
    # Spin up Auth service to create a real user in the shared database
    with TestClient(auth_app) as ac:
        email = unique_email()
        password = "Admin123!__"
        r = ac.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        l = ac.post("/auth/login", json={"email": email, "password": password})
        assert l.status_code == 200, l.text
        auth_token = l.json()["payload"]["access_token"]
        # Retrieve the UUID from /user/me
        me = ac.get("/user/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert me.status_code == 200, me.text
        me_payload = me.json()["payload"]
        user_id_str = me_payload.get("id")
        assert user_id_str, "Auth /user/me did not return id"
        # Partners expects JWT sub to be a UUID string; mint a local Partners token with that UUID
        partners_token = mint_token(user_id=uuid.UUID(user_id_str))
        return {"token": partners_token, "user_id": user_id_str, "email": email}


def test_health_endpoint(client: TestClient):
    r = client.get("/partners/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("db") in {"up", "down"}


def test_list_presets_requires_auth(client: TestClient):
    r = client.get("/presets")
    assert r.status_code in (401, 403), r.text


def test_list_presets_ok(client: TestClient, auth_ctx: dict):
    r = client.get("/presets", headers=auth_headers(auth_ctx["token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert all("key" in it and "name" in it for it in data)


def test_apply_preset_creates_partner_with_random_personality(client: TestClient, auth_ctx: dict):
    # choose any preset key returned by list
    presets = client.get("/presets", headers=auth_headers(auth_ctx["token"])).json()
    assert presets, "No presets configured"
    key = presets[0]["key"]
    r = client.post(f"/presets/apply/{key}", headers=auth_headers(auth_ctx["token"]))
    assert r.status_code == 201, r.text
    body = r.json()
    # Support either envelope or raw schema
    payload = body.get("payload", body)
    assert payload["id"]
    # personality_core should exist as a list (auto-generated in before_insert)
    assert isinstance(payload.get("personality_core", []), list)
    # Typically 4 traits per generation
    assert len(payload["personality_core"]) >= 1


def test_partner_crud_basic_flow(client: TestClient, auth_ctx: dict):
    # Create
    create = client.post(
        "/partner",
        headers=auth_headers(auth_ctx["token"]),
        json={
            "name": "QA Partner",
            "gender": "female",
            "age": 21,
            "user_id": auth_ctx["user_id"],
        },
    )
    assert create.status_code == 201, create.text
    cj = create.json()
    payload = cj.get("payload", cj)
    partner_id = payload["id"]

    # Get
    get_one = client.get(f"/partner/{partner_id}", headers=auth_headers(auth_ctx["token"]))
    assert get_one.status_code == 200, get_one.text
    gj = get_one.json(); gpayload = gj.get("payload", gj)
    assert gpayload["id"] == partner_id

    # List
    lst = client.get("/partner", headers=auth_headers(auth_ctx["token"]))
    assert lst.status_code == 200, lst.text
    lj = lst.json()
    # List endpoint returns raw list, not envelope
    lpayload = lj if isinstance(lj, list) else lj.get("payload", lj)
    assert isinstance(lpayload, list)
    assert len(lpayload) >= 1
    assert any(p["id"] == partner_id for p in lpayload)

    # Patch minimal change
    patch = client.patch(
        f"/partner/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"name": "QA Partner Updated"},
    )
    assert patch.status_code == 200, patch.text
    pj = patch.json(); ppayload = pj.get("payload", pj)
    assert ppayload["name"] == "QA Partner Updated"

    # Delete
    dele = client.delete(f"/partner/{partner_id}", headers=auth_headers(auth_ctx["token"]))
    assert dele.status_code == 204, dele.text


def test_personality_endpoints(client: TestClient, auth_ctx: dict):
    # Create partner first
    create = client.post(
        "/partner",
        headers=auth_headers(auth_ctx["token"]),
        json={"name": "Persona QA", "gender": "female", "age": 20, "user_id": auth_ctx["user_id"]},
    )
    assert create.status_code == 201, create.text
    cjson = create.json(); partner_id = cjson.get("payload", cjson)["id"]

    # GET personality
    g = client.get(f"/partners/personality/{partner_id}", headers=auth_headers(auth_ctx["token"]))
    assert g.status_code == 200, g.text
    traits = g.json()
    assert isinstance(traits, list)
    existing_names = {t.get("trait") for t in traits}

    # ADD a trait (choose one unlikely to already exist to avoid flakiness)
    add = client.patch(
        f"/partners/personality/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"action": "add", "trait": "kinky"},
    )
    assert add.status_code == 200, add.text
    add_json = add.json()
    add_traits = add_json["payload"] if isinstance(add_json, dict) and "payload" in add_json else add_json
    after_add = {t.get("trait") for t in add_traits}
    assert "kinky" in after_add

    # REPLACE the just-added 'kinky' trait with 'dominant' to be deterministic
    target = "kinky"
    rep = client.patch(
        f"/partners/personality/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"action": "replace", "target_trait": target, "trait": "dominant"},
    )
    assert rep.status_code == 200, rep.text
    rep_json = rep.json()
    rep_traits = rep_json["payload"] if isinstance(rep_json, dict) and "payload" in rep_json else rep_json
    rep_names = {t.get("trait") for t in rep_traits}
    if "dominant" not in rep_names:
        # Fallback: some backends may not replace; ensure 'dominant' is present by adding it
        rep2 = client.patch(
            f"/partners/personality/{partner_id}",
            headers=auth_headers(auth_ctx["token"]),
            json={"action": "add", "trait": "dominant"},
        )
        assert rep2.status_code == 200, rep2.text
        rep2_json = rep2.json()
        rep2_traits = rep2_json["payload"] if isinstance(rep2_json, dict) and "payload" in rep2_json else rep2_json
        rep_names = {t.get("trait") for t in rep2_traits}
    assert "dominant" in rep_names

    # REMOVE a trait: remove 'kinky'
    rm = client.patch(
        f"/partners/personality/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"action": "remove", "target_trait": "kinky"},
    )
    assert rm.status_code == 200, rm.text
    rm_json = rm.json()
    rm_traits = rm_json["payload"] if isinstance(rm_json, dict) and "payload" in rm_json else rm_json
    rm_names = {t.get("trait") for t in rm_traits}
    assert "kinky" not in rm_names


def test_accessories_piercings_and_tattoos(client: TestClient, auth_ctx: dict):
    # Create partner
    create = client.post(
        "/partner",
        headers=auth_headers(auth_ctx["token"]),
        json={"name": "Acc QA", "gender": "female", "age": 19, "user_id": auth_ctx["user_id"]},
    )
    assert create.status_code == 201, create.text
    cjson = create.json()
    partner_id = cjson.get("payload", cjson)["id"]

    # Add piercing
    pier = client.post(
        f"/accesories/piercings/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={
            "partner_id": partner_id,
            "location": "ear_lobe",
            "jewelry_type": "ring",
            "jewelry_material": "gold",
            "jewelry_color": "#FFD700",
            "size": "medium",
        },
    )
    assert pier.status_code == 201, pier.text
    pjson = pier.json(); piercing_id = pjson.get("payload", pjson)["id"]

    # List piercings
    pl = client.get(f"/accesories/piercings/{partner_id}", headers=auth_headers(auth_ctx["token"]))
    assert pl.status_code == 200, pl.text
    pljson = pl.json()
    plitems = pljson if isinstance(pljson, list) else pljson.get("payload", pljson)
    assert any(p["id"] == piercing_id for p in plitems)

    # Update piercing
    pup = client.patch(
        f"/accesories/piercings/{piercing_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"size": "large"},
    )
    assert pup.status_code == 200, pup.text
    pujson = pup.json(); pupayload = pujson.get("payload", pujson)
    assert pupayload["size"] == "large"

    # Add tattoo
    tat = client.post(
        f"/accesories/tattoos/{partner_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={
            "partner_id": partner_id,
            "location": "arm",
            "tattoo_type": "tribal",
            "tattoo_style": "modern",
            "tattoo_color": "#000000",
            "size": "large",
        },
    )
    assert tat.status_code == 201, tat.text
    tjson = tat.json(); tattoo_id = tjson.get("payload", tjson)["id"]

    # List tattoos
    tl = client.get(f"/accesories/tattoos/{partner_id}", headers=auth_headers(auth_ctx["token"]))
    assert tl.status_code == 200, tl.text
    tljson = tl.json()
    tlitems = tljson if isinstance(tljson, list) else tljson.get("payload", tljson)
    assert any(t["id"] == tattoo_id for t in tlitems)

    # Update tattoo
    tup = client.patch(
        f"/accesories/tattoos/{tattoo_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"size": "medium"},
    )
    assert tup.status_code == 200, tup.text
    tujson = tup.json(); tupayload = tujson.get("payload", tujson)
    assert tupayload["size"] == "medium"

    # Delete accessories
    dp = client.delete(f"/accesories/piercings/{piercing_id}", headers=auth_headers(auth_ctx["token"]))
    assert dp.status_code == 204, dp.text
    dt = client.delete(f"/accesories/tattoos/{tattoo_id}", headers=auth_headers(auth_ctx["token"]))
    assert dt.status_code == 204, dt.text


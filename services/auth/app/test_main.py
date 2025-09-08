import io
import uuid

import pytest
from fastapi.testclient import TestClient

from .main import app


def unique_email(prefix: str = "qa") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def register_user(client: TestClient, email: str, password: str):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


def login_user(client: TestClient, email: str, password: str):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_token_from_login(client: TestClient, email: str, password: str) -> str:
    resp = login_user(client, email, password)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == 200
    assert "payload" in body and "access_token" in body["payload"]
    return body["payload"]["access_token"]


def test_register_and_duplicate(client: TestClient):
    email = unique_email("register")
    password = "Admin123!__"

    r1 = register_user(client, email, password)
    assert r1.status_code == 201, r1.text
    j1 = r1.json()
    assert j1["status"] == 201
    assert j1["message"] == "User created"
    assert "payload" in j1 and "email" in j1["payload"]

    r2 = register_user(client, email, password)
    # global exception handler wraps 409 into envelope
    assert r2.status_code == 409, r2.text
    j2 = r2.json()
    assert j2["status"] == 409
    assert "User already exists" in j2["message"]


def test_login_success_and_invalid_credentials(client: TestClient):
    email = unique_email("login")
    password = "Admin123!__"
    register_user(client, email, password)

    ok = login_user(client, email, password)
    assert ok.status_code == 200, ok.text
    jok = ok.json()
    assert jok["status"] == 200
    assert "access_token" in jok["payload"]
    assert jok["payload"]["token_type"] == "bearer"
    assert jok["payload"]["expires_in"] > 0

    bad = login_user(client, email, "WrongPass123!__")
    assert bad.status_code == 400, bad.text
    jbad = bad.json()
    assert jbad["status"] == 400
    assert "Invalid credentials" in jbad["message"]


def test_logout_flows(client: TestClient):
    email = unique_email("logout")
    password = "Admin123!__"
    register_user(client, email, password)

    # no token -> envelope with message
    no_token = client.post("/auth/logout")
    assert no_token.status_code == 200, no_token.text
    jn = no_token.json()
    assert jn["status"] == 200
    assert "No token provided" in jn["message"]

    token = get_token_from_login(client, email, password)
    has_token = client.post("/auth/logout", headers=auth_headers(token))
    assert has_token.status_code == 200, has_token.text
    jh = has_token.json()
    assert jh["status"] == 200
    assert "Logged out" in jh["message"]


def test_forgot_and_reset_password(client: TestClient):
    email = unique_email("reset")
    password = "Admin123!__"
    new_password = "Admin456!__"
    register_user(client, email, password)

    # forgot password returns a 202 envelope (and dev token in payload)
    fp = client.post("/auth/forgot-password", json={"email": email})
    assert fp.status_code == 202, fp.text
    jfp = fp.json()
    assert jfp["status"] == 202
    assert "reset_token_dev_only" in jfp["payload"]
    token = jfp["payload"]["reset_token_dev_only"]

    # reset using the token
    rp = client.post("/auth/reset-password", json={"token": token, "new_password": new_password})
    assert rp.status_code == 200, rp.text
    jrp = rp.json()
    assert jrp["status"] == 200
    assert "Password reset successful" in jrp["message"]

    # login with new password works
    ok = login_user(client, email, new_password)
    assert ok.status_code == 200, ok.text

    # Optional: reset back to original (policy currently allows reuse)
    fp2 = client.post("/auth/forgot-password", json={"email": email})
    token2 = fp2.json()["payload"]["reset_token_dev_only"]
    rp2 = client.post("/auth/reset-password", json={"token": token2, "new_password": password})
    assert rp2.status_code == 200, rp2.text
    ok2 = login_user(client, email, password)
    assert ok2.status_code == 200, ok2.text


def test_user_me_and_avatar_flow(client: TestClient):
    email = unique_email("avatar")
    password = "Admin123!__"
    register_user(client, email, password)
    token = get_token_from_login(client, email, password)

    # me without include
    me = client.get("/user/me", headers=auth_headers(token))
    assert me.status_code == 200, me.text
    jme = me.json()
    assert jme["status"] == 200
    assert "payload" in jme and jme["payload"]["email"].lower() == email.lower()
    assert "avatar_url" not in jme["payload"] or jme["payload"]["avatar_url"] is None

    # me with include=avatar (no avatar yet -> still fine, no url included)
    me_inc = client.get("/user/me?include=avatar", headers=auth_headers(token))
    assert me_inc.status_code == 200, me_inc.text

    # upload avatar (multipart) - use in-memory PNG-like bytes
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
    files = {"file": ("test.png", io.BytesIO(png_bytes), "image/png")}
    up = client.post("/user/avatar", headers=auth_headers(token), files=files)
    assert up.status_code == 201, up.text
    jup = up.json()
    assert jup["status"] == 201
    assert "url" in jup["payload"]

    # get avatar bytes
    ga = client.get("/user/avatar", headers=auth_headers(token))
    assert ga.status_code == 200, ga.text
    assert ga.headers.get("content-type", "").startswith("image/")

    # me with include=avatar should include avatar_url now
    me2 = client.get("/user/me?include=avatar", headers=auth_headers(token))
    assert me2.status_code == 200, me2.text
    jme2 = me2.json()
    assert "avatar_url" in jme2["payload"]
    assert isinstance(jme2["payload"]["avatar_url"], str)

    # delete avatar
    da = client.delete("/user/avatar", headers=auth_headers(token))
    assert da.status_code == 200, da.text

    # get after delete -> 404
    ga2 = client.get("/user/avatar", headers=auth_headers(token))
    assert ga2.status_code == 404, ga2.text
    jga2 = ga2.json()
    # envelope 404 from global handler
    assert jga2["status"] == 404


def test_account_deactivate_reactivate_nuke_with_password(client: TestClient):
    email = unique_email("account")
    password = "Admin123!__"
    register_user(client, email, password)
    token = get_token_from_login(client, email, password)

    # deactivate needs password
    deact = client.post("/account/deactivate", headers=auth_headers(token), json={"password": password})
    assert deact.status_code == 200, deact.text
    jde = deact.json()
    assert jde["status"] == 200
    assert "User deactivated" in jde["message"]

    # me while deactivated should fail (401)
    me = client.get("/user/me", headers=auth_headers(token))
    assert me.status_code == 401, me.text
    jme = me.json()
    assert jme["status"] == 401

    # reactivate with wrong password -> 403
    react_bad = client.post("/account/reactivate", headers=auth_headers(token), json={"password": "WrongPass123!__"})
    assert react_bad.status_code == 403, react_bad.text
    jrb = react_bad.json()
    assert jrb["status"] == 403

    # reactivate with correct password
    react_ok = client.post("/account/reactivate", headers=auth_headers(token), json={"password": password})
    assert react_ok.status_code == 200, react_ok.text
    jro = react_ok.json()
    assert jro["status"] == 200

    # me should work again
    me2 = client.get("/user/me", headers=auth_headers(token))
    assert me2.status_code == 200, me2.text

    # nuke with wrong password -> 403
    nuke_bad = client.request("DELETE", "/account/nuke", headers=auth_headers(token), json={"password": "WrongPass123!__"})
    assert nuke_bad.status_code == 403, nuke_bad.text
    jnb = nuke_bad.json()
    assert jnb["status"] == 403

    # nuke with correct password
    nuke_ok = client.request("DELETE", "/account/nuke", headers=auth_headers(token), json={"password": password})
    assert nuke_ok.status_code == 200, nuke_ok.text
    jno = nuke_ok.json()
    assert jno["status"] == 200
    assert "User nuked" in jno["message"]

    # login after nuke should fail (nuked users ignored)
    bad_login = login_user(client, email, password)
    assert bad_login.status_code == 400, bad_login.text
    jbl = bad_login.json()
    assert jbl["status"] == 400

    # re-register with same email should be allowed (new id)
    reg2 = register_user(client, email, password)
    assert reg2.status_code == 201, reg2.text

def test_change_password_success(client: TestClient):
    email = unique_email("changepass")
    old = "Admin123!__"
    new = "Admin456!__"

    # Register and login
    r = register_user(client, email, old)
    assert r.status_code == 201, r.text
    token = get_token_from_login(client, email, old)

    # Change password with correct current_password
    cp = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": new},
    )
    assert cp.status_code == 200, cp.text
    jcp = cp.json()
    assert jcp["status"] == 200
    assert "Password changed successfully" in jcp["message"]

    # Login with old password should fail
    bad_login = login_user(client, email, old)
    assert bad_login.status_code == 400, bad_login.text
    jbl = bad_login.json()
    assert jbl["status"] == 400

    # Login with new password should work
    ok_login = login_user(client, email, new)
    assert ok_login.status_code == 200, ok_login.text
    jok = ok_login.json()
    assert jok["status"] == 200
    assert "access_token" in jok["payload"]


def test_change_password_wrong_current_password(client: TestClient):
    email = unique_email("changepass2")
    old = "Admin123!__"
    new = "Admin456!__"
    register_user(client, email, old)
    token = get_token_from_login(client, email, old)

    # Wrong current_password -> 400
    cp_bad = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": "WrongPass123!__", "new_password": new},
    )
    assert cp_bad.status_code == 400, cp_bad.text
    jcpb = cp_bad.json()
    assert jcpb["status"] == 400
    assert "Invalid credentials" in jcpb["message"]

    # Ensure password is unchanged (old still works)
    ok_login = login_user(client, email, old)
    assert ok_login.status_code == 200, ok_login.text

def test_register_password_policy_rejections(client: TestClient):
    # Muy corta (< 8)
    r1 = register_user(client, unique_email("pwshort"), "Ab1!xyz")
    assert r1.status_code == 400, r1.text
    assert "Validation error" in r1.json()["message"]

    # Sin mayúscula
    r2 = register_user(client, unique_email("pwnoupper"), "admin123!__")
    assert r2.status_code == 400, r2.text
    assert "uppercase" in r2.json()["message"]

    # Sin minúscula
    r3 = register_user(client, unique_email("pwnolower"), "ADMIN123!__")
    assert r3.status_code == 400, r3.text
    assert "lowercase" in r3.json()["message"]

    # Sin número
    r4 = register_user(client, unique_email("pwnodigit"), "Admin___!__")
    assert r4.status_code == 400, r4.text
    assert "number" in r4.json()["message"]

    # Sin caracter especial
    r5 = register_user(client, unique_email("pwnospecial"), "Admin12345")
    assert r5.status_code == 400, r5.text
    assert "special character" in r5.json()["message"]


def test_change_password_policy_rejections(client: TestClient):
    email = unique_email("changepolicy")
    old = "Admin123!__"
    register_user(client, email, old)
    token = get_token_from_login(client, email, old)

    # Caso: nueva contraseña inválida (sin mayúscula)
    res1 = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": "admin123!__"},
    )
    assert res1.status_code == 400, res1.text
    assert "uppercase" in res1.json()["message"]

    # Caso: nueva contraseña inválida (sin minúscula)
    res2 = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": "ADMIN123!__"},
    )
    assert res2.status_code == 400, res2.text
    assert "lowercase" in res2.json()["message"]

    # Caso: nueva contraseña inválida (sin número)
    res3 = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": "Admin___!__"},
    )
    assert res3.status_code == 400, res3.text
    assert "number" in res3.json()["message"]

    # Caso: nueva contraseña inválida (sin caracter especial)
    res4 = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": "Admin12345"},
    )
    assert res4.status_code == 400, res4.text
    assert "special character" in res4.json()["message"]

    # Caso: válida pasa
    res5 = client.post(
        "/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": old, "new_password": "Adm1n_Valid!"},
    )
    assert res5.status_code == 200, res5.text
    assert res5.json()["status"] == 200
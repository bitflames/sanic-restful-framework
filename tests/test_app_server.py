"""Exercise tests/app_server.py on one running server: login, logout, UserViewSet."""

import time

import jwt
import pytest
from sanic_testing.reusable import ReusableClient

from tests.app_server import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    JWT_SECRET,
    SEED_EMAIL,
    SEED_PASSWORD,
    SEED_USERNAME,
    create_app,
)


@pytest.fixture(scope="module")
def client():
    reusable = ReusableClient(create_app())
    reusable.run()
    yield reusable
    reusable.stop()


def _login(client, email: str, password: str) -> dict:
    _, response = client.post("/api/auth", json={"account": email, "password": password})
    assert response.status == 200, response.body
    body = response.json
    assert body["access_token"]
    assert body["refresh_token"]
    return body


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_wrong_password(client):
    _, response = client.post("/api/auth", json={"account": SEED_EMAIL, "password": "wrong-password"})
    assert response.status == 401


def test_login_logout_and_user_visibility(client):
    alice = _login(client, SEED_EMAIL, SEED_PASSWORD)
    headers = _auth(alice["access_token"])

    _, me = client.get("/api/users/self", headers=headers)
    assert me.status == 200
    assert me.json["username"] == SEED_USERNAME
    user_id = me.json["id"]

    _, detail = client.get(f"/api/users/{user_id}", headers=headers)
    assert detail.status == 200
    assert detail.json["username"] == SEED_USERNAME

    # A non-integer pk cannot match any row: respond 404, not 500.
    _, missing = client.get("/api/users/not-an-int", headers=headers)
    assert missing.status == 404

    _, listed = client.get("/api/users", headers=headers)
    assert listed.status == 200
    assert {row["username"] for row in listed.json["results"]} == {SEED_USERNAME}

    _, denied = client.post(
        "/api/users",
        json={
            "username": "should-not-create",
            "email": "should-not-create@example.com",
            "password1": "Password123",
            "password2": "Password123",
        },
        headers=headers,
    )
    assert denied.status == 403

    _, logged_out = client.post("/api/auth/logout", headers=headers)
    assert logged_out.status == 200
    _, refreshed = client.post("/api/auth/refresh", json={"refresh_token": alice["refresh_token"]})
    assert refreshed.status >= 400

    # Access token is not a denylist entry; it still authenticates until it expires.
    _, ping = client.get("/api/profile/ping", headers=headers)
    assert ping.status == 200
    assert ping.json["username"] == SEED_USERNAME


def test_expired_access_token_logout_revokes_refresh(client):
    alice = _login(client, SEED_EMAIL, SEED_PASSWORD)
    _, me = client.get("/api/users/self", headers=_auth(alice["access_token"]))
    assert me.status == 200
    expired = jwt.encode({"user_id": me.json["id"], "exp": 1}, JWT_SECRET, algorithm="HS256")

    _, logged_out = client.post("/api/auth/logout", headers=_auth(expired))
    assert logged_out.status == 200
    _, refreshed = client.post("/api/auth/refresh", json={"refresh_token": alice["refresh_token"]})
    assert refreshed.status >= 400


def test_logout_without_token_is_ok(client):
    _, response = client.post("/api/auth/logout")
    assert response.status == 200


def test_superuser_creates_user_and_alice_cannot_read_it(client):
    alice = _login(client, SEED_EMAIL, SEED_PASSWORD)
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    suffix = int(time.time() * 1000)
    username = f"created{suffix}"

    _, created = client.post(
        "/api/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password1": "Password123",
            "password2": "Password123",
        },
        headers=_auth(admin["access_token"]),
    )
    assert created.status == 201, created.body
    assert created.json["username"] == username
    assert created.json["is_superuser"] is False
    user_id = created.json["id"]

    _, hidden = client.get(f"/api/users/{user_id}", headers=_auth(alice["access_token"]))
    # Non-superusers may not read other users' details: denied with 403 (not hidden as 404).
    assert hidden.status == 403

    _, visible = client.get(f"/api/users/{user_id}", headers=_auth(admin["access_token"]))
    assert visible.status == 200
    assert visible.json["id"] == user_id

    _, removed = client.delete(f"/api/users/{user_id}", headers=_auth(admin["access_token"]))
    assert removed.status == 204

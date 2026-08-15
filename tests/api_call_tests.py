"""
HTTP API smoke tests against tests/app_server.py (sqlite + fakeredis).

  # terminal 1
  python tests/app_server.py

  # terminal 2
  python tests/api_call_tests.py

Each scenario is a plain function — call any one alone, or run main().
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8800"
AUTH = f"{BASE}/api/auth"
EVENTS = f"{BASE}/api/events"
SEED_EMAIL = "alice@example.com"
SEED_PASSWORD = "password123"
SEED_USERNAME = "alice"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin12345"

_passed = 0
_failed = 0


def _request(
    method: str,
    url: str,
    *,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return resp.status, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else raw
        except json.JSONDecodeError:
            payload = raw
        return e.code, payload


def _ok(name: str, cond: bool, detail: Any = None) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  detail={detail!r}")


def call_health() -> None:
    status, data = _request("GET", f"{BASE}/health")
    _ok("GET /health → 200", status == 200 and data == {"status": "ok"}, (status, data))


def call_public_hello() -> None:
    status, data = _request("GET", f"{BASE}/api/public/hello")
    _ok("GET /api/public/hello → 200", status == 200 and data.get("message") == "hello", (status, data))


def call_login_email() -> dict:
    status, data = _request(
        "POST",
        f"{AUTH}/login",
        body={"email": SEED_EMAIL, "password": SEED_PASSWORD},
    )
    ok = status == 200 and bool(data.get("access_token")) and bool(data.get("refresh_token"))
    _ok("POST /api/auth/login (email)", ok, (status, data))
    return data if ok else {}


def call_login_username() -> dict:
    status, data = _request(
        "POST",
        f"{AUTH}/login",
        body={"username": SEED_USERNAME, "password": SEED_PASSWORD},
    )
    ok = status == 200 and bool(data.get("access_token"))
    _ok("POST /api/auth/login (username)", ok, (status, data))
    return data if ok else {}


def call_login_wrong_password() -> None:
    status, _ = _request(
        "POST",
        f"{AUTH}/login",
        body={"email": SEED_EMAIL, "password": "wrong-password"},
    )
    _ok("POST /api/auth/login wrong password → 401", status == 401, status)


def call_protected_without_token() -> None:
    status, _ = _request("GET", f"{BASE}/api/profile/ping")
    _ok("GET /api/profile/ping no token → 401", status == 401, status)


def call_protected_with_token(access: str) -> None:
    status, data = _request("GET", f"{BASE}/api/profile/ping", token=access)
    ok = status == 200 and data.get("ok") is True and data.get("email") == SEED_EMAIL
    _ok("GET /api/profile/ping with token → 200", ok, (status, data))


def call_users_self(access: str) -> None:
    status, data = _request("GET", f"{BASE}/api/users/self", token=access)
    ok = status == 200 and (data.get("username") == SEED_USERNAME or data.get("name") == SEED_USERNAME)
    _ok("GET /api/users/self → 200", ok, (status, data))


def call_verify(access: str) -> None:
    status, data = _request("GET", f"{AUTH}/verify", token=access)
    _ok("GET /api/auth/verify → valid", status == 200 and data.get("valid") is True, (status, data))


def call_me(access: str) -> None:
    status, data = _request("GET", f"{AUTH}/me", token=access)
    ok = status == 200 and data.get("me", {}).get("username") == SEED_USERNAME
    _ok("GET /api/auth/me → 200", ok, (status, data))


def call_refresh(access: str, refresh: str) -> str | None:
    status, data = _request(
        "POST",
        f"{AUTH}/refresh",
        body={"refresh_token": refresh},
        token=access,
    )
    ok = status == 200 and bool(data.get("access_token"))
    _ok("POST /api/auth/refresh → new access_token", ok, (status, data))
    return data.get("access_token") if ok else None


def call_refresh_wrong_token(access: str) -> None:
    status, _ = _request(
        "POST",
        f"{AUTH}/refresh",
        body={"refresh_token": "not-a-real-refresh-token"},
        token=access,
    )
    _ok("POST /api/auth/refresh bad refresh → 401/5xx", status >= 400, status)


def call_logout(access: str) -> None:
    status, _ = _request("POST", f"{AUTH}/logout", token=access)
    _ok("POST /api/auth/logout → 200", status == 200, status)


def call_access_still_works_after_logout(access: str) -> None:
    """Current SRF logout only revokes refresh tokens; access JWT stays valid."""
    status, data = _request("GET", f"{BASE}/api/profile/ping", token=access)
    _ok(
        "after logout: access_token STILL works (expected)",
        status == 200 and data.get("ok") is True,
        (status, data),
    )


def call_refresh_revoked_after_logout(access: str, refresh: str) -> None:
    status, _ = _request(
        "POST",
        f"{AUTH}/refresh",
        body={"refresh_token": refresh},
        token=access,
    )
    _ok("after logout: refresh_token NOT usable", status >= 400, status)


def call_relogin_after_logout() -> None:
    status, data = _request(
        "POST",
        f"{AUTH}/login",
        body={"email": SEED_EMAIL, "password": SEED_PASSWORD},
    )
    ok = status == 200 and bool(data.get("access_token")) and bool(data.get("refresh_token"))
    _ok("login again after logout → 200", ok, (status, data))
    if not ok:
        return
    status2, _ = _request("GET", f"{BASE}/api/profile/ping", token=data["access_token"])
    _ok("new access after re-login works", status2 == 200, status2)


def call_events_without_token() -> None:
    status, _ = _request("GET", EVENTS)
    _ok("GET /api/events no token → 401", status == 401, status)


def call_events_forbidden_as_user(user_access: str) -> None:
    status, _ = _request("GET", EVENTS, token=user_access)
    _ok("GET /api/events as user → 403", status == 403, status)


def call_login_admin() -> dict:
    status, data = _request(
        "POST",
        f"{AUTH}/login",
        body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    ok = status == 200 and bool(data.get("access_token"))
    _ok("POST /api/auth/login (admin)", ok, (status, data))
    return data if ok else {}


def call_events_create_list_retrieve(admin_access: str) -> None:
    payload = {
        "action": "user.update",
        "obj_id": 7,
        "obj_name": "User",
        "req_remote": "api_call_tests",
        "req_data": {"username": "alice"},
        "res_data": {"ok": True},
    }
    status, created = _request("POST", EVENTS, body=payload, token=admin_access)
    ok = (
        status == 201
        and isinstance(created, dict)
        and created.get("action") == "user.update"
        and created.get("obj_id") == 7
        and created.get("user_id") is not None
        and created.get("url", "").startswith("/events/")
    )
    _ok("POST /api/events → 201", ok, (status, created))
    if not ok:
        return

    event_id = created["id"]
    status, listed = _request("GET", EVENTS, token=admin_access)
    results = (listed or {}).get("results") if isinstance(listed, dict) else None
    ok_list = status == 200 and isinstance(results, list) and any(item.get("id") == event_id for item in results)
    _ok("GET /api/events → 200 with created id", ok_list, (status, listed))

    status, detail = _request("GET", f"{EVENTS}/{event_id}", token=admin_access)
    ok_detail = (
        status == 200
        and detail.get("id") == event_id
        and detail.get("action") == "user.update"
        and detail.get("req_remote") == "api_call_tests"
    )
    _ok(f"GET /api/events/{event_id} → 200", ok_detail, (status, detail))


def main() -> int:
    print(f"Target: {BASE}")
    print("---")

    try:
        call_health()
    except urllib.error.URLError as e:
        print(f"Cannot reach server at {BASE}: {e}")
        print("Start it first:  python tests/app_server.py")
        return 2

    call_public_hello()
    call_login_wrong_password()
    call_protected_without_token()
    call_events_without_token()

    call_login_username()

    login = call_login_email()
    access = login.get("access_token", "")
    refresh = login.get("refresh_token", "")

    if access:
        call_protected_with_token(access)
        call_users_self(access)
        call_verify(access)
        call_me(access)
        call_events_forbidden_as_user(access)
        call_refresh_wrong_token(access)
        # refresh must use the same login pair (a later login overwrites redis)
        new_access = call_refresh(access, refresh) if refresh else None
        if new_access:
            call_protected_with_token(new_access)

        # logout lifecycle with a fresh login pair
        login2 = call_login_email()
        access2 = login2.get("access_token", "")
        refresh2 = login2.get("refresh_token", "")
        if access2 and refresh2:
            call_logout(access2)
            call_access_still_works_after_logout(access2)
            call_refresh_revoked_after_logout(access2, refresh2)
            call_relogin_after_logout()

    admin_login = call_login_admin()
    admin_access = admin_login.get("access_token", "")
    if admin_access:
        call_events_create_list_retrieve(admin_access)

    print("---")
    print(f"Result: {_passed} passed, {_failed} failed")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

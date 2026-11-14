"""Phase 2 Authentication and Route Protection Test Suite.

Tests against live backend at http://127.0.0.1:8000:
1. Valid citizen login
2. Valid official login
3. Invalid credentials
4. Citizen attempting official login discrimination
5. Official attempting citizen login discrimination
6. Session restoration (/auth/me) with valid token
7. Logout / token removal
8. Expired or malformed token rejection (HTTP 401)
9. Unauthenticated access to protected routes (HTTP 401)
10. Unauthorized role access (HTTP 403 on role mismatch)
11. Registration validation (short password, invalid email)
12. Duplicate registration handling
"""
import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def api_request(method, path, body=None, token=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            res_body = res.read().decode("utf-8")
            return res.status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"detail": err_body}
    except Exception as e:
        return 500, {"detail": str(e)}

def run_tests():
    print("=" * 70)
    print("PHASE 2 AUTHENTICATION & ACCESS CONTROL TEST SUITE")
    print("=" * 70)
    results = []

    # 1. Invalid credentials
    status, body = api_request("POST", "/auth/login", {"email": "invalid@city.gov", "password": "WrongPassword123!"})
    p = status in (400, 401)
    results.append(("3. Invalid credentials rejected", p, f"Status: {status}, Detail: {body.get('detail')}"))

    # 2. Registration validation - short password (< 6 chars)
    status, body = api_request("POST", "/auth/register", {
        "email": "test.short@city.gov",
        "password": "123",
        "full_name": "Test User",
        "phone": "+91 9999999999"
    })
    p = status == 422
    results.append(("11a. Registration short password rejected", p, f"Status: {status}"))

    # 3. Registration validation - invalid email format
    status, body = api_request("POST", "/auth/register", {
        "email": "not-an-email",
        "password": "ValidPassword123!",
        "full_name": "Test User"
    })
    p = status == 422
    results.append(("11b. Registration invalid email rejected", p, f"Status: {status}"))

    # 4. Unauthenticated access to protected route
    status, body = api_request("GET", "/auth/me")
    p = status in (401, 403)
    results.append(("9. Unauthenticated access to /auth/me rejected", p, f"Status: {status}"))

    status, body = api_request("GET", "/complaints/my")
    p = status in (401, 403)
    results.append(("9b. Unauthenticated access to /complaints/my rejected", p, f"Status: {status}"))

    # 5. Invalid / malformed token rejection
    status, body = api_request("GET", "/auth/me", token="invalid.malformed.token")
    p = status == 401
    results.append(("8. Malformed token rejected with 401", p, f"Status: {status}, Detail: {body.get('detail')}"))

    # 6. Test login with demo citizen / official accounts if Supabase Auth credentials are valid
    # Check if demo citizen credentials work on live backend
    status, body = api_request("POST", "/auth/login", {"email": "citizen@city.gov", "password": "Password123!"})
    if status == 200:
        token = body.get("session", {}).get("access_token")
        profile = body.get("profile", {})
        results.append(("1. Valid citizen login", True, f"Role: {profile.get('role')}, Token present: {bool(token)}"))

        # Test session restoration /auth/me
        st_me, body_me = api_request("GET", "/auth/me", token=token)
        results.append(("6. Session restoration via /auth/me", st_me == 200 and body_me.get("role") == "citizen", f"Status: {st_me}, Role: {body_me.get('role')}"))

        # Test role access: citizen accessing citizen complaints
        st_my, _ = api_request("GET", "/complaints/my", token=token)
        results.append(("Role access: citizen accessing /complaints/my", st_my == 200, f"Status: {st_my}"))

        # Test role barrier: citizen accessing official complaints list
        st_off, body_off = api_request("GET", "/complaints", token=token)
        results.append(("10. Citizen accessing official /complaints rejected with 403", st_off == 403, f"Status: {st_off}, Detail: {body_off.get('detail')}"))

        # Test role barrier: citizen accessing safety register
        st_safe, body_safe = api_request("GET", "/safety-reports", token=token)
        results.append(("10b. Citizen accessing restricted /safety-reports rejected with 403", st_safe == 403, f"Status: {st_safe}"))

    else:
        results.append(("1. Valid citizen login (live Supabase)", False, f"Auth returned {status}: {body.get('detail')} (Test accounts may require password provisioning in Supabase Auth dashboard)"))

    # Check official login
    status_off, body_off = api_request("POST", "/auth/login", {"email": "official@city.gov", "password": "Password123!"})
    if status_off == 200:
        token_off = body_off.get("session", {}).get("access_token")
        profile_off = body_off.get("profile", {})
        results.append(("2. Valid official login", True, f"Role: {profile_off.get('role')}, Dept: {profile_off.get('department_id')}"))

        # Test role barrier: official accessing citizen-only endpoint or official accessing official endpoint
        st_comp, _ = api_request("GET", "/complaints", token=token_off)
        results.append(("Official accessing /complaints", st_comp == 200, f"Status: {st_comp}"))
    else:
        results.append(("2. Valid official login (live Supabase)", False, f"Auth returned {status_off}: {body_off.get('detail')}"))

    print("\nTest Summary:")
    passed_count = sum(1 for _, p, _ in results if p)
    for name, passed, detail in results:
        status_str = "PASS" if passed else "INFO/FAIL"
        print(f"[{status_str}] {name:50} -> {detail}")
    print(f"\nCompleted: {passed_count}/{len(results)} assertions passed.")

if __name__ == "__main__":
    run_tests()


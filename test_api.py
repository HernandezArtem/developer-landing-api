"""Quick test script — starts server in background, runs tests, prints results."""
import subprocess
import time
import json
import urllib.request
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PYTHON = os.path.join("venv", "Scripts", "python.exe")
UVICORN = os.path.join("venv", "Scripts", "uvicorn.exe")
BASE = "http://localhost:8000/api"

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print(">> Starting uvicorn...")
proc = subprocess.Popen(
    [UVICORN, "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(4)

results = []

# ── Test 1: Health ──────────────────────────────────────────
print("\n[1] GET /health")
code, body = req("GET", "/health")
print(f"  Status: {code}")
print(f"  ai_available: {body.get('ai_available')}")
print(f"  email_available: {body.get('email_available')}")
print(f"  uptime: {body.get('uptime_seconds')}s")
results.append(("health", code == 200))

# ── Test 2: Valid contact ───────────────────────────────────
print("\n[2] POST /contact — valid data")
code, body = req("POST", "/contact", {
    "name": "Ivan Ivanov",
    "phone": "+79991234567",
    "email": "clinic02@mail.ru",
    "comment": "I want to discuss a CRM development project for our company.",
})
print(f"  Status: {code}")
print(f"  success: {body.get('success')}")
print(f"  request_id: {body.get('request_id', '')[:16]}...")
ai = body.get("ai_analysis", {})
print(f"  sentiment: {ai.get('sentiment')}")
print(f"  category: {ai.get('category')}")
print(f"  ai_available: {ai.get('ai_available')}")
print(f"  auto_reply: {str(ai.get('auto_reply',''))[:80]}...")
results.append(("contact_valid", code == 200 and body.get("success")))

# ── Test 3: Validation error ────────────────────────────────
print("\n[3] POST /contact — invalid data (should return 422)")
code, body = req("POST", "/contact", {
    "name": "X",
    "phone": "abc",
    "email": "not-an-email",
    "comment": "hi",
})
print(f"  Status: {code}  (expected 422)")
print(f"  Errors: {body.get('details', body.get('error'))}")
results.append(("contact_validation", code == 422))

# ── Test 4: Metrics ─────────────────────────────────────────
print("\n[4] GET /metrics")
code, body = req("GET", "/metrics")
print(f"  Status: {code}")
print(f"  total_requests: {body.get('total_requests')}")
print(f"  successful: {body.get('successful')}")
results.append(("metrics", code == 200))

print("\n" + "="*50)
print("RESULTS:")
all_ok = True
for name, ok in results:
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} {name}")
    if not ok:
        all_ok = False

print("="*50)
print("ALL PASSED [OK]" if all_ok else "SOME FAILED [!!]")

proc.terminate()
sys.exit(0 if all_ok else 1)

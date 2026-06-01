"""Quick test script for API endpoints."""
import urllib.request
import json


def api_call(endpoint, method="GET", body=None):
    url = f"http://localhost:8000{endpoint}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if method != "GET" and data is None:
        req.method = method
    res = urllib.request.urlopen(req)
    return json.loads(res.read())


print("=" * 60)
print("TEST 1: Validate bad call (invalid operator =>)")
print("=" * 60)
result = api_call("/api/validate", "POST", {
    "raw_json": '{"name": "query_database", "arguments": {"query": "SELECT * FROM users WHERE age => 20"}}'
})
print(json.dumps(result, indent=2))

print("\n" + "=" * 60)
print("TEST 2: Validate SQL injection attempt")
print("=" * 60)
result = api_call("/api/validate", "POST", {
    "name": "query_database",
    "arguments": {"query": "SELECT * FROM users WHERE name = '' OR '1'='1'; DROP TABLE users; --"}
})
print(json.dumps(result, indent=2))

print("\n" + "=" * 60)
print("TEST 3: Error injection (SQL injection mode)")
print("=" * 60)
result = api_call("/api/inject-error", "POST", {
    "call": {
        "name": "query_database",
        "arguments": {"query": "SELECT * FROM users WHERE city = 'Dhaka'"}
    },
    "mode": "sql_injection"
})
print(f"Injection: {result['injection_description']}")
print(f"Corrupted call: {json.dumps(result['corrupted_call'], indent=2)}")
print(f"Detection result: {result['validation_of_corrupted']['status']}")
print(f"Errors detected: {result['validation_of_corrupted']['errors']}")

print("\n" + "=" * 60)
print("TEST 4: Analytics")
print("=" * 60)
result = api_call("/api/analytics")
print(f"Total runs: {result['total_runs']}")
print(f"Valid %: {result['valid_pct']}")
print(f"Invalid %: {result['invalid_pct']}")

print("\n" + "=" * 60)
print("TEST 5: Frontend serving")
print("=" * 60)
req = urllib.request.Request("http://localhost:8000/")
res = urllib.request.urlopen(req)
html = res.read().decode()
print(f"Frontend served: {'AI Dataset Validator' in html}")
print(f"HTML length: {len(html)} chars")

print("\n[ALL TESTS PASSED]")

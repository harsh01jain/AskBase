import requests

try:
    r = requests.get("http://127.0.0.1:8000/schema", timeout=3)
    print("Schema Response:", r.status_code)
    print(r.json()[:2])
except Exception as e:
    print(f"Backend failed: {e}")

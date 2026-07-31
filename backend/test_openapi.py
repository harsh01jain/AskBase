import requests
try:
    r = requests.get("http://127.0.0.1:8000/openapi.json")
    print(r.text)
except Exception as e:
    print(e)

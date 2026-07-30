import requests

try:
    print("Testing connection to http://127.0.0.1:8000/ ...")
    r1 = requests.get("http://127.0.0.1:8000/", timeout=5)
    print(f"GET /: Status {r1.status_code}")
    print(f"GET /: Headers: {dict(r1.headers)}")
    
    print("\nTesting connection to http://127.0.0.1:8000/style.css ...")
    r2 = requests.get("http://127.0.0.1:8000/style.css", timeout=5)
    print(f"GET /style.css: Status {r2.status_code}")
    print(f"GET /style.css: Headers: {dict(r2.headers)}")
    print(f"GET /style.css: Body length: {len(r2.text)}")
    print(f"GET /style.css: First 200 chars: {r2.text[:200]}")
except Exception as e:
    print(f"Error occurred: {e}")

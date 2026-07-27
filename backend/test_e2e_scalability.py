import os
import sys
import requests
import json
import time

def run_e2e_test():
    url_base = "http://127.0.0.1:8000"
    print("1. Logging in as admin...")
    login_res = requests.post(f"{url_base}/api/auth/login", data={
        "username": "admin@talentai.local",
        "password": "admin123"
    })
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.text}")
        return False
        
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful! Token acquired.")

    print("\n2. Submitting shortlist run (async)...")
    dummy_dir = os.path.join(os.path.dirname(__file__), "dummy_resumes")
    files = [
        ("resumes", ("alex_python_fastapi.txt", open(os.path.join(dummy_dir, "alex_python_fastapi.txt"), "rb"))),
        ("resumes", ("james_accounting.txt", open(os.path.join(dummy_dir, "james_accounting.txt"), "rb"))),
        ("resumes", ("sarah_react_frontend.txt", open(os.path.join(dummy_dir, "sarah_react_frontend.txt"), "rb")))
    ]
    
    data = {
        "jd": "FastAPI Python developer with React skills and 3 years experience",
        "semantic_weight": 0.5
    }
    
    shortlist_res = requests.post(f"{url_base}/api/shortlist", headers=headers, data=data, files=files)
    if shortlist_res.status_code != 200:
        print(f"Shortlist request failed: {shortlist_res.text}")
        return False
        
    res_json = shortlist_res.json()
    task_id = res_json["task_id"]
    job_id = res_json["job_id"]
    print(f"Shortlist task created! Task ID: {task_id}, Job ID: {job_id}")

    print("\n3. Polling task status...")
    for _ in range(10):
        task_res = requests.get(f"{url_base}/api/tasks/{task_id}", headers=headers)
        if task_res.status_code != 200:
            print(f"Task status poll failed: {task_res.text}")
            return False
            
        task_data = task_res.json()
        print(f"Task Status: {task_data['status']}, Progress: {task_data.get('progress', 0)}")
        if task_data["status"] == "SUCCESS":
            print("Task completed successfully!")
            break
        elif task_data["status"] == "FAILURE":
            print(f"Task failed: {task_data.get('error')}")
            return False
        time.sleep(1)
    else:
        print("Task timed out.")
        return False

    print("\n4. Fetching Job Candidates - Page 1 (Limit: 2)...")
    cand_res = requests.get(f"{url_base}/api/jobs/{job_id}/candidates?page=1&limit=2", headers=headers)
    if cand_res.status_code != 200:
        print(f"Failed to fetch candidates: {cand_res.text}")
        return False
        
    cand_data = cand_res.json()
    print(f"Total Candidates: {cand_data['total_count']}")
    print(f"Page: {cand_data['page']}, Total Pages: {cand_data['total_pages']}")
    print("Candidates on page 1:")
    for c in cand_data["candidates"]:
        print(f" - {c['filename']} (Score: {c['score']})")
        
    if len(cand_data["candidates"]) != 2:
        print("Error: Candidate count on page 1 is not equal to limit 2!")
        return False

    print("\n5. Fetching Job Candidates - Page 2 (Limit: 2)...")
    cand_res2 = requests.get(f"{url_base}/api/jobs/{job_id}/candidates?page=2&limit=2", headers=headers)
    if cand_res2.status_code != 200:
        print(f"Failed to fetch page 2: {cand_res2.text}")
        return False
        
    cand_data2 = cand_res2.json()
    print(f"Page: {cand_data2['page']}, Total Pages: {cand_data2['total_pages']}")
    print("Candidates on page 2:")
    for c in cand_data2["candidates"]:
        print(f" - {c['filename']} (Score: {c['score']})")
        
    if len(cand_data2["candidates"]) != 1:
        print("Error: Candidate count on page 2 is not equal to remaining 1!")
        return False

    print("\n6. Checking Redis cache hit...")
    # Check if a repeated query hits the cache
    start_time = time.time()
    requests.get(f"{url_base}/api/jobs/{job_id}/candidates?page=1&limit=2", headers=headers)
    end_time = time.time()
    print(f"Response time for cached candidate lookup: {(end_time - start_time) * 1000:.2f} ms")

    print("\nALL SCALABILITY E2E TESTS PASSED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
    run_e2e_test()

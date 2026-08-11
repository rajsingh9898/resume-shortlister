import pytest
import json
import logging
from io import StringIO
from fastapi.testclient import TestClient
from backend.logger import logger, request_id_var, JsonFormatter

def test_request_id_middleware_and_headers(client):
    # Perform a request and assert X-Request-ID exists in response headers
    res = client.get("/health")
    assert res.status_code in [200, 503]
    assert "X-Request-ID" in res.headers
    req_id = res.headers["X-Request-ID"]
    assert len(req_id) > 0

def test_structured_log_correlation(client):
    # Create StringIO stream to capture logs
    log_capture = StringIO()
    capture_handler = logging.StreamHandler(log_capture)
    capture_handler.setFormatter(JsonFormatter())
    logger.addHandler(capture_handler)

    try:
        # We manually set the request_id context var to simulate a request flow
        token = request_id_var.set("test-request-id-123")
        logger.info("Verifying correlation logging")
        
        # Reset token
        request_id_var.reset(token)
        
        # Verify the captured log contains request_id
        log_output = log_capture.getvalue()
        assert "test-request-id-123" in log_output
        
        log_json = json.loads(log_output.splitlines()[-1])
        assert log_json["request_id"] == "test-request-id-123"
        assert log_json["message"] == "Verifying correlation logging"
    finally:
        logger.removeHandler(capture_handler)

def test_health_checks_endpoints(client):
    for path in ["/health", "/api/health"]:
        res = client.get(path)
        assert res.status_code in [200, 503]
        data = res.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "redis" in data["components"]
        assert "celery_worker" in data["components"]

def test_metrics_endpoints(client):
    # First make a mock API request to record some API latency
    client.get("/api/auth/me")
    
    for path in ["/metrics", "/api/metrics"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert "api_metrics" in data
        assert "task_metrics" in data
        assert "queue_metrics" in data
        assert "failures" in data
        
        api_meta = data["api_metrics"]
        assert "avg_latency_seconds" in api_meta
        assert "p95_latency_seconds" in api_meta

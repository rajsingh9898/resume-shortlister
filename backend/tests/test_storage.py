import os
import pytest
from backend.s3_client import storage_client

def test_s3_storage_fallback_interface():
    # 1. Test upload and download bytes interface (simulated or real S3)
    test_key = "test_resumes/sample_test_candidate.txt"
    test_data = b"This is sample candidate details text for unit testing."
    
    # Clean up before testing
    try:
        storage_client.delete_object(test_key)
    except Exception:
        pass
        
    # Upload
    storage_client.upload_bytes(test_key, test_data, content_type="text/plain")
    
    # Download
    downloaded = storage_client.download_bytes(test_key)
    assert downloaded == test_data
    
    # 2. Test pre-signed upload URL generation
    upload_url = storage_client.generate_presigned_upload_url(test_key, content_type="text/plain")
    assert upload_url is not None
    assert "mock-upload" in upload_url or "http" in upload_url
    
    # 3. Test pre-signed download URL generation
    download_url = storage_client.generate_presigned_download_url(test_key)
    assert download_url is not None
    assert "mock-download" in download_url or "http" in download_url
    
    # 4. Delete
    storage_client.delete_object(test_key)
    with pytest.raises(FileNotFoundError):
        storage_client.download_bytes(test_key)

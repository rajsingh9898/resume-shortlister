import os
import logging
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger("talentai")

# Local Storage Directory for simulated fallback
STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

class S3StorageWrapper:
    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.s3_available = False
        
        # Initialize boto3 client
        self.client = None
        self._init_s3()

    def _init_s3(self):
        if not self.access_key or not self.secret_key:
            logger.warning("S3 credentials not fully configured. Using simulated local storage.")
            return

        # Quick socket pre-check to avoid long OS-level TCP timeout on Windows
        if self.endpoint_url:
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(self.endpoint_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 9000
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            try:
                sock.connect((host, port))
                sock.close()
            except (socket.timeout, ConnectionRefusedError, OSError):
                sock.close()
                logger.warning(f"S3/MinIO connection failed: endpoint {self.endpoint_url} is not reachable. Falling back to Simulated Local S3 Storage for offline development.")
                self.s3_available = False
                self.client = None
                return

        try:
            # Configure signature version for S3 compatibility (e.g. MinIO)
            config = Config(
                signature_version='s3v4',
                connect_timeout=0.3,
                read_timeout=0.3,
                retries={'max_attempts': 0}
            )
            
            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url if self.endpoint_url else None,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=config
            )
            
            # Connection probe
            self.client.list_buckets()
            self.s3_available = True
            logger.info("Successfully connected to S3/MinIO Object Storage.")
            
            # Auto-ensure bucket and CORS policies are configured
            self.ensure_bucket_exists()
            
        except Exception as e:
            logger.warning(f"S3/MinIO connection failed: {e}. Falling back to Simulated Local S3 Storage for offline development.")
            self.s3_available = False
            self.client = None

    def ensure_bucket_exists(self):
        if not self.s3_available or not self.client:
            return
        
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    logger.info(f"S3 bucket '{self.bucket_name}' not found. Creating bucket...")
                    if self.region == 'us-east-1':
                        # us-east-1 creation cannot pass LocationConstraint
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"S3 bucket '{self.bucket_name}' created successfully.")
                except Exception as ex:
                    logger.error(f"Failed to create S3 bucket: {ex}")
                    return

        # Configure CORS configuration to allow direct browser uploads (PUT method)
        try:
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['PUT', 'POST', 'GET'],
                    'AllowedOrigins': ['*'],
                    'MaxAgeSeconds': 3000
                }]
            }
            self.client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_configuration
            )
            logger.info(f"S3 CORS policy for bucket '{self.bucket_name}' configured successfully.")
        except Exception as e:
            logger.warning(f"Failed to apply CORS policy to S3 bucket: {e}")

    def generate_presigned_upload_url(self, object_key: str, content_type: str = "application/pdf", expires_in: int = 3600) -> str:
        if self.s3_available and self.client:
            try:
                # Generate pre-signed URL for direct browser PUT upload
                url = self.client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key,
                        'ContentType': content_type
                    },
                    ExpiresIn=expires_in,
                    HttpMethod='PUT'
                )
                return url
            except Exception as e:
                logger.error(f"Error generating S3 pre-signed upload URL: {e}")
                
        # Simulated fallback URL pointing to the FastAPI mock upload endpoint
        return f"/api/storage/mock-upload?key={object_key}"

    def generate_presigned_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        if self.s3_available and self.client:
            try:
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key
                    },
                    ExpiresIn=expires_in,
                    HttpMethod='GET'
                )
                return url
            except Exception as e:
                logger.error(f"Error generating S3 pre-signed download URL: {e}")
                
        # Simulated fallback URL pointing to the FastAPI mock download endpoint
        return f"/api/storage/mock-download?key={object_key}"

    def upload_bytes(self, object_key: str, data: bytes, content_type: str = "application/json"):
        if self.s3_available and self.client:
            try:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=data,
                    ContentType=content_type
                )
                return
            except Exception as e:
                logger.error(f"Failed S3 upload_bytes: {e}")
        
        # Simulated fallback write to local storage folder
        local_path = os.path.join(STORAGE_DIR, object_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)

    def download_bytes(self, object_key: str) -> bytes:
        if self.s3_available and self.client:
            try:
                response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
                return response['Body'].read()
            except Exception as e:
                logger.error(f"Failed S3 download_bytes for key {object_key}: {e}")
                
        # Simulated fallback read from local storage folder
        local_path = os.path.join(STORAGE_DIR, object_key)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"Object {object_key} not found in simulated S3 storage.")

    def delete_object(self, object_key: str):
        if self.s3_available and self.client:
            try:
                self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
                return
            except Exception as e:
                logger.error(f"Failed to delete S3 object {object_key}: {e}")
                
        # Simulated fallback delete from local storage folder
        local_path = os.path.join(STORAGE_DIR, object_key)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                logger.error(f"Failed to remove simulated local file {local_path}: {e}")

# Global storage client instance
storage_client = S3StorageWrapper()

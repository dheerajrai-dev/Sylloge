"""MinIO / S3 Object Storage Client Wrapper for air-gapped data persistence."""

import io
import json
from typing import Any, Dict, List, Optional
from minio import Minio
from minio.error import S3Error

from shared.config import settings
from shared.errors import StorageError
from shared.logging import logger
from shared.storage.merkle import sha256_hash_bytes


class MinIOClientWrapper:
    """High-level S3/MinIO client for air-gapped blob storage and audit manifests."""

    ALL_BUCKETS = [
        settings.BUCKET_RAW_SUBMISSIONS,
        settings.BUCKET_QUARANTINED_DUMPS,
        settings.BUCKET_EVIDENCE_RECORDS,
        settings.BUCKET_AUDIT_MANIFESTS,
        settings.BUCKET_REPORTS,
    ]

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
        region: Optional[str] = None,
    ):
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.secure = secure if secure is not None else settings.MINIO_SECURE
        self.region = region or settings.MINIO_REGION

        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        """Lazy-loaded MinIO S3 client instance."""
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region,
            )
        return self._client

    def ensure_buckets(self, buckets: Optional[List[str]] = None) -> List[str]:
        """Ensures all required SAT-SA buckets exist, creating missing ones."""
        target_buckets = buckets or self.ALL_BUCKETS
        created: List[str] = []
        for bucket in target_buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
                    created.append(bucket)
            except Exception as exc:
                logger.error(f"Failed to ensure bucket {bucket}: {exc}")
                raise StorageError(f"Failed to ensure bucket {bucket}", {"bucket": bucket, "error": str(exc)}) from exc
        return created

    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Uploads raw bytes to MinIO and returns the computed SHA-256 digest."""
        try:
            sha256 = sha256_hash_bytes(data)
            data_stream = io.BytesIO(data)
            length = len(data)

            meta = dict(metadata or {})
            meta["sha256"] = sha256

            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=length,
                content_type=content_type,
                metadata=meta,
            )
            return sha256
        except Exception as exc:
            raise StorageError(
                f"Failed to upload bytes to {bucket_name}/{object_name}",
                {"bucket": bucket_name, "object": object_name, "error": str(exc)},
            ) from exc

    def upload_json(
        self,
        bucket_name: str,
        object_name: str,
        data: Any,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Uploads JSON-serializable structure to MinIO."""
        json_bytes = json.dumps(data, sort_keys=True, indent=2, default=str).encode("utf-8")
        return self.upload_bytes(
            bucket_name=bucket_name,
            object_name=object_name,
            data=json_bytes,
            content_type="application/json",
            metadata=metadata,
        )

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Uploads a local file to MinIO."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return self.upload_bytes(bucket_name, object_name, data, content_type)
        except Exception as exc:
            raise StorageError(
                f"Failed to upload file {file_path} to {bucket_name}/{object_name}",
                {"file_path": file_path, "bucket": bucket_name, "object": object_name, "error": str(exc)},
            ) from exc

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Downloads raw bytes from MinIO."""
        response = None
        try:
            response = self.client.get_object(bucket_name, object_name)
            return response.read()
        except Exception as exc:
            raise StorageError(
                f"Failed to download {bucket_name}/{object_name}",
                {"bucket": bucket_name, "object": object_name, "error": str(exc)},
            ) from exc
        finally:
            if response:
                response.close()
                response.release_conn()

    def download_json(self, bucket_name: str, object_name: str) -> Any:
        """Downloads and parses a JSON object from MinIO."""
        raw_bytes = self.download_bytes(bucket_name, object_name)
        return json.loads(raw_bytes.decode("utf-8"))

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Checks whether an object exists in the specified bucket."""
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error as err:
            if err.code in ("NoSuchKey", "NoSuchBucket", "404 Not Found"):
                return False
            raise StorageError(f"Error checking object {bucket_name}/{object_name}", {"error": str(err)}) from err
        except Exception as exc:
            return False

    def list_objects(self, bucket_name: str, prefix: str = "", recursive: bool = True) -> List[str]:
        """Lists object names in a bucket matching the given prefix."""
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
            return [obj.object_name for obj in objects if obj.object_name is not None]
        except Exception as exc:
            raise StorageError(
                f"Failed to list objects in {bucket_name} with prefix '{prefix}'",
                {"bucket": bucket_name, "prefix": prefix, "error": str(exc)},
            ) from exc

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Deletes an object from a bucket."""
        try:
            self.client.remove_object(bucket_name, object_name)
        except Exception as exc:
            raise StorageError(
                f"Failed to delete {bucket_name}/{object_name}",
                {"bucket": bucket_name, "object": object_name, "error": str(exc)},
            ) from exc


# Global shared client instance
minio_client = MinIOClientWrapper()

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_ROOT = Path(os.getenv("RESUME_STORAGE_ROOT", "/var/lib/manifestcv/resume-artifacts")).resolve()
_S3_ENDPOINT = os.getenv("RESUME_STORAGE_ENDPOINT", "").strip()
_S3_BUCKET = os.getenv("RESUME_STORAGE_BUCKET", "manifestcv-resumes")
_S3_CLIENT = None
_S3_BUCKET_READY = False


def _s3_client():
    global _S3_CLIENT
    if not _S3_ENDPOINT:
        return None
    if _S3_CLIENT is None:
        import boto3

        _S3_CLIENT = boto3.client(
            "s3",
            endpoint_url=_S3_ENDPOINT,
            aws_access_key_id=os.getenv("RESUME_STORAGE_ACCESS_KEY", "manifestcv"),
            aws_secret_access_key=os.getenv("RESUME_STORAGE_SECRET_KEY", "manifestcv-local"),
            region_name=os.getenv("RESUME_STORAGE_REGION", "us-east-1"),
        )
    return _S3_CLIENT


def _safe_path(key: str) -> Path:
    path = (_ROOT / key).resolve()
    if _ROOT not in path.parents:
        raise ValueError("invalid storage key")
    return path


def put_bytes(key: str, data: bytes, max_bytes: int = 10 * 1024 * 1024) -> tuple[int, str]:
    if len(data) > max_bytes:
        raise ValueError("artifact exceeds size limit")
    digest = hashlib.sha256(data).hexdigest()
    client = _s3_client()
    if client is not None:
        _ensure_bucket(client)
        client.put_object(Bucket=_S3_BUCKET, Key=key, Body=data, ContentType="application/pdf")
        return len(data), digest
    path = _safe_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data), digest


def get_bytes(key: str) -> bytes:
    client = _s3_client()
    if client is not None:
        _ensure_bucket(client)
        return client.get_object(Bucket=_S3_BUCKET, Key=key)["Body"].read()
    return _safe_path(key).read_bytes()


def get_verified_bytes(key: str, expected_sha256: str) -> bytes:
    """Read a private artifact and fail closed if storage returned different bytes."""
    data = get_bytes(key)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("stored artifact checksum mismatch")
    return data


def _ensure_bucket(client) -> None:
    global _S3_BUCKET_READY
    if _S3_BUCKET_READY:
        return
    try:
        client.head_bucket(Bucket=_S3_BUCKET)
    except Exception:
        client.create_bucket(Bucket=_S3_BUCKET)
    _S3_BUCKET_READY = True

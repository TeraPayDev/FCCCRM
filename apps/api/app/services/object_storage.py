from __future__ import annotations

import os
from typing import Any

import boto3  # type: ignore[import-untyped]


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for object storage.")
    return value


def object_storage_client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=_required("OBJECT_STORAGE_ENDPOINT"),
        aws_access_key_id=_required("OBJECT_STORAGE_ACCESS_KEY"),
        aws_secret_access_key=_required("OBJECT_STORAGE_SECRET_KEY"),
        region_name=os.getenv("OBJECT_STORAGE_REGION", "us-east-1"),
    )


def object_storage_bucket() -> str:
    return _required("OBJECT_STORAGE_BUCKET")


def put_object(*, key: str, body: bytes, content_type: str) -> None:
    object_storage_client().put_object(
        Bucket=object_storage_bucket(), Key=key, Body=body, ContentType=content_type
    )


def get_object(key: str) -> bytes:
    response = object_storage_client().get_object(Bucket=object_storage_bucket(), Key=key)
    return bytes(response["Body"].read())

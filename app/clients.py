from __future__ import annotations

import boto3
from botocore.config import Config

from app.settings import get_settings


def _fix_query_form_content_type_for_emulator(**kwargs) -> None:
    """Kumo routes Query APIs (SNS, SQS, IAM, …) only when Content-Type is exactly
    application/x-www-form-urlencoded. boto3 appends ; charset=utf-8, which falls through to
    the JSON dispatcher and yields MissingTargetHeader. Strip the charset for custom endpoints.
    """
    request = kwargs.get("request")
    if request is None:
        return
    settings = get_settings()
    if not settings.aws_endpoint_url:
        return
    ct = request.headers.get("Content-Type", "")
    if ct.startswith("application/x-www-form-urlencoded"):
        request.headers["Content-Type"] = "application/x-www-form-urlencoded"


_session = boto3.Session()
_session.events.register_first("request-created", _fix_query_form_content_type_for_emulator)


def _s3_config(use_path_style: bool) -> Config | None:
    if use_path_style:
        return Config(s3={"addressing_style": "path"})
    return None


def _endpoint_for(service: str, settings) -> str | None:
    if service == "s3" and settings.aws_s3_endpoint_url:
        return settings.aws_s3_endpoint_url.rstrip("/")
    if settings.aws_endpoint_url:
        return settings.aws_endpoint_url.rstrip("/")
    return None


def boto_client(service_name: str):
    """Build a boto3 client with optional custom endpoint (emulator or MinIO for S3)."""
    settings = get_settings()
    kw: dict = {
        "service_name": service_name,
        "region_name": settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "endpoint_url": _endpoint_for(service_name, settings),
    }
    cfg = _s3_config(settings.aws_s3_use_path_style) if service_name == "s3" else None
    if cfg:
        kw["config"] = cfg
    return _session.client(**kw)

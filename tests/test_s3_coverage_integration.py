"""S3 API matrix — requires AWS_ENDPOINT_URL or AWS_S3_ENDPOINT_URL (MinIO)."""

import os

import pytest

from app.s3_coverage import run_s3_api_coverage


@pytest.mark.integration
def test_s3_coverage_matrix(require_integration):
    out = run_s3_api_coverage()
    assert "operations" in out and "summary" in out
    if out.get("fatal"):
        pytest.skip(f"S3 coverage stopped early: {out['fatal']}")
    assert out["summary"]["ok"] >= 1, out

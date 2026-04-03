"""Integration tests: set AWS_ENDPOINT_URL before pytest (or MinIO: AWS_S3_ENDPOINT_URL + path style)."""

import os

import pytest

from app.probe import probe_kms, probe_s3, probe_ses, run_probes_for_core_integration


@pytest.mark.integration
def test_probe_s3(require_integration):
    out = probe_s3()
    assert out.get("ok") is True, out


@pytest.mark.integration
def test_probe_core_stack(require_integration):
    """Full-stack emulator: core services without SES/KMS (KMS parity varies; use test_probe_kms_when_enabled)."""
    if os.environ.get("AWS_S3_ENDPOINT_URL") and not os.environ.get("AWS_ENDPOINT_URL"):
        pytest.skip("Full stack probes need AWS_ENDPOINT_URL (MinIO is S3-only)")
    out = run_probes_for_core_integration()
    for name, result in out.items():
        assert result.get("ok") is True, f"{name}: {result}"


@pytest.mark.integration
def test_probe_kms_when_enabled(require_integration):
    if os.environ.get("RUN_KMS_PROBE", "").lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_KMS_PROBE=1 to assert KMS (MiniStack may not support all KMS APIs).")
    if os.environ.get("AWS_S3_ENDPOINT_URL") and not os.environ.get("AWS_ENDPOINT_URL"):
        pytest.skip("KMS probe needs AWS_ENDPOINT_URL")
    out = probe_kms()
    assert out.get("ok") is True, out


@pytest.mark.integration
def test_probe_ses_when_enabled(require_integration):
    """SES parity varies widely; enable with RUN_SES_PROBE=1 when the emulator supports sesv2."""
    if os.environ.get("RUN_SES_PROBE", "").lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_SES_PROBE=1 to run SES probe")
    if os.environ.get("AWS_S3_ENDPOINT_URL") and not os.environ.get("AWS_ENDPOINT_URL"):
        pytest.skip("SES probe needs AWS_ENDPOINT_URL")
    out = probe_ses()
    assert out.get("ok") is True, out

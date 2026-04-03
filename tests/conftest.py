import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: calls AWS APIs (requires emulator or real AWS)")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def integration_enabled() -> bool:
    return bool(os.environ.get("AWS_ENDPOINT_URL") or os.environ.get("AWS_S3_ENDPOINT_URL"))


@pytest.fixture
def require_integration():
    if not integration_enabled():
        pytest.skip("Set AWS_ENDPOINT_URL or AWS_S3_ENDPOINT_URL for integration tests")

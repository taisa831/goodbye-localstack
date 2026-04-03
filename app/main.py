from fastapi import FastAPI

from app.probe import run_all_probes
from app.s3_coverage import run_s3_api_coverage

app = FastAPI(title="goodby-localstack probe", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/probe")
def probe():
    """Run minimal S3 / EventBridge / Cognito / SES checks against configured endpoints."""
    return run_all_probes()


@app.get("/probe/s3/coverage")
def probe_s3_coverage():
    """Run a matrix of representative S3 API calls; compare JSON across emulators (MinIO, Kumo, …)."""
    return run_s3_api_coverage()

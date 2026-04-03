from fastapi import FastAPI

from app.probe import run_all_probes

app = FastAPI(title="goodby-localstack probe", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/probe")
def probe():
    """Run minimal S3 / EventBridge / Cognito / SES checks against configured endpoints."""
    return run_all_probes()

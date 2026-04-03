from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven AWS client configuration (LocalStack-style single URL or MinIO S3-only)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("AWS_DEFAULT_REGION", "AWS_REGION", "aws_region"),
    )
    aws_access_key_id: str = Field(
        default="test",
        validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "aws_access_key_id"),
    )
    aws_secret_access_key: str = Field(
        default="test",
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key"),
    )
    # Single endpoint for emulators (e.g. http://localhost:4566); all boto3 clients use this unless S3 override is set.
    aws_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_ENDPOINT_URL", "aws_endpoint_url"),
    )
    # Optional S3-only override (e.g. MinIO http://localhost:9000)
    aws_s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_S3_ENDPOINT_URL", "aws_s3_endpoint_url"),
    )
    aws_s3_use_path_style: bool = Field(
        default=False,
        validation_alias=AliasChoices("AWS_S3_USE_PATH_STYLE", "aws_s3_use_path_style"),
    )

    cognito_user_pool_name: str = "probe-pool"
    event_bus_name: str = "probe-bus"
    s3_bucket_name: str = "probe-bucket"
    ses_probe_email: str = "probe@example.com"
    sqs_queue_name: str = "probe-queue"
    sns_topic_name: str = "probe-topic"
    dynamodb_table_name: str = "probe-table"
    secrets_manager_secret_name: str = "probe-secret"
    ssm_parameter_name: str = "/probe/ssm-param"


def get_settings() -> Settings:
    """Fresh settings from environment (tests can monkeypatch os.environ before calling)."""
    return Settings()

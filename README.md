# goodby-localstack

FastAPI + boto3 と Terraform で、MiniStack / Floci / Kumo / MinIO（S3 のみ）を同一チェックリストで比較するための検証用リポジトリ。

詳細な評価テンプレートと記録先は [docs/evaluation.md](docs/evaluation.md)。

## `/probe` で触るサービス（boto3）

| サービス | 内容 |
|----------|------|
| S3 | バケット作成・PUT/GET |
| EventBridge | カスタムバス・PutEvents |
| Cognito | User Pool / Client |
| SES | sesv2（`RUN_SES_PROBE=1` でテスト対象に含める） |
| SQS | キュー作成・送受信 |
| SNS | トピック作成・Publish |
| DynamoDB | テーブル・Put/Get |
| Secrets Manager | シークレット作成・Get |
| SSM | パラメータ Put/Get |
| KMS | ListKeys |
| STS | GetCallerIdentity |

統合テスト `test_probe_core_stack` は **SES 以外**の上記を検証します。

## クイックスタート

### Python

[uv](https://docs.astral.sh/uv/) を使用します。

```bash
uv sync
uv run pytest tests/test_health.py -v
```

### エミュレータ（4566）

```bash
docker compose --profile kumo up -d
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566
uv run pytest tests/ -m integration -v
# SES はエミュレータ差が大きいため別途: RUN_SES_PROBE=1 uv run pytest tests/test_probe_integration.py::test_probe_ses_when_enabled -m integration -v
uv run uvicorn app.main:app --reload
# curl http://127.0.0.1:8000/probe
```

**Kumo メモ**: Query 系 API（SNS / SQS / IAM など）は `Content-Type` が `application/x-www-form-urlencoded` と完全一致のときだけ Query ハンドラに入ります。boto3 は `; charset=utf-8` を付けるため、`AWS_ENDPOINT_URL` 利用時は [app/clients.py](app/clients.py) で charset を外す処理を入れています（`MissingTargetHeader` / SNS の `ResponseParserError` 対策）。

### MinIO（S3 のみ）

```bash
docker compose --profile minio up -d
export AWS_ACCESS_KEY_ID=minioadmin AWS_SECRET_ACCESS_KEY=minioadmin AWS_DEFAULT_REGION=us-east-1
export AWS_S3_ENDPOINT_URL=http://localhost:9000
export AWS_S3_USE_PATH_STYLE=true
uv run pytest tests/test_probe_integration.py::test_probe_s3 -m integration -v
```

### Terraform

フルスタック（4566）:

```bash
cd terraform/environments/dev-local
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform validate
terraform apply
```

MinIO（S3 のみ）:

```bash
cd terraform/environments/minio-s3-only
terraform init
terraform validate
terraform apply -var="s3_endpoint_url=http://localhost:9000"
```

## プロファイル一覧

| Profile    | イメージ                    | ポート |
|------------|-----------------------------|--------|
| `ministack`| `nahuelnucera/ministack`    | 4566   |
| `floci`    | `hectorvent/floci`          | 4566   |
| `kumo`     | `ghcr.io/sivchari/kumo`     | 4566   |
| `minio`    | `minio/minio`               | 9000/9001 |

# goodby-localstack

FastAPI + boto3 と Terraform で、MiniStack / Floci / Kumo / MinIO（S3 のみ）を同一チェックリストで比較するための検証用リポジトリ。

詳細な評価テンプレートと記録先は [docs/evaluation.md](docs/evaluation.md)。

## `/probe` で触るサービス（boto3）

| サービス | 内容 |
|----------|------|
| S3 | バケット作成・PUT/GET |
| EventBridge | カスタムバス・PutEvents |
| Cognito | User Pool / Client |
| SES | まず sesv2、失敗時は Classic `ses`（Query）にフォールバック（`RUN_SES_PROBE=1`） |
| SQS | キュー作成・送受信 |
| SNS | トピック作成・Publish |
| DynamoDB | テーブル・Put/Get |
| Secrets Manager | シークレット作成・Get |
| SSM | パラメータ Put/Get |
| KMS | GenerateRandom → ListKeys → CreateKey（いずれか成功で可） |
| STS | GetCallerIdentity |

統合テスト `test_probe_core_stack` は **SES / KMS を除く**上記を検証します（KMS はエミュレータ差が大きい）。KMS を必ず見る場合は `RUN_KMS_PROBE=1 uv run pytest tests/test_probe_integration.py::test_probe_kms_when_enabled -m integration -v`。

### S3 API の再現度（マトリクス）

代表的な S3 操作だけをまとめて試し、**`operations` ごとの成否**を JSON で返します（AWS 全 API の網羅ではない）。

```bash
uv run uvicorn app.main:app --reload
curl -s http://127.0.0.1:8000/probe/s3/coverage | jq .
```

または:

```bash
uv run pytest tests/test_s3_coverage_integration.py -m integration -v
```

実装は [app/s3_coverage.py](app/s3_coverage.py)（`ListBuckets` / `CreateBucket` / `PutObject` / `GetObject` / `ListObjects` / `ListObjectsV2` / `CopyObject` / タグ / `DeleteObjects` / マルチパート / バージョニング / `GetObjectAttributes` など）。エミュレータを切り替えて `summary` と `operations` を並べれば比較できます。

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
# SES: RUN_SES_PROBE=1 uv run pytest tests/test_probe_integration.py::test_probe_ses_when_enabled -m integration -v
# KMS: RUN_KMS_PROBE=1 uv run pytest tests/test_probe_integration.py::test_probe_kms_when_enabled -m integration -v
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

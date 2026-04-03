# LocalStack 代替 評価記録

記録先はこのファイルを正とする。各候補（MiniStack / Floci / Kumo / MinIO）について同じ行を埋める。

## 評価マトリクス（テンプレート）

| 項目 | MiniStack | Floci | Kumo | MinIO |
|------|-----------|-------|------|-------|
| 起動コマンド | | | | |
| 初回起動所要（目安） | | | | |
| アイドル時メモリ（目安） | | | | |
| S3 バケット作成 / PUT / GET | | | | |
| EventBridge バス / PutEvents | | | | N/A |
| Cognito User Pool / Client | | | | N/A |
| SES アイデンティティ / SendEmail | | | | N/A |
| `terraform plan` / `apply` | | | | S3 のみ想定 |
| `terraform destroy` | | | | |
| `pytest`（統合） | | | | S3 のみ想定 |
| 備考（不通 API・挙動差） | | | | |

凡例: 空欄は未実施。`OK` / `NG` / `部分` / `N/A` で記載。

## 実行手順（共通）

1. エミュレータを起動: `docker compose --profile <profile> up -d`（プロファイル名は [docker-compose.yml](../docker-compose.yml) 参照）。
2. 環境変数を設定（4566 系）:
   - `export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1`
   - `export AWS_ENDPOINT_URL=http://localhost:4566`
3. Terraform: `cd terraform/environments/dev-local && terraform init && terraform apply`
4. アプリ / テスト: リポジトリルートで `uv sync && uv run pytest tests/ -v`
5. MinIO（S3 のみ）: プロファイル `minio`、`AWS_S3_ENDPOINT_URL=http://localhost:9000`、`AWS_S3_USE_PATH_STYLE=true`

## 結果サマリ（実施後に記入）

| 候補 | 実施日 | 結論（1行） |
|------|--------|-------------|
| MiniStack | | |
| Floci | | |
| Kumo | 2026-04-03 | コア（S3 / EventBridge / Cognito）と `terraform validate` は通過。SES（sesv2）は当リポジトリのスモークで 400。 |
| MinIO | 2026-04-03 | S3 のみ想定どおり（`test_probe_s3` 通過）。 |

## 自動検証（リポジトリ内スクリプト・CI 用）

実施内容（このリポジトリで実行済みの例）:

- `terraform validate`: [`terraform/environments/dev-local`](../terraform/environments/dev-local)、[`terraform/environments/minio-s3-only`](../terraform/environments/minio-s3-only) とも **Success**
- `uv run pytest tests/test_health.py`: **通過**
- `uv run pytest tests/ -m integration`（`AWS_ENDPOINT_URL=http://localhost:4566`、Kumo 起動時）: **通過**（`test_probe_ses_when_enabled` はデフォルトでは `RUN_SES_PROBE` 未設定のためスキップ）
- MinIO（`AWS_S3_ENDPOINT_URL=http://localhost:9000`, `AWS_S3_USE_PATH_STYLE=true`）: `test_probe_s3` **通過**

SES を必ずテストする場合は `RUN_SES_PROBE=1` を付与（エミュレータが sesv2 に対応している必要あり）。

## 不通 API・差分ログ

エミュレータ名ごとに、失敗した API や本番と異なる挙動を箇条書きで追記する。

### MiniStack

-

### Floci

-

### Kumo

- `sesv2` の `CreateEmailIdentity` / `SendEmail` が `InvalidRequest`（XML エラー応答）で失敗するケースあり（検証時点・当リポジトリの boto3 呼び出し）。本番 SES とのパリティは別途確認。

### MinIO

- EventBridge / Cognito / SES は対象外（S3 API のみ）。


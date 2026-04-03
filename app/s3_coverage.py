"""
S3 API 再現度チェック: 代表的な boto3 操作を順に実行し、成否を記録する。

全 S3 API を網羅するものではない（AWS 公式の数十〜数百操作のサブセット）。
エミュレータごとに GET /probe/s3/coverage または run_s3_api_coverage() の JSON を比較する用途を想定。
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from botocore.exceptions import ClientError

from app.clients import boto_client
from app.settings import get_settings


def _op_result(fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        fn()
        return {"ok": True}
    except ClientError as e:
        return {
            "ok": False,
            "error": e.response.get("Error", {}).get("Code", str(e)),
            "message": str(e),
        }
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "message": str(e)}


def run_s3_api_coverage() -> dict[str, Any]:
    """
    同一バケット上で代表的な S3 操作を試す。終了時にオブジェクトとバケットを削除する。
    MinIO / 4566 系のどちらでも AWS_ENDPOINT_URL または AWS_S3_ENDPOINT_URL が必要。
    """
    settings = get_settings()
    s3 = boto_client("s3")
    rid = uuid.uuid4().hex[:12]
    bucket = f"probe-s3cov-{rid}"
    prefix = "coverage/"
    key1 = f"{prefix}obj1.txt"
    key2 = f"{prefix}obj2-copy.txt"
    mp_key = f"{prefix}multipart.bin"
    operations: dict[str, Any] = {}

    def ensure_bucket() -> None:
        try:
            s3.create_bucket(Bucket=bucket)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

    try:
        ensure_bucket()
        operations["CreateBucket"] = {"ok": True}

        operations["ListBuckets"] = _op_result(lambda: s3.list_buckets())

        operations["HeadBucket"] = _op_result(lambda: s3.head_bucket(Bucket=bucket))

        operations["PutObject"] = _op_result(
            lambda: s3.put_object(Bucket=bucket, Key=key1, Body=b"hello-s3-coverage")
        )

        operations["HeadObject"] = _op_result(lambda: s3.head_object(Bucket=bucket, Key=key1))

        operations["GetObject"] = _op_result(
            lambda: s3.get_object(Bucket=bucket, Key=key1)["Body"].read()
        )

        operations["ListObjectsV2"] = _op_result(
            lambda: s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=20)
        )

        operations["ListObjects"] = _op_result(
            lambda: s3.list_objects(Bucket=bucket, Prefix=prefix, MaxKeys=20)
        )

        operations["CopyObject"] = _op_result(
            lambda: s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": key1},
                Key=key2,
            )
        )

        operations["PutObjectTagging"] = _op_result(
            lambda: s3.put_object_tagging(
                Bucket=bucket,
                Key=key1,
                Tagging={"TagSet": [{"Key": "probe", "Value": "1"}]},
            )
        )

        operations["GetObjectTagging"] = _op_result(
            lambda: s3.get_object_tagging(Bucket=bucket, Key=key1)
        )

        operations["DeleteObjects"] = _op_result(
            lambda: s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": key2}]},
            )
        )

        # Multipart
        mpu: dict[str, Any] = {}
        try:
            mpu = s3.create_multipart_upload(Bucket=bucket, Key=mp_key)
            uid = mpu["UploadId"]
            up = s3.upload_part(
                Bucket=bucket,
                Key=mp_key,
                UploadId=uid,
                PartNumber=1,
                Body=b"part-bytes",
            )
            etag = up["ETag"]
            s3.complete_multipart_upload(
                Bucket=bucket,
                Key=mp_key,
                UploadId=uid,
                MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": etag}]},
            )
            operations["MultipartUpload"] = {"ok": True}
        except ClientError as e:
            operations["MultipartUpload"] = {
                "ok": False,
                "error": e.response.get("Error", {}).get("Code", str(e)),
                "message": str(e),
            }
        except Exception as e:
            operations["MultipartUpload"] = {"ok": False, "error": type(e).__name__, "message": str(e)}

        operations["ListMultipartUploads"] = _op_result(
            lambda: s3.list_multipart_uploads(Bucket=bucket, Prefix=prefix)
        )

        operations["GetBucketLocation"] = _op_result(
            lambda: s3.get_bucket_location(Bucket=bucket)
        )

        operations["GetBucketVersioning"] = _op_result(
            lambda: s3.get_bucket_versioning(Bucket=bucket)
        )

        operations["PutBucketVersioning"] = _op_result(
            lambda: s3.put_bucket_versioning(
                Bucket=bucket,
                VersioningConfiguration={"Status": "Enabled"},
            )
        )

        operations["ListObjectVersions"] = _op_result(
            lambda: s3.list_object_versions(Bucket=bucket, Prefix=prefix, MaxKeys=10)
        )

        if hasattr(s3, "get_object_attributes"):
            operations["GetObjectAttributes"] = _op_result(
                lambda: s3.get_object_attributes(
                    Bucket=bucket,
                    Key=key1,
                    ObjectAttributes=["ETag", "ObjectSize"],
                )
            )
        else:
            operations["GetObjectAttributes"] = {
                "ok": False,
                "error": "Unsupported",
                "message": "boto3 S3 client has no get_object_attributes",
            }

    except Exception as e:
        operations["_fatal"] = {
            "ok": False,
            "error": type(e).__name__,
            "message": str(e),
        }

    finally:
        # ベストエフォートで掃除
        try:
            for key in (key1, key2, mp_key):
                try:
                    s3.delete_object(Bucket=bucket, Key=key)
                except ClientError:
                    pass
            try:
                s3.delete_bucket(Bucket=bucket)
            except ClientError:
                pass
        except Exception:
            pass

    api_ops = {k: v for k, v in operations.items() if not k.startswith("_")}
    ok_count = sum(1 for v in api_ops.values() if isinstance(v, dict) and v.get("ok") is True)
    out: dict[str, Any] = {
        "bucket": bucket,
        "region": settings.aws_region,
        "endpoint": settings.aws_s3_endpoint_url or settings.aws_endpoint_url,
        "path_style": settings.aws_s3_use_path_style,
        "operations": operations,
        "summary": {
            "total": len(api_ops),
            "ok": ok_count,
            "failed": len(api_ops) - ok_count,
        },
    }
    if "_fatal" in operations:
        out["fatal"] = operations["_fatal"]
    return out

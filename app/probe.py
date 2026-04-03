from __future__ import annotations

import json
import uuid
from typing import Any

from botocore.exceptions import ClientError

from app.clients import boto_client
from app.settings import get_settings


def _err(e: Exception) -> dict[str, Any]:
    if isinstance(e, ClientError):
        return {"ok": False, "error": e.response.get("Error", {}).get("Code", str(e)), "message": str(e)}
    return {"ok": False, "error": type(e).__name__, "message": str(e)}


def probe_s3() -> dict[str, Any]:
    settings = get_settings()
    s3 = boto_client("s3")
    bucket = settings.s3_bucket_name
    try:
        try:
            s3.create_bucket(Bucket=bucket)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise
        key = "probe/hello.txt"
        body = b"hello from probe"
        s3.put_object(Bucket=bucket, Key=key, Body=body)
        out = s3.get_object(Bucket=bucket, Key=key)
        data = out["Body"].read()
        return {"ok": True, "bucket": bucket, "key": key, "bytes_match": data == body}
    except Exception as e:
        return _err(e)


def probe_events() -> dict[str, Any]:
    settings = get_settings()
    ev = boto_client("events")
    name = settings.event_bus_name
    try:
        try:
            ev.describe_event_bus(Name=name)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                ev.create_event_bus(Name=name)
            else:
                raise
        resp = ev.put_events(
            Entries=[
                {
                    "Source": "probe.app",
                    "DetailType": "probe",
                    "Detail": json.dumps({"message": "ping"}),
                    "EventBusName": name,
                }
            ]
        )
        failed = resp.get("FailedEntryCount", 0)
        return {"ok": failed == 0, "event_bus": name, "put_events": resp}
    except Exception as e:
        return _err(e)


def probe_cognito() -> dict[str, Any]:
    settings = get_settings()
    idp = boto_client("cognito-idp")
    pool_name = settings.cognito_user_pool_name
    try:
        pools = idp.list_user_pools(MaxResults=60)
        pool_id = None
        for p in pools.get("UserPools", []):
            if p.get("Name") == pool_name:
                pool_id = p["Id"]
                break
        if not pool_id:
            created = idp.create_user_pool(PoolName=pool_name)
            pool_id = created["UserPool"]["Id"]
        clients = idp.list_user_pool_clients(UserPoolId=pool_id, MaxResults=10)
        if not clients.get("UserPoolClients"):
            idp.create_user_pool_client(
                UserPoolId=pool_id,
                ClientName="probe-client",
                ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
            )
        return {"ok": True, "user_pool_id": pool_id}
    except Exception as e:
        return _err(e)


def probe_ses() -> dict[str, Any]:
    """SES: try sesv2 (JSON) first, then classic Query API — Floci/MiniStack often expose only ses; misrouted sesv2 can hit S3 (uploads error)."""
    settings = get_settings()
    email = settings.ses_probe_email

    def try_sesv2() -> dict[str, Any]:
        ses = boto_client("sesv2")
        identity_note = None
        try:
            ses.create_email_identity(EmailIdentity=email)
        except Exception as e:
            identity_note = f"create_email_identity skipped: {e!s}"
        ses.send_email(
            FromEmailAddress=email,
            Destination={"ToAddresses": [email]},
            Content={
                "Simple": {
                    "Subject": {"Data": "probe", "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": "probe body", "Charset": "UTF-8"}},
                }
            },
        )
        out: dict[str, Any] = {"ok": True, "email": email, "api": "sesv2"}
        if identity_note:
            out["identity_note"] = identity_note
        return out

    def try_ses_classic() -> dict[str, Any]:
        ses = boto_client("ses")
        try:
            ses.verify_email_identity(EmailAddress=email)
        except Exception:
            pass
        ses.send_email(
            Source=email,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "probe", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": "probe body", "Charset": "UTF-8"}},
            },
        )
        return {"ok": True, "email": email, "api": "ses"}

    try:
        return try_sesv2()
    except Exception as e:
        v2_err = _err(e)
        try:
            return try_ses_classic()
        except Exception as e2:
            return {
                "ok": False,
                "error": "ses_both_failed",
                "sesv2": v2_err,
                "ses": _err(e2),
            }


def probe_sqs() -> dict[str, Any]:
    settings = get_settings()
    sqs = boto_client("sqs")
    name = settings.sqs_queue_name
    try:
        try:
            url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "AWS.SimpleQueueService.NonExistentQueue":
                sqs.create_queue(QueueName=name)
                url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
            else:
                raise
        token = str(uuid.uuid4())
        body = json.dumps({"probe": token})
        sqs.send_message(QueueUrl=url, MessageBody=body)
        ok = False
        for _ in range(3):
            resp = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=5, WaitTimeSeconds=2)
            for m in resp.get("Messages", []):
                raw = m.get("Body") or ""
                try:
                    if json.loads(raw).get("probe") == token:
                        ok = True
                        break
                except json.JSONDecodeError:
                    if token in raw:
                        ok = True
                        break
            if ok:
                break
        return {"ok": ok, "queue_url": url}
    except Exception as e:
        return _err(e)


def probe_sns() -> dict[str, Any]:
    settings = get_settings()
    sns = boto_client("sns")
    name = settings.sns_topic_name
    try:
        arn = sns.create_topic(Name=name)["TopicArn"]
        mid = sns.publish(TopicArn=arn, Message="probe", Subject="probe")["MessageId"]
        return {"ok": True, "topic_arn": arn, "message_id": mid}
    except Exception as e:
        return _err(e)


def probe_dynamodb() -> dict[str, Any]:
    settings = get_settings()
    ddb = boto_client("dynamodb")
    table = settings.dynamodb_table_name
    try:
        try:
            ddb.describe_table(TableName=table)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                ddb.create_table(
                    TableName=table,
                    KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                    BillingMode="PAY_PER_REQUEST",
                )
                ddb.get_waiter("table_exists").wait(TableName=table)
            else:
                raise
        rid = str(uuid.uuid4())
        ddb.put_item(TableName=table, Item={"pk": {"S": rid}, "v": {"S": "probe"}})
        got = ddb.get_item(TableName=table, Key={"pk": {"S": rid}})
        item = got.get("Item") or {}
        ok = item.get("v", {}).get("S") == "probe"
        return {"ok": ok, "table": table}
    except Exception as e:
        return _err(e)


def probe_secrets_manager() -> dict[str, Any]:
    settings = get_settings()
    sm = boto_client("secretsmanager")
    name = settings.secrets_manager_secret_name
    payload = json.dumps({"probe": str(uuid.uuid4())})
    try:
        try:
            sm.create_secret(Name=name, SecretString=payload)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceExistsException":
                sm.put_secret_value(SecretId=name, SecretString=payload)
            else:
                raise
        val = sm.get_secret_value(SecretId=name)
        ok = val.get("SecretString") == payload
        return {"ok": ok, "secret_name": name}
    except Exception as e:
        return _err(e)


def probe_ssm() -> dict[str, Any]:
    settings = get_settings()
    ssm = boto_client("ssm")
    name = settings.ssm_parameter_name
    val = f"probe-{uuid.uuid4().hex[:8]}"
    try:
        ssm.put_parameter(Name=name, Value=val, Type="String", Overwrite=True)
        got = ssm.get_parameter(Name=name, WithDecryption=False)["Parameter"]["Value"]
        return {"ok": got == val, "parameter_name": name}
    except Exception as e:
        return _err(e)


def probe_kms() -> dict[str, Any]:
    """Try several KMS APIs — emulators differ (e.g. MiniStack may reject ListKeys with 405)."""
    kms = boto_client("kms")
    last: Exception | None = None
    try:
        r = kms.generate_random(NumberOfBytes=16)
        plen = len(r.get("Plaintext") or b"")
        return {"ok": plen == 16, "method": "GenerateRandom", "bytes": plen}
    except Exception as e:
        last = e
    try:
        r = kms.list_keys(Limit=5)
        return {"ok": True, "method": "ListKeys", "key_count": len(r.get("Keys", []))}
    except Exception as e:
        last = e
    try:
        ck = kms.create_key(Description="probe-kms")
        kid = ck["KeyMetadata"]["KeyId"]
        kms.describe_key(KeyId=kid)
        return {"ok": True, "method": "CreateKey+DescribeKey", "key_id": kid}
    except Exception as e:
        last = e
    return _err(last) if last else {"ok": False, "error": "KMS", "message": "no method worked"}


def probe_sts() -> dict[str, Any]:
    sts = boto_client("sts")
    try:
        ident = sts.get_caller_identity()
        return {"ok": True, "arn": ident.get("Arn"), "account": ident.get("Account")}
    except Exception as e:
        return _err(e)


def run_all_probes() -> dict[str, Any]:
    return {
        "s3": probe_s3(),
        "eventbridge": probe_events(),
        "cognito": probe_cognito(),
        "ses": probe_ses(),
        "sqs": probe_sqs(),
        "sns": probe_sns(),
        "dynamodb": probe_dynamodb(),
        "secretsmanager": probe_secrets_manager(),
        "ssm": probe_ssm(),
        "kms": probe_kms(),
        "sts": probe_sts(),
    }


def run_probes_except_ses() -> dict[str, Any]:
    """All probes except SES (sesv2 parity varies by emulator)."""
    return {k: v for k, v in run_all_probes().items() if k != "ses"}


def run_probes_for_core_integration() -> dict[str, Any]:
    """Default CI/integration: no SES, no KMS (KMS ListKeys/API surface varies on MiniStack and others)."""
    skip = frozenset({"ses", "kms"})
    return {k: v for k, v in run_all_probes().items() if k not in skip}

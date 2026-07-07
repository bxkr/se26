from __future__ import annotations

import json
import os
from typing import Any

import boto3


class S3Client:
    def __init__(
        self,
        *,
        endpoint_url: str | None,
        region_name: str,
        aws_access_key_id: str | None,
        aws_secret_access_key: str | None,
    ) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    @classmethod
    def from_env(cls) -> "S3Client":
        return cls(
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def get_json(self, *, bucket: str, key: str) -> dict[str, Any]:
        response = self._client.get_object(Bucket=bucket, Key=key)
        raw_bytes = response["Body"].read()
        return json.loads(raw_bytes.decode("utf-8"))

    def put_json(self, *, bucket: str, key: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json; charset=utf-8",
        )
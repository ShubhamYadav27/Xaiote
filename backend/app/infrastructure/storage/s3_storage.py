import boto3
from botocore.client import Config

from app.core.config import settings
from app.core.interfaces import ObjectStorage


class S3Storage(ObjectStorage):
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )

    async def upload(self, bucket_name: str, object_name: str, data: bytes):
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except Exception:  # noqa: BLE001
            self.client.create_bucket(Bucket=bucket_name)

        self.client.put_object(Bucket=bucket_name, Key=object_name, Body=data)

    async def download(self, bucket_name: str, object_name: str) -> bytes:
        response = self.client.get_object(Bucket=bucket_name, Key=object_name)
        return response["Body"].read()

    async def delete(self, bucket_name: str, object_name: str):
        self.client.delete_object(Bucket=bucket_name, Key=object_name)

    async def exists(self, bucket_name: str, object_name: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket_name, Key=object_name)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def get_presigned_url(self, bucket_name: str, object_name: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=3600,
        )


storage_client = S3Storage()


def get_storage() -> ObjectStorage:
    return storage_client

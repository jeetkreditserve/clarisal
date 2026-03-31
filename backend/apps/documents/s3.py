import boto3
from django.conf import settings


def _client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def upload_file(file_obj, key, content_type):
    _client().upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        key,
        ExtraArgs={'ContentType': content_type},
    )


def generate_presigned_url(key, expiry=900):
    return _client().generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
        ExpiresIn=expiry,
    )


def delete_file(key):
    _client().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)

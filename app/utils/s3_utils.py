from pathlib import Path
from uuid import UUID, uuid4

import boto3
from fastapi import HTTPException, UploadFile

from app.utils.settings import settings

S3_BUCKET_TRANSACTIONS = settings.S3_BUCKET_TRANSACTIONS


def _client():
    """Explicit region_name provided, without it, boto3 falls back to us-east-1's legacy global endpoint, which fails on any bucket outside that region with a confusing
    signing error instead of a clear one."""
    return boto3.client("s3", region_name=settings.AWS_REGION)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


def validate_file(file: UploadFile, id: UUID) -> str:
    filename = file.filename
    content_type = file.content_type

    if not filename:
        raise HTTPException(400, "Filename not found")

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Invalid file type")

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "Invalid content type")

    ext = Path(filename).suffix.lower().lstrip(".")
    key = f"{id}_{uuid4().hex}.{ext}"

    return key


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(file: UploadFile, id: UUID) -> str:
    """Like validate_file, but images only (no PDFs) and size-capped - for
    avatars, which are displayed in the browser rather than downloaded."""
    filename = file.filename

    if not filename:
        raise HTTPException(400, "Filename not found")

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(400, "Invalid file type. Use a JPG, PNG or WebP image")

    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(400, "Invalid content type. Use a JPG, PNG or WebP image")

    if file.size is not None and file.size > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image is too large. The limit is 5MB")

    return f"{id}_{uuid4().hex}.{ext}"


def upload_file(file, bucket, object_name=None, content_type=None):
    """Upload a file to an S3 bucket

    :param file: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :param content_type: Stored as the object's Content-Type. Without it S3
        serves the object as binary/octet-stream, which browsers download
        instead of displaying inline.
    :return: True if file was uploaded, else False
    """

    # Upload the file
    _client().upload_fileobj(
        file,
        bucket,
        object_name,
        ExtraArgs={"ContentType": content_type} if content_type else None,
    )


def delete_file(bucket, object_name):
    """Delete an object from an S3 bucket. Not raised on a missing key: S3's
    delete is idempotent, so this is safe to call speculatively."""
    _client().delete_object(Bucket=bucket, Key=object_name)


def get_image_url(key, bucket=S3_BUCKET_TRANSACTIONS):
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=900,  # 15 minutes
    )

import boto3
from fastapi import HTTPException, UploadFile
from pathlib import Path
from uuid import UUID, uuid4
from app.utils.settings import settings



S3_BUCKET_NAME = settings.S3_BUCKET_NAME

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

def validate_file(file: UploadFile, trans_id: UUID) -> str:
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
    key = f"{trans_id}_{uuid4().hex}.{ext}"
    
    return f"transactions/{key}" # upload to transactions directory in s3 bucket


def upload_file(file, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # Upload the file
    s3_client = boto3.client('s3')
    s3_client.upload_fileobj(
        file, 
        bucket, 
        object_name, 
    )


def get_image_url(key):
    s3_client = boto3.client('s3')
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=900  # 15 minutes
    )
    
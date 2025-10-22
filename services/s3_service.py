import os
import time
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config


def upload_buffer_to_s3(file_buffer: bytes, mime_type: str, original_filename: str, folder_name: str) -> Optional[str]:
    """
    Uploads a bytes file to DigitalOcean Spaces (S3-compatible).
    
    Args:
        file_buffer: The file content as bytes
        mime_type: The MIME type of the file
        original_filename: The original filename
        folder_name: The folder name to upload to
        
    Returns:
        The public URL of the uploaded file, or None if upload fails
        
    Raises:
        ValueError: If required environment variables are missing
        Exception: If upload fails
    """
    
    # Load ENV vars
    spaces_region = os.getenv("SPACES_REGION")
    spaces_endpoint = os.getenv("SPACES_ENDPOINT")
    access_key = os.getenv("SPACES_ACCESS_KEY")
    secret_key = os.getenv("SPACES_SECRET_KEY")
    bucket_name = os.getenv("SPACES_BUCKET")
    
    if not all([bucket_name, access_key, secret_key, spaces_endpoint, spaces_region]):
        raise ValueError("Missing required DigitalOcean Spaces env variables")
    
    try:
        # Configure S3 client
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=spaces_region
        )
        
        s3_client = session.client(
            's3',
            endpoint_url=spaces_endpoint,
            config=Config(signature_version='s3v4')
        )
        
        # Create a unique file key
        filename = Path(original_filename).name
        timestamp = int(time.time())
        object_key = f"{folder_name}/{timestamp}_{filename}"
        
        # Upload the file
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_buffer,
            ACL='public-read',
            ContentType=mime_type
        )
        
        # Return the public URL
        url = f"{spaces_endpoint}/{bucket_name}/{object_key}"
        return url
        
    except NoCredentialsError:
        raise Exception("AWS credentials not found")
    except ClientError as e:
        raise Exception(f"Failed to upload to DO Spaces: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")


def upload_file_to_s3(file_path: str, folder_name: str) -> Optional[str]:
    """
    Uploads a file from disk to DigitalOcean Spaces.
    
    Args:
        file_path: Path to the file on disk
        folder_name: The folder name to upload to
        
    Returns:
        The public URL of the uploaded file, or None if upload fails
    """
    try:
        with open(file_path, 'rb') as file:
            file_buffer = file.read()
        
        # Determine MIME type based on file extension
        file_extension = Path(file_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        filename = Path(file_path).name
        return upload_buffer_to_s3(file_buffer, mime_type, filename, folder_name)
        
    except FileNotFoundError:
        raise Exception(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Failed to read file: {str(e)}")


def delete_file_from_s3(object_key: str) -> bool:
    """
    Deletes a file from DigitalOcean Spaces.
    
    Args:
        object_key: The S3 object key to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    spaces_region = os.getenv("SPACES_REGION")
    spaces_endpoint = os.getenv("SPACES_ENDPOINT")
    access_key = os.getenv("SPACES_ACCESS_KEY")
    secret_key = os.getenv("SPACES_SECRET_KEY")
    bucket_name = os.getenv("SPACES_BUCKET")
    
    if not all([bucket_name, access_key, secret_key, spaces_endpoint, spaces_region]):
        raise ValueError("Missing required DigitalOcean Spaces env variables")
    
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=spaces_region
        )
        
        s3_client = session.client(
            's3',
            endpoint_url=spaces_endpoint,
            config=Config(signature_version='s3v4')
        )
        
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        return True
        
    except Exception as e:
        print(f"Failed to delete file: {str(e)}")
        return False


def get_file_url(object_key: str) -> str:
    """
    Gets the public URL for a file in DigitalOcean Spaces.
    
    Args:
        object_key: The S3 object key
        
    Returns:
        The public URL of the file
    """
    spaces_endpoint = os.getenv("SPACES_ENDPOINT")
    bucket_name = os.getenv("SPACES_BUCKET")
    
    if not all([bucket_name, spaces_endpoint]):
        raise ValueError("Missing required DigitalOcean Spaces env variables")
    
    return f"{spaces_endpoint}/{bucket_name}/{object_key}"

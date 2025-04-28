from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING, BinaryIO, Optional, Tuple, Union

import ibm_boto3
from ibm_botocore.client import ClientError, Config

# Set up logger
from logger import get_logger
from service_types import Error, error

# Set up logging
logger = get_logger()
if TYPE_CHECKING:
    from ibm_boto3.resources.factory.s3 import ServiceResource
    from sliderblend.pkg import IBMSettings


def _create_client(credentials: IBMSettings) -> ServiceResource:
    logger.debug("Creating IBM COS client...")
    client = ibm_boto3.client(
        "s3",
        ibm_api_key_id=credentials.ibm_api_key,
        ibm_service_instance_id=credentials.ibm_bucket_instance_id,
        config=Config(signature_version="oauth"),
        endpoint_url=credentials.ibm_service_endpoint,
    )
    logger.info("IBM COS client created successfully.")
    return client


class IBMStorage:
    def __init__(self, settings: IBMSettings) -> None:
        logger.debug("Initializing IBMStorage class...")
        self.credentials = settings
        self._client = _create_client(self.credentials)

    def get_buckets(self):
        logger.info("Retrieving list of buckets")
        try:
            buckets = self._client.list_buckets()
            for bucket in buckets["Buckets"]:
                logger.debug("Bucket Name: %s", bucket["Name"])
        except ClientError as be:
            logger.error("CLIENT ERROR: %s", be)
        except Exception as e:
            logger.error(f"Unable to retrieve list buckets: {e}")

    def upload_to_bucket(
        self,
        file_data: Union[str, bytes, BinaryIO],
        object_name: str,
        folder_path: Optional[str] = None,
    ) -> Tuple[Optional[str], error]:
        bucket_name = self.credentials.ibm_bucket_name

        if folder_path:
            folder_path = folder_path.strip("/")
            if folder_path and not folder_path.endswith("/"):
                folder_path += "/"
            full_object_name = f"{folder_path}{object_name}"
        else:
            full_object_name = object_name

        logger.info("Uploading to IBM bucket: %s/%s", bucket_name, full_object_name)

        try:
            if isinstance(file_data, str):
                logger.debug("Uploading file from path: %s", file_data)
                self._client.upload_file(file_data, bucket_name, full_object_name)
            else:
                logger.debug("Uploading file from bytes/BinaryIO")
                file_obj = BytesIO(file_data)
                self._client.upload_fileobj(
                    file_obj,
                    bucket_name,
                    full_object_name,
                )

            logger.info("Upload successful: %s", full_object_name)
            object_location = f"https://{self.credentials.ibm_bucket_name}.{self.credentials.ibm_service_endpoint.removeprefix('https://')}/{full_object_name}"
            return object_location, None
        except Exception as e:
            logger.error("Upload failed: %s", e)
            return None, Error(f"Error uploading file to IBM COS: {e}")

    def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        folder_path: Optional[str] = None,
    ) -> Tuple[Optional[str], error]:
        if not os.path.exists(file_path):
            logger.warning("File not found: %s", file_path)
            return None, Error(f"File not found: {file_path}")

        if object_name is None:
            object_name = os.path.basename(file_path)
            logger.debug("Using default object name: %s", object_name)

        return self.upload_to_bucket(file_path, object_name, folder_path)

    def upload_bytes(
        self, data: bytes, object_name: str, folder_path: Optional[str] = None
    ) -> Tuple[Optional[str], Error]:
        logger.debug("Preparing to upload bytes as: %s", object_name)
        return self.upload_to_bucket(data, object_name, folder_path)

    def download_objects(
        self,
        object_name: str,
        destination: Union[str, BinaryIO] = None,
    ) -> Tuple[Optional[str], error]:
        logger.info("Downloading object: %s", object_name)
        try:
            self._client.download_fileobj(
                Bucket=self.credentials.ibm_bucket_name,
                Key=object_name,
                Fileobj=destination,
            )
            logger.info("Downloaded object: %s", object_name)
            return f"<in-memory:{object_name}>", None
        except Exception as e:
            logger.error("Download failed: %s", e)
            return None, Error(f"Error downloading object: {str(e)}")

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> Tuple[Optional[str], error]:
        logger.info("Generating presigned URL for: %s", key)
        try:
            url = self._client.meta.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.credentials.bucket_name, "Key": key},
                ExpiresIn=expiration,
                HttpMethod=http_method,
            )
            logger.debug("Presigned URL generated:")
            return url, None
        except Exception as e:
            logger.error("Presigned URL generation failed: %s", e)
            return None, Error("Failed to generate presigned URL: {str(e)}")

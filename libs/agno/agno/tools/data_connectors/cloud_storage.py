"""
Cloud storage connectors for AWS S3, Google Cloud Storage, and Azure Blob Storage.

Supports:
- AWS S3
- Google Cloud Storage (GCS)
- Azure Blob Storage
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agno.tools.data_connectors.base import DataConnectorBase, DataConnectorConfig, with_retry
from agno.utils.log import logger


@dataclass
class CloudStorageConfig(DataConnectorConfig):
    """Configuration for cloud storage connectors."""

    bucket_name: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    credentials_path: Optional[str] = None
    project_id: Optional[str] = None
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    connection_string: Optional[str] = None


class S3Connector(DataConnectorBase):
    """AWS S3 connector with multipart upload support."""

    def __init__(
        self,
        bucket_name: str,
        config: Optional[CloudStorageConfig] = None,
        **s3_kwargs,
    ):
        """
        Initialize S3 connector.

        Args:
            bucket_name: S3 bucket name
            config: Cloud storage configuration
            **s3_kwargs: Additional boto3 parameters
        """
        super().__init__(config or CloudStorageConfig())
        if isinstance(self.config, CloudStorageConfig):
            self.config.bucket_name = bucket_name
        self.s3_kwargs = s3_kwargs
        self._client = None
        self._resource = None

    def connect(self) -> None:
        """Connect to S3."""
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 not installed. Install with: pip install boto3")

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        try:
            session_kwargs = {}
            if config.access_key and config.secret_key:
                session_kwargs["aws_access_key_id"] = config.access_key
                session_kwargs["aws_secret_access_key"] = config.secret_key

            if config.region:
                session_kwargs["region_name"] = config.region

            session = boto3.Session(**session_kwargs)
            self._client = session.client("s3", **self.s3_kwargs)
            self._resource = session.resource("s3")

            self._is_connected = True
            self._record_metric("connections")
            logger.info(f"Connected to S3 bucket: {config.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close S3 connection."""
        self._client = None
        self._resource = None
        self._is_connected = False
        logger.info("Disconnected from S3")

    def read(
        self, query: str, as_bytes: bool = False, **kwargs
    ) -> Union[str, bytes, Dict[str, Any]]:
        """
        Read object from S3.

        Args:
            query: S3 object key
            as_bytes: Whether to return bytes instead of string
            **kwargs: Additional get_object parameters

        Returns:
            Object content as string or bytes
        """
        if not self._is_connected or not self._client:
            self.connect()

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        def _read_object():
            response = self._client.get_object(
                Bucket=config.bucket_name, Key=query, **kwargs
            )
            content = response["Body"].read()
            return content if as_bytes else content.decode("utf-8")

        try:
            result = with_retry(_read_object, config.retry_config)()
            self._record_metric("reads")
            logger.info(f"Read object from S3: {query}")
            return result
        except Exception as e:
            logger.error(f"Error reading from S3: {e}")
            self._record_metric("errors")
            raise

    def write(
        self, data: Union[str, bytes], target: str, metadata: Optional[Dict[str, str]] = None, **kwargs
    ) -> None:
        """
        Write object to S3.

        Args:
            data: Data to write (string or bytes)
            target: S3 object key
            metadata: Object metadata
            **kwargs: Additional put_object parameters
        """
        if not self._is_connected or not self._client:
            self.connect()

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        def _write_object():
            body = data.encode("utf-8") if isinstance(data, str) else data

            put_kwargs = {"Bucket": config.bucket_name, "Key": target, "Body": body}

            if metadata:
                put_kwargs["Metadata"] = metadata

            put_kwargs.update(kwargs)
            self._client.put_object(**put_kwargs)

        try:
            with_retry(_write_object, config.retry_config)()
            self._record_metric("writes")
            logger.info(f"Wrote object to S3: {target}")
        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            self._record_metric("errors")
            raise

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket.

        Args:
            prefix: Object key prefix filter
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata
        """
        if not self._is_connected or not self._client:
            self.connect()

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        try:
            response = self._client.list_objects_v2(
                Bucket=config.bucket_name, Prefix=prefix, MaxKeys=max_keys
            )

            objects = response.get("Contents", [])
            logger.info(f"Listed {len(objects)} objects from S3")
            return objects
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            raise

    def delete(self, key: str) -> None:
        """Delete object from S3."""
        if not self._is_connected or not self._client:
            self.connect()

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        try:
            self._client.delete_object(Bucket=config.bucket_name, Key=key)
            logger.info(f"Deleted object from S3: {key}")
        except Exception as e:
            logger.error(f"Error deleting from S3: {e}")
            raise


class GCSConnector(DataConnectorBase):
    """Google Cloud Storage connector."""

    def __init__(
        self,
        bucket_name: str,
        config: Optional[CloudStorageConfig] = None,
        **gcs_kwargs,
    ):
        """
        Initialize GCS connector.

        Args:
            bucket_name: GCS bucket name
            config: Cloud storage configuration
            **gcs_kwargs: Additional GCS client parameters
        """
        super().__init__(config or CloudStorageConfig())
        if isinstance(self.config, CloudStorageConfig):
            self.config.bucket_name = bucket_name
        self.gcs_kwargs = gcs_kwargs
        self._client = None
        self._bucket = None

    def connect(self) -> None:
        """Connect to GCS."""
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage not installed. Install with: pip install google-cloud-storage"
            )

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        try:
            client_kwargs = {}
            if config.project_id:
                client_kwargs["project"] = config.project_id
            if config.credentials_path:
                client_kwargs["credentials"] = config.credentials_path

            client_kwargs.update(self.gcs_kwargs)

            self._client = storage.Client(**client_kwargs)
            self._bucket = self._client.bucket(config.bucket_name)

            self._is_connected = True
            self._record_metric("connections")
            logger.info(f"Connected to GCS bucket: {config.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to connect to GCS: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close GCS connection."""
        self._client = None
        self._bucket = None
        self._is_connected = False
        logger.info("Disconnected from GCS")

    def read(self, query: str, as_bytes: bool = False, **kwargs) -> Union[str, bytes]:
        """
        Read blob from GCS.

        Args:
            query: Blob name
            as_bytes: Whether to return bytes instead of string
            **kwargs: Additional download parameters

        Returns:
            Blob content as string or bytes
        """
        if not self._is_connected or not self._bucket:
            self.connect()

        def _read_blob():
            blob = self._bucket.blob(query)

            if as_bytes:
                return blob.download_as_bytes(**kwargs)
            else:
                return blob.download_as_text(**kwargs)

        try:
            result = with_retry(_read_blob, self.config.retry_config)()
            self._record_metric("reads")
            logger.info(f"Read blob from GCS: {query}")
            return result
        except Exception as e:
            logger.error(f"Error reading from GCS: {e}")
            self._record_metric("errors")
            raise

    def write(
        self, data: Union[str, bytes], target: str, metadata: Optional[Dict[str, str]] = None, **kwargs
    ) -> None:
        """
        Write blob to GCS.

        Args:
            data: Data to write
            target: Blob name
            metadata: Blob metadata
            **kwargs: Additional upload parameters
        """
        if not self._is_connected or not self._bucket:
            self.connect()

        def _write_blob():
            blob = self._bucket.blob(target)

            if metadata:
                blob.metadata = metadata

            if isinstance(data, bytes):
                blob.upload_from_string(data, **kwargs)
            else:
                blob.upload_from_string(data.encode("utf-8"), **kwargs)

        try:
            with_retry(_write_blob, self.config.retry_config)()
            self._record_metric("writes")
            logger.info(f"Wrote blob to GCS: {target}")
        except Exception as e:
            logger.error(f"Error writing to GCS: {e}")
            self._record_metric("errors")
            raise

    def list_blobs(self, prefix: str = "", max_results: int = 1000) -> List[Any]:
        """List blobs in GCS bucket."""
        if not self._is_connected or not self._bucket:
            self.connect()

        try:
            blobs = list(self._bucket.list_blobs(prefix=prefix, max_results=max_results))
            logger.info(f"Listed {len(blobs)} blobs from GCS")
            return blobs
        except Exception as e:
            logger.error(f"Error listing GCS blobs: {e}")
            raise


class AzureBlobConnector(DataConnectorBase):
    """Azure Blob Storage connector."""

    def __init__(
        self,
        container_name: str,
        config: Optional[CloudStorageConfig] = None,
        **azure_kwargs,
    ):
        """
        Initialize Azure Blob connector.

        Args:
            container_name: Azure container name
            config: Cloud storage configuration
            **azure_kwargs: Additional Azure client parameters
        """
        super().__init__(config or CloudStorageConfig())
        if isinstance(self.config, CloudStorageConfig):
            self.config.bucket_name = container_name  # Reuse bucket_name field
        self.azure_kwargs = azure_kwargs
        self._client = None
        self._container_client = None

    def connect(self) -> None:
        """Connect to Azure Blob Storage."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob not installed. Install with: pip install azure-storage-blob"
            )

        config = self.config
        if not isinstance(config, CloudStorageConfig):
            raise ValueError("Invalid config type")

        try:
            if config.connection_string:
                self._client = BlobServiceClient.from_connection_string(
                    config.connection_string, **self.azure_kwargs
                )
            elif config.account_name and config.account_key:
                account_url = f"https://{config.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(
                    account_url=account_url, credential=config.account_key, **self.azure_kwargs
                )
            else:
                raise ValueError("Must provide connection_string or account_name/account_key")

            self._container_client = self._client.get_container_client(config.bucket_name)

            self._is_connected = True
            self._record_metric("connections")
            logger.info(f"Connected to Azure container: {config.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Azure: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close Azure connection."""
        if self._client:
            self._client.close()
        self._client = None
        self._container_client = None
        self._is_connected = False
        logger.info("Disconnected from Azure")

    def read(self, query: str, as_bytes: bool = False, **kwargs) -> Union[str, bytes]:
        """
        Read blob from Azure.

        Args:
            query: Blob name
            as_bytes: Whether to return bytes instead of string
            **kwargs: Additional download parameters

        Returns:
            Blob content
        """
        if not self._is_connected or not self._container_client:
            self.connect()

        def _read_blob():
            blob_client = self._container_client.get_blob_client(query)
            content = blob_client.download_blob(**kwargs).readall()
            return content if as_bytes else content.decode("utf-8")

        try:
            result = with_retry(_read_blob, self.config.retry_config)()
            self._record_metric("reads")
            logger.info(f"Read blob from Azure: {query}")
            return result
        except Exception as e:
            logger.error(f"Error reading from Azure: {e}")
            self._record_metric("errors")
            raise

    def write(
        self, data: Union[str, bytes], target: str, metadata: Optional[Dict[str, str]] = None, **kwargs
    ) -> None:
        """
        Write blob to Azure.

        Args:
            data: Data to write
            target: Blob name
            metadata: Blob metadata
            **kwargs: Additional upload parameters
        """
        if not self._is_connected or not self._container_client:
            self.connect()

        def _write_blob():
            blob_client = self._container_client.get_blob_client(target)
            body = data.encode("utf-8") if isinstance(data, str) else data

            upload_kwargs = {}
            if metadata:
                upload_kwargs["metadata"] = metadata
            upload_kwargs.update(kwargs)

            blob_client.upload_blob(body, overwrite=True, **upload_kwargs)

        try:
            with_retry(_write_blob, self.config.retry_config)()
            self._record_metric("writes")
            logger.info(f"Wrote blob to Azure: {target}")
        except Exception as e:
            logger.error(f"Error writing to Azure: {e}")
            self._record_metric("errors")
            raise

    def list_blobs(self, name_starts_with: str = "") -> List[Any]:
        """List blobs in Azure container."""
        if not self._is_connected or not self._container_client:
            self.connect()

        try:
            blobs = list(self._container_client.list_blobs(name_starts_with=name_starts_with))
            logger.info(f"Listed {len(blobs)} blobs from Azure")
            return blobs
        except Exception as e:
            logger.error(f"Error listing Azure blobs: {e}")
            raise


class CloudStorageConnector(DataConnectorBase):
    """Unified cloud storage connector supporting S3, GCS, and Azure."""

    def __init__(
        self,
        provider: str,
        bucket_name: str,
        config: Optional[CloudStorageConfig] = None,
        **provider_kwargs,
    ):
        """
        Initialize cloud storage connector.

        Args:
            provider: Cloud provider (s3, gcs, azure)
            bucket_name: Bucket/container name
            config: Cloud storage configuration
            **provider_kwargs: Provider-specific parameters
        """
        super().__init__(config or CloudStorageConfig())
        self.provider = provider.lower()

        # Create appropriate connector
        if self.provider in ["s3", "aws"]:
            self._connector = S3Connector(bucket_name, config, **provider_kwargs)
        elif self.provider in ["gcs", "gcp", "google"]:
            self._connector = GCSConnector(bucket_name, config, **provider_kwargs)
        elif self.provider in ["azure", "azureblob"]:
            self._connector = AzureBlobConnector(bucket_name, config, **provider_kwargs)
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")

    def connect(self) -> None:
        """Connect to cloud storage."""
        self._connector.connect()
        self._is_connected = self._connector._is_connected

    def disconnect(self) -> None:
        """Disconnect from cloud storage."""
        self._connector.disconnect()
        self._is_connected = False

    def read(self, query: str, **kwargs) -> Any:
        """Read data from cloud storage."""
        return self._connector.read(query, **kwargs)

    def write(self, data: Any, target: str, **kwargs) -> None:
        """Write data to cloud storage."""
        self._connector.write(data, target, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        return self._connector.get_metrics()

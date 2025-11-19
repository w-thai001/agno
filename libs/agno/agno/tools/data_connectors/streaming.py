"""
Streaming data source connectors.

Supports:
- Apache Kafka
- RabbitMQ
- Redis Streams
- WebSocket streams
"""

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from agno.tools.data_connectors.base import DataConnectorBase, DataConnectorConfig
from agno.utils.log import logger


@dataclass
class StreamingConfig(DataConnectorConfig):
    """Configuration for streaming connectors."""

    bootstrap_servers: Optional[List[str]] = None
    topic: Optional[str] = None
    group_id: Optional[str] = None
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    max_poll_records: int = 500
    consumer_timeout_ms: int = 1000


class KafkaConnector(DataConnectorBase):
    """Apache Kafka connector for streaming data."""

    def __init__(
        self,
        config: Optional[StreamingConfig] = None,
        **kafka_kwargs,
    ):
        """
        Initialize Kafka connector.

        Args:
            config: Streaming configuration
            **kafka_kwargs: Additional Kafka parameters
        """
        super().__init__(config or StreamingConfig())
        self.kafka_kwargs = kafka_kwargs
        self._producer = None
        self._consumer = None

    def connect(self) -> None:
        """Connect to Kafka cluster."""
        try:
            from kafka import KafkaProducer, KafkaConsumer
        except ImportError:
            raise ImportError("kafka-python not installed. Install with: pip install kafka-python")

        config = self.config
        if not isinstance(config, StreamingConfig):
            raise ValueError("Invalid config type")

        try:
            # Create producer
            producer_config = {
                "bootstrap_servers": config.bootstrap_servers,
                "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
            }
            producer_config.update(self.kafka_kwargs.get("producer", {}))
            self._producer = KafkaProducer(**producer_config)

            # Create consumer if topic and group_id are specified
            if config.topic and config.group_id:
                consumer_config = {
                    "bootstrap_servers": config.bootstrap_servers,
                    "group_id": config.group_id,
                    "auto_offset_reset": config.auto_offset_reset,
                    "enable_auto_commit": config.enable_auto_commit,
                    "max_poll_records": config.max_poll_records,
                    "consumer_timeout_ms": config.consumer_timeout_ms,
                    "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
                }
                consumer_config.update(self.kafka_kwargs.get("consumer", {}))
                self._consumer = KafkaConsumer(config.topic, **consumer_config)

            self._is_connected = True
            self._record_metric("connections")
            logger.info("Connected to Kafka cluster")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close Kafka connections."""
        if self._producer:
            self._producer.close()
            self._producer = None

        if self._consumer:
            self._consumer.close()
            self._consumer = None

        self._is_connected = False
        logger.info("Disconnected from Kafka")

    def read(
        self, query: Optional[int] = None, timeout_ms: Optional[int] = None, **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Consume messages from Kafka.

        Args:
            query: Maximum number of messages to consume (None for continuous)
            timeout_ms: Poll timeout in milliseconds
            **kwargs: Additional poll parameters

        Yields:
            Message data
        """
        if not self._consumer:
            raise RuntimeError("Consumer not initialized. Provide topic and group_id in config.")

        try:
            count = 0
            poll_timeout = timeout_ms or 1000

            for message in self._consumer:
                yield {
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "key": message.key.decode("utf-8") if message.key else None,
                    "value": message.value,
                    "timestamp": message.timestamp,
                }

                count += 1
                self._record_metric("reads")

                if query and count >= query:
                    break

        except Exception as e:
            logger.error(f"Error consuming from Kafka: {e}")
            self._record_metric("errors")
            raise

    def write(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]], target: str, key: Optional[str] = None, **kwargs
    ) -> None:
        """
        Produce messages to Kafka topic.

        Args:
            data: Message data (dict or list of dicts)
            target: Topic name
            key: Optional message key
            **kwargs: Additional send parameters
        """
        if not self._producer:
            raise RuntimeError("Producer not initialized")

        try:
            messages = [data] if isinstance(data, dict) else data

            for msg in messages:
                key_bytes = key.encode("utf-8") if key else None
                future = self._producer.send(target, value=msg, key=key_bytes, **kwargs)
                # Wait for send to complete
                future.get(timeout=10)
                self._record_metric("writes")

            self._producer.flush()
            logger.info(f"Sent {len(messages)} messages to topic {target}")

        except Exception as e:
            logger.error(f"Error producing to Kafka: {e}")
            self._record_metric("errors")
            raise


class RabbitMQConnector(DataConnectorBase):
    """RabbitMQ connector for message queuing."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/",
        config: Optional[DataConnectorConfig] = None,
        **rabbitmq_kwargs,
    ):
        """
        Initialize RabbitMQ connector.

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            username: Username
            password: Password
            virtual_host: Virtual host
            config: Connector configuration
            **rabbitmq_kwargs: Additional pika parameters
        """
        super().__init__(config)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.rabbitmq_kwargs = rabbitmq_kwargs
        self._connection = None
        self._channel = None

    def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            import pika
        except ImportError:
            raise ImportError("pika not installed. Install with: pip install pika")

        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                **self.rabbitmq_kwargs,
            )

            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()

            self._is_connected = True
            self._record_metric("connections")
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()

        self._connection = None
        self._channel = None
        self._is_connected = False
        logger.info("Disconnected from RabbitMQ")

    def read(
        self, query: str, max_messages: Optional[int] = None, auto_ack: bool = False, **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Consume messages from RabbitMQ queue.

        Args:
            query: Queue name
            max_messages: Maximum number of messages to consume
            auto_ack: Whether to auto-acknowledge messages
            **kwargs: Additional consume parameters

        Yields:
            Message data
        """
        if not self._channel:
            raise RuntimeError("Not connected to RabbitMQ")

        try:
            count = 0

            # Declare queue (idempotent)
            self._channel.queue_declare(queue=query, durable=True)

            for method_frame, properties, body in self._channel.consume(
                queue=query, auto_ack=auto_ack, **kwargs
            ):
                if method_frame:
                    yield {
                        "delivery_tag": method_frame.delivery_tag,
                        "exchange": method_frame.exchange,
                        "routing_key": method_frame.routing_key,
                        "body": json.loads(body.decode("utf-8")),
                        "properties": {
                            "content_type": properties.content_type,
                            "correlation_id": properties.correlation_id,
                            "message_id": properties.message_id,
                        },
                    }

                    count += 1
                    self._record_metric("reads")

                    if max_messages and count >= max_messages:
                        self._channel.cancel()
                        break

        except Exception as e:
            logger.error(f"Error consuming from RabbitMQ: {e}")
            self._record_metric("errors")
            raise

    def write(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        target: str,
        exchange: str = "",
        **kwargs,
    ) -> None:
        """
        Publish messages to RabbitMQ queue.

        Args:
            data: Message data
            target: Queue/routing key
            exchange: Exchange name (empty string for default)
            **kwargs: Additional publish parameters
        """
        if not self._channel:
            raise RuntimeError("Not connected to RabbitMQ")

        try:
            import pika

            # Declare queue
            self._channel.queue_declare(queue=target, durable=True)

            messages = [data] if isinstance(data, dict) else data

            for msg in messages:
                body = json.dumps(msg).encode("utf-8")
                self._channel.basic_publish(
                    exchange=exchange,
                    routing_key=target,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                        content_type="application/json",
                    ),
                    **kwargs,
                )
                self._record_metric("writes")

            logger.info(f"Published {len(messages)} messages to {target}")

        except Exception as e:
            logger.error(f"Error publishing to RabbitMQ: {e}")
            self._record_metric("errors")
            raise


class RedisStreamConnector(DataConnectorBase):
    """Redis Streams connector."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        config: Optional[DataConnectorConfig] = None,
        **redis_kwargs,
    ):
        """
        Initialize Redis Streams connector.

        Args:
            host: Redis host
            port: Redis port
            db: Database number
            password: Password (if required)
            config: Connector configuration
            **redis_kwargs: Additional redis parameters
        """
        super().__init__(config)
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_kwargs = redis_kwargs
        self._client = None

    def connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis
        except ImportError:
            raise ImportError("redis not installed. Install with: pip install redis")

        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False,
                **self.redis_kwargs,
            )

            # Test connection
            self._client.ping()

            self._is_connected = True
            self._record_metric("connections")
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None

        self._is_connected = False
        logger.info("Disconnected from Redis")

    def read(
        self,
        query: str,
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
        count: Optional[int] = None,
        block: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Read from Redis stream.

        Args:
            query: Stream name
            consumer_group: Consumer group name
            consumer_name: Consumer name
            count: Maximum number of messages
            block: Block for N milliseconds
            **kwargs: Additional xread/xreadgroup parameters

        Returns:
            List of stream messages
        """
        if not self._client:
            raise RuntimeError("Not connected to Redis")

        try:
            if consumer_group and consumer_name:
                # Read as part of consumer group
                messages = self._client.xreadgroup(
                    groupname=consumer_group,
                    consumername=consumer_name,
                    streams={query: ">"},
                    count=count,
                    block=block,
                    **kwargs,
                )
            else:
                # Read from stream directly
                messages = self._client.xread(
                    streams={query: "0"}, count=count, block=block, **kwargs
                )

            results = []
            for stream_name, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    # Decode message data
                    decoded_data = {k.decode("utf-8"): v.decode("utf-8") for k, v in msg_data.items()}
                    results.append(
                        {
                            "stream": stream_name.decode("utf-8") if isinstance(stream_name, bytes) else stream_name,
                            "id": msg_id.decode("utf-8") if isinstance(msg_id, bytes) else msg_id,
                            "data": decoded_data,
                        }
                    )

            self._record_metric("reads", len(results))
            return results

        except Exception as e:
            logger.error(f"Error reading from Redis stream: {e}")
            self._record_metric("errors")
            raise

    def write(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]], target: str, maxlen: Optional[int] = None, **kwargs
    ) -> None:
        """
        Write to Redis stream.

        Args:
            data: Message data
            target: Stream name
            maxlen: Maximum stream length (optional trimming)
            **kwargs: Additional xadd parameters
        """
        if not self._client:
            raise RuntimeError("Not connected to Redis")

        try:
            messages = [data] if isinstance(data, dict) else data

            for msg in messages:
                self._client.xadd(name=target, fields=msg, maxlen=maxlen, **kwargs)
                self._record_metric("writes")

            logger.info(f"Wrote {len(messages)} messages to Redis stream {target}")

        except Exception as e:
            logger.error(f"Error writing to Redis stream: {e}")
            self._record_metric("errors")
            raise


class StreamingConnector(DataConnectorBase):
    """Unified streaming connector supporting Kafka, RabbitMQ, and Redis Streams."""

    def __init__(
        self,
        stream_type: str,
        config: Optional[Union[StreamingConfig, DataConnectorConfig]] = None,
        **stream_kwargs,
    ):
        """
        Initialize streaming connector.

        Args:
            stream_type: Streaming type (kafka, rabbitmq, redis)
            config: Streaming configuration
            **stream_kwargs: Stream-specific parameters
        """
        super().__init__(config)
        self.stream_type = stream_type.lower()

        # Create appropriate connector
        if self.stream_type == "kafka":
            self._connector = KafkaConnector(config, **stream_kwargs)  # type: ignore
        elif self.stream_type == "rabbitmq":
            self._connector = RabbitMQConnector(config=config, **stream_kwargs)
        elif self.stream_type == "redis":
            self._connector = RedisStreamConnector(config=config, **stream_kwargs)
        else:
            raise ValueError(f"Unsupported streaming type: {stream_type}")

    def connect(self) -> None:
        """Connect to streaming source."""
        self._connector.connect()
        self._is_connected = self._connector._is_connected

    def disconnect(self) -> None:
        """Disconnect from streaming source."""
        self._connector.disconnect()
        self._is_connected = False

    def read(self, query: Any, **kwargs) -> Any:
        """Read from streaming source."""
        return self._connector.read(query, **kwargs)

    def write(self, data: Any, target: str, **kwargs) -> None:
        """Write to streaming source."""
        self._connector.write(data, target, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        return self._connector.get_metrics()

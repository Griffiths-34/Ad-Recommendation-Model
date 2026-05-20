"""Kafka producer for event publishing"""

import json
import logging
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Attempt a top-level import so static analyzers can resolve the symbol; if aiokafka
# is not installed in the current environment we provide a None fallback so the
# runtime can detect and raise a clear error when attempting to start the producer.
try:
    from aiokafka import AIOKafkaProducer  # type: ignore
except Exception:
    AIOKafkaProducer = None  # type: ignore

# Lightweight shim to provide a minimal structlog-like API backed by the stdlib logging module.
class _StructlogShim:
    def __init__(self, name: str = "kafka_producer"):
        self._logger = logging.getLogger(name)
        if not logging.root.handlers:
            # Configure basic logging if the application hasn't set up handlers.
            logging.basicConfig(level=logging.INFO)

    def get_logger(self):
        class _Logger:
            def __init__(self, l):
                self._l = l

            def _log(self, level, event: str, **kwargs):
                details = " ".join(f"{k}={v!r}" for k, v in kwargs.items()) if kwargs else ""
                msg = f"{event} | {details}" if details else event
                self._l.log(level, msg)

            def info(self, event: str, **kwargs):
                self._log(logging.INFO, event, **kwargs)

            def debug(self, event: str, **kwargs):
                self._log(logging.DEBUG, event, **kwargs)

            def warning(self, event: str, **kwargs):
                self._log(logging.WARNING, event, **kwargs)

            def error(self, event: str, **kwargs):
                self._log(logging.ERROR, event, **kwargs)

            def exception(self, event: str, **kwargs):
                # Keep same signature as structlog.exception (logs an error)
                self._log(logging.ERROR, event, **kwargs)

        return _Logger(self._logger)

logger = _StructlogShim().get_logger()


class KafkaProducerClient:
    """Async Kafka producer for publishing events"""
    def __init__(self) -> None:
        # aiokafka may not be installed in this environment; ensure it's available.
        if AIOKafkaProducer is None:
            raise RuntimeError("aiokafka is not installed; install aiokafka to use KafkaProducerClient")
        self.producer = None
        self.is_connected: bool = False

    async def start(self) -> None:
        """Start the Kafka producer"""
        try:
            # Import aiokafka lazily so the module can be analyzed/installed
            # in environments where aiokafka is not present at edit time.
            from aiokafka import AIOKafkaProducer  # local import

            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type=settings.KAFKA_COMPRESSION_TYPE,
                acks=settings.KAFKA_ACKS,
                max_batch_size=settings.KAFKA_BATCH_SIZE,
                linger_ms=settings.KAFKA_LINGER_MS,
                max_request_size=1048576,  # 1MB
            )
            await self.producer.start()
            self.is_connected = True
            logger.info("kafka_producer_started", bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.error("kafka_producer_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer"""
        if self.producer:
            try:
                await self.producer.stop()
            finally:
                self.is_connected = False
                logger.info("kafka_producer_stopped")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def send_event(self, topic: str, event: Dict[str, Any], key: Optional[str] = None) -> None:
        """
        Send an event to Kafka topic

        Args:
            topic: Kafka topic name
            event: Event data dictionary
            key: Optional partition key
        """
        if not self.producer or not self.is_connected:
            raise RuntimeError("Kafka producer is not connected")

        try:
            # Convert key to bytes if provided
            key_bytes = key.encode("utf-8") if key else None

            # Send to Kafka
            await self.producer.send_and_wait(topic=topic, value=event, key=key_bytes)

            logger.debug(
                "event_published",
                topic=topic,
                event_type=event.get("eventName"),
                user_id=event.get("userId"),
            )
        except Exception as e:
            logger.error(
                "kafka_send_failed",
                topic=topic,
                error=str(e),
                event_type=event.get("eventName"),
            )
            # Send to dead letter queue, but don't suppress original error
            try:
                await self._send_to_dlq(event, str(e))
            except Exception:
                # _send_to_dlq errors are logged inside that method
                pass
            raise

    async def send_batch(self, topic: str, events: List[Dict[str, Any]]) -> None:
        """
        Send a batch of events to Kafka

        Args:
            topic: Kafka topic name
            events: List of event dictionaries
        """
        if not self.producer or not self.is_connected:
            raise RuntimeError("Kafka producer is not connected")

        try:
            for event in events:
                key = event.get("userId") or event.get("sessionId")
                key_bytes = key.encode("utf-8") if key else None

                await self.producer.send(topic=topic, value=event, key=key_bytes)

            # Wait for all messages to be delivered
            await self.producer.flush()

            logger.info("batch_published", topic=topic, event_count=len(events))
        except Exception as e:
            logger.error(
                "kafka_batch_send_failed",
                topic=topic,
                error=str(e),
                event_count=len(events),
            )
            # Optionally send failing batch or items to DLQ here
            raise

    async def _send_to_dlq(self, event: Dict[str, Any], error: str) -> None:
        """Send failed event to dead letter queue"""
        if not self.producer:
            logger.error("dlq_send_failed", error="producer_not_initialized")
            return

        try:
            dlq_event = {
                **event,
                "error": error,
                "dlq_timestamp": event.get("timestamp"),
            }
            await self.producer.send_and_wait(topic=settings.KAFKA_TOPIC_EVENTS_DLQ, value=dlq_event)
            logger.info("event_sent_to_dlq", event_type=event.get("eventName"))
        except Exception as e:
            logger.error("dlq_send_failed", error=str(e))


# Global Kafka producer instance
kafka_producer = KafkaProducerClient()

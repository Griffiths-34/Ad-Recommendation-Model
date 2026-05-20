"""
Kafka consumer for processing events from event-collector.
Uses aiokafka for async consumption with batching.
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import structlog
from typing import List, Dict, Any

from app.core.config import settings
from app.models.events import Event, EventBatch

logger = structlog.get_logger()


class EventConsumer:
    """
    Async Kafka consumer with batch processing.
    
    Why async?
    - Handle 10,000+ events/second without blocking
    - Process multiple batches concurrently
    - Better resource utilization
    """
    
    def __init__(self):
        self.consumer: AIOKafkaConsumer = None
        self.running = False
        
    async def start(self) -> None:
        """
        Start Kafka consumer with retry logic.
        
        Configuration explained:
        - group_id: Multiple processors can share workload
        - auto_offset_reset: Start from earliest if no offset saved
        - enable_auto_commit: False = manual control over commits
        - max_poll_records: Batch size for efficiency
        """
        retries = 0
        max_retries = 5
        
        while retries < max_retries:
            try:
                self.consumer = AIOKafkaConsumer(
                    settings.KAFKA_TOPIC_EVENTS,
                    bootstrap_servers=settings.kafka_servers,
                    group_id=settings.KAFKA_GROUP_ID,
                    auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
                    enable_auto_commit=False,  # Manual commits for reliability
                    max_poll_records=settings.BATCH_SIZE,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                )
                
                await self.consumer.start()
                self.running = True
                
                logger.info(
                    "kafka_consumer_started",
                    topic=settings.KAFKA_TOPIC_EVENTS,
                    group_id=settings.KAFKA_GROUP_ID,
                    servers=settings.kafka_servers
                )
                break
                
            except KafkaError as e:
                retries += 1
                logger.warning(
                    "kafka_connection_failed",
                    error=str(e),
                    retry=retries,
                    max_retries=max_retries
                )
                if retries >= max_retries:
                    logger.error("kafka_connection_failed_max_retries")
                    raise
                await asyncio.sleep(2 ** retries)  # Exponential backoff
                
    async def stop(self) -> None:
        """Stop consumer gracefully."""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("kafka_consumer_stopped")
            
    async def consume_batch(self) -> List[Event]:
        """
        Consume a batch of events from Kafka.
        
        Returns:
            List of validated Event objects
            
        Why batching?
        - 10-100x faster than processing one-by-one
        - Reduces database write overhead
        - Better use of network bandwidth
        """
        events = []
        timeout_ms = settings.BATCH_TIMEOUT_SECONDS * 1000
        
        try:
            # Fetch batch of messages
            msg_batch = await self.consumer.getmany(
                timeout_ms=timeout_ms,
                max_records=settings.BATCH_SIZE
            )
            
            # Process messages from all partitions
            for topic_partition, messages in msg_batch.items():
                for message in messages:
                    try:
                        # Validate event with Pydantic
                        event_data = message.value
                        
                        # Handle both single events and batches
                        if isinstance(event_data, dict):
                            if "events" in event_data:
                                # Batch format from tracker SDK
                                for evt in event_data["events"]:
                                    event = Event(**evt)
                                    events.append(event)
                            else:
                                # Single event format
                                event = Event(**event_data)
                                events.append(event)
                                
                    except Exception as e:
                        logger.error(
                            "event_validation_failed",
                            error=str(e),
                            offset=message.offset,
                            partition=message.partition
                        )
                        # Continue processing other events
                        continue
            
            if events:
                logger.info(
                    "batch_consumed",
                    event_count=len(events),
                    batch_size=settings.BATCH_SIZE
                )
                
        except Exception as e:
            logger.error("batch_consumption_failed", error=str(e))
            
        return events
        
    async def commit(self) -> None:
        """
        Commit offset to Kafka after successful processing.
        
        Why manual commits?
        - Ensures events are processed before marking as consumed
        - Prevents data loss if processor crashes
        - Enables exactly-once processing semantics
        """
        try:
            await self.consumer.commit()
            logger.debug("offsets_committed")
        except Exception as e:
            logger.error("commit_failed", error=str(e))


# Global consumer instance
consumer = EventConsumer()

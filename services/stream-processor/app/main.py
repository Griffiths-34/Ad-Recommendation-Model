"""
Main application entry point for Stream Processor.
Orchestrates Kafka consumption and event processing.
"""

import asyncio
import signal
import structlog
from typing import Optional

from app.core.config import settings
from app.core.database import db
from app.kafka.consumer import consumer
from app.processors.event_processor import processor
from app.ml.recommender import recommender

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class StreamProcessor:
    """
    Main stream processing application.
    
    Architecture:
    1. Consume events from Kafka (batched)
    2. Process and store in PostgreSQL
    3. Update ML feature store
    4. Commit Kafka offsets (exactly-once semantics)
    """
    
    def __init__(self):
        self.running = False
        self.tasks: list[asyncio.Task] = []
        
    async def start(self) -> None:
        """
        Start all components:
        - Database connection pool
        - Kafka consumer
        - Processing workers
        - ML model updater
        """
        logger.info("stream_processor_starting")
        
        try:
            # 1. Connect to database
            await db.connect()
            
            # 2. Start Kafka consumer
            await consumer.start()
            
            # 3. Load ML features
            await recommender.load_features()
            
            # 4. Start processing workers
            self.running = True
            for i in range(settings.WORKER_COUNT):
                task = asyncio.create_task(
                    self._process_events_worker(worker_id=i)
                )
                self.tasks.append(task)
            
            # 5. Start periodic ML model refresh
            ml_task = asyncio.create_task(self._refresh_ml_model())
            self.tasks.append(ml_task)
            
            logger.info(
                "stream_processor_started",
                workers=settings.WORKER_COUNT,
                batch_size=settings.BATCH_SIZE
            )
            
            # Keep running until interrupted
            await self._wait_for_shutdown()
            
        except Exception as e:
            logger.error("stream_processor_failed", error=str(e))
            raise
        finally:
            await self.stop()
            
    async def stop(self) -> None:
        """Gracefully stop all components."""
        logger.info("stream_processor_stopping")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to finish
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop Kafka consumer
        await consumer.stop()
        
        # Close database connections
        await db.disconnect()
        
        logger.info("stream_processor_stopped")
        
    async def _process_events_worker(self, worker_id: int) -> None:
        """
        Worker that processes events in a loop.
        
        Flow:
        1. Consume batch from Kafka
        2. Process batch (validate, transform, store)
        3. Commit Kafka offset
        4. Repeat
        
        Args:
            worker_id: Worker identifier for logging
        """
        logger.info("worker_started", worker_id=worker_id)
        
        while self.running:
            try:
                # 1. Consume batch of events
                events = await consumer.consume_batch()
                
                if not events:
                    # No events, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                # 2. Process events
                await processor.process_batch(events)
                
                # 3. Commit offset (marks events as processed)
                await consumer.commit()
                
                logger.info(
                    "batch_processed_successfully",
                    worker_id=worker_id,
                    event_count=len(events)
                )
                
            except asyncio.CancelledError:
                logger.info("worker_cancelled", worker_id=worker_id)
                break
            except Exception as e:
                logger.error(
                    "worker_error",
                    worker_id=worker_id,
                    error=str(e)
                )
                # Wait before retrying to avoid tight error loop
                await asyncio.sleep(5)
                
        logger.info("worker_stopped", worker_id=worker_id)
        
    async def _refresh_ml_model(self) -> None:
        """
        Periodically refresh ML model with latest data.
        
        Why periodic refresh?
        - User preferences change over time
        - New products added
        - Seasonal trends
        - Keep model fresh without full retraining
        """
        while self.running:
            try:
                await asyncio.sleep(settings.FEATURE_STORE_UPDATE_INTERVAL)
                
                logger.info("ml_model_refresh_started")
                await recommender.load_features()
                logger.info("ml_model_refresh_completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("ml_model_refresh_failed", error=str(e))
                
    async def _wait_for_shutdown(self) -> None:
        """Wait for shutdown signal (Ctrl+C or SIGTERM)."""
        shutdown_event = asyncio.Event()
        
        def signal_handler(sig, frame):
            logger.info("shutdown_signal_received", signal=sig)
            shutdown_event.set()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Wait for signal
        await shutdown_event.wait()


async def main():
    """Application entry point."""
    app = StreamProcessor()
    await app.start()


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())

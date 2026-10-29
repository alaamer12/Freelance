# Service ID: DSE75 - Real-time Data Streaming Engine
# محرك تدفق البيانات في الوقت الفعلي المتقدم

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import websockets
import aiohttp
import pandas as pd
import numpy as np

# Kafka integration
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka not available. Install with: pip install kafka-python")

# Redis for caching and pub/sub
try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Install with: pip install redis")

logger = logging.getLogger(__name__)

@dataclass
class StreamConfig:
    """
    Stream configuration
    تكوين التدفق
    """
    stream_name: str
    source_type: str  # kafka, websocket, api, file, database
    source_config: Dict[str, Any]
    processing_config: Dict[str, Any] = None
    output_config: Dict[str, Any] = None
    batch_size: int = 100
    batch_timeout: float = 5.0
    max_retries: int = 3
    error_handling: str = "continue"  # continue, stop, retry

@dataclass
class StreamMessage:
    """
    Stream message container
    حاوي رسالة التدفق
    """
    stream_name: str
    message_id: str
    timestamp: str
    data: Any
    metadata: Dict[str, Any] = None
    processing_status: str = "pending"

@dataclass
class StreamMetrics:
    """
    Stream processing metrics
    مقاييس معالجة التدفق
    """
    stream_name: str
    messages_processed: int = 0
    messages_failed: int = 0
    processing_rate: float = 0.0
    average_latency: float = 0.0
    last_processed: str = None
    uptime: float = 0.0

class AdvancedStreamingDataEngine:
    """
    Advanced real-time data streaming engine
    محرك تدفق البيانات في الوقت الفعلي المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.streams_path = workspace_path / "data_streams"
        self.logs_path = workspace_path / "stream_logs"
        self.checkpoints_path = workspace_path / "stream_checkpoints"
        
        for path in [self.streams_path, self.logs_path, self.checkpoints_path]:
            path.mkdir(exist_ok=True)
        
        self.active_streams: Dict[str, StreamConfig] = {}
        self.stream_processors: Dict[str, Any] = {}
        self.stream_metrics: Dict[str, StreamMetrics] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize connections
        self.redis_client = None
        self.kafka_producer = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {str(e)}")
                self.redis_client = None
    
    async def create_stream(self, config: StreamConfig) -> bool:
        """
        Create and configure a data stream
        إنشاء وتكوين تدفق البيانات
        """
        try:
            # Validate configuration
            self._validate_stream_config(config)
            
            # Initialize stream processor
            if config.source_type == "kafka" and KAFKA_AVAILABLE:
                processor = await self._create_kafka_stream(config)
            elif config.source_type == "websocket":
                processor = await self._create_websocket_stream(config)
            elif config.source_type == "api":
                processor = await self._create_api_stream(config)
            elif config.source_type == "file":
                processor = await self._create_file_stream(config)
            else:
                raise ValueError(f"Unsupported source type: {config.source_type}")
            
            # Store configuration and processor
            self.active_streams[config.stream_name] = config
            self.stream_processors[config.stream_name] = processor
            self.stream_metrics[config.stream_name] = StreamMetrics(stream_name=config.stream_name)
            
            logger.info(f"Stream created successfully: {config.stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create stream {config.stream_name}: {str(e)}")
            return False
    
    async def start_stream(self, stream_name: str) -> bool:
        """
        Start processing a data stream
        بدء معالجة تدفق البيانات
        """
        try:
            if stream_name not in self.active_streams:
                raise ValueError(f"Stream not found: {stream_name}")
            
            config = self.active_streams[stream_name]
            processor = self.stream_processors[stream_name]
            
            # Start processing task
            task = asyncio.create_task(self._process_stream(config, processor))
            self.stream_processors[f"{stream_name}_task"] = task
            
            # Update metrics
            self.stream_metrics[stream_name].last_processed = datetime.utcnow().isoformat()
            
            logger.info(f"Stream started: {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream {stream_name}: {str(e)}")
            return False
    
    async def stop_stream(self, stream_name: str) -> bool:
        """
        Stop processing a data stream
        إيقاف معالجة تدفق البيانات
        """
        try:
            task_name = f"{stream_name}_task"
            if task_name in self.stream_processors:
                task = self.stream_processors[task_name]
                task.cancel()
                del self.stream_processors[task_name]
            
            logger.info(f"Stream stopped: {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop stream {stream_name}: {str(e)}")
            return False
    
    async def _create_kafka_stream(self, config: StreamConfig) -> Any:
        """Create Kafka stream processor"""
        kafka_config = config.source_config
        
        consumer = KafkaConsumer(
            kafka_config['topic'],
            bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
            group_id=kafka_config.get('group_id', f"{config.stream_name}_group"),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
            auto_offset_reset=kafka_config.get('auto_offset_reset', 'latest')
        )
        
        return consumer
    
    async def _create_websocket_stream(self, config: StreamConfig) -> Any:
        """Create WebSocket stream processor"""
        ws_config = config.source_config
        uri = ws_config['uri']
        
        async def websocket_generator():
            try:
                async with websockets.connect(uri) as websocket:
                    async for message in websocket:
                        yield json.loads(message)
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                yield None
        
        return websocket_generator()
    
    async def _create_api_stream(self, config: StreamConfig) -> Any:
        """Create API polling stream processor"""
        api_config = config.source_config
        
        async def api_generator():
            session = aiohttp.ClientSession()
            try:
                while True:
                    try:
                        async with session.get(
                            api_config['url'],
                            headers=api_config.get('headers', {}),
                            params=api_config.get('params', {})
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                yield data
                            else:
                                logger.warning(f"API request failed: {response.status}")
                        
                        await asyncio.sleep(api_config.get('poll_interval', 10))
                        
                    except Exception as e:
                        logger.error(f"API polling error: {str(e)}")
                        await asyncio.sleep(5)
                        
            finally:
                await session.close()
        
        return api_generator()
    
    async def _create_file_stream(self, config: StreamConfig) -> Any:
        """Create file monitoring stream processor"""
        file_config = config.source_config
        file_path = Path(file_config['file_path'])
        
        async def file_generator():
            last_position = 0
            
            while True:
                try:
                    if file_path.exists():
                        current_size = file_path.stat().st_size
                        
                        if current_size > last_position:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                f.seek(last_position)
                                new_lines = f.readlines()
                                last_position = f.tell()
                                
                                for line in new_lines:
                                    line = line.strip()
                                    if line:
                                        try:
                                            yield json.loads(line)
                                        except json.JSONDecodeError:
                                            yield {'raw_data': line}
                    
                    await asyncio.sleep(file_config.get('poll_interval', 1))
                    
                except Exception as e:
                    logger.error(f"File monitoring error: {str(e)}")
                    await asyncio.sleep(5)
        
        return file_generator()
    
    async def _process_stream(self, config: StreamConfig, processor: Any):
        """
        Process stream messages
        معالجة رسائل التدفق
        """
        stream_name = config.stream_name
        metrics = self.stream_metrics[stream_name]
        start_time = time.time()
        
        batch = []
        last_batch_time = time.time()
        
        try:
            if config.source_type == "kafka":
                # Kafka processing
                for message in processor:
                    if message.value:
                        stream_message = StreamMessage(
                            stream_name=stream_name,
                            message_id=f"{message.partition}_{message.offset}",
                            timestamp=datetime.utcnow().isoformat(),
                            data=message.value,
                            metadata={
                                'partition': message.partition,
                                'offset': message.offset,
                                'topic': message.topic
                            }
                        )
                        
                        batch.append(stream_message)
                        
                        # Process batch if size or timeout reached
                        if (len(batch) >= config.batch_size or 
                            time.time() - last_batch_time >= config.batch_timeout):
                            await self._process_batch(config, batch, metrics)
                            batch = []
                            last_batch_time = time.time()
            
            else:
                # Async generator processing (WebSocket, API, File)
                async for data in processor:
                    if data:
                        stream_message = StreamMessage(
                            stream_name=stream_name,
                            message_id=f"{int(time.time() * 1000000)}",
                            timestamp=datetime.utcnow().isoformat(),
                            data=data
                        )
                        
                        batch.append(stream_message)
                        
                        # Process batch if size or timeout reached
                        if (len(batch) >= config.batch_size or 
                            time.time() - last_batch_time >= config.batch_timeout):
                            await self._process_batch(config, batch, metrics)
                            batch = []
                            last_batch_time = time.time()
        
        except asyncio.CancelledError:
            logger.info(f"Stream processing cancelled: {stream_name}")
        except Exception as e:
            logger.error(f"Stream processing error for {stream_name}: {str(e)}")
        finally:
            # Process remaining batch
            if batch:
                await self._process_batch(config, batch, metrics)
            
            # Update final metrics
            metrics.uptime = time.time() - start_time
    
    async def _process_batch(self, config: StreamConfig, batch: List[StreamMessage], metrics: StreamMetrics):
        """
        Process a batch of stream messages
        معالجة دفعة من رسائل التدفق
        """
        batch_start = time.time()
        
        try:
            # Apply processing transformations
            if config.processing_config:
                processed_batch = await self._apply_stream_processing(batch, config.processing_config)
            else:
                processed_batch = batch
            
            # Send to output destinations
            if config.output_config:
                await self._send_to_outputs(processed_batch, config.output_config)
            
            # Call custom message handlers
            stream_name = config.stream_name
            if stream_name in self.message_handlers:
                await self.message_handlers[stream_name](processed_batch)
            
            # Update metrics
            batch_time = time.time() - batch_start
            metrics.messages_processed += len(batch)
            metrics.processing_rate = metrics.messages_processed / (time.time() - batch_start + 0.001)
            metrics.average_latency = (metrics.average_latency + batch_time) / 2
            metrics.last_processed = datetime.utcnow().isoformat()
            
            # Cache processed data if Redis available
            if self.redis_client:
                await self._cache_batch_data(stream_name, processed_batch)
            
            logger.debug(f"Processed batch of {len(batch)} messages for stream {stream_name}")
            
        except Exception as e:
            metrics.messages_failed += len(batch)
            logger.error(f"Batch processing failed for stream {config.stream_name}: {str(e)}")
            
            if config.error_handling == "stop":
                raise
    
    async def _apply_stream_processing(self, batch: List[StreamMessage], processing_config: Dict[str, Any]) -> List[StreamMessage]:
        """
        Apply processing transformations to stream data
        تطبيق تحويلات المعالجة على بيانات التدفق
        """
        processed_batch = []
        
        for message in batch:
            try:
                processed_data = message.data
                
                # Apply filters
                if 'filters' in processing_config:
                    if not self._apply_filters(processed_data, processing_config['filters']):
                        continue
                
                # Apply transformations
                if 'transformations' in processing_config:
                    processed_data = self._apply_transformations(processed_data, processing_config['transformations'])
                
                # Apply enrichment
                if 'enrichment' in processing_config:
                    processed_data = await self._apply_enrichment(processed_data, processing_config['enrichment'])
                
                # Create processed message
                processed_message = StreamMessage(
                    stream_name=message.stream_name,
                    message_id=message.message_id,
                    timestamp=message.timestamp,
                    data=processed_data,
                    metadata=message.metadata,
                    processing_status="processed"
                )
                
                processed_batch.append(processed_message)
                
            except Exception as e:
                logger.error(f"Message processing failed: {str(e)}")
                message.processing_status = "failed"
                processed_batch.append(message)
        
        return processed_batch
    
    def _apply_filters(self, data: Any, filters: List[Dict[str, Any]]) -> bool:
        """Apply filters to determine if message should be processed"""
        for filter_config in filters:
            filter_type = filter_config.get('type')
            
            if filter_type == 'field_exists':
                field = filter_config['field']
                if isinstance(data, dict) and field not in data:
                    return False
            
            elif filter_type == 'field_value':
                field = filter_config['field']
                expected_value = filter_config['value']
                operator = filter_config.get('operator', 'equals')
                
                if isinstance(data, dict) and field in data:
                    actual_value = data[field]
                    
                    if operator == 'equals' and actual_value != expected_value:
                        return False
                    elif operator == 'not_equals' and actual_value == expected_value:
                        return False
                    elif operator == 'greater_than' and actual_value <= expected_value:
                        return False
                    elif operator == 'less_than' and actual_value >= expected_value:
                        return False
        
        return True
    
    def _apply_transformations(self, data: Any, transformations: List[Dict[str, Any]]) -> Any:
        """Apply transformations to message data"""
        transformed_data = data
        
        for transform_config in transformations:
            transform_type = transform_config.get('type')
            
            if transform_type == 'add_field':
                if isinstance(transformed_data, dict):
                    field_name = transform_config['field']
                    field_value = transform_config['value']
                    transformed_data[field_name] = field_value
            
            elif transform_type == 'remove_field':
                if isinstance(transformed_data, dict):
                    field_name = transform_config['field']
                    transformed_data.pop(field_name, None)
            
            elif transform_type == 'rename_field':
                if isinstance(transformed_data, dict):
                    old_name = transform_config['old_name']
                    new_name = transform_config['new_name']
                    if old_name in transformed_data:
                        transformed_data[new_name] = transformed_data.pop(old_name)
            
            elif transform_type == 'format_timestamp':
                if isinstance(transformed_data, dict):
                    field_name = transform_config['field']
                    if field_name in transformed_data:
                        timestamp_value = transformed_data[field_name]
                        # Convert to ISO format
                        if isinstance(timestamp_value, (int, float)):
                            transformed_data[field_name] = datetime.fromtimestamp(timestamp_value).isoformat()
        
        return transformed_data
    
    async def _apply_enrichment(self, data: Any, enrichment_config: Dict[str, Any]) -> Any:
        """Apply data enrichment"""
        enriched_data = data.copy() if isinstance(data, dict) else data
        
        enrichment_type = enrichment_config.get('type')
        
        if enrichment_type == 'lookup' and self.redis_client:
            # Redis lookup enrichment
            lookup_key = enrichment_config['key']
            target_field = enrichment_config['target_field']
            
            if isinstance(enriched_data, dict) and lookup_key in enriched_data:
                lookup_value = self.redis_client.get(f"lookup:{enriched_data[lookup_key]}")
                if lookup_value:
                    enriched_data[target_field] = json.loads(lookup_value)
        
        elif enrichment_type == 'add_metadata':
            # Add processing metadata
            if isinstance(enriched_data, dict):
                enriched_data['_processing_timestamp'] = datetime.utcnow().isoformat()
                enriched_data['_enrichment_applied'] = True
        
        return enriched_data
    
    async def _send_to_outputs(self, batch: List[StreamMessage], output_config: Dict[str, Any]):
        """
        Send processed messages to output destinations
        إرسال الرسائل المعالجة إلى وجهات الإخراج
        """
        outputs = output_config.get('destinations', [])
        
        for output in outputs:
            output_type = output.get('type')
            
            try:
                if output_type == 'kafka' and KAFKA_AVAILABLE:
                    await self._send_to_kafka(batch, output)
                elif output_type == 'redis' and self.redis_client:
                    await self._send_to_redis(batch, output)
                elif output_type == 'file':
                    await self._send_to_file(batch, output)
                elif output_type == 'webhook':
                    await self._send_to_webhook(batch, output)
                
            except Exception as e:
                logger.error(f"Failed to send to {output_type}: {str(e)}")
    
    async def _send_to_kafka(self, batch: List[StreamMessage], output_config: Dict[str, Any]):
        """Send messages to Kafka topic"""
        if not self.kafka_producer:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=output_config.get('bootstrap_servers', ['localhost:9092']),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        
        topic = output_config['topic']
        
        for message in batch:
            self.kafka_producer.send(topic, asdict(message))
        
        self.kafka_producer.flush()
    
    async def _send_to_redis(self, batch: List[StreamMessage], output_config: Dict[str, Any]):
        """Send messages to Redis"""
        operation = output_config.get('operation', 'publish')
        
        if operation == 'publish':
            channel = output_config['channel']
            for message in batch:
                self.redis_client.publish(channel, json.dumps(asdict(message)))
        
        elif operation == 'set':
            key_pattern = output_config['key_pattern']
            for message in batch:
                key = key_pattern.format(message_id=message.message_id, stream_name=message.stream_name)
                self.redis_client.set(key, json.dumps(asdict(message)))
    
    async def _send_to_file(self, batch: List[StreamMessage], output_config: Dict[str, Any]):
        """Send messages to file"""
        file_path = Path(output_config['file_path'])
        
        with open(file_path, 'a', encoding='utf-8') as f:
            for message in batch:
                f.write(json.dumps(asdict(message)) + '\n')
    
    async def _send_to_webhook(self, batch: List[StreamMessage], output_config: Dict[str, Any]):
        """Send messages to webhook"""
        url = output_config['url']
        headers = output_config.get('headers', {'Content-Type': 'application/json'})
        
        async with aiohttp.ClientSession() as session:
            payload = [asdict(message) for message in batch]
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Webhook request failed: {response.status}")
    
    async def _cache_batch_data(self, stream_name: str, batch: List[StreamMessage]):
        """Cache batch data in Redis for analytics"""
        if not self.redis_client:
            return
        
        # Store recent messages for analytics
        for message in batch[-10:]:  # Keep last 10 messages
            key = f"stream:{stream_name}:recent:{message.message_id}"
            self.redis_client.setex(key, 3600, json.dumps(asdict(message)))  # 1 hour TTL
    
    def register_message_handler(self, stream_name: str, handler: Callable):
        """
        Register custom message handler for a stream
        تسجيل معالج رسائل مخصص للتدفق
        """
        self.message_handlers[stream_name] = handler
        logger.info(f"Message handler registered for stream: {stream_name}")
    
    def _validate_stream_config(self, config: StreamConfig):
        """Validate stream configuration"""
        if not config.stream_name:
            raise ValueError("Stream name is required")
        
        if not config.source_type:
            raise ValueError("Source type is required")
        
        if not config.source_config:
            raise ValueError("Source configuration is required")
    
    def get_stream_metrics(self, stream_name: str = None) -> Dict[str, Any]:
        """
        Get stream processing metrics
        الحصول على مقاييس معالجة التدفق
        """
        if stream_name:
            if stream_name in self.stream_metrics:
                return asdict(self.stream_metrics[stream_name])
            else:
                return {}
        
        # Return all metrics
        return {
            name: asdict(metrics) 
            for name, metrics in self.stream_metrics.items()
        }
    
    def get_streaming_statistics(self) -> Dict[str, Any]:
        """
        Get overall streaming engine statistics
        الحصول على إحصائيات محرك التدفق الشاملة
        """
        total_processed = sum(m.messages_processed for m in self.stream_metrics.values())
        total_failed = sum(m.messages_failed for m in self.stream_metrics.values())
        
        active_streams = len([s for s in self.active_streams.keys() 
                            if f"{s}_task" in self.stream_processors])
        
        return {
            'total_streams': len(self.active_streams),
            'active_streams': active_streams,
            'total_messages_processed': total_processed,
            'total_messages_failed': total_failed,
            'success_rate': (total_processed / (total_processed + total_failed) * 100) if (total_processed + total_failed) > 0 else 0,
            'average_processing_rate': np.mean([m.processing_rate for m in self.stream_metrics.values()]) if self.stream_metrics else 0,
            'redis_available': self.redis_client is not None,
            'kafka_available': KAFKA_AVAILABLE,
            'generated_at': datetime.utcnow().isoformat()
        }

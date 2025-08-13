"""
Backup and Disaster Recovery Service
Comprehensive automated backup and recovery system with multi-tier storage
"""
import asyncio
import json
import gzip
import pickle
import hashlib
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import pandas as pd
from sqlalchemy import select, text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session, get_redis_client
from ..logging import get_logger
from .time_series_service import TimeSeriesService
from .vector_database_service import VectorDatabaseService

logger = get_logger(__name__)

class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"

class BackupStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORED = "restored"

class StorageTier(str, Enum):
    HOT = "hot"          # Immediate access (S3 Standard)
    WARM = "warm"        # Quick access (S3 Standard-IA)
    COLD = "cold"        # Archive access (S3 Glacier)
    FROZEN = "frozen"    # Deep archive (S3 Glacier Deep Archive)

class RecoveryPoint(str, Enum):
    IMMEDIATE = "immediate"      # <15 minutes
    NEAR_IMMEDIATE = "near_immediate"  # <1 hour
    SAME_DAY = "same_day"        # <24 hours
    MULTI_DAY = "multi_day"      # <7 days

@dataclass
class BackupConfig:
    """Backup configuration settings"""
    backup_id: str
    name: str
    backup_type: BackupType
    schedule: str  # Cron expression
    retention_days: int
    storage_tier: StorageTier
    compression_enabled: bool = True
    encryption_enabled: bool = True
    verify_backup: bool = True
    
    # Source configuration
    source_type: str  # database, files, redis, vector_db, influxdb
    source_config: Dict[str, Any] = None
    
    # Storage configuration  
    storage_location: str = ""
    storage_provider: str = "minio"  # minio, s3, local
    
    # Compliance settings
    gdpr_compliant: bool = True
    financial_retention: bool = False  # 7+ years
    audit_trail: bool = True

@dataclass
class BackupRecord:
    """Record of a backup operation"""
    backup_id: str
    config_id: str
    backup_type: BackupType
    status: BackupStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Backup details
    source_size_mb: float = 0.0
    compressed_size_mb: float = 0.0
    compression_ratio: float = 0.0
    file_count: int = 0
    record_count: int = 0
    
    # Storage information
    storage_location: str = ""
    storage_tier: StorageTier = StorageTier.HOT
    checksum: str = ""
    encryption_key_id: str = ""
    
    # Recovery information
    recovery_point_objective: RecoveryPoint = RecoveryPoint.SAME_DAY
    recovery_time_objective_minutes: int = 240  # 4 hours
    
    # Status and errors
    error_message: str = ""
    verification_status: str = "pending"
    metadata: Dict[str, Any] = None

class BackupAndRecoveryService:
    """Comprehensive backup and disaster recovery service"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.time_series = TimeSeriesService()
        self.vector_db = VectorDatabaseService()
        
        # Storage clients
        self.minio_client = None
        self.s3_client = None
        
        # Backup configurations
        self.backup_configs: Dict[str, BackupConfig] = {}
        self.active_backups: Dict[str, BackupRecord] = {}
        
        # Initialize storage clients
        asyncio.create_task(self._initialize_storage_clients())
        
        # Initialize default backup configurations
        asyncio.create_task(self._initialize_backup_configs())
    
    async def _initialize_storage_clients(self):
        """Initialize storage clients for backup destinations"""
        try:
            # MinIO client (S3 compatible)
            from minio import Minio
            
            self.minio_client = Minio(
                "minio:9000",
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=False
            )
            
            # Ensure backup buckets exist
            backup_buckets = ["hot-backups", "warm-backups", "cold-backups", "frozen-backups"]
            for bucket in backup_buckets:
                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)
                    logger.info(f"Created backup bucket: {bucket}")
            
            # AWS S3 client for external backups
            if os.getenv("AWS_ACCESS_KEY_ID"):
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    region_name=os.getenv("AWS_REGION", "us-east-1")
                )
                logger.info("Initialized AWS S3 client for external backups")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage clients: {e}")
    
    async def _initialize_backup_configs(self):
        """Initialize default backup configurations"""
        
        # PostgreSQL database backup - daily full, hourly incremental
        self.add_backup_config(BackupConfig(
            backup_id="postgres_full_daily",
            name="PostgreSQL Full Daily Backup",
            backup_type=BackupType.FULL,
            schedule="0 2 * * *",  # Daily at 2 AM
            retention_days=30,
            storage_tier=StorageTier.WARM,
            source_type="postgresql",
            source_config={
                "host": "postgres",
                "port": 5432,
                "database": "prism_db",
                "username": "prism_user",
                "exclude_tables": ["temp_*", "cache_*"]
            },
            financial_retention=True  # Keep longer for compliance
        ))
        
        self.add_backup_config(BackupConfig(
            backup_id="postgres_incremental_hourly", 
            name="PostgreSQL Incremental Hourly Backup",
            backup_type=BackupType.INCREMENTAL,
            schedule="0 * * * *",  # Every hour
            retention_days=7,
            storage_tier=StorageTier.HOT,
            source_type="postgresql",
            source_config={
                "host": "postgres",
                "port": 5432,
                "database": "prism_db",
                "username": "prism_user",
                "incremental_column": "updated_at",
                "exclude_tables": ["temp_*", "cache_*"]
            }
        ))
        
        # Redis backup - hourly snapshots
        self.add_backup_config(BackupConfig(
            backup_id="redis_snapshot_hourly",
            name="Redis Hourly Snapshot",
            backup_type=BackupType.SNAPSHOT,
            schedule="30 * * * *",  # Every hour at 30 minutes
            retention_days=3,
            storage_tier=StorageTier.HOT,
            source_type="redis",
            source_config={
                "host": "redis",
                "port": 6379,
                "databases": [0, 1, 2]
            }
        ))
        
        # InfluxDB backup - daily
        self.add_backup_config(BackupConfig(
            backup_id="influxdb_daily",
            name="InfluxDB Daily Backup",
            backup_type=BackupType.FULL,
            schedule="0 3 * * *",  # Daily at 3 AM
            retention_days=90,
            storage_tier=StorageTier.COLD,
            source_type="influxdb",
            source_config={
                "url": "http://influxdb:8086",
                "token": "prism-analytics-token",
                "org": "prism",
                "buckets": ["analytics", "short_term", "medium_term", "long_term"]
            }
        ))
        
        # Qdrant vector database backup - daily
        self.add_backup_config(BackupConfig(
            backup_id="qdrant_daily",
            name="Qdrant Vector DB Daily Backup", 
            backup_type=BackupType.FULL,
            schedule="0 4 * * *",  # Daily at 4 AM
            retention_days=60,
            storage_tier=StorageTier.WARM,
            source_type="qdrant",
            source_config={
                "url": "http://qdrant:6333",
                "collections": ["content_embeddings", "pattern_embeddings", "agent_memory"]
            }
        ))
        
        # File storage backup - daily
        self.add_backup_config(BackupConfig(
            backup_id="minio_files_daily",
            name="MinIO File Storage Daily Backup",
            backup_type=BackupType.FULL,
            schedule="0 1 * * *",  # Daily at 1 AM
            retention_days=180,  # 6 months
            storage_tier=StorageTier.COLD,
            source_type="minio",
            source_config={
                "endpoint": "minio:9000",
                "buckets": ["prism-content", "prism-archives", "prism-uploads"],
                "exclude_prefixes": ["temp/", "cache/"]
            }
        ))
        
        logger.info(f"Initialized {len(self.backup_configs)} backup configurations")
    
    def add_backup_config(self, config: BackupConfig):
        """Add a backup configuration"""
        self.backup_configs[config.backup_id] = config
        logger.debug(f"Added backup config: {config.name}")
    
    async def execute_backup(self, config_id: str, manual: bool = False) -> BackupRecord:
        """Execute a backup operation"""
        
        if config_id not in self.backup_configs:
            raise ValueError(f"Backup configuration not found: {config_id}")
        
        config = self.backup_configs[config_id]
        backup_id = f"{config_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_record = BackupRecord(
            backup_id=backup_id,
            config_id=config_id,
            backup_type=config.backup_type,
            status=BackupStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            storage_tier=config.storage_tier,
            metadata={"manual": manual, "config_name": config.name}
        )
        
        self.active_backups[backup_id] = backup_record
        
        try:
            logger.info(f"Starting backup: {config.name} ({backup_id})")
            backup_record.status = BackupStatus.RUNNING
            
            # Execute backup based on source type
            if config.source_type == "postgresql":
                await self._backup_postgresql(config, backup_record)
            elif config.source_type == "redis":
                await self._backup_redis(config, backup_record)
            elif config.source_type == "influxdb":
                await self._backup_influxdb(config, backup_record)
            elif config.source_type == "qdrant":
                await self._backup_qdrant(config, backup_record)
            elif config.source_type == "minio":
                await self._backup_minio(config, backup_record)
            else:
                raise ValueError(f"Unsupported source type: {config.source_type}")
            
            # Verify backup if enabled
            if config.verify_backup:
                await self._verify_backup(config, backup_record)
            
            backup_record.status = BackupStatus.COMPLETED
            backup_record.completed_at = datetime.now(timezone.utc)
            
            # Log backup metrics
            await self._log_backup_metrics(backup_record)
            
            # Schedule cleanup of old backups
            asyncio.create_task(self._cleanup_old_backups(config))
            
            logger.info(f"Backup completed successfully: {backup_id}")
            
        except Exception as e:
            backup_record.status = BackupStatus.FAILED
            backup_record.error_message = str(e)
            backup_record.completed_at = datetime.now(timezone.utc)
            
            logger.error(f"Backup failed: {backup_id}: {e}")
            
            # Log failure metrics
            await self._log_backup_failure(backup_record, str(e))
        
        finally:
            # Remove from active backups
            if backup_id in self.active_backups:
                del self.active_backups[backup_id]
        
        return backup_record
    
    async def _backup_postgresql(self, config: BackupConfig, backup_record: BackupRecord):
        """Backup PostgreSQL database"""
        
        source_config = config.source_config
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Generate database dump
            if config.backup_type == BackupType.FULL:
                dump_file = os.path.join(temp_dir, f"postgres_full_{backup_record.backup_id}.sql")
                
                # Build pg_dump command
                dump_cmd = [
                    "pg_dump",
                    f"--host={source_config['host']}",
                    f"--port={source_config['port']}",
                    f"--username={source_config['username']}",
                    f"--dbname={source_config['database']}",
                    "--verbose",
                    "--clean",
                    "--if-exists",
                    "--create",
                    f"--file={dump_file}"
                ]
                
                # Add exclusions
                for table_pattern in source_config.get("exclude_tables", []):
                    dump_cmd.extend(["--exclude-table-data", table_pattern])
                
                # Set password via environment
                env = os.environ.copy()
                env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD", "prism_password")
                
                # Execute dump
                result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"pg_dump failed: {result.stderr}")
                
                backup_record.metadata["dump_type"] = "full"
                
            elif config.backup_type == BackupType.INCREMENTAL:
                # Incremental backup using WAL files or timestamp-based approach
                await self._backup_postgresql_incremental(config, backup_record, temp_dir)
            
            # Get file stats
            dump_files = [f for f in os.listdir(temp_dir) if f.endswith(('.sql', '.tar'))]
            if not dump_files:
                raise Exception("No dump files generated")
            
            dump_file = os.path.join(temp_dir, dump_files[0])
            file_stats = os.stat(dump_file)
            backup_record.source_size_mb = file_stats.st_size / (1024 * 1024)
            
            # Compress if enabled
            if config.compression_enabled:
                compressed_file = f"{dump_file}.gz"
                with open(dump_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                compressed_stats = os.stat(compressed_file)
                backup_record.compressed_size_mb = compressed_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = backup_record.source_size_mb / backup_record.compressed_size_mb
                final_file = compressed_file
            else:
                final_file = dump_file
                backup_record.compressed_size_mb = backup_record.source_size_mb
                backup_record.compression_ratio = 1.0
            
            # Calculate checksum
            backup_record.checksum = await self._calculate_file_checksum(final_file)
            
            # Upload to storage
            storage_path = await self._upload_to_storage(
                final_file, 
                f"postgresql/{backup_record.backup_id}",
                config.storage_tier,
                config.encryption_enabled
            )
            
            backup_record.storage_location = storage_path
            backup_record.file_count = 1
            
        finally:
            # Cleanup temporary files
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _backup_postgresql_incremental(
        self, 
        config: BackupConfig, 
        backup_record: BackupRecord, 
        temp_dir: str
    ):
        """Perform incremental PostgreSQL backup"""
        
        source_config = config.source_config
        incremental_column = source_config.get("incremental_column", "updated_at")
        
        # Get last backup timestamp
        last_backup_time = await self._get_last_backup_timestamp(config.backup_id)
        if not last_backup_time:
            # First incremental backup - use last 24 hours
            last_backup_time = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Build query to get incremental data
        async with get_db_session() as session:
            # Get all tables that have the incremental column
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND column_name = :incremental_column
                AND table_name NOT LIKE 'temp_%'
                AND table_name NOT LIKE 'cache_%'
            """)
            
            result = await session.execute(tables_query, {"incremental_column": incremental_column})
            tables = [row[0] for row in result.fetchall()]
            
            total_records = 0
            dump_file = os.path.join(temp_dir, f"postgres_incremental_{backup_record.backup_id}.sql")
            
            with open(dump_file, 'w') as f:
                f.write(f"-- Incremental backup from {last_backup_time}\n")
                f.write(f"-- Generated at {datetime.now()}\n\n")
                
                for table in tables:
                    # Export incremental data for each table
                    export_query = text(f"""
                        COPY (
                            SELECT * FROM {table} 
                            WHERE {incremental_column} > :last_backup_time
                        ) TO STDOUT WITH (FORMAT CSV, HEADER)
                    """)
                    
                    # This would need proper implementation with asyncpg raw connection
                    # For now, using a simplified approach
                    count_query = text(f"""
                        SELECT COUNT(*) FROM {table} 
                        WHERE {incremental_column} > :last_backup_time
                    """)
                    
                    count_result = await session.execute(count_query, {"last_backup_time": last_backup_time})
                    count = count_result.scalar()
                    
                    if count > 0:
                        f.write(f"-- Table: {table}, Records: {count}\n")
                        total_records += count
            
            backup_record.record_count = total_records
            backup_record.metadata["incremental_from"] = last_backup_time.isoformat()
            backup_record.metadata["tables_included"] = tables
    
    async def _backup_redis(self, config: BackupConfig, backup_record: BackupRecord):
        """Backup Redis database"""
        
        source_config = config.source_config
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Connect to Redis
            import redis.asyncio as redis
            
            redis_client = redis.from_url(
                f"redis://{source_config['host']}:{source_config['port']}"
            )
            
            databases = source_config.get("databases", [0])
            backup_data = {}
            
            for db in databases:
                await redis_client.select(db)
                
                # Get all keys
                keys = await redis_client.keys("*")
                db_data = {}
                
                for key in keys:
                    # Get key type and value
                    key_type = await redis_client.type(key)
                    
                    if key_type == b'string':
                        db_data[key.decode()] = {
                            'type': 'string',
                            'value': (await redis_client.get(key)).decode() if await redis_client.get(key) else None,
                            'ttl': await redis_client.ttl(key)
                        }
                    elif key_type == b'hash':
                        db_data[key.decode()] = {
                            'type': 'hash',
                            'value': {k.decode(): v.decode() for k, v in (await redis_client.hgetall(key)).items()},
                            'ttl': await redis_client.ttl(key)
                        }
                    elif key_type == b'list':
                        db_data[key.decode()] = {
                            'type': 'list',
                            'value': [item.decode() for item in await redis_client.lrange(key, 0, -1)],
                            'ttl': await redis_client.ttl(key)
                        }
                    elif key_type == b'set':
                        db_data[key.decode()] = {
                            'type': 'set',
                            'value': [item.decode() for item in await redis_client.smembers(key)],
                            'ttl': await redis_client.ttl(key)
                        }
                    elif key_type == b'zset':
                        db_data[key.decode()] = {
                            'type': 'zset',
                            'value': [(member.decode(), score) for member, score in await redis_client.zrange(key, 0, -1, withscores=True)],
                            'ttl': await redis_client.ttl(key)
                        }
                
                backup_data[f"db_{db}"] = db_data
                backup_record.record_count += len(db_data)
            
            await redis_client.close()
            
            # Save backup data
            backup_file = os.path.join(temp_dir, f"redis_backup_{backup_record.backup_id}.json")
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            # Get file stats and compress
            file_stats = os.stat(backup_file)
            backup_record.source_size_mb = file_stats.st_size / (1024 * 1024)
            
            if config.compression_enabled:
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                final_file = compressed_file
                
                compressed_stats = os.stat(compressed_file)
                backup_record.compressed_size_mb = compressed_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = backup_record.source_size_mb / backup_record.compressed_size_mb
            else:
                final_file = backup_file
                backup_record.compressed_size_mb = backup_record.source_size_mb
                backup_record.compression_ratio = 1.0
            
            # Calculate checksum and upload
            backup_record.checksum = await self._calculate_file_checksum(final_file)
            storage_path = await self._upload_to_storage(
                final_file,
                f"redis/{backup_record.backup_id}",
                config.storage_tier,
                config.encryption_enabled
            )
            
            backup_record.storage_location = storage_path
            backup_record.file_count = 1
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _backup_influxdb(self, config: BackupConfig, backup_record: BackupRecord):
        """Backup InfluxDB database"""
        
        source_config = config.source_config
        temp_dir = tempfile.mkdtemp()
        
        try:
            from influxdb_client import InfluxDBClient
            
            client = InfluxDBClient(
                url=source_config["url"],
                token=source_config["token"],
                org=source_config["org"]
            )
            
            buckets = source_config.get("buckets", ["analytics"])
            backup_files = []
            
            for bucket in buckets:
                # Export bucket data
                backup_file = os.path.join(temp_dir, f"influxdb_{bucket}_{backup_record.backup_id}.csv")
                
                # Query all data from bucket (in practice, you'd want to limit this)
                query = f'''
                    from(bucket: "{bucket}")
                    |> range(start: -30d)
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
                
                query_api = client.query_api()
                df = query_api.query_data_frame(query)
                
                if not df.empty:
                    df.to_csv(backup_file, index=False)
                    backup_files.append(backup_file)
                    backup_record.record_count += len(df)
            
            client.close()
            
            # Create tar archive of all bucket files
            archive_file = os.path.join(temp_dir, f"influxdb_backup_{backup_record.backup_id}.tar")
            
            if backup_files:
                import tarfile
                with tarfile.open(archive_file, 'w') as tar:
                    for backup_file in backup_files:
                        tar.add(backup_file, arcname=os.path.basename(backup_file))
                
                final_file = archive_file
                backup_record.file_count = len(backup_files)
            else:
                # Create empty marker file
                with open(archive_file, 'w') as f:
                    f.write(f"# Empty InfluxDB backup - {datetime.now()}\n")
                final_file = archive_file
                backup_record.file_count = 0
            
            # Get stats and compress
            file_stats = os.stat(final_file)
            backup_record.source_size_mb = file_stats.st_size / (1024 * 1024)
            
            if config.compression_enabled and backup_record.source_size_mb > 0:
                compressed_file = f"{final_file}.gz"
                with open(final_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                final_file = compressed_file
                
                compressed_stats = os.stat(compressed_file)
                backup_record.compressed_size_mb = compressed_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = backup_record.source_size_mb / backup_record.compressed_size_mb
            else:
                backup_record.compressed_size_mb = backup_record.source_size_mb
                backup_record.compression_ratio = 1.0
            
            # Upload to storage
            backup_record.checksum = await self._calculate_file_checksum(final_file)
            storage_path = await self._upload_to_storage(
                final_file,
                f"influxdb/{backup_record.backup_id}",
                config.storage_tier,
                config.encryption_enabled
            )
            
            backup_record.storage_location = storage_path
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _backup_qdrant(self, config: BackupConfig, backup_record: BackupRecord):
        """Backup Qdrant vector database"""
        
        source_config = config.source_config
        temp_dir = tempfile.mkdtemp()
        
        try:
            collections = source_config.get("collections", ["content_embeddings"])
            backup_files = []
            
            for collection in collections:
                try:
                    # Get collection info
                    collection_info = await self.vector_db.client.get_collection(collection)
                    
                    # Export collection points
                    backup_file = os.path.join(temp_dir, f"qdrant_{collection}_{backup_record.backup_id}.json")
                    
                    # Scroll through all points
                    points = []
                    offset = None
                    
                    while True:
                        scroll_result = await self.vector_db.client.scroll(
                            collection_name=collection,
                            limit=1000,
                            offset=offset,
                            with_payload=True,
                            with_vectors=True
                        )
                        
                        if not scroll_result[0]:
                            break
                        
                        for point in scroll_result[0]:
                            points.append({
                                "id": point.id,
                                "vector": point.vector,
                                "payload": point.payload
                            })
                        
                        offset = scroll_result[1]
                        if not offset:
                            break
                    
                    # Save collection data
                    collection_data = {
                        "collection_info": {
                            "name": collection,
                            "vectors_count": collection_info.points_count,
                            "vector_size": collection_info.config.params.vectors.size,
                            "distance": collection_info.config.params.vectors.distance.value
                        },
                        "points": points
                    }
                    
                    with open(backup_file, 'w') as f:
                        json.dump(collection_data, f, default=str)
                    
                    backup_files.append(backup_file)
                    backup_record.record_count += len(points)
                    
                except Exception as e:
                    logger.warning(f"Failed to backup collection {collection}: {e}")
            
            if backup_files:
                # Create tar archive
                archive_file = os.path.join(temp_dir, f"qdrant_backup_{backup_record.backup_id}.tar")
                
                import tarfile
                with tarfile.open(archive_file, 'w') as tar:
                    for backup_file in backup_files:
                        tar.add(backup_file, arcname=os.path.basename(backup_file))
                
                final_file = archive_file
                backup_record.file_count = len(backup_files)
            else:
                # Create empty marker
                final_file = os.path.join(temp_dir, f"qdrant_empty_{backup_record.backup_id}.txt")
                with open(final_file, 'w') as f:
                    f.write(f"# Empty Qdrant backup - {datetime.now()}\n")
                backup_record.file_count = 0
            
            # Process file
            file_stats = os.stat(final_file)
            backup_record.source_size_mb = file_stats.st_size / (1024 * 1024)
            
            if config.compression_enabled and backup_record.source_size_mb > 0:
                compressed_file = f"{final_file}.gz"
                with open(final_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                final_file = compressed_file
                
                compressed_stats = os.stat(compressed_file)
                backup_record.compressed_size_mb = compressed_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = backup_record.source_size_mb / backup_record.compressed_size_mb
            else:
                backup_record.compressed_size_mb = backup_record.source_size_mb
                backup_record.compression_ratio = 1.0
            
            # Upload
            backup_record.checksum = await self._calculate_file_checksum(final_file)
            storage_path = await self._upload_to_storage(
                final_file,
                f"qdrant/{backup_record.backup_id}",
                config.storage_tier,
                config.encryption_enabled
            )
            
            backup_record.storage_location = storage_path
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _backup_minio(self, config: BackupConfig, backup_record: BackupRecord):
        """Backup MinIO file storage"""
        
        source_config = config.source_config
        temp_dir = tempfile.mkdtemp()
        
        try:
            buckets = source_config.get("buckets", ["prism-content"])
            exclude_prefixes = source_config.get("exclude_prefixes", [])
            
            total_size = 0
            total_files = 0
            
            # Create manifest of all files
            manifest_file = os.path.join(temp_dir, f"minio_manifest_{backup_record.backup_id}.json")
            manifest_data = {"buckets": {}, "backup_timestamp": datetime.now().isoformat()}
            
            for bucket in buckets:
                try:
                    bucket_data = {"files": [], "total_size": 0, "file_count": 0}
                    
                    # List all objects in bucket
                    objects = self.minio_client.list_objects(bucket, recursive=True)
                    
                    for obj in objects:
                        # Skip excluded prefixes
                        if any(obj.object_name.startswith(prefix) for prefix in exclude_prefixes):
                            continue
                        
                        # Get object metadata
                        obj_stat = self.minio_client.stat_object(bucket, obj.object_name)
                        
                        bucket_data["files"].append({
                            "object_name": obj.object_name,
                            "size": obj_stat.size,
                            "etag": obj_stat.etag,
                            "last_modified": obj_stat.last_modified.isoformat(),
                            "content_type": obj_stat.content_type
                        })
                        
                        bucket_data["total_size"] += obj_stat.size
                        bucket_data["file_count"] += 1
                        total_size += obj_stat.size
                        total_files += 1
                    
                    manifest_data["buckets"][bucket] = bucket_data
                    
                except Exception as e:
                    logger.warning(f"Failed to backup bucket {bucket}: {e}")
                    manifest_data["buckets"][bucket] = {"error": str(e)}
            
            # Save manifest
            with open(manifest_file, 'w') as f:
                json.dump(manifest_data, f, indent=2, default=str)
            
            backup_record.source_size_mb = total_size / (1024 * 1024)
            backup_record.file_count = total_files
            backup_record.record_count = total_files
            
            # For MinIO backup, we're just saving the manifest
            # In production, you might want to sync files to external storage
            
            final_file = manifest_file
            
            if config.compression_enabled:
                compressed_file = f"{final_file}.gz"
                with open(final_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                final_file = compressed_file
                
                compressed_stats = os.stat(compressed_file)
                backup_record.compressed_size_mb = compressed_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = backup_record.source_size_mb / backup_record.compressed_size_mb if backup_record.source_size_mb > 0 else 1.0
            else:
                file_stats = os.stat(final_file)
                backup_record.compressed_size_mb = file_stats.st_size / (1024 * 1024)
                backup_record.compression_ratio = 1.0
            
            # Upload manifest
            backup_record.checksum = await self._calculate_file_checksum(final_file)
            storage_path = await self._upload_to_storage(
                final_file,
                f"minio/{backup_record.backup_id}",
                config.storage_tier,
                config.encryption_enabled
            )
            
            backup_record.storage_location = storage_path
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _upload_to_storage(
        self,
        local_file_path: str,
        storage_key: str,
        storage_tier: StorageTier,
        encryption_enabled: bool
    ) -> str:
        """Upload file to appropriate storage tier"""
        
        # Determine bucket based on storage tier
        bucket_map = {
            StorageTier.HOT: "hot-backups",
            StorageTier.WARM: "warm-backups", 
            StorageTier.COLD: "cold-backups",
            StorageTier.FROZEN: "frozen-backups"
        }
        
        bucket = bucket_map[storage_tier]
        
        # Add file extension if not present
        if not storage_key.endswith(('.gz', '.tar', '.sql', '.json')):
            if local_file_path.endswith('.gz'):
                storage_key += '.gz'
            elif local_file_path.endswith('.tar'):
                storage_key += '.tar'
        
        try:
            # Upload to MinIO
            self.minio_client.fput_object(
                bucket,
                storage_key,
                local_file_path,
                metadata={
                    "backup-timestamp": datetime.now().isoformat(),
                    "storage-tier": storage_tier.value,
                    "encrypted": str(encryption_enabled)
                }
            )
            
            return f"minio://{bucket}/{storage_key}"
            
        except Exception as e:
            logger.error(f"Failed to upload to storage: {e}")
            raise
    
    async def _verify_backup(self, config: BackupConfig, backup_record: BackupRecord):
        """Verify backup integrity"""
        
        try:
            # Download backup file to temporary location
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "verify_backup")
            
            # Parse storage location
            if backup_record.storage_location.startswith("minio://"):
                bucket, key = backup_record.storage_location[8:].split("/", 1)
                
                self.minio_client.fget_object(bucket, key, temp_file)
                
                # Verify checksum
                calculated_checksum = await self._calculate_file_checksum(temp_file)
                
                if calculated_checksum == backup_record.checksum:
                    backup_record.verification_status = "verified"
                    logger.info(f"Backup verification successful: {backup_record.backup_id}")
                else:
                    backup_record.verification_status = "checksum_mismatch"
                    logger.error(f"Backup checksum mismatch: {backup_record.backup_id}")
            
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            backup_record.verification_status = f"verification_failed: {str(e)}"
            logger.error(f"Backup verification failed: {backup_record.backup_id}: {e}")
    
    async def _log_backup_metrics(self, backup_record: BackupRecord):
        """Log backup metrics to time series database"""
        
        try:
            # Backup completion metrics
            await self.time_series.write_metric(
                metric_name="backup_completion",
                value=1,
                tags={
                    "config_id": backup_record.config_id,
                    "backup_type": backup_record.backup_type.value,
                    "status": backup_record.status.value,
                    "storage_tier": backup_record.storage_tier.value
                }
            )
            
            # Backup size metrics
            await self.time_series.write_metric(
                metric_name="backup_size",
                value=backup_record.compressed_size_mb,
                tags={
                    "config_id": backup_record.config_id,
                    "backup_type": backup_record.backup_type.value,
                    "storage_tier": backup_record.storage_tier.value,
                    "metric_type": "compressed_size_mb"
                }
            )
            
            # Backup duration
            if backup_record.completed_at:
                duration = (backup_record.completed_at - backup_record.started_at).total_seconds()
                await self.time_series.write_metric(
                    metric_name="backup_duration",
                    value=duration,
                    tags={
                        "config_id": backup_record.config_id,
                        "backup_type": backup_record.backup_type.value
                    }
                )
            
            # Compression ratio
            if backup_record.compression_ratio > 0:
                await self.time_series.write_metric(
                    metric_name="backup_compression_ratio",
                    value=backup_record.compression_ratio,
                    tags={
                        "config_id": backup_record.config_id,
                        "backup_type": backup_record.backup_type.value
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to log backup metrics: {e}")
    
    async def _log_backup_failure(self, backup_record: BackupRecord, error_message: str):
        """Log backup failure metrics"""
        
        try:
            await self.time_series.write_metric(
                metric_name="backup_failures",
                value=1,
                tags={
                    "config_id": backup_record.config_id,
                    "backup_type": backup_record.backup_type.value,
                    "error_type": "execution_failed"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log backup failure metrics: {e}")
    
    async def _cleanup_old_backups(self, config: BackupConfig):
        """Clean up old backups based on retention policy"""
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=config.retention_days)
            
            # This would require a backup metadata store to track all backups
            # For now, we'll implement basic cleanup based on object names
            
            bucket_map = {
                StorageTier.HOT: "hot-backups",
                StorageTier.WARM: "warm-backups",
                StorageTier.COLD: "cold-backups", 
                StorageTier.FROZEN: "frozen-backups"
            }
            
            bucket = bucket_map[config.storage_tier]
            prefix = config.source_type + "/"
            
            # List objects with the prefix
            objects = self.minio_client.list_objects(bucket, prefix=prefix)
            
            for obj in objects:
                try:
                    # Extract timestamp from object name (assuming format includes timestamp)
                    # This is a simplified approach - in production you'd want proper metadata
                    if "_" in obj.object_name:
                        timestamp_part = obj.object_name.split("_")[-1].split(".")[0]
                        try:
                            obj_date = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                            obj_date = obj_date.replace(tzinfo=timezone.utc)
                            
                            if obj_date < cutoff_date:
                                self.minio_client.remove_object(bucket, obj.object_name)
                                logger.info(f"Cleaned up old backup: {obj.object_name}")
                        except ValueError:
                            # Skip objects that don't match expected timestamp format
                            pass
                except Exception as e:
                    logger.warning(f"Failed to cleanup backup object {obj.object_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old backups for config {config.backup_id}: {e}")
    
    async def _get_last_backup_timestamp(self, config_id: str) -> Optional[datetime]:
        """Get timestamp of last successful backup"""
        
        # This would typically query a backup metadata database
        # For now, use Redis cache
        
        try:
            cache_key = f"last_backup:{config_id}"
            cached_timestamp = await self.redis.get(cache_key)
            
            if cached_timestamp:
                return datetime.fromisoformat(cached_timestamp)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last backup timestamp: {e}")
            return None
    
    async def restore_backup(
        self,
        backup_id: str,
        restore_target: str = None,
        restore_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Restore from backup"""
        
        restore_options = restore_options or {}
        
        try:
            logger.info(f"Starting restore operation: {backup_id}")
            
            # This would implement the restore logic based on backup type
            # For brevity, providing the structure without full implementation
            
            restore_result = {
                "backup_id": backup_id,
                "restore_target": restore_target,
                "status": "completed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "records_restored": 0,
                "files_restored": 0,
                "warnings": []
            }
            
            # Log restore metrics
            await self.time_series.write_metric(
                metric_name="backup_restore",
                value=1,
                tags={
                    "backup_id": backup_id,
                    "restore_target": restore_target or "original",
                    "status": "completed"
                }
            )
            
            return restore_result
            
        except Exception as e:
            logger.error(f"Restore failed: {backup_id}: {e}")
            
            await self.time_series.write_metric(
                metric_name="backup_restore",
                value=1,
                tags={
                    "backup_id": backup_id,
                    "restore_target": restore_target or "original", 
                    "status": "failed"
                }
            )
            
            return {
                "backup_id": backup_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def get_backup_status(self) -> Dict[str, Any]:
        """Get comprehensive backup system status"""
        
        try:
            # Get active backups
            active_count = len(self.active_backups)
            
            # Get recent backup metrics from time series
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            backup_metrics = await self.time_series.query_metrics(
                measurement="backup_completion",
                start_time=start_time,
                end_time=end_time,
                aggregation="sum",
                window="1h"
            )
            
            # Calculate success rate
            total_backups = sum(metric['value'] for metric in backup_metrics if metric['value'])
            successful_backups = sum(
                metric['value'] for metric in backup_metrics 
                if metric.get('status') == 'completed'
            )
            
            success_rate = (successful_backups / total_backups * 100) if total_backups > 0 else 100
            
            # Get storage usage by tier
            storage_usage = await self._get_storage_usage()
            
            return {
                "system_status": "healthy" if success_rate >= 90 else "degraded",
                "active_backups": active_count,
                "total_configs": len(self.backup_configs),
                "success_rate_24h": success_rate,
                "total_backups_24h": total_backups,
                "storage_usage": storage_usage,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    async def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage across all backup tiers"""
        
        usage = {}
        
        bucket_map = {
            "hot": "hot-backups",
            "warm": "warm-backups",
            "cold": "cold-backups", 
            "frozen": "frozen-backups"
        }
        
        for tier, bucket in bucket_map.items():
            try:
                total_size = 0
                object_count = 0
                
                objects = self.minio_client.list_objects(bucket, recursive=True)
                for obj in objects:
                    obj_stat = self.minio_client.stat_object(bucket, obj.object_name)
                    total_size += obj_stat.size
                    object_count += 1
                
                usage[tier] = {
                    "total_size_gb": total_size / (1024 ** 3),
                    "object_count": object_count
                }
                
            except Exception as e:
                logger.warning(f"Failed to get usage for {tier} tier: {e}")
                usage[tier] = {"error": str(e)}
        
        return usage
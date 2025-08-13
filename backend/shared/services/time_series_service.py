"""
Time Series Database Service
InfluxDB integration for analytics and performance monitoring
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.delete_api import DeleteApi
from influxdb_client.domain.write_precision import WritePrecision
import pandas as pd

from ..database import get_redis_client
from ..logging import get_logger

logger = get_logger(__name__)

@dataclass
class TimeSeriesPoint:
    """Time series data point"""
    measurement: str
    timestamp: datetime
    tags: Dict[str, str]
    fields: Dict[str, Union[float, int, str, bool]]

@dataclass
class MetricDefinition:
    """Definition for a metric"""
    name: str
    measurement: str
    field: str
    tags: List[str]
    description: str
    unit: str
    aggregation_method: str = "mean"  # mean, sum, count, max, min

class TimeSeriesService:
    """Comprehensive time series database service using InfluxDB"""
    
    def __init__(
        self,
        url: str = "http://influxdb:8086",
        token: str = "prism-analytics-token",
        org: str = "prism",
        bucket: str = "analytics"
    ):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self.query_api = None
        self.delete_api = None
        self.redis = get_redis_client()
        
        # Metric definitions
        self.metric_definitions = self._initialize_metric_definitions()
        
        # Initialize InfluxDB client
        asyncio.create_task(self._initialize_client())
    
    async def _initialize_client(self):
        """Initialize InfluxDB client and APIs"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()
            self.delete_api = self.client.delete_api()
            
            logger.info("InfluxDB client initialized successfully")
            
            # Create retention policies
            await self._setup_retention_policies()
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
    
    def _initialize_metric_definitions(self) -> Dict[str, MetricDefinition]:
        """Initialize all metric definitions"""
        return {
            # Content Generation Metrics
            'content_generation_time': MetricDefinition(
                name='Content Generation Time',
                measurement='content_generation',
                field='generation_time_seconds',
                tags=['domain', 'agent_type', 'model_used'],
                description='Time taken to generate content',
                unit='seconds'
            ),
            'content_quality_score': MetricDefinition(
                name='Content Quality Score',
                measurement='content_quality',
                field='quality_score',
                tags=['domain', 'content_type', 'analyzer_version'],
                description='Overall quality score of generated content',
                unit='score'
            ),
            'api_cost': MetricDefinition(
                name='API Cost',
                measurement='api_usage',
                field='cost_usd',
                tags=['provider', 'model', 'domain'],
                description='Cost of API usage',
                unit='USD',
                aggregation_method='sum'
            ),
            
            # System Performance Metrics
            'response_time': MetricDefinition(
                name='Response Time',
                measurement='system_performance',
                field='response_time_ms',
                tags=['service', 'endpoint', 'method'],
                description='API response time',
                unit='milliseconds'
            ),
            'error_rate': MetricDefinition(
                name='Error Rate',
                measurement='system_errors',
                field='error_count',
                tags=['service', 'error_type', 'severity'],
                description='System error occurrences',
                unit='count',
                aggregation_method='sum'
            ),
            'memory_usage': MetricDefinition(
                name='Memory Usage',
                measurement='system_resources',
                field='memory_percent',
                tags=['service', 'instance'],
                description='Memory usage percentage',
                unit='percent'
            ),
            'cpu_usage': MetricDefinition(
                name='CPU Usage',
                measurement='system_resources',
                field='cpu_percent',
                tags=['service', 'instance'],
                description='CPU usage percentage',
                unit='percent'
            ),
            
            # Publishing Metrics
            'publishing_success_rate': MetricDefinition(
                name='Publishing Success Rate',
                measurement='publishing',
                field='success_rate',
                tags=['platform', 'domain', 'content_type'],
                description='Publishing success rate',
                unit='percent'
            ),
            'engagement_rate': MetricDefinition(
                name='Engagement Rate',
                measurement='content_engagement',
                field='engagement_rate',
                tags=['platform', 'domain', 'content_type'],
                description='Content engagement rate',
                unit='percent'
            ),
            
            # Agent Learning Metrics
            'agent_effectiveness': MetricDefinition(
                name='Agent Effectiveness',
                measurement='agent_performance',
                field='effectiveness_score',
                tags=['agent_type', 'domain', 'memory_type'],
                description='Agent learning effectiveness',
                unit='score'
            ),
            'pattern_discovery': MetricDefinition(
                name='Pattern Discovery',
                measurement='agent_learning',
                field='patterns_discovered',
                tags=['agent_type', 'domain'],
                description='Number of patterns discovered',
                unit='count',
                aggregation_method='sum'
            ),
            
            # Data Pipeline Metrics
            'pipeline_throughput': MetricDefinition(
                name='Pipeline Throughput',
                measurement='data_pipeline',
                field='items_processed',
                tags=['pipeline_stage', 'source_type', 'domain'],
                description='Data pipeline throughput',
                unit='items/hour',
                aggregation_method='sum'
            ),
            'data_quality': MetricDefinition(
                name='Data Quality',
                measurement='data_quality',
                field='quality_score',
                tags=['source', 'domain', 'validation_type'],
                description='Data quality score',
                unit='score'
            )
        }
    
    async def _setup_retention_policies(self):
        """Setup retention policies for different data types"""
        try:
            # High-frequency metrics: keep for 30 days
            await self._create_bucket_if_not_exists(
                "short_term", 
                retention_period="720h",  # 30 days
                description="Short-term high-frequency metrics"
            )
            
            # Medium-frequency metrics: keep for 1 year
            await self._create_bucket_if_not_exists(
                "medium_term",
                retention_period="8760h",  # 1 year
                description="Medium-term aggregate metrics"
            )
            
            # Long-term analytics: keep for 7 years (compliance)
            await self._create_bucket_if_not_exists(
                "long_term",
                retention_period="61320h",  # 7 years
                description="Long-term compliance and analytics data"
            )
            
        except Exception as e:
            logger.warning(f"Failed to setup retention policies: {e}")
    
    async def _create_bucket_if_not_exists(
        self,
        bucket_name: str,
        retention_period: str,
        description: str
    ):
        """Create bucket if it doesn't exist"""
        try:
            buckets_api = self.client.buckets_api()
            
            # Check if bucket exists
            existing_buckets = buckets_api.find_buckets(name=bucket_name)
            
            if not existing_buckets.buckets:
                # Create bucket
                from influxdb_client.domain.bucket import Bucket
                from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules
                
                retention_rule = BucketRetentionRules(
                    type="expire",
                    every_seconds=self._parse_duration_to_seconds(retention_period)
                )
                
                bucket = Bucket(
                    name=bucket_name,
                    org_id=self.org,
                    retention_rules=[retention_rule],
                    description=description
                )
                
                buckets_api.create_bucket(bucket=bucket)
                logger.info(f"Created bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
    
    def _parse_duration_to_seconds(self, duration: str) -> int:
        """Parse duration string to seconds"""
        if duration.endswith('h'):
            return int(duration[:-1]) * 3600
        elif duration.endswith('d'):
            return int(duration[:-1]) * 86400
        elif duration.endswith('w'):
            return int(duration[:-1]) * 604800
        else:
            return int(duration)
    
    async def write_metric(
        self,
        metric_name: str,
        value: Union[float, int, str, bool],
        tags: Dict[str, str] = None,
        timestamp: datetime = None,
        bucket: str = None
    ) -> bool:
        """Write a single metric to InfluxDB"""
        
        try:
            if metric_name not in self.metric_definitions:
                logger.warning(f"Unknown metric: {metric_name}")
                return False
            
            metric_def = self.metric_definitions[metric_name]
            
            # Use current time if not provided
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Create point
            point = Point(metric_def.measurement) \
                .time(timestamp, WritePrecision.S) \
                .field(metric_def.field, value)
            
            # Add tags
            if tags:
                for tag_key, tag_value in tags.items():
                    point = point.tag(tag_key, str(tag_value))
            
            # Write to appropriate bucket
            target_bucket = bucket or self._determine_bucket(metric_name)
            
            self.write_api.write(
                bucket=target_bucket,
                org=self.org,
                record=point
            )
            
            # Cache recent metrics for quick access
            await self._cache_recent_metric(metric_name, value, tags, timestamp)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write metric {metric_name}: {e}")
            return False
    
    async def write_metrics_batch(
        self,
        metrics: List[TimeSeriesPoint],
        bucket: str = None
    ) -> Dict[str, Any]:
        """Write batch of metrics to InfluxDB"""
        
        try:
            points = []
            
            for metric in metrics:
                point = Point(metric.measurement) \
                    .time(metric.timestamp, WritePrecision.S)
                
                # Add fields
                for field_name, field_value in metric.fields.items():
                    point = point.field(field_name, field_value)
                
                # Add tags
                for tag_name, tag_value in metric.tags.items():
                    point = point.tag(tag_name, str(tag_value))
                
                points.append(point)
            
            # Write batch
            target_bucket = bucket or self.bucket
            self.write_api.write(
                bucket=target_bucket,
                org=self.org,
                record=points
            )
            
            logger.debug(f"Wrote {len(points)} metrics to InfluxDB")
            
            return {
                'success': True,
                'points_written': len(points),
                'bucket': target_bucket
            }
            
        except Exception as e:
            logger.error(f"Failed to write metrics batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'points_written': 0
            }
    
    async def query_metrics(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime = None,
        filters: Dict[str, str] = None,
        aggregation: str = "mean",
        window: str = "1h",
        bucket: str = None
    ) -> List[Dict[str, Any]]:
        """Query metrics from InfluxDB"""
        
        try:
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            
            # Build Flux query
            query = self._build_flux_query(
                measurement=measurement,
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation=aggregation,
                window=window,
                bucket=bucket or self.bucket
            )
            
            # Execute query
            result = self.query_api.query(org=self.org, query=query)
            
            # Convert to list of dictionaries
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        'time': record.get_time(),
                        'value': record.get_value(),
                        'field': record.get_field(),
                        'measurement': record.get_measurement(),
                        **{k: v for k, v in record.values.items() 
                           if k not in ['_time', '_value', '_field', '_measurement']}
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            return []
    
    def _build_flux_query(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        filters: Dict[str, str] = None,
        aggregation: str = "mean",
        window: str = "1h",
        bucket: str = None
    ) -> str:
        """Build Flux query string"""
        
        query_parts = [
            f'from(bucket: "{bucket or self.bucket}")',
            f'|> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})',
            f'|> filter(fn: (r) => r._measurement == "{measurement}")'
        ]
        
        # Add tag filters
        if filters:
            for tag, value in filters.items():
                query_parts.append(f'|> filter(fn: (r) => r.{tag} == "{value}")')
        
        # Add aggregation
        if window and aggregation:
            query_parts.append(f'|> aggregateWindow(every: {window}, fn: {aggregation})')
        
        # Add final transformations
        query_parts.append('|> yield(name: "result")')
        
        return ' '.join(query_parts)
    
    async def get_system_health_metrics(
        self,
        time_range: str = "1h"
    ) -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = self._parse_time_range(time_range, end_time)
            
            health_metrics = {}
            
            # System performance metrics
            response_times = await self.query_metrics(
                measurement="system_performance",
                start_time=start_time,
                end_time=end_time,
                aggregation="mean",
                window="5m"
            )
            
            error_counts = await self.query_metrics(
                measurement="system_errors",
                start_time=start_time,
                end_time=end_time,
                aggregation="sum",
                window="5m"
            )
            
            resource_usage = await self.query_metrics(
                measurement="system_resources",
                start_time=start_time,
                end_time=end_time,
                aggregation="mean",
                window="5m"
            )
            
            # Calculate health scores
            health_metrics['overall_health'] = self._calculate_overall_health(
                response_times, error_counts, resource_usage
            )
            
            health_metrics['response_time_trend'] = self._calculate_trend(response_times)
            health_metrics['error_rate_trend'] = self._calculate_trend(error_counts)
            health_metrics['resource_usage_trend'] = self._calculate_trend(resource_usage)
            
            # Service-specific metrics
            health_metrics['services'] = await self._get_service_specific_metrics(
                start_time, end_time
            )
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"Failed to get system health metrics: {e}")
            return {'error': str(e)}
    
    async def get_content_analytics(
        self,
        domain: str = None,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get comprehensive content analytics"""
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = self._parse_time_range(time_range, end_time)
            
            analytics = {}
            
            # Content generation metrics
            filters = {'domain': domain} if domain else None
            
            generation_times = await self.query_metrics(
                measurement="content_generation",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            quality_scores = await self.query_metrics(
                measurement="content_quality",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            api_costs = await self.query_metrics(
                measurement="api_usage",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="sum",
                window="1h"
            )
            
            # Publishing metrics
            publishing_metrics = await self.query_metrics(
                measurement="publishing",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            engagement_metrics = await self.query_metrics(
                measurement="content_engagement",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            # Calculate analytics
            analytics['generation_performance'] = {
                'average_time': self._calculate_average(generation_times),
                'time_trend': self._calculate_trend(generation_times),
                'efficiency_score': self._calculate_efficiency_score(generation_times)
            }
            
            analytics['quality_analysis'] = {
                'average_score': self._calculate_average(quality_scores),
                'quality_trend': self._calculate_trend(quality_scores),
                'quality_distribution': self._calculate_distribution(quality_scores)
            }
            
            analytics['cost_analysis'] = {
                'total_cost': self._calculate_sum(api_costs),
                'cost_trend': self._calculate_trend(api_costs),
                'cost_per_content': self._calculate_cost_per_content(api_costs, generation_times)
            }
            
            analytics['publishing_performance'] = {
                'success_rate': self._calculate_average(publishing_metrics),
                'engagement_rate': self._calculate_average(engagement_metrics),
                'performance_trend': self._calculate_trend(publishing_metrics)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get content analytics: {e}")
            return {'error': str(e)}
    
    async def get_agent_performance_metrics(
        self,
        agent_type: str,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """Get agent performance metrics"""
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = self._parse_time_range(time_range, end_time)
            
            filters = {'agent_type': agent_type}
            
            # Agent effectiveness
            effectiveness_data = await self.query_metrics(
                measurement="agent_performance",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="mean",
                window="1h"
            )
            
            # Pattern discovery
            pattern_data = await self.query_metrics(
                measurement="agent_learning",
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                aggregation="sum",
                window="1d"
            )
            
            return {
                'agent_type': agent_type,
                'effectiveness_score': self._calculate_average(effectiveness_data),
                'effectiveness_trend': self._calculate_trend(effectiveness_data),
                'patterns_discovered': self._calculate_sum(pattern_data),
                'learning_velocity': self._calculate_learning_velocity(
                    effectiveness_data, pattern_data
                ),
                'performance_consistency': self._calculate_consistency(effectiveness_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent performance metrics: {e}")
            return {'error': str(e)}
    
    async def create_alert_rule(
        self,
        rule_name: str,
        measurement: str,
        field: str,
        condition: str,
        threshold: float,
        time_window: str = "5m",
        tags_filter: Dict[str, str] = None
    ) -> bool:
        """Create an alert rule for monitoring"""
        
        try:
            # Store alert rule in Redis for monitoring
            alert_rule = {
                'rule_name': rule_name,
                'measurement': measurement,
                'field': field,
                'condition': condition,
                'threshold': threshold,
                'time_window': time_window,
                'tags_filter': tags_filter or {},
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            await self.redis.setex(
                f"alert_rule:{rule_name}",
                86400 * 7,  # Keep for 7 days
                json.dumps(alert_rule)
            )
            
            logger.info(f"Created alert rule: {rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            return False
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all active alert rules"""
        
        try:
            alerts = []
            
            # Get all alert rules
            rule_keys = await self.redis.keys("alert_rule:*")
            
            for rule_key in rule_keys:
                rule_data = await self.redis.get(rule_key)
                if not rule_data:
                    continue
                
                rule = json.loads(rule_data)
                if not rule.get('active'):
                    continue
                
                # Check rule condition
                is_triggered = await self._check_alert_condition(rule)
                
                if is_triggered:
                    alert = {
                        'rule_name': rule['rule_name'],
                        'measurement': rule['measurement'],
                        'field': rule['field'],
                        'condition': rule['condition'],
                        'threshold': rule['threshold'],
                        'current_value': is_triggered['current_value'],
                        'severity': self._determine_alert_severity(rule, is_triggered),
                        'triggered_at': datetime.now().isoformat(),
                        'message': f"{rule['rule_name']}: {rule['field']} is {rule['condition']} {rule['threshold']} (current: {is_triggered['current_value']})"
                    }
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
            return []
    
    # Private helper methods
    
    def _determine_bucket(self, metric_name: str) -> str:
        """Determine appropriate bucket based on metric type"""
        
        high_frequency_metrics = [
            'response_time', 'memory_usage', 'cpu_usage'
        ]
        
        long_term_metrics = [
            'api_cost', 'content_quality_score', 'agent_effectiveness'
        ]
        
        if metric_name in high_frequency_metrics:
            return "short_term"
        elif metric_name in long_term_metrics:
            return "long_term"
        else:
            return "medium_term"
    
    async def _cache_recent_metric(
        self,
        metric_name: str,
        value: Union[float, int, str, bool],
        tags: Dict[str, str],
        timestamp: datetime
    ):
        """Cache recent metrics for quick access"""
        
        cache_key = f"recent_metric:{metric_name}"
        
        metric_data = {
            'value': value,
            'tags': tags or {},
            'timestamp': timestamp.isoformat()
        }
        
        # Keep last 10 values
        await self.redis.lpush(cache_key, json.dumps(metric_data, default=str))
        await self.redis.ltrim(cache_key, 0, 9)
        await self.redis.expire(cache_key, 3600)  # 1 hour TTL
    
    def _parse_time_range(self, time_range: str, end_time: datetime) -> datetime:
        """Parse time range string to start datetime"""
        
        if time_range.endswith('m'):
            minutes = int(time_range[:-1])
            return end_time - timedelta(minutes=minutes)
        elif time_range.endswith('h'):
            hours = int(time_range[:-1])
            return end_time - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            return end_time - timedelta(days=days)
        elif time_range.endswith('w'):
            weeks = int(time_range[:-1])
            return end_time - timedelta(weeks=weeks)
        else:
            # Default to 1 hour
            return end_time - timedelta(hours=1)
    
    def _calculate_overall_health(
        self,
        response_times: List[Dict],
        error_counts: List[Dict],
        resource_usage: List[Dict]
    ) -> float:
        """Calculate overall system health score"""
        
        try:
            # Response time health (0-100)
            avg_response_time = self._calculate_average(response_times)
            response_health = max(0, 100 - (avg_response_time / 10))  # 1000ms = 0 health
            
            # Error rate health (0-100)
            total_errors = self._calculate_sum(error_counts)
            error_health = max(0, 100 - (total_errors * 5))  # 20 errors = 0 health
            
            # Resource usage health (0-100)
            avg_resource_usage = self._calculate_average(resource_usage)
            resource_health = max(0, 100 - avg_resource_usage)
            
            # Weighted average
            overall_health = (
                response_health * 0.4 +
                error_health * 0.4 +
                resource_health * 0.2
            )
            
            return min(100, max(0, overall_health))
            
        except:
            return 50.0  # Default moderate health
    
    def _calculate_average(self, data: List[Dict]) -> float:
        """Calculate average value from metric data"""
        if not data:
            return 0.0
        
        values = [item.get('value', 0) for item in data if item.get('value') is not None]
        return np.mean(values) if values else 0.0
    
    def _calculate_sum(self, data: List[Dict]) -> float:
        """Calculate sum from metric data"""
        if not data:
            return 0.0
        
        values = [item.get('value', 0) for item in data if item.get('value') is not None]
        return np.sum(values) if values else 0.0
    
    def _calculate_trend(self, data: List[Dict]) -> float:
        """Calculate trend from metric data (positive = improving)"""
        if len(data) < 2:
            return 0.0
        
        try:
            values = [item.get('value', 0) for item in data if item.get('value') is not None]
            if len(values) < 2:
                return 0.0
            
            # Simple linear regression slope
            x = np.arange(len(values))
            y = np.array(values)
            
            slope = np.polyfit(x, y, 1)[0]
            return float(slope)
            
        except:
            return 0.0
    
    def _calculate_distribution(self, data: List[Dict]) -> Dict[str, float]:
        """Calculate value distribution"""
        if not data:
            return {}
        
        values = [item.get('value', 0) for item in data if item.get('value') is not None]
        if not values:
            return {}
        
        return {
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'percentile_25': float(np.percentile(values, 25)),
            'percentile_75': float(np.percentile(values, 75)),
            'percentile_95': float(np.percentile(values, 95))
        }
    
    def _calculate_efficiency_score(self, generation_times: List[Dict]) -> float:
        """Calculate efficiency score based on generation times"""
        if not generation_times:
            return 0.0
        
        avg_time = self._calculate_average(generation_times)
        
        # Efficiency score: lower time = higher efficiency
        if avg_time <= 10:
            return 100.0
        elif avg_time <= 30:
            return 80.0
        elif avg_time <= 60:
            return 60.0
        else:
            return max(0, 60 - (avg_time - 60) * 0.5)
    
    def _calculate_cost_per_content(
        self,
        api_costs: List[Dict],
        generation_times: List[Dict]
    ) -> float:
        """Calculate cost per content item"""
        total_cost = self._calculate_sum(api_costs)
        content_count = len([t for t in generation_times if t.get('value', 0) > 0])
        
        return total_cost / max(1, content_count)
    
    def _calculate_learning_velocity(
        self,
        effectiveness_data: List[Dict],
        pattern_data: List[Dict]
    ) -> float:
        """Calculate agent learning velocity"""
        effectiveness_trend = self._calculate_trend(effectiveness_data)
        pattern_count = self._calculate_sum(pattern_data)
        
        # Combine effectiveness improvement with pattern discovery
        velocity = (effectiveness_trend * 50) + (pattern_count * 0.1)
        return min(10.0, max(-10.0, velocity))
    
    def _calculate_consistency(self, data: List[Dict]) -> float:
        """Calculate performance consistency (lower variance = higher consistency)"""
        if not data:
            return 0.0
        
        values = [item.get('value', 0) for item in data if item.get('value') is not None]
        if len(values) < 2:
            return 100.0
        
        coefficient_of_variation = np.std(values) / max(0.001, np.mean(values))
        consistency = max(0, 100 - (coefficient_of_variation * 100))
        
        return consistency
    
    async def _get_service_specific_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Dict[str, Any]]:
        """Get metrics for each service"""
        
        services = [
            'content-generation', 'detection', 'publishing',
            'configuration', 'user-management', 'analytics',
            'file-storage', 'external-api'
        ]
        
        service_metrics = {}
        
        for service in services:
            try:
                response_times = await self.query_metrics(
                    measurement="system_performance",
                    start_time=start_time,
                    end_time=end_time,
                    filters={'service': service},
                    aggregation="mean",
                    window="5m"
                )
                
                errors = await self.query_metrics(
                    measurement="system_errors",
                    start_time=start_time,
                    end_time=end_time,
                    filters={'service': service},
                    aggregation="sum",
                    window="5m"
                )
                
                service_metrics[service] = {
                    'average_response_time': self._calculate_average(response_times),
                    'total_errors': self._calculate_sum(errors),
                    'health_score': self._calculate_service_health(response_times, errors)
                }
                
            except Exception as e:
                logger.warning(f"Failed to get metrics for service {service}: {e}")
                service_metrics[service] = {
                    'error': str(e),
                    'health_score': 0.0
                }
        
        return service_metrics
    
    def _calculate_service_health(
        self,
        response_times: List[Dict],
        errors: List[Dict]
    ) -> float:
        """Calculate health score for a specific service"""
        
        avg_response_time = self._calculate_average(response_times)
        total_errors = self._calculate_sum(errors)
        
        # Health based on response time and error count
        response_health = max(0, 100 - (avg_response_time / 20))
        error_health = max(0, 100 - (total_errors * 10))
        
        return (response_health * 0.7 + error_health * 0.3)
    
    async def _check_alert_condition(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if alert condition is met"""
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = self._parse_time_range(rule['time_window'], end_time)
            
            data = await self.query_metrics(
                measurement=rule['measurement'],
                start_time=start_time,
                end_time=end_time,
                filters=rule.get('tags_filter'),
                aggregation="mean",
                window=rule['time_window']
            )
            
            if not data:
                return None
            
            current_value = self._calculate_average(data)
            condition = rule['condition']
            threshold = rule['threshold']
            
            is_triggered = False
            if condition == 'greater_than' and current_value > threshold:
                is_triggered = True
            elif condition == 'less_than' and current_value < threshold:
                is_triggered = True
            elif condition == 'equals' and abs(current_value - threshold) < 0.001:
                is_triggered = True
            
            if is_triggered:
                return {
                    'current_value': current_value,
                    'threshold': threshold,
                    'condition': condition
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check alert condition: {e}")
            return None
    
    def _determine_alert_severity(
        self,
        rule: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ) -> str:
        """Determine alert severity based on how far value is from threshold"""
        
        current_value = trigger_data['current_value']
        threshold = trigger_data['threshold']
        
        # Calculate deviation percentage
        deviation = abs(current_value - threshold) / max(0.001, abs(threshold))
        
        if deviation > 0.5:
            return 'critical'
        elif deviation > 0.25:
            return 'high'
        elif deviation > 0.1:
            return 'medium'
        else:
            return 'low'
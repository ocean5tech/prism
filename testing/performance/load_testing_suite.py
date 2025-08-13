"""
Performance and Load Testing Suite
Comprehensive performance testing for content generation platform
"""

import asyncio
import time
import json
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import psutil
import numpy as np
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import plotly.graph_objects as go
import pandas as pd

from shared.logging import get_logger
from shared.config import TestSettings

logger = get_logger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    test_scenario: str
    additional_data: Dict[str, Any] = None

@dataclass
class LoadTestScenario:
    """Load test scenario configuration"""
    name: str
    target_endpoint: str
    concurrent_users: int
    duration_seconds: int
    ramp_up_seconds: int
    request_rate: float  # requests per second
    payload_generator: Callable = None
    expected_response_time: float = None  # seconds
    expected_success_rate: float = 0.95

@dataclass
class PerformanceTestResult:
    """Performance test execution result"""
    scenario_name: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    cpu_usage_avg: float
    memory_usage_avg: float
    detailed_metrics: List[PerformanceMetric]
    errors: List[Dict[str, Any]]

class SystemResourceMonitor:
    """Monitor system resources during performance tests"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.metrics = []
        self.monitoring = False
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.metrics.clear()
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("System resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_task:
            await self.monitor_task
        logger.info("System resource monitoring stopped")
    
    async def _monitor_loop(self):
        """Resource monitoring loop"""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024 ** 3)
                
                # Network I/O
                net_io = psutil.net_io_counters()
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                
                timestamp = datetime.now(timezone.utc)
                
                # Record metrics
                self.metrics.extend([
                    PerformanceMetric("cpu_usage_percent", cpu_percent, "percent", timestamp, "system"),
                    PerformanceMetric("memory_usage_percent", memory_percent, "percent", timestamp, "system"),
                    PerformanceMetric("memory_used_gb", memory_used_gb, "gb", timestamp, "system"),
                    PerformanceMetric("network_bytes_sent", net_io.bytes_sent, "bytes", timestamp, "system"),
                    PerformanceMetric("network_bytes_recv", net_io.bytes_recv, "bytes", timestamp, "system"),
                    PerformanceMetric("disk_read_bytes", disk_io.read_bytes, "bytes", timestamp, "system"),
                    PerformanceMetric("disk_write_bytes", disk_io.write_bytes, "bytes", timestamp, "system"),
                ])
                
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
                await asyncio.sleep(self.sampling_interval)
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Get average values for key metrics"""
        if not self.metrics:
            return {}
        
        cpu_values = [m.value for m in self.metrics if m.metric_name == "cpu_usage_percent"]
        memory_values = [m.value for m in self.metrics if m.metric_name == "memory_usage_percent"]
        
        return {
            "avg_cpu_usage": statistics.mean(cpu_values) if cpu_values else 0,
            "max_cpu_usage": max(cpu_values) if cpu_values else 0,
            "avg_memory_usage": statistics.mean(memory_values) if memory_values else 0,
            "max_memory_usage": max(memory_values) if memory_values else 0
        }

class ContentGenerationLoadTester:
    """Load tester for content generation endpoints"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self.session = None
        self.metrics = []
        self.resource_monitor = SystemResourceMonitor()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers=self.auth_headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def single_content_generation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single content generation request"""
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/content/generate",
                json=payload
            ) as response:
                response_time = time.time() - start_time
                response_data = await response.json()
                
                return {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "response_time": response_time,
                    "response_data": response_data,
                    "error_message": None if response.status == 200 else response_data.get("detail", "Unknown error")
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "status_code": None,
                "response_time": response_time,
                "response_data": None,
                "error_message": str(e)
            }
    
    async def run_load_test_scenario(self, scenario: LoadTestScenario) -> PerformanceTestResult:
        """Execute a complete load test scenario"""
        logger.info(f"Starting load test scenario: {scenario.name}")
        
        # Start system monitoring
        await self.resource_monitor.start_monitoring()
        
        start_time = datetime.now(timezone.utc)
        results = []
        errors = []
        
        # Generate test payloads
        test_payloads = []
        for i in range(scenario.concurrent_users * 10):  # Generate enough payloads
            if scenario.payload_generator:
                payload = scenario.payload_generator(i)
            else:
                payload = self._default_payload_generator(i)
            test_payloads.append(payload)
        
        try:
            # Execute concurrent requests
            tasks = []
            for user_id in range(scenario.concurrent_users):
                task = asyncio.create_task(
                    self._user_simulation(
                        user_id, 
                        scenario, 
                        test_payloads,
                        results,
                        errors
                    )
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = datetime.now(timezone.utc)
            
            # Stop system monitoring
            await self.resource_monitor.stop_monitoring()
            system_metrics = self.resource_monitor.get_average_metrics()
            
            # Calculate performance metrics
            successful_results = [r for r in results if r["success"]]
            failed_results = [r for r in results if not r["success"]]
            
            total_requests = len(results)
            successful_requests = len(successful_results)
            failed_requests = len(failed_results)
            
            if successful_results:
                response_times = [r["response_time"] for r in successful_results]
                avg_response_time = statistics.mean(response_times)
                p95_response_time = np.percentile(response_times, 95)
                p99_response_time = np.percentile(response_times, 99)
            else:
                avg_response_time = p95_response_time = p99_response_time = 0
            
            test_duration = (end_time - start_time).total_seconds()
            requests_per_second = total_requests / test_duration if test_duration > 0 else 0
            error_rate = failed_requests / total_requests if total_requests > 0 else 1
            
            # Create detailed metrics
            detailed_metrics = []
            for result in results:
                detailed_metrics.append(
                    PerformanceMetric(
                        "response_time",
                        result["response_time"],
                        "seconds",
                        start_time,
                        scenario.name,
                        {"success": result["success"], "status_code": result["status_code"]}
                    )
                )
            
            # Add system resource metrics
            detailed_metrics.extend(self.resource_monitor.metrics)
            
            test_result = PerformanceTestResult(
                scenario_name=scenario.name,
                start_time=start_time,
                end_time=end_time,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                requests_per_second=requests_per_second,
                error_rate=error_rate,
                cpu_usage_avg=system_metrics.get("avg_cpu_usage", 0),
                memory_usage_avg=system_metrics.get("avg_memory_usage", 0),
                detailed_metrics=detailed_metrics,
                errors=errors
            )
            
            logger.info(f"Load test scenario completed: {scenario.name}")
            logger.info(f"Total requests: {total_requests}, Success rate: {(1-error_rate)*100:.1f}%")
            logger.info(f"Average response time: {avg_response_time:.3f}s, P95: {p95_response_time:.3f}s")
            
            return test_result
            
        except Exception as e:
            logger.error(f"Load test scenario failed: {e}")
            await self.resource_monitor.stop_monitoring()
            raise
    
    async def _user_simulation(self, user_id: int, scenario: LoadTestScenario, 
                              test_payloads: List[Dict], results: List, errors: List):
        """Simulate individual user behavior"""
        end_time = time.time() + scenario.duration_seconds
        payload_index = user_id % len(test_payloads)
        
        # Staggered start (ramp-up)
        ramp_up_delay = (user_id / scenario.concurrent_users) * scenario.ramp_up_seconds
        await asyncio.sleep(ramp_up_delay)
        
        request_interval = 1.0 / scenario.request_rate if scenario.request_rate > 0 else 1.0
        
        while time.time() < end_time:
            try:
                payload = test_payloads[payload_index % len(test_payloads)]
                result = await self.single_content_generation_request(payload)
                results.append(result)
                
                if not result["success"]:
                    errors.append({
                        "user_id": user_id,
                        "error_message": result["error_message"],
                        "status_code": result["status_code"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                payload_index += 1
                await asyncio.sleep(request_interval)
                
            except Exception as e:
                errors.append({
                    "user_id": user_id,
                    "error_message": str(e),
                    "status_code": None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                await asyncio.sleep(request_interval)
    
    def _default_payload_generator(self, index: int) -> Dict[str, Any]:
        """Generate default test payload"""
        domains = ["finance", "sports", "technology"]
        sample_contents = [
            "Market analysis shows significant trends in technology sector...",
            "Championship game highlights showcase exceptional athletic performance...",
            "New artificial intelligence breakthrough promises industry transformation..."
        ]
        
        domain = domains[index % len(domains)]
        content = sample_contents[index % len(sample_contents)]
        
        return {
            "domain": domain,
            "source_content": content,
            "style_parameters": {
                "tone": ["professional", "engaging", "technical"][index % 3],
                "creativity": 0.5 + (index % 5) * 0.1
            },
            "target_length": 800 + (index % 5) * 100
        }

class PerformanceTestSuite:
    """Complete performance testing suite"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.test_results = []
    
    def create_test_scenarios(self) -> List[LoadTestScenario]:
        """Create comprehensive test scenarios"""
        scenarios = [
            # Baseline performance test
            LoadTestScenario(
                name="baseline_performance",
                target_endpoint="/api/v1/content/generate",
                concurrent_users=10,
                duration_seconds=300,  # 5 minutes
                ramp_up_seconds=60,
                request_rate=2.0,  # 2 requests per second per user
                expected_response_time=30.0,
                expected_success_rate=0.98
            ),
            
            # High-volume load test
            LoadTestScenario(
                name="high_volume_load",
                target_endpoint="/api/v1/content/generate", 
                concurrent_users=50,
                duration_seconds=600,  # 10 minutes
                ramp_up_seconds=120,
                request_rate=1.5,
                expected_response_time=45.0,
                expected_success_rate=0.95
            ),
            
            # Stress test - beyond normal capacity
            LoadTestScenario(
                name="stress_test",
                target_endpoint="/api/v1/content/generate",
                concurrent_users=100,
                duration_seconds=300,
                ramp_up_seconds=180,
                request_rate=1.0,
                expected_response_time=60.0,
                expected_success_rate=0.90
            ),
            
            # Spike test - sudden load increase
            LoadTestScenario(
                name="spike_test",
                target_endpoint="/api/v1/content/generate",
                concurrent_users=200,
                duration_seconds=180,  # 3 minutes
                ramp_up_seconds=30,    # Quick ramp-up
                request_rate=0.5,
                expected_response_time=90.0,
                expected_success_rate=0.85
            ),
            
            # Endurance test - sustained load
            LoadTestScenario(
                name="endurance_test",
                target_endpoint="/api/v1/content/generate",
                concurrent_users=25,
                duration_seconds=3600,  # 1 hour
                ramp_up_seconds=300,
                request_rate=1.0,
                expected_response_time=35.0,
                expected_success_rate=0.97
            ),
            
            # API endpoint performance test
            LoadTestScenario(
                name="api_endpoint_performance",
                target_endpoint="/api/v1/quality/analyze",
                concurrent_users=20,
                duration_seconds=300,
                ramp_up_seconds=60,
                request_rate=5.0,  # Faster for analysis endpoint
                expected_response_time=5.0,
                expected_success_rate=0.99
            )
        ]
        
        return scenarios
    
    async def run_comprehensive_performance_tests(self) -> Dict[str, Any]:
        """Run complete suite of performance tests"""
        logger.info("Starting comprehensive performance test suite")
        
        scenarios = self.create_test_scenarios()
        results = []
        
        async with ContentGenerationLoadTester(self.base_url, self.auth_token) as tester:
            for scenario in scenarios:
                try:
                    logger.info(f"Executing performance test: {scenario.name}")
                    result = await tester.run_load_test_scenario(scenario)
                    results.append(result)
                    
                    # Cool-down period between tests
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Performance test {scenario.name} failed: {e}")
                    continue
        
        # Analyze results
        test_summary = self._analyze_performance_results(results)
        
        # Generate reports
        await self._generate_performance_reports(results, test_summary)
        
        logger.info("Comprehensive performance test suite completed")
        return test_summary
    
    def _analyze_performance_results(self, results: List[PerformanceTestResult]) -> Dict[str, Any]:
        """Analyze performance test results"""
        if not results:
            return {"error": "No performance test results to analyze"}
        
        total_requests = sum(r.total_requests for r in results)
        total_successful = sum(r.successful_requests for r in results)
        total_failed = sum(r.failed_requests for r in results)
        
        overall_success_rate = total_successful / total_requests if total_requests > 0 else 0
        
        # Response time analysis
        all_response_times = []
        for result in results:
            response_time_metrics = [
                m for m in result.detailed_metrics 
                if m.metric_name == "response_time" and m.additional_data.get("success", False)
            ]
            all_response_times.extend([m.value for m in response_time_metrics])
        
        response_time_stats = {
            "average": statistics.mean(all_response_times) if all_response_times else 0,
            "median": statistics.median(all_response_times) if all_response_times else 0,
            "p95": np.percentile(all_response_times, 95) if all_response_times else 0,
            "p99": np.percentile(all_response_times, 99) if all_response_times else 0,
            "max": max(all_response_times) if all_response_times else 0
        }
        
        # Performance benchmarks validation
        benchmark_results = {}
        for result in results:
            benchmark_results[result.scenario_name] = {
                "meets_response_time_target": result.average_response_time <= 30.0,  # 30s target
                "meets_success_rate_target": (1 - result.error_rate) >= 0.95,  # 95% success
                "meets_throughput_target": result.requests_per_second >= 1.0,  # 1 RPS minimum
                "system_resource_healthy": result.cpu_usage_avg <= 80.0  # 80% CPU max
            }
        
        summary = {
            "test_execution": {
                "total_scenarios": len(results),
                "total_requests": total_requests,
                "overall_success_rate": overall_success_rate * 100,
                "test_duration_total": sum(
                    (r.end_time - r.start_time).total_seconds() for r in results
                )
            },
            "performance_metrics": {
                "response_times": response_time_stats,
                "throughput": {
                    "max_requests_per_second": max(r.requests_per_second for r in results),
                    "average_requests_per_second": statistics.mean([r.requests_per_second for r in results])
                },
                "system_resources": {
                    "max_cpu_usage": max(r.cpu_usage_avg for r in results),
                    "max_memory_usage": max(r.memory_usage_avg for r in results)
                }
            },
            "benchmark_validation": benchmark_results,
            "detailed_results": [asdict(r) for r in results]
        }
        
        return summary
    
    async def _generate_performance_reports(self, results: List[PerformanceTestResult], 
                                          summary: Dict[str, Any]):
        """Generate performance test reports"""
        # Save detailed JSON report
        report_data = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "detailed_results": [asdict(result) for result in results]
        }
        
        with open("/tmp/performance_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Generate performance charts
        await self._generate_performance_charts(results)
        
        logger.info("Performance reports generated: /tmp/performance_test_report.json")
    
    async def _generate_performance_charts(self, results: List[PerformanceTestResult]):
        """Generate performance visualization charts"""
        try:
            # Response time comparison chart
            scenario_names = [r.scenario_name for r in results]
            avg_response_times = [r.average_response_time for r in results]
            p95_response_times = [r.p95_response_time for r in results]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Average Response Time', x=scenario_names, y=avg_response_times))
            fig.add_trace(go.Bar(name='P95 Response Time', x=scenario_names, y=p95_response_times))
            fig.update_layout(
                title='Response Time Comparison by Scenario',
                xaxis_title='Test Scenarios',
                yaxis_title='Response Time (seconds)',
                barmode='group'
            )
            fig.write_html("/tmp/response_time_comparison.html")
            
            # Throughput vs Error Rate chart
            throughput = [r.requests_per_second for r in results]
            error_rates = [r.error_rate * 100 for r in results]
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=throughput, 
                y=error_rates,
                mode='markers+text',
                text=scenario_names,
                textposition="top center",
                name='Scenarios'
            ))
            fig2.update_layout(
                title='Throughput vs Error Rate',
                xaxis_title='Requests per Second',
                yaxis_title='Error Rate (%)'
            )
            fig2.write_html("/tmp/throughput_vs_error_rate.html")
            
            logger.info("Performance charts generated: /tmp/*.html")
            
        except Exception as e:
            logger.warning(f"Failed to generate performance charts: {e}")

# Locust-based load testing classes
class ContentGenerationUser(HttpUser):
    """Locust user for content generation load testing"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        self.client.headers.update({
            "Authorization": f"Bearer {self.environment.parsed_options.auth_token}",
            "Content-Type": "application/json"
        })
        
        self.payloads = [
            {
                "domain": "finance",
                "source_content": "Market analysis shows significant volatility...",
                "style_parameters": {"tone": "professional", "creativity": 0.7},
                "target_length": 800
            },
            {
                "domain": "sports", 
                "source_content": "Championship game features incredible performances...",
                "style_parameters": {"tone": "engaging", "creativity": 0.8},
                "target_length": 600
            },
            {
                "domain": "technology",
                "source_content": "AI breakthrough promises industry transformation...",
                "style_parameters": {"tone": "technical", "creativity": 0.6},
                "target_length": 1000
            }
        ]
    
    @task(3)
    def generate_content(self):
        """Content generation task"""
        payload = self.payloads[hash(str(self.client)) % len(self.payloads)]
        
        with self.client.post(
            "/api/v1/content/generate",
            json=payload,
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "generated_content" in response_data:
                    response.success()
                else:
                    response.failure("Missing generated content in response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def analyze_quality(self):
        """Quality analysis task"""
        payload = {
            "content": "Sample content for quality analysis testing...",
            "domain": "technology",
            "analysis_options": {
                "check_plagiarism": True,
                "check_patterns": True
            }
        }
        
        with self.client.post(
            "/api/v1/quality/analyze",
            json=payload,
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "overall_score" in response_data:
                    response.success()
                else:
                    response.failure("Missing quality score in response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

def run_locust_load_test(host: str, users: int = 50, spawn_rate: int = 10, 
                        duration: str = "5m", auth_token: str = None) -> Dict[str, Any]:
    """Run Locust-based load test"""
    # Set up Locust environment
    env = Environment(user_classes=[ContentGenerationUser])
    env.create_local_runner()
    
    # Add custom options
    env.parsed_options = type('Options', (), {
        'host': host,
        'users': users,
        'spawn_rate': spawn_rate,
        'run_time': duration,
        'auth_token': auth_token
    })()
    
    # Start load test
    env.runner.start(users, spawn_rate=spawn_rate)
    
    # Run for specified duration
    import time
    duration_seconds = 300  # Default 5 minutes
    if duration.endswith('m'):
        duration_seconds = int(duration[:-1]) * 60
    elif duration.endswith('s'):
        duration_seconds = int(duration[:-1])
    
    time.sleep(duration_seconds)
    
    # Stop test and collect results
    env.runner.stop()
    
    stats = env.runner.stats
    return {
        "total_requests": stats.total.num_requests,
        "total_failures": stats.total.num_failures,
        "average_response_time": stats.total.avg_response_time,
        "min_response_time": stats.total.min_response_time,
        "max_response_time": stats.total.max_response_time,
        "requests_per_second": stats.total.current_rps,
        "failure_rate": stats.total.fail_ratio
    }

# Main performance testing execution
async def main():
    """Main performance testing execution"""
    test_settings = TestSettings()
    
    suite = PerformanceTestSuite(
        base_url=test_settings.API_BASE_URL,
        auth_token=test_settings.AUTH_TOKEN
    )
    
    results = await suite.run_comprehensive_performance_tests()
    
    print("\n" + "="*60)
    print("PERFORMANCE TEST RESULTS SUMMARY")
    print("="*60)
    
    execution_summary = results["test_execution"]
    print(f"Total Scenarios: {execution_summary['total_scenarios']}")
    print(f"Total Requests: {execution_summary['total_requests']}")
    print(f"Success Rate: {execution_summary['overall_success_rate']:.1f}%")
    
    perf_metrics = results["performance_metrics"]
    print(f"\nResponse Times:")
    print(f"  Average: {perf_metrics['response_times']['average']:.3f}s")
    print(f"  P95: {perf_metrics['response_times']['p95']:.3f}s")
    print(f"  P99: {perf_metrics['response_times']['p99']:.3f}s")
    
    print(f"\nThroughput:")
    print(f"  Max RPS: {perf_metrics['throughput']['max_requests_per_second']:.2f}")
    print(f"  Avg RPS: {perf_metrics['throughput']['average_requests_per_second']:.2f}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
import threading
import time

# Thread-safe lists to store sliding windows of observation values
# Limits length to prevent memory consumption issues in long-running processes
MAX_HISTORY = 1000

class MetricsManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.api_latencies = []
        self.task_durations = []
        self.queue_latencies = []
        self.failures = {}

    def record_api_latency(self, endpoint: str, latency: float):
        with self.lock:
            self.api_latencies.append(latency)
            if len(self.api_latencies) > MAX_HISTORY:
                self.api_latencies.pop(0)

    def record_task_duration(self, task_name: str, duration: float):
        with self.lock:
            self.task_durations.append(duration)
            if len(self.task_durations) > MAX_HISTORY:
                self.task_durations.pop(0)

    def record_queue_latency(self, task_name: str, latency: float):
        with self.lock:
            self.queue_latencies.append(latency)
            if len(self.queue_latencies) > MAX_HISTORY:
                self.queue_latencies.pop(0)

    def record_failure(self, failure_type: str):
        with self.lock:
            self.failures[failure_type] = self.failures.get(failure_type, 0) + 1

    def get_summary(self) -> dict:
        with self.lock:
            apis = list(self.api_latencies)
            tasks = list(self.task_durations)
            queues = list(self.queue_latencies)
            fails = dict(self.failures)

        def calculate_p95(vals):
            if not vals:
                return 0.0
            sorted_vals = sorted(vals)
            idx = int(len(sorted_vals) * 0.95)
            idx = min(idx, len(sorted_vals) - 1)
            return round(sorted_vals[idx], 4)

        def calculate_avg(vals):
            if not vals:
                return 0.0
            return round(sum(vals) / len(vals), 4)

        return {
            "api_metrics": {
                "count": len(apis),
                "avg_latency_seconds": calculate_avg(apis),
                "p95_latency_seconds": calculate_p95(apis)
            },
            "task_metrics": {
                "count": len(tasks),
                "avg_duration_seconds": calculate_avg(tasks),
                "p95_duration_seconds": calculate_p95(tasks)
            },
            "queue_metrics": {
                "count": len(queues),
                "avg_latency_seconds": calculate_avg(queues),
                "p95_latency_seconds": calculate_p95(queues)
            },
            "failures": fails
        }

metrics_manager = MetricsManager()

"""
Enhanced logging configuration for the Knowledge Graph system.
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class StructuredLogger:
    """Structured logger for better monitoring and debugging."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create formatter for structured logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def log_event(self, level: str, event_type: str, message: str, 
                  extra_data: Optional[Dict[str, Any]] = None):
        """Log a structured event."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        log_message = f"{event_type}: {message}"
        if extra_data:
            log_message += f" | Data: {json.dumps(extra_data)}"
        
        getattr(self.logger, level.lower())(log_message)
    
    def log_file_processing(self, file_path: str, status: str, 
                           triples_added: int = 0, processing_time: float = 0.0,
                           error: Optional[str] = None):
        """Log file processing events."""
        extra_data = {
            "file_path": file_path,
            "status": status,
            "triples_added": triples_added,
            "processing_time_seconds": round(processing_time, 3)
        }
        
        if error:
            extra_data["error"] = error
        
        level = "error" if status == "failed" else "info"
        self.log_event(level, "file_processing", 
                      f"File {status}: {file_path}", extra_data)
    
    def log_api_request(self, endpoint: str, method: str, status_code: int,
                       response_time: float, client_ip: str = "unknown"):
        """Log API request events."""
        extra_data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_seconds": round(response_time, 3),
            "client_ip": client_ip
        }
        
        level = "error" if status_code >= 400 else "info"
        self.log_event(level, "api_request",
                      f"{method} {endpoint} -> {status_code}", extra_data)
    
    def log_system_metric(self, metric_name: str, value: Any, unit: str = ""):
        """Log system metrics."""
        extra_data = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit
        }
        
        self.log_event("info", "system_metric",
                      f"Metric {metric_name}: {value} {unit}", extra_data)


class MetricsCollector:
    """Collect and track system metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.counters = {}
        self.start_time = time.time()
        
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric."""
        self.counters[name] = self.counters.get(name, 0) + value
    
    def set_gauge(self, name: str, value: Any):
        """Set a gauge metric."""
        self.metrics[name] = {
            "value": value,
            "timestamp": time.time()
        }
    
    def record_timing(self, name: str, duration: float):
        """Record a timing metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "duration": duration,
            "timestamp": time.time()
        })
        
        # Keep only last 100 measurements
        if len(self.metrics[name]) > 100:
            self.metrics[name] = self.metrics[name][-100:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        return {
            "uptime_seconds": time.time() - self.start_time,
            "counters": self.counters.copy(),
            "gauges": {k: v["value"] for k, v in self.metrics.items() 
                      if isinstance(v, dict) and "value" in v},
            "timings_summary": self._get_timing_summaries()
        }
    
    def _get_timing_summaries(self) -> Dict[str, Dict[str, float]]:
        """Get timing summaries (avg, min, max) for timing metrics."""
        summaries = {}
        
        for name, measurements in self.metrics.items():
            if isinstance(measurements, list) and measurements:
                durations = [m["duration"] for m in measurements]
                summaries[name] = {
                    "count": len(durations),
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations)
                }
        
        return summaries

# Global instances
system_logger = StructuredLogger("kg_system")
metrics_collector = MetricsCollector()

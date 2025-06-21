"""
Monitoring and logging utilities for the Football Analytics Predictor.
"""

import logging
import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from contextlib import asynccontextmanager
import psutil
import os


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor application performance metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.start_time = time.time()
    
    def record_request(self, response_time: float, status_code: int):
        """Record a request with its response time and status."""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_count += 1
        
        # Keep only last 1000 response times to prevent memory issues
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        uptime = time.time() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "average_response_time": avg_response_time,
            "requests_per_second": self.request_count / uptime if uptime > 0 else 0
        }


class HealthChecker:
    """Check application health status."""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from app.db import SessionLocal
            session = SessionLocal()
            session.execute("SELECT 1")
            session.close()
            return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}
    
    @staticmethod
    def check_external_api() -> Dict[str, Any]:
        """Check external API connectivity."""
        try:
            from app.fetcher import get_odds_fetcher
            fetcher = get_odds_fetcher()
            if fetcher:
                return {"status": "healthy", "message": "Odds API configured"}
            else:
                return {"status": "warning", "message": "Odds API not configured"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"External API error: {str(e)}"}
    
    @staticmethod
    def check_system_resources() -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "warning"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 80:
                status = "warning"
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 80:
                status = "warning"
                warnings.append(f"High disk usage: {disk.percent}%")
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "warnings": warnings
            }
        except Exception as e:
            return {"status": "unhealthy", "message": f"System check error: {str(e)}"}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        db_health = self.check_database()
        api_health = self.check_external_api()
        system_health = self.check_system_resources()
        
        overall_status = "healthy"
        if any(check["status"] == "unhealthy" for check in [db_health, api_health, system_health]):
            overall_status = "unhealthy"
        elif any(check["status"] == "warning" for check in [db_health, api_health, system_health]):
            overall_status = "warning"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_health,
                "external_api": api_health,
                "system": system_health
            }
        }


class ErrorTracker:
    """Track and log application errors."""
    
    def __init__(self):
        self.errors = []
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log an error with context."""
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        self.errors.append(error_data)
        
        # Keep only last 100 errors to prevent memory issues
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
        
        # Log to file
        logger.error(f"Error occurred: {error_data}")
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors."""
        return self.errors[-limit:]


class RequestLogger:
    """Log HTTP requests and responses."""
    
    @staticmethod
    def log_request(request: Request, response: Response, response_time: float):
        """Log request details."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "response_time": response_time,
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else "unknown"
        }
        
        if response.status_code >= 400:
            logger.warning(f"HTTP {response.status_code}: {log_data}")
        else:
            logger.info(f"HTTP {response.status_code}: {log_data}")


# Global instances
performance_monitor = PerformanceMonitor()
health_checker = HealthChecker()
error_tracker = ErrorTracker()


@asynccontextmanager
async def monitor_request(request: Request):
    """Context manager to monitor request performance."""
    start_time = time.time()
    try:
        yield
    finally:
        response_time = time.time() - start_time
        # This will be used in middleware


def create_monitoring_middleware():
    """Create monitoring middleware for FastAPI."""
    
    async def monitoring_middleware(request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # Record metrics
            performance_monitor.record_request(response_time, response.status_code)
            
            # Log request
            RequestLogger.log_request(request, response, response_time)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Record error
            performance_monitor.record_request(response_time, 500)
            error_tracker.log_error(e, {
                "method": request.method,
                "url": str(request.url),
                "response_time": response_time
            })
            
            raise
    
    return monitoring_middleware


def setup_logging():
    """Set up application logging."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure different loggers for different components
    loggers = {
        "app": logging.getLogger("app"),
        "security": logging.getLogger("security"),
        "database": logging.getLogger("database"),
        "api": logging.getLogger("api")
    }
    
    for name, logger in loggers.items():
        handler = logging.FileHandler(f"logs/{name}.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return loggers

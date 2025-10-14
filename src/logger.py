"""
Logging configuration for Pod Cleaner
"""

import logging
import sys
from typing import Any, Dict
import structlog
from colorama import init as colorama_init
from config import config

# Initialize colorama for cross-platform colored output
colorama_init()


def setup_logging() -> None:
    """Setup structured logging for the application"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if config.log_format == "json" 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.log_level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class PodCleanerLogger:
    """Specialized logger for Pod Cleaner operations"""
    
    def __init__(self):
        self.logger = get_logger("pod-cleaner")
    
    def log_startup(self, config_dict: Dict[str, Any]) -> None:
        """Log application startup"""
        self.logger.info(
            "Pod Cleaner starting up",
            version="1.0.0",
            config=config_dict
        )
    
    def log_cycle_start(self, cycle_id: str) -> None:
        """Log the start of a cleaning cycle"""
        self.logger.info(
            "Starting pod cleaning cycle",
            cycle_id=cycle_id
        )
    
    def log_cycle_end(self, cycle_id: str, cleaned_pods: int, total_checked: int) -> None:
        """Log the end of a cleaning cycle"""
        self.logger.info(
            "Pod cleaning cycle completed",
            cycle_id=cycle_id,
            cleaned_pods=cleaned_pods,
            total_pods_checked=total_checked
        )
    
    def log_pod_cleaned(self, namespace: str, pod_name: str, 
                       previous_state: str, reason: str = None) -> None:
        """Log when a pod is cleaned/restarted"""
        self.logger.info(
            "Pod cleaned/restarted",
            namespace=namespace,
            pod_name=pod_name,
            previous_state=previous_state,
            reason=reason or "Not in healthy state"
        )
    
    def log_pod_skipped(self, namespace: str, pod_name: str, reason: str) -> None:
        """Log when a pod is skipped"""
        self.logger.debug(
            "Pod skipped",
            namespace=namespace,
            pod_name=pod_name,
            reason=reason
        )
    
    def log_error(self, error: Exception, context: str = None) -> None:
        """Log errors with context"""
        self.logger.error(
            "Error occurred",
            error=str(error),
            error_type=type(error).__name__,
            context=context,
            exc_info=True
        )
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warnings"""
        self.logger.warning(message, **kwargs)
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug information"""
        self.logger.debug(message, **kwargs)


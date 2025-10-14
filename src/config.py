"""
Configuration management for Pod Cleaner
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Configuration class for Pod Cleaner"""
    
    # Kubernetes configuration
    kube_config_path: Optional[str] = None
    in_cluster: bool = True
    
    # Namespace configuration
    excluded_namespaces: List[str] = None
    
    # Pod states to monitor (exclude these from cleaning)
    healthy_pod_states: List[str] = None
    
    # Scheduling configuration
    run_interval_minutes: int = 10
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Execution control
    max_concurrent_runs: int = 1
    timeout_seconds: int = 300
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.excluded_namespaces is None:
            self.excluded_namespaces = ["kube-system", "kube-public", "kube-node-lease"]
        
        if self.healthy_pod_states is None:
            self.healthy_pod_states = ["Running", "Init"]
        
        # Override with environment variables if present
        self.kube_config_path = os.getenv("KUBE_CONFIG_PATH", self.kube_config_path)
        self.in_cluster = os.getenv("IN_CLUSTER", str(self.in_cluster)).lower() == "true"
        self.run_interval_minutes = int(os.getenv("RUN_INTERVAL_MINUTES", self.run_interval_minutes))
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_format = os.getenv("LOG_FORMAT", self.log_format)
        self.timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", self.timeout_seconds))
        
        # Parse excluded namespaces from environment
        excluded_env = os.getenv("EXCLUDED_NAMESPACES")
        if excluded_env:
            self.excluded_namespaces = [ns.strip() for ns in excluded_env.split(",")]
        
        # Parse healthy pod states from environment
        healthy_states_env = os.getenv("HEALTHY_POD_STATES")
        if healthy_states_env:
            self.healthy_pod_states = [state.strip() for state in healthy_states_env.split(",")]


# Global configuration instance
config = Config()


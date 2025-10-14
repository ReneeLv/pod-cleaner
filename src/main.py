#!/usr/bin/env python3
"""
Kubernetes Pod Cleaner - Main Application
"""

import os
import time
import logging
import json
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
import os

# Load .env file from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname.lower(),
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'props'):
            log_entry.update(record.props)
            
        return json.dumps(log_entry)

def setup_logging():
    """Setup logging for all modules"""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    
    # Configure root logger
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    
    # Suppress verbose kubernetes client logs
    logging.getLogger('kubernetes').setLevel(logging.WARNING)

def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger('main')
    
    logger.info("Pod Cleaner application starting...")
    
    # Check if we should use mock mode
    if os.getenv('MOCK_MODE', 'false').lower() == 'true':
        logger.info("🔧 Running in MOCK MODE - no actual Kubernetes operations")
    
    try:
        from pod_cleaner import PodCleaner
        
        # Initialize pod cleaner
        cleaner = PodCleaner()
        logger.info("Pod Cleaner initialized successfully")
        
        # Test mode - run once and exit (for local testing)
        if os.getenv('TEST_MODE', 'false').lower() == 'true':
            logger.info("Running in test mode - single execution")
            cleaner.run_cleanup()
            return
        
        # Production mode - run every 10 minutes
        logger.info("Starting main loop (10 minute intervals)")
        
        cycle_count = 0
        while True:
            cycle_count += 1
            logger.info(f"Starting cleanup cycle #{cycle_count}")
            cleaner.run_cleanup()
            
            logger.info("Waiting 10 minutes until next run...")
            interval = int(os.getenv("RUN_INTERVAL_MINUTES", 10)) * 60
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
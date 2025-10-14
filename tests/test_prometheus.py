#!/usr/bin/env python3
"""
Test Prometheus notification functionality
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Prometheus configuration
os.environ['PROMETHEUS_PUSHGATEWAY_URL'] = 'http://localhost:9091'  # 修改为您的 Pushgateway URL
os.environ['PROMETHEUS_JOB_NAME'] = 'kubernetes_pod_cleaner_test'
os.environ['CLUSTER_NAME'] = 'minikube'
os.environ['ENVIRONMENT'] = 'Production'

try:
    from src.notifications import NotificationManager
    print("✅ Successfully imported NotificationManager")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_prometheus_notification():
    """Test Prometheus notification"""
    print("Testing Prometheus notification...")
    
    notification_manager = NotificationManager()
    
    # Test pod info
    pod_info = {
        'namespace': 'default',
        'name': 'test-pod-12345',
        'phase': 'Failed',
        'timestamp': '2024-01-01T12:00:00Z'
    }
    
    error_details = """Pod failed to start after 3 restart attempts.
    
Container Status:
- main-container: CrashLoopBackOff - Error: failed to start container
- init-container: Completed successfully
"""
    
    try:
        success = notification_manager.send_notification(pod_info, error_details, 3)
        if success:
            print("✅ Prometheus notification sent successfully!")
            print("Check your Prometheus/Pushgateway for metrics")
        else:
            print("❌ Failed to send Prometheus notification")
    except Exception as e:
        print(f"❌ Error sending Prometheus notification: {e}")

def test_multiple_notifications():
    """Test multiple Prometheus notifications"""
    print("\nTesting multiple Prometheus notifications...")
    
    notification_manager = NotificationManager()
    
    test_cases = [
        {
            'namespace': 'default',
            'name': 'web-app-pod',
            'phase': 'Failed',
            'error': 'CrashLoopBackOff: Container restarting too frequently',
            'retries': 2
        },
        {
            'namespace': 'production',
            'name': 'database-pod',
            'phase': 'Pending',
            'error': 'ImagePullBackOff: Failed to pull image',
            'retries': 1
        },
        {
            'namespace': 'monitoring',
            'name': 'grafana-pod',
            'phase': 'Unknown',
            'error': 'Node lost connection',
            'retries': 3
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        
        pod_info = {
            'namespace': test_case['namespace'],
            'name': test_case['name'],
            'phase': test_case['phase'],
            'timestamp': '2024-01-01T12:00:00Z'
        }
        
        success = notification_manager.send_notification(
            pod_info, 
            test_case['error'], 
            test_case['retries']
        )
        
        if success:
            print(f"✅ Prometheus notification for {test_case['namespace']}/{test_case['name']} sent successfully")
        else:
            print(f"❌ Failed to send Prometheus notification for {test_case['namespace']}/{test_case['name']}")

if __name__ == "__main__":
    test_prometheus_notification()
    test_multiple_notifications()
    print("\n🎉 Prometheus notification tests completed!")
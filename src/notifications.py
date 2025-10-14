"""
Notification system for pod restart failures - Prometheus only
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.sent_notifications = {}
        self.notification_cooldown = timedelta(minutes=30)
        
    def send_notification(self, pod_info, error_details, retry_count=0):
        """Send notification about failed pod restart - Prometheus only"""
        pod_key = f"{pod_info['namespace']}/{pod_info['name']}"
        
        last_notification = self.sent_notifications.get(pod_key)
        if last_notification and datetime.now() - last_notification < self.notification_cooldown:
            logger.debug(f"Notification for {pod_key} is in cooldown")
            return False
        
        try:
            return self._send_prometheus_alert(pod_info, error_details, retry_count)
            
        except Exception as e:
            logger.error(f"Failed to send notification for {pod_key}: {e}")
            return self._send_log_notification(pod_info, error_details, retry_count)
    
    def _send_log_notification(self, pod_info, error_details, retry_count):
        """Log-based notification (fallback)"""
        logger.error(
            f" POD RESTART FAILED - {pod_info['namespace']}/{pod_info['name']}\n"
            f"   Phase: {pod_info.get('phase', 'Unknown')}\n"
            f"   Error: {error_details}\n"
            f"   Retry Count: {retry_count}\n"
            f"   Timestamp: {datetime.utcnow().isoformat()}Z"
        )
        return True
    
    def _send_prometheus_alert(self, pod_info, error_details, retry_count):
        """Send alert to Prometheus"""
        try:
            
            prometheus_url = os.getenv('PROMETHEUS_PUSHGATEWAY_URL')
            job_name = os.getenv('PROMETHEUS_JOB_NAME', 'kubernetes_pod_cleaner')
            
            if prometheus_url:
                self._push_to_pushgateway(prometheus_url, job_name, pod_info, error_details, retry_count)
            else:
                self._update_prometheus_metrics(pod_info, error_details, retry_count)
            
            logger.info(f"📊 Prometheus alert sent for {pod_info['namespace']}/{pod_info['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Prometheus alert: {e}")
            # Fall back to log notification
            return self._send_log_notification(pod_info, error_details, retry_count)
    
    def _push_to_pushgateway(self, pushgateway_url, job_name, pod_info, error_details, retry_count):
        """Push metrics to Prometheus Pushgateway"""
        try:
            import requests
            
            metrics_data = f"""# HELP pod_cleaner_restart_failure Pod restart failure event
# TYPE pod_cleaner_restart_failure gauge
pod_cleaner_restart_failure{{namespace="{pod_info['namespace']}",pod="{pod_info['name']}",phase="{pod_info.get('phase', 'Unknown')}",cluster="{os.getenv('CLUSTER_NAME', 'Unknown')}"}} 1

# HELP pod_cleaner_retry_count Number of retry attempts for failed pod
# TYPE pod_cleaner_retry_count gauge
pod_cleaner_retry_count{{namespace="{pod_info['namespace']}",pod="{pod_info['name']}"}} {retry_count}

# HELP pod_cleaner_last_failure_timestamp Timestamp of last pod failure
# TYPE pod_cleaner_last_failure_timestamp gauge
pod_cleaner_last_failure_timestamp{{namespace="{pod_info['namespace']}",pod="{pod_info['name']}"}} {datetime.utcnow().timestamp()}
"""
            
            # Push to Pushgateway
            url = f"{pushgateway_url}/metrics/job/{job_name}"
            response = requests.put(url, data=metrics_data, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Successfully pushed metrics to Pushgateway for {pod_info['namespace']}/{pod_info['name']}")
            
        except ImportError:
            logger.warning("requests library not available, cannot push to Pushgateway")
        except Exception as e:
            logger.error(f"Failed to push to Pushgateway: {e}")
            raise
    
    def _update_prometheus_metrics(self, pod_info, error_details, retry_count):
        """Update Prometheus metrics directly (if using client library)"""
        try:
            from prometheus_client import Counter, Gauge, Histogram
            
            pod_restart_failures = Counter(
                'pod_cleaner_restart_failures_total',
                'Total number of pod restart failures',
                ['namespace', 'pod_name', 'phase']
            )
            
            pod_retry_count = Gauge(
                'pod_cleaner_retry_count',
                'Current retry count for pod',
                ['namespace', 'pod_name']
            )
            
            pod_restart_failures.labels(
                namespace=pod_info['namespace'],
                pod_name=pod_info['name'],
                phase=pod_info.get('phase', 'Unknown')
            ).inc()
            
            pod_retry_count.labels(
                namespace=pod_info['namespace'],
                pod_name=pod_info['name']
            ).set(retry_count)
            
            logger.debug(f"Updated Prometheus metrics for {pod_info['namespace']}/{pod_info['name']}")
            
        except ImportError:
            logger.warning("prometheus_client not available, using Pushgateway method")
        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")
            raise
    
    def check_pod_health_after_restart(self, pod_info, k8s_client, check_interval=60, max_checks=5):
        """Check if pod is healthy after restart"""
        logger.info(f"Monitoring pod {pod_info['namespace']}/{pod_info['name']} after restart")
        
        for check_count in range(max_checks):
            # Wait before checking
            import time
            time.sleep(check_interval)
            
            try:
                # Get the current state of the pod
                current_pod = self._get_pod(pod_info['namespace'], pod_info['name'], k8s_client)
                
                if not current_pod:
                    logger.warning(f"Pod {pod_info['namespace']}/{pod_info['name']} not found after restart")
                    continue
                
                if self._is_pod_healthy(current_pod):
                    logger.info(f"✅ Pod {pod_info['namespace']}/{pod_info['name']} is healthy after restart")
                    return True
                else:
                    logger.warning(f"⚠️ Pod {pod_info['namespace']}/{pod_info['name']} still not healthy (check {check_count + 1}/{max_checks})")
                    
            except Exception as e:
                logger.error(f"Error checking pod health for {pod_info['namespace']}/{pod_info['name']}: {e}")
        
        # If we get here, the pod never became healthy
        error_details = f"Pod failed to become healthy after {max_checks} checks over {max_checks * check_interval} seconds"
        self.send_notification(pod_info, error_details, max_checks)
        return False
    
    def _get_pod(self, namespace, name, k8s_client):
        """Get pod by namespace and name"""
        try:
            return k8s_client.v1.read_namespaced_pod(name=name, namespace=namespace)
        except Exception as e:
            logger.debug(f"Could not find pod {namespace}/{name}: {e}")
            return None
    
    def _is_pod_healthy(self, pod):
        """Check if pod is in healthy state"""
        if pod.status.phase != "Running":
            return False
        
        # Check container statuses
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if not container_status.ready:
                    return False
                if container_status.state and (container_status.state.waiting or container_status.state.terminated):
                    return False
        
        return True
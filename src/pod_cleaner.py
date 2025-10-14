import os
import time
import logging
from datetime import datetime
from threading import Lock
from kubernetes_client import KubernetesClient
from notifications import NotificationManager

logger = logging.getLogger(__name__)

class PodCleaner:
    def __init__(self):
        # Determine if we should use mock mode
        use_mock = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
        self.k8s_client = KubernetesClient(use_mock=use_mock)
        self.notification_manager = NotificationManager()
        self.cleaned_pods = []
        self.lock = Lock()
        self.is_running = False
        self.use_mock = use_mock
        
        # Performance optimization - cache for large clusters
        self.pod_cache = {}
        self.cache_ttl = 300  # 5 minutes

    def should_clean_pod(self, pod):
        """Check if pod should be restarted with caching for performance"""
        cache_key = f"{pod.metadata.namespace}/{pod.metadata.name}"
        
        # Check cache first (for large clusters)
        if cache_key in self.pod_cache:
            cached_result, cached_time = self.pod_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_result
        
        # Skip kube-system namespace
        if pod.metadata.namespace == 'kube-system':
            self.pod_cache[cache_key] = (False, time.time())
            return False
        
        phase = pod.status.phase
        
        # Allow Running pods
        if phase == 'Running':
            self.pod_cache[cache_key] = (False, time.time())
            return False
            
        # Allow Pending pods that are in init phase
        if phase == 'Pending':
            # Check init container statuses
            init_statuses = pod.status.init_container_statuses or []
            for init_status in init_statuses:
                if init_status.state:
                    if init_status.state.running:
                        self.pod_cache[cache_key] = (False, time.time())
                        return False  # Still in init phase
                    if (init_status.state.terminated and 
                        not init_status.state.terminated.exit_code == 0):
                        self.pod_cache[cache_key] = (False, time.time())
                        return False  # Init container failed but still in init phase
            
            # Check for container creating state
            container_statuses = pod.status.container_statuses or []
            for status in container_statuses:
                if status.state and status.state.waiting:
                    if status.state.waiting.reason in ['PodInitializing', 'ContainerCreating']:
                        self.pod_cache[cache_key] = (False, time.time())
                        return False  # Still initializing
            
            # If we get here, it's a Pending pod that's not in init - should be cleaned
            self.pod_cache[cache_key] = (True, time.time())
            return True
        
        # Clean Failed, Succeeded, Unknown, and other states
        self.pod_cache[cache_key] = (True, time.time())
        return True

    def clean_pod(self, pod):
        """Clean (restart) a pod by deleting it and monitor health"""
        try:
            logger.info(f"Cleaning pod {pod.metadata.namespace}/{pod.metadata.name} (Phase: {pod.status.phase})")
            
            # Store pod info for monitoring
            pod_info = {
                'namespace': pod.metadata.namespace,
                'name': pod.metadata.name,
                'phase': pod.status.phase,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            success = self.k8s_client.delete_pod(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace
            )
            
            if success:
                self.cleaned_pods.append(pod_info)
                
                # Monitor pod health after restart (async - don't wait for completion)
                if os.getenv('ENABLE_HEALTH_CHECKS', 'true').lower() == 'true':
                    self._monitor_pod_health_async(pod_info)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to clean pod {pod.metadata.namespace}/{pod.metadata.name}: {e}")
            return False

    def _monitor_pod_health_async(self, pod_info):
        """Monitor pod health asynchronously after restart"""
        import threading
        
        def monitor():
            try:
                healthy = self.notification_manager.check_pod_health_after_restart(
                    pod_info, 
                    self.k8s_client,
                    check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
                    max_checks=int(os.getenv('MAX_HEALTH_CHECKS', '3'))
                )
                if not healthy:
                    logger.error(f"Pod {pod_info['namespace']}/{pod_info['name']} failed to recover after restart")
            except Exception as e:
                logger.error(f"Error monitoring pod health: {e}")
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def run_cleanup(self):
        """Run one cleanup cycle with performance optimizations"""
        with self.lock:
            if self.is_running:
                logger.info("Previous run still in progress, skipping...")
                return
            
            self.is_running = True
            self.cleaned_pods = []
        
        try:
            start_time = time.time()
            logger.info("Starting pod cleanup cycle...")
            
            # Get all pods (with performance optimization for large clusters)
            pods = self._get_pods_optimized()
            
            if self.use_mock:
                # Generate mock pods for testing
                pods = self._generate_mock_pods()
                logger.info(f"Mock mode - testing with {len(pods)} mock pods")
            else:
                logger.info(f"Found {len(pods)} total pods")
            
            # Filter out kube-system and check pod states
            target_pods = [pod for pod in pods if pod.metadata.namespace != 'kube-system']
            
            if not self.use_mock:
                logger.info(f"Checking {len(target_pods)} pods (excluding kube-system)")
            
            # Check and clean problematic pods
            cleaned_count = 0
            for pod in target_pods:
                if self.should_clean_pod(pod):
                    if self.clean_pod(pod):
                        cleaned_count += 1
            
            # Log results
            execution_time = time.time() - start_time
            self.log_results(cleaned_count, execution_time)
            
            # Clear cache periodically
            self._clean_old_cache_entries()
            
        except Exception as e:
            logger.error(f"Error during cleanup cycle: {e}")
        finally:
            with self.lock:
                self.is_running = False

    def _get_pods_optimized(self):
        """Optimized pod retrieval for large clusters"""
        try:
            # Use field selector to only get non-running pods (major performance boost)
            field_selector = "status.phase!=Running"
            pods = self.k8s_client.v1.list_pod_for_all_namespaces(
                watch=False,
                field_selector=field_selector
            )
            logger.info(f"Retrieved {len(pods.items)} non-running pods using field selector")
            return pods.items
            
        except Exception as e:
            logger.warning(f"Field selector failed, falling back to full list: {e}")
            # Fallback to full list if field selector fails
            return self.k8s_client.list_all_pods()

    def _clean_old_cache_entries(self):
        """Remove old entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.pod_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.pod_cache[key]
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")

    def log_results(self, cleaned_count, execution_time):
        """Log all cleaned pods at the end of the run"""
        logger.info("=== CLEANUP SUMMARY ===")
        
        if self.use_mock:
            logger.info("MOCK MODE - No actual pods were cleaned")
            logger.info(f"Would have cleaned {cleaned_count} pods in this cycle")
        else:
            logger.info(f"Cleaned {cleaned_count} pods in this cycle")
            logger.info(f"Execution time: {execution_time:.2f} seconds")
        
        if self.cleaned_pods:
            logger.info("Cleaned pods:")
            for pod_info in self.cleaned_pods:
                logger.info(
                    f"  - {pod_info['namespace']}/{pod_info['name']} "
                    f"(Phase: {pod_info['phase']}) at {pod_info['timestamp']}"
                )
        else:
            logger.info("No pods were cleaned in this cycle")
        
        logger.info("=== END SUMMARY ===")

    def _generate_mock_pods(self):
        """Generate mock pods for testing"""
        from unittest.mock import Mock
        
        mock_pods = []
        states = ['Running', 'Failed', 'Pending', 'Succeeded', 'Unknown']
        namespaces = ['default', 'app-namespace', 'test-namespace']
        
        for i, state in enumerate(states):
            pod = Mock()
            pod.metadata.namespace = namespaces[i % len(namespaces)]
            pod.metadata.name = f"mock-pod-{i}-{state.lower()}"
            pod.status.phase = state
            pod.status.init_container_statuses = []
            pod.status.container_statuses = []
            
            mock_pods.append(pod)
        
        return mock_pods
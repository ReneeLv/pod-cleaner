import os
import time
import logging
from datetime import datetime
from threading import Lock
from kubernetes_client import KubernetesClient

logger = logging.getLogger(__name__)

class PodCleaner:
    def __init__(self):
        # Determine if we should use mock mode
        use_mock = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
        self.k8s_client = KubernetesClient(use_mock=use_mock)
        self.cleaned_pods = []
        self.lock = Lock()
        self.is_running = False
        self.use_mock = use_mock

    def should_clean_pod(self, pod):
        """Check if pod should be restarted"""
        # Skip kube-system namespace
        if pod.metadata.namespace == 'kube-system':
            return False
        
        phase = pod.status.phase
        
        # Allow Running pods
        if phase == 'Running':
            return False
            
        # Allow Pending pods that are in init phase
        if phase == 'Pending':
            # Check init container statuses
            init_statuses = pod.status.init_container_statuses or []
            for init_status in init_statuses:
                if init_status.state:
                    if init_status.state.running:
                        return False  # Still in init phase
                    if (init_status.state.terminated and 
                        not init_status.state.terminated.exit_code == 0):
                        return False  # Init container failed but still in init phase
            
            # Check for container creating state
            container_statuses = pod.status.container_statuses or []
            for status in container_statuses:
                if status.state and status.state.waiting:
                    if status.state.waiting.reason in ['PodInitializing', 'ContainerCreating']:
                        return False  # Still initializing
            
            # If we get here, it's a Pending pod that's not in init - should be cleaned
            return True
        
        # Clean Failed, Succeeded, Unknown, and other states
        return True

    def clean_pod(self, pod):
        """Clean (restart) a pod by deleting it"""
        try:
            logger.info(f"Cleaning pod {pod.metadata.namespace}/{pod.metadata.name} (Phase: {pod.status.phase})")
            
            success = self.k8s_client.delete_pod(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace
            )
            
            if success:
                pod_info = {
                    'namespace': pod.metadata.namespace,
                    'name': pod.metadata.name,
                    'phase': pod.status.phase,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                self.cleaned_pods.append(pod_info)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to clean pod {pod.metadata.namespace}/{pod.metadata.name}: {e}")
            return False

    def run_cleanup(self):
        """Run one cleanup cycle"""
        with self.lock:
            if self.is_running:
                logger.info("Previous run still in progress, skipping...")
                return
            
            self.is_running = True
            self.cleaned_pods = []
        
        try:
            logger.info("Starting pod cleanup cycle...")
            
            # Get all pods
            pods = self.k8s_client.list_all_pods()
            
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
            self.log_results(cleaned_count)
            
        except Exception as e:
            logger.error(f"Error during cleanup cycle: {e}")
        finally:
            with self.lock:
                self.is_running = False

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
            
            # Add some init container status for Pending pods
            if state == 'Pending' and i % 2 == 0:
                init_status = Mock()
                init_status.state = Mock()
                init_status.state.running = Mock()
                pod.status.init_container_statuses = [init_status]
            
            mock_pods.append(pod)
        
        return mock_pods

    def log_results(self, cleaned_count):
        """Log all cleaned pods at the end of the run"""
        logger.info("=== CLEANUP SUMMARY ===")
        
        if self.use_mock:
            logger.info("MOCK MODE - No actual pods were cleaned")
            logger.info(f"Would have cleaned {cleaned_count} pods in this cycle")
        else:
            logger.info(f"Cleaned {cleaned_count} pods in this cycle")
        
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

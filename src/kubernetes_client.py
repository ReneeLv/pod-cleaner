import os
import logging
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

logger = logging.getLogger(__name__)

class KubernetesClient:
    def __init__(self, use_mock=False):
        self.v1 = None
        self.client = client
        
        if use_mock:
            logger.info("Using mock mode - no real Kubernetes connection")
            return
            
        try:
            # First, try to load from environment variable if set
            kubeconfig_path = os.getenv('KUBECONFIG')
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                logger.info(f"Loading kubeconfig from KUBECONFIG environment: {kubeconfig_path}")
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                # Try multiple configuration methods
                try:
                    # Method 1: Try in-cluster config (when running in Kubernetes)
                    config.load_incluster_config()
                    logger.info("Loaded in-cluster Kubernetes configuration")
                except ConfigException:
                    # Method 2: Try default kubeconfig location
                    try:
                        config.load_kube_config()
                        logger.info("Loaded kubeconfig from default location")
                    except ConfigException:
                        # Method 3: Try common kubeconfig paths
                        possible_paths = [
                            os.path.expanduser("~/.kube/config"),
                            "/etc/kubernetes/admin.conf",
                            "/etc/rancher/k3s/k3s.yaml"
                        ]
                        
                        for kube_path in possible_paths:
                            if os.path.exists(kube_path):
                                logger.info(f"Loading kubeconfig from: {kube_path}")
                                config.load_kube_config(config_file=kube_path)
                                break
                        else:
                            # If all methods fail, provide helpful error message
                            raise Exception(
                                "Could not load Kubernetes configuration. "
                                "Please ensure you have:\n"
                                "1. A running Kubernetes cluster\n"
                                "2. kubectl configured properly\n"
                                "3. Or set KUBECONFIG environment variable\n"
                                "4. Or run with MOCK_MODE=true for testing"
                            )
            
            self.v1 = client.CoreV1Api()
            
            # Test the connection
            try:
                self.v1.get_api_resources()
                logger.info("✅ Kubernetes client initialized successfully")
            except Exception as e:
                logger.warning(f"Kubernetes connection test failed: {e}")
                logger.info("Continuing with limited functionality...")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def list_all_pods(self):
        """List all pods from all namespaces"""
        if not self.v1:
            logger.warning("Mock mode - returning empty pod list")
            return []
            
        try:
            pods = self.v1.list_pod_for_all_namespaces(watch=False)
            return pods.items
        except Exception as e:
            logger.error(f"Failed to list pods: {e}")
            return []

    def delete_pod(self, name, namespace):
        """Delete a pod"""
        if not self.v1:
            logger.warning(f"Mock mode - would delete pod {namespace}/{name}")
            return True
            
        try:
            self.v1.delete_namespaced_pod(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy='Foreground')
            )
            logger.info(f"✅ Successfully deleted pod {namespace}/{name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete pod {namespace}/{name}: {e}")
            return False

    def test_connection(self):
        """Test Kubernetes connection"""
        if not self.v1:
            return False
        try:
            self.v1.get_api_resources()
            return True
        except Exception:
            return False
#!/usr/bin/env python3
"""
Test script for local development
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# from src import kubernetes_client 
from src.kubernetes_client import KubernetesClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_kubernetes_connection():
    """Test Kubernetes connection"""
    try:
        client = KubernetesClient()
        print("✅ Kubernetes connection successful!")
        
        # Test listing pods
        pods = client.list_all_pods()
        print(f"✅ Found {len(pods)} pods in cluster")
        
        # Show namespaces
        namespaces = set(pod.metadata.namespace for pod in pods)
        print(f"✅ Namespaces: {', '.join(sorted(namespaces))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Kubernetes connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Docker Desktop is running with Kubernetes enabled")
        print("2. Run: kubectl cluster-info")
        print("3. Run: kubectl get pods --all-namespaces")
        print("4. Check if ~/.kube/config exists")
        return False

if __name__ == "__main__":
    test_kubernetes_connection()
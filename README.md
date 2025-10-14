# Pod Cleaner

A Kubernetes-native application that monitors and automatically restarts pods that are not in healthy states (Running or Init).

## 🎯 Features

- **Automatic Pod Monitoring**: Scans all namespaces (except excluded ones) for unhealthy pods
- **Smart Pod Restart**: Only restarts pods managed by controllers (Deployments, StatefulSets, etc.)
- **Configurable Scheduling**: Runs every 10 minutes by default (configurable)
- **Comprehensive Logging**: Structured logging with JSON output for production
- **Safety Features**: 
  - Excludes system namespaces (kube-system, etc.)
  - Skips pods with special annotations
  - Prevents cleaning pods that are too young
  - Only runs one cleaning cycle at a time
- **Kubernetes Native**: Designed to run as a Kubernetes deployment with proper RBAC

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pod Cleaner   │────│  Kubernetes API  │────│  Target Pods    │
│   Application   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │   RBAC Rules    │              │
         │              │  - list pods    │              │
         │              │  - delete pods  │              │
         │              │  - list namespaces│            │
         │              └─────────────────┘              │
         │                                               │
         └─────────────── Restart Pods ──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Docker (for building)

### Kubernetes Deployment

1. **Build and deploy**:
   ```bash
   make build-and-deploy
   ```

2. **Check status**:
   ```bash
   make status
   make logs
   ```

3. **Undeploy**:
   ```bash
   make undeploy
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IN_CLUSTER` | `true` | Run in Kubernetes cluster |
| `KUBE_CONFIG_PATH` | - | Path to kubeconfig (outside cluster) |
| `EXCLUDED_NAMESPACES` | `kube-system` | Comma-separated namespaces to skip |
| `HEALTHY_POD_STATES` | `Running,Init` | Pod states considered healthy |
| `RUN_INTERVAL_MINUTES` | `10` | Minutes between cleaning cycles |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format (json/console) |
| `TIMEOUT_SECONDS` | `300` | Operation timeout |

### Kubernetes ConfigMap

The application can also be configured via Kubernetes ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pod-cleaner-config
data:
  config.yaml: |
    excluded_namespaces:
      - "kube-system"
    healthy_pod_states:
      - "Running"
      - "Init"
    run_interval_minutes: 10
```

## 🔧 How It Works

### Pod Selection Logic

The application identifies pods for cleaning based on these criteria:

1. **Namespace**: Excludes system namespaces (configurable)
2. **Pod State**: Only processes pods NOT in "Running" or "Init" states
3. **Management**: Only processes pods with owner references (managed by controllers)
4. **Age**: Skips pods younger than 5 minutes (prevents cleaning starting pods)
5. **Annotations**: Skips pods with `pod-cleaner.kubernetes.io/skip=true`

### Cleaning Process

1. **Scan**: Lists all namespaces and pods
2. **Filter**: Applies selection criteria
3. **Clean**: Deletes unhealthy pods (controllers will recreate them)
4. **Log**: Records all cleaning actions

### Safety Mechanisms

- **Single Execution**: Only one cleaning cycle runs at a time
- **Graceful Shutdown**: Handles SIGTERM/SIGINT properly
- **Error Handling**: Continues operation even if individual pods fail
- **Resource Limits**: CPU and memory limits defined in deployment

## 📊 Monitoring

### Logs

The application provides structured JSON logs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "message": "Pod cleaned/restarted",
  "namespace": "default",
  "pod_name": "unhealthy-app-123",
  "previous_state": "Pending",
  "reason": "Not in healthy state"
}
```

### Metrics

Monitor the pod cleaner deployment:

```bash
# Check deployment status
kubectl get deployment pod-cleaner

# View logs
kubectl logs -f deployment/pod-cleaner

# Check resource usage
kubectl top pod -l app=pod-cleaner
```

## 🛡️ Security

### RBAC Permissions

The application requires minimal permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-cleaner
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "delete"]
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list"]
```

### Security Context(only use if no user specific in Dockerfile)

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privileged access
- Minimal container image (python:3.11-slim)


## 🔨 Development

### Project Structure

```
pod-cleaner/
├── src/                   # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   ├── kubernetes_client.py # K8s API wrapper
│   ├── pod_cleaner.py     # Main logic
│   ├── test_local.py      # Local test k8s connection
│   └── main.py            # Entry point
├── k8s/                   # Kubernetes manifests
├── Dockerfile             # Container build
├── Makefile               # Build commands
└── requirements.txt       # Dependencies
```

## Debug

- Check logs: `make logs`
- View status: `make status`
- Test locally: `make run-local`

## How to handle the large kubernetes cluster with tens of thousands of pods

* Concurrent processing pod
* handle the pod with different priority: high, middle, low, ignore
* batch processing by namespace


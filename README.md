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
         │              │  - list namespaces│             │
         │              └─────────────────┘              │
         │                                               │
         └─────────────── Restart Pods ──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Docker (for building)

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd pod-cleaner
   make dev-setup
   ```

2. **Configure**:
   ```bash
   cp env.example .env
   # Edit .env as needed
   ```

3. **Run locally** (requires kubeconfig):
   ```bash
   make run-local
   ```

4. **Run tests**:
   ```bash
   make test
   ```

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
| `EXCLUDED_NAMESPACES` | `kube-system,kube-public,kube-node-lease` | Comma-separated namespaces to skip |
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
      - "kube-public"
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

### Security Context

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privileged access
- Minimal container image (python:3.11-slim)

## 🧪 Testing

### Unit Tests

```bash
make test
```

### Integration Tests

```bash
# Run against a test cluster
make run-local
```

### Test Coverage

```bash
make test-cov
```

## 🔨 Development

### Project Structure

```
pod-cleaner/
├── src/                    # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   ├── kubernetes_client.py # K8s API wrapper
│   ├── pod_cleaner.py     # Main logic
│   └── main.py           # Entry point
├── tests/                 # Test code
├── k8s/                   # Kubernetes manifests
├── Dockerfile            # Container build
├── Makefile              # Build commands
└── requirements.txt      # Dependencies
```

### Adding Features

1. **New Logic**: Add to `src/pod_cleaner.py`
2. **Configuration**: Extend `src/config.py`
3. **Tests**: Add to `tests/`
4. **Documentation**: Update this README

### Code Quality

```bash
make format    # Format code
make lint      # Check style
make check     # Full check
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make check`
5. Submit a pull request

## 🆘 Troubleshooting

### Common Issues

**Pod Cleaner not starting**:
- Check RBAC permissions
- Verify service account exists
- Check logs: `kubectl logs deployment/pod-cleaner`

**Pods not being cleaned**:
- Verify pod has owner references
- Check if pod is in excluded namespace
- Confirm pod state is not Running/Init
- Check pod age (must be > 5 minutes)

**Permission denied errors**:
- Verify ClusterRole and ClusterRoleBinding
- Check service account configuration

### Debug Mode

Run with debug logging:

```bash
kubectl set env deployment/pod-cleaner LOG_LEVEL=DEBUG
```

### Support

- Check logs: `make logs`
- View status: `make status`
- Test locally: `make run-local`


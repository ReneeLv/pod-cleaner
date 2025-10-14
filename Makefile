# Pod Cleaner Makefile

	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-deps:  ## Install Python dependencies
	pip3 install -r requirements.txt
	eval $(minikube docker-env)

build:  ## Build Docker image
	docker build -t pod-cleaner:latest .
	minikube image load pod-cleaner:latest

run-local:  ## Run locally (requires kubeconfig)
	python3 src/main.py

run-dev:  ## Run in development mode
	IN_CLUSTER=false LOG_FORMAT=console python -m src.main

deploy:  ## Deploy to Kubernetes
	kubectl apply -f k8s/rbac.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/deployment.yaml

undeploy:  ## Remove from Kubernetes
	kubectl delete -f k8s/deployment.yaml
	kubectl delete -f k8s/configmap.yaml
	kubectl delete -f k8s/rbac.yaml

logs:  ## View pod cleaner logs
	kubectl logs -f deployment/pod-cleaner

status:  ## Check deployment status
	kubectl get pods -l app=pod-cleaner
	kubectl get deployment pod-cleaner

test:  ## Run tests
	python3 test/test_local.py
	python3 test/test_prometheus.py

clean:  ## Clean temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/

# Pod Cleaner Makefile

.PHONY: help build test lint format clean deploy run-local install-deps

help:  ## Show help information
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-deps:  ## Install Python dependencies
	pip install -r requirements.txt

build:  ## Build Docker image
	docker build -t pod-cleaner:latest .

build-local:  ## Build for local testing
	docker build -t pod-cleaner:local .

test:  ## Run tests
	python -m pytest tests/ -v

test-cov:  ## Run tests with coverage
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:  ## Run linting
	flake8 src/ tests/
	mypy src/

format:  ## Format code
	black src/ tests/

format-check:  ## Check code formatting
	black --check src/ tests/

clean:  ## Clean temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/

run-local:  ## Run locally (requires kubeconfig)
	python -m src.main

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

check: format-check lint test  ## Full check (format, lint, test)

dev-setup:  ## Setup development environment
	pip install -r requirements.txt
	cp env.example .env

docker-dev:  ## Run in Docker for development
	docker run --rm -it \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/.env:/app/.env \
		-v ~/.kube/config:/home/podcleaner/.kube/config \
		-e IN_CLUSTER=false \
		-e KUBE_CONFIG_PATH=/home/podcleaner/.kube/config \
		pod-cleaner:local

build-and-deploy: build deploy  ## Build and deploy

all: clean install-deps test lint build  ## Run all checks and build


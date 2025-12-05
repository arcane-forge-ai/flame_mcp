# Flame MCP Server - Build and Deployment Makefile
# =================================================

# Variables
REGISTRY := arcaneforgedev.azurecr.io
REPO := arcaneforge/flame-mcp
IMAGE_NAME := $(REGISTRY)/$(REPO)
LOCAL_IMAGE := flame-mcp-server
DATE_TAG := $(shell powershell -Command "Get-Date -Format 'yyyyMMdd-HHmmss'")
LATEST_TAG := latest
NAMESPACE := mcp
HELM_RELEASE := flame-mcp-server

# Allow user to override the tag
TAG ?= $(DATE_TAG)

# Docker Build Variables
BUILD_DATE := $(shell powershell -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'")
VCS_REF := $(shell git rev-parse --short HEAD)

# Default target
.PHONY: help
help: ## Show this help message
	@echo "Flame MCP Server - Available Commands:"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Build Commands
.PHONY: build
build: ## Build Docker image locally (latest tag)
	@echo "[BUILD] Building local Docker image..."
	docker build \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg VCS_REF="$(VCS_REF)" \
		--build-arg VERSION="$(TAG)" \
		-t $(LOCAL_IMAGE):$(LATEST_TAG) \
		.
	@echo "[BUILD] Local build complete: $(LOCAL_IMAGE):$(LATEST_TAG)"

.PHONY: build-acr
build-acr: ## Build Docker image for ACR (date tag + latest, override with TAG=mytag)
	@echo "[BUILD] Building Docker image for ACR..."
	@echo "[BUILD] Using tag: $(TAG)"
	docker build \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg VCS_REF="$(VCS_REF)" \
		--build-arg VERSION="$(TAG)" \
		-t $(IMAGE_NAME):$(TAG) \
		-t $(IMAGE_NAME):$(LATEST_TAG) \
		.
	@echo "[BUILD] ACR build complete: $(IMAGE_NAME):$(TAG)"

.PHONY: login-acr
login-acr: ## Login to Azure Container Registry
	@echo "[AUTH] Logging into Azure Container Registry..."
	az acr login --name arcaneforgedev
	@echo "[AUTH] ACR login successful"

.PHONY: push
push: ## Push Docker image to ACR (specify TAG=yourtag)
ifndef TAG
	@echo "[ERROR] Please specify TAG=yourtag (e.g., make push TAG=20241217-143022)"
	@exit 1
endif
	@echo "[PUSH] Pushing to Azure Container Registry..."
	@echo "[PUSH] Tag: $(TAG)"
	docker push $(IMAGE_NAME):$(TAG)
	docker push $(IMAGE_NAME):$(LATEST_TAG)
	@echo "[PUSH] Push complete: $(IMAGE_NAME):$(TAG)"

# Helm Commands
.PHONY: helm-template
helm-template: ## Generate Helm template output for review
	@echo "[HELM] Generating Helm templates..."
	helm template test-release ./helm/ --dry-run -f ./helm/values-dev-with-secrets.yaml > ./helm/rendered.yaml
	@echo "[HELM] Templates generated: ./helm/rendered.yaml"

.PHONY: helm-install-dev
helm-install-dev: ## Install Helm release
	@echo "[HELM] Installing Helm release..."
	helm install $(HELM_RELEASE) ./helm/ -f ./helm/values-dev-with-secrets.yaml -n $(NAMESPACE)
	@echo "[HELM] Install complete" 

.PHONY: helm-upgrade-dev
helm-upgrade-dev: ## Upgrade Helm release
	@echo "[HELM] Upgrading Helm release..."
	helm upgrade $(HELM_RELEASE) ./helm/ -f ./helm/values-dev-with-secrets.yaml -n $(NAMESPACE)
	@echo "[HELM] Upgrade complete" 
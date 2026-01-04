# Flame MCP Server - Build and Deployment Makefile
# =================================================

# Variables
# Azure Container Registry
REGISTRY := arcaneforgedev.azurecr.io
REPO := arcaneforge/flame-mcp
IMAGE_NAME := $(REGISTRY)/$(REPO)
LOCAL_IMAGE := flame-mcp-server
DATE_TAG := $(shell powershell -Command "Get-Date -Format 'yyyyMMdd-HHmmss'")
LATEST_TAG := latest
NAMESPACE := mcp
HELM_RELEASE := flame-mcp-server

# GCP Variables (update these for your GCP project)
GCP_PROJECT ?= arcane-forge-dev
GCP_REGION ?= us-central1
GCP_REGISTRY := $(GCP_REGION)-docker.pkg.dev
GCP_REPO := $(GCP_PROJECT)/arcane-forge-dev/flame-mcp-server
GCP_IMAGE_NAME := $(GCP_REGISTRY)/$(GCP_REPO)
GCP_CLUSTER ?= arcane-forge-dev-autopilot-1
GCP_NAMESPACE := mcp
GCP_HELM_RELEASE := flame-mcp-server

# Allow user to override the tag
TAG ?= $(DATE_TAG)

# Docker Build Variables
BUILD_DATE := $(shell powershell -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'")
VCS_REF := $(shell git rev-parse --short HEAD)

# Cloud target (azure or gcp)
CLOUD ?= gcp

# Default target
.PHONY: help
help: ## Show this help message
	@echo "Flame MCP Server - Available Commands:"
	@echo "======================================"
	@powershell -Command "Select-String -Pattern '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | ForEach-Object { $$_.Line -replace ':.*?## ', ' - ' }"

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

# GCP Commands
.PHONY: build-gcr
build-gcr: ## Build Docker image for GCP Artifact Registry (date tag + latest, override with TAG=mytag)
	@echo "[BUILD] Building Docker image for GCP Artifact Registry..."
	@echo "[BUILD] Using tag: $(TAG)"
	docker build \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg VCS_REF="$(VCS_REF)" \
		--build-arg VERSION="$(TAG)" \
		-t $(GCP_IMAGE_NAME):$(TAG) \
		-t $(GCP_IMAGE_NAME):$(LATEST_TAG) \
		.
	@echo "[BUILD] GCR build complete: $(GCP_IMAGE_NAME):$(TAG)"

.PHONY: login-gcr
login-gcr: ## Login to GCP Artifact Registry
	@echo "[AUTH] Logging into GCP Artifact Registry..."
	gcloud auth configure-docker $(GCP_REGISTRY)
	@echo "[AUTH] GCR login successful"

.PHONY: push-gcr
push-gcr: ## Push Docker image to GCP Artifact Registry (specify TAG=yourtag)
ifndef TAG
	@echo "[ERROR] Please specify TAG=yourtag (e.g., make push-gcr TAG=20241217-143022)"
	@exit 1
endif
	@echo "[PUSH] Pushing to GCP Artifact Registry..."
	@echo "[PUSH] Tag: $(TAG)"
	docker push $(GCP_IMAGE_NAME):$(TAG)
	docker push $(GCP_IMAGE_NAME):$(LATEST_TAG)
	@echo "[PUSH] Push complete: $(GCP_IMAGE_NAME):$(TAG)"

.PHONY: gke-auth
gke-auth: ## Authenticate kubectl with GKE cluster
	@echo "[AUTH] Authenticating kubectl with GKE..."
	gcloud container clusters get-credentials $(GCP_CLUSTER) --region $(GCP_REGION) --project $(GCP_PROJECT)
	@echo "[AUTH] GKE authentication successful"

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

.PHONY: helm-uninstall
helm-uninstall: ## Uninstall Helm release
	@echo "[HELM] Uninstalling Helm release..."
	helm uninstall $(HELM_RELEASE) -n $(NAMESPACE)
	@echo "[HELM] Uninstall complete"

# GCP Helm Commands
.PHONY: helm-template-gcp
helm-template-gcp: ## Generate Helm template output for GCP review
	@echo "[HELM] Generating Helm templates for GCP..."
	helm template test-release ./helm/ --dry-run -f ./helm/values-gcp-dev-secret.yaml > ./helm/rendered-gcp.yaml
	@echo "[HELM] Templates generated: ./helm/rendered-gcp.yaml"

.PHONY: helm-install-gcp
helm-install-gcp: ## Install Helm release to GKE
	@echo "[HELM] Installing Helm release to GKE..."
	helm install $(GCP_HELM_RELEASE) ./helm/ -f ./helm/values-gcp-dev-secret.yaml -n $(GCP_NAMESPACE) --create-namespace
	@echo "[HELM] Install complete"

.PHONY: helm-upgrade-gcp
helm-upgrade-gcp: ## Upgrade Helm release on GKE
	@echo "[HELM] Upgrading Helm release on GKE..."
	helm upgrade $(GCP_HELM_RELEASE) ./helm/ -f ./helm/values-gcp-dev-secret.yaml -n $(GCP_NAMESPACE)
	@echo "[HELM] Upgrade complete"

.PHONY: helm-uninstall-gcp
helm-uninstall-gcp: ## Uninstall Helm release from GKE
	@echo "[HELM] Uninstalling Helm release from GKE..."
	helm uninstall $(GCP_HELM_RELEASE) -n $(GCP_NAMESPACE)
	@echo "[HELM] Uninstall complete"

# Multi-Cloud Deployment Workflows
.PHONY: deploy-azure
deploy-azure: build-acr login-acr ## Build and push to Azure (use TAG=mytag to override)
	@echo "[DEPLOY] Starting Azure deployment..."
	$(MAKE) push TAG=$(TAG)
	@echo "[DEPLOY] Azure deployment complete. Run 'make helm-upgrade-dev' to update AKS"

.PHONY: deploy-gcp
deploy-gcp: build-gcr login-gcr ## Build and push to GCP (use TAG=mytag to override)
	@echo "[DEPLOY] Starting GCP deployment..."
	$(MAKE) push-gcr TAG=$(TAG)
	@echo "[DEPLOY] GCP deployment complete. Run 'make helm-upgrade-gcp' to update GKE"

.PHONY: deploy-all
deploy-all: ## Deploy to both Azure and GCP
	@echo "[DEPLOY] Starting multi-cloud deployment..."
	$(MAKE) deploy-azure TAG=$(TAG)
	$(MAKE) deploy-gcp TAG=$(TAG)
	@echo "[DEPLOY] Multi-cloud deployment complete" 
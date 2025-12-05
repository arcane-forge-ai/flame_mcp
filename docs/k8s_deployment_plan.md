# Kubernetes Deployment Implementation Plan

## Project Overview
The Flame MCP (Model Context Protocol) server is a FastAPI-based application that provides semantic search capabilities over Flame engine documentation. It uses:
- **FastMCP** for the MCP server framework
- **Azure OpenAI** for embeddings generation
- **Qdrant** for vector database storage
- **Python 3.9+** runtime

## Implementation Plan

### Phase 1: Dockerization
1. **Create Dockerfile**
   - Use Python 3.9 slim base image for smaller size
   - Multi-stage build for optimization
   - Install system dependencies
   - Copy requirements and install Python dependencies
   - Copy application code
   - Set proper user permissions (non-root)
   - Configure health check
   - Expose port 8000 (default FastMCP port)

2. **Create .dockerignore**
   - Exclude unnecessary files (tests, docs, .git, etc.)
   - Keep image size minimal

3. **Test Docker Build**
   - Build image locally
   - Run container with environment variables
   - Test health endpoint
   - Test MCP endpoints functionality

### Phase 2: Helm Chart Creation
1. **Chart Structure**
   ```
   helm/
   ├── Chart.yaml
   ├── values.yaml
   ├── templates/
   │   ├── deployment.yaml
   │   ├── service.yaml
   │   ├── configmap.yaml
   │   ├── secret.yaml
   │   ├── hpa.yaml (optional)
   │   └── ingress.yaml (optional)
   └── README.md
   ```

2. **Kubernetes Resources**
   - **Deployment**: Main application deployment with health checks
   - **Service**: ClusterIP service for internal communication
   - **ConfigMap**: Non-sensitive configuration
   - **Secret**: Sensitive data (API keys)
   - **HPA**: Horizontal Pod Autoscaler (optional)
   - **Ingress**: External access (optional)

3. **Helm Chart Dryrun Render**
   - Make sure all templates and values are rendered as expected.

## Technical Specifications

### Docker Configuration
- **Base Image**: `python:3.9-slim`
- **Port**: 8000
- **User**: Non-root user for security
- **Health Check**: `/health` endpoint
- **Resource Limits**: CPU/Memory limits defined

### Kubernetes Resources
- **Replicas**: 2 (for HA)
- **Resource Requests**: CPU: 100m, Memory: 256Mi
- **Resource Limits**: CPU: 500m, Memory: 512Mi
- **Liveness Probe**: `/health` endpoint
- **Readiness Probe**: `/health` endpoint
- **Service Type**: ClusterIP (internal)

### External Dependencies
- **Qdrant Vector Database**: Required for vector storage
- **Azure OpenAI**: Required for embeddings
- **Network Access**: Outbound HTTPS for Azure OpenAI

## Security Considerations
1. **Non-root Container**: Run as dedicated user
2. **Secret Management**: Use Kubernetes secrets for sensitive data
3. **Network Policies**: Restrict ingress/egress (optional)
4. **Image Scanning**: Scan for vulnerabilities
5. **RBAC**: Minimal required permissions

## Deployment Options
1. **Standalone**: Deploy only the MCP server
2. **With Qdrant**: Include Qdrant as a dependency
3. **Full Stack**: Include processing pipeline components

## Post-Deployment Verification
1. **Health Checks**: Verify `/health` endpoint responds
2. **MCP Functionality**: Test `get_flame_knowledge` tool
3. **External Connectivity**: Test Azure OpenAI and Qdrant connections
4. **Scaling**: Test horizontal pod autoscaling
5. **Monitoring**: Set up logging and metrics collection

## Files to be Created
1. `Dockerfile` - Multi-stage Docker build
2. `helm/Chart.yaml` - Helm chart metadata
3. `helm/values.yaml` - Default configuration values
4. `helm/templates/deployment.yaml` - Kubernetes deployment
5. `helm/templates/service.yaml` - Kubernetes service
6. `helm/templates/configmap.yaml` - Configuration map
7. `helm/templates/secret.yaml` - Secrets template
8. `helm/templates/hpa.yaml` - Horizontal Pod Autoscaler
9. `helm/templates/ingress.yaml` - Ingress controller
10. `.dockerignore` - Docker ignore file


## Prerequisites for Implementation
- Docker installed locally
- Helm 3.x installed
- Azure OpenAI service access
- Qdrant database (local or remote)

## Success Criteria
- [x] Docker image builds successfully
- [x] Container runs and passes health checks
- [x] Helm chart deploys without errors
- [x] MCP endpoints are accessible and functional
- [x] External dependencies connect properly
- [x] Application scales horizontally
- [x] Configuration is properly injected via K8s resources 
# 📡 Fleet Manager API Documentation

This document provides comprehensive documentation for all Fleet Manager API endpoints used in this GitOps project.

## 🔑 Authentication

All API requests require Bearer token authentication:

```python
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
```

**Environment Variables:**
- `SC_FM_APIKEY`: Your Fleet Manager API key
- `FLEET_MANAGER_API_URL`: API base URL (defaults to `https://api.scalecomputing.com/api/v2`)

## 📋 API Endpoints

### 🏥 Health Check

**GET** `/clusters`
- **Purpose**: Test API connectivity and authentication
- **Response**: List of clusters (used as health check)
- **Usage**: Verify API key and connectivity

### 📦 Deployment Applications

#### List Applications
**GET** `/deployment-applications?limit=50`
- **Purpose**: Retrieve all deployment applications
- **Parameters**:
  - `limit`: Number of results per page (default: 50, max: 200)
- **Pagination**: Handle pagination to get all applications
- **Response**: Array of application objects with `id`, `name`, `version`, etc.

#### Get Application by ID
**GET** `/deployment-applications/{id}`
- **Purpose**: Get full details for a specific application
- **Response**: Complete application object including `sourceConfig` (YAML manifest)

#### Create Application
**POST** `/deployment-applications`
- **Purpose**: Create a new deployment application
- **Payload**:
  ```json
  {
    "name": "application-name",
    "version": "1",
    "sourceConfig": "yaml_manifest_content",
    "sourceType": "gitops",
    "description": "GitOps managed via https://github.com/user/repo"
  }
  ```
- **Response**: Created application object with assigned ID

#### Update Application
**PUT** `/deployment-applications/{id}`
- **Purpose**: Update an existing deployment application
- **Payload**: Same as create
- **Response**: Updated application object

### 🚀 Deployments

#### List Deployments
**GET** `/deployments?limit=50`
- **Purpose**: Retrieve all deployments
- **Parameters**:
  - `limit`: Number of results per page (default: 50, max: 200)
- **Pagination**: Handle pagination to get all deployments
- **Response**: Array of deployment objects

#### Get Deployment by ID
**GET** `/deployments/{id}`
- **Purpose**: Get full details for a specific deployment
- **Response**: Complete deployment object including `applications` field (array of application IDs)

#### Create Deployment
**POST** `/deployments`
- **Purpose**: Create a new deployment binding application to cluster group
- **Payload**:
  ```json
  {
    "name": "application-name-cluster-group",
    "applicationId": "application-uuid",
    "clusterGroupId": "cluster-group-uuid",
    "applicationVersion": "1"
  }
  ```
- **Response**: Created deployment object with assigned ID

#### Update Deployment
**PUT** `/deployments/{id}`
- **Purpose**: Update an existing deployment
- **Payload**: Same as create
- **Response**: Updated deployment object

#### Trigger Deployment Release
**POST** `/deployments/{id}/deploy`
- **Purpose**: Trigger a deployment release (start actual deployment)
- **Response**: Deployment release information
- **Status Codes**:
  - `200/201`: Success
  - `409`: Conflict (deployment already running/in progress)

### 🏢 Cluster Groups

#### List Cluster Groups
**GET** `/cluster-groups?limit=200`
- **Purpose**: Retrieve all cluster groups
- **Parameters**:
  - `limit`: Number of results per page
- **Response**: Array of cluster group objects with `id`, `name`, etc.
- **Usage**: Map cluster group names to IDs for deployment creation

### 📊 Deployment Releases

#### Get Deployment Releases
**GET** `/deployments/{deployment_id}/releases`
- **Purpose**: Get all releases for a specific deployment
- **Response**: Array of release objects with status, timestamps, etc.
- **Usage**: Monitor deployment progress and results

## 🔄 API Workflow

### Typical Deployment Flow

1. **Health Check**: `GET /clusters`
2. **List Applications**: `GET /deployment-applications` (check if app exists)
3. **Create/Update Application**: `POST/PUT /deployment-applications`
4. **List Cluster Groups**: `GET /cluster-groups` (get cluster group IDs)
5. **Check Deployment Conflicts**: `GET /deployments` (find existing deployments)
6. **Create/Update Deployment**: `POST/PUT /deployments`
7. **Trigger Release**: `POST /deployments/{id}/deploy`

### Error Handling

**Common HTTP Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request (invalid payload)
- `401`: Unauthorized (invalid API key)
- `404`: Not Found
- `409`: Conflict (deployment already running)
- `500`: Internal Server Error

**Rate Limiting**: API may have rate limits. Implement retry logic with exponential backoff.

## 📝 Data Models

### Application Object
```json
{
  "id": "uuid",
  "name": "application-name",
  "version": "1",
  "sourceConfig": "yaml_manifest_content",
  "sourceType": "gitops",
  "description": "Description text",
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

### Deployment Object
```json
{
  "id": "uuid",
  "name": "application-name-cluster-group",
  "applicationId": "application-uuid",
  "applications": ["application-uuid"],
  "clusterGroupId": "cluster-group-uuid",
  "status": "Created|Running|Success|Failed",
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

### Cluster Group Object
```json
{
  "id": "uuid",
  "name": "cluster-group-name",
  "description": "Description text",
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

## 🛠️ Implementation Notes

### Pagination
- All list endpoints support pagination
- Use `limit` parameter to control page size
- Implement pagination handling to retrieve all results

### Naming Conventions
- **Applications**: Use descriptive names from manifest metadata
- **Deployments**: Format: `{application-name}-{cluster-group-name}`
- **Test Applications**: Add `-test` suffix for isolation

### GitOps Integration
- Set `sourceType: "gitops"` for applications
- Include repository URL in description
- Use raw YAML content in `sourceConfig` to preserve comments

### Error Recovery
- Handle 409 conflicts gracefully (deployment already running)
- Implement retry logic for transient failures
- Log detailed error information for debugging

## 🔍 Debugging

### Common Issues

**401 Unauthorized:**
- Check API key validity
- Verify Bearer token format

**409 Conflict:**
- Deployment already exists or is running
- Check deployment status before creating new ones

**500 Internal Server Error:**
- Application may be corrupted or deleted
- Check application content and validity

### Debug Commands
```bash
# Test API connectivity
curl -H "Authorization: Bearer $SC_FM_APIKEY" \
     https://api.scalecomputing.com/api/v2/clusters

# List applications
curl -H "Authorization: Bearer $SC_FM_APIKEY" \
     https://api.scalecomputing.com/api/v2/deployment-applications

# Get specific application
curl -H "Authorization: Bearer $SC_FM_APIKEY" \
     https://api.scalecomputing.com/api/v2/deployment-applications/{id}
```

## 📚 Additional Resources

- [Fleet Manager API Reference](https://api.scalecomputing.com/docs)
- [Scale Computing Documentation](https://docs.scalecomputing.com)
- [GitHub Repository](https://github.com/ddemlow/fleet-manager-gitops)

---

*This documentation is based on the actual API usage patterns in the GitOps deployment scripts and represents the current state of the Fleet Manager API as of October 2025.*

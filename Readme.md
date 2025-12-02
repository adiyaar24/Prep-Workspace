# Harness Workspace Preparation Plugin

A robust workspace preparation plugin for Harness CI/CD pipelines with comprehensive error handling, enhanced logging, and seamless integration with Harness expressions.

## Features

- **🔧 Flexible Action Support**: Support for create, update, and delete workspace operations
- **🛡️ Robust Error Handling**: Comprehensive error handling with retry mechanisms and validation
- **📤 Smart Output Management**: Automatic environment variable outputs with drone integration
- **🔄 API Integration**: Seamless integration with Pangea API for tag management
- **🐛 Enhanced Debug Support**: Advanced logging with color coding and performance monitoring
- **⚙️ Zero Dependencies**: Uses only Python standard library (urllib instead of requests)
- **🌍 Harness Native**: Full integration with Harness expressions and pipeline variables

## Quick Start

### Prerequisites

- Python 3.12+
- Harness CI/CD pipeline environment
- Access to Pangea API (for tag fetching)

### Environment Variables

The plugin automatically reads Harness pipeline variables using expression syntax:

#### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `action` | Action type (create/update/delete) | `create` |
| `org.identifier` | Organization identifier | `default` |
| `project.identifier` | Project identifier | `my_project` |

#### Action-Specific Variables

**CREATE Action:**
```yaml
variables:
  - name: action
    value: "create"
  - name: asset_id
    value: "<asset_id_value>"
  - name: cloud_project
    value: "my-cloud-project"
```

**UPDATE Action:**
```yaml
variables:
  - name: action
    value: "update"
  - name: component_name
    value: "component1,component2,component3"
  - name: asset_id
    value: "<asset_id_value>"
  - name: cloud_project
    value: "my-cloud-project"
```

**DELETE Action:**
```yaml
variables:
  - name: action
    value: "delete"
  - name: component_name
    value: "component1,component2,component3"
```

## Supported Actions

### Create Action

Creates new workspace configurations with full tag integration and resource naming.

**Pipeline Variables Required:**
- `repeat.item`: Current workspace name from iteration
- `item_map`: JSON mapping from preparation stage output
- `asset_id`: Asset identifier for tag fetching
- `cloud_project`: Cloud project identifier
- `deployment_name`: Deployment name from preparation stage
- `strategy.iteration`: Current iteration number

**Generated Outputs:**
- `WORKSPACE_NAME`: Current workspace name
- `ASSET_ID`: Asset identifier
- `TERRAFORM_VARS`: JSON-formatted terraform variables with tags
- `CONNECTOR`: Processed connector name
- `MODULE_NAME`: Module name for workspace
- `RESOURCE_NAME`: Generated normalized resource name
- `ENTITY_ID`: Generated normalized entity identifier

**Example Harness Expression:**
```yaml
- step:
    type: Plugin
    name: Workspace Preparation
    identifier: workspace_prep
    spec:
      image: your-registry/harness-workspace-plugin:latest
      settings:
        action: create
        repeat_item: <+repeat.item>
        item_map: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.item_map>
        asset_id: <+pipeline.variables.asset_id>
        cloud_project: <+pipeline.variables.cloud_project>
        deployment_name: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.DEPLOYMENT_NAME>
        iteration: <+strategy.iteration>
```

### Update Action

Updates existing workspace configurations with current resource settings.

**Pipeline Variables Required:**
- `component_name`: Comma-separated list of component names
- `strategy.iteration`: Current iteration number
- `repeat.item`: Current workspace name
- `asset_id`: Asset identifier for tag fetching
- `resource_config`: Resource configuration JSON
- `cloud_project`: Cloud project identifier

**Generated Outputs:**
- `RESOURCE_NAME`: Current component name
- `ENTITY_ID`: Current component name
- `WORKSPACE_NAME`: Current workspace name
- `ASSET_ID`: Asset identifier
- `TERRAFORM_VARS`: Filtered terraform variables
- `CONNECTOR`: Processed connector name
- `MODULE_NAME`: Module name for workspace

### Delete Action

Removes workspace configurations by component name.

**Pipeline Variables Required:**
- `component_name`: Comma-separated list of component names
- `strategy.iteration`: Current iteration number

**Generated Outputs:**
- `RESOURCE_NAME`: Current component name
- `ENTITY_ID`: Current component name

## API Integration

### Pangea API Integration

The plugin integrates with Pangea API to fetch project tags:

**API Endpoint:**
```
https://svc-pangea-api-nginx.int.nebula-dit.connectcdk.com/api/projects?asset_id=<asset_id>
```

**Features:**
- Automatic tag fetching and integration
- Error handling for API failures
- 30-second timeout configuration
- Graceful fallback for missing data

**Tag Processing:**
- Tags are automatically added to `cdk_std_tags` in terraform variables
- All tag values are converted to strings for consistency
- Empty or failed responses result in empty tag maps

## Output Management

### Environment Variables

All outputs are automatically set as environment variables and written to drone output files:

**Drone Integration:**
- `DRONE_OUTPUT`: Primary drone output file
- `DRONE_STEP_ENV`: Step-specific environment file
- `/drone/src/output.env`: Fallback location

**Output Format:**
```bash
WORKSPACE_NAME="example-workspace"
ASSET_ID="asset-123"
TERRAFORM_VARS='{"key":"value","cdk_std_tags":{"env":"prod"}}'
CONNECTOR="my_cloud_project"
MODULE_NAME="terraform-module"
RESOURCE_NAME="s3_bucket_deployment_name0"
ENTITY_ID="s3_bucket_deployment_name0"
```

### Common Outputs

All actions generate these common outputs:

```bash
RESOURCE_OWNER="user:account/user@example.com"
ENTITY_SCOPE="account.default.my_project"
ENTITY_REF="account.default.my_project/resource_name"
```

## Resource Naming Convention

### Normalization Rules

Resource names and entity IDs follow consistent normalization:

1. Convert to lowercase
2. Replace hyphens with underscores
3. Follow pattern: `{type}_{resource_name}_{deployment_name}{iteration}`

**Examples:**
- Input: `S3-Bucket` → Output: `s3_bucket_deployment_abc_1230`
- Input: `RDS-Database` → Output: `rds_database_deployment_abc_1230`

### Entity References

Entity references follow Harness scoping pattern:
```
account.{org_identifier}.{project_identifier}/{entity_id}
```

## Error Handling

### Comprehensive Error Management

The plugin includes robust error handling:

**Validation Errors:**
- Missing required pipeline variables
- Invalid JSON configurations
- Out-of-range iteration values

**API Errors:**
- Network timeouts (30s)
- HTTP error responses
- JSON parsing failures
- Authentication issues

**Configuration Errors:**
- Invalid action types
- Missing component names
- Malformed resource configurations

### Error Recovery

**Graceful Degradation:**
- API failures result in empty tag maps (operation continues)
- Missing optional variables use sensible defaults
- Export failures are logged but don't stop execution

**Debug Information:**
- Detailed error messages with context
- Full stack traces in debug mode
- Performance monitoring and metrics

## Docker Integration

### Building the Image

```dockerfile
FROM python:3.12-slim

# Set metadata
LABEL maintainer="Harness Workspace Plugin"
LABEL description="Harness Workspace Preparation Plugin for CI/CD pipeline automation"
LABEL version="1.0.0"

# Copy application code
COPY main.py /usr/local/bin/plugin.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set entrypoint
ENTRYPOINT python /usr/local/bin/plugin.py
```

### Building and Running

```bash
# Build the image
docker build -t harness-workspace-plugin:latest .

# Run with test environment
docker run --rm \
  -e action="create" \
  -e repeat_item="test-workspace" \
  -e item_map='[{"test-workspace":{"type":"s3","resource_name":"bucket"}}]' \
  -e asset_id="test-asset" \
  -e cloud_project="test-project" \
  -e deployment_name="test_deployment" \
  -e iteration="0" \
  harness-workspace-plugin:latest
```

## Harness Pipeline Integration

### Complete Pipeline Step

```yaml
- step:
    type: Plugin
    name: Workspace Preparation
    identifier: workspace_preparation
    spec:
      connectorRef: <+input>  # Your Docker connector
      image: your-registry/harness-workspace-plugin:latest
      settings:
        # These are passed as environment variables to the container
        action: <+pipeline.variables.action>
        
        # CREATE-specific variables
        repeat_item: <+repeat.item>
        item_map: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.item_map>
        asset_id: <+pipeline.variables.asset_id>
        cloud_project: <+pipeline.variables.cloud_project>
        deployment_name: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.DEPLOYMENT_NAME>
        iteration: <+strategy.iteration>
        
        # UPDATE/DELETE-specific variables
        component_name: <+pipeline.variables.component_name>
        resource_config: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.RESOURCE_CONFIG>
        
        # Common variables
        org_identifier: <+org.identifier>
        project_identifier: <+project.identifier>
        resource_owner: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.RESOURCE_OWNER>
      timeout: 10m
```

### Strategy Configuration

For iterative processing (CREATE and UPDATE actions):

```yaml
strategy:
  repeat:
    items: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.workspace_ids>.split(',')
  maxConcurrency: 1
```

### Required Pipeline Variables

```yaml
variables:
  - name: action
    type: String
    description: "Action to perform: create, update, or delete"
    value: <+input>
  
  - name: asset_id
    type: String
    description: "Asset ID for API tag fetching"
    value: <+input>
  
  - name: cloud_project
    type: String
    description: "Cloud project identifier"
    value: <+input>
  
  - name: component_name
    type: String
    description: "Comma-separated component names (UPDATE/DELETE only)"
    value: <+input>.allowedValues(create,update,delete)
```

## Logging and Debugging

### Enhanced Logging

The plugin features advanced logging capabilities:

**Log Levels:**
- `INFO`: Standard operational messages
- `DEBUG`: Detailed troubleshooting information
- `WARNING`: Non-fatal issues and fallbacks
- `ERROR`: Fatal errors with full context

**Color-Coded Output:**
- 🟢 **INFO**: Green - Normal operations
- 🔵 **DEBUG**: Blue - Debug information
- 🟡 **WARNING**: Yellow - Warnings and fallbacks
- 🔴 **ERROR**: Red - Errors and failures

**Debug Features:**
- Performance monitoring
- API request/response logging
- Environment variable tracking
- Resource processing details

### Debug Mode

Enable debug mode by setting log level in pipeline:

```yaml
settings:
  log_level: "DEBUG"
  debug_mode: "true"
```

## Troubleshooting

### Common Issues

**1. Missing Pipeline Variables**
```
ERROR - Missing required variable: repeat_item
```
*Solution:* Ensure all required variables are configured for your action type.

**2. JSON Parsing Errors**
```
ERROR - Failed to parse item map: Invalid JSON
```
*Solution:* Verify JSON format in preparation stage outputs.

**3. API Connection Issues**
```
WARNING - Network Error fetching tags: Connection timeout
```
*Solution:* Check network connectivity to Pangea API endpoint.

**4. Iteration Out of Range**
```
ERROR - Iteration 3 out of range for component names (max: 2)
```
*Solution:* Verify strategy iteration matches available items.

### Debug Tips

1. **Enable Debug Logging**: Set `log_level: "DEBUG"` for detailed output
2. **Check Environment Variables**: Verify all Harness expressions resolve correctly
3. **Validate JSON**: Ensure all JSON configurations are properly formatted
4. **Monitor API Responses**: Check Pangea API connectivity and responses
5. **Review Iteration Logic**: Verify strategy configuration matches data

## Performance Considerations

### Optimization Features

- **API Caching**: Implement caching for repeated API calls
- **Parallel Processing**: Use maxConcurrency for optimal performance
- **Resource Limits**: Set appropriate timeouts and memory limits
- **Network Optimization**: Handle network timeouts gracefully

### Recommended Settings

```yaml
spec:
  resources:
    limits:
      memory: "512Mi"
      cpu: "500m"
    requests:
      memory: "256Mi"
      cpu: "250m"
  timeout: 10m
```

## Security Considerations

### Best Practices

1. **Environment Variables**: Never log sensitive values
2. **API Credentials**: Use Harness secrets for API authentication
3. **Resource Access**: Limit plugin permissions to required operations
4. **Network Security**: Ensure secure API endpoints only

### Secret Management

```yaml
settings:
  api_token: <+secrets.getValue("pangea_api_token")>
  # Other sensitive configurations
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Update documentation
5. Submit a pull request

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Enable debug mode for detailed logging
- Review Harness pipeline logs

## Changelog

### v1.0.0
- Initial release
- Support for create, update, delete actions
- Pangea API integration
- Enhanced logging and debugging
- Drone output integration
- Comprehensive error handling
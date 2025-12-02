# Harness Workspace Preparation Plugin

A robust workspace preparation plugin for Harness CI/CD pipelines with enhanced logging and seamless drone integration.

## Features

- **🔧 Flexible Action Support**: Support for create, update, and delete workspace operations
- **🛡️ Robust Error Handling**: Comprehensive error handling with validation
- **📤 Drone Output Integration**: Automatic environment variable outputs to DRONE_OUTPUT
- **🔄 API Integration**: Seamless integration with Pangea API for tag management
- **🐛 Enhanced Logging**: Color-coded logging with debug capabilities
- **⚙️ Zero Dependencies**: Uses only Python standard library (urllib instead of requests)
- **🌍 Harness Native**: Full integration with Harness pipeline variables

## Quick Start

### Environment Variables

The plugin uses PLUGIN_ prefixed environment variables:

#### Required Variables (All Actions)
| Variable | Description | Example |
|----------|-------------|---------|
| `PLUGIN_ACTION` | Action type | `create`, `update`, `delete` |
| `PLUGIN_ORG_IDENTIFIER` | Organization identifier | `default` |
| `PLUGIN_PROJECT_IDENTIFIER` | Project identifier | `my_project` |
| `PLUGIN_RESOURCE_OWNER` | Resource owner | `user:account/user@example.com` |

#### CREATE Action Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `PLUGIN_REPEAT_ITEM` | Current workspace name | `s3-bucket-deployment_123` |
| `PLUGIN_ITEM_MAP` | JSON workspace mapping | `[{"workspace":{"type":"s3"}}]` |
| `PLUGIN_ASSET_ID` | Asset identifier | `asset-12345` |
| `PLUGIN_CLOUD_PROJECT` | Cloud project | `my-cloud-project` |
| `PLUGIN_DEPLOYMENT_NAME` | Deployment name | `deployment_123` |
| `PLUGIN_ITERATION` | Iteration number | `0` |

#### UPDATE Action Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `PLUGIN_COMPONENT_NAME` | Component names (comma-separated) | `comp1,comp2,comp3` |
| `PLUGIN_ITERATION` | Iteration number | `1` |
| `PLUGIN_REPEAT_ITEM` | Current workspace | `s3-bucket-deployment_123` |
| `PLUGIN_ASSET_ID` | Asset identifier | `asset-67890` |
| `PLUGIN_RESOURCE_CONFIG` | Resource configuration JSON | `{"entries":[...]}` |
| `PLUGIN_CLOUD_PROJECT` | Cloud project | `my-cloud-project` |

#### DELETE Action Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `PLUGIN_COMPONENT_NAME` | Component names (comma-separated) | `comp1,comp2` |
| `PLUGIN_ITERATION` | Iteration number | `0` |

#### Optional Variables
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PLUGIN_API_URL` | API endpoint | Pangea API URL | Custom API URL |
| `DEBUG_MODE` | Enable debug logging | `false` | `true`, `false` |

## Output Variables

All outputs use camelCase naming and are written to environment variables and DRONE_OUTPUT:

### Common Outputs (All Actions)
- `resourceOwner` - Resource owner identifier
- `entityScope` - Entity scope (account.org.project)
- `entityRef` - Full entity reference

### CREATE Action Outputs
- `workspaceName` - Current workspace name
- `assetId` - Asset identifier
- `terraformVars` - JSON terraform variables with tags
- `connector` - Processed connector name
- `moduleName` - Module name
- `resourceName` - Generated resource name
- `entityId` - Generated entity ID

### UPDATE Action Outputs
- `resourceName` - Current component name
- `entityId` - Current component name  
- `workspaceName` - Current workspace name
- `assetId` - Asset identifier
- `terraformVars` - Filtered terraform variables
- `connector` - Processed connector name
- `moduleName` - Module name

### DELETE Action Outputs
- `resourceName` - Current component name
- `entityId` - Current component name

## Harness Pipeline Integration

### Plugin Step Configuration

```yaml
- step:
    type: Plugin
    name: Workspace Preparation
    identifier: workspace_preparation
    spec:
      connectorRef: <+input>
      image: your-registry/harness-workspace-plugin:latest
      settings:
        PLUGIN_ACTION: <+pipeline.variables.action>
        PLUGIN_ORG_IDENTIFIER: <+org.identifier>
        PLUGIN_PROJECT_IDENTIFIER: <+project.identifier>
        PLUGIN_RESOURCE_OWNER: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.RESOURCE_OWNER>
        
        # CREATE-specific
        PLUGIN_REPEAT_ITEM: <+repeat.item>
        PLUGIN_ITEM_MAP: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.item_map>
        PLUGIN_ASSET_ID: <+pipeline.variables.asset_id>
        PLUGIN_CLOUD_PROJECT: <+pipeline.variables.cloud_project>
        PLUGIN_DEPLOYMENT_NAME: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.DEPLOYMENT_NAME>
        PLUGIN_ITERATION: <+strategy.iteration>
        
        # UPDATE/DELETE-specific
        PLUGIN_COMPONENT_NAME: <+pipeline.variables.component_name>
        PLUGIN_RESOURCE_CONFIG: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.RESOURCE_CONFIG>
      timeout: 10m
```

### Strategy Configuration

```yaml
strategy:
  repeat:
    items: <+pipeline.stages.Create_Deployment.spec.execution.steps.Prep_Stage.output.outputVariables.workspace_ids>.split(',')
  maxConcurrency: 1
```

## API Integration

### Pangea API
- **Endpoint**: `https://svc-pangea-api-nginx.int.nebula-dit.connectcdk.com/api/projects`
- **Timeout**: 30 seconds
- **Retries**: 3 attempts with exponential backoff
- **Tags**: Automatically added to `cdk_std_tags` in terraform variables

## Docker Integration

### Dockerfile
```dockerfile
FROM python:3.12-slim

LABEL maintainer="Harness Workspace Plugin"
LABEL description="Harness Workspace Preparation Plugin"
LABEL version="1.0.0"

COPY main.py /usr/local/bin/plugin.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT python /usr/local/bin/plugin.py
```

### Build and Run
```bash
# Build
docker build -t harness-workspace-plugin:latest .

# Run
docker run --rm \
  -e PLUGIN_ACTION="create" \
  -e PLUGIN_ORG_IDENTIFIER="default" \
  -e PLUGIN_PROJECT_IDENTIFIER="test" \
  -e PLUGIN_RESOURCE_OWNER="user:account/user@example.com" \
  -e PLUGIN_REPEAT_ITEM="test-workspace" \
  -e PLUGIN_ITEM_MAP='[{"test-workspace":{"type":"s3","resource_name":"bucket"}}]' \
  -e PLUGIN_ASSET_ID="test-asset" \
  -e PLUGIN_CLOUD_PROJECT="test-project" \
  -e PLUGIN_DEPLOYMENT_NAME="test_deployment" \
  -e PLUGIN_ITERATION="0" \
  harness-workspace-plugin:latest
```

## Logging and Debugging

### Log Levels
- **INFO**: Standard operational messages (Green)
- **DEBUG**: Detailed information (Cyan) 
- **WARNING**: Non-fatal issues (Yellow)
- **ERROR**: Fatal errors (Red)

### Debug Mode
Set `DEBUG_MODE=true` for enhanced logging:
```bash
export DEBUG_MODE="true"
python main.py
```

## Error Handling

### Validation Errors
- Missing required PLUGIN_ environment variables
- Invalid action types
- Malformed JSON configurations
- Invalid iteration values

### API Errors
- Network timeouts (30s)
- HTTP error responses  
- JSON parsing failures
- Graceful fallback with empty tags

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```
   ValueError: PLUGIN_ACTION environment variable is required
   ```
   **Solution**: Set all required PLUGIN_ variables for your action type

2. **JSON Parsing Errors**
   ```
   ValueError: Invalid JSON in item map
   ```
   **Solution**: Verify JSON format in PLUGIN_ITEM_MAP or PLUGIN_RESOURCE_CONFIG

3. **API Connection Issues**
   ```
   WARNING: Failed to fetch tags after 3 attempts
   ```
   **Solution**: Check network connectivity; plugin continues with empty tags

4. **Invalid Iteration**
   ```
   ValueError: PLUGIN_ITERATION must be a valid integer
   ```
   **Solution**: Ensure PLUGIN_ITERATION is a valid number

### Debug Tips
1. Set `DEBUG_MODE=true` for detailed output
2. Check all PLUGIN_ environment variables are set
3. Validate JSON configurations
4. Monitor DRONE_OUTPUT file for outputs

## Output Format

Outputs are written to both environment variables and DRONE_OUTPUT file:

```bash
# Environment variables
resourceOwner=user:account/user@example.com
workspaceName=s3-bucket-deployment_123
assetId=asset-12345
terraformVars={"key":"value","cdk_std_tags":{"env":"prod"}}
connector=my_cloud_project
moduleName=terraform-module
resourceName=s3_bucket_deployment_123_0
entityId=s3_bucket_deployment_123_0
entityScope=account.default.my_project
entityRef=account.default.my_project/s3_bucket_deployment_123_0
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the repository
- Check troubleshooting section
- Enable debug mode for detailed logging
#!/usr/bin/env python3
"""
Harness Workspace Preparation Plugin
A robust workspace preparation plugin for Harness CI/CD pipelines with comprehensive
error handling, enhanced logging, and seamless integration with Harness expressions.

Features:
- Enhanced color-coded logging with debug support
- Comprehensive error handling with retries and validation
- Advanced debugging and performance monitoring
- Robust drone environment variable output
- Zero external dependencies (uses urllib instead of requests)
- Full Harness expression integration
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
import subprocess
import socket
from pathlib import Path
from typing import Dict, Any, Optional
import re


class EnhancedLogger:
    """Enhanced logger with color coding and debug capabilities."""
    
    def __init__(self, name: str = __name__, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.logger = self._setup_logging(name)
        
    def _setup_logging(self, name: str) -> logging.Logger:
        """Setup enhanced logging with color coding."""
        
        class ColoredFormatter(logging.Formatter):
            # Enhanced ANSI color codes
            COLORS = {
                'DEBUG': '\033[96m',     # Bright Cyan
                'INFO': '\033[92m',      # Bright Green  
                'WARNING': '\033[93m',   # Bright Yellow
                'ERROR': '\033[91m',     # Bright Red
                'CRITICAL': '\033[95m',  # Bright Magenta
            }
            
            BACKGROUND_COLORS = {
                'ERROR': '\033[41m',     # Red background
                'CRITICAL': '\033[45m',  # Magenta background
            }
            
            RESET = '\033[0m'
            BOLD = '\033[1m'
            DIM = '\033[2m'
            
            # Emoji mapping for log levels
            EMOJIS = {
                'DEBUG': '🔍',
                'INFO': '📝', 
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '💥'
            }
            
            def format(self, record):
                color = self.COLORS.get(record.levelname, self.RESET)
                bg_color = self.BACKGROUND_COLORS.get(record.levelname, '')
                emoji = self.EMOJIS.get(record.levelname, '📝')
                
                if hasattr(record, 'debug_mode') and record.debug_mode:
                    timestamp = self.formatTime(record, '%H:%M:%S.%f')[:-3]
                    location_info = f"[{record.filename}:{record.funcName}:{record.lineno}]"
                    log_format = (f'{self.DIM}[{timestamp}]{self.RESET} '
                                f'{bg_color}{color}{self.BOLD}[{record.levelname:<8}]{self.RESET} '
                                f'{emoji} {self.DIM}{location_info}{self.RESET} '
                                f'{record.getMessage()}')
                else:
                    timestamp = self.formatTime(record, '%H:%M:%S')
                    log_format = (f'{self.DIM}[{timestamp}]{self.RESET} '
                                f'{bg_color}{color}[{record.levelname}]{self.RESET} '
                                f'{emoji} {record.getMessage()}')
                
                return log_format
        
        # Create logger with handlers
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        
        # Add debug_mode flag to records
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.debug_mode = self.debug_mode
            return record
        logging.setLogRecordFactory(record_factory)
        
        logger.addHandler(console_handler)
        
        # File handler for debug mode
        if self.debug_mode:
            try:
                debug_file = Path('/tmp/workspace_plugin_debug.log')
                debug_file.parent.mkdir(exist_ok=True)
                file_handler = logging.FileHandler(debug_file, mode='a')
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - [%(levelname)s] - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception:
                pass  # Don't fail if we can't create debug file
        
        return logger
    
    def info(self, msg: str): 
        self.logger.info(msg)
        
    def debug(self, msg: str):
        self.logger.debug(msg)
        
    def warning(self, msg: str):
        self.logger.warning(msg)
        
    def error(self, msg: str, exc_info: bool = False):
        self.logger.error(msg, exc_info=exc_info)
        
    def critical(self, msg: str, exc_info: bool = False):
        self.logger.critical(msg, exc_info=exc_info)


class DroneOutputManager:
    """Enhanced output manager with robust drone integration."""
    
    def __init__(self, logger: EnhancedLogger):
        self.logger = logger
        self.outputs: Dict[str, str] = {}
        self._validated_keys: set = set()
        
    def add_output(self, key: str, value: str) -> None:
        """Add output with validation and drone integration."""
        try:
            # Enhanced validation
            if not key or not isinstance(key, str):
                raise ValueError("Output key must be a non-empty string")
            
            if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', key):
                self.logger.warning(f"Key '{key}' contains special characters")
            
            if not isinstance(value, str):
                original_type = type(value).__name__
                value = str(value)
                self.logger.debug(f"Converted {original_type} to string for key '{key}'")
                
            # Store output
            self.outputs[key] = value
            self._validated_keys.add(key)
            
            # Set environment variable
            os.environ[key] = value
            
            truncated_value = value[:50] + '...' if len(value) > 50 else value
            self.logger.info(f"📤 EXPORTED: {key}={truncated_value}")
                
        except Exception as e:
            error_msg = f"Failed to add output {key}: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def write_drone_outputs(self) -> None:
        """Write outputs to drone output file if available."""
        if not self.outputs:
            self.logger.info("No outputs to write")
            return
            
        # Write to drone output file if available
        drone_output_file = os.environ.get('DRONE_OUTPUT')
        if drone_output_file:
            try:
                Path(drone_output_file).parent.mkdir(parents=True, exist_ok=True)
                
                with open(drone_output_file, 'a') as f:
                    for key, value in self.outputs.items():
                        f.write(f"{key}={value}\n")
                self.logger.debug(f"✅ Wrote {len(self.outputs)} outputs to {drone_output_file}")
                
            except Exception as e:
                self.logger.debug(f"Failed to write to DRONE_OUTPUT file {drone_output_file}: {e}")
                # Don't raise exception for debug file write failures
    
    def finalize_outputs(self) -> None:
        """Finalize all outputs."""
        # Write to drone file
        self.write_drone_outputs()
        
        self.logger.info(f"🎯 Generated {len(self.outputs)} output variables")
    
    def get_summary(self) -> Dict[str, str]:
        """Get a summary of all outputs."""
        return self.outputs.copy()


# Initialize enhanced logger
debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() in ['true', '1', 'yes']
logger = EnhancedLogger(__name__, debug_mode)
output_manager = DroneOutputManager(logger)


def safe_json_parse(json_str: str, config_name: str) -> Any:
    """Enhanced JSON parsing with comprehensive error handling and validation."""
    try:
        if not json_str or json_str.strip() == '':
            logger.warning(f"📄 {config_name} is empty, returning empty dict")
            return {}
            
        # Pre-validation
        if len(json_str) > 1024 * 1024:  # 1MB limit
            raise ValueError(f"{config_name} exceeds maximum size (1MB)")
            
        logger.debug(f"🔍 Parsing {config_name} ({len(json_str)} chars)")
        
        config = json.loads(json_str)
        logger.info(f"✅ Successfully parsed {config_name}")
        
        # Post-validation
        if isinstance(config, dict):
            logger.debug(f"📊 Parsed dict with {len(config)} keys")
        elif isinstance(config, list):
            logger.debug(f"📊 Parsed list with {len(config)} items")
            
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse {config_name}: {e}")
        logger.error(f"📄 Invalid JSON content (line {e.lineno}, col {e.colno}): {json_str[:200]}...")
        
        if logger.debug_mode:
            # Show the problematic part of JSON
            lines = json_str.split('\\n')
            if hasattr(e, 'lineno') and e.lineno <= len(lines):
                problem_line = lines[e.lineno - 1]
                logger.debug(f"🔍 Problem line: {problem_line}")
                if hasattr(e, 'colno'):
                    pointer = ' ' * (e.colno - 1) + '^'
                    logger.debug(f"🔍 Position: {pointer}")
        
        raise ValueError(f"Invalid JSON in {config_name}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error parsing {config_name}: {e}")
        raise ValueError(f"Unexpected error parsing {config_name}: {e}")


def export_env_var(name: str, value: str) -> None:
    """Enhanced environment variable export with validation and drone integration."""
    try:
        # Validation
        if not name or not isinstance(name, str):
            raise ValueError("Variable name must be a non-empty string")
            
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
            logger.warning(f"⚠️  Variable name '{name}' may cause issues in some environments")
            
        # Convert value to string if needed
        if not isinstance(value, str):
            original_type = type(value).__name__
            value = str(value)
            logger.debug(f"🔄 Converted {original_type} to string for {name}")
        
        # Use the enhanced output manager
        output_manager.add_output(name, value)
        
        # Legacy subprocess call for compatibility (with error handling)
        try:
            subprocess.run(f"export {name}", shell=True, check=False, capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️  Export subprocess timeout for {name}")
        except Exception as e:
            logger.debug(f"🔍 Subprocess export failed for {name}: {e} (this is expected in some environments)")
            
    except Exception as e:
        logger.error(f"❌ Failed to export variable {name}: {e}")
        raise ValueError(f"Failed to export {name}: {e}")


def fetch_tags_from_api(asset_id: str, api_url: str, retry_attempts: int = 3) -> Dict[str, str]:
    """Enhanced API tag fetching with retries, comprehensive error handling, and monitoring."""
    if not asset_id or not asset_id.strip():
        logger.warning("⚠️  Asset ID is empty, skipping API call")
        return {}
        
    logger.info(f"🌐 Fetching tags for asset_id: {asset_id}")
    
    for attempt in range(retry_attempts):
        try:
            # Construct and validate URL
            url = f"{api_url}?asset_id={asset_id.strip()}"
            logger.debug(f"🔗 API URL: {url}")
            
            # Create request with headers
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Harness-Workspace-Plugin/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            # Make request with timeout
            api_start = time.time()
            with urllib.request.urlopen(req, timeout=30) as response:
                api_duration = time.time() - api_start
                logger.debug(f"⏱️  API response time: {round(api_duration * 1000, 2)}ms")
                
                response_body = response.read().decode('utf-8')
                logger.debug(f"📥 Response size: {len(response_body)} bytes")
                
                if response.status == 200:
                    data = json.loads(response_body)
                    
                    if data and len(data) > 0:
                        # Extract tags with validation
                        properties = data[0].get('properties', {})
                        if not isinstance(properties, dict):
                            logger.warning("⚠️  Properties is not a dict, skipping tags")
                            return {}
                            
                        tags = properties.get('tags', {})
                        if not isinstance(tags, dict):
                            logger.warning("⚠️  Tags is not a dict, returning empty")
                            return {}
                        
                        # Convert all tag values to strings and validate
                        tags_map = {}
                        for k, v in tags.items():
                            if isinstance(k, str) and k.strip():
                                tags_map[k] = str(v) if v is not None else ""
                            else:
                                logger.debug(f"🔍 Skipping invalid tag key: {k}")
                        
                        logger.info(f"✅ Retrieved {len(tags_map)} tags")
                        if logger.debug_mode:
                            for k, v in tags_map.items():
                                logger.debug(f"  🏷️  {k}: {v[:50]}{'...' if len(str(v)) > 50 else ''}")
                        
                        return tags_map
                    else:
                        logger.warning(f"⚠️  No data returned for asset_id: {asset_id}")
                        return {}
                else:
                    logger.error(f"❌ API returned status code: {response.status}")
                    
                    # Try to read error response
                    try:
                        error_body = response_body[:500]  # Limit error body size
                        logger.debug(f"🔍 Error response: {error_body}")
                    except Exception:
                        pass
                    
                    return {}
                    
        except urllib.error.HTTPError as e:
            logger.error(f"❌ HTTP Error (attempt {attempt + 1}/{retry_attempts}): {e.code} - {e.reason}")
            
            # Don't retry on client errors (4xx)
            if 400 <= e.code < 500:
                logger.warning("⚠️  Client error, not retrying")
                break
                
        except urllib.error.URLError as e:
            logger.error(f"❌ Network Error (attempt {attempt + 1}/{retry_attempts}): {e.reason}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Parse Error (attempt {attempt + 1}/{retry_attempts}): {e}")
            
        except socket.timeout:
            logger.error(f"❌ Request timeout (attempt {attempt + 1}/{retry_attempts})")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error (attempt {attempt + 1}/{retry_attempts}): {e}")
            
            if logger.debug_mode:
                logger.error("🔍 Full traceback:", exc_info=True)
        
        # Wait before retry (exponential backoff)
        if attempt < retry_attempts - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s...
            logger.info(f"⏳ Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    logger.warning(f"⚠️  Failed to fetch tags after {retry_attempts} attempts, returning empty dict")
    return {}

def normalize_name(name: str) -> str:
    """
    Normalize resource name: lowercase and replace hyphens with underscores.
    """
    return name.lower().replace('-', '_')


def process_delete_action(component_name_list: str, iteration: int) -> None:
    """
    Process 'delete' action workflow.
    """
    logger.info("=" * 60)
    logger.info("Processing 'delete' action")
    logger.info("=" * 60)
    
    try:
        # Split component names by comma
        component_names = [name.strip() for name in component_name_list.split(',')]
        
        if iteration >= len(component_names):
            raise ValueError(f"Iteration {iteration} out of range for component names (max: {len(component_names) - 1})")
        
        current_component = component_names[iteration]
        logger.info(f"Current iteration: {iteration}")
        logger.info(f"Current component: {current_component}")
        
        # Export environment variables
        logger.info("")
        logger.info("Exporting environment variables:")
        export_env_var('resourceName', current_component)
        export_env_var('entityId', current_component)
        
    except Exception as e:
        logger.error(f"Error processing 'delete' action: {e}", exc_info=True)
        raise


def process_update_action(component_name_list: str, iteration: int, repeat_item: str,
                          asset_id: str, resource_config_str: str, cloud_project: str,
                          api_url: str) -> None:
    """
    Process 'update' action workflow.
    """
    logger.info("=" * 60)
    logger.info("Processing 'update' action")
    logger.info("=" * 60)
    
    try:
        # Split component names by comma
        component_names = [name.strip() for name in component_name_list.split(',')]
        
        if iteration >= len(component_names):
            raise ValueError(f"Iteration {iteration} out of range for component names (max: {len(component_names) - 1})")
        
        current_component = component_names[iteration]
        logger.info(f"Current iteration: {iteration}")
        logger.info(f"Current component: {current_component}")
        logger.info(f"Workspace name: {repeat_item}")
        
        # Parse resource configuration
        resource_config = safe_json_parse(resource_config_str, "resource configuration")
        
        # Get the resource config for this iteration
        entries = resource_config.get('entries', [])
        if iteration >= len(entries):
            raise ValueError(f"Iteration {iteration} out of range for entries (max: {len(entries) - 1})")
        
        workspace_vars = entries[iteration]
        logger.info(f"Workspace variables for iteration {iteration}: {workspace_vars}")
        
        # Process connector name
        connector = cloud_project.replace('-', '_')
        logger.info(f"Connector: {connector}")
        
        # Extract values from workspace vars
        module_name = workspace_vars.get('module_name', '')
        
        # Filter terraform vars - remove specific keys
        filtered_terraform_vars = {k: v for k, v in workspace_vars.items() 
                                   if k not in ['module_name', 'cloud_project', 'type', 'show_advanced']}
        
        # Fetch tags from API and add to terraform vars
        tags_map = fetch_tags_from_api(asset_id, api_url)
        if tags_map:
            filtered_terraform_vars['cdk_std_tags'] = tags_map
        
        terraform_vars_json = json.dumps(filtered_terraform_vars, separators=(',', ':'))
        logger.info(f"Filtered terraform vars: {terraform_vars_json[:200]}...")
        
        # Export environment variables
        logger.info("")
        logger.info("Exporting environment variables:")
        export_env_var('resourceName', current_component)
        export_env_var('entityId', current_component)
        export_env_var('workspaceName', repeat_item)
        export_env_var('assetId', asset_id)
        export_env_var('terraformVars', terraform_vars_json)
        export_env_var('connector', connector)
        export_env_var('moduleName', module_name)
        
    except Exception as e:
        logger.error(f"Error processing 'update' action: {e}", exc_info=True)
        raise


def process_create_action(repeat_item: str, item_map_str: str, asset_id: str,
                          cloud_project: str, deployment_name: str, iteration: int,
                          api_url: str) -> None:
    """
    Process 'create' action workflow.
    """
    logger.info("=" * 60)
    logger.info("Processing 'create' action")
    logger.info("=" * 60)
    
    try:
        logger.info(f"Workspace name: {repeat_item}")
        logger.info(f"Iteration: {iteration}")
        
        # Parse item map
        item_map = safe_json_parse(item_map_str, "item map")
        
        # Find workspace vars for this workspace name
        workspace_vars = None
        for item in item_map:
            if repeat_item in item:
                workspace_vars = item[repeat_item]
                break
        
        if not workspace_vars:
            raise ValueError(f"Workspace '{repeat_item}' not found in item_map")
        
        logger.info(f"Workspace variables: {workspace_vars}")
        
        # Process connector name
        connector = cloud_project.replace('-', '_')
        logger.info(f"Connector: {connector}")
        
        # Extract values from workspace vars
        module_name = workspace_vars.get('module_name', '')
        resource_name = workspace_vars.get('resource_name', '')
        resource_type = workspace_vars.get('type', '')
        
        logger.info(f"Module: {module_name}, Resource: {resource_name}, Type: {resource_type}")
        
        # Filter terraform vars - remove specific keys
        filtered_terraform_vars = {k: v for k, v in workspace_vars.items() 
                                   if k not in ['module_name', 'connector', 'type', 'show_advanced']}
        
        # Fetch tags from API and add to terraform vars
        tags_map = fetch_tags_from_api(asset_id, api_url)
        if tags_map:
            filtered_terraform_vars['cdk_std_tags'] = tags_map
        
        terraform_vars_json = json.dumps(filtered_terraform_vars, separators=(',', ':'))
        logger.info(f"Final terraform vars: {terraform_vars_json[:200]}...")
        
        # Generate resource name and entity ID
        resource_name_raw = f"{resource_type}_{resource_name}_{deployment_name}{iteration}"
        entity_id_raw = f"{resource_type}_{resource_name}_{deployment_name}{iteration}"
        
        resource_name_normalized = normalize_name(resource_name_raw)
        entity_id_normalized = normalize_name(entity_id_raw)
        
        logger.info(f"Resource name: {resource_name_normalized}")
        logger.info(f"Entity ID: {entity_id_normalized}")
        
        # Export environment variables
        logger.info("")
        logger.info("Exporting environment variables:")
        export_env_var('workspaceName', repeat_item)
        export_env_var('assetId', asset_id)
        export_env_var('terraformVars', terraform_vars_json)
        export_env_var('connector', connector)
        export_env_var('moduleName', module_name)
        export_env_var('resourceName', resource_name_normalized)
        export_env_var('entityId', entity_id_normalized)
        
    except Exception as e:
        logger.error(f"Error processing 'create' action: {e}", exc_info=True)
        raise


def main():
    """Enhanced main execution function with comprehensive error handling and monitoring."""
    exit_code = 0
    execution_start = time.time()
    
    try:
        # Print enhanced startup banner
        logger.info("🚀 " + "=" * 68)
        logger.info("🚀 HARNESS WORKSPACE PREPARATION PLUGIN - EXECUTION STARTED")
        logger.info("🚀 " + "=" * 68)
        
        # Log system information in debug mode
        if logger.debug_mode:
            logger.debug(f"🐍 Python Version: {sys.version}")
            logger.debug(f"💻 Platform: {sys.platform}")
            logger.debug(f"📁 Working Directory: {os.getcwd()}")
            logger.debug(f"🌍 Environment Variables: {len(os.environ)} total")
        
        # Read and validate plugin configuration from PLUGIN_ environment variables
        logger.info("📋 Reading plugin configuration...")
        
        # Validate required action variable
        action = os.environ.get('PLUGIN_ACTION')
        if not action:
            raise ValueError("PLUGIN_ACTION environment variable is required")
            
        logger.info(f"🎬 Workspace Preparation Action: {action}")
        
        # Validate action
        valid_actions = ['create', 'update', 'delete']
        if action not in valid_actions:
            raise ValueError(f"Invalid action '{action}'. Must be one of: {valid_actions}")
        
        # Validate required common variables
        org_identifier = os.environ.get('PLUGIN_ORG_IDENTIFIER')
        project_identifier = os.environ.get('PLUGIN_PROJECT_IDENTIFIER')
        resource_owner = os.environ.get('PLUGIN_RESOURCE_OWNER')
        
        if not org_identifier:
            raise ValueError("PLUGIN_ORG_IDENTIFIER environment variable is required")
        if not project_identifier:
            raise ValueError("PLUGIN_PROJECT_IDENTIFIER environment variable is required")
        if not resource_owner:
            raise ValueError("PLUGIN_RESOURCE_OWNER environment variable is required")
        
        logger.debug(f"🏢 Organization: {org_identifier}")
        logger.debug(f"📁 Project: {project_identifier}")
        logger.debug(f"👤 Resource Owner: {resource_owner[:50]}{'...' if len(resource_owner) > 50 else ''}")
        
        # API endpoint with validation
        api_url = os.environ.get('PLUGIN_API_URL', "https://svc-pangea-api-nginx.int.nebula-dit.connectcdk.com/api/projects")
        logger.debug(f"🌐 API URL: {api_url}")
        
        # Process based on action with validation
        logger.info(f"⚙️  Processing '{action}' action workflow...")
        
        if action == "delete":
            component_name = os.environ.get('PLUGIN_COMPONENT_NAME')
            iteration_str = os.environ.get('PLUGIN_ITERATION')
            
            if not component_name:
                raise ValueError("PLUGIN_COMPONENT_NAME environment variable is required for delete action")
            if not iteration_str:
                raise ValueError("PLUGIN_ITERATION environment variable is required for delete action")
            
            try:
                iteration = int(iteration_str)
            except (ValueError, TypeError):
                raise ValueError(f"PLUGIN_ITERATION must be a valid integer, got: {iteration_str}")
            
            process_delete_action(
                component_name_list=component_name,
                iteration=iteration
            )
            
        elif action == "update":
            component_name = os.environ.get('PLUGIN_COMPONENT_NAME')
            iteration_str = os.environ.get('PLUGIN_ITERATION')
            repeat_item = os.environ.get('PLUGIN_REPEAT_ITEM')
            asset_id = os.environ.get('PLUGIN_ASSET_ID')
            resource_config = os.environ.get('PLUGIN_RESOURCE_CONFIG')
            cloud_project = os.environ.get('PLUGIN_CLOUD_PROJECT')
            
            if not component_name:
                raise ValueError("PLUGIN_COMPONENT_NAME environment variable is required for update action")
            if not iteration_str:
                raise ValueError("PLUGIN_ITERATION environment variable is required for update action")
            if not repeat_item:
                raise ValueError("PLUGIN_REPEAT_ITEM environment variable is required for update action")
            if not asset_id:
                raise ValueError("PLUGIN_ASSET_ID environment variable is required for update action")
            if not resource_config:
                raise ValueError("PLUGIN_RESOURCE_CONFIG environment variable is required for update action")
            if not cloud_project:
                raise ValueError("PLUGIN_CLOUD_PROJECT environment variable is required for update action")
            
            try:
                iteration = int(iteration_str)
            except (ValueError, TypeError):
                raise ValueError(f"PLUGIN_ITERATION must be a valid integer, got: {iteration_str}")
            
            process_update_action(
                component_name_list=component_name,
                iteration=iteration,
                repeat_item=repeat_item,
                asset_id=asset_id,
                resource_config_str=resource_config,
                cloud_project=cloud_project,
                api_url=api_url
            )
            
        else:  # create action
            repeat_item = os.environ.get('PLUGIN_REPEAT_ITEM')
            item_map = os.environ.get('PLUGIN_ITEM_MAP')
            asset_id = os.environ.get('PLUGIN_ASSET_ID')
            cloud_project = os.environ.get('PLUGIN_CLOUD_PROJECT')
            deployment_name = os.environ.get('PLUGIN_DEPLOYMENT_NAME')
            iteration_str = os.environ.get('PLUGIN_ITERATION')
            
            if not repeat_item:
                raise ValueError("PLUGIN_REPEAT_ITEM environment variable is required for create action")
            if not item_map:
                raise ValueError("PLUGIN_ITEM_MAP environment variable is required for create action")
            if not asset_id:
                raise ValueError("PLUGIN_ASSET_ID environment variable is required for create action")
            if not cloud_project:
                raise ValueError("PLUGIN_CLOUD_PROJECT environment variable is required for create action")
            if not deployment_name:
                raise ValueError("PLUGIN_DEPLOYMENT_NAME environment variable is required for create action")
            if not iteration_str:
                raise ValueError("PLUGIN_ITERATION environment variable is required for create action")
            
            try:
                iteration = int(iteration_str)
            except (ValueError, TypeError):
                raise ValueError(f"PLUGIN_ITERATION must be a valid integer, got: {iteration_str}")
            
            process_create_action(
                repeat_item=repeat_item,
                item_map_str=item_map,
                asset_id=asset_id,
                cloud_project=cloud_project,
                deployment_name=deployment_name,
                iteration=iteration,
                api_url=api_url
            )
        
        # Export common variables with camelCase naming
        logger.info("📤 Exporting common environment variables...")
        
        entity_scope = f"account.{org_identifier}.{project_identifier}"
        entity_id = os.environ.get('entityId', '')
        entity_ref = f"{entity_scope}/{entity_id}" if entity_id else entity_scope
        
        export_env_var('resourceOwner', resource_owner)
        export_env_var('entityScope', entity_scope)
        export_env_var('entityRef', entity_ref)
        
        logger.info(f"🔗 Entity Reference: {entity_ref}")
        
        # Finalize all outputs
        logger.info("🎯 Finalizing outputs...")
        output_manager.finalize_outputs()
        
        # Success banner
        logger.info("✅ " + "=" * 68)
        logger.info("✅ WORKSPACE PREPARATION COMPLETED SUCCESSFULLY")
        logger.info("✅ " + "=" * 68)
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Execution interrupted by user (Ctrl+C)")
        exit_code = 130
        
    except ValueError as e:
        logger.error("❌ " + "=" * 68)
        logger.error("❌ VALIDATION ERROR IN WORKSPACE PREPARATION")
        logger.error("❌ " + "=" * 68)
        logger.error(f"💥 Validation Error: {e}")
        if logger.debug_mode:
            logger.error("🔍 Full traceback:", exc_info=True)
        exit_code = 2
        
    except Exception as e:
        logger.error("💥 " + "=" * 68)
        logger.error("💥 FATAL ERROR IN WORKSPACE PREPARATION")
        logger.error("💥 " + "=" * 68)
        logger.error(f"💥 Error: {e}")
        
        if logger.debug_mode:
            logger.error("🔍 Full traceback:", exc_info=True)
        
        exit_code = 1
    
    finally:
        execution_duration = time.time() - execution_start
        logger.info(f"⏱️  Total execution time: {round(execution_duration * 1000, 2)}ms")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
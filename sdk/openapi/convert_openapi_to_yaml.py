"""
Convert openapi.json to yaml, filtering for only SDK-relevant routes.

This script:
1. Reads the openapi.json file
2. Filters paths to only include routes used in Python/Go SDKs
3. Improves operationIds to be more user-friendly for SDK function names
4. Extracts all referenced schemas and their dependencies
5. Converts to YAML format
6. Outputs as plato.yaml
"""

import json
import sys

# Routes to include (based on SDK usage)
ROUTES_TO_INCLUDE = {
    # Python SDK - Environment Management
    "/api/env/make2": ["post"],
    "/api/env/{job_group_id}/status": ["get"],
    "/api/env/{job_group_id}/cdp_url": ["get"],
    "/api/env/{job_group_id}/proxy_url": ["get"],
    "/api/env/{job_group_id}/close": ["post"],
    "/api/env/{job_group_id}/backup": ["post"],
    "/api/env/{job_group_id}/reset": ["post"],
    "/api/env/{job_group_id}/state": ["get"],
    "/api/env/{job_id}/worker_ready": ["get"],
    "/api/env/{job_id}/heartbeat": ["post"],
    "/api/env/{job_group_id}/active_session": ["get"],
    "/api/env/session/{session_id}/evaluate": ["post"],
    "/api/env/session/{session_id}/score": ["post"],
    "/api/env/{session_id}/log": ["post"],
    "/api/env/simulators": ["get", "post"],
    
    # Python SDK - Simulator Routes
    "/api/simulator/{artifact_id}/flows": ["get"],
    "/api/simulator/{simulator_name}/versions": ["get"],
    "/api/simulator/{artifact_id}/db_config": ["get"],
    
    # Python SDK - Gitea Routes
    "/api/gitea/my-info": ["get"],
    "/api/gitea/simulators": ["get"],
    "/api/gitea/simulators/{simulator_id}/repo": ["get", "post"],
    "/api/gitea/credentials": ["get"],
    
    # Go SDK - Public Build / Sandbox Management
    "/api/public-build/vm/create": ["post"],
    "/api/public-build/events/{correlation_id}": ["get"],
    "/api/public-build/vm/{public_id}/setup-sandbox": ["post"],
    "/api/public-build/vm/{public_id}": ["delete"],
    "/api/public-build/vm/{public_id}/setup-root-access": ["post"],
    "/api/public-build/vm/{public_id}/snapshot": ["post"],
    "/api/public-build/vm/{public_id}/checkpoint": ["post"],
    "/api/public-build/vm/{public_id}/start-worker": ["post"],
    
    # Testcases endpoint (used by Python SDK)
    "/api/testcases": ["get"],
    
    # Running sessions count (used by Python SDK)
    "/api/user/organization/running-sessions": ["get"],
}

# Mapping of verbose operationIds to user-friendly SDK function names
# This makes generated SDK code much more readable
OPERATION_ID_MAPPINGS = {
    # Environment Operations
    'make_env_api_env_make2_post': 'makeEnvironment',
    'evaluate_session_api_env_session__session_id__evaluate_post': 'evaluateSession',
    'get_job_status_api_env__job_group_id__status_get': 'getJobStatus',
    'keep_alive_api_env__job_group_id__keep_alive_post': 'keepEnvironmentAlive',
    'close_env_api_env__job_group_id__close_post': 'closeEnvironment',
    'reset_env_api_env__job_group_id__reset_post': 'resetEnvironment',
    'take_screenshot_api_env__job_group_id__screenshot_post': 'takeScreenshot',
    'get_db_config_api_env__job_group_id__db_config_get': 'getDbConfig',
    'get_worker_ready_api_env__job_group_id__ready_get': 'getWorkerReady',
    'batch_log_api_env_batch_log_post': 'batchLog',
    'get_cdp_url_api_env__job_group_id__cdp_url_get': 'getCdpUrl',
    'get_proxy_url_api_env__job_group_id__proxy_url_get': 'getProxyUrl',
    'get_env_state_api_env__job_group_id__state_get': 'getEnvironmentState',
    'backup_env_api_env__job_group_id__backup_post': 'backupEnvironment',
    'get_active_session_api_env__job_group_id__active_session_get': 'getActiveSession',
    'score_session_api_env_session__session_id__score_post': 'scoreSession',
    'log_api_env__session_id__log_post': 'logToEnvironment',
    'heartbeat_api_env__job_id__heartbeat_post': 'sendHeartbeat',
    'get_simulators_api_env_simulators_get': 'getSimulators',
    'create_simulator_api_env_simulators_post': 'createSimulator',
    
    # VM/Public Build Operations
    'create_vm_api_public_build_vm_create_post': 'createVM',
    'keep_vm_alive_api_public_build_vm__public_id__keep_alive_post': 'keepVMAlive',
    'close_vm_api_public_build_vm__public_id__close_post': 'closeVM',
    'delete_vm_api_public_build_vm__public_id__delete': 'deleteVM',
    'setup_sandbox_api_public_build_vm__public_id__setup_sandbox_post': 'setupSandbox',
    'setup_root_password_api_public_build_vm__public_id__setup_root_access_post': 'setupRootPassword',
    'get_operation_events_api_public_build_events__correlation_id__get': 'getOperationEvents',
    'vm_management_api_public_build_vm__public_id__management_post': 'manageVM',
    'snapshot_vm_api_public_build_vm__public_id__snapshot_post': 'snapshotVM',
    'checkpoint_vm_api_public_build_vm__public_id__checkpoint_post': 'checkpointVM',
    'start_worker_api_public_build_vm__public_id__start_worker_post': 'startWorker',
    
    # Simulator Operations  
    'get_simulator_flows_api_simulator__artifact_id__flows_get': 'getSimulatorFlows',
    'get_simulator_versions_api_simulator__simulator_name__versions_get': 'getSimulatorVersions',
    'get_simulator_db_config_api_simulator__artifact_id__db_config_get': 'getSimulatorDbConfig',
    
    # Gitea Operations
    'get_gitea_my_info_api_gitea_my_info_get': 'getGiteaMyInfo',
    'get_gitea_simulators_api_gitea_simulators_get': 'getGiteaSimulators',
    'get_gitea_simulator_repo_api_gitea_simulators__simulator_id__repo_get': 'getGiteaSimulatorRepo',
    'create_gitea_simulator_repo_api_gitea_simulators__simulator_id__repo_post': 'createGiteaSimulatorRepo',
    'get_gitea_credentials_api_gitea_credentials_get': 'getGiteaCredentials',
    
    # Test Cases Operations
    'get_testcases_api_testcases_get': 'getTestcases',
    
    # User Operations
    'get_running_sessions_api_user_organization_running_sessions_get': 'getRunningSessionsCount',
}


def improve_operation_ids(paths):
    """
    Improve operationIds in the filtered paths to be more user-friendly.
    Returns the number of operationIds that were updated.
    """
    updated_count = 0
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if 'operationId' in operation:
                old_id = operation['operationId']
                
                if old_id in OPERATION_ID_MAPPINGS:
                    new_id = OPERATION_ID_MAPPINGS[old_id]
                    operation['operationId'] = new_id
                    updated_count += 1
                    print(f"  ✨ {old_id} → {new_id}")
    
    return updated_count


def extract_schema_refs(obj, refs_set):
    """Recursively extract all $ref schema references from an object."""
    if isinstance(obj, dict):
        if '$ref' in obj:
            ref = obj['$ref']
            if ref.startswith('#/components/schemas/'):
                refs_set.add(ref.split('/')[-1])
        for value in obj.values():
            extract_schema_refs(value, refs_set)
    elif isinstance(obj, list):
        for item in obj:
            extract_schema_refs(item, refs_set)


def get_all_dependent_schemas(schema_name, all_schemas, result_set):
    """Recursively get all schemas that a given schema depends on."""
    if schema_name in result_set or schema_name not in all_schemas:
        return
    
    result_set.add(schema_name)
    schema = all_schemas[schema_name]
    
    # Find all refs in this schema
    refs = set()
    extract_schema_refs(schema, refs)
    
    # Recursively process dependencies
    for ref in refs:
        get_all_dependent_schemas(ref, all_schemas, result_set)


def dict_to_yaml(d, indent=0):
    """Convert a dictionary to YAML format with proper indentation."""
    lines = []
    indent_str = '  ' * indent
    
    if isinstance(d, dict):
        for key, value in d.items():
            if value is None:
                lines.append(f"{indent_str}{key}:")
            elif isinstance(value, (dict, list)):
                if isinstance(value, dict) and len(value) == 0:
                    lines.append(f"{indent_str}{key}: {{}}")
                elif isinstance(value, list) and len(value) == 0:
                    lines.append(f"{indent_str}{key}: []")
                else:
                    lines.append(f"{indent_str}{key}:")
                    lines.extend(dict_to_yaml(value, indent + 1))
            elif isinstance(value, bool):
                lines.append(f"{indent_str}{key}: {str(value).lower()}")
            elif isinstance(value, str):
                # Handle multiline strings
                if '\n' in value:
                    lines.append(f"{indent_str}{key}: |")
                    for line in value.split('\n'):
                        lines.append(f"{indent_str}  {line}")
                else:
                    # Escape strings that need quotes
                    needs_quotes = (
                        ':' in value or 
                        '#' in value or 
                        value.startswith(('&', '*', '!', '|', '>', '@', '`', '"', "'")) or
                        value in ('true', 'false', 'yes', 'no', 'null')
                    )
                    if needs_quotes:
                        # Escape quotes in the value
                        escaped = value.replace('"', '\\"')
                        lines.append(f'{indent_str}{key}: "{escaped}"')
                    else:
                        lines.append(f"{indent_str}{key}: {value}")
            elif isinstance(value, (int, float)):
                lines.append(f"{indent_str}{key}: {value}")
            else:
                lines.append(f"{indent_str}{key}: {value}")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (dict, list)):
                if isinstance(item, dict):
                    # For dict items, put first key on same line as dash
                    if item:
                        first_key = list(item.keys())[0]
                        first_value = item[first_key]
                        if isinstance(first_value, (dict, list)):
                            lines.append(f"{indent_str}- {first_key}:")
                            lines.extend(dict_to_yaml(first_value, indent + 2))
                            # Process remaining keys
                            for key in list(item.keys())[1:]:
                                value = item[key]
                                if isinstance(value, (dict, list)):
                                    lines.append(f"{indent_str}  {key}:")
                                    lines.extend(dict_to_yaml(value, indent + 2))
                                else:
                                    lines.extend(dict_to_yaml({key: value}, indent + 1))
                        else:
                            lines.append(f"{indent_str}-")
                            lines.extend(dict_to_yaml(item, indent + 1))
                    else:
                        lines.append(f"{indent_str}- {{}}")
                else:
                    lines.append(f"{indent_str}-")
                    lines.extend(dict_to_yaml(item, indent + 1))
            else:
                if isinstance(item, bool):
                    lines.append(f"{indent_str}- {str(item).lower()}")
                elif isinstance(item, str):
                    needs_quotes = ':' in item or '#' in item
                    if needs_quotes:
                        lines.append(f'{indent_str}- "{item}"')
                    else:
                        lines.append(f"{indent_str}- {item}")
                else:
                    lines.append(f"{indent_str}- {item}")
    
    return lines


def clean_enum_defaults(obj):
    """Remove default values from enum fields (Fern doesn't like them)."""
    if isinstance(obj, dict):
        # If this object has both 'enum' and 'default', remove the default
        if 'enum' in obj and 'default' in obj:
            del obj['default']
        
        # Recursively clean nested objects
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                clean_enum_defaults(value)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                clean_enum_defaults(item)
    
    return obj


def fix_sse_endpoint(path_spec):
    """Fix SSE endpoint to use text/event-stream with Fern streaming extensions."""
    if '200' in path_spec.get('responses', {}):
        response_200 = path_spec['responses']['200']
        if 'content' in response_200:
            # Replace application/json with text/event-stream for SSE
            if 'application/json' in response_200['content']:
                response_200['content']['text/event-stream'] = {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'type': {
                                'type': 'string',
                                'description': 'Event type',
                                'enum': ['connected', 'progress', 'complete', 'error']
                            },
                            'success': {
                                'type': 'boolean',
                                'description': 'Whether the operation succeeded'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'Human-readable message'
                            },
                            'error': {
                                'type': 'string',
                                'description': 'Error details if failed'
                            }
                        },
                        'required': ['type']
                    },
                    'x-fern-streaming': {
                        'format': 'sse',
                        'stream-type': 'object'
                    }
                }
                del response_200['content']['application/json']
                response_200['description'] = 'Server-Sent Events stream'
        
        # Update description to be more detailed
        if 'description' in path_spec:
            path_spec['description'] = (
                'Stream operation results via Server-Sent Events (SSE) for public usage.\n\n'
                'Returns a stream of events with the following format:\n'
                '- event: Event type (e.g., "connected", "progress", "complete", "error")\n'
                '- data: JSON payload with event details\n\n'
                'Events:\n'
                '- connected: Initial connection established\n'
                '- progress: Operation progress update\n'
                '- complete: Operation completed successfully\n'
                '- error: Operation failed with error details'
            )


def main():
    print("🔄 Converting openapi.json to plato.yaml...")
    
    # Read openapi.json
    try:
        with open('openapi.json', 'r') as f:
            spec = json.load(f)
        print("✅ Loaded openapi.json")
    except FileNotFoundError:
        print("❌ Error: openapi.json not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing openapi.json: {e}")
        sys.exit(1)
    
    # Filter paths
    filtered_paths = {}
    for path, methods in ROUTES_TO_INCLUDE.items():
        if path in spec.get('paths', {}):
            filtered_paths[path] = {}
            for method in methods:
                if method in spec['paths'][path]:
                    filtered_paths[path][method] = spec['paths'][path][method]
                    
                    # Fix SSE endpoint for /public-build/events/{correlation_id}
                    if path == "/api/public-build/events/{correlation_id}" and method == "get":
                        fix_sse_endpoint(filtered_paths[path][method])
                        print("✅ Fixed SSE endpoint for /public-build/events/{correlation_id}")
                else:
                    print(f"⚠️  Warning: Method {method.upper()} not found for {path}")
        else:
            print(f"⚠️  Warning: Path {path} not found in openapi.json")
    
    print(f"✅ Filtered {len(filtered_paths)} paths with {sum(len(m) for m in filtered_paths.values())} methods")
    
    # Improve operationIds to be more user-friendly
    print("🔧 Improving operationIds for better SDK function names...")
    updated_count = improve_operation_ids(filtered_paths)
    print(f"✅ Updated {updated_count} operationIds")
    
    # Extract all schema references from filtered paths
    schema_refs = set()
    for path_spec in filtered_paths.values():
        extract_schema_refs(path_spec, schema_refs)
    
    print(f"✅ Found {len(schema_refs)} directly referenced schemas")
    
    # Get all dependent schemas recursively
    all_schemas = spec.get('components', {}).get('schemas', {})
    required_schemas = set()
    for schema_name in schema_refs:
        get_all_dependent_schemas(schema_name, all_schemas, required_schemas)
    
    print(f"✅ Including {len(required_schemas)} total schemas (with dependencies)")
    
    # Build filtered schemas dict
    filtered_schemas = {}
    for schema_name in sorted(required_schemas):
        if schema_name in all_schemas:
            filtered_schemas[schema_name] = all_schemas[schema_name]
    
    # Clean enum defaults from all schemas (Fern doesn't support them)
    print("🔧 Removing default values from enum fields...")
    for schema_name in filtered_schemas:
        clean_enum_defaults(filtered_schemas[schema_name])
    
    # Remove /api prefix from paths for cleaner API
    clean_paths = {}
    for path, methods in filtered_paths.items():
        clean_path = path.replace('/api', '')
        clean_paths[clean_path] = methods
    
    # Build output spec
    output_spec = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Plato API',
            'version': '1.0.0',
            'description': 'API for Plato platform - SDK routes only'
        },
        'paths': clean_paths,
        'components': {
            'schemas': filtered_schemas,
            'securitySchemes': {
                'ApiKeyAuth': {
                    'type': 'apiKey',
                    'in': 'header',
                    'name': 'X-Api-Key',
                    'description': 'API Key authentication header'
                }
            }
        },
        'security': [
            {'ApiKeyAuth': []}
        ]
    }
    
    # Convert to YAML
    print("🔄 Converting to YAML format...")
    yaml_lines = []
    
    # Add header
    yaml_lines.append("openapi: 3.0.0")
    yaml_lines.append("info:")
    yaml_lines.append("  title: Plato API")
    yaml_lines.append("  version: 1.0.0")
    yaml_lines.append("  description: API for Plato platform - SDK routes only")
    yaml_lines.append("")
    
    # Add security
    yaml_lines.append("security:")
    yaml_lines.append("  - ApiKeyAuth: []")
    yaml_lines.append("")
    
    # Add paths
    yaml_lines.append("paths:")
    for path in sorted(clean_paths.keys()):
        yaml_lines.append(f"  {path}:")
        path_yaml = dict_to_yaml(clean_paths[path], 2)
        yaml_lines.extend(path_yaml)
        yaml_lines.append("")
    
    # Add components
    yaml_lines.append("components:")
    yaml_lines.append("  schemas:")
    for schema_name in sorted(filtered_schemas.keys()):
        yaml_lines.append(f"    {schema_name}:")
        schema_yaml = dict_to_yaml(filtered_schemas[schema_name], 3)
        yaml_lines.extend(schema_yaml)
        yaml_lines.append("")
    
    # Add security schemes
    yaml_lines.append("  securitySchemes:")
    yaml_lines.append("    ApiKeyAuth:")
    yaml_lines.append("      type: apiKey")
    yaml_lines.append("      in: header")
    yaml_lines.append("      name: X-Api-Key")
    yaml_lines.append("      description: API Key authentication header")
    
    # Write to file
    output_file = 'plato.yaml'
    with open(output_file, 'w') as f:
        f.write('\n'.join(yaml_lines))
    
    print(f"✅ Successfully created {output_file}")
    print(f"\n📊 Summary:")
    print(f"   Paths: {len(clean_paths)}")
    print(f"   Methods: {sum(len(m) for m in clean_paths.values())}")
    print(f"   Schemas: {len(filtered_schemas)}")
    print(f"\n✨ Done!")


if __name__ == '__main__':
    main()

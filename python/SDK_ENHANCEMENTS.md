# Plato SDK Enhancements

This document outlines the new functionality added to the Plato SDK for Play-Doh environment configuration and S3 download capabilities.

## Summary

Two new functions have been added to both the async (`sdk.py`) and sync (`sync_sdk.py`) versions of the Plato SDK:

1. **`get_playdoh_environment_config(env_name)`** - Retrieve configuration for any environment by name
2. **`download_from_s3(s3_path, local_path)`** - Download files from S3 using S3 paths

## Functions Added

### `get_playdoh_environment_config(env_name: str = "playdoh") -> Dict[str, Any]`

**Purpose**: Gets the configuration for a specified environment by calling the `listSimulators` endpoint and finding the environment by name.

**Parameters**:
- `env_name` (str): The name of the environment to get config for. Defaults to "playdoh".

**Returns**: Dictionary containing the environment configuration

**Usage**:
```python
# Async version
client = Plato()
config = await client.get_playdoh_environment_config("firefly")
print(config)  # {'type': 'docker_app', 'cookies': None, 'authentication': {...}, ...}

# Sync version
client = SyncPlato()
config = client.get_playdoh_environment_config("firefly")
```

### `download_from_s3(s3_path: str, local_path: str) -> None`

**Purpose**: Downloads a file from S3 using the provided S3 path and saves it locally.

**Parameters**:
- `s3_path` (str): The S3 path (e.g., 's3://bucket-name/path/to/file.zip')
- `local_path` (str): The local path to save the file

**Usage**:
```python
# If config contains flowsS3Path
flows_s3_path = config.get("flowsS3Path")
if flows_s3_path:
    # Async version
    await client.download_from_s3(flows_s3_path, "/tmp/flows.zip")
    
    # Sync version
    client.download_from_s3(flows_s3_path, "/tmp/flows.zip")
```

## Implementation Details

### Dependencies Added
- `boto3>=1.35.0` - For S3 operations
- `requests>=2.28.0` - For HTTP requests in sync SDK

### Error Handling
- Both functions include comprehensive error handling
- `get_playdoh_environment_config` raises `PlatoClientError` if environment not found
- `download_from_s3` handles AWS credential errors and S3 access errors gracefully

### S3 Path Parsing
The S3 download function correctly parses S3 paths in the format `s3://bucket-name/path/to/file` and uses boto3 to perform the download.

## Testing Results

The implementation was tested with the provided API credentials:
- ✅ Successfully connects to Plato API
- ✅ Successfully lists 63 available simulators
- ✅ Successfully retrieves configuration for available environments (e.g., 'firefly')
- ✅ S3 download function correctly handles authentication errors and invalid paths
- ✅ Both async and sync versions work correctly

## Available Environments

Based on testing, the following environments are available (note: no 'playdoh' environment was found, but the function can work with any environment name):

- firefly, bugsink, odooattendances, taiga, redmine, odooelearning, nextcloud, odoopurchase
- craigslist, getcalfresh, suitecrm, odoorecruitment, metabase, hubspot, odooevents
- google_calendar, delta, odoo, costco, odoocrm, odooemailmarketing, opencart
- And 40+ more environments...

## Usage Example

```python
import asyncio
from plato.sdk import Plato

async def main():
    client = Plato()
    
    try:
        # Get config for any environment
        config = await client.get_playdoh_environment_config("firefly")
        
        # Check if flowsS3Path exists
        if "flowsS3Path" in config:
            await client.download_from_s3(config["flowsS3Path"], "/tmp/flows.zip")
            
    finally:
        await client.close()

asyncio.run(main())
```

The functions are now ready for use and will work with any environment that includes the `flowsS3Path` in its configuration.
# OpenAPI Spec Management

This directory contains scripts and configurations for managing the Plato API OpenAPI specification.

## Files

- **`openapi.json`** - Full OpenAPI spec exported from FastAPI backend
- **`plato.yaml`** - Filtered SDK-only spec in YAML format (generated)
- **`generate_sdk.py`** - Main SDK generation script

## Workflow

### 1. Export OpenAPI Spec from Backend

First, export the latest OpenAPI spec from your FastAPI backend:

```bash
# From your backend directory
curl http://localhost:8000/openapi.json > sdk/openapi/openapi.json
```

### 2. Convert and Improve

Run the conversion script to:
- Filter routes to SDK-relevant endpoints only
- **Improve operationIds** for user-friendly SDK function names
- Extract required schemas and dependencies
- Convert to YAML format

```bash
cd sdk/openapi
python generate_sdk.py
```

This will create `plato.yaml` with improved operation IDs like:
- ❌ `make_env_api_env_make2_post` → ✅ `makeEnvironment`
- ❌ `create_vm_api_public_build_vm_create_post` → ✅ `createVM`
- ❌ `get_job_status_api_env__job_group_id__status_get` → ✅ `getJobStatus`

### 3. Generate SDK

After creating `plato.yaml`, generate the TypeScript SDK:

```bash
cd sdk

docker run --rm \
  -v "${PWD}/openapi:/spec" \
  -v "${PWD}/typescript-sdk:/output" \
  openapitools/openapi-generator-cli:latest generate \
  -i /spec/plato.yaml \
  -g typescript-fetch \
  -o /output \
  --additional-properties=npmName=@plato-ai/sdk,supportsES6=true,typescriptThreePlus=true
```

### 4. Build SDK

```bash
cd typescript-sdk
npm install
npm run build
```

## Customizing Operation IDs

To add or modify SDK function names, edit the `OPERATION_ID_MAPPINGS` dictionary in `generate_sdk.py`:

```python
OPERATION_ID_MAPPINGS = {
    'verbose_operation_id_from_backend': 'friendlyFunctionName',
    'another_operation_id': 'anotherFriendlyName',
    # ... add more mappings
}
```

## Benefits of Improved Operation IDs

**Before:**
```typescript
// Generated code with ugly names
await client.env.makeEnvApiEnvMake2Post({ ... });
await client.publicBuild.createVmApiPublicBuildVmCreatePost({ ... });
```

**After:**
```typescript
// Generated code with friendly names
await client.env.makeEnvironment({ ... });
await client.publicBuild.createVM({ ... });
```

This makes the SDK much more intuitive and pleasant to use!

## Protected Files

The following files in `typescript-sdk` are protected from regeneration (via `.openapi-generator-ignore`):
- `src/client.ts` - Custom wrapper with heartbeat management
- `src/flow/**` - Flow executor for browser automation
- `README.md` - Custom documentation
- `package.json` - Custom dependencies

See [typescript-sdk/REGENERATION.md](../typescript-sdk/REGENERATION.md) for details.


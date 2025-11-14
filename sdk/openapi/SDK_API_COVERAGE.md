# Plato API - SDK Coverage and OpenAPI Schema Status

This document tracks all API endpoints used in the Plato SDKs and whether they have proper response type definitions in the **`openapi.json`** specification (the auto-generated FastAPI spec).

**Legend:**
- ✅ Has typed response schema in `openapi.json`
- ❌ Missing typed response schema in `openapi.json` (returns empty `{}`)

---

## Python SDK (`python/src/plato/sdk.py`)

### Environment Management (`/env`)

| Method | Endpoint | SDK Method | Has Schema? | Notes |
|--------|----------|------------|-------------|-------|
| POST | `/env/make2` | `make_environment()` | ❌ | Empty schema |
| GET | `/env/{job_id}/status` | `get_job_status()` | ✅ | Schema ref: #/components/schemas/JobStatusResponse |
| GET | `/env/{job_id}/cdp_url` | `get_cdp_url()` | ❌ | Empty schema |
| GET | `/env/{job_id}/proxy_url` | `get_proxy_url()` | ❌ | Empty schema |
| POST | `/env/{job_id}/close` | `close_environment()` | ❌ | Empty schema |
| POST | `/env/{job_id}/backup` | `backup_environment()` | ❌ | Empty schema |
| POST | `/env/{job_id}/reset` | `reset_environment()` | ❌ | Empty schema |
| GET | `/env/{job_id}/state` | `get_environment_state()` | ❌ | Empty schema |
| GET | `/env/{job_id}/worker_ready` | `get_worker_ready()` | ❌ | Path not found |
| POST | `/env/{job_id}/heartbeat` | `send_heartbeat()` | ❌ | Path not found |
| GET | `/env/{job_id}/active_session` | `get_active_session()` | ❌ | Empty schema |
| POST | `/env/session/{session_id}/evaluate` | `evaluate()` | ❌ | Empty schema |
| POST | `/env/session/{session_id}/score` | `post_evaluation_result()` | ❌ | Empty schema |
| POST | `/env/{session_id}/log` | `log()` | ❌ | Empty schema |
| GET | `/env/simulators` | `list_simulators()` | ❌ | Empty schema |
| POST | `/env/simulators` | `create_simulator()` | ❌ | Empty schema |

### Simulator Routes (`/simulator`)

| Method | Endpoint | SDK Method | Has Schema? | Notes |
|--------|----------|------------|-------------|-------|
| GET | `/simulator/{artifact_id}/flows` | `get_simulator_flows()` | ❌ | Empty schema |

### Gitea Routes (`/gitea`)

| Method | Endpoint | SDK Method | Has Schema? | Notes |
|--------|----------|------------|-------------|-------|
| GET | `/gitea/my-info` | `get_gitea_info()` | ✅ | Has type definition |
| GET | `/gitea/simulators` | `list_gitea_simulators()` | ✅ | Has type definition |
| GET | `/gitea/simulators/{simulator_id}/repo` | `get_simulator_repository()` | ✅ | Has type definition |
| GET | `/gitea/credentials` | `get_gitea_credentials()` | ✅ | Has type definition |
| POST | `/gitea/simulators/{simulator_id}/repo` | `create_simulator_repository()` | ✅ | Has type definition |

---

## Go SDK (`sdk/services/sandbox.go`)

### Public Build / Sandbox Management (`/public-build`)

| Method | Endpoint | SDK Method | Has Schema? | Notes |
|--------|----------|------------|-------------|-------|
| POST | `/public-build/vm/create` | `Create()` | ✅ | Schema ref: #/components/schemas/CreateVMResponse |
| GET | `/public-build/events/{correlation_id}` | `MonitorOperation()` | ❌ | Empty schema |
| POST | `/public-build/vm/{public_id}/setup-sandbox` | `SetupSandbox()` | ✅ | Schema ref: #/components/schemas/SetupSandboxResponse |
| DELETE | `/public-build/vm/{public_id}` | `DeleteVM()` | ✅ | Schema ref: #/components/schemas/VMManagementResponse |
| POST | `/public-build/vm/{public_id}/setup-root-access` | `SetupRootPassword()` | ✅ | Schema ref: #/components/schemas/VMManagementResponse |
| POST | `/public-build/vm/{public_id}/snapshot` | `CreateSnapshot()` | ✅ | Schema ref: #/components/schemas/CreateSnapshotResponse |
| POST | `/public-build/vm/{public_id}/checkpoint` | `CreateCheckpoint()` | ✅ | Schema ref: #/components/schemas/CreateSnapshotResponse |
| POST | `/public-build/vm/{public_id}/start-worker` | `StartWorker()` | ✅ | Schema ref: #/components/schemas/VMManagementResponse |

### Environment Management (`/env`)

| Method | Endpoint | SDK Method | Has Schema? | Notes |
|--------|----------|------------|-------------|-------|
| POST | `/env/{job_group_id}/heartbeat` | `SendHeartbeat()` | ❌ | Path not found |
| GET | `/env/{job_group_id}/state` | `clearEnvState()` | ❌ | Empty schema |

---

## Additional Simulator Routes

These routes are needed for simulator management and configuration:

| Method | Endpoint | Purpose | Has Schema? | Notes |
|--------|----------|---------|-------------|-------|
| GET | `/simulator/{simulator_name}/versions` | List simulator versions | ✅ | Schema ref: #/components/schemas/SimulatorVersionsResponse |
| GET | `/simulator/{artifact_id}/db_config` | Get database config | ✅ | Schema ref: #/components/schemas/DbConfigResponse |

---

## Summary

### Python SDK Coverage (openapi.json)
- **Environment (`/env`)**: 1/16 typed (6%)
- **Simulator**: 0/1 typed (0%)
- **Gitea**: 5/5 typed (100%)

### Go SDK Coverage (openapi.json)
- **Public Build (`/public-build`)**: 7/8 typed (87%)
- **Environment (`/env`)**: 0/2 typed (0%)

### Additional Routes (openapi.json)
- **Simulator routes**: 2/2 typed (100%)

### Overall
- **Total**: 15/34 endpoints have typed schemas in openapi.json (44%)
- **Missing**: 19 endpoints return empty schemas `{}`

---

## Action Items

### Critical: Add Response Models to FastAPI Backend

The following endpoints need Pydantic response models added to their FastAPI route definitions:

- `POST /env/make2` - Used by Python SDK `make_environment()`
- `GET /env/{job_group_id}/cdp_url` - Used by Python SDK `get_cdp_url()`
- `GET /env/{job_group_id}/proxy_url` - Used by Python SDK `get_proxy_url()`
- `POST /env/{job_group_id}/close` - Used by Python SDK `close_environment()`
- `POST /env/{job_group_id}/backup` - Used by Python SDK `backup_environment()`
- `POST /env/{job_group_id}/reset` - Used by Python SDK `reset_environment()`
- `GET /env/{job_group_id}/state` - Used by Python SDK `get_environment_state()`
- `GET /env/{job_group_id}/worker_ready` - Used by Python SDK `get_worker_ready()`
- `POST /env/{job_group_id}/heartbeat` - Used by Python SDK `send_heartbeat()`
- `GET /env/{job_group_id}/active_session` - Used by Python SDK `get_active_session()`
- `POST /env/session/{session_id}/evaluate` - Used by Python SDK `evaluate()`
- `POST /env/session/{session_id}/score` - Used by Python SDK `post_evaluation_result()`
- `POST /env/{session_id}/log` - Used by Python SDK `log()`
- `GET /env/simulators` - Used by Python SDK `list_simulators()`
- `POST /env/simulators` - Used by Python SDK `create_simulator()`
- `GET /simulator/{artifact_id}/flows` - Used by Python SDK `get_simulator_flows()`
- `GET /public-build/events/{correlation_id}` - Used by Go SDK `MonitorOperation()`
- `POST /env/{job_group_id}/heartbeat` - Used by Go SDK `SendHeartbeat()`
- `GET /env/{job_group_id}/state` - Used by Go SDK `clearEnvState()`

---

## Recommendation

Since the `openapi.json` is auto-generated from FastAPI, the missing schemas indicate that the FastAPI route handlers don't have proper response model type annotations. 

**To fix this:**

1. Add Pydantic response models to the FastAPI route definitions
2. Use `response_model` parameter in route decorators
3. Regenerate `openapi.json` from FastAPI

**Example:**
```python
@app.get("/env/{job_id}/active_session", response_model=ActiveSessionResponse)
async def get_active_session(job_id: str):
    # ...
    return {"session_id": session_id}
```

Alternatively, you can manually define these schemas in `plato.yaml` as you've been doing, which will be used for SDK generation.

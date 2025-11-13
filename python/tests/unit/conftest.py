"""Shared fixtures for unit tests."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any
import aiohttp
import requests


# ============================================================================
# Mock Response Fixtures
# ============================================================================

@pytest.fixture
def mock_job_response() -> Dict[str, Any]:
    """Mock response for environment creation."""
    return {
        "job_id": "test-job-123",
        "alias": "test-alias",
        "status": "running"
    }


@pytest.fixture
def mock_job_status() -> Dict[str, Any]:
    """Mock response for job status."""
    return {
        "status": "running",
        "job_id": "test-job-123",
        "ready": True
    }


@pytest.fixture
def mock_worker_ready() -> Dict[str, Any]:
    """Mock response for worker ready check."""
    return {
        "ready": True,
        "worker_ip": "192.168.1.1",
        "worker_port": 8080,
        "health_status": {"healthy": True}
    }


@pytest.fixture
def mock_cdp_response() -> Dict[str, Any]:
    """Mock response for CDP URL."""
    return {
        "error": None,
        "data": {
            "cdp_url": "ws://localhost:9222/devtools/browser/test-123"
        }
    }


@pytest.fixture
def mock_proxy_response() -> Dict[str, Any]:
    """Mock response for proxy URL."""
    return {
        "error": None,
        "data": {
            "proxy_url": "http://proxy.example.com:8080"
        }
    }


@pytest.fixture
def mock_environment_state() -> Dict[str, Any]:
    """Mock response for environment state."""
    return {
        "data": {
            "state": {
                "url": "https://example.com",
                "title": "Test Page",
                "mutations": []
            }
        }
    }


@pytest.fixture
def mock_active_session() -> Dict[str, Any]:
    """Mock response for active session."""
    return {
        "session_id": "session-123",
        "status": "active",
        "started_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_simulators_list() -> list:
    """Mock list of simulators."""
    return [
        {
            "id": 1,
            "name": "test-simulator-1",
            "enabled": True,
            "description": "Test Simulator 1"
        },
        {
            "id": 2,
            "name": "test-simulator-2",
            "enabled": True,
            "description": "Test Simulator 2"
        },
        {
            "id": 3,
            "name": "disabled-simulator",
            "enabled": False,
            "description": "Disabled Simulator"
        }
    ]


@pytest.fixture
def mock_tasks_response() -> Dict[str, Any]:
    """Mock response for tasks."""
    return {
        "testcases": [
            {
                "publicId": "task-1",
                "name": "Test Task 1",
                "prompt": "Do something",
                "startUrl": "https://example.com",
                "simulator": {"name": "test-simulator"},
                "averageTimeTaken": 30.0,
                "averageStepsTaken": 5,
                "defaultScoringConfig": {"num_sessions_used": 10},
                "scoringTypes": ["output"],  # Valid ScoringType: output or mutations
                "outputSchema": None,
                "isSample": False,
                "simulatorArtifactId": "artifact-1",
                "metadataConfig": {
                    "reasoningLevel": "level_1",  # Valid values: level_1, level_2, level_3, level_4, level_5
                    "skills": ["navigation"],
                    "capabilities": ["web"],
                    "tags": ["test"],
                    "rejected": False
                },
                "version": "1.0"
            }
        ]
    }


@pytest.fixture
def mock_evaluation_response() -> Dict[str, Any]:
    """Mock response for evaluation."""
    return {
        "score": {
            "success": True,
            "reason": "Task completed successfully",
            "score": 1.0
        }
    }


@pytest.fixture
def mock_gitea_info() -> Dict[str, Any]:
    """Mock response for Gitea info."""
    return {
        "username": "test-user",
        "org_name": "test-org",
        "email": "test@example.com"
    }


@pytest.fixture
def mock_gitea_credentials() -> Dict[str, Any]:
    """Mock response for Gitea credentials."""
    return {
        "username": "admin",
        "password": "secret123"
    }


@pytest.fixture
def mock_simulator_flows() -> str:
    """Mock YAML response for simulator flows."""
    return """
flows:
  - name: login
    steps:
      - type: navigate
        url: https://example.com/login
      - type: fill
        selector: "#username"
        value: test@example.com
      - type: fill
        selector: "#password"
        value: password123
      - type: click
        selector: "#login-button"
"""


@pytest.fixture
def mock_running_sessions() -> Dict[str, Any]:
    """Mock response for running sessions count."""
    return {
        "organization_id": "org-123",
        "running_sessions": 5,
        "max_sessions": 10
    }


# ============================================================================
# Async SDK Fixtures
# ============================================================================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.closed = False

    # Mock the close method
    async def mock_close():
        session.closed = True
    session.close = AsyncMock(side_effect=mock_close)

    # Create mock response context manager
    async def create_mock_response(status=200, json_data=None, text_data=None):
        response = AsyncMock()
        response.status = status
        response.reason = "OK" if status < 400 else "Error"

        if json_data is not None:
            response.json = AsyncMock(return_value=json_data)
        if text_data is not None:
            response.text = AsyncMock(return_value=text_data)

        # Make it work as an async context manager
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)

        return response

    session._create_mock_response = create_mock_response
    return session


@pytest.fixture
def async_plato_client(mock_aiohttp_session):
    """Create a Plato client with mocked session."""
    from plato.sdk import Plato

    client = Plato(api_key="test-api-key", base_url="https://api.test.com")
    # Override the _http_session to avoid creating a real aiohttp session
    client._http_session = mock_aiohttp_session
    return client


# ============================================================================
# Sync SDK Fixtures
# ============================================================================

@pytest.fixture
def mock_requests_session():
    """Mock requests Session."""
    session = Mock(spec=requests.Session)
    session.headers = {}
    session.cookies = Mock()

    def create_mock_response(status_code=200, json_data=None, text_data=None):
        response = Mock()
        response.status_code = status_code
        response.reason = "OK" if status_code < 400 else "Error"

        if json_data is not None:
            response.json = Mock(return_value=json_data)
        if text_data is not None:
            response.text = text_data

        return response

    session._create_mock_response = create_mock_response
    return session


@pytest.fixture
def sync_plato_client(mock_requests_session):
    """Create a SyncPlato client with mocked session."""
    from plato.sync_sdk import SyncPlato

    client = SyncPlato(api_key="test-api-key", base_url="https://api.test.com")
    client._http_session = mock_requests_session
    return client


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def mock_async_env(async_plato_client):
    """Create a mock PlatoEnvironment."""
    from plato.models.env import PlatoEnvironment

    env = PlatoEnvironment(
        client=async_plato_client,
        env_id="test-env",
        id="test-job-123",
        alias="test-alias",
        fast=False
    )
    return env


@pytest.fixture
def mock_sync_env(sync_plato_client):
    """Create a mock SyncPlatoEnvironment."""
    from plato.sync_env import SyncPlatoEnvironment

    env = SyncPlatoEnvironment(
        client=sync_plato_client,
        env_id="test-env",
        id="test-job-123",
        alias="test-alias",
        fast=False
    )
    return env


# ============================================================================
# Playwright Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_async_playwright_page():
    """Mock async Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.screenshot = AsyncMock()
    return page


@pytest.fixture
def mock_sync_playwright_page():
    """Mock sync Playwright page."""
    page = Mock()
    page.goto = Mock()
    page.fill = Mock()
    page.click = Mock()
    page.wait_for_selector = Mock()
    page.screenshot = Mock()
    return page


# ============================================================================
# Error Response Fixtures
# ============================================================================

@pytest.fixture
def mock_error_response() -> Dict[str, Any]:
    """Mock error response."""
    return {
        "error": "Something went wrong",
        "message": "Internal server error",
        "code": 500
    }


@pytest.fixture
def mock_cdp_error_response() -> Dict[str, Any]:
    """Mock CDP error response."""
    return {
        "error": "CDP not available",
        "data": None
    }

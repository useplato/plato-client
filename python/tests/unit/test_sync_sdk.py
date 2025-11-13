"""Unit tests for sync Plato SDK (plato.sync_sdk.SyncPlato class)."""

import pytest
from unittest.mock import Mock, patch
from plato.sync_sdk import SyncPlato
from plato.sync_env import SyncPlatoEnvironment
from plato.models import PlatoTask
from plato.models.task import EvaluationResult
from plato.exceptions import PlatoClientError
import requests


class TestSyncPlatoInit:
    """Test SyncPlato initialization."""

    def test_init_with_api_key_and_base_url(self):
        """Test initialization with explicit API key and base URL."""
        client = SyncPlato(api_key="test-key", base_url="https://test.com")
        assert client.api_key == "test-key"
        assert client.base_url == "https://test.com"
        assert client.feature_flags == {}

    def test_init_with_feature_flags(self):
        """Test initialization with feature flags."""
        flags = {"flag1": True, "flag2": "value"}
        client = SyncPlato(api_key="test-key", feature_flags=flags)
        assert client.feature_flags == flags

    @patch('plato.sync_sdk.config')
    def test_init_with_config_fallback(self, mock_config):
        """Test initialization falls back to config."""
        mock_config.api_key = "config-key"
        mock_config.base_url = "https://config.com"
        client = SyncPlato()
        assert client.api_key == "config-key"
        assert client.base_url == "https://config.com"


class TestSyncPlatoHttpSession:
    """Test HTTP session management."""

    def test_http_session_property_creates_session(self):
        """Test that http_session property creates a new session."""
        client = SyncPlato(api_key="test-key")
        session = client.http_session
        assert isinstance(session, requests.Session)
        assert "X-API-Key" in session.headers

    def test_http_session_property_reuses_session(self):
        """Test that http_session property reuses existing session."""
        client = SyncPlato(api_key="test-key")
        session1 = client.http_session
        session2 = client.http_session
        assert session1 is session2

    def test_http_session_with_feature_flags(self):
        """Test that http_session sets feature flags as cookies (lines 66-67)."""
        flags = {"enable_feature_x": True, "user_segment": "beta"}
        client = SyncPlato(api_key="test-key", feature_flags=flags)

        # Access the session to trigger cookie setting
        session = client.http_session

        # Verify cookies were set
        assert session.cookies.get("enable_feature_x") == "True"
        assert session.cookies.get("user_segment") == "beta"

    def test_close_closes_session(self):
        """Test that close() closes the HTTP session."""
        client = SyncPlato(api_key="test-key")
        session = client.http_session
        client.close()
        # Session should be closed (set to None)
        assert client._http_session is None

    def test_close_when_no_session_exists(self):
        """Test that close() handles case when no session exists (line 72->exit)."""
        client = SyncPlato(api_key="test-key")
        # Don't access http_session, so _http_session stays None
        assert client._http_session is None
        # Should not raise an error
        client.close()
        assert client._http_session is None


class TestSyncPlatoErrorHandling:
    """Test error handling methods."""

    def test_handle_response_error_with_json_decode_error(self):
        """Test _handle_response_error when JSON parsing fails (lines 94-96)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        # Make json() raise JSONDecodeError
        mock_response.json = Mock(side_effect=requests.exceptions.JSONDecodeError("msg", "doc", 0))

        with pytest.raises(PlatoClientError, match="HTTP 500: Internal Server Error"):
            client._handle_response_error(mock_response)

    def test_handle_response_error_with_value_error(self):
        """Test _handle_response_error when JSON parsing raises ValueError."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        # Make json() raise ValueError
        mock_response.json = Mock(side_effect=ValueError("Invalid JSON"))

        with pytest.raises(PlatoClientError, match="HTTP 400: Bad Request"):
            client._handle_response_error(mock_response)


class TestSyncPlatoMakeEnvironment:
    """Test make_environment method."""

    def test_make_environment_success(self, mock_job_response):
        """Test successful environment creation."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_job_response)

        with patch.object(client.http_session, 'post', return_value=mock_response):
            env = client.make_environment(env_id="test-env")

            assert isinstance(env, SyncPlatoEnvironment)
            assert env.env_id == "test-env"
            assert env.id == "test-job-123"
            assert env.alias == "test-alias"
            assert env.fast is False

    def test_make_environment_with_all_params(self, mock_job_response):
        """Test environment creation with all parameters."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_job_response)

        with patch.object(client.http_session, 'post', return_value=mock_response) as mock_post:
            client.make_environment(
                env_id="test-env",
                open_page_on_start=True,
                viewport_width=1280,
                viewport_height=720,
                interface_type="browser",
                record_network_requests=True,
                record_actions=True,
                env_config={"key": "value"},
                keepalive=True,
                alias="my-alias",
                fast=True,
                version="1.0",
                tag="test-tag",
                dataset="test-dataset",
                artifact_id="artifact-123"
            )

            # Verify request was made with correct params
            call_args = mock_post.call_args
            assert call_args[1]['json']['env_id'] == "test-env"
            assert call_args[1]['json']['open_page_on_start'] is True
            assert call_args[1]['json']['interface_width'] == 1280
            assert call_args[1]['json']['interface_height'] == 720
            assert call_args[1]['json']['interface_type'] == "browser"

    def test_make_environment_error(self, mock_error_response):
        """Test environment creation with error response."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json = Mock(return_value=mock_error_response)
        mock_response.reason = "Internal Server Error"

        with patch.object(client.http_session, 'post', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="HTTP 500"):
                client.make_environment(env_id="test-env")


class TestSyncPlatoJobStatus:
    """Test get_job_status method."""

    def test_get_job_status_success(self, mock_job_status):
        """Test successful job status retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_job_status)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            status = client.get_job_status("test-job-123")

            assert status["status"] == "running"
            assert status["job_id"] == "test-job-123"
            assert status["ready"] is True

    def test_get_job_status_error(self):
        """Test job status retrieval with error."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json = Mock(return_value={"error": "Job not found"})
        mock_response.reason = "Not Found"

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="HTTP 404"):
                client.get_job_status("nonexistent-job")


class TestSyncPlatoCDPUrl:
    """Test get_cdp_url method."""

    def test_get_cdp_url_success(self, mock_cdp_response):
        """Test successful CDP URL retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_cdp_response)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            cdp_url = client.get_cdp_url("test-job-123")

            assert cdp_url == "ws://localhost:9222/devtools/browser/test-123"

    def test_get_cdp_url_error_in_response(self, mock_cdp_error_response):
        """Test CDP URL retrieval with error in response data."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_cdp_error_response)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="CDP not available"):
                client.get_cdp_url("test-job-123")


class TestSyncPlatoProxyUrl:
    """Test get_proxy_url method."""

    def test_get_proxy_url_success(self, mock_proxy_response):
        """Test successful proxy URL retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_proxy_response)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            proxy_url = client.get_proxy_url("test-job-123")

            assert proxy_url == "http://proxy.example.com:8080"

    def test_get_proxy_url_error_in_response(self):
        """Test proxy URL retrieval with error in response data."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"error": "Proxy not available", "data": None})

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Proxy not available"):
                client.get_proxy_url("test-job-123")


class TestSyncPlatoEnvironmentOperations:
    """Test environment operation methods."""

    def test_close_environment_success(self):
        """Test successful environment closure."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"success": True})

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.close_environment("test-job-123")

            assert result["success"] is True

    def test_backup_environment_success(self):
        """Test successful environment backup."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"backup_id": "backup-123"})

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.backup_environment("test-job-123")

            assert result["backup_id"] == "backup-123"

    def test_reset_environment_success(self):
        """Test successful environment reset."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"session_id": "session-123"})

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.reset_environment("test-job-123")

            assert result["session_id"] == "session-123"

    def test_reset_environment_with_task(self):
        """Test environment reset with task."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"session_id": "session-123"})

        with patch.object(client.http_session, 'post', return_value=mock_response) as mock_post:
            client.reset_environment(
                "test-job-123",
                task=mock_task,
                agent_version="1.0",
                model="gpt-4",
                load_authenticated=True
            )

            call_args = mock_post.call_args
            assert call_args[1]['json']['test_case_public_id'] == "task-123"
            assert call_args[1]['json']['agent_version'] == "1.0"
            assert call_args[1]['json']['model'] == "gpt-4"
            assert call_args[1]['json']['load_browser_state'] is True


class TestSyncPlatoEnvironmentState:
    """Test environment state methods."""

    def test_get_environment_state_success(self, mock_environment_state):
        """Test successful environment state retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_environment_state)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            state = client.get_environment_state("test-job-123")

            assert state["url"] == "https://example.com"
            assert state["title"] == "Test Page"

    def test_get_environment_state_with_merge_mutations(self, mock_environment_state):
        """Test environment state retrieval with merge_mutations flag."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_environment_state)

        with patch.object(client.http_session, 'get', return_value=mock_response) as mock_get:
            client.get_environment_state("test-job-123", merge_mutations=True)

            call_args = mock_get.call_args
            assert call_args[1]['params']['merge_mutations'] == "true"

    def test_get_worker_ready_success(self, mock_worker_ready):
        """Test successful worker ready check."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_worker_ready)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            ready = client.get_worker_ready("test-job-123")

            assert ready["ready"] is True
            assert ready["worker_ip"] == "192.168.1.1"
            assert ready["worker_port"] == 8080

    def test_get_live_view_url_success(self, mock_worker_ready):
        """Test successful live view URL retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_worker_ready)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            url = client.get_live_view_url("test-job-123")

            assert "live" in url
            assert "test-job-123" in url

    def test_get_live_view_url_worker_not_ready(self):
        """Test live view URL retrieval when worker is not ready."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"ready": False})

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Worker is not ready"):
                client.get_live_view_url("test-job-123")

    def test_get_live_view_url_request_exception(self):
        """Test get_live_view_url when requests.RequestException is raised (line 359)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        with patch.object(client.http_session, 'get', side_effect=requests.RequestException("Connection error")):
            with pytest.raises(PlatoClientError, match="Connection error"):
                client.get_live_view_url("test-job-123")

    def test_send_heartbeat_success(self):
        """Test successful heartbeat."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"success": True})

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.send_heartbeat("test-job-123")

            assert result["success"] is True


class TestSyncPlatoSessionManagement:
    """Test session management methods."""

    def test_get_active_session_success(self, mock_active_session):
        """Test successful active session retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_active_session)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            session = client.get_active_session("test-job-123")

            assert session["session_id"] == "session-123"
            assert session["status"] == "active"

    def test_get_active_session_error(self):
        """Test active session retrieval with error in response."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"error": "No active session"})

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="No active session"):
                client.get_active_session("test-job-123")

    def test_process_snapshot_success(self):
        """Test successful snapshot processing."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"snapshot_id": "snap-123"})

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.process_snapshot("session-123")

            assert result["snapshot_id"] == "snap-123"


class TestSyncPlatoEvaluation:
    """Test evaluation methods."""

    def test_evaluate_success(self, mock_evaluation_response):
        """Test successful evaluation."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_evaluation_response)

        with patch.object(client.http_session, 'post', return_value=mock_response):
            result = client.evaluate("session-123")

            assert result["success"] is True
            assert result["reason"] == "Task completed successfully"

    def test_evaluate_with_value(self, mock_evaluation_response):
        """Test evaluation with value parameter."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_evaluation_response)

        with patch.object(client.http_session, 'post', return_value=mock_response) as mock_post:
            client.evaluate("session-123", value={"key": "value"})

            call_args = mock_post.call_args
            assert call_args[1]['json']['value'] == {"key": "value"}

    def test_post_evaluation_result_success(self):
        """Test successful evaluation result posting."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        eval_result = EvaluationResult(
            success=True,
            reason="Task completed",
            score=1.0
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"success": True})

        with patch.object(client.http_session, 'post', return_value=mock_response) as mock_post:
            result = client.post_evaluation_result("session-123", eval_result)

            assert result["success"] is True
            call_args = mock_post.call_args
            assert call_args[1]['json']['success'] is True
            assert call_args[1]['json']['reason'] == "Task completed"


class TestSyncPlatoLogging:
    """Test logging methods."""

    def test_log_success(self):
        """Test successful logging."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"logged": True})

        with patch.object(client.http_session, 'post', return_value=mock_response) as mock_post:
            result = client.log("session-123", {"message": "test"}, type="info")

            assert result["logged"] is True
            call_args = mock_post.call_args
            assert call_args[1]['json']['message'] == {"message": "test"}
            assert call_args[1]['json']['type'] == "info"
            assert call_args[1]['json']['source'] == "agent"


class TestSyncPlatoSimulatorsAndTasks:
    """Test simulators and tasks methods."""

    def test_list_simulators_success(self, mock_simulators_list):
        """Test successful simulators listing."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_simulators_list)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            simulators = client.list_simulators()

            # Should only return enabled simulators
            assert len(simulators) == 2
            assert all(s["enabled"] for s in simulators)

    def test_load_tasks_success(self, mock_tasks_response):
        """Test successful tasks loading."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_tasks_response)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            tasks = client.load_tasks("test-simulator")

            assert len(tasks) == 1
            assert isinstance(tasks[0], PlatoTask)
            assert tasks[0].public_id == "task-1"
            assert tasks[0].name == "Test Task 1"


class TestSyncPlatoOrganization:
    """Test organization methods."""

    def test_get_running_sessions_count_success(self, mock_running_sessions):
        """Test successful running sessions count retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=mock_running_sessions)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            result = client.get_running_sessions_count()

            assert result["organization_id"] == "org-123"
            assert result["running_sessions"] == 5


class TestSyncPlatoFlows:
    """Test flow/authentication methods."""

    def test_get_simulator_flows_success(self, mock_simulator_flows):
        """Test successful simulator flows retrieval."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(client.http_session, 'get', return_value=mock_response):
            flows = client.get_simulator_flows("artifact-123")

            assert len(flows) == 1
            assert flows[0]["name"] == "login"
            assert len(flows[0]["steps"]) == 4

    def test_get_simulator_flows_json_response(self):
        """Test simulator flows retrieval with JSON wrapped response."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        import json
        mock_json = {
            "data": {
                "flows": "flows:\n  - name: login\n    steps: []"
            }
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(mock_json)

        with patch.object(client.http_session, 'get', return_value=mock_response):
            flows = client.get_simulator_flows("artifact-123")

            assert len(flows) == 1
            assert flows[0]["name"] == "login"

    def test_get_simulator_flows_json_missing_flows_field(self):
        """Test get_simulator_flows when JSON is missing 'flows' field (line 629)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        import json
        # To test line 629, we need:
        # 1. Valid JSON that parses successfully
        # 2. flows_yaml ends up falsy (None, empty string, etc)
        # 3. The fallback to raw YAML parsing should also produce a result

        # Use JSON with flows as None
        mock_json_text = json.dumps({"data": {"flows": None}})

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_json_text

        with patch.object(client.http_session, 'get', return_value=mock_response):
            # JSON parses OK, flows is None (falsy), line 629 raises ValueError
            # Caught on line 630, falls back to raw YAML which will parse the JSON text as YAML
            # Line 634: scripts.get("flows", []) will return []
            flows = client.get_simulator_flows("artifact-123")
            # Should return empty list since YAML parsing of JSON returns dict without "flows" key
            assert flows == []

    def test_get_simulator_flows_generic_exception(self):
        """Test get_simulator_flows exception handling (lines 636-637)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "invalid: yaml: content: [unclosed"

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Failed to load flows from API"):
                client.get_simulator_flows("artifact-123")

    def test_login_artifact_success(self, mock_simulator_flows, mock_sync_playwright_page):
        """Test successful artifact login."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=True)
                mock_executor_class.return_value = mock_executor

                client.login_artifact("artifact-123", mock_sync_playwright_page)

                mock_executor.execute_flow.assert_called_once()

    def test_login_artifact_failure_no_throw(self, mock_simulator_flows, mock_sync_playwright_page):
        """Test artifact login failure without throwing."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=False)
                mock_executor_class.return_value = mock_executor

                # Should not raise, just log warning
                client.login_artifact("artifact-123", mock_sync_playwright_page, throw_on_login_error=False)

    def test_login_artifact_failure_with_throw(self, mock_simulator_flows, mock_sync_playwright_page):
        """Test artifact login failure with throwing."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=False)
                mock_executor_class.return_value = mock_executor

                with pytest.raises(PlatoClientError, match="Failed to login"):
                    client.login_artifact("artifact-123", mock_sync_playwright_page, throw_on_login_error=True)

    def test_login_artifact_no_login_flow_found(self, mock_sync_playwright_page):
        """Test login_artifact when no login flow is found (line 693)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        # Mock response with a flow that's not named "login"
        mock_flows_yaml = """
flows:
  - name: some_other_flow
    steps:
      - type: navigate
        url: https://example.com
"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_flows_yaml

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="No login flow 'login' found"):
                client.login_artifact("artifact-123", mock_sync_playwright_page, throw_on_login_error=True)

    def test_login_artifact_exception_with_throw(self, mock_sync_playwright_page):
        """Test login_artifact exception handling with throw_on_login_error=True (line 707)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        with patch.object(client.http_session, 'get', side_effect=Exception("Network failure")):
            # The exception is caught first by get_simulator_flows which wraps it, then login_artifact wraps it again
            with pytest.raises(PlatoClientError, match="Login failed:.*Network failure"):
                client.login_artifact("artifact-123", mock_sync_playwright_page, throw_on_login_error=True)

    def test_login_artifact_exception_no_throw(self, mock_sync_playwright_page):
        """Test login_artifact exception handling with throw_on_login_error=False."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        with patch.object(client.http_session, 'get', side_effect=Exception("Network failure")):
            # Should not raise, just log error
            client.login_artifact("artifact-123", mock_sync_playwright_page, throw_on_login_error=False)

    def test_login_artifact_with_custom_dataset(self, mock_sync_playwright_page):
        """Test login_artifact with custom dataset parameter (line 687)."""
        client = SyncPlato(api_key="test-key", base_url="https://api.test.com")

        # Mock flows with a custom dataset flow
        mock_flows_yaml = """
flows:
  - name: custom_dataset
    steps:
      - type: navigate
        url: https://example.com/login
      - type: click
        selector: "#login-button"
"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_flows_yaml

        with patch.object(client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=True)
                mock_executor_class.return_value = mock_executor

                # Pass custom dataset, which triggers line 687
                client.login_artifact("artifact-123", mock_sync_playwright_page, dataset="custom_dataset")

                # Verify the flow executor was created
                mock_executor.execute_flow.assert_called_once()

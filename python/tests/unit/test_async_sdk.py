"""Unit tests for async Plato SDK (plato.sdk.Plato class)."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from plato.sdk import Plato
from plato.models import PlatoEnvironment, PlatoTask
from plato.models.task import EvaluationResult
from plato.exceptions import PlatoClientError
import aiohttp


class TestPlatoInit:
    """Test Plato initialization."""

    def test_init_with_api_key_and_base_url(self):
        """Test initialization with explicit API key and base URL."""
        client = Plato(api_key="test-key", base_url="https://test.com")
        assert client.api_key == "test-key"
        assert client.base_url == "https://test.com"
        assert client.feature_flags == {}

    def test_init_with_feature_flags(self):
        """Test initialization with feature flags."""
        flags = {"flag1": True, "flag2": "value"}
        client = Plato(api_key="test-key", feature_flags=flags)
        assert client.feature_flags == flags

    @patch('plato.sdk.config')
    def test_init_with_config_fallback(self, mock_config):
        """Test initialization falls back to config."""
        mock_config.api_key = "config-key"
        mock_config.base_url = "https://config.com"
        client = Plato()
        assert client.api_key == "config-key"
        assert client.base_url == "https://config.com"


class TestPlatoHttpSession:
    """Test HTTP session management."""

    @pytest.mark.asyncio
    async def test_http_session_property_creates_session(self, async_plato_client):
        """Test that http_session property creates a new session."""
        # Session is already mocked in the fixture
        session = async_plato_client.http_session
        assert session is not None
        assert not session.closed

    @pytest.mark.asyncio
    async def test_http_session_property_reuses_session(self, async_plato_client):
        """Test that http_session property reuses existing session."""
        session1 = async_plato_client.http_session
        session2 = async_plato_client.http_session
        assert session1 is session2

    @pytest.mark.asyncio
    async def test_close_closes_session(self, async_plato_client):
        """Test that close() closes the HTTP session."""
        session = async_plato_client.http_session
        await async_plato_client.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_http_session_creates_real_session_with_feature_flags(self):
        """Test that http_session creates real aiohttp session with feature flags (lines 65-79)."""
        from plato.sdk import Plato

        # Create client with feature flags but without mocked session
        client = Plato(
            api_key="test-key",
            base_url="https://test.com/api",
            feature_flags={"flag1": "value1", "flag2": True}
        )

        try:
            # Access the session property to trigger creation
            session = client.http_session

            # Verify session was created
            assert session is not None
            assert isinstance(session, aiohttp.ClientSession)
            assert not session.closed

            # Verify timeout settings
            assert session.timeout.total == 600
            assert session.timeout.connect == 60
            assert session.timeout.sock_read == 600
            assert session.timeout.sock_connect == 60

            # Verify cookie jar was created
            assert session.cookie_jar is not None

            # Verify feature flags were added as cookies
            cookies = session.cookie_jar.filter_cookies("https://test.com")
            assert "flag1" in cookies
            assert "flag2" in cookies
        finally:
            # Clean up
            await client.close()

    @pytest.mark.asyncio
    async def test_close_when_session_is_none(self):
        """Test close() when session is None (lines 87-89)."""
        from plato.sdk import Plato

        client = Plato(api_key="test-key", base_url="https://test.com")
        # Ensure session is None
        assert client._http_session is None

        # Should not raise an error
        await client.close()

        # Session should still be None
        assert client._http_session is None

    @pytest.mark.asyncio
    async def test_close_when_session_is_already_closed(self):
        """Test close() when session is already closed (lines 87-89)."""
        from plato.sdk import Plato

        client = Plato(api_key="test-key", base_url="https://test.com")

        try:
            # Create and close session
            session = client.http_session
            await session.close()

            # Now call client.close() when session is already closed
            await client.close()

            # Should still be closed
            assert session.closed
        finally:
            # Clean up if needed
            if not client._http_session.closed:
                await client.close()


class TestPlatoErrorHandling:
    """Test error handling methods."""

    @pytest.mark.asyncio
    async def test_handle_response_error_with_json_parsing_failure(self, async_plato_client):
        """Test error handling fallback when JSON parsing fails (lines 109-111)."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"
        # Simulate JSON parsing error
        mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(
            request_info=Mock(),
            history=()
        ))

        with pytest.raises(PlatoClientError, match="HTTP 500: Internal Server Error"):
            await async_plato_client._handle_response_error(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_error_with_value_error(self, async_plato_client):
        """Test error handling fallback when ValueError occurs (lines 109-111)."""
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.reason = "Service Unavailable"
        # Simulate ValueError
        mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        with pytest.raises(PlatoClientError, match="HTTP 503: Service Unavailable"):
            await async_plato_client._handle_response_error(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_error_with_no_reason(self, async_plato_client):
        """Test error handling fallback when reason is None (lines 109-111)."""
        mock_response = AsyncMock()
        mock_response.status = 502
        mock_response.reason = None
        # Simulate JSON parsing error
        mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(
            request_info=Mock(),
            history=()
        ))

        with pytest.raises(PlatoClientError, match="HTTP 502: HTTP 502"):
            await async_plato_client._handle_response_error(mock_response)


class TestPlatoMakeEnvironment:
    """Test make_environment method."""

    @pytest.mark.asyncio
    async def test_make_environment_success(self, async_plato_client, mock_job_response):
        """Test successful environment creation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_job_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            # Mock _start_heartbeat to prevent unawaited coroutine warning
            with patch.object(PlatoEnvironment, '_start_heartbeat', new_callable=AsyncMock):
                env = await async_plato_client.make_environment(env_id="test-env")

                assert isinstance(env, PlatoEnvironment)
                assert env.env_id == "test-env"
                assert env.id == "test-job-123"
                assert env.alias == "test-alias"
                assert env.fast is False

    @pytest.mark.asyncio
    async def test_make_environment_with_all_params(self, async_plato_client, mock_job_response):
        """Test environment creation with all parameters."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_job_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            # Mock _start_heartbeat to prevent unawaited coroutine warning
            with patch.object(PlatoEnvironment, '_start_heartbeat', new_callable=AsyncMock):
                await async_plato_client.make_environment(
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

    @pytest.mark.asyncio
    async def test_make_environment_error(self, async_plato_client, mock_error_response):
        """Test environment creation with error response."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value=mock_error_response)
        mock_response.reason = "Internal Server Error"
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            # Mock _start_heartbeat to prevent unawaited coroutine warning (though it won't be called on error)
            with patch.object(PlatoEnvironment, '_start_heartbeat', new_callable=AsyncMock):
                with pytest.raises(PlatoClientError, match="HTTP 500"):
                    await async_plato_client.make_environment(env_id="test-env")


class TestPlatoJobStatus:
    """Test get_job_status method."""

    @pytest.mark.asyncio
    async def test_get_job_status_success(self, async_plato_client, mock_job_status):
        """Test successful job status retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_job_status)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            status = await async_plato_client.get_job_status("test-job-123")

            assert status["status"] == "running"
            assert status["job_id"] == "test-job-123"
            assert status["ready"] is True

    @pytest.mark.asyncio
    async def test_get_job_status_error(self, async_plato_client):
        """Test job status retrieval with error."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": "Job not found"})
        mock_response.reason = "Not Found"
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="HTTP 404"):
                await async_plato_client.get_job_status("nonexistent-job")


class TestPlatoCDPUrl:
    """Test get_cdp_url method."""

    @pytest.mark.asyncio
    async def test_get_cdp_url_success(self, async_plato_client, mock_cdp_response):
        """Test successful CDP URL retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cdp_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            cdp_url = await async_plato_client.get_cdp_url("test-job-123")

            assert cdp_url == "ws://localhost:9222/devtools/browser/test-123"

    @pytest.mark.asyncio
    async def test_get_cdp_url_error_in_response(self, async_plato_client, mock_cdp_error_response):
        """Test CDP URL retrieval with error in response data."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cdp_error_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="CDP not available"):
                await async_plato_client.get_cdp_url("test-job-123")


class TestPlatoProxyUrl:
    """Test get_proxy_url method."""

    @pytest.mark.asyncio
    async def test_get_proxy_url_success(self, async_plato_client, mock_proxy_response):
        """Test successful proxy URL retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_proxy_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            proxy_url = await async_plato_client.get_proxy_url("test-job-123")

            assert proxy_url == "http://proxy.example.com:8080"

    @pytest.mark.asyncio
    async def test_get_proxy_url_error_in_response(self, async_plato_client):
        """Test proxy URL retrieval with error in response data."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"error": "Proxy not available", "data": None})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Proxy not available"):
                await async_plato_client.get_proxy_url("test-job-123")


class TestPlatoEnvironmentOperations:
    """Test environment operation methods."""

    @pytest.mark.asyncio
    async def test_close_environment_success(self, async_plato_client):
        """Test successful environment closure."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.close_environment("test-job-123")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_backup_environment_success(self, async_plato_client):
        """Test successful environment backup."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"backup_id": "backup-123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.backup_environment("test-job-123")

            assert result["backup_id"] == "backup-123"

    @pytest.mark.asyncio
    async def test_reset_environment_success(self, async_plato_client):
        """Test successful environment reset."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"session_id": "session-123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.reset_environment("test-job-123")

            assert result["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_reset_environment_with_task(self, async_plato_client):
        """Test environment reset with task."""
        mock_task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"session_id": "session-123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            await async_plato_client.reset_environment(
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


class TestPlatoEnvironmentState:
    """Test environment state methods."""

    @pytest.mark.asyncio
    async def test_get_environment_state_success(self, async_plato_client, mock_environment_state):
        """Test successful environment state retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_environment_state)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            state = await async_plato_client.get_environment_state("test-job-123")

            assert state["url"] == "https://example.com"
            assert state["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_get_environment_state_with_merge_mutations(self, async_plato_client, mock_environment_state):
        """Test environment state retrieval with merge_mutations flag."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_environment_state)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response) as mock_get:
            await async_plato_client.get_environment_state("test-job-123", merge_mutations=True)

            call_args = mock_get.call_args
            assert call_args[1]['params']['merge_mutations'] == "true"

    @pytest.mark.asyncio
    async def test_get_worker_ready_success(self, async_plato_client, mock_worker_ready):
        """Test successful worker ready check."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_worker_ready)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            ready = await async_plato_client.get_worker_ready("test-job-123")

            assert ready["ready"] is True
            assert ready["worker_ip"] == "192.168.1.1"
            assert ready["worker_port"] == 8080

    @pytest.mark.asyncio
    async def test_get_live_view_url_success(self, async_plato_client, mock_worker_ready):
        """Test successful live view URL retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_worker_ready)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            url = await async_plato_client.get_live_view_url("test-job-123")

            assert "live" in url
            assert "test-job-123" in url

    @pytest.mark.asyncio
    async def test_get_live_view_url_worker_not_ready(self, async_plato_client):
        """Test live view URL retrieval when worker is not ready."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ready": False})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Worker is not ready"):
                await async_plato_client.get_live_view_url("test-job-123")

    @pytest.mark.asyncio
    async def test_get_live_view_url_aiohttp_client_error(self, async_plato_client):
        """Test live view URL retrieval with aiohttp.ClientError exception (line 394)."""
        # Simulate aiohttp.ClientError being raised
        with patch.object(
            async_plato_client,
            'get_worker_ready',
            side_effect=aiohttp.ClientError("Connection error")
        ):
            with pytest.raises(PlatoClientError, match="Connection error"):
                await async_plato_client.get_live_view_url("test-job-123")

    @pytest.mark.asyncio
    async def test_send_heartbeat_success(self, async_plato_client):
        """Test successful heartbeat."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.send_heartbeat("test-job-123")

            assert result["success"] is True


class TestPlatoSessionManagement:
    """Test session management methods."""

    @pytest.mark.asyncio
    async def test_get_active_session_success(self, async_plato_client, mock_active_session):
        """Test successful active session retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_active_session)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            session = await async_plato_client.get_active_session("test-job-123")

            assert session["session_id"] == "session-123"
            assert session["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_active_session_error(self, async_plato_client):
        """Test active session retrieval with error in response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"error": "No active session"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="No active session"):
                await async_plato_client.get_active_session("test-job-123")

    @pytest.mark.asyncio
    async def test_process_snapshot_success(self, async_plato_client):
        """Test successful snapshot processing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"snapshot_id": "snap-123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.process_snapshot("session-123")

            assert result["snapshot_id"] == "snap-123"


class TestPlatoEvaluation:
    """Test evaluation methods."""

    @pytest.mark.asyncio
    async def test_evaluate_success(self, async_plato_client, mock_evaluation_response):
        """Test successful evaluation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_evaluation_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            result = await async_plato_client.evaluate("session-123")

            assert result["success"] is True
            assert result["reason"] == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_evaluate_with_value(self, async_plato_client, mock_evaluation_response):
        """Test evaluation with value parameter."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_evaluation_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            await async_plato_client.evaluate("session-123", value={"key": "value"})

            call_args = mock_post.call_args
            assert call_args[1]['json']['value'] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_post_evaluation_result_success(self, async_plato_client):
        """Test successful evaluation result posting."""
        eval_result = EvaluationResult(
            success=True,
            reason="Task completed",
            score=1.0
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            result = await async_plato_client.post_evaluation_result("session-123", eval_result)

            assert result["success"] is True
            call_args = mock_post.call_args
            assert call_args[1]['json']['success'] is True
            assert call_args[1]['json']['reason'] == "Task completed"


class TestPlatoLogging:
    """Test logging methods."""

    @pytest.mark.asyncio
    async def test_log_success(self, async_plato_client):
        """Test successful logging."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"logged": True})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            result = await async_plato_client.log("session-123", {"message": "test"}, type="info")

            assert result["logged"] is True
            call_args = mock_post.call_args
            assert call_args[1]['json']['message'] == {"message": "test"}
            assert call_args[1]['json']['type'] == "info"
            assert call_args[1]['json']['source'] == "agent"


class TestPlatoSimulatorsAndTasks:
    """Test simulators and tasks methods."""

    @pytest.mark.asyncio
    async def test_list_simulators_success(self, async_plato_client, mock_simulators_list):
        """Test successful simulators listing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_simulators_list)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            simulators = await async_plato_client.list_simulators()

            # Should only return enabled simulators
            assert len(simulators) == 2
            assert all(s["enabled"] for s in simulators)

    @pytest.mark.asyncio
    async def test_load_tasks_success(self, async_plato_client, mock_tasks_response):
        """Test successful tasks loading."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_tasks_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            tasks = await async_plato_client.load_tasks("test-simulator")

            assert len(tasks) == 1
            assert isinstance(tasks[0], PlatoTask)
            assert tasks[0].public_id == "task-1"
            assert tasks[0].name == "Test Task 1"

    @pytest.mark.asyncio
    async def test_list_simulator_tasks_by_id_success(self, async_plato_client, mock_tasks_response):
        """Test successful tasks listing by simulator ID."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_tasks_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            tasks = await async_plato_client.list_simulator_tasks_by_id("sim-123")

            assert len(tasks) == 1
            assert tasks[0]["publicId"] == "task-1"


class TestPlatoOrganization:
    """Test organization methods."""

    @pytest.mark.asyncio
    async def test_get_running_sessions_count_success(self, async_plato_client, mock_running_sessions):
        """Test successful running sessions count retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_running_sessions)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            result = await async_plato_client.get_running_sessions_count()

            assert result["organization_id"] == "org-123"
            assert result["running_sessions"] == 5


class TestPlatoGitea:
    """Test Gitea/repository methods."""

    @pytest.mark.asyncio
    async def test_get_gitea_info_success(self, async_plato_client, mock_gitea_info):
        """Test successful Gitea info retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_gitea_info)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            info = await async_plato_client.get_gitea_info()

            assert info["username"] == "test-user"
            assert info["org_name"] == "test-org"

    @pytest.mark.asyncio
    async def test_list_gitea_simulators_success(self, async_plato_client):
        """Test successful Gitea simulators listing."""
        mock_data = [{"id": 1, "name": "sim1"}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            simulators = await async_plato_client.list_gitea_simulators()

            assert len(simulators) == 1
            assert simulators[0]["name"] == "sim1"

    @pytest.mark.asyncio
    async def test_get_simulator_repository_success(self, async_plato_client):
        """Test successful simulator repository retrieval."""
        mock_repo = {"repo_url": "https://gitea.com/org/repo"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_repo)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            repo = await async_plato_client.get_simulator_repository(123)

            assert repo["repo_url"] == "https://gitea.com/org/repo"

    @pytest.mark.asyncio
    async def test_get_gitea_credentials_success(self, async_plato_client, mock_gitea_credentials):
        """Test successful Gitea credentials retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_gitea_credentials)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            creds = await async_plato_client.get_gitea_credentials()

            assert creds["username"] == "admin"
            assert creds["password"] == "secret123"

    @pytest.mark.asyncio
    async def test_create_simulator_success(self, async_plato_client):
        """Test successful simulator creation."""
        mock_simulator = {"id": 123, "name": "new-simulator"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_simulator)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response) as mock_post:
            result = await async_plato_client.create_simulator("new-simulator", "Description", "docker_app")

            assert result["id"] == 123
            call_args = mock_post.call_args
            assert call_args[1]['json']['name'] == "new-simulator"
            assert call_args[1]['json']['description'] == "Description"
            assert call_args[1]['json']['simType'] == "docker_app"

    @pytest.mark.asyncio
    async def test_create_simulator_repository_success(self, async_plato_client):
        """Test successful simulator repository creation."""
        mock_repo = {"repo_url": "https://gitea.com/org/new-repo"}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_repo)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'post', return_value=mock_response):
            repo = await async_plato_client.create_simulator_repository(123)

            assert repo["repo_url"] == "https://gitea.com/org/new-repo"


class TestPlatoFlows:
    """Test flow/authentication methods."""

    @pytest.mark.asyncio
    async def test_get_simulator_flows_success(self, async_plato_client, mock_simulator_flows):
        """Test successful simulator flows retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            flows = await async_plato_client.get_simulator_flows("artifact-123")

            assert len(flows) == 1
            assert flows[0]["name"] == "login"
            assert len(flows[0]["steps"]) == 4

    @pytest.mark.asyncio
    async def test_get_simulator_flows_json_response(self, async_plato_client):
        """Test simulator flows retrieval with JSON wrapped response."""
        mock_json = {
            "data": {
                "flows": "flows:\n  - name: login\n    steps: []"
            }
        }

        import json
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_json))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            flows = await async_plato_client.get_simulator_flows("artifact-123")

            assert len(flows) == 1
            assert flows[0]["name"] == "login"

    @pytest.mark.asyncio
    async def test_get_simulator_flows_http_error(self, async_plato_client):
        """Test simulator flows with HTTP error (lines 817-825)."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"
        mock_response.json = AsyncMock(return_value={"error": "Server error"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Failed to load flows from API"):
                await async_plato_client.get_simulator_flows("artifact-123")

    @pytest.mark.asyncio
    async def test_get_simulator_flows_yaml_parsing_error(self, async_plato_client):
        """Test simulator flows with YAML parsing error (lines 817-825)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="invalid: yaml: content: [")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Failed to load flows from API"):
                await async_plato_client.get_simulator_flows("artifact-123")

    @pytest.mark.asyncio
    async def test_get_simulator_flows_missing_flows_key(self, async_plato_client):
        """Test simulator flows with missing 'flows' key in YAML (lines 817-825)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        # Valid YAML but missing 'flows' key
        mock_response.text = AsyncMock(return_value="other_key:\n  - value: test")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            # Should not raise, but return empty list or handle gracefully
            flows = await async_plato_client.get_simulator_flows("artifact-123")
            assert flows == []

    @pytest.mark.asyncio
    async def test_get_simulator_flows_json_missing_flows(self, async_plato_client):
        """Test simulator flows with JSON response missing 'flows' (lines 817-825)."""
        import json
        # When flows is missing in JSON, it falls back to parsing the JSON string as YAML
        # This will fail because JSON is not valid YAML with the flows key
        mock_json = {
            "data": {
                "other_key": "value"
            }
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_json))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            # This will return empty list because the fallback YAML parsing doesn't have 'flows' key
            flows = await async_plato_client.get_simulator_flows("artifact-123")
            assert flows == []

    @pytest.mark.asyncio
    async def test_login_artifact_success(self, async_plato_client, mock_simulator_flows, mock_async_playwright_page):
        """Test successful artifact login."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=True)
                mock_executor_class.return_value = mock_executor

                await async_plato_client.login_artifact("artifact-123", mock_async_playwright_page)

                mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_artifact_with_custom_dataset(self, async_plato_client, mock_async_playwright_page):
        """Test artifact login with custom dataset (line 876)."""
        # Mock flows with a custom flow name
        mock_flows = """
flows:
  - name: custom_flow
    steps:
      - type: navigate
        url: https://example.com
"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=True)
                mock_executor_class.return_value = mock_executor

                # Use custom dataset name
                await async_plato_client.login_artifact(
                    "artifact-123",
                    mock_async_playwright_page,
                    dataset="custom_flow"
                )

                mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_artifact_failure_no_throw(self, async_plato_client, mock_simulator_flows, mock_async_playwright_page):
        """Test artifact login failure without throwing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=False)
                mock_executor_class.return_value = mock_executor

                # Should not raise, just log warning
                await async_plato_client.login_artifact("artifact-123", mock_async_playwright_page, throw_on_login_error=False)

    @pytest.mark.asyncio
    async def test_login_artifact_failure_with_throw(self, async_plato_client, mock_simulator_flows, mock_async_playwright_page):
        """Test artifact login failure with throwing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=False)
                mock_executor_class.return_value = mock_executor

                with pytest.raises(PlatoClientError, match="Failed to login"):
                    await async_plato_client.login_artifact("artifact-123", mock_async_playwright_page, throw_on_login_error=True)

    @pytest.mark.asyncio
    async def test_login_artifact_no_login_flow_with_throw(self, async_plato_client, mock_async_playwright_page):
        """Test login_artifact when no login flow is found with throw (line 882)."""
        # Mock flows without a 'login' flow
        mock_flows = """
flows:
  - name: other_flow
    steps: []
"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="No login flow 'login' found"):
                await async_plato_client.login_artifact(
                    "artifact-123",
                    mock_async_playwright_page,
                    throw_on_login_error=True
                )

    @pytest.mark.asyncio
    async def test_login_artifact_no_login_flow_without_throw(self, async_plato_client, mock_async_playwright_page):
        """Test login_artifact when no login flow is found without throw (lines 876-897)."""
        # Mock flows without a 'login' flow
        mock_flows = """
flows:
  - name: other_flow
    steps: []
"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            # Should not raise, just log error
            await async_plato_client.login_artifact(
                "artifact-123",
                mock_async_playwright_page,
                throw_on_login_error=False
            )

    @pytest.mark.asyncio
    async def test_login_artifact_exception_in_flow_executor_with_throw(self, async_plato_client, mock_simulator_flows, mock_async_playwright_page):
        """Test login_artifact when flow executor raises exception with throw (lines 893-895)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(side_effect=Exception("Flow execution failed"))
                mock_executor_class.return_value = mock_executor

                with pytest.raises(PlatoClientError, match="Login failed: Flow execution failed"):
                    await async_plato_client.login_artifact(
                        "artifact-123",
                        mock_async_playwright_page,
                        throw_on_login_error=True
                    )

    @pytest.mark.asyncio
    async def test_login_artifact_exception_in_flow_executor_without_throw(self, async_plato_client, mock_simulator_flows, mock_async_playwright_page):
        """Test login_artifact when flow executor raises exception without throw (lines 896-897)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(side_effect=Exception("Flow execution failed"))
                mock_executor_class.return_value = mock_executor

                # Should not raise, just log error
                await async_plato_client.login_artifact(
                    "artifact-123",
                    mock_async_playwright_page,
                    throw_on_login_error=False
                )

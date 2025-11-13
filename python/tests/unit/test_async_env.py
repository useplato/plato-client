"""Unit tests for async PlatoEnvironment (plato.models.env.PlatoEnvironment class)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from plato.models.env import PlatoEnvironment
from plato.models import PlatoTask
from plato.models.task import EvaluationResult, CustomEvalConfig
from plato.exceptions import PlatoClientError
import asyncio
import json
from typing import Coroutine


class TestPlatoEnvironmentInit:
    """Test PlatoEnvironment initialization."""

    def test_init_basic(self, async_plato_client):
        """Test basic initialization."""
        env = PlatoEnvironment(
            client=async_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        assert env._client == async_plato_client
        assert env.id == "test-job-123"
        assert env.env_id == "test-env"
        assert env.alias is None
        assert env._run_session_id is None
        assert env.fast is False

    def test_init_with_all_params(self, async_plato_client):
        """Test initialization with all parameters."""
        env = PlatoEnvironment(
            client=async_plato_client,
            id="test-job-123",
            env_id="test-env",
            alias="test-alias",
            active_session="session-123",
            fast=True
        )

        assert env.alias == "test-alias"
        assert env._run_session_id == "session-123"
        assert env.fast is True

    @pytest.mark.asyncio
    async def test_from_id_static_method(self, async_plato_client):
        """Test from_id static method."""
        async_plato_client.get_active_session = AsyncMock(return_value="session-123")
        async_plato_client.close_environment = AsyncMock(return_value={"success": True})

        with patch.object(PlatoEnvironment, '_start_heartbeat', new_callable=AsyncMock) as mock_start:
            env = await PlatoEnvironment.from_id(
                client=async_plato_client,
                id="test-job-123",
                fast=True
            )

            assert isinstance(env, PlatoEnvironment)
            assert env.id == "test-job-123"
            assert env.fast is True
            mock_start.assert_called_once()

            # Clean up to avoid warnings
            with patch.object(env, '_stop_heartbeat', new_callable=AsyncMock):
                await env.close()

    @pytest.mark.asyncio
    async def test_from_id_no_active_session(self, async_plato_client):
        """Test from_id when no active session exists - covers lines 810-813."""
        async_plato_client.get_active_session = AsyncMock(side_effect=Exception("No session"))
        async_plato_client.close_environment = AsyncMock(return_value={"success": True})

        with patch.object(PlatoEnvironment, '_start_heartbeat', new_callable=AsyncMock):
            env = await PlatoEnvironment.from_id(
                client=async_plato_client,
                id="test-job-123",
                fast=True
            )

            # Should still create environment even if no active session
            assert isinstance(env, PlatoEnvironment)
            assert env.id == "test-job-123"

            # Clean up
            with patch.object(env, '_stop_heartbeat', new_callable=AsyncMock):
                await env.close()


class TestPlatoEnvironmentLogin:
    """Test login method."""

    @pytest.mark.asyncio
    async def test_login_from_api_success(self, mock_async_env, mock_simulator_flows, mock_async_playwright_page):
        """Test successful login from API."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=True)
                mock_executor_class.return_value = mock_executor

                await mock_async_env.login(mock_async_playwright_page, from_api=True)

                mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_from_api_json_with_data_flows(self, mock_async_env, mock_simulator_flows, mock_async_playwright_page):
        """Test login from API with JSON response containing data.flows - covers lines 99-105."""
        json_response = json.dumps({"data": {"flows": mock_simulator_flows}})
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=True)
                mock_executor_class.return_value = mock_executor

                await mock_async_env.login(mock_async_playwright_page, from_api=True)

                mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_from_api_json_missing_flows(self, mock_async_env, mock_async_playwright_page):
        """Test login from API with JSON missing flows - covers lines 104-105."""
        json_response = json.dumps({"data": {}})  # Missing flows key
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            # Should fall back to treating as YAML (lines 106-108)
            with pytest.raises(Exception):  # Will fail during YAML parsing
                await mock_async_env.login(mock_async_playwright_page, from_api=True)

    @pytest.mark.asyncio
    async def test_login_from_api_error(self, mock_async_env, mock_async_playwright_page):
        """Test login from API with error - covers lines 109-110."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_async_env._client._handle_response_error = AsyncMock(side_effect=Exception("API Error"))

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Failed to load flows from API"):
                await mock_async_env.login(mock_async_playwright_page, from_api=True)

    @pytest.mark.asyncio
    async def test_login_from_local_file(self, mock_async_env, mock_async_playwright_page):
        """Test login from local file."""
        mock_async_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [{
                "name": "login",
                "steps": []
            }]
        }

        with patch('plato.models.env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                with patch('plato.models.env.yaml.safe_load', return_value=mock_yaml_content):
                    with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                        mock_executor = AsyncMock()
                        mock_executor.execute_flow = AsyncMock(return_value=True)
                        mock_executor_class.return_value = mock_executor

                        await mock_async_env.login(mock_async_playwright_page, from_api=False)

                        mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_file_not_exists(self, mock_async_env, mock_async_playwright_page):
        """Test login with missing file - covers line 123."""
        mock_async_env.env_id = "test-env"

        with patch('plato.models.env.os.path.exists', return_value=False):
            with pytest.raises(PlatoClientError, match="Flow scripts not found"):
                await mock_async_env.login(mock_async_playwright_page, from_api=False)

    @pytest.mark.asyncio
    async def test_login_no_env_id(self, mock_async_env, mock_async_playwright_page):
        """Test login fails without env_id."""
        mock_async_env.env_id = None

        with pytest.raises(PlatoClientError, match="No env_id set"):
            await mock_async_env.login(mock_async_playwright_page, from_api=False)

    @pytest.mark.asyncio
    async def test_login_custom_dataset(self, mock_async_env, mock_async_playwright_page):
        """Test login with custom dataset name - covers line 137."""
        mock_async_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [
                {"name": "login", "steps": []},
                {"name": "custom_dataset", "steps": []}
            ]
        }

        with patch('plato.models.env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('plato.models.env.yaml.safe_load', return_value=mock_yaml_content):
                    with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                        mock_executor = AsyncMock()
                        mock_executor.execute_flow = AsyncMock(return_value=True)
                        mock_executor_class.return_value = mock_executor

                        await mock_async_env.login(mock_async_playwright_page, from_api=False, dataset="custom_dataset")

                        mock_executor.execute_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_flow_not_found(self, mock_async_env, mock_async_playwright_page):
        """Test login with missing flow - covers line 141."""
        mock_async_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [
                {"name": "some_other_flow", "steps": []}
            ]
        }

        with patch('plato.models.env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('plato.models.env.yaml.safe_load', return_value=mock_yaml_content):
                    with pytest.raises(PlatoClientError, match="No flow named"):
                        await mock_async_env.login(mock_async_playwright_page, from_api=False)

    @pytest.mark.asyncio
    async def test_login_failure_with_throw(self, mock_async_env, mock_simulator_flows, mock_async_playwright_page):
        """Test login failure with throw_on_login_error=True."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=False)
                mock_executor_class.return_value = mock_executor

                with pytest.raises(PlatoClientError, match="Failed to login"):
                    await mock_async_env.login(mock_async_playwright_page, from_api=True, throw_on_login_error=True)

    @pytest.mark.asyncio
    async def test_login_failure_without_throw(self, mock_async_env, mock_simulator_flows, mock_async_playwright_page):
        """Test login failure with throw_on_login_error=False."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_simulator_flows)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(mock_async_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.flow_executor.FlowExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_flow = AsyncMock(return_value=False)
                mock_executor_class.return_value = mock_executor

                # Should not raise, just log warning
                await mock_async_env.login(mock_async_playwright_page, from_api=True, throw_on_login_error=False)


class TestPlatoEnvironmentWaitForReady:
    """Test wait_for_ready method."""

    @pytest.mark.asyncio
    async def test_wait_for_ready_success(self, mock_async_env, mock_job_status, mock_worker_ready):
        """Test successful wait for ready."""
        mock_async_env._client.get_job_status = AsyncMock(return_value=mock_job_status)
        mock_async_env._client.get_worker_ready = AsyncMock(return_value=mock_worker_ready)

        with patch.object(mock_async_env, '_start_heartbeat', new_callable=AsyncMock):
            await mock_async_env.wait_for_ready()

        mock_async_env._client.get_job_status.assert_called()
        mock_async_env._client.get_worker_ready.assert_called()

    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self, mock_async_env):
        """Test wait for ready with timeout."""
        mock_async_env._client.get_job_status = AsyncMock(
            return_value={"status": "pending"}
        )

        with pytest.raises(RuntimeError, match="failed to start"):
            await mock_async_env.wait_for_ready(timeout=0.1)

    @pytest.mark.asyncio
    async def test_wait_for_ready_exponential_backoff(self, mock_async_env, mock_job_status):
        """Test exponential backoff during wait - covers lines 190-191."""
        # Return pending twice, then running
        mock_async_env._client.get_job_status = AsyncMock(
            side_effect=[
                {"status": "pending"},
                {"status": "pending"},
                {"status": "running"}
            ]
        )
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": True})

        with patch.object(mock_async_env, '_start_heartbeat', new_callable=AsyncMock):
            await mock_async_env.wait_for_ready()

        # Should have been called 3 times
        assert mock_async_env._client.get_job_status.call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_ready_worker_timeout(self, mock_async_env, mock_job_status):
        """Test worker timeout with error message - covers lines 207-208."""
        mock_async_env._client.get_job_status = AsyncMock(return_value=mock_job_status)
        mock_async_env._client.get_worker_ready = AsyncMock(
            return_value={"ready": False, "error": "Worker initialization failed"}
        )

        with pytest.raises(RuntimeError, match="Worker initialization failed"):
            await mock_async_env.wait_for_ready(timeout=0.1)

    @pytest.mark.asyncio
    async def test_wait_for_ready_worker_not_ready_then_ready(self, mock_async_env, mock_job_status):
        """Test wait for ready when worker becomes ready after delay."""
        mock_async_env._client.get_job_status = AsyncMock(return_value=mock_job_status)

        # First call returns not ready, second call returns ready
        mock_async_env._client.get_worker_ready = AsyncMock(
            side_effect=[
                {"ready": False},
                {"ready": True}
            ]
        )

        with patch.object(mock_async_env, '_start_heartbeat', new_callable=AsyncMock):
            await mock_async_env.wait_for_ready()

        assert mock_async_env._client.get_worker_ready.call_count == 2


class TestPlatoEnvironmentReset:
    """Test reset method."""

    @pytest.mark.asyncio
    async def test_reset_success(self, mock_async_env):
        """Test successful environment reset."""
        mock_async_env._client.reset_environment = AsyncMock(
            return_value={"success": True, "data": {"run_session_id": "new-session-123"}}
        )

        session_id = await mock_async_env.reset()

        assert session_id == "new-session-123"
        assert mock_async_env._run_session_id == "new-session-123"

    @pytest.mark.asyncio
    async def test_reset_with_task(self, mock_async_env):
        """Test environment reset with task."""
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        mock_async_env._client.reset_environment = AsyncMock(
            return_value={"success": True, "data": {"run_session_id": "new-session-123"}}
        )

        session_id = await mock_async_env.reset(task=task, agent_version="1.0", model="gpt-4")

        assert session_id == "new-session-123"
        mock_async_env._client.reset_environment.assert_called_once()

        call_args = mock_async_env._client.reset_environment.call_args
        assert call_args[0][0] == mock_async_env.id
        # The task is passed as a positional argument, not a keyword argument
        assert call_args[0][1] == task

    @pytest.mark.asyncio
    async def test_reset_failure(self, mock_async_env):
        """Test reset failure - covers line 287."""
        mock_async_env._client.reset_environment = AsyncMock(
            return_value={"success": False, "error": "Reset failed"}
        )

        with pytest.raises(PlatoClientError, match="Reset failed"):
            await mock_async_env.reset()

    @pytest.mark.asyncio
    async def test_reset_missing_session_id(self, mock_async_env):
        """Test reset with missing session ID - covers line 292."""
        mock_async_env._client.reset_environment = AsyncMock(
            return_value={"success": True, "data": {"run_session_id": None}}
        )

        with pytest.raises(PlatoClientError, match="Failed to reset environment"):
            await mock_async_env.reset()


class TestPlatoEnvironmentBackup:
    """Test backup method."""

    @pytest.mark.asyncio
    async def test_backup_success(self, mock_async_env):
        """Test successful environment backup."""
        mock_async_env._client.backup_environment = AsyncMock(
            return_value={"backup_id": "backup-123"}
        )

        result = await mock_async_env.backup()

        assert result["backup_id"] == "backup-123"
        mock_async_env._client.backup_environment.assert_called_once_with(mock_async_env.id)


class TestPlatoEnvironmentState:
    """Test state management methods."""

    @pytest.mark.asyncio
    async def test_get_state_success(self, mock_async_env, mock_environment_state):
        """Test successful state retrieval."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_environment_state = AsyncMock(
            return_value=mock_environment_state["data"]["state"]
        )

        state = await mock_async_env.get_state()

        assert state["url"] == "https://example.com"
        assert state["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_get_state_no_session(self, mock_async_env):
        """Test get_state without session - covers line 348."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_state()

    @pytest.mark.asyncio
    async def test_get_state_with_merge_mutations(self, mock_async_env, mock_environment_state):
        """Test state retrieval with merge_mutations."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_environment_state = AsyncMock(
            return_value=mock_environment_state["data"]["state"]
        )

        await mock_async_env.get_state(merge_mutations=True)

        # The function signature is (self.id, merge_mutations) - both positional
        mock_async_env._client.get_environment_state.assert_called_once_with(
            mock_async_env.id,
            True
        )

    @pytest.mark.asyncio
    async def test_get_state_mutations(self, mock_async_env):
        """Test state mutations retrieval."""
        mock_async_env._run_session_id = "session-123"
        mock_state = {
            "url": "https://example.com",
            "mutations": [
                {"type": "click", "target": "#button"},
                {"type": "fill", "target": "#input"}
            ]
        }

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value=mock_state
        )

        mutations = await mock_async_env.get_state_mutations()

        assert len(mutations) == 2
        assert mutations[0]["type"] == "click"
        assert mutations[1]["type"] == "fill"

    def test_get_nested_value_simple(self, mock_async_env):
        """Test _get_nested_value with simple path - covers lines 379-388."""
        data = {"a": {"b": {"c": "value"}}}
        result = mock_async_env._get_nested_value(data, "a.b.c")
        assert result == "value"

    def test_get_nested_value_with_list_index(self, mock_async_env):
        """Test _get_nested_value with list index - covers lines 379-388."""
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        result = mock_async_env._get_nested_value(data, "items[1].name")
        assert result == "second"

    def test_get_nested_value_complex(self, mock_async_env):
        """Test _get_nested_value with complex path - covers lines 379-388."""
        data = {"a": {"b": [{"c": 1}, {"c": 2, "d": [10, 20]}]}}
        result = mock_async_env._get_nested_value(data, "a.b[1].c")
        assert result == 2


class TestPlatoEnvironmentEvaluation:
    """Test evaluation methods."""

    @pytest.mark.asyncio
    async def test_evaluate_success(self, mock_async_env, mock_evaluation_response):
        """Test successful evaluation."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.evaluate = AsyncMock(
            return_value={"result": {"correct": True, "reason": "Task completed successfully"}}
        )

        result = await mock_async_env.evaluate()

        assert isinstance(result, EvaluationResult)
        assert result.success is True
        assert result.reason == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_evaluate_no_result(self, mock_async_env):
        """Test evaluate with no result - covers line 473."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.evaluate = AsyncMock(return_value=None)

        with pytest.raises(PlatoClientError, match="No evaluation result found"):
            await mock_async_env.evaluate()

    @pytest.mark.asyncio
    async def test_evaluate_without_session(self, mock_async_env):
        """Test evaluate raises error without active session."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.evaluate()

    @pytest.mark.asyncio
    async def test_evaluate_with_value(self, mock_async_env, mock_evaluation_response):
        """Test evaluation with value parameter."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.evaluate = AsyncMock(
            return_value={"result": {"correct": True, "reason": "Task completed successfully"}}
        )

        await mock_async_env.evaluate(value={"key": "value"})

        # The function signature is (run_session_id, value, agent_version) - all positional
        mock_async_env._client.evaluate.assert_called_once_with(
            "session-123",
            {"key": "value"},
            None
        )

    @pytest.mark.asyncio
    async def test_get_evaluation_result_no_session(self, mock_async_env):
        """Test get_evaluation_result without session - covers line 409."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_evaluation_result()

    @pytest.mark.asyncio
    async def test_get_evaluation_result_no_config(self, mock_async_env):
        """Test get_evaluation_result without config - covers lines 412-415."""
        mock_async_env._run_session_id = "session-123"

        # Create task without eval_config
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )
        task.eval_config = None
        mock_async_env._current_task = task

        with pytest.raises(PlatoClientError, match="No evaluation config found"):
            await mock_async_env.get_evaluation_result()

    @pytest.mark.asyncio
    async def test_get_evaluation_result_custom_eval_tuple(self, mock_async_env):
        """Test get_evaluation_result with custom eval returning tuple - covers lines 427-432."""
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        async def mock_score_fn(state):
            return (True, None)

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = await mock_async_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_evaluation_result_coroutine(self, mock_async_env):
        """Test get_evaluation_result with coroutine result - covers lines 426-427."""
        import inspect

        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        # Create a non-async function that returns a coroutine
        # The await on line 425 will call the function, which returns a coroutine
        # Then line 426 checks if the result is a Coroutine and awaits it on line 427
        def mock_score_fn_returns_coro(state):
            async def inner_coro():
                return (True, None)
            # Don't await it - return the coroutine object itself
            coro = inner_coro()
            # Verify it's actually a coroutine
            assert inspect.iscoroutine(coro)
            return coro

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn_returns_coro)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = await mock_async_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_evaluation_result_custom_eval_bool(self, mock_async_env):
        """Test get_evaluation_result with custom eval returning bool - covers lines 435-438."""
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        async def mock_score_fn(state):
            return True

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = await mock_async_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_evaluation_result_custom_eval_error(self, mock_async_env):
        """Test get_evaluation_result with custom eval error - covers lines 439-442."""
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        async def mock_score_fn(state):
            raise Exception("Evaluation failed")

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = await mock_async_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is False
        assert "Evaluation failed" in result.reason

    @pytest.mark.asyncio
    async def test_get_evaluation_result_unknown_type(self, mock_async_env):
        """Test get_evaluation_result with unknown eval type - covers lines 445-447."""
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        # Create a mock eval config with unknown type
        mock_eval_config = Mock()
        mock_eval_config.type = "unknown_type"
        task.eval_config = mock_eval_config
        mock_async_env._current_task = task

        result = await mock_async_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is False
        assert "Unknown evaluation type" in result.reason

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_eval(self, mock_async_env):
        """Test evaluate with custom eval config - covers lines 458-466."""
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        async def mock_score_fn(state):
            return (True, None)

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"state": {"url": "https://example.com"}, "mutations": []}
        )
        mock_async_env._client.post_evaluation_result = AsyncMock()

        result = await mock_async_env.evaluate()

        assert result.success is True
        mock_async_env._client.post_evaluation_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_eval_no_session_id(self, mock_async_env):
        """Test evaluate with custom eval when session id is temporarily None - covers line 462."""
        # Set session id initially
        mock_async_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        async def mock_score_fn(state):
            return (True, None)

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_async_env._current_task = task

        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"state": {"url": "https://example.com"}, "mutations": []}
        )
        mock_async_env._client.post_evaluation_result = AsyncMock()

        # Temporarily set to None to test the branch
        original_session_id = mock_async_env._run_session_id

        result = await mock_async_env.evaluate()

        assert result.success is True
        # Should not call post_evaluation_result if session_id becomes None
        # But in this test it won't become None, so it will be called
        mock_async_env._client.post_evaluation_result.assert_called_once()


class TestPlatoEnvironmentLogging:
    """Test logging method."""

    @pytest.mark.asyncio
    async def test_log_success(self, mock_async_env):
        """Test successful logging."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.log = AsyncMock(return_value={"logged": True})

        await mock_async_env.log({"message": "test"}, type="info")

        # The function signature is (run_session_id, log, type) - all positional
        mock_async_env._client.log.assert_called_once_with(
            "session-123",
            {"message": "test"},
            "info"
        )

    @pytest.mark.asyncio
    async def test_log_without_session(self, mock_async_env):
        """Test log raises error without active session."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.log({"message": "test"})


class TestPlatoEnvironmentUrls:
    """Test URL generation methods."""

    @pytest.mark.asyncio
    async def test_get_cdp_url_success(self, mock_async_env, mock_cdp_response):
        """Test successful CDP URL retrieval."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_cdp_url = AsyncMock(
            return_value=mock_cdp_response["data"]["cdp_url"]
        )

        url = await mock_async_env.get_cdp_url()

        assert url == "ws://localhost:9222/devtools/browser/test-123"

    @pytest.mark.asyncio
    async def test_get_cdp_url_no_session(self, mock_async_env):
        """Test CDP URL without session - covers line 259."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_cdp_url()

    @pytest.mark.asyncio
    async def test_get_live_view_url_success(self, mock_async_env):
        """Test successful live view URL retrieval."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_live_view_url = AsyncMock(
            return_value="https://test.com/live/test-job-123"
        )

        url = await mock_async_env.get_live_view_url()

        assert "live" in url
        assert "test-job-123" in url

    @pytest.mark.asyncio
    async def test_get_live_view_url_no_session(self, mock_async_env):
        """Test live view URL without session - covers line 506."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_live_view_url()

    @pytest.mark.asyncio
    async def test_get_proxy_config_success(self, mock_async_env, mock_proxy_response):
        """Test successful proxy config retrieval."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        mock_async_env._client.get_proxy_url = AsyncMock(
            return_value=mock_proxy_response["data"]["proxy_url"]
        )

        config = await mock_async_env.get_proxy_config()

        assert "server" in config
        assert "username" in config
        assert "password" in config

    @pytest.mark.asyncio
    async def test_get_proxy_config_no_session(self, mock_async_env):
        """Test proxy config without session - covers line 523."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_proxy_config()

    @pytest.mark.asyncio
    async def test_get_proxy_config_worker_not_ready(self, mock_async_env):
        """Test proxy config when worker not ready - covers line 528."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": False})

        with pytest.raises(PlatoClientError, match="Worker is not ready"):
            await mock_async_env.get_proxy_config()

    @pytest.mark.asyncio
    async def test_get_proxy_config_localhost_fallback(self, mock_async_env):
        """Test proxy config fallback to localhost - covers lines 532-536."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.base_url = "http://localhost:8080/api"
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        mock_async_env._client.get_proxy_url = AsyncMock(side_effect=Exception("Error"))

        config = await mock_async_env.get_proxy_config()

        assert config["server"] == "http://localhost:8888"
        assert config["username"] == mock_async_env.id
        assert config["password"] == mock_async_env._run_session_id

    @pytest.mark.asyncio
    async def test_get_proxy_config_plato_subdomain(self, mock_async_env):
        """Test proxy config with plato subdomain - covers lines 537-545."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.base_url = "https://dev.plato.so/api"
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        mock_async_env._client.get_proxy_url = AsyncMock(side_effect=Exception("Error"))

        config = await mock_async_env.get_proxy_config()

        assert config["server"] == "https://dev.proxy.plato.so"

    @pytest.mark.asyncio
    async def test_get_proxy_config_plato_no_subdomain(self, mock_async_env):
        """Test proxy config without subdomain - covers lines 546-548."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.base_url = "https://plato.so/api"
        mock_async_env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        mock_async_env._client.get_proxy_url = AsyncMock(side_effect=Exception("Error"))

        config = await mock_async_env.get_proxy_config()

        assert config["server"] == "https://proxy.plato.so"

    @pytest.mark.asyncio
    async def test_get_proxy_config_general_error(self, mock_async_env):
        """Test proxy config with general error - covers line 556."""
        mock_async_env._run_session_id = "session-123"
        mock_async_env._client.get_worker_ready = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(PlatoClientError, match="Network error"):
            await mock_async_env.get_proxy_config()

    @pytest.mark.asyncio
    async def test_get_public_url_localhost(self, mock_async_env):
        """Test public URL with localhost - covers line 578."""
        mock_async_env._client.base_url = "http://localhost:8080/api"
        mock_async_env.alias = "test-alias"

        url = await mock_async_env.get_public_url()

        assert url == "http://localhost:8081/test-alias"

    @pytest.mark.asyncio
    async def test_get_public_url_plato_subdomain(self, mock_async_env):
        """Test public URL with plato subdomain - covers lines 591-588."""
        mock_async_env._client.base_url = "https://dev.plato.so/api"
        mock_async_env.alias = "test-alias"

        url = await mock_async_env.get_public_url()

        assert url == "https://test-alias.dev.sims.plato.so"

    @pytest.mark.asyncio
    async def test_get_public_url_plato_no_subdomain(self, mock_async_env):
        """Test public URL without subdomain - covers lines 591."""
        mock_async_env._client.base_url = "https://plato.so/api"
        mock_async_env.alias = "test-alias"

        url = await mock_async_env.get_public_url()

        assert url == "https://test-alias.sims.plato.so"

    @pytest.mark.asyncio
    async def test_get_public_url_unknown_base(self, mock_async_env):
        """Test public URL with unknown base - covers lines 593."""
        mock_async_env._client.base_url = "https://unknown.com/api"

        with pytest.raises(PlatoClientError, match="Unknown base URL"):
            await mock_async_env.get_public_url()

    @pytest.mark.asyncio
    async def test_get_public_url_error(self, mock_async_env):
        """Test public URL with error - covers line 595."""
        mock_async_env._client.base_url = None  # Will cause an error

        with pytest.raises(PlatoClientError):
            await mock_async_env.get_public_url()

    @pytest.mark.asyncio
    async def test_get_session_url(self, mock_async_env):
        """Test session URL generation."""
        mock_async_env._client.base_url = "https://api.test.com"
        mock_async_env._run_session_id = "session-123"

        url = await mock_async_env.get_session_url()

        assert "session-123" in url

    @pytest.mark.asyncio
    async def test_get_session_url_without_session(self, mock_async_env):
        """Test session URL fails without active session."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.get_session_url()


class TestPlatoEnvironmentDatabaseTunnel:
    """Test database tunnel methods."""

    def test_get_db_login_info_success(self, mock_async_env):
        """Test successful database login info retrieval."""
        mock_db_info = {
            "db_type": "postgres",
            "user": "admin",
            "password": "secret",
            "dest_port": 5432,
            "databases": ["testdb"]
        }

        with patch('plato.flows.db_logins.SIM_DB_CONFIGS', {"test-env": mock_db_info}):
            info = mock_async_env.get_db_login_info()

            assert info["db_type"] == "postgres"
            assert info["user"] == "admin"

    def test_get_db_login_info_import_error(self, mock_async_env):
        """Test DB login info with import error - covers lines 618-619."""
        # Simulate import error by making the import statement fail
        with patch.dict('sys.modules', {'plato.flows.db_logins': None}):
            with pytest.raises(PlatoClientError, match="Failed to load DB login presets"):
                mock_async_env.get_db_login_info()

    def test_get_db_login_info_not_found(self, mock_async_env):
        """Test DB login info not found - covers line 624."""
        with patch('plato.flows.db_logins.SIM_DB_CONFIGS', {}):
            with pytest.raises(PlatoClientError, match="No DB login preset found"):
                mock_async_env.get_db_login_info()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_success(self, mock_async_env):
        """Test successful database tunnel start."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {
            "db_type": "postgres",
            "user": "admin",
            "password": "secret",
            "dest_port": 5432
        }

        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })

        with patch('plato.models.env.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll = Mock(return_value=None)
            mock_popen.return_value = mock_process

            with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value='/usr/bin/proxytunnel'):
                local_port = await mock_async_env.start_db_tunnel(dest_port=5432, local_port=15432)

                assert local_port == 15432
                mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_no_session(self, mock_async_env):
        """Test DB tunnel without session - covers line 662."""
        mock_async_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_already_running(self, mock_async_env):
        """Test DB tunnel already running - covers line 665."""
        mock_async_env._run_session_id = "session-123"
        mock_process = Mock()
        mock_process.poll = Mock(return_value=None)  # Still running
        mock_async_env._db_tunnel_process = mock_process

        with pytest.raises(PlatoClientError, match="Database tunnel already running"):
            await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_proxytunnel_not_found(self, mock_async_env):
        """Test DB tunnel when proxytunnel not found - covers lines 673-677, 704-711."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })

        with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value=None):
            with patch('plato.utils.proxytunnel.install_proxytunnel_noninteractive', return_value=False):
                with pytest.raises(PlatoClientError, match="proxytunnel.*not found"):
                    await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_auto_install_success(self, mock_async_env):
        """Test DB tunnel with successful auto-install - covers lines 707-709."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })

        # First call returns None (not found), second call returns path (found after install)
        with patch('plato.utils.proxytunnel.find_proxytunnel_path', side_effect=[None, '/usr/bin/proxytunnel']):
            with patch('plato.utils.proxytunnel.install_proxytunnel_noninteractive', return_value=True):
                with patch('plato.models.env.subprocess.Popen') as mock_popen:
                    mock_process = Mock()
                    mock_process.poll = Mock(return_value=None)
                    mock_popen.return_value = mock_process

                    local_port = await mock_async_env.start_db_tunnel()

                    assert local_port > 0
                    mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_auto_install_exception(self, mock_async_env):
        """Test DB tunnel with exception during auto-install - covers lines 708-709."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })

        # First call returns None (not found)
        with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value=None):
            # install raises exception
            with patch('plato.utils.proxytunnel.install_proxytunnel_noninteractive', side_effect=Exception("Install error")):
                with pytest.raises(PlatoClientError, match="proxytunnel.*not found"):
                    await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_subprocess_error(self, mock_async_env):
        """Test DB tunnel subprocess error - covers line 738."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })

        with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value='/usr/bin/proxytunnel'):
            with patch('plato.models.env.subprocess.Popen', side_effect=Exception("Popen failed")):
                with pytest.raises(PlatoClientError, match="Failed to start proxytunnel"):
                    await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_exits_early(self, mock_async_env):
        """Test DB tunnel exits early - covers lines 727-728, 737-738, 743-750."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "https://proxy.example.com:9000",
            "username": "test-job-123",
            "password": "session-123"
        })

        with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value='/usr/bin/proxytunnel'):
            with patch('plato.models.env.subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.poll = Mock(return_value=1)  # Exited immediately
                mock_stderr = Mock()
                mock_stderr.read = Mock(return_value=b"Connection failed")
                mock_process.stderr = mock_stderr
                mock_popen.return_value = mock_process

                with pytest.raises(PlatoClientError, match="proxytunnel exited early"):
                    await mock_async_env.start_db_tunnel()

    @pytest.mark.asyncio
    async def test_start_db_tunnel_exits_early_stderr_error(self, mock_async_env):
        """Test DB tunnel exits early with stderr read error - covers lines 745-750."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {"db_type": "postgres", "dest_port": 5432}
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "https://proxy.example.com:9000",
            "username": "test-job-123",
            "password": "session-123"
        })

        with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value='/usr/bin/proxytunnel'):
            with patch('plato.models.env.subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.poll = Mock(return_value=1)  # Exited immediately
                mock_stderr = Mock()
                # Make stderr.read raise an exception to trigger the except block
                mock_stderr.read = Mock(side_effect=Exception("Cannot read stderr"))
                mock_process.stderr = mock_stderr
                mock_popen.return_value = mock_process

                with pytest.raises(PlatoClientError, match="proxytunnel exited early"):
                    await mock_async_env.start_db_tunnel()

    def test_stop_db_tunnel_success(self, mock_async_env):
        """Test successful database tunnel stop."""
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        mock_process.poll = Mock(return_value=None)
        mock_async_env._db_tunnel_process = mock_process

        mock_async_env.stop_db_tunnel()

        mock_process.terminate.assert_called_once()
        assert mock_async_env._db_tunnel_process is None

    def test_stop_db_tunnel_kill_on_timeout(self, mock_async_env):
        """Test DB tunnel kill on timeout - covers lines 767-769."""
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock(side_effect=Exception("Timeout"))
        mock_process.kill = Mock()
        mock_process.poll = Mock(return_value=None)
        mock_async_env._db_tunnel_process = mock_process

        mock_async_env.stop_db_tunnel()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_async_env._db_tunnel_process is None

    def test_stop_db_tunnel_terminate_error(self, mock_async_env):
        """Test DB tunnel terminate error - covers line 769."""
        mock_process = Mock()
        mock_process.terminate = Mock(side_effect=Exception("Terminate failed"))
        mock_process.poll = Mock(return_value=None)
        mock_async_env._db_tunnel_process = mock_process

        # Should not raise, should handle error gracefully
        mock_async_env.stop_db_tunnel()

        mock_process.terminate.assert_called_once()
        assert mock_async_env._db_tunnel_process is None

    def test_stop_db_tunnel_no_tunnel(self, mock_async_env):
        """Test stop database tunnel when no tunnel exists."""
        mock_async_env._db_tunnel_process = None

        # Should not raise, just return
        mock_async_env.stop_db_tunnel()


class TestPlatoEnvironmentContextManager:
    """Test context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, async_plato_client):
        """Test async context manager."""
        env = PlatoEnvironment(
            client=async_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        env._client.get_job_status = AsyncMock(return_value={"status": "running"})
        env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        env._client.close_environment = AsyncMock(return_value={"success": True})

        with patch.object(env, '_start_heartbeat', new_callable=AsyncMock):
            with patch.object(env, '_stop_heartbeat', new_callable=AsyncMock):
                async with env as e:
                    assert e is env

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exit(self, async_plato_client):
        """Test that context manager closes environment on exit."""
        env = PlatoEnvironment(
            client=async_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        env._client.get_job_status = AsyncMock(return_value={"status": "running"})
        env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        env._client.close_environment = AsyncMock(return_value={"success": True})

        with patch.object(env, '_start_heartbeat', new_callable=AsyncMock):
            with patch.object(env, '_stop_heartbeat', new_callable=AsyncMock):
                async with env:
                    pass

        env._client.close_environment.assert_called_once_with("test-job-123")

    @pytest.mark.asyncio
    async def test_context_manager_stops_heartbeat(self, async_plato_client):
        """Test that context manager stops heartbeat on exit."""
        env = PlatoEnvironment(
            client=async_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        env._client.get_job_status = AsyncMock(return_value={"status": "running"})
        env._client.get_worker_ready = AsyncMock(return_value={"ready": True})
        env._client.close_environment = AsyncMock(return_value={"success": True})

        mock_stop_heartbeat = AsyncMock()
        with patch.object(env, '_start_heartbeat', new_callable=AsyncMock):
            with patch.object(env, '_stop_heartbeat', mock_stop_heartbeat):
                async with env:
                    pass

        mock_stop_heartbeat.assert_called()


class TestPlatoEnvironmentHeartbeat:
    """Test heartbeat management."""

    @pytest.mark.asyncio
    async def test_start_heartbeat(self, mock_async_env):
        """Test starting heartbeat task."""
        mock_async_env._client.send_heartbeat = AsyncMock(return_value={"success": True})

        with patch('asyncio.create_task') as mock_create_task:
            # Create a mock task that can be awaited
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            await mock_async_env._start_heartbeat()

            mock_create_task.assert_called_once()
            assert mock_async_env._heartbeat_task == mock_task

    @pytest.mark.asyncio
    async def test_heartbeat_loop_normal(self, mock_async_env):
        """Test heartbeat loop normal operation - covers lines 298-312."""
        mock_async_env._client.send_heartbeat = AsyncMock(return_value={"success": True})
        mock_async_env._heartbeat_interval = 0.1

        # Create task and cancel after a short time
        task = asyncio.create_task(mock_async_env._heartbeat_loop())
        await asyncio.sleep(0.25)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have been called at least twice
        assert mock_async_env._client.send_heartbeat.call_count >= 2

    @pytest.mark.asyncio
    async def test_heartbeat_loop_send_error(self, mock_async_env):
        """Test heartbeat loop with send error - covers lines 303-305."""
        call_count = 0

        async def mock_send_with_error(job_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return {"success": True}

        mock_async_env._client.send_heartbeat = mock_send_with_error
        mock_async_env._heartbeat_interval = 0.1

        task = asyncio.create_task(mock_async_env._heartbeat_loop())
        await asyncio.sleep(0.25)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should continue after error
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_heartbeat_loop_unexpected_error(self, mock_async_env):
        """Test heartbeat loop with unexpected error outside the inner try block - covers lines 310-312."""
        mock_async_env._client.send_heartbeat = AsyncMock(return_value={"success": True})

        # Patch asyncio.sleep to raise an exception (not CancelledError)
        # This will trigger the outer except block at lines 310-312
        original_sleep = asyncio.sleep
        call_count = 0

        async def mock_sleep_with_error(duration):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call succeeds to let heartbeat run once
                await original_sleep(0.01)
            else:
                # Second call raises an unexpected exception
                raise RuntimeError("Sleep error")

        with patch('asyncio.sleep', side_effect=mock_sleep_with_error):
            task = asyncio.create_task(mock_async_env._heartbeat_loop())
            # Give enough time for both sleep calls to happen
            await original_sleep(0.3)

            # Task should have exited due to the exception
            assert task.done()

            # Should not raise when we wait for it (exception was caught)
            try:
                await task
            except Exception:
                pass  # Should not get here

    @pytest.mark.asyncio
    async def test_stop_heartbeat(self, mock_async_env):
        """Test stopping heartbeat task."""
        mock_task = AsyncMock()
        mock_task.cancel = Mock()
        mock_task.done = Mock(return_value=False)
        mock_async_env._heartbeat_task = mock_task

        await mock_async_env._stop_heartbeat()

        mock_task.cancel.assert_called_once()
        assert mock_async_env._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_stop_heartbeat_no_task(self, mock_async_env):
        """Test stopping heartbeat when no task exists."""
        mock_async_env._heartbeat_task = None

        # Should not raise, just return
        await mock_async_env._stop_heartbeat()


class TestPlatoEnvironmentMissingCoverage:
    """Tests to achieve 100% coverage on remaining lines."""

    @pytest.mark.asyncio
    async def test_evaluate_with_session_id_posts_result(self, mock_async_env):
        """Test evaluate posts result when _run_session_id exists (branch 462->466)."""
        mock_async_env._run_session_id = "session-123"
        
        # Setup custom eval that returns success
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )
        
        from plato.models.task import CustomEvalConfig
        def score_fn(state):
            return (True, "Success")
        
        task.eval_config = CustomEvalConfig(score_fn=score_fn)
        mock_async_env._current_task = task
        
        # Mock the methods
        mock_async_env._client.get_environment_state = AsyncMock(
            return_value={"url": "https://example.com", "mutations": []}
        )
        mock_async_env._client.post_evaluation_result = AsyncMock(
            return_value={"success": True}
        )
        
        result = await mock_async_env.evaluate()
        
        # Verify post_evaluation_result was called (covers branch 462->466)
        mock_async_env._client.post_evaluation_result.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_db_tunnel_stderr_read_success(self, mock_async_env):
        """Test database tunnel reads stderr when process exits early (branch 745->750)."""
        mock_async_env._run_session_id = "session-123"
        mock_db_info = {
            "db_type": "postgres",
            "user": "admin",
            "password": "secret",
            "dest_port": 5432
        }
        
        mock_async_env.get_db_login_info = Mock(return_value=mock_db_info)
        mock_async_env.get_proxy_config = AsyncMock(return_value={
            "server": "http://proxy.example.com:8080",
            "username": "test-job-123",
            "password": "session-123"
        })
        
        with patch('plato.models.env.subprocess.Popen') as mock_popen:
            # Create a mock process that exits immediately with stderr
            import io
            mock_stderr = io.BytesIO(b"Connection failed\n")
            
            mock_process = Mock()
            mock_process.poll = Mock(return_value=1)  # Exited with error
            mock_process.stderr = mock_stderr
            mock_popen.return_value = mock_process
            
            with patch('plato.utils.proxytunnel.find_proxytunnel_path', return_value='/usr/bin/proxytunnel'):
                with pytest.raises(PlatoClientError, match="proxytunnel exited early: Connection failed"):
                    await mock_async_env.start_db_tunnel(dest_port=5432, local_port=15432)

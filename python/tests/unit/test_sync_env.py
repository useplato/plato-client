"""Unit tests for sync PlatoEnvironment (plato.sync_env.SyncPlatoEnvironment class)."""

import pytest
from unittest.mock import Mock, patch
from plato.sync_env import SyncPlatoEnvironment
from plato.models import PlatoTask
from plato.models.task import EvaluationResult, CustomEvalConfig
from plato.exceptions import PlatoClientError
import json
import time


class TestSyncPlatoEnvironmentInit:
    """Test SyncPlatoEnvironment initialization."""

    def test_init_basic(self, sync_plato_client):
        """Test basic initialization."""
        env = SyncPlatoEnvironment(
            client=sync_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        assert env._client == sync_plato_client
        assert env.id == "test-job-123"
        assert env.env_id == "test-env"
        assert env.alias is None
        assert env._run_session_id is None
        assert env.fast is False

    def test_init_with_all_params(self, sync_plato_client):
        """Test initialization with all parameters."""
        env = SyncPlatoEnvironment(
            client=sync_plato_client,
            id="test-job-123",
            env_id="test-env",
            alias="test-alias",
            active_session="session-123",
            fast=True
        )

        assert env.alias == "test-alias"
        assert env._run_session_id == "session-123"
        assert env.fast is True

    def test_from_id_static_method(self, sync_plato_client):
        """Test from_id static method."""
        env = SyncPlatoEnvironment.from_id(
            client=sync_plato_client,
            id="test-job-123",
            fast=True
        )

        assert isinstance(env, SyncPlatoEnvironment)
        assert env.id == "test-job-123"
        assert env.fast is True


class TestSyncPlatoEnvironmentLogin:
    """Test login method."""

    def test_login_from_api_success(self, mock_sync_env, mock_simulator_flows, mock_sync_playwright_page):
        """Test successful login from API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=True)
                mock_executor_class.return_value = mock_executor

                mock_sync_env.login(mock_sync_playwright_page, from_api=True)

                mock_executor.execute_flow.assert_called_once()

    def test_login_from_local_file(self, mock_sync_env, mock_sync_playwright_page):
        """Test login from local file."""
        mock_sync_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [{
                "name": "login",
                "steps": []
            }]
        }

        with patch('plato.sync_env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('plato.sync_env.yaml.safe_load', return_value=mock_yaml_content):
                    with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                        mock_executor = Mock()
                        mock_executor.execute_flow = Mock(return_value=True)
                        mock_executor_class.return_value = mock_executor

                        mock_sync_env.login(mock_sync_playwright_page, from_api=False)

                        mock_executor.execute_flow.assert_called_once()

    def test_login_no_env_id(self, mock_sync_env, mock_sync_playwright_page):
        """Test login fails without env_id."""
        mock_sync_env.env_id = None

        with pytest.raises(PlatoClientError, match="No env_id set"):
            mock_sync_env.login(mock_sync_playwright_page, from_api=False)

    def test_login_failure_with_throw(self, mock_sync_env, mock_simulator_flows, mock_sync_playwright_page):
        """Test login failure with throw_on_login_error=True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=False)
                mock_executor_class.return_value = mock_executor

                with pytest.raises(PlatoClientError, match="Failed to login"):
                    mock_sync_env.login(mock_sync_playwright_page, from_api=True, throw_on_login_error=True)

    def test_login_failure_without_throw(self, mock_sync_env, mock_simulator_flows, mock_sync_playwright_page):
        """Test login failure with throw_on_login_error=False."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_simulator_flows

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=False)
                mock_executor_class.return_value = mock_executor

                # Should not raise, just log warning
                mock_sync_env.login(mock_sync_playwright_page, from_api=True, throw_on_login_error=False)

    def test_login_from_api_json_with_data_flows(self, mock_sync_env, mock_simulator_flows, mock_sync_playwright_page):
        """Test login from API with JSON response containing data.flows - covers lines 100-105."""
        json_response = json.dumps({"data": {"flows": mock_simulator_flows}})
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json_response

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_flow = Mock(return_value=True)
                mock_executor_class.return_value = mock_executor

                mock_sync_env.login(mock_sync_playwright_page, from_api=True)

                mock_executor.execute_flow.assert_called_once()

    def test_login_from_api_json_missing_flows(self, mock_sync_env, mock_sync_playwright_page):
        """Test login from API with JSON missing flows - covers lines 104-106."""
        json_response = json.dumps({"data": {}})  # Missing flows key
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json_response

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            # Should fall back to treating as YAML (lines 107-108)
            with pytest.raises(Exception):  # Will fail during YAML parsing
                mock_sync_env.login(mock_sync_playwright_page, from_api=True)

    def test_login_from_api_error(self, mock_sync_env, mock_sync_playwright_page):
        """Test login from API with error - covers lines 110-111."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"

        mock_sync_env._client._handle_response_error = Mock(side_effect=Exception("API Error"))

        with patch.object(mock_sync_env._client.http_session, 'get', return_value=mock_response):
            with pytest.raises(PlatoClientError, match="Failed to load flows from API"):
                mock_sync_env.login(mock_sync_playwright_page, from_api=True)

    def test_login_file_not_exists(self, mock_sync_env, mock_sync_playwright_page):
        """Test login with missing file - covers line 121."""
        mock_sync_env.env_id = "test-env"

        with patch('plato.sync_env.os.path.exists', return_value=False):
            with pytest.raises(PlatoClientError, match="Flow scripts not found"):
                mock_sync_env.login(mock_sync_playwright_page, from_api=False)

    def test_login_custom_dataset(self, mock_sync_env, mock_sync_playwright_page):
        """Test login with custom dataset name - covers line 135."""
        mock_sync_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [
                {"name": "login", "steps": []},
                {"name": "custom_dataset", "steps": []}
            ]
        }

        with patch('plato.sync_env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('plato.sync_env.yaml.safe_load', return_value=mock_yaml_content):
                    with patch('plato.sync_flow_executor.SyncFlowExecutor') as mock_executor_class:
                        mock_executor = Mock()
                        mock_executor.execute_flow = Mock(return_value=True)
                        mock_executor_class.return_value = mock_executor

                        mock_sync_env.login(mock_sync_playwright_page, from_api=False, dataset="custom_dataset")

                        mock_executor.execute_flow.assert_called_once()

    def test_login_flow_not_found(self, mock_sync_env, mock_sync_playwright_page):
        """Test login with missing flow - covers line 139."""
        mock_sync_env.env_id = "test-env"

        mock_yaml_content = {
            "flows": [
                {"name": "some_other_flow", "steps": []}
            ]
        }

        with patch('plato.sync_env.os.path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('plato.sync_env.yaml.safe_load', return_value=mock_yaml_content):
                    with pytest.raises(PlatoClientError, match="No login flow"):
                        mock_sync_env.login(mock_sync_playwright_page, from_api=False)


class TestSyncPlatoEnvironmentWaitForReady:
    """Test wait_for_ready method."""

    def test_wait_for_ready_success(self, mock_sync_env, mock_job_status, mock_worker_ready):
        """Test successful wait for ready."""
        mock_sync_env._client.get_job_status = Mock(return_value=mock_job_status)
        mock_sync_env._client.get_worker_ready = Mock(return_value=mock_worker_ready)

        mock_sync_env.wait_for_ready()

        mock_sync_env._client.get_job_status.assert_called()
        mock_sync_env._client.get_worker_ready.assert_called()

    def test_wait_for_ready_timeout(self, mock_sync_env):
        """Test wait for ready with timeout."""
        mock_sync_env._client.get_job_status = Mock(
            return_value={"status": "pending"}
        )

        with pytest.raises(RuntimeError, match="failed to start"):
            mock_sync_env.wait_for_ready(timeout=0.1)

    def test_wait_for_ready_worker_not_ready_then_ready(self, mock_sync_env, mock_job_status):
        """Test wait for ready when worker becomes ready after delay."""
        mock_sync_env._client.get_job_status = Mock(return_value=mock_job_status)

        # First call returns not ready, second call returns ready
        mock_sync_env._client.get_worker_ready = Mock(
            side_effect=[
                {"ready": False},
                {"ready": True}
            ]
        )

        mock_sync_env.wait_for_ready()

        assert mock_sync_env._client.get_worker_ready.call_count == 2

    def test_wait_for_ready_exponential_backoff(self, mock_sync_env, mock_job_status):
        """Test exponential backoff during wait - covers lines 184-185."""
        # Return pending twice, then running
        mock_sync_env._client.get_job_status = Mock(
            side_effect=[
                {"status": "pending"},
                {"status": "pending"},
                {"status": "running"}
            ]
        )
        mock_sync_env._client.get_worker_ready = Mock(return_value={"ready": True})

        with patch('time.sleep'):  # Mock sleep to speed up test
            mock_sync_env.wait_for_ready()

        # Should have been called 3 times
        assert mock_sync_env._client.get_job_status.call_count == 3

    def test_wait_for_ready_worker_timeout(self, mock_sync_env, mock_job_status):
        """Test worker timeout with error message - covers lines 201-202."""
        mock_sync_env._client.get_job_status = Mock(return_value=mock_job_status)
        mock_sync_env._client.get_worker_ready = Mock(
            return_value={"ready": False, "error": "Worker initialization failed"}
        )

        with pytest.raises(RuntimeError, match="Worker initialization failed"):
            mock_sync_env.wait_for_ready(timeout=0.1)


class TestSyncPlatoEnvironmentReset:
    """Test reset method."""

    def test_reset_success(self, mock_sync_env):
        """Test successful environment reset."""
        mock_sync_env._client.reset_environment = Mock(
            return_value={"success": True, "data": {"run_session_id": "new-session-123"}}
        )

        session_id = mock_sync_env.reset()

        assert session_id == "new-session-123"
        assert mock_sync_env._run_session_id == "new-session-123"

    def test_reset_with_task(self, mock_sync_env):
        """Test environment reset with task."""
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        mock_sync_env._client.reset_environment = Mock(
            return_value={"success": True, "data": {"run_session_id": "new-session-123"}}
        )

        session_id = mock_sync_env.reset(task=task, agent_version="1.0", model="gpt-4")

        assert session_id == "new-session-123"
        mock_sync_env._client.reset_environment.assert_called_once()

        call_args = mock_sync_env._client.reset_environment.call_args
        assert call_args[0][0] == mock_sync_env.id
        assert call_args[0][1] == task

    def test_reset_sets_current_task(self, mock_sync_env):
        """Test that reset sets current task."""
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        mock_sync_env._client.reset_environment = Mock(
            return_value={"success": True, "data": {"run_session_id": "new-session-123"}}
        )

        mock_sync_env.reset(task=task)

        assert mock_sync_env._current_task == task

    def test_reset_failure(self, mock_sync_env):
        """Test reset failure - covers line 281."""
        mock_sync_env._client.reset_environment = Mock(
            return_value={"success": False, "error": "Reset failed"}
        )

        with pytest.raises(PlatoClientError, match="Reset failed"):
            mock_sync_env.reset()

    def test_reset_missing_session_id(self, mock_sync_env):
        """Test reset with missing session ID - covers line 286."""
        mock_sync_env._client.reset_environment = Mock(
            return_value={"success": True, "data": {"run_session_id": None}}
        )

        with pytest.raises(PlatoClientError, match="Failed to reset environment"):
            mock_sync_env.reset()


class TestSyncPlatoEnvironmentBackup:
    """Test backup method."""

    def test_backup_success(self, mock_sync_env):
        """Test successful environment backup."""
        mock_sync_env._client.backup_environment = Mock(
            return_value={"backup_id": "backup-123"}
        )

        result = mock_sync_env.backup()

        assert result["backup_id"] == "backup-123"
        mock_sync_env._client.backup_environment.assert_called_once_with(mock_sync_env.id)


class TestSyncPlatoEnvironmentState:
    """Test state management methods."""

    def test_get_state_success(self, mock_sync_env, mock_environment_state):
        """Test successful state retrieval."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_environment_state = Mock(
            return_value=mock_environment_state["data"]["state"]
        )

        state = mock_sync_env.get_state()

        assert state["url"] == "https://example.com"
        assert state["title"] == "Test Page"

    def test_get_state_with_merge_mutations(self, mock_sync_env, mock_environment_state):
        """Test state retrieval with merge_mutations."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_environment_state = Mock(
            return_value=mock_environment_state["data"]["state"]
        )

        mock_sync_env.get_state(merge_mutations=True)

        mock_sync_env._client.get_environment_state.assert_called_once_with(
            mock_sync_env.id,
            True
        )

    def test_get_state_mutations(self, mock_sync_env):
        """Test state mutations retrieval."""
        mock_sync_env._run_session_id = "session-123"
        mock_state = {
            "url": "https://example.com",
            "mutations": [
                {"type": "click", "target": "#button"},
                {"type": "fill", "target": "#input"}
            ]
        }

        mock_sync_env._client.get_environment_state = Mock(
            return_value=mock_state
        )

        mutations = mock_sync_env.get_state_mutations()

        assert len(mutations) == 2
        assert mutations[0]["type"] == "click"
        assert mutations[1]["type"] == "fill"

    def test_get_state_no_session(self, mock_sync_env):
        """Test get_state without session - covers line 342."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_state()

    def test_get_nested_value_simple(self, mock_sync_env):
        """Test _get_nested_value with simple path - covers lines 373-382."""
        data = {"a": {"b": {"c": "value"}}}
        result = mock_sync_env._get_nested_value(data, "a.b.c")
        assert result == "value"

    def test_get_nested_value_with_list_index(self, mock_sync_env):
        """Test _get_nested_value with list index - covers lines 373-382."""
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        result = mock_sync_env._get_nested_value(data, "items[1].name")
        assert result == "second"

    def test_get_nested_value_complex(self, mock_sync_env):
        """Test _get_nested_value with complex path - covers lines 373-382."""
        data = {"a": {"b": [{"c": 1}, {"c": 2, "d": [10, 20]}]}}
        result = mock_sync_env._get_nested_value(data, "a.b[1].c")
        assert result == 2


class TestSyncPlatoEnvironmentEvaluation:
    """Test evaluation methods."""

    def test_evaluate_success(self, mock_sync_env):
        """Test successful evaluation."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.evaluate = Mock(
            return_value={"result": {"correct": True, "reason": "Task completed successfully"}}
        )

        result = mock_sync_env.evaluate()

        assert isinstance(result, EvaluationResult)
        assert result.success is True
        assert result.reason == "Task completed successfully"

    def test_evaluate_without_session(self, mock_sync_env):
        """Test evaluate raises error without active session."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.evaluate()

    def test_evaluate_with_value(self, mock_sync_env):
        """Test evaluation with value parameter."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.evaluate = Mock(
            return_value={"result": {"correct": True, "reason": "Task completed successfully"}}
        )

        mock_sync_env.evaluate(value={"key": "value"})

        mock_sync_env._client.evaluate.assert_called_once_with(
            "session-123",
            {"key": "value"},
            None
        )

    def test_get_evaluation_result(self, mock_sync_env):
        """Test get_evaluation_result method with custom eval config."""
        mock_sync_env._run_session_id = "session-123"

        # Setup a task with custom eval config
        def score_fn(state):
            return True, "Task completed"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )
        task.eval_config = CustomEvalConfig(score_fn=score_fn)
        mock_sync_env._current_task = task

        # Mock get_state to return valid state
        mock_sync_env._client.get_environment_state = Mock(
            return_value={"url": "https://example.com"}
        )

        result = mock_sync_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    def test_get_evaluation_result_no_session(self, mock_sync_env):
        """Test get_evaluation_result without session - covers line 403."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_evaluation_result()

    def test_get_evaluation_result_no_config(self, mock_sync_env):
        """Test get_evaluation_result without config - covers lines 406-409."""
        mock_sync_env._run_session_id = "session-123"

        # Create task without eval_config
        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )
        task.eval_config = None
        mock_sync_env._current_task = task

        with pytest.raises(PlatoClientError, match="No evaluation config found"):
            mock_sync_env.get_evaluation_result()

    def test_get_evaluation_result_custom_eval_tuple(self, mock_sync_env):
        """Test get_evaluation_result with custom eval returning tuple - covers lines 427-430."""
        mock_sync_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        def mock_score_fn(state):
            return (True, None)

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_sync_env._current_task = task

        mock_sync_env._client.get_environment_state = Mock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = mock_sync_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    def test_get_evaluation_result_custom_eval_bool(self, mock_sync_env):
        """Test get_evaluation_result with custom eval returning bool - covers lines 427-430."""
        mock_sync_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        def mock_score_fn(state):
            return True

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_sync_env._current_task = task

        mock_sync_env._client.get_environment_state = Mock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = mock_sync_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is True

    def test_get_evaluation_result_custom_eval_error(self, mock_sync_env):
        """Test get_evaluation_result with custom eval error - covers lines 431-434."""
        mock_sync_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        def mock_score_fn(state):
            raise Exception("Evaluation failed")

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_sync_env._current_task = task

        mock_sync_env._client.get_environment_state = Mock(
            return_value={"url": "https://example.com", "title": "Test"}
        )

        result = mock_sync_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is False
        assert "Evaluation failed" in result.reason

    def test_get_evaluation_result_unknown_type(self, mock_sync_env):
        """Test get_evaluation_result with unknown eval type - covers lines 436-438."""
        mock_sync_env._run_session_id = "session-123"

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
        mock_sync_env._current_task = task

        result = mock_sync_env.get_evaluation_result()

        assert isinstance(result, EvaluationResult)
        assert result.success is False
        assert "Unknown evaluation type" in result.reason

    def test_evaluate_no_result(self, mock_sync_env):
        """Test evaluate with no result - covers line 475."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.evaluate = Mock(return_value=None)

        with pytest.raises(PlatoClientError, match="No evaluation result found"):
            mock_sync_env.evaluate()

    def test_evaluate_with_custom_eval(self, mock_sync_env):
        """Test evaluate with custom eval config - covers lines 462-470."""
        mock_sync_env._run_session_id = "session-123"

        task = PlatoTask(
            public_id="task-123",
            name="Test Task",
            prompt="Do something",
            start_url="https://example.com",
            env_id="test-env"
        )

        def mock_score_fn(state):
            return (True, None)

        task.eval_config = CustomEvalConfig(score_fn=mock_score_fn)
        mock_sync_env._current_task = task

        mock_sync_env._client.get_environment_state = Mock(
            return_value={"state": {"url": "https://example.com"}, "mutations": []}
        )
        mock_sync_env._client.post_evaluation_result = Mock()

        result = mock_sync_env.evaluate()

        assert result.success is True
        mock_sync_env._client.post_evaluation_result.assert_called_once()


class TestSyncPlatoEnvironmentLogging:
    """Test logging method."""

    def test_log_success(self, mock_sync_env):
        """Test successful logging."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.log = Mock(return_value={"logged": True})

        mock_sync_env.log({"message": "test"}, type="info")

        mock_sync_env._client.log.assert_called_once_with(
            "session-123",
            {"message": "test"},
            "info"
        )

    def test_log_without_session(self, mock_sync_env):
        """Test log raises error without active session."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.log({"message": "test"})


class TestSyncPlatoEnvironmentUrls:
    """Test URL generation methods."""

    def test_get_cdp_url_success(self, mock_sync_env, mock_cdp_response):
        """Test successful CDP URL retrieval."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_cdp_url = Mock(
            return_value=mock_cdp_response["data"]["cdp_url"]
        )

        url = mock_sync_env.get_cdp_url()

        assert url == "ws://localhost:9222/devtools/browser/test-123"

    def test_get_live_view_url_success(self, mock_sync_env):
        """Test successful live view URL retrieval."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_live_view_url = Mock(
            return_value="https://test.com/live/test-job-123"
        )

        url = mock_sync_env.get_live_view_url()

        assert "live" in url
        assert "test-job-123" in url

    def test_get_proxy_config_success(self, mock_sync_env, mock_proxy_response, mock_worker_ready):
        """Test successful proxy config retrieval."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_worker_ready = Mock(return_value=mock_worker_ready)
        mock_sync_env._client.get_proxy_url = Mock(
            return_value=mock_proxy_response["data"]["proxy_url"]
        )

        config = mock_sync_env.get_proxy_config()

        assert "server" in config
        assert "username" in config
        assert "password" in config

    def test_get_public_url(self, mock_sync_env):
        """Test public URL generation."""
        mock_sync_env._client.base_url = "https://dev.plato.so/api"

        url = mock_sync_env.get_public_url()

        # Uses alias if available
        assert "test-alias" in url

    def test_get_session_url(self, mock_sync_env):
        """Test session URL generation."""
        mock_sync_env._client.base_url = "https://api.test.com"
        mock_sync_env._run_session_id = "session-123"

        url = mock_sync_env.get_session_url()

        assert "session-123" in url

    def test_get_session_url_without_session(self, mock_sync_env):
        """Test session URL fails without active session."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_session_url()

    def test_get_cdp_url_no_session(self, mock_sync_env):
        """Test CDP URL without session - covers line 253."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_cdp_url()

    def test_get_live_view_url_no_session(self, mock_sync_env):
        """Test live view URL without session - covers line 509."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_live_view_url()

    def test_get_proxy_config_no_session(self, mock_sync_env):
        """Test proxy config without session - covers line 526."""
        mock_sync_env._run_session_id = None

        with pytest.raises(PlatoClientError, match="No active run session"):
            mock_sync_env.get_proxy_config()

    def test_get_proxy_config_worker_not_ready(self, mock_sync_env):
        """Test proxy config when worker not ready - covers line 531."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_worker_ready = Mock(return_value={"ready": False})

        with pytest.raises(PlatoClientError, match="Worker is not ready"):
            mock_sync_env.get_proxy_config()

    def test_get_proxy_config_localhost_fallback(self, mock_sync_env):
        """Test proxy config fallback to localhost - covers lines 535-539."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.base_url = "http://localhost:8080/api"
        mock_sync_env._client.get_worker_ready = Mock(return_value={"ready": True})
        mock_sync_env._client.get_proxy_url = Mock(side_effect=Exception("Error"))

        config = mock_sync_env.get_proxy_config()

        assert config["server"] == "http://localhost:8888"
        assert config["username"] == mock_sync_env.id
        assert config["password"] == mock_sync_env._run_session_id

    def test_get_proxy_config_plato_subdomain(self, mock_sync_env):
        """Test proxy config with plato subdomain - covers lines 540-548."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.base_url = "https://dev.plato.so/api"
        mock_sync_env._client.get_worker_ready = Mock(return_value={"ready": True})
        mock_sync_env._client.get_proxy_url = Mock(side_effect=Exception("Error"))

        config = mock_sync_env.get_proxy_config()

        assert config["server"] == "https://dev.proxy.plato.so"

    def test_get_proxy_config_plato_no_subdomain(self, mock_sync_env):
        """Test proxy config without subdomain - covers lines 549-551."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.base_url = "https://plato.so/api"
        mock_sync_env._client.get_worker_ready = Mock(return_value={"ready": True})
        mock_sync_env._client.get_proxy_url = Mock(side_effect=Exception("Error"))

        config = mock_sync_env.get_proxy_config()

        assert config["server"] == "https://proxy.plato.so"

    def test_get_proxy_config_general_error(self, mock_sync_env):
        """Test proxy config with general error - covers line 559."""
        mock_sync_env._run_session_id = "session-123"
        mock_sync_env._client.get_worker_ready = Mock(side_effect=Exception("Network error"))

        with pytest.raises(PlatoClientError, match="Network error"):
            mock_sync_env.get_proxy_config()

    def test_get_public_url_localhost(self, mock_sync_env):
        """Test public URL with localhost - covers line 581."""
        mock_sync_env._client.base_url = "http://localhost:8080/api"
        mock_sync_env.alias = "test-alias"

        url = mock_sync_env.get_public_url()

        assert url == "http://localhost:8081/test-alias"

    def test_get_public_url_plato_subdomain(self, mock_sync_env):
        """Test public URL with plato subdomain - covers lines 582-591."""
        mock_sync_env._client.base_url = "https://dev.plato.so/api"
        mock_sync_env.alias = "test-alias"

        url = mock_sync_env.get_public_url()

        assert url == "https://test-alias.dev.sims.plato.so"

    def test_get_public_url_plato_no_subdomain(self, mock_sync_env):
        """Test public URL without subdomain - covers lines 592-594."""
        mock_sync_env._client.base_url = "https://plato.so/api"
        mock_sync_env.alias = "test-alias"

        url = mock_sync_env.get_public_url()

        assert url == "https://test-alias.sims.plato.so"

    def test_get_public_url_unknown_base(self, mock_sync_env):
        """Test public URL with unknown base - covers line 596."""
        mock_sync_env._client.base_url = "https://unknown.com/api"

        with pytest.raises(PlatoClientError, match="Unknown base URL"):
            mock_sync_env.get_public_url()

    def test_get_public_url_error(self, mock_sync_env):
        """Test public URL with error - covers line 598."""
        mock_sync_env._client.base_url = None  # Will cause an error

        with pytest.raises(PlatoClientError):
            mock_sync_env.get_public_url()


class TestSyncPlatoEnvironmentContextManager:
    """Test context manager behavior."""

    def test_context_manager_enter_exit(self, sync_plato_client, mock_job_status, mock_worker_ready):
        """Test sync context manager."""
        env = SyncPlatoEnvironment(
            client=sync_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        # Mock wait_for_ready dependencies
        env._client.get_job_status = Mock(return_value=mock_job_status)
        env._client.get_worker_ready = Mock(return_value=mock_worker_ready)
        env._client.close_environment = Mock(return_value={"success": True})

        with env as e:
            assert e is env

    def test_context_manager_closes_on_exit(self, sync_plato_client, mock_job_status, mock_worker_ready):
        """Test that context manager closes environment on exit."""
        env = SyncPlatoEnvironment(
            client=sync_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        # Mock wait_for_ready dependencies
        env._client.get_job_status = Mock(return_value=mock_job_status)
        env._client.get_worker_ready = Mock(return_value=mock_worker_ready)
        env._client.close_environment = Mock(return_value={"success": True})

        with env:
            pass

        env._client.close_environment.assert_called_once_with("test-job-123")

    def test_context_manager_stops_heartbeat(self, sync_plato_client, mock_job_status, mock_worker_ready):
        """Test that context manager stops heartbeat on exit."""
        env = SyncPlatoEnvironment(
            client=sync_plato_client,
            id="test-job-123",
            env_id="test-env"
        )

        # Mock wait_for_ready dependencies
        env._client.get_job_status = Mock(return_value=mock_job_status)
        env._client.get_worker_ready = Mock(return_value=mock_worker_ready)

        mock_heartbeat_thread = Mock()
        mock_heartbeat_thread.is_alive = Mock(return_value=True)
        mock_heartbeat_thread.join = Mock()
        env._heartbeat_thread = mock_heartbeat_thread
        env._stop_heartbeat = False

        env._client.close_environment = Mock(return_value={"success": True})

        with env:
            pass

        # Verify that _stop_heartbeat was set to True
        assert env._stop_heartbeat is True
        mock_heartbeat_thread.join.assert_called_once()


class TestSyncPlatoEnvironmentHeartbeat:
    """Test heartbeat management."""

    def test_start_heartbeat(self, mock_sync_env):
        """Test starting heartbeat thread."""
        mock_sync_env._client.send_heartbeat = Mock(return_value={"success": True})

        with patch('threading.Thread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread.daemon = False
            mock_thread.start = Mock()
            mock_thread_class.return_value = mock_thread

            mock_sync_env._start_heartbeat()

            mock_thread_class.assert_called_once()
            mock_thread.start.assert_called_once()

    def test_stop_heartbeat(self, mock_sync_env):
        """Test stopping heartbeat thread."""
        mock_thread = Mock()
        mock_thread.is_alive = Mock(return_value=True)
        mock_thread.join = Mock()

        mock_sync_env._heartbeat_thread = mock_thread
        mock_sync_env._stop_heartbeat = False

        mock_sync_env._stop_heartbeat_thread()

        assert mock_sync_env._stop_heartbeat is True
        mock_thread.join.assert_called_once()

    def test_stop_heartbeat_no_thread(self, mock_sync_env):
        """Test stopping heartbeat when no thread exists."""
        mock_sync_env._heartbeat_thread = None

        # Should not raise, just return
        mock_sync_env._stop_heartbeat_thread()

    def test_heartbeat_loop_normal(self, mock_sync_env):
        """Test heartbeat loop normal operation - covers lines 299-306."""
        mock_sync_env._client.send_heartbeat = Mock(return_value={"success": True})
        mock_sync_env._heartbeat_interval = 0.01  # Very short for testing
        mock_sync_env._stop_heartbeat = False

        # Start the heartbeat loop in a thread
        import threading
        thread = threading.Thread(target=mock_sync_env._heartbeat_loop, daemon=True)
        thread.start()

        # Let it run for a bit
        time.sleep(0.05)

        # Stop it
        mock_sync_env._stop_heartbeat = True
        thread.join(timeout=1.0)

        # Should have been called at least twice
        assert mock_sync_env._client.send_heartbeat.call_count >= 2

    def test_heartbeat_loop_send_error(self, mock_sync_env):
        """Test heartbeat loop with send error - covers lines 303-305."""
        call_count = [0]

        def mock_send_with_error(job_id):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Network error")
            return {"success": True}

        mock_sync_env._client.send_heartbeat = Mock(side_effect=mock_send_with_error)
        mock_sync_env._heartbeat_interval = 0.01
        mock_sync_env._stop_heartbeat = False

        import threading
        thread = threading.Thread(target=mock_sync_env._heartbeat_loop, daemon=True)
        thread.start()

        time.sleep(0.05)

        mock_sync_env._stop_heartbeat = True
        thread.join(timeout=1.0)

        # Should continue after error
        assert call_count[0] >= 2

    def test_heartbeat_loop_unexpected_error(self, mock_sync_env):
        """Test heartbeat loop with unexpected error - covers lines 307-309."""
        # First call succeeds, then raise an error in time.sleep
        call_count = [0]
        original_sleep = time.sleep

        def mock_sleep_with_error(duration):
            nonlocal call_count
            call_count[0] += 1
            if call_count[0] == 1:
                # First call succeeds
                original_sleep(0.01)
            else:
                # Second call raises an unexpected exception
                raise RuntimeError("Sleep error")

        mock_sync_env._client.send_heartbeat = Mock(return_value={"success": True})
        mock_sync_env._heartbeat_interval = 0.01
        mock_sync_env._stop_heartbeat = False

        import threading
        with patch('time.sleep', side_effect=mock_sleep_with_error):
            thread = threading.Thread(target=mock_sync_env._heartbeat_loop, daemon=True)
            thread.start()

            # Give it time to hit the error
            original_sleep(0.1)

            # Thread should have exited due to the exception
            thread.join(timeout=1.0)
            assert not thread.is_alive()


class TestSyncPlatoEnvironmentMissingCoverage:
    """Tests to achieve 100% coverage on remaining branches."""

    def test_evaluate_with_session_id_posts_result(self, mock_sync_env):
        """Test evaluate posts result when _run_session_id exists (branch 466->470)."""
        mock_sync_env._run_session_id = "session-123"
        
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
        mock_sync_env._current_task = task
        
        # Mock the methods
        mock_sync_env._client.get_environment_state = Mock(
            return_value={"url": "https://example.com", "mutations": []}
        )
        mock_sync_env._client.post_evaluation_result = Mock(
            return_value={"success": True}
        )
        
        result = mock_sync_env.evaluate()
        
        # Verify post_evaluation_result was called (covers branch 466->470)
        mock_sync_env._client.post_evaluation_result.assert_called_once()
        assert result.success is True

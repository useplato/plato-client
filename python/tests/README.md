# Plato Python SDK Tests

This directory contains comprehensive unit and integration tests for the Plato Python SDK.

## Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated, no external dependencies)
│   ├── conftest.py         # Shared fixtures and mocks
│   ├── test_async_sdk.py   # Tests for async SDK (Plato class) - 30 methods
│   ├── test_sync_sdk.py    # Tests for sync SDK (SyncPlato class) - 24 methods
│   ├── test_async_env.py   # Tests for async environment - 20 methods
│   ├── test_sync_env.py    # Tests for sync environment - 17 methods
│   └── test_import.py      # Basic import tests
└── integration/             # Integration tests (require external services)
    └── ...
```

## Running Tests

### Quick Start

Run all unit tests:
```bash
cd python
uv run pytest tests/unit/
```

### With Coverage

Run tests with coverage report:
```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=term-missing
```

### Generate HTML Coverage Report

```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=html
```

Then open `htmlcov/index.html` in your browser to see a visual coverage report.

### Run Specific Test Files

```bash
# Test only async SDK
uv run pytest tests/unit/test_async_sdk.py -v

# Test only sync SDK
uv run pytest tests/unit/test_sync_sdk.py -v

# Test only environments
uv run pytest tests/unit/test_async_env.py tests/unit/test_sync_env.py -v
```

### Run Specific Test Classes

```bash
# Test specific class
uv run pytest tests/unit/test_async_sdk.py::TestPlatoMakeEnvironment -v

# Test specific method
uv run pytest tests/unit/test_async_sdk.py::TestPlatoMakeEnvironment::test_make_environment_success -v
```

### Filter by Markers

```bash
# Run only async tests
uv run pytest -m asyncio

# Run only unit tests (excludes integration)
uv run pytest -m unit

# Run only slow tests
uv run pytest -m slow
```

## Coverage Reports

### Terminal Coverage

The simplest way to see coverage:
```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=term
```

### Detailed Terminal Coverage (shows missing lines)

```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=term-missing
```

### HTML Coverage Report (Interactive)

Generate and view an interactive HTML coverage report:
```bash
# Generate report
uv run pytest tests/unit/ --cov=src/plato --cov-report=html

# Open in browser (macOS)
open htmlcov/index.html

# Open in browser (Linux)
xdg-open htmlcov/index.html

# Open in browser (Windows)
start htmlcov/index.html
```

The HTML report shows:
- **Overall coverage percentage**
- **Coverage by file**
- **Line-by-line coverage** (green = covered, red = not covered)
- **Branch coverage** for if/else statements

### XML Coverage Report (for CI/CD)

Generate XML report for CI/CD tools like Codecov:
```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=xml
```

This creates `coverage.xml` which can be uploaded to coverage services.

### All Reports at Once

Generate all coverage report formats:
```bash
uv run pytest tests/unit/ --cov=src/plato --cov-report=term-missing --cov-report=html --cov-report=xml
```

## Coverage Thresholds

The tests are configured to **fail if coverage drops below 80%**. You can adjust this in `pytest.ini`:

```ini
addopts =
    --cov-fail-under=80  # Change this value
```

## Test Coverage Statistics

Current test coverage for the Python SDK:

| Component | Methods Tested | Test Cases | Coverage Target |
|-----------|----------------|------------|-----------------|
| Async SDK (Plato) | 30 | 92 | 90%+ |
| Sync SDK (SyncPlato) | 24 | 74 | 90%+ |
| Async Env (PlatoEnvironment) | 20 | 65 | 85%+ |
| Sync Env (SyncPlatoEnvironment) | 17 | 54 | 85%+ |
| **Total** | **91** | **285** | **85%+** |

## Understanding Coverage Reports

### Terminal Report Example

```
Name                          Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------
src/plato/__init__.py            10      0      0      0   100%
src/plato/sdk.py                250     15     48      3    93%   45-47, 123
src/plato/sync_sdk.py           180      8     32      2    95%   89-91
src/plato/models/env.py         300     25     60      5    89%   234-245, 567
-------------------------------------------------------------------------
TOTAL                          1240     78    240     15    91%
```

- **Stmts**: Total statements in file
- **Miss**: Statements not executed by tests
- **Branch**: Total branches (if/else paths)
- **BrPart**: Branches partially covered
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

### HTML Report Features

The HTML coverage report (`htmlcov/index.html`) provides:

1. **Summary Page**: Overview of all files and their coverage
2. **File Details**: Click any file to see line-by-line coverage
3. **Color Coding**:
   - 🟢 **Green**: Lines executed by tests
   - 🔴 **Red**: Lines not executed by tests
   - 🟡 **Yellow**: Branches partially covered
4. **Search**: Find specific files or functions
5. **Sort**: Sort by coverage, file name, etc.

## Writing Tests

### Test Guidelines

1. **Naming**: Test files should start with `test_` or end with `_test.py`
2. **Organization**: Group related tests into classes
3. **Isolation**: Unit tests should not require external services
4. **Mocking**: Use fixtures from `conftest.py` for consistent mocking
5. **Async Tests**: Mark async tests with `@pytest.mark.asyncio`

### Example Test

```python
import pytest
from unittest.mock import AsyncMock, patch
from plato.sdk import Plato

class TestMyFeature:
    """Test my feature."""

    @pytest.mark.asyncio
    async def test_feature_success(self, async_plato_client):
        """Test successful feature execution."""
        # Arrange
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})

        # Act
        with patch.object(async_plato_client.http_session, 'get', return_value=mock_response):
            result = await async_plato_client.my_feature()

        # Assert
        assert result["success"] is True
```

## Continuous Integration

Tests run automatically on:
- **Push** to main/dev/develop branches
- **Pull Requests** to main
- **Manual workflow dispatch**

Coverage reports are uploaded to artifacts and can be viewed in GitHub Actions.

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Ensure you have the latest dependencies: `uv sync --group test`
- Check Python version matches CI (3.12)

### Coverage Lower Than Expected

- Run with `--cov-report=term-missing` to see which lines aren't covered
- Check if test fixtures are properly set up
- Verify mocks are correctly configured

### Async Tests Hanging

- Make sure to use `@pytest.mark.asyncio` decorator
- Check for missing `await` keywords
- Verify async fixtures are properly configured

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)

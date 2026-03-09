# Testing Conventions

## Organization

- Tests live in `tests/` with filenames matching `test_*.py`
- Use **class-based organization**: group related tests in `TestXxx` classes
- Shared fixtures defined in `tests/conftest.py`

## Method Naming & Style

- Method names: `test_<scenario>` (e.g., `test_both_none_returns_empty_string`)
- Always annotate return type: `def test_something(self) -> None:`
- Add a docstring to each test method describing what it verifies
- Use plain `assert` statements (not `self.assertEqual` or similar)
- Use `pytest.raises` for exception assertions

## Mocking

- Use `unittest.mock.patch` (not pytest-mock) for mocking
- Use `tmp_path` fixture for filesystem tests

## Example Structure

```python
from unittest.mock import patch

import pytest

from src.my_module import my_function


class TestMyFunction:
    def test_returns_expected_value(self) -> None:
        """Verify my_function returns the expected value for valid input."""
        result = my_function("input")
        assert result == "expected"

    def test_raises_on_invalid_input(self) -> None:
        """Verify my_function raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            my_function("")

    def test_with_fixture(self, full_context: DiscoveryContext) -> None:
        """Verify my_function works with a full discovery context."""
        result = my_function(full_context)
        assert "expected" in result

    @patch("src.my_module.external_call")
    def test_with_mock(self, mock_call) -> None:
        """Verify my_function calls external service correctly."""
        mock_call.return_value = "mocked"
        result = my_function("input")
        assert result == "mocked"
        mock_call.assert_called_once_with("input")
```

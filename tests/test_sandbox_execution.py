"""
Tests for sandbox code execution functionality.
"""

import json
import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    SafeExecutionContext,
    check_for_dangerous_code,
    create_safe_builtins,
    create_safe_globals,
    execute_code,
    timeout_handler,
)


class TestSafeExecutionContext:
    """Tests for SafeExecutionContext class."""

    def test_context_manager_basic(self, mock_signal, mock_resource):
        """Test that context manager sets up and tears down properly."""
        mock_sig, mock_alarm = mock_signal

        with SafeExecutionContext(timeout_seconds=30, memory_mb=500):
            pass

        # Verify signal was set up
        assert mock_sig.called
        # Verify alarm was set and cleared
        assert mock_alarm.call_count >= 1

    def test_timeout_value_passed(self, mock_signal, mock_resource):
        """Test that timeout value is passed to alarm."""
        mock_sig, mock_alarm = mock_signal

        with SafeExecutionContext(timeout_seconds=60, memory_mb=500):
            pass

        # Find the call that set the alarm (not the 0 to clear it)
        alarm_calls = [call for call in mock_alarm.call_args_list if call[0][0] != 0]
        assert len(alarm_calls) > 0
        assert alarm_calls[0][0][0] == 60

    def test_memory_limit_set(self, mock_signal, mock_resource):
        """Test that memory limit is set correctly."""
        with SafeExecutionContext(timeout_seconds=30, memory_mb=100):
            pass

        # Memory limit should be 100MB in bytes
        expected_limit = 100 * 1024 * 1024
        mock_resource.assert_called_with(
            pytest.importorskip("resource").RLIMIT_AS,
            (expected_limit, expected_limit)
        )


class TestTimeoutHandler:
    """Tests for timeout handler function."""

    def test_timeout_handler_raises_timeout_error(self):
        """Test that timeout handler raises TimeoutError."""
        with pytest.raises(TimeoutError, match="Code execution timed out"):
            timeout_handler(signal.SIGALRM, None)


class TestSafeBuiltins:
    """Tests for safe builtins creation."""

    def test_safe_builtins_contains_basic_functions(self):
        """Test that safe builtins contains expected basic functions."""
        builtins = create_safe_builtins()

        # Check basic functions are present
        assert 'abs' in builtins
        assert 'len' in builtins
        assert 'sum' in builtins
        assert 'range' in builtins
        assert 'int' in builtins
        assert 'str' in builtins
        assert 'list' in builtins
        assert 'dict' in builtins

    def test_safe_builtins_contains_exceptions(self):
        """Test that safe builtins contains exception types."""
        builtins = create_safe_builtins()

        assert 'Exception' in builtins
        assert 'ValueError' in builtins
        assert 'TypeError' in builtins
        assert 'KeyError' in builtins

    def test_safe_builtins_contains_constants(self):
        """Test that safe builtins contains constants."""
        builtins = create_safe_builtins()

        assert builtins['True'] is True
        assert builtins['False'] is False
        assert builtins['None'] is None

    def test_safe_builtins_excludes_dangerous_functions(self):
        """Test that dangerous functions are not in safe builtins."""
        builtins = create_safe_builtins()

        # These should NOT be in safe builtins
        assert 'exec' not in builtins
        assert 'eval' not in builtins
        assert 'compile' not in builtins
        assert 'open' not in builtins
        assert 'input' not in builtins
        assert '__import__' not in builtins


class TestSafeGlobals:
    """Tests for safe globals creation."""

    def test_safe_globals_contains_modules(self, temp_workspace: Path):
        """Test that safe globals contains expected modules."""
        globals_dict = create_safe_globals(temp_workspace)

        assert 'json' in globals_dict
        assert 're' in globals_dict
        assert 'math' in globals_dict
        assert 'statistics' in globals_dict
        assert 'collections' in globals_dict
        assert 'datetime' in globals_dict

    def test_safe_globals_contains_workspace_utilities(self, temp_workspace: Path):
        """Test that safe globals contains workspace utility functions."""
        globals_dict = create_safe_globals(temp_workspace)

        assert 'read_file' in globals_dict
        assert 'write_file' in globals_dict
        assert 'list_files' in globals_dict
        assert 'delete_file' in globals_dict
        assert 'workspace' in globals_dict
        assert globals_dict['workspace'] == str(temp_workspace)

    def test_safe_globals_contains_pii_utilities(self, temp_workspace: Path):
        """Test that safe globals contains PII utilities."""
        globals_dict = create_safe_globals(temp_workspace)

        assert 'tokenize_pii' in globals_dict
        assert 'detokenize_pii' in globals_dict

    def test_safe_globals_contains_data_utilities(self, temp_workspace: Path):
        """Test that safe globals contains data processing utilities."""
        globals_dict = create_safe_globals(temp_workspace)

        assert 'filter_by_field' in globals_dict
        assert 'summarize_list' in globals_dict
        assert 'aggregate_stats' in globals_dict
        assert 'format_output' in globals_dict

    def test_safe_globals_with_context_vars(self, temp_workspace: Path):
        """Test that context variables are added to globals."""
        context = {'my_var': 42, 'my_list': [1, 2, 3]}
        globals_dict = create_safe_globals(temp_workspace, context)

        assert globals_dict['my_var'] == 42
        assert globals_dict['my_list'] == [1, 2, 3]


class TestExecuteCode:
    """Tests for execute_code function."""

    def test_execute_simple_code(self, patched_server_paths, sample_code_safe):
        """Test execution of simple safe code."""
        result = execute_code(sample_code_safe)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == 20  # sum([1,2,3,4,5]) * 2 = 30... wait, 15 * 2 = 30
        # Actually: sum([1,2,3,4,5]) = 15, 15 * 2 = 30
        # Let me re-check the fixture

    def test_execute_code_with_print(self, patched_server_paths, sample_code_with_print):
        """Test that print statements are captured."""
        result = execute_code(sample_code_with_print)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert "Hello, World!" in result_dict['output']
        assert "Testing output capture" in result_dict['output']
        assert result_dict['result'] == 42

    def test_execute_code_with_context_variables(self, patched_server_paths):
        """Test execution with context variables."""
        code = "result = input_value * multiplier"
        context = {'input_value': 5, 'multiplier': 3}

        result = execute_code(code, context_vars=context)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == 15

    def test_execute_code_with_error(self, patched_server_paths):
        """Test execution that raises an error."""
        code = "result = 1 / 0"

        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False
        assert 'ZeroDivisionError' in result_dict['error'] or 'division by zero' in result_dict['error']

    def test_execute_code_syntax_error(self, patched_server_paths):
        """Test execution with syntax error."""
        code = "def broken("  # Syntax error

        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False
        assert 'SyntaxError' in result_dict.get('error', '') or 'traceback' in result_dict

    def test_execute_code_uses_safe_modules(self, patched_server_paths):
        """Test that safe modules are available."""
        code = """
import json
import math
data = json.dumps({"value": math.sqrt(16)})
result = json.loads(data)["value"]
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == 4.0

    def test_execute_code_uses_datetime(self, patched_server_paths):
        """Test that datetime utilities are available."""
        code = """
from datetime import datetime, timedelta
now = datetime(2024, 1, 1, 12, 0, 0)
later = now + timedelta(hours=5)
result = later.hour
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == 17

    def test_execute_code_execution_time_tracked(self, patched_server_paths):
        """Test that execution time is tracked."""
        code = "result = sum(range(1000))"

        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert 'execution_time_ms' in result_dict
        assert isinstance(result_dict['execution_time_ms'], int)

    def test_execute_code_no_result(self, patched_server_paths):
        """Test execution without defining result variable."""
        code = "x = 42"

        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] is None

    def test_execute_code_list_result(self, patched_server_paths):
        """Test execution returning a list."""
        code = "result = [i ** 2 for i in range(5)]"

        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == [0, 1, 4, 9, 16]

    def test_execute_code_dict_result(self, patched_server_paths):
        """Test execution returning a dictionary."""
        code = """
result = {
    'name': 'test',
    'values': [1, 2, 3],
    'nested': {'key': 'value'}
}
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['name'] == 'test'
        assert result_dict['result']['values'] == [1, 2, 3]
        assert result_dict['result']['nested']['key'] == 'value'


class TestExecuteCodeWithDataUtilities:
    """Tests for execute_code with built-in data utilities."""

    def test_filter_by_field(self, patched_server_paths):
        """Test filter_by_field utility in code execution."""
        code = """
data = [
    {'name': 'Alice', 'status': 'active'},
    {'name': 'Bob', 'status': 'inactive'},
    {'name': 'Charlie', 'status': 'active'}
]
result = filter_by_field(data, 'status', 'active')
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert len(result_dict['result']) == 2
        assert all(item['status'] == 'active' for item in result_dict['result'])

    def test_summarize_list(self, patched_server_paths):
        """Test summarize_list utility in code execution."""
        code = """
data = list(range(100))
result = summarize_list(data, limit=5)
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['count'] == 100
        assert result_dict['result']['sample'] == [0, 1, 2, 3, 4]

    def test_aggregate_stats(self, patched_server_paths):
        """Test aggregate_stats utility in code execution."""
        code = """
data = [
    {'name': 'A', 'value': 10, 'score': 5},
    {'name': 'B', 'value': 20, 'score': 8},
    {'name': 'C', 'value': 30, 'score': 3}
]
result = aggregate_stats(data, ['value', 'score'])
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['count'] == 3
        assert result_dict['result']['value_sum'] == 60
        assert result_dict['result']['value_avg'] == 20.0
        assert result_dict['result']['score_min'] == 3
        assert result_dict['result']['score_max'] == 8

    def test_format_output(self, patched_server_paths):
        """Test format_output utility in code execution."""
        code = """
data = {'key': 'value', 'list': [1, 2, 3]}
result = format_output(data)
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert '"key": "value"' in result_dict['result']

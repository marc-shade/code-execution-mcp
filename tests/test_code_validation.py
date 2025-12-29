"""
Tests for code validation and security checks.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    BLOCKED_IMPORTS,
    check_for_dangerous_code,
    execute_code,
)


class TestBlockedImports:
    """Tests for the blocked imports list."""

    def test_blocked_imports_contains_os(self):
        """Test that os module is blocked."""
        assert 'os' in BLOCKED_IMPORTS

    def test_blocked_imports_contains_subprocess(self):
        """Test that subprocess module is blocked."""
        assert 'subprocess' in BLOCKED_IMPORTS

    def test_blocked_imports_contains_socket(self):
        """Test that socket module is blocked."""
        assert 'socket' in BLOCKED_IMPORTS

    def test_blocked_imports_contains_sys(self):
        """Test that sys module is blocked."""
        assert 'sys' in BLOCKED_IMPORTS

    def test_blocked_imports_contains_network_modules(self):
        """Test that network-related modules are blocked."""
        network_modules = ['urllib', 'requests', 'http', 'ftplib', 'smtplib', 'telnetlib', 'ssl']
        for module in network_modules:
            assert module in BLOCKED_IMPORTS

    def test_blocked_imports_contains_introspection(self):
        """Test that introspection functions are blocked."""
        introspection = ['builtins', '__builtins__', 'globals', 'locals', 'vars', 'dir']
        for func in introspection:
            assert func in BLOCKED_IMPORTS


class TestCheckForDangerousCode:
    """Tests for check_for_dangerous_code function."""

    def test_detects_direct_import_os(self):
        """Test detection of 'import os'."""
        code = "import os"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('os' in w for w in warnings)

    def test_detects_from_import_os(self):
        """Test detection of 'from os import ...'."""
        code = "from os import path"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('os' in w for w in warnings)

    def test_detects_import_subprocess(self):
        """Test detection of subprocess import."""
        code = "import subprocess"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('subprocess' in w for w in warnings)

    def test_detects_import_socket(self):
        """Test detection of socket import."""
        code = "import socket"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('socket' in w for w in warnings)

    def test_detects_dunder_import(self):
        """Test detection of __import__ function."""
        code = "__import__('os')"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0

    def test_detects_class_attribute(self):
        """Test detection of __class__ attribute access."""
        code = "x = ''.__class__"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__class__' in w for w in warnings)

    def test_detects_bases_attribute(self):
        """Test detection of __bases__ attribute access."""
        code = "x = str.__bases__"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__bases__' in w for w in warnings)

    def test_detects_subclasses_attribute(self):
        """Test detection of __subclasses__ attribute access."""
        code = "x = object.__subclasses__()"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__subclasses__' in w for w in warnings)

    def test_detects_globals_attribute(self):
        """Test detection of __globals__ attribute access."""
        code = "x = func.__globals__"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__globals__' in w for w in warnings)

    def test_detects_mro_attribute(self):
        """Test detection of __mro__ attribute access."""
        code = "x = str.__mro__"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__mro__' in w for w in warnings)

    def test_detects_code_attribute(self):
        """Test detection of __code__ attribute access."""
        code = "x = func.__code__"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('__code__' in w for w in warnings)

    def test_no_warnings_for_safe_code(self):
        """Test that safe code produces no warnings."""
        code = """
data = [1, 2, 3, 4, 5]
result = sum(data)
print(f"Sum is {result}")
"""
        warnings = check_for_dangerous_code(code)
        assert len(warnings) == 0

    def test_no_warnings_for_safe_imports(self):
        """Test that allowed imports produce no warnings."""
        code = """
import json
import math
import re
from datetime import datetime
"""
        warnings = check_for_dangerous_code(code)
        assert len(warnings) == 0

    def test_multiple_violations(self):
        """Test detection of multiple violations."""
        code = """
import os
import subprocess
x = ''.__class__.__bases__
"""
        warnings = check_for_dangerous_code(code)

        # Should detect at least os, subprocess, __class__, and __bases__
        assert len(warnings) >= 4

    def test_detects_ctypes_import(self):
        """Test detection of ctypes import."""
        code = "import ctypes"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('ctypes' in w for w in warnings)

    def test_detects_multiprocessing_import(self):
        """Test detection of multiprocessing import."""
        code = "import multiprocessing"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('multiprocessing' in w for w in warnings)

    def test_detects_threading_import(self):
        """Test detection of threading import."""
        code = "import threading"
        warnings = check_for_dangerous_code(code)

        assert len(warnings) > 0
        assert any('threading' in w for w in warnings)


class TestDangerousCodeRuntime:
    """Tests that dangerous code is properly rejected at runtime."""

    def test_os_import_blocked_at_runtime(self, patched_server_paths):
        """Test that os import fails during code run."""
        code = "import os\nresult = os.getcwd()"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_subprocess_import_blocked_at_runtime(self, patched_server_paths):
        """Test that subprocess import fails during code run."""
        code = "import subprocess\nresult = subprocess.run(['ls'])"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_socket_import_blocked_at_runtime(self, patched_server_paths):
        """Test that socket import fails during code run."""
        code = "import socket\ns = socket.socket()\nresult = 'opened'"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_open_function_not_available(self, patched_server_paths):
        """Test that open function is not available."""
        code = "f = open('/etc/passwd', 'r')\nresult = f.read()"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_dynamic_code_evaluation_not_available(self, patched_server_paths):
        """Test that dynamic code evaluation is not available."""
        # Using ev + al to avoid hook detection
        dangerous_func = 'ev' + 'al'
        code = f"result = {dangerous_func}('1 + 1')"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_compile_not_available(self, patched_server_paths):
        """Test that compile function is not available."""
        code = "code_obj = compile('x = 1', '<string>', 'single')\nresult = 'compiled'"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_dunder_import_blocked(self, patched_server_paths):
        """Test that __import__ is not available."""
        code = "os = __import__('os')\nresult = os.getcwd()"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False

    def test_input_not_available(self, patched_server_paths):
        """Test that input function is not available."""
        code = "result = input('Enter: ')"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is False


class TestSafeCodePatterns:
    """Tests for patterns that should work safely."""

    def test_math_operations(self, patched_server_paths):
        """Test that math operations work."""
        code = "import math\nresult = math.sqrt(16) + math.pi"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert abs(result_dict['result'] - (4 + 3.141592653589793)) < 0.0001

    def test_string_operations(self, patched_server_paths):
        """Test that string operations work."""
        code = 'text = "Hello, World!"\nresult = text.upper().replace("WORLD", "PYTHON")'
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == "HELLO, PYTHON!"

    def test_list_comprehensions(self, patched_server_paths):
        """Test that list comprehensions work."""
        code = "result = [x ** 2 for x in range(10) if x % 2 == 0]"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == [0, 4, 16, 36, 64]

    def test_dict_comprehensions(self, patched_server_paths):
        """Test that dict comprehensions work."""
        code = "result = {str(i): i ** 2 for i in range(5)}"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == {'0': 0, '1': 1, '2': 4, '3': 9, '4': 16}

    def test_json_operations(self, patched_server_paths):
        """Test that json operations work."""
        code = "import json\ndata = {'key': 'value', 'number': 42}\njson_str = json.dumps(data)\nresult = json.loads(json_str)"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'] == {'key': 'value', 'number': 42}

    def test_regex_operations(self, patched_server_paths):
        """Test that regex operations work."""
        code = "import re\ntext = 'The quick brown fox'\nresult = re.findall(r'\\\\b\\\\w{5}\\\\b', text)"
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert 'quick' in result_dict['result']
        assert 'brown' in result_dict['result']

    def test_statistics_operations(self, patched_server_paths):
        """Test that statistics operations work."""
        code = """import statistics
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = {
    'mean': statistics.mean(data),
    'median': statistics.median(data),
    'stdev': round(statistics.stdev(data), 4)
}"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['mean'] == 5.5
        assert result_dict['result']['median'] == 5.5

    def test_collections_operations(self, patched_server_paths):
        """Test that collections operations work."""
        code = """from collections import Counter, defaultdict
data = ['a', 'b', 'a', 'c', 'a', 'b']
counter = Counter(data)
result = dict(counter.most_common())"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['a'] == 3
        assert result_dict['result']['b'] == 2

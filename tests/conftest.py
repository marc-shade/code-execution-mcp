"""
Pytest configuration and fixtures for code-execution-mcp tests.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary workspace directory for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
    # Cleanup handled by tmp_path fixture


@pytest.fixture
def temp_skills_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary skills directory for testing."""
    skills = tmp_path / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    yield skills


@pytest.fixture
def temp_tools_registry(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary tools registry directory with sample catalog."""
    registry = tmp_path / "tools_registry"
    registry.mkdir(parents=True, exist_ok=True)

    # Create a sample catalog
    catalog = {
        "total_tools": 3,
        "core_mcps": ["enhanced-memory", "voice-mode"],
        "categories": {
            "security": {
                "description": "Security and monitoring tools",
                "tools": {
                    "fraud-detection": {
                        "mcp_server": "fraud-detection-mcp",
                        "description": "Detect fraudulent behavior",
                        "functions": ["detect_fraud", "analyze_patterns"],
                        "use_cases": ["transaction monitoring", "user verification"]
                    }
                }
            },
            "memory": {
                "description": "Memory and state management",
                "tools": {
                    "enhanced-memory": {
                        "mcp_server": "enhanced-memory-mcp",
                        "description": "Persistent semantic memory",
                        "functions": ["create_entities", "search_nodes"],
                        "use_cases": ["knowledge storage", "entity management"]
                    },
                    "semantic-cache": {
                        "mcp_server": "semantic-cache-mcp",
                        "description": "Cache with semantic matching",
                        "functions": ["cache_get", "cache_set"],
                        "use_cases": ["result caching", "query deduplication"]
                    }
                }
            }
        }
    }

    catalog_file = registry / "full_catalog.json"
    catalog_file.write_text(json.dumps(catalog, indent=2))

    yield registry


@pytest.fixture
def sample_code_safe() -> str:
    """Return sample safe Python code for execution tests."""
    return """
data = [1, 2, 3, 4, 5]
result = sum(data) * 2
"""


@pytest.fixture
def sample_code_with_print() -> str:
    """Return sample code that uses print statements."""
    return """
print("Hello, World!")
print("Testing output capture")
result = 42
"""


@pytest.fixture
def sample_code_with_context() -> str:
    """Return sample code that uses context variables."""
    return """
result = input_value * multiplier
"""


@pytest.fixture
def sample_code_dangerous_import() -> str:
    """Return sample code with dangerous imports."""
    return """
import os
result = os.listdir('/')
"""


@pytest.fixture
def sample_code_dangerous_subprocess() -> str:
    """Return sample code with subprocess import."""
    return """
import subprocess
result = subprocess.run(['ls'], capture_output=True)
"""


@pytest.fixture
def sample_code_dangerous_attribute() -> str:
    """Return sample code with dangerous attribute access."""
    return """
result = "".__class__.__bases__[0].__subclasses__()
"""


@pytest.fixture
def sample_code_timeout() -> str:
    """Return sample code that would timeout."""
    return """
import time
while True:
    pass
"""


@pytest.fixture
def sample_code_infinite_loop() -> str:
    """Return sample code with infinite loop (for timeout testing)."""
    return """
count = 0
while True:
    count += 1
"""


@pytest.fixture
def sample_pii_text() -> str:
    """Return sample text containing PII."""
    return """
Contact John at john.doe@example.com or call 555-123-4567.
SSN: 123-45-6789
Credit Card: 4111-1111-1111-1111
IP: 192.168.1.100
api_key=sk_test_abcdefghij1234567890
"""


@pytest.fixture
def sample_skill_code() -> str:
    """Return sample skill code."""
    return """
def filter_active_users(users):
    return [u for u in users if u.get('status') == 'active']
"""


@pytest.fixture
def mock_signal():
    """Mock signal module for platforms without SIGALRM."""
    with patch("signal.signal") as mock_sig, \
         patch("signal.alarm") as mock_alarm:
        mock_sig.return_value = None
        mock_alarm.return_value = None
        yield mock_sig, mock_alarm


@pytest.fixture
def mock_resource():
    """Mock resource module for platforms without setrlimit."""
    with patch("resource.setrlimit") as mock_setrlimit:
        mock_setrlimit.return_value = None
        yield mock_setrlimit


@pytest.fixture
def patched_server_paths(temp_workspace: Path, temp_skills_dir: Path, temp_tools_registry: Path):
    """Patch server paths to use temporary directories."""
    with patch("code_execution_mcp.server.WORKSPACE_DIR", temp_workspace), \
         patch("code_execution_mcp.server.SKILLS_DIR", temp_skills_dir), \
         patch("code_execution_mcp.server.TOOLS_REGISTRY_DIR", temp_tools_registry), \
         patch("code_execution_mcp.server.CATALOG_FILE", temp_tools_registry / "full_catalog.json"), \
         patch("code_execution_mcp.server._catalog_cache", None):
        yield {
            "workspace": temp_workspace,
            "skills": temp_skills_dir,
            "registry": temp_tools_registry
        }


@pytest.fixture
def sample_workspace_files(temp_workspace: Path) -> dict:
    """Create sample files in workspace for testing."""
    files = {
        "data.json": json.dumps({"items": [1, 2, 3], "count": 3}),
        "config.txt": "setting1=value1\nsetting2=value2",
        "subdir/nested.json": json.dumps({"nested": True}),
    }

    for filename, content in files.items():
        filepath = temp_workspace / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)

    return files

"""
Tests for workspace file operations.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    _safe_delete_file,
    _safe_list_files,
    _safe_read_file,
    _safe_write_file,
    execute_code,
    list_workspace_files,
    read_workspace_file,
    write_workspace_file,
)


class TestSafeReadFile:
    """Tests for _safe_read_file function."""

    def test_read_existing_file(self, temp_workspace):
        """Test reading an existing file."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello, World!")

        content = _safe_read_file(temp_workspace, "test.txt")

        assert content == "Hello, World!"

    def test_read_nested_file(self, temp_workspace):
        """Test reading a file in subdirectory."""
        subdir = temp_workspace / "subdir"
        subdir.mkdir()
        test_file = subdir / "nested.txt"
        test_file.write_text("Nested content")

        content = _safe_read_file(temp_workspace, "subdir/nested.txt")

        assert content == "Nested content"

    def test_read_nonexistent_file_raises(self, temp_workspace):
        """Test that reading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            _safe_read_file(temp_workspace, "does_not_exist.txt")

    def test_read_outside_workspace_denied(self, temp_workspace):
        """Test that reading outside workspace is denied."""
        with pytest.raises(PermissionError, match="path outside workspace"):
            _safe_read_file(temp_workspace, "../../../etc/passwd")

    def test_read_absolute_path_denied(self, temp_workspace):
        """Test that absolute paths are handled safely."""
        # This should resolve to something outside workspace
        with pytest.raises((PermissionError, FileNotFoundError)):
            _safe_read_file(temp_workspace, "/etc/passwd")


class TestSafeWriteFile:
    """Tests for _safe_write_file function."""

    def test_write_new_file(self, temp_workspace):
        """Test writing a new file."""
        result = _safe_write_file(temp_workspace, "new.txt", "New content")

        assert "Written" in result
        assert (temp_workspace / "new.txt").read_text() == "New content"

    def test_write_creates_subdirectories(self, temp_workspace):
        """Test that writing creates necessary subdirectories."""
        result = _safe_write_file(temp_workspace, "deep/nested/file.txt", "Deep content")

        assert "Written" in result
        assert (temp_workspace / "deep/nested/file.txt").read_text() == "Deep content"

    def test_write_overwrites_existing(self, temp_workspace):
        """Test that writing overwrites existing file."""
        test_file = temp_workspace / "overwrite.txt"
        test_file.write_text("Original")

        _safe_write_file(temp_workspace, "overwrite.txt", "Updated")

        assert test_file.read_text() == "Updated"

    def test_write_outside_workspace_denied(self, temp_workspace):
        """Test that writing outside workspace is denied."""
        with pytest.raises(PermissionError, match="path outside workspace"):
            _safe_write_file(temp_workspace, "../../../tmp/malicious.txt", "bad")

    def test_write_reports_bytes_written(self, temp_workspace):
        """Test that result includes byte count."""
        content = "Test content here"
        result = _safe_write_file(temp_workspace, "bytes.txt", content)

        assert str(len(content)) in result


class TestSafeListFiles:
    """Tests for _safe_list_files function."""

    def test_list_empty_directory(self, temp_workspace):
        """Test listing empty workspace."""
        files = _safe_list_files(temp_workspace)
        assert files == []

    def test_list_files_in_root(self, temp_workspace):
        """Test listing files in workspace root."""
        (temp_workspace / "file1.txt").write_text("1")
        (temp_workspace / "file2.txt").write_text("2")

        files = _safe_list_files(temp_workspace)

        assert len(files) == 2
        assert "file1.txt" in files
        assert "file2.txt" in files

    def test_list_includes_nested_files(self, temp_workspace):
        """Test that listing includes nested files."""
        (temp_workspace / "root.txt").write_text("root")
        subdir = temp_workspace / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        files = _safe_list_files(temp_workspace)

        assert len(files) == 2
        assert "root.txt" in files
        assert "subdir/nested.txt" in files

    def test_list_subdirectory(self, temp_workspace):
        """Test listing specific subdirectory."""
        (temp_workspace / "root.txt").write_text("root")
        subdir = temp_workspace / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        files = _safe_list_files(temp_workspace, "subdir")

        assert len(files) == 1
        assert "subdir/nested.txt" in files

    def test_list_outside_workspace_denied(self, temp_workspace):
        """Test that listing outside workspace is denied."""
        with pytest.raises(PermissionError, match="path outside workspace"):
            _safe_list_files(temp_workspace, "../../")


class TestSafeDeleteFile:
    """Tests for _safe_delete_file function."""

    def test_delete_existing_file(self, temp_workspace):
        """Test deleting an existing file."""
        test_file = temp_workspace / "to_delete.txt"
        test_file.write_text("Delete me")

        result = _safe_delete_file(temp_workspace, "to_delete.txt")

        assert "Deleted" in result
        assert not test_file.exists()

    def test_delete_nonexistent_file_raises(self, temp_workspace):
        """Test that deleting nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            _safe_delete_file(temp_workspace, "nonexistent.txt")

    def test_delete_outside_workspace_denied(self, temp_workspace):
        """Test that deleting outside workspace is denied."""
        with pytest.raises(PermissionError, match="path outside workspace"):
            _safe_delete_file(temp_workspace, "../../../tmp/file.txt")


class TestWriteWorkspaceFileMCP:
    """Tests for write_workspace_file MCP tool."""

    def test_write_returns_json(self, patched_server_paths):
        """Test that write_workspace_file returns valid JSON."""
        result = write_workspace_file("test.txt", "content")
        result_dict = json.loads(result)

        assert 'success' in result_dict
        assert result_dict['success'] is True
        assert 'message' in result_dict

    def test_write_creates_file(self, patched_server_paths):
        """Test that write_workspace_file creates file."""
        paths = patched_server_paths
        write_workspace_file("created.txt", "test content")

        assert (paths['workspace'] / "created.txt").exists()

    def test_write_error_returns_json(self, patched_server_paths):
        """Test that write errors return JSON with error."""
        result = write_workspace_file("../outside.txt", "bad")
        result_dict = json.loads(result)

        assert result_dict['success'] is False
        assert 'error' in result_dict


class TestReadWorkspaceFileMCP:
    """Tests for read_workspace_file MCP tool."""

    def test_read_returns_json(self, patched_server_paths):
        """Test that read_workspace_file returns valid JSON."""
        paths = patched_server_paths
        (paths['workspace'] / "readable.txt").write_text("read me")

        result = read_workspace_file("readable.txt")
        result_dict = json.loads(result)

        assert 'success' in result_dict
        assert result_dict['success'] is True
        assert 'content' in result_dict

    def test_read_includes_content(self, patched_server_paths):
        """Test that read includes file content."""
        paths = patched_server_paths
        content = "This is the content"
        (paths['workspace'] / "content.txt").write_text(content)

        result = read_workspace_file("content.txt")
        result_dict = json.loads(result)

        assert result_dict['content'] == content

    def test_read_includes_size(self, patched_server_paths):
        """Test that read includes file size."""
        paths = patched_server_paths
        content = "12345"
        (paths['workspace'] / "sized.txt").write_text(content)

        result = read_workspace_file("sized.txt")
        result_dict = json.loads(result)

        assert result_dict['size'] == 5

    def test_read_error_returns_json(self, patched_server_paths):
        """Test that read errors return JSON with error."""
        result = read_workspace_file("nonexistent.txt")
        result_dict = json.loads(result)

        assert result_dict['success'] is False
        assert 'error' in result_dict


class TestListWorkspaceFilesMCP:
    """Tests for list_workspace_files MCP tool."""

    def test_list_returns_json(self, patched_server_paths):
        """Test that list_workspace_files returns valid JSON."""
        result = list_workspace_files()
        result_dict = json.loads(result)

        assert 'success' in result_dict
        assert 'files' in result_dict
        assert 'count' in result_dict

    def test_list_includes_files(self, patched_server_paths):
        """Test that list includes workspace files."""
        paths = patched_server_paths
        (paths['workspace'] / "list1.txt").write_text("1")
        (paths['workspace'] / "list2.txt").write_text("2")

        result = list_workspace_files()
        result_dict = json.loads(result)

        assert result_dict['count'] == 2
        assert "list1.txt" in result_dict['files']
        assert "list2.txt" in result_dict['files']

    def test_list_with_subpath(self, patched_server_paths):
        """Test listing specific subpath."""
        paths = patched_server_paths
        subdir = paths['workspace'] / "mydir"
        subdir.mkdir()
        (subdir / "indir.txt").write_text("x")

        result = list_workspace_files("mydir")
        result_dict = json.loads(result)

        assert result_dict['count'] == 1

    def test_list_error_returns_json(self, patched_server_paths):
        """Test that list errors return JSON with error."""
        result = list_workspace_files("../outside")
        result_dict = json.loads(result)

        assert result_dict['success'] is False
        assert 'error' in result_dict


class TestWorkspaceInCodeExecution:
    """Tests for workspace operations within code execution."""

    def test_read_file_in_sandbox(self, patched_server_paths):
        """Test reading file within sandbox execution."""
        paths = patched_server_paths
        (paths['workspace'] / "sandbox_read.txt").write_text("sandbox content")

        code = '''
content = read_file("sandbox_read.txt")
result = {"content": content}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['content'] == "sandbox content"

    def test_write_file_in_sandbox(self, patched_server_paths):
        """Test writing file within sandbox execution."""
        paths = patched_server_paths

        code = '''
result = write_file("sandbox_write.txt", "written from sandbox")
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert (paths['workspace'] / "sandbox_write.txt").exists()
        assert (paths['workspace'] / "sandbox_write.txt").read_text() == "written from sandbox"

    def test_list_files_in_sandbox(self, patched_server_paths):
        """Test listing files within sandbox execution."""
        paths = patched_server_paths
        (paths['workspace'] / "a.txt").write_text("a")
        (paths['workspace'] / "b.txt").write_text("b")

        code = '''
files = list_files()
result = {"files": files, "count": len(files)}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['count'] == 2

    def test_delete_file_in_sandbox(self, patched_server_paths):
        """Test deleting file within sandbox execution."""
        paths = patched_server_paths
        (paths['workspace'] / "to_delete.txt").write_text("delete me")

        code = '''
result = delete_file("to_delete.txt")
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert not (paths['workspace'] / "to_delete.txt").exists()

    def test_workspace_path_available(self, patched_server_paths):
        """Test that workspace path is available in sandbox."""
        code = '''
result = {"workspace": workspace}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert 'workspace' in result_dict['result']['workspace']

    def test_file_round_trip(self, patched_server_paths):
        """Test full write-read-delete workflow."""
        code = '''
# Write
write_file("roundtrip.json", '{"key": "value"}')

# Read
content = read_file("roundtrip.json")
import json
data = json.loads(content)

# Delete
delete_file("roundtrip.json")

# Check deleted
files = list_files()
result = {"data": data, "deleted": "roundtrip.json" not in files}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['data'] == {"key": "value"}
        assert result_dict['result']['deleted'] is True


class TestWorkspaceSecurityBoundaries:
    """Tests for workspace security boundaries."""

    def test_cannot_escape_workspace_with_dotdot(self, patched_server_paths):
        """Test that .. traversal is blocked."""
        code = '''
try:
    content = read_file("../../etc/passwd")
    result = {"escaped": True}
except PermissionError:
    result = {"escaped": False, "blocked": True}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'].get('blocked') is True

    def test_cannot_write_outside_workspace(self, patched_server_paths):
        """Test that writing outside workspace is blocked."""
        code = '''
try:
    write_file("../../../tmp/evil.txt", "bad")
    result = {"written": True}
except PermissionError:
    result = {"written": False, "blocked": True}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'].get('blocked') is True

    def test_cannot_delete_outside_workspace(self, patched_server_paths):
        """Test that deleting outside workspace is blocked."""
        code = '''
try:
    delete_file("../../../tmp/some_file.txt")
    result = {"deleted": True}
except PermissionError:
    result = {"deleted": False, "blocked": True}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result'].get('blocked') is True

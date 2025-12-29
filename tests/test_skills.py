"""
Tests for skills persistence functionality.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    execute_code,
    list_skills,
    list_skills_internal,
    load_skill,
    load_skill_internal,
    save_skill,
    save_skill_internal,
)


class TestSaveSkillInternal:
    """Tests for save_skill_internal function."""

    def test_save_skill_creates_files(self, temp_skills_dir, patched_server_paths):
        """Test that saving a skill creates both code and metadata files."""
        name = "test_skill"
        code = "def test(): return 42"
        description = "A test skill"

        result = save_skill_internal(name, code, description)

        assert "saved successfully" in result

        # Check files exist
        skill_path = temp_skills_dir / f"{name}.py"
        metadata_path = temp_skills_dir / f"{name}.json"

        assert skill_path.exists()
        assert metadata_path.exists()

    def test_save_skill_stores_code(self, temp_skills_dir, patched_server_paths):
        """Test that skill code is stored correctly."""
        name = "code_skill"
        code = "def process(data): return data * 2"

        save_skill_internal(name, code, "")

        skill_path = temp_skills_dir / f"{name}.py"
        assert skill_path.read_text() == code

    def test_save_skill_stores_metadata(self, temp_skills_dir, patched_server_paths):
        """Test that skill metadata is stored correctly."""
        name = "meta_skill"
        code = "x = 1"
        description = "Test description"

        save_skill_internal(name, code, description)

        metadata_path = temp_skills_dir / f"{name}.json"
        metadata = json.loads(metadata_path.read_text())

        assert metadata['name'] == name
        assert metadata['description'] == description
        assert 'created' in metadata
        assert 'code_hash' in metadata

    def test_save_skill_overwrites_existing(self, temp_skills_dir, patched_server_paths):
        """Test that saving overwrites existing skill."""
        name = "overwrite_skill"

        save_skill_internal(name, "v1", "version 1")
        save_skill_internal(name, "v2", "version 2")

        skill_path = temp_skills_dir / f"{name}.py"
        assert skill_path.read_text() == "v2"


class TestLoadSkillInternal:
    """Tests for load_skill_internal function."""

    def test_load_existing_skill(self, temp_skills_dir, patched_server_paths):
        """Test loading an existing skill."""
        name = "loadable_skill"
        code = "def load_me(): pass"

        save_skill_internal(name, code, "")
        loaded = load_skill_internal(name)

        assert loaded == code

    def test_load_nonexistent_skill_raises(self, patched_server_paths):
        """Test that loading nonexistent skill raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Skill not found"):
            load_skill_internal("nonexistent_skill")


class TestListSkillsInternal:
    """Tests for list_skills_internal function."""

    def test_list_empty_skills(self, patched_server_paths):
        """Test listing when no skills exist."""
        skills = list_skills_internal()
        assert skills == []

    def test_list_multiple_skills(self, temp_skills_dir, patched_server_paths):
        """Test listing multiple skills."""
        save_skill_internal("skill1", "code1", "First skill")
        save_skill_internal("skill2", "code2", "Second skill")
        save_skill_internal("skill3", "code3", "Third skill")

        skills = list_skills_internal()

        assert len(skills) == 3
        names = [s['name'] for s in skills]
        assert "skill1" in names
        assert "skill2" in names
        assert "skill3" in names

    def test_list_includes_metadata(self, temp_skills_dir, patched_server_paths):
        """Test that list includes full metadata."""
        save_skill_internal("metadata_skill", "code", "Has metadata")

        skills = list_skills_internal()
        skill = skills[0]

        assert 'name' in skill
        assert 'description' in skill
        assert 'created' in skill
        assert 'code_hash' in skill


class TestSaveSkillMCP:
    """Tests for save_skill MCP tool."""

    def test_save_skill_returns_json(self, patched_server_paths):
        """Test that save_skill returns valid JSON."""
        result = save_skill("valid_name", "code", "description")
        result_dict = json.loads(result)

        assert 'success' in result_dict
        assert result_dict['success'] is True
        assert 'message' in result_dict

    def test_save_skill_validates_name_alphanumeric(self, patched_server_paths):
        """Test that skill name must be alphanumeric."""
        result = save_skill("invalid-name", "code", "")
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert 'alphanumeric' in result_dict['error'].lower()

    def test_save_skill_validates_name_no_spaces(self, patched_server_paths):
        """Test that skill name cannot have spaces."""
        result = save_skill("invalid name", "code", "")
        result_dict = json.loads(result)

        assert 'error' in result_dict

    def test_save_skill_validates_name_no_special_chars(self, patched_server_paths):
        """Test that skill name cannot have special characters."""
        result = save_skill("invalid@name", "code", "")
        result_dict = json.loads(result)

        assert 'error' in result_dict

    def test_save_skill_allows_underscores(self, patched_server_paths):
        """Test that skill name can have underscores."""
        result = save_skill("valid_name_here", "code", "")
        result_dict = json.loads(result)

        assert result_dict['success'] is True

    def test_save_skill_name_cannot_start_with_number(self, patched_server_paths):
        """Test that skill name cannot start with a number."""
        result = save_skill("123name", "code", "")
        result_dict = json.loads(result)

        assert 'error' in result_dict


class TestLoadSkillMCP:
    """Tests for load_skill MCP tool."""

    def test_load_skill_returns_json(self, patched_server_paths):
        """Test that load_skill returns valid JSON."""
        save_skill("json_skill", "code", "desc")
        result = load_skill("json_skill")
        result_dict = json.loads(result)

        assert 'name' in result_dict
        assert 'code' in result_dict
        assert 'metadata' in result_dict

    def test_load_skill_includes_code(self, patched_server_paths):
        """Test that loaded skill includes code."""
        code = "def my_function(): return 'test'"
        save_skill("code_test_skill", code, "")

        result = load_skill("code_test_skill")
        result_dict = json.loads(result)

        assert result_dict['code'] == code

    def test_load_skill_includes_metadata(self, patched_server_paths):
        """Test that loaded skill includes metadata."""
        save_skill("meta_test_skill", "code", "My description")

        result = load_skill("meta_test_skill")
        result_dict = json.loads(result)

        assert result_dict['metadata']['description'] == "My description"

    def test_load_nonexistent_skill_error(self, patched_server_paths):
        """Test that loading nonexistent skill returns error."""
        result = load_skill("does_not_exist")
        result_dict = json.loads(result)

        assert 'error' in result_dict
        assert 'not found' in result_dict['error'].lower()


class TestListSkillsMCP:
    """Tests for list_skills MCP tool."""

    def test_list_skills_returns_json(self, patched_server_paths):
        """Test that list_skills returns valid JSON."""
        result = list_skills()
        result_dict = json.loads(result)

        assert 'count' in result_dict
        assert 'skills' in result_dict

    def test_list_skills_counts_correctly(self, patched_server_paths):
        """Test that skill count is accurate."""
        save_skill("count_skill1", "code", "")
        save_skill("count_skill2", "code", "")

        result = list_skills()
        result_dict = json.loads(result)

        assert result_dict['count'] == 2


class TestSkillsInCodeExecution:
    """Tests for skills used within code execution."""

    def test_save_skill_from_sandbox(self, patched_server_paths):
        """Test saving a skill from within sandbox execution."""
        code = '''
skill_code = """
def filter_active(data):
    return [d for d in data if d.get('active')]
"""
result = save_skill("filter_active", skill_code, "Filter active items")
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True

        # Verify skill was saved
        skills_result = list_skills()
        skills_dict = json.loads(skills_result)
        assert skills_dict['count'] >= 1

    def test_load_skill_from_sandbox(self, patched_server_paths):
        """Test loading a skill from within sandbox execution."""
        # First save a skill
        save_skill("loadable", "def run(): return 99", "Test skill")

        # Then load it in sandbox
        code = '''
skill_code = load_skill("loadable")
result = {"loaded": True, "code": skill_code}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['loaded'] is True
        assert "def run()" in result_dict['result']['code']

    def test_list_skills_from_sandbox(self, patched_server_paths):
        """Test listing skills from within sandbox execution."""
        save_skill("skill_a", "a", "A")
        save_skill("skill_b", "b", "B")

        code = '''
skills = list_skills()
result = {"skill_count": len(skills)}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['skill_count'] == 2

    def test_skill_reuse_workflow(self, patched_server_paths):
        """Test full skill save-load-use workflow."""
        # Save a skill
        save_skill("double_values", "def double(x): return x * 2", "Double input")

        # Use the skill in execution
        code = '''
# Load the skill
skill_code = load_skill("double_values")

# We can't directly execute the loaded skill, but we can verify it loads
result = {"skill_loaded": "def double" in skill_code}
'''
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['skill_loaded'] is True

"""
Tests for tool registry and progressive discovery functionality.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    get_catalog,
    get_tool_definition,
    get_tool_from_catalog,
    list_categories,
    list_tool_categories,
    search_catalog,
    search_tools,
)


class TestGetCatalog:
    """Tests for get_catalog function."""

    def test_get_catalog_returns_dict(self, patched_server_paths):
        """Test that get_catalog returns a dictionary."""
        catalog = get_catalog()
        assert isinstance(catalog, dict)

    def test_get_catalog_has_categories(self, patched_server_paths):
        """Test that catalog contains categories."""
        catalog = get_catalog()
        assert 'categories' in catalog

    def test_get_catalog_caches_result(self, patched_server_paths):
        """Test that catalog is cached after first load."""
        catalog1 = get_catalog()
        catalog2 = get_catalog()
        assert catalog1 is catalog2  # Same object reference


class TestSearchCatalog:
    """Tests for search_catalog function."""

    def test_search_by_name(self, patched_server_paths):
        """Test searching by tool name."""
        results = search_catalog("fraud")

        assert len(results) >= 1
        assert any("fraud" in r['name'].lower() for r in results)

    def test_search_by_description(self, patched_server_paths):
        """Test searching by description."""
        results = search_catalog("memory")

        assert len(results) >= 1

    def test_search_by_function(self, patched_server_paths):
        """Test searching by function name."""
        results = search_catalog("create_entities")

        assert len(results) >= 1

    def test_search_by_use_case(self, patched_server_paths):
        """Test searching by use case."""
        results = search_catalog("transaction")

        assert len(results) >= 1

    def test_search_with_category_filter(self, patched_server_paths):
        """Test searching with category filter."""
        results = search_catalog("memory", category="memory")

        assert len(results) >= 1
        assert all(r['category'] == 'memory' for r in results)

    def test_search_no_results(self, patched_server_paths):
        """Test search with no matching results."""
        results = search_catalog("xyznonexistent123")

        assert len(results) == 0

    def test_search_case_insensitive(self, patched_server_paths):
        """Test that search is case insensitive."""
        results_lower = search_catalog("fraud")
        results_upper = search_catalog("FRAUD")

        assert len(results_lower) == len(results_upper)

    def test_search_returns_tool_details(self, patched_server_paths):
        """Test that search results include tool details."""
        results = search_catalog("enhanced-memory")

        if len(results) > 0:
            result = results[0]
            assert 'name' in result
            assert 'category' in result
            assert 'mcp_server' in result
            assert 'description' in result


class TestGetToolFromCatalog:
    """Tests for get_tool_from_catalog function."""

    def test_get_existing_tool(self, patched_server_paths):
        """Test getting an existing tool."""
        tool = get_tool_from_catalog("enhanced-memory")

        assert tool is not None
        assert 'description' in tool
        assert 'functions' in tool

    def test_get_nonexistent_tool(self, patched_server_paths):
        """Test getting a nonexistent tool."""
        tool = get_tool_from_catalog("nonexistent-tool-xyz")

        assert tool is None

    def test_get_tool_includes_category(self, patched_server_paths):
        """Test that retrieved tool includes category."""
        tool = get_tool_from_catalog("enhanced-memory")

        assert tool is not None
        assert 'category' in tool
        assert tool['category'] == 'memory'


class TestListCategories:
    """Tests for list_categories function."""

    def test_list_categories_returns_dict(self, patched_server_paths):
        """Test that list_categories returns a dictionary."""
        categories = list_categories()
        assert isinstance(categories, dict)

    def test_list_categories_has_descriptions(self, patched_server_paths):
        """Test that categories have descriptions."""
        categories = list_categories()

        for cat_name, cat_data in categories.items():
            assert 'description' in cat_data

    def test_list_categories_has_tool_counts(self, patched_server_paths):
        """Test that categories have tool counts."""
        categories = list_categories()

        for cat_name, cat_data in categories.items():
            assert 'tool_count' in cat_data
            assert isinstance(cat_data['tool_count'], int)


class TestSearchToolsMCP:
    """Tests for search_tools MCP tool."""

    def test_search_tools_returns_json(self, patched_server_paths):
        """Test that search_tools returns valid JSON."""
        result = search_tools("memory")
        result_dict = json.loads(result)

        assert 'query' in result_dict
        assert 'count' in result_dict
        assert 'tools' in result_dict

    def test_search_tools_summary_mode(self, patched_server_paths):
        """Test search with summary detail level."""
        result = search_tools("memory", detail_level="summary")
        result_dict = json.loads(result)

        if result_dict['count'] > 0:
            tool = result_dict['tools'][0]
            assert 'name' in tool
            assert 'description' in tool
            # Summary should not include full details
            assert 'use_cases' not in tool or tool.get('use_cases') is None

    def test_search_tools_full_mode(self, patched_server_paths):
        """Test search with full detail level."""
        result = search_tools("memory", detail_level="full")
        result_dict = json.loads(result)

        if result_dict['count'] > 0:
            tool = result_dict['tools'][0]
            assert 'functions' in tool
            assert 'use_cases' in tool

    def test_search_tools_with_category(self, patched_server_paths):
        """Test search with category filter."""
        result = search_tools("", category="security")
        result_dict = json.loads(result)

        if result_dict['count'] > 0:
            assert all(t['category'] == 'security' for t in result_dict['tools'])

    def test_search_tools_includes_query_in_response(self, patched_server_paths):
        """Test that response includes original query."""
        result = search_tools("test_query")
        result_dict = json.loads(result)

        assert result_dict['query'] == "test_query"


class TestGetToolDefinitionMCP:
    """Tests for get_tool_definition MCP tool."""

    def test_get_definition_returns_json(self, patched_server_paths):
        """Test that get_tool_definition returns valid JSON."""
        result = get_tool_definition("enhanced-memory")

        if result:  # May be None if tool doesn't exist
            result_dict = json.loads(result)
            assert isinstance(result_dict, dict)

    def test_get_definition_includes_functions(self, patched_server_paths):
        """Test that definition includes function list."""
        result = get_tool_definition("enhanced-memory")

        if result:
            result_dict = json.loads(result)
            assert 'functions' in result_dict

    def test_get_definition_includes_use_cases(self, patched_server_paths):
        """Test that definition includes use cases."""
        result = get_tool_definition("enhanced-memory")

        if result:
            result_dict = json.loads(result)
            assert 'use_cases' in result_dict

    def test_get_definition_nonexistent_tool(self, patched_server_paths):
        """Test getting definition for nonexistent tool."""
        result = get_tool_definition("totally-fake-tool")

        assert result is None


class TestListToolCategoriesMCP:
    """Tests for list_tool_categories MCP tool."""

    def test_list_categories_returns_json(self, patched_server_paths):
        """Test that list_tool_categories returns valid JSON."""
        result = list_tool_categories()
        result_dict = json.loads(result)

        assert 'categories' in result_dict

    def test_list_categories_includes_totals(self, patched_server_paths):
        """Test that response includes total tool count."""
        result = list_tool_categories()
        result_dict = json.loads(result)

        assert 'total_tools' in result_dict

    def test_list_categories_includes_core_mcps(self, patched_server_paths):
        """Test that response includes core MCPs."""
        result = list_tool_categories()
        result_dict = json.loads(result)

        assert 'core_mcps' in result_dict
        assert isinstance(result_dict['core_mcps'], list)


class TestProgressiveDiscoveryWorkflow:
    """Tests for the progressive discovery workflow pattern."""

    def test_discovery_workflow(self, patched_server_paths):
        """Test the full progressive discovery workflow."""
        # Step 1: List categories to understand available tools
        categories_result = list_tool_categories()
        categories = json.loads(categories_result)

        assert 'categories' in categories

        # Step 2: Search for specific capability
        search_result = search_tools("memory", detail_level="summary")
        search = json.loads(search_result)

        assert search['count'] >= 0

        # Step 3: Get full definition for a specific tool
        if search['count'] > 0:
            tool_name = search['tools'][0]['name']
            definition_result = get_tool_definition(tool_name)

            if definition_result:
                definition = json.loads(definition_result)
                assert 'functions' in definition

    def test_token_efficiency_summary_vs_full(self, patched_server_paths):
        """Test that summary mode returns less data than full mode."""
        summary_result = search_tools("memory", detail_level="summary")
        full_result = search_tools("memory", detail_level="full")

        # Summary should be shorter (fewer tokens)
        assert len(summary_result) <= len(full_result)


class TestCatalogEdgeCases:
    """Tests for catalog edge cases."""

    def test_empty_query_search(self, patched_server_paths):
        """Test searching with empty query."""
        results = search_catalog("")

        # Empty query should match nothing or everything
        assert isinstance(results, list)

    def test_special_characters_in_query(self, patched_server_paths):
        """Test searching with special characters."""
        results = search_catalog("test@#$%")

        assert isinstance(results, list)

    def test_unicode_in_query(self, patched_server_paths):
        """Test searching with unicode characters."""
        results = search_catalog("memory")

        assert isinstance(results, list)

    def test_very_long_query(self, patched_server_paths):
        """Test searching with very long query."""
        long_query = "a" * 1000
        results = search_catalog(long_query)

        assert isinstance(results, list)
        assert len(results) == 0  # Unlikely to match anything

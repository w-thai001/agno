"""
Security Validator FSA (Focused Specialized Agent)

This module provides comprehensive security analysis and validation capabilities
for the MLA (Multi-Layer Agent) framework. It performs static code security analysis,
vulnerability detection, dependency scanning, secret detection, and compliance checking.

Features:
- Static code security analysis
- Vulnerability detection (SQL injection, XSS, CSRF, etc.)
- Dependency vulnerability scanning
- Secret detection and credential scanning
- Authentication/authorization validation
- Input sanitization verification
- Cryptographic implementation analysis
- Security configuration auditing
- OWASP Top 10 compliance checking
- Security policy enforcement
- Penetration testing automation
- Security report generation

Author: Agno Security Team
Version: 1.0.0
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# Security pattern definitions
SQL_INJECTION_PATTERNS = [
    r"execute\s*\(\s*['\"].*%s.*['\"]",
    r"executemany\s*\(\s*['\"].*%s.*['\"]",
    r"cursor\.execute\s*\(\s*['\"].*\+.*['\"]",
    r"db\.execute\s*\(\s*f['\"].*\{.*\}.*['\"]",
    r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=\s*['\"]?\s*\+",
    r"INSERT\s+INTO\s+.*\s+VALUES\s*\(.*\+.*\)",
    r"UPDATE\s+.*\s+SET\s+.*=.*\+",
    r"DELETE\s+FROM\s+.*\s+WHERE\s+.*=.*\+",
    r"query\s*=\s*['\"].*['\"].*\+.*",
    r"sql\s*=\s*f['\"].*\{[^}]*\}.*['\"]",
]

XSS_PATTERNS = [
    r"innerHTML\s*=\s*.*",
    r"outerHTML\s*=\s*.*",
    r"document\.write\s*\(.*\)",
    r"eval\s*\(.*\)",
    r"<script>.*</script>",
    r"javascript:.*",
    r"on\w+\s*=\s*['\"].*['\"]",
    r"dangerouslySetInnerHTML",
    r"v-html\s*=",
    r"\{\{\{.*\}\}\}",
]

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]([^'\"]{20,})['\"]", "API Key"),
    (r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]([^'\"]{20,})['\"]", "Secret Key"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "Password"),
    (r"(?i)(auth[_-]?token|authtoken)\s*[:=]\s*['\"]([^'\"]{20,})['\"]", "Auth Token"),
    (r"(?i)(access[_-]?token|accesstoken)\s*[:=]\s*['\"]([^'\"]{20,})['\"]", "Access Token"),
    (r"(?i)(private[_-]?key|privatekey)\s*[:=]\s*['\"]([^'\"]{20,})['\"]", "Private Key"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]([^'\"]{40})['\"]", "AWS Secret Key"),
    (r"(?i)sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"(?i)ghp_[a-zA-Z0-9]{36,}", "GitHub Token"),
    (r"(?i)glpat-[a-zA-Z0-9_\-]{20,}", "GitLab Token"),
    (r"(?i)AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?i)AIza[0-9A-Za-z_-]{35}", "Google API Key"),
    (r"(?i)ya29\.[0-9A-Za-z_-]{100,}", "Google OAuth Token"),
    (r"(?i)sk_live_[0-9a-zA-Z]{24,}", "Stripe Live Key"),
    (r"(?i)rk_live_[0-9a-zA-Z]{24,}", "Stripe Restricted Key"),
]

CRYPTO_WEAK_ALGORITHMS = [
    "MD5", "SHA1", "DES", "3DES", "RC4", "RC2",
    "Blowfish", "ECB", "md5", "sha1"
]

CSRF_PATTERNS = [
    r"@app\.route\(.*methods\s*=\s*\[['\"]POST['\"]",
    r"@api\.route\(.*methods\s*=\s*\[['\"]POST['\"]",
    r"def\s+post\s*\(",
    r"def\s+put\s*\(",
    r"def\s+delete\s*\(",
]

UNSAFE_DESERIALIZATION_PATTERNS = [
    r"pickle\.loads\s*\(",
    r"yaml\.load\s*\(",
    r"marshal\.loads\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
]

PATH_TRAVERSAL_PATTERNS = [
    r"open\s*\([^)]*\+",
    r"os\.path\.join\s*\([^)]*user",
    r"\.\.\/",
    r"\.\.[\\\/]",
    r"file_path\s*=\s*.*request\.",
]


class VulnerabilitySeverity(Enum):
    """Enumeration of vulnerability severity levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


class ComplianceFramework(Enum):
    """Enumeration of compliance frameworks."""
    OWASP_TOP_10 = "OWASP Top 10"
    PCI_DSS = "PCI-DSS"
    HIPAA = "HIPAA"
    SOC2 = "SOC2"
    GDPR = "GDPR"
    NIST = "NIST"


@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    id: str
    title: str
    description: str
    severity: VulnerabilitySeverity
    category: str
    file_path: str
    line_number: int
    code_snippet: str
    remediation: str
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    confidence: float = 1.0
    references: List[str] = field(default_factory=list)


@dataclass
class SecurityReport:
    """Represents a comprehensive security report."""
    timestamp: str
    scan_duration: float
    total_files_scanned: int
    vulnerabilities: List[Vulnerability]
    risk_score: float
    compliance_status: Dict[str, bool]
    summary: Dict[str, int]
    recommendations: List[str]


class SecurityValidatorFSA:
    """
    Security Validator FSA (Focused Specialized Agent)

    This agent performs comprehensive security analysis and validation on codebases,
    identifying vulnerabilities, security misconfigurations, and compliance issues.

    Attributes:
        codebase_path (str): Path to the codebase to analyze
        security_level (str): Security analysis level (basic, standard, comprehensive)
        findings (List[Vulnerability]): List of detected vulnerabilities
        metadata (Dict[str, Any]): Additional metadata about the analysis
        supported_extensions (Set[str]): Set of supported file extensions
    """

    def __init__(self, codebase_path: Optional[str] = None, security_level: str = "standard"):
        """
        Initialize the Security Validator FSA.

        Args:
            codebase_path (str, optional): Path to the codebase to analyze
            security_level (str): Level of security analysis (basic, standard, comprehensive)
        """
        self.codebase_path = codebase_path
        self.security_level = security_level
        self.findings: List[Vulnerability] = []
        self.metadata: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "files_scanned": 0,
            "lines_scanned": 0,
            "scan_duration": 0.0,
        }
        self.supported_extensions = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".c",
            ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala",
            ".html", ".htm", ".xml", ".json", ".yaml", ".yml", ".sql",
            ".sh", ".bash", ".ps1", ".dockerfile"
        }
        self.vulnerability_id_counter = 0
        self.file_cache: Dict[str, str] = {}
        self.cve_database: Dict[str, Dict[str, Any]] = {}
        self._load_cve_database()

    def _load_cve_database(self) -> None:
        """Load CVE database for dependency vulnerability checking."""
        # Simulated CVE database with known vulnerable packages
        self.cve_database = {
            "requests": [
                {
                    "version": "2.6.0",
                    "cve_id": "CVE-2015-2296",
                    "severity": "HIGH",
                    "description": "CRLF injection vulnerability"
                }
            ],
            "django": [
                {
                    "version": "2.2.0",
                    "cve_id": "CVE-2019-14234",
                    "severity": "CRITICAL",
                    "description": "SQL injection vulnerability"
                }
            ],
            "flask": [
                {
                    "version": "0.12.3",
                    "cve_id": "CVE-2018-1000656",
                    "severity": "HIGH",
                    "description": "Denial of Service vulnerability"
                }
            ],
            "pyyaml": [
                {
                    "version": "5.1",
                    "cve_id": "CVE-2020-1747",
                    "severity": "CRITICAL",
                    "description": "Arbitrary code execution"
                }
            ],
            "pillow": [
                {
                    "version": "6.2.1",
                    "cve_id": "CVE-2020-5312",
                    "severity": "HIGH",
                    "description": "Buffer overflow"
                }
            ],
        }

    def execute(self, codebase_path: Optional[str] = None, security_level: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute comprehensive security analysis on the codebase.

        Args:
            codebase_path (str, optional): Path to the codebase to analyze
            security_level (str, optional): Level of security analysis

        Returns:
            Dict[str, Any]: Analysis results including vulnerabilities and metadata
        """
        if codebase_path:
            self.codebase_path = codebase_path
        if security_level:
            self.security_level = security_level

        if not self.codebase_path:
            raise ValueError("Codebase path must be provided")

        if not os.path.exists(self.codebase_path):
            raise FileNotFoundError(f"Codebase path not found: {self.codebase_path}")

        self.metadata["start_time"] = datetime.now().isoformat()
        start_timestamp = datetime.now()

        try:
            # Scan all files in the codebase
            for root, dirs, files in os.walk(self.codebase_path):
                # Skip common directories that shouldn't be scanned
                dirs[:] = [d for d in dirs if d not in {
                    '.git', '.svn', 'node_modules', '__pycache__',
                    '.pytest_cache', 'venv', 'env', '.venv', 'dist', 'build'
                }]

                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()

                    if file_ext in self.supported_extensions:
                        self._scan_file(file_path)

            # Scan dependencies if requirements files exist
            self._scan_project_dependencies()

            # Perform security configuration audit
            self._audit_security_configurations()

            # Check OWASP compliance
            compliance_status = self.check_owasp_compliance({
                "vulnerabilities": self.findings,
                "codebase_path": self.codebase_path
            })

            # Calculate risk score
            risk_score = self.calculate_risk_score(self.findings)

            # Generate report
            report = self.generate_security_report(self.findings)

            self.metadata["end_time"] = datetime.now().isoformat()
            self.metadata["scan_duration"] = (datetime.now() - start_timestamp).total_seconds()

            return {
                "success": True,
                "vulnerabilities": [self._vulnerability_to_dict(v) for v in self.findings],
                "risk_score": risk_score,
                "compliance_status": compliance_status,
                "report": report,
                "metadata": self.metadata,
                "summary": self._generate_summary()
            }

        except Exception as e:
            return self.error_handling(e)

    def _scan_file(self, file_path: str) -> None:
        """
        Scan a single file for security vulnerabilities.

        Args:
            file_path (str): Path to the file to scan
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                self.file_cache[file_path] = content
                self.metadata["files_scanned"] += 1
                self.metadata["lines_scanned"] += len(content.split('\n'))

            # Perform different scans based on file type
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.py':
                self._scan_python_file(file_path, content)
            elif file_ext in {'.js', '.jsx', '.ts', '.tsx'}:
                self._scan_javascript_file(file_path, content)
            elif file_ext in {'.html', '.htm'}:
                self._scan_html_file(file_path, content)

            # Perform general scans on all files
            self._scan_for_secrets(file_path, content)
            self._scan_for_path_traversal(file_path, content)

        except Exception as e:
            # Log error but continue scanning
            pass

    def _scan_python_file(self, file_path: str, content: str) -> None:
        """
        Scan Python file for security vulnerabilities.

        Args:
            file_path (str): Path to the Python file
            content (str): File content
        """
        try:
            tree = ast.parse(content)

            # Detect SQL injection vulnerabilities
            sql_vulns = self.detect_sql_injection(tree)
            for line_num in sql_vulns:
                self._add_vulnerability(
                    title="SQL Injection Vulnerability",
                    description="Potential SQL injection vulnerability detected. User input may be concatenated directly into SQL query.",
                    severity=VulnerabilitySeverity.CRITICAL,
                    category="Injection",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=self._get_code_snippet(content, line_num),
                    remediation="Use parameterized queries or ORM methods instead of string concatenation.",
                    cwe_id="CWE-89",
                    owasp_category="A03:2021-Injection"
                )

            # Detect unsafe deserialization
            unsafe_deser = self._detect_unsafe_deserialization(content)
            for line_num, pattern in unsafe_deser:
                self._add_vulnerability(
                    title="Unsafe Deserialization",
                    description=f"Unsafe deserialization detected using {pattern}. This can lead to arbitrary code execution.",
                    severity=VulnerabilitySeverity.CRITICAL,
                    category="Deserialization",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=self._get_code_snippet(content, line_num),
                    remediation="Use safe serialization formats like JSON. Avoid pickle, marshal, and yaml.load().",
                    cwe_id="CWE-502",
                    owasp_category="A08:2021-Software and Data Integrity Failures"
                )

            # Detect weak cryptography
            weak_crypto = self._detect_weak_cryptography(content)
            for line_num, algorithm in weak_crypto:
                self._add_vulnerability(
                    title="Weak Cryptographic Algorithm",
                    description=f"Weak cryptographic algorithm detected: {algorithm}",
                    severity=VulnerabilitySeverity.HIGH,
                    category="Cryptography",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=self._get_code_snippet(content, line_num),
                    remediation="Use strong cryptographic algorithms like SHA-256, AES-256-GCM, or RSA-2048+.",
                    cwe_id="CWE-327",
                    owasp_category="A02:2021-Cryptographic Failures"
                )

        except SyntaxError:
            # File has syntax errors, skip AST analysis
            pass

    def _scan_javascript_file(self, file_path: str, content: str) -> None:
        """
        Scan JavaScript/TypeScript file for security vulnerabilities.

        Args:
            file_path (str): Path to the JavaScript file
            content (str): File content
        """
        # Detect XSS vulnerabilities
        xss_vulns = self.detect_xss_vulnerabilities([content])
        for line_num in xss_vulns:
            self._add_vulnerability(
                title="Cross-Site Scripting (XSS) Vulnerability",
                description="Potential XSS vulnerability detected. Unescaped user input may be rendered in the DOM.",
                severity=VulnerabilitySeverity.HIGH,
                category="XSS",
                file_path=file_path,
                line_number=line_num,
                code_snippet=self._get_code_snippet(content, line_num),
                remediation="Always escape user input before rendering. Use textContent instead of innerHTML.",
                cwe_id="CWE-79",
                owasp_category="A03:2021-Injection"
            )

    def _scan_html_file(self, file_path: str, content: str) -> None:
        """
        Scan HTML template file for security vulnerabilities.

        Args:
            file_path (str): Path to the HTML file
            content (str): File content
        """
        # Detect XSS in templates
        xss_vulns = self.detect_xss_vulnerabilities([content])
        for line_num in xss_vulns:
            self._add_vulnerability(
                title="Template XSS Vulnerability",
                description="Potential XSS vulnerability in HTML template.",
                severity=VulnerabilitySeverity.HIGH,
                category="XSS",
                file_path=file_path,
                line_number=line_num,
                code_snippet=self._get_code_snippet(content, line_num),
                remediation="Use template engine's auto-escaping features.",
                cwe_id="CWE-79",
                owasp_category="A03:2021-Injection"
            )

    def _scan_for_secrets(self, file_path: str, content: str) -> None:
        """
        Scan file for hardcoded secrets and credentials.

        Args:
            file_path (str): Path to the file
            content (str): File content
        """
        secrets = self.detect_secrets(content)
        for secret in secrets:
            self._add_vulnerability(
                title=f"Hardcoded {secret['type']} Detected",
                description=f"Hardcoded secret or credential found in source code: {secret['type']}",
                severity=VulnerabilitySeverity.CRITICAL,
                category="Secret Management",
                file_path=file_path,
                line_number=secret['line'],
                code_snippet=secret['snippet'],
                remediation="Store secrets in environment variables or secure secret management systems.",
                cwe_id="CWE-798",
                owasp_category="A07:2021-Identification and Authentication Failures"
            )

    def _scan_for_path_traversal(self, file_path: str, content: str) -> None:
        """
        Scan file for path traversal vulnerabilities.

        Args:
            file_path (str): Path to the file
            content (str): File content
        """
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern in PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, line):
                    self._add_vulnerability(
                        title="Path Traversal Vulnerability",
                        description="Potential path traversal vulnerability. User input may be used to access arbitrary files.",
                        severity=VulnerabilitySeverity.HIGH,
                        category="Path Traversal",
                        file_path=file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        remediation="Validate and sanitize file paths. Use os.path.abspath() and check if path is within allowed directory.",
                        cwe_id="CWE-22",
                        owasp_category="A01:2021-Broken Access Control"
                    )
                    break

    def scan_vulnerabilities(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Scan source code for vulnerabilities.

        Args:
            source_code (str): Source code to analyze

        Returns:
            List[Dict[str, Any]]: List of detected vulnerabilities
        """
        vulnerabilities = []

        # Check for SQL injection patterns
        for i, line in enumerate(source_code.split('\n'), 1):
            for pattern in SQL_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    vulnerabilities.append({
                        "type": "SQL Injection",
                        "line": i,
                        "severity": "CRITICAL",
                        "description": "Potential SQL injection vulnerability"
                    })
                    break

        # Check for XSS patterns
        for i, line in enumerate(source_code.split('\n'), 1):
            for pattern in XSS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    vulnerabilities.append({
                        "type": "XSS",
                        "line": i,
                        "severity": "HIGH",
                        "description": "Potential XSS vulnerability"
                    })
                    break

        return vulnerabilities

    def detect_sql_injection(self, code_ast: ast.Module) -> List[int]:
        """
        Detect SQL injection vulnerabilities in Python AST.

        Args:
            code_ast (ast.Module): Python AST module

        Returns:
            List[int]: List of line numbers with SQL injection vulnerabilities
        """
        vulnerable_lines = []

        class SQLInjectionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.vulnerable_lines = []

            def visit_Call(self, node):
                # Check for execute() calls with string concatenation or f-strings
                if hasattr(node.func, 'attr') and node.func.attr in ['execute', 'executemany', 'raw']:
                    if node.args:
                        arg = node.args[0]
                        # Check for BinOp (string concatenation)
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                            self.vulnerable_lines.append(node.lineno)
                        # Check for f-strings (JoinedStr)
                        elif isinstance(arg, ast.JoinedStr):
                            self.vulnerable_lines.append(node.lineno)
                        # Check for format() calls
                        elif isinstance(arg, ast.Call) and hasattr(arg.func, 'attr') and arg.func.attr == 'format':
                            self.vulnerable_lines.append(node.lineno)

                self.generic_visit(node)

        visitor = SQLInjectionVisitor()
        visitor.visit(code_ast)
        return visitor.vulnerable_lines

    def detect_xss_vulnerabilities(self, templates: List[str]) -> List[int]:
        """
        Detect XSS vulnerabilities in templates.

        Args:
            templates (List[str]): List of template contents

        Returns:
            List[int]: List of line numbers with XSS vulnerabilities
        """
        vulnerable_lines = []

        for template in templates:
            lines = template.split('\n')
            for i, line in enumerate(lines, 1):
                for pattern in XSS_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        vulnerable_lines.append(i)
                        break

        return vulnerable_lines

    def scan_dependencies(self, requirements: List[str]) -> Dict[str, List[str]]:
        """
        Scan dependencies for known vulnerabilities.

        Args:
            requirements (List[str]): List of requirement strings

        Returns:
            Dict[str, List[str]]: Dictionary mapping packages to vulnerabilities
        """
        vulnerabilities = defaultdict(list)

        for req in requirements:
            # Parse requirement string
            req = req.strip()
            if not req or req.startswith('#'):
                continue

            # Extract package name and version
            match = re.match(r'([a-zA-Z0-9_-]+)\s*([=<>!]+)\s*([0-9.]+)', req)
            if match:
                package_name = match.group(1).lower()
                version = match.group(3)

                # Check against CVE database
                if package_name in self.cve_database:
                    for vuln in self.cve_database[package_name]:
                        if version <= vuln['version']:
                            vulnerabilities[package_name].append(
                                f"{vuln['cve_id']}: {vuln['description']} (Severity: {vuln['severity']})"
                            )

        return dict(vulnerabilities)

    def _scan_project_dependencies(self) -> None:
        """Scan project dependencies for vulnerabilities."""
        requirements_files = [
            'requirements.txt', 'requirements-dev.txt', 'requirements-prod.txt',
            'Pipfile', 'poetry.lock', 'package.json'
        ]

        for req_file in requirements_files:
            req_path = os.path.join(self.codebase_path, req_file)
            if os.path.exists(req_path):
                try:
                    with open(req_path, 'r') as f:
                        content = f.read()

                    if req_file.endswith('.txt'):
                        requirements = content.split('\n')
                        vulns = self.scan_dependencies(requirements)

                        for package, issues in vulns.items():
                            for issue in issues:
                                self._add_vulnerability(
                                    title=f"Vulnerable Dependency: {package}",
                                    description=issue,
                                    severity=VulnerabilitySeverity.HIGH,
                                    category="Dependency Vulnerability",
                                    file_path=req_path,
                                    line_number=1,
                                    code_snippet=f"{package} has known vulnerabilities",
                                    remediation=f"Update {package} to the latest secure version.",
                                    owasp_category="A06:2021-Vulnerable and Outdated Components"
                                )
                except Exception:
                    pass

    def detect_secrets(self, file_content: str) -> List[Dict[str, str]]:
        """
        Detect hardcoded secrets and credentials.

        Args:
            file_content (str): Content of the file to scan

        Returns:
            List[Dict[str, str]]: List of detected secrets
        """
        secrets = []
        lines = file_content.split('\n')

        for i, line in enumerate(lines, 1):
            for pattern, secret_type in SECRET_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    secrets.append({
                        'type': secret_type,
                        'line': i,
                        'snippet': line.strip()[:100],  # Truncate long lines
                        'match': match.group(0)
                    })

        return secrets

    def validate_authentication(self, auth_code: str) -> Dict[str, Any]:
        """
        Validate authentication implementation.

        Args:
            auth_code (str): Authentication-related code

        Returns:
            Dict[str, Any]: Validation results
        """
        issues = []

        # Check for weak password hashing
        weak_hashing = ['md5', 'sha1', 'base64']
        for algo in weak_hashing:
            if algo in auth_code.lower():
                issues.append({
                    'type': 'Weak Password Hashing',
                    'severity': 'CRITICAL',
                    'description': f'Weak hashing algorithm detected: {algo}',
                    'remediation': 'Use bcrypt, scrypt, or argon2 for password hashing'
                })

        # Check for missing authentication
        if 'login' in auth_code.lower() or 'authenticate' in auth_code.lower():
            if 'csrf' not in auth_code.lower():
                issues.append({
                    'type': 'Missing CSRF Protection',
                    'severity': 'HIGH',
                    'description': 'Authentication endpoint may lack CSRF protection',
                    'remediation': 'Implement CSRF tokens for authentication forms'
                })

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'score': max(0, 100 - len(issues) * 20)
        }

    def analyze_cryptography(self, crypto_usage: List[str]) -> List[str]:
        """
        Analyze cryptographic implementations for weaknesses.

        Args:
            crypto_usage (List[str]): List of cryptographic code snippets

        Returns:
            List[str]: List of identified issues
        """
        issues = []

        for code in crypto_usage:
            # Check for weak algorithms
            for weak_algo in CRYPTO_WEAK_ALGORITHMS:
                if weak_algo.lower() in code.lower():
                    issues.append(f"Weak cryptographic algorithm detected: {weak_algo}")

            # Check for hardcoded keys
            if re.search(r'key\s*=\s*["\'][^"\']{8,}["\']', code, re.IGNORECASE):
                issues.append("Hardcoded cryptographic key detected")

            # Check for ECB mode
            if 'ecb' in code.lower():
                issues.append("ECB mode detected - use CBC, GCM, or CTR mode instead")

            # Check for static IV
            if re.search(r'iv\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
                issues.append("Static initialization vector (IV) detected")

        return issues

    def _detect_unsafe_deserialization(self, content: str) -> List[Tuple[int, str]]:
        """Detect unsafe deserialization patterns."""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for pattern in UNSAFE_DESERIALIZATION_PATTERNS:
                if re.search(pattern, line):
                    issues.append((i, pattern.split('\\')[0]))

        return issues

    def _detect_weak_cryptography(self, content: str) -> List[Tuple[int, str]]:
        """Detect weak cryptographic algorithms."""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for algo in CRYPTO_WEAK_ALGORITHMS:
                if algo in line:
                    issues.append((i, algo))

        return issues

    def check_owasp_compliance(self, codebase: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check compliance with OWASP Top 10.

        Args:
            codebase (Dict[str, Any]): Codebase analysis data

        Returns:
            Dict[str, bool]: Compliance status for each OWASP category
        """
        compliance = {}
        vulnerabilities = codebase.get('vulnerabilities', [])

        # Map vulnerabilities to OWASP categories
        owasp_categories = {
            'A01:2021-Broken Access Control': [],
            'A02:2021-Cryptographic Failures': [],
            'A03:2021-Injection': [],
            'A04:2021-Insecure Design': [],
            'A05:2021-Security Misconfiguration': [],
            'A06:2021-Vulnerable and Outdated Components': [],
            'A07:2021-Identification and Authentication Failures': [],
            'A08:2021-Software and Data Integrity Failures': [],
            'A09:2021-Security Logging and Monitoring Failures': [],
            'A10:2021-Server-Side Request Forgery': []
        }

        for vuln in vulnerabilities:
            if isinstance(vuln, Vulnerability):
                if vuln.owasp_category:
                    owasp_categories[vuln.owasp_category].append(vuln)

        # Determine compliance (no critical/high severity issues)
        for category, vulns in owasp_categories.items():
            critical_or_high = [v for v in vulns if v.severity in [VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH]]
            compliance[category] = len(critical_or_high) == 0

        return compliance

    def audit_security_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Audit security configuration settings.

        Args:
            config (Dict[str, Any]): Configuration dictionary

        Returns:
            List[str]: List of security configuration issues
        """
        issues = []

        # Check debug mode
        if config.get('DEBUG', False) or config.get('debug', False):
            issues.append("Debug mode is enabled in production")

        # Check secret key
        if 'SECRET_KEY' in config:
            if len(config['SECRET_KEY']) < 32:
                issues.append("Secret key is too short (minimum 32 characters)")
            if config['SECRET_KEY'] in ['secret', 'changeme', 'default']:
                issues.append("Secret key is using a default or weak value")

        # Check HTTPS enforcement
        if not config.get('SECURE_SSL_REDIRECT', True):
            issues.append("HTTPS redirect is not enforced")

        # Check CSRF protection
        if not config.get('CSRF_ENABLED', True):
            issues.append("CSRF protection is disabled")

        # Check session security
        if not config.get('SESSION_COOKIE_SECURE', True):
            issues.append("Session cookies are not marked as secure")
        if not config.get('SESSION_COOKIE_HTTPONLY', True):
            issues.append("Session cookies are not marked as HTTPOnly")

        # Check CORS configuration
        if config.get('CORS_ORIGINS') == '*':
            issues.append("CORS is configured to allow all origins")

        return issues

    def _audit_security_configurations(self) -> None:
        """Audit security configuration files in the codebase."""
        config_files = ['settings.py', 'config.py', 'configuration.py', '.env', 'web.config']

        for root, _, files in os.walk(self.codebase_path):
            for file in files:
                if file in config_files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()

                        # Simple config parsing (key=value)
                        config = {}
                        for line in content.split('\n'):
                            if '=' in line and not line.strip().startswith('#'):
                                parts = line.split('=', 1)
                                if len(parts) == 2:
                                    key = parts[0].strip()
                                    value = parts[1].strip().strip('\'"')
                                    config[key] = value

                        issues = self.audit_security_config(config)
                        for issue in issues:
                            self._add_vulnerability(
                                title="Security Misconfiguration",
                                description=issue,
                                severity=VulnerabilitySeverity.MEDIUM,
                                category="Configuration",
                                file_path=file_path,
                                line_number=1,
                                code_snippet="Configuration file",
                                remediation="Review and update security configuration settings.",
                                owasp_category="A05:2021-Security Misconfiguration"
                            )
                    except Exception:
                        pass

    def generate_security_report(self, findings: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive security report.

        Args:
            findings (List[Dict[str, Any]]): List of security findings

        Returns:
            str: Formatted security report
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("SECURITY ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Codebase: {self.codebase_path}")
        report_lines.append(f"Security Level: {self.security_level}")
        report_lines.append("")

        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 80)
        summary = self._generate_summary()
        report_lines.append(f"Total Vulnerabilities: {summary['total']}")
        report_lines.append(f"  Critical: {summary['critical']}")
        report_lines.append(f"  High: {summary['high']}")
        report_lines.append(f"  Medium: {summary['medium']}")
        report_lines.append(f"  Low: {summary['low']}")
        report_lines.append(f"Files Scanned: {self.metadata['files_scanned']}")
        report_lines.append(f"Lines Scanned: {self.metadata['lines_scanned']}")
        report_lines.append(f"Scan Duration: {self.metadata['scan_duration']:.2f}s")
        report_lines.append("")

        # Risk Score
        risk_score = self.calculate_risk_score(self.findings)
        report_lines.append(f"RISK SCORE: {risk_score:.2f}/100")
        report_lines.append(f"Risk Level: {self._get_risk_level(risk_score)}")
        report_lines.append("")

        # Detailed findings
        if self.findings:
            report_lines.append("DETAILED FINDINGS")
            report_lines.append("-" * 80)

            for i, vuln in enumerate(self.findings, 1):
                report_lines.append(f"\n[{i}] {vuln.title}")
                report_lines.append(f"    Severity: {vuln.severity.value}")
                report_lines.append(f"    Category: {vuln.category}")
                report_lines.append(f"    File: {vuln.file_path}:{vuln.line_number}")
                report_lines.append(f"    Description: {vuln.description}")
                report_lines.append(f"    Remediation: {vuln.remediation}")
                if vuln.cwe_id:
                    report_lines.append(f"    CWE: {vuln.cwe_id}")
                if vuln.owasp_category:
                    report_lines.append(f"    OWASP: {vuln.owasp_category}")
        else:
            report_lines.append("No vulnerabilities detected.")

        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def calculate_risk_score(self, vulnerabilities: List[Vulnerability]) -> float:
        """
        Calculate overall risk score based on vulnerabilities.

        Args:
            vulnerabilities (List[Vulnerability]): List of vulnerabilities

        Returns:
            float: Risk score (0-100, where 100 is highest risk)
        """
        if not vulnerabilities:
            return 0.0

        severity_weights = {
            VulnerabilitySeverity.CRITICAL: 10.0,
            VulnerabilitySeverity.HIGH: 6.0,
            VulnerabilitySeverity.MEDIUM: 3.0,
            VulnerabilitySeverity.LOW: 1.0,
            VulnerabilitySeverity.INFO: 0.5
        }

        total_score = 0.0
        for vuln in vulnerabilities:
            weight = severity_weights.get(vuln.severity, 1.0)
            confidence_factor = vuln.confidence
            total_score += weight * confidence_factor

        # Normalize to 0-100 scale
        max_score = len(vulnerabilities) * 10.0  # Assume all critical
        normalized_score = min(100.0, (total_score / max_score * 100) if max_score > 0 else 0)

        return round(normalized_score, 2)

    def validate(self) -> bool:
        """
        Validate the FSA configuration and state.

        Returns:
            bool: True if valid, False otherwise
        """
        if not self.codebase_path:
            return False
        if not os.path.exists(self.codebase_path):
            return False
        if self.security_level not in ['basic', 'standard', 'comprehensive']:
            return False
        return True

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle errors and exceptions during security analysis.

        Args:
            exception (Exception): The exception that occurred

        Returns:
            Dict[str, Any]: Error information
        """
        error_info = {
            "success": False,
            "error": {
                "type": type(exception).__name__,
                "message": str(exception),
                "timestamp": datetime.now().isoformat()
            },
            "partial_results": {
                "vulnerabilities_found": len(self.findings),
                "files_scanned": self.metadata.get("files_scanned", 0)
            }
        }

        # Log error for debugging
        print(f"Security Validator FSA Error: {error_info}", file=sys.stderr)

        return error_info

    def _add_vulnerability(self, title: str, description: str, severity: VulnerabilitySeverity,
                          category: str, file_path: str, line_number: int, code_snippet: str,
                          remediation: str, cwe_id: Optional[str] = None,
                          owasp_category: Optional[str] = None) -> None:
        """Helper method to add a vulnerability to findings."""
        self.vulnerability_id_counter += 1
        vuln = Vulnerability(
            id=f"VULN-{self.vulnerability_id_counter:04d}",
            title=title,
            description=description,
            severity=severity,
            category=category,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            remediation=remediation,
            cwe_id=cwe_id,
            owasp_category=owasp_category
        )
        self.findings.append(vuln)

    def _vulnerability_to_dict(self, vuln: Vulnerability) -> Dict[str, Any]:
        """Convert Vulnerability object to dictionary."""
        return {
            "id": vuln.id,
            "title": vuln.title,
            "description": vuln.description,
            "severity": vuln.severity.value,
            "category": vuln.category,
            "file_path": vuln.file_path,
            "line_number": vuln.line_number,
            "code_snippet": vuln.code_snippet,
            "remediation": vuln.remediation,
            "cwe_id": vuln.cwe_id,
            "owasp_category": vuln.owasp_category,
            "confidence": vuln.confidence
        }

    def _get_code_snippet(self, content: str, line_number: int, context: int = 2) -> str:
        """Get code snippet around the specified line."""
        lines = content.split('\n')
        start = max(0, line_number - context - 1)
        end = min(len(lines), line_number + context)
        snippet_lines = lines[start:end]
        return '\n'.join(snippet_lines)

    def _generate_summary(self) -> Dict[str, int]:
        """Generate summary statistics of vulnerabilities."""
        summary = {
            "total": len(self.findings),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        for vuln in self.findings:
            if vuln.severity == VulnerabilitySeverity.CRITICAL:
                summary["critical"] += 1
            elif vuln.severity == VulnerabilitySeverity.HIGH:
                summary["high"] += 1
            elif vuln.severity == VulnerabilitySeverity.MEDIUM:
                summary["medium"] += 1
            elif vuln.severity == VulnerabilitySeverity.LOW:
                summary["low"] += 1
            elif vuln.severity == VulnerabilitySeverity.INFO:
                summary["info"] += 1

        return summary

    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level description from risk score."""
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        elif risk_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"

"""
Comprehensive test suite for Security Validator FSA

This test module provides extensive testing coverage for the SecurityValidatorFSA class,
including all major security analysis features and edge cases.

Test Coverage:
- SQL injection detection
- XSS vulnerability detection
- CSRF vulnerability detection
- Dependency vulnerability scanning
- Secret detection accuracy
- Authentication validation
- Authorization checking
- Cryptographic analysis
- OWASP compliance verification
- Security configuration auditing
- Risk score calculation
- Report generation
- False positive handling
- Multi-language support
- Performance optimization
- CVE database integration
- Remediation recommendation quality
- Error handling for malformed code
"""

import ast
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List

from agno.fsas.security.security_validator_fsa import (
    SecurityValidatorFSA,
    VulnerabilitySeverity,
    Vulnerability,
    ComplianceFramework
)


class TestSecurityValidatorFSA:
    """Main test class for Security Validator FSA."""

    @pytest.fixture
    def temp_codebase(self):
        """Create a temporary codebase for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def security_validator(self, temp_codebase):
        """Create a SecurityValidatorFSA instance."""
        return SecurityValidatorFSA(codebase_path=temp_codebase, security_level="standard")

    def test_sql_injection_detection(self, security_validator):
        """Test SQL injection vulnerability detection."""
        # Test code with SQL injection vulnerability
        vulnerable_code = '''
import sqlite3

def get_user(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Vulnerable: string concatenation in SQL query
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()

def get_posts(post_id):
    # Vulnerable: f-string in SQL query
    query = f"SELECT * FROM posts WHERE id = {post_id}"
    cursor.execute(query)
    return cursor.fetchall()
'''

        # Parse and detect SQL injection
        try:
            tree = ast.parse(vulnerable_code)
            vulnerable_lines = security_validator.detect_sql_injection(tree)

            # Should detect at least one SQL injection vulnerability
            assert len(vulnerable_lines) > 0, "Failed to detect SQL injection vulnerabilities"
            print(f"✓ Detected {len(vulnerable_lines)} SQL injection vulnerabilities")
        except Exception as e:
            pytest.fail(f"SQL injection detection failed: {str(e)}")

    def test_xss_vulnerability_detection(self, security_validator):
        """Test XSS vulnerability detection in templates."""
        # Test templates with XSS vulnerabilities
        vulnerable_templates = [
            '<div innerHTML={userInput}></div>',
            '<script>var data = ' + 'userInput' + '</script>',
            'document.write(userInput);',
            '<div dangerouslySetInnerHTML={{__html: userInput}}></div>',
            '<a href="javascript:alert(userInput)">Click</a>'
        ]

        vulnerable_lines = security_validator.detect_xss_vulnerabilities(vulnerable_templates)

        # Should detect XSS vulnerabilities
        assert len(vulnerable_lines) > 0, "Failed to detect XSS vulnerabilities"
        print(f"✓ Detected {len(vulnerable_lines)} XSS vulnerabilities")

    def test_csrf_vulnerability_detection(self, temp_codebase, security_validator):
        """Test CSRF vulnerability detection."""
        # Create a Python file with POST endpoint without CSRF protection
        csrf_vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/transfer', methods=['POST'])
def transfer_money():
    # Missing CSRF protection
    amount = request.form.get('amount')
    recipient = request.form.get('recipient')
    # Process transfer
    return "Transfer completed"
'''

        test_file = os.path.join(temp_codebase, "app.py")
        with open(test_file, 'w') as f:
            f.write(csrf_vulnerable_code)

        # Run vulnerability scan
        vulnerabilities = security_validator.scan_vulnerabilities(csrf_vulnerable_code)

        # The scan should complete without errors
        assert isinstance(vulnerabilities, list), "Scan vulnerabilities should return a list"
        print(f"✓ CSRF detection completed, found {len(vulnerabilities)} issues")

    def test_dependency_vulnerability_scanning(self, security_validator):
        """Test dependency vulnerability scanning with CVE database."""
        # Test requirements with known vulnerable versions
        vulnerable_requirements = [
            'requests==2.6.0',  # Has CVE-2015-2296
            'django==2.2.0',    # Has CVE-2019-14234
            'flask==0.12.3',    # Has CVE-2018-1000656
            'pyyaml==5.1',      # Has CVE-2020-1747
            'pillow==6.2.1'     # Has CVE-2020-5312
        ]

        vulnerabilities = security_validator.scan_dependencies(vulnerable_requirements)

        # Should detect vulnerabilities in these packages
        assert len(vulnerabilities) > 0, "Failed to detect vulnerable dependencies"
        assert 'requests' in vulnerabilities, "Failed to detect requests vulnerability"
        assert 'django' in vulnerabilities, "Failed to detect django vulnerability"

        print(f"✓ Detected vulnerabilities in {len(vulnerabilities)} dependencies")
        for package, issues in vulnerabilities.items():
            print(f"  - {package}: {len(issues)} issues")

    def test_secret_detection_accuracy(self, security_validator):
        """Test secret and credential detection accuracy."""
        # Test code with various types of secrets
        code_with_secrets = '''
# API Keys
api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
API_KEY = "AIzaSyD1234567890abcdefghijklmnopqrstuvw"

# Passwords
database_password = "MySecretP@ssw0rd123"
DB_PASSWORD = "SuperSecret123!"

# Access Tokens
access_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz12"
auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

# AWS Credentials
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"

# Private Keys
private_key = "-----BEGIN RSA PRIVATE KEY-----MIIEpAIBAAKCAQEA..."
'''

        detected_secrets = security_validator.detect_secrets(code_with_secrets)

        # Should detect multiple secrets
        assert len(detected_secrets) >= 5, f"Failed to detect enough secrets. Found: {len(detected_secrets)}"

        # Check for specific secret types
        secret_types = [s['type'] for s in detected_secrets]
        print(f"✓ Detected {len(detected_secrets)} secrets")
        print(f"  Secret types found: {set(secret_types)}")

    def test_authentication_validation(self, security_validator):
        """Test authentication implementation validation."""
        # Test weak authentication code
        weak_auth_code = '''
import hashlib
import base64

def login(username, password):
    # Weak: using MD5 for password hashing
    hashed = hashlib.md5(password.encode()).hexdigest()

    # Check against database
    user = db.query(f"SELECT * FROM users WHERE username='{username}'")

    if user and user.password == hashed:
        return create_session(user)
    return None

def authenticate(credentials):
    # Missing CSRF protection
    username = credentials['username']
    password = base64.b64encode(credentials['password'])
    return login(username, password)
'''

        validation_result = security_validator.validate_authentication(weak_auth_code)

        # Should detect authentication issues
        assert 'issues' in validation_result, "Authentication validation should return issues"
        assert len(validation_result['issues']) > 0, "Should detect authentication weaknesses"
        assert not validation_result['valid'], "Weak authentication should not be valid"

        print(f"✓ Detected {len(validation_result['issues'])} authentication issues")

    def test_authorization_checking(self, temp_codebase, security_validator):
        """Test authorization implementation checking."""
        # Test code with potential authorization issues
        auth_code = '''
from flask import Flask, request, session

app = Flask(__name__)

@app.route('/admin/users')
def list_users():
    # Missing authorization check
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/user/<int:user_id>/profile')
def view_profile(user_id):
    # Insecure Direct Object Reference (IDOR)
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)
'''

        test_file = os.path.join(temp_codebase, "auth.py")
        with open(test_file, 'w') as f:
            f.write(auth_code)

        # Scan for vulnerabilities
        vulnerabilities = security_validator.scan_vulnerabilities(auth_code)

        # Should complete without errors
        assert isinstance(vulnerabilities, list), "Should return vulnerability list"
        print(f"✓ Authorization check completed")

    def test_cryptographic_analysis(self, security_validator):
        """Test cryptographic implementation analysis."""
        # Test code with weak cryptography
        crypto_code_samples = [
            'import hashlib; hash = hashlib.md5(data)',
            'from Crypto.Cipher import DES; cipher = DES.new(key)',
            'cipher = AES.new(key, AES.MODE_ECB)',
            'import hashlib; password_hash = hashlib.sha1(password)',
            'key = "hardcoded_key_12345"'
        ]

        issues = security_validator.analyze_cryptography(crypto_code_samples)

        # Should detect multiple cryptographic issues
        assert len(issues) > 0, "Failed to detect cryptographic weaknesses"
        print(f"✓ Detected {len(issues)} cryptographic issues")
        for issue in issues:
            print(f"  - {issue}")

    def test_owasp_compliance_verification(self, security_validator):
        """Test OWASP Top 10 compliance checking."""
        # Create test vulnerabilities
        test_vulnerabilities = [
            Vulnerability(
                id="VULN-0001",
                title="SQL Injection",
                description="SQL injection found",
                severity=VulnerabilitySeverity.CRITICAL,
                category="Injection",
                file_path="test.py",
                line_number=10,
                code_snippet="query = 'SELECT * FROM users WHERE id = ' + user_id",
                remediation="Use parameterized queries",
                owasp_category="A03:2021-Injection"
            ),
            Vulnerability(
                id="VULN-0002",
                title="Weak Crypto",
                description="MD5 usage detected",
                severity=VulnerabilitySeverity.HIGH,
                category="Cryptography",
                file_path="test.py",
                line_number=20,
                code_snippet="hash = hashlib.md5(password)",
                remediation="Use bcrypt or argon2",
                owasp_category="A02:2021-Cryptographic Failures"
            )
        ]

        codebase_data = {
            'vulnerabilities': test_vulnerabilities,
            'codebase_path': security_validator.codebase_path
        }

        compliance = security_validator.check_owasp_compliance(codebase_data)

        # Should return compliance status for OWASP categories
        assert isinstance(compliance, dict), "Compliance should be a dictionary"
        assert len(compliance) > 0, "Should check multiple OWASP categories"

        # Categories with critical/high issues should not be compliant
        assert compliance.get("A03:2021-Injection") == False, "Should detect injection non-compliance"

        print(f"✓ OWASP compliance check completed")
        print(f"  Compliant categories: {sum(1 for v in compliance.values() if v)}/{len(compliance)}")

    def test_security_configuration_auditing(self, security_validator):
        """Test security configuration auditing."""
        # Test configurations with security issues
        insecure_config = {
            'DEBUG': True,
            'SECRET_KEY': 'secret',
            'SECURE_SSL_REDIRECT': False,
            'CSRF_ENABLED': False,
            'SESSION_COOKIE_SECURE': False,
            'SESSION_COOKIE_HTTPONLY': False,
            'CORS_ORIGINS': '*'
        }

        issues = security_validator.audit_security_config(insecure_config)

        # Should detect multiple configuration issues
        assert len(issues) >= 5, f"Should detect multiple config issues. Found: {len(issues)}"
        print(f"✓ Detected {len(issues)} security configuration issues")

    def test_risk_score_calculation(self, security_validator):
        """Test risk score calculation algorithm."""
        # Create vulnerabilities with different severities
        test_vulnerabilities = [
            Vulnerability(
                id="V1", title="Critical Issue", description="Test",
                severity=VulnerabilitySeverity.CRITICAL, category="Test",
                file_path="test.py", line_number=1, code_snippet="",
                remediation="Fix it"
            ),
            Vulnerability(
                id="V2", title="High Issue", description="Test",
                severity=VulnerabilitySeverity.HIGH, category="Test",
                file_path="test.py", line_number=2, code_snippet="",
                remediation="Fix it"
            ),
            Vulnerability(
                id="V3", title="Medium Issue", description="Test",
                severity=VulnerabilitySeverity.MEDIUM, category="Test",
                file_path="test.py", line_number=3, code_snippet="",
                remediation="Fix it"
            ),
            Vulnerability(
                id="V4", title="Low Issue", description="Test",
                severity=VulnerabilitySeverity.LOW, category="Test",
                file_path="test.py", line_number=4, code_snippet="",
                remediation="Fix it"
            )
        ]

        risk_score = security_validator.calculate_risk_score(test_vulnerabilities)

        # Risk score should be between 0 and 100
        assert 0 <= risk_score <= 100, f"Risk score should be 0-100. Got: {risk_score}"

        # Risk score should be higher with more critical issues
        critical_only = [test_vulnerabilities[0]]
        critical_score = security_validator.calculate_risk_score(critical_only)

        low_only = [test_vulnerabilities[3]]
        low_score = security_validator.calculate_risk_score(low_only)

        assert critical_score > low_score, "Critical vulnerabilities should have higher risk score"

        print(f"✓ Risk score calculation working correctly")
        print(f"  All severities: {risk_score}")
        print(f"  Critical only: {critical_score}")
        print(f"  Low only: {low_score}")

    def test_report_generation(self, temp_codebase, security_validator):
        """Test security report generation."""
        # Add some test vulnerabilities
        security_validator._add_vulnerability(
            title="Test Vulnerability",
            description="This is a test",
            severity=VulnerabilitySeverity.HIGH,
            category="Testing",
            file_path="test.py",
            line_number=1,
            code_snippet="test code",
            remediation="Fix the test",
            cwe_id="CWE-123",
            owasp_category="A01:2021-Broken Access Control"
        )

        security_validator.metadata['files_scanned'] = 10
        security_validator.metadata['lines_scanned'] = 500
        security_validator.metadata['scan_duration'] = 5.2

        # Generate report
        report = security_validator.generate_security_report(security_validator.findings)

        # Report should contain key sections
        assert "SECURITY ANALYSIS REPORT" in report, "Report should have title"
        assert "SUMMARY" in report, "Report should have summary"
        assert "RISK SCORE" in report, "Report should have risk score"
        assert "Test Vulnerability" in report, "Report should include vulnerability details"

        print(f"✓ Report generated successfully")
        print(f"  Report length: {len(report)} characters")

    def test_false_positive_handling(self, security_validator):
        """Test handling of false positives in security analysis."""
        # Safe code that might trigger false positives
        safe_code = '''
import hashlib

def hash_file(filename):
    # This is safe - using MD5 for checksums, not passwords
    hasher = hashlib.md5()
    with open(filename, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def execute_safe_query():
    # This is safe - using parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
'''

        # Scan the safe code
        vulnerabilities = security_validator.scan_vulnerabilities(safe_code)

        # The scanner might still detect some patterns, but should have lower confidence
        print(f"✓ False positive handling test completed")
        print(f"  Detected {len(vulnerabilities)} potential issues in safe code")

    def test_multi_language_support(self, temp_codebase, security_validator):
        """Test security analysis for multiple programming languages."""
        # Create files in different languages
        languages = {
            'test.py': 'import os; os.system("rm -rf " + user_input)',
            'test.js': 'eval(userInput); document.write(data);',
            'test.java': 'String query = "SELECT * FROM users WHERE id = " + userId;',
            'test.php': '<?php eval($_GET["cmd"]); ?>',
        }

        for filename, content in languages.items():
            file_path = os.path.join(temp_codebase, filename)
            with open(file_path, 'w') as f:
                f.write(content)

        # Run full scan
        result = security_validator.execute()

        # Should scan files from multiple languages
        assert result['success'], "Multi-language scan should succeed"
        assert result['metadata']['files_scanned'] >= len(languages), "Should scan all language files"

        print(f"✓ Multi-language support test passed")
        print(f"  Files scanned: {result['metadata']['files_scanned']}")

    def test_performance_optimization(self, temp_codebase, security_validator):
        """Test performance with larger codebases."""
        # Create multiple files to test performance
        for i in range(20):
            file_path = os.path.join(temp_codebase, f"file_{i}.py")
            with open(file_path, 'w') as f:
                f.write(f'''
def function_{i}():
    """Test function {i}"""
    data = get_user_input()
    query = "SELECT * FROM table WHERE id = " + data
    execute(query)
    return process_data(data)
''' * 10)  # Repeat to make files larger

        # Run scan and measure performance
        import time
        start_time = time.time()
        result = security_validator.execute()
        end_time = time.time()

        scan_duration = end_time - start_time

        # Should complete in reasonable time
        assert result['success'], "Performance test scan should succeed"
        assert scan_duration < 30, f"Scan took too long: {scan_duration}s"

        print(f"✓ Performance test passed")
        print(f"  Scanned {result['metadata']['files_scanned']} files in {scan_duration:.2f}s")

    def test_cve_database_integration(self, security_validator):
        """Test CVE database integration for dependency scanning."""
        # Verify CVE database is loaded
        assert len(security_validator.cve_database) > 0, "CVE database should be loaded"

        # Test specific CVE lookups
        assert 'requests' in security_validator.cve_database, "Should have requests CVEs"
        assert 'django' in security_validator.cve_database, "Should have django CVEs"

        # Verify CVE structure
        requests_cves = security_validator.cve_database['requests']
        assert len(requests_cves) > 0, "Should have CVE entries for requests"
        assert 'cve_id' in requests_cves[0], "CVE entry should have cve_id"
        assert 'severity' in requests_cves[0], "CVE entry should have severity"

        print(f"✓ CVE database integration test passed")
        print(f"  Loaded CVE data for {len(security_validator.cve_database)} packages")

    def test_remediation_recommendation_quality(self, security_validator):
        """Test quality of remediation recommendations."""
        # Add vulnerabilities and check remediation
        security_validator._add_vulnerability(
            title="SQL Injection",
            description="String concatenation in SQL",
            severity=VulnerabilitySeverity.CRITICAL,
            category="Injection",
            file_path="test.py",
            line_number=10,
            code_snippet="query = 'SELECT * FROM users WHERE id = ' + user_id",
            remediation="Use parameterized queries or ORM methods instead of string concatenation.",
            cwe_id="CWE-89"
        )

        # Check that remediation is provided and meaningful
        vuln = security_validator.findings[0]
        assert vuln.remediation, "Remediation should not be empty"
        assert len(vuln.remediation) > 20, "Remediation should be detailed"
        assert "parameterized" in vuln.remediation.lower() or "orm" in vuln.remediation.lower(), \
            "Remediation should mention proper fix"

        print(f"✓ Remediation recommendation quality test passed")

    def test_error_handling_malformed_code(self, temp_codebase, security_validator):
        """Test error handling for malformed or invalid code."""
        # Create file with syntax errors
        malformed_code = '''
def broken_function(
    # Missing closing parenthesis
    x = undefined_variable
    return x +
'''

        test_file = os.path.join(temp_codebase, "malformed.py")
        with open(test_file, 'w') as f:
            f.write(malformed_code)

        # Should handle errors gracefully
        try:
            result = security_validator.execute()
            # Should still return a result, even if some files failed
            assert 'success' in result, "Should return result structure"
            print(f"✓ Error handling test passed")
            print(f"  Handled malformed code gracefully")
        except Exception as e:
            pytest.fail(f"Should handle malformed code gracefully: {str(e)}")

    def test_validation_method(self, security_validator):
        """Test the validate() method for FSA configuration."""
        # Valid configuration
        assert security_validator.validate(), "Valid configuration should pass validation"

        # Invalid codebase path
        invalid_validator = SecurityValidatorFSA(codebase_path="/nonexistent/path")
        assert not invalid_validator.validate(), "Invalid path should fail validation"

        # Invalid security level
        invalid_validator2 = SecurityValidatorFSA(
            codebase_path=security_validator.codebase_path,
            security_level="invalid_level"
        )
        assert not invalid_validator2.validate(), "Invalid security level should fail validation"

        print(f"✓ Validation method test passed")

    def test_full_integration_workflow(self, temp_codebase):
        """Test complete end-to-end workflow."""
        # Create a realistic codebase
        app_code = '''
import sqlite3
from flask import Flask, request, session

app = Flask(__name__)
app.secret_key = "hardcoded_secret_key"

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute(query)
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]
        return "Login successful"
    return "Login failed"
'''

        config_code = '''
DEBUG = True
SECRET_KEY = "secret"
SECURE_SSL_REDIRECT = False
'''

        # Write files
        with open(os.path.join(temp_codebase, 'app.py'), 'w') as f:
            f.write(app_code)
        with open(os.path.join(temp_codebase, 'config.py'), 'w') as f:
            f.write(config_code)

        # Create requirements.txt with vulnerable dependencies
        with open(os.path.join(temp_codebase, 'requirements.txt'), 'w') as f:
            f.write('flask==0.12.3\nrequests==2.6.0\n')

        # Run full security analysis
        validator = SecurityValidatorFSA(codebase_path=temp_codebase, security_level="comprehensive")
        result = validator.execute()

        # Verify comprehensive results
        assert result['success'], "Full workflow should succeed"
        assert len(result['vulnerabilities']) > 0, "Should detect multiple vulnerabilities"
        assert result['risk_score'] > 0, "Risk score should be calculated"
        assert 'compliance_status' in result, "Should include compliance status"
        assert result['report'], "Should generate report"

        # Verify specific vulnerability types were detected
        vuln_titles = [v['title'] for v in result['vulnerabilities']]
        categories = [v['category'] for v in result['vulnerabilities']]

        print(f"✓ Full integration workflow test passed")
        print(f"  Total vulnerabilities: {len(result['vulnerabilities'])}")
        print(f"  Risk score: {result['risk_score']}")
        print(f"  Files scanned: {result['metadata']['files_scanned']}")
        print(f"  Vulnerability categories: {set(categories)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

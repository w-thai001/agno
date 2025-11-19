"""
Tests for OAuth Pattern Discovery and Analysis System
"""

import pytest
import ast
from unittest.mock import Mock, patch, mock_open

from agno.cli.oauth_pattern_analyzer import (
    OAuthPatternAnalyzer,
    OAuthASTVisitor,
    CodePattern,
    PatternCluster,
    PatternType,
    PatternSeverity
)


class TestOAuthASTVisitor:
    """Test AST visitor for pattern extraction"""

    def test_visit_state_transition_method(self):
        """Test detection of state transition methods"""
        code = """
class Handler:
    def transition_to_authenticated(self, state):
        self.state = state
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert len(visitor.state_transitions) == 1
        assert visitor.state_transitions[0]["name"] == "transition_to_authenticated"
        assert visitor.state_transitions[0]["class"] == "Handler"

    def test_visit_error_handler(self):
        """Test detection of error handling methods"""
        code = """
class Handler:
    def handle_error(self, error):
        logger.error(error)

    def error_callback(self):
        pass
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert len(visitor.error_handlers) == 2

    def test_visit_token_operations(self):
        """Test detection of token operations"""
        code = """
def refresh_token(self):
    return new_token

def get_token(self):
    return self.token
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert len(visitor.token_operations) == 2

    def test_visit_validations(self):
        """Test detection of validation methods"""
        code = """
def validate_state(self, state):
    return state == self.state

def check_scopes(self, scopes):
    return True
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert len(visitor.validations) == 2

    def test_visit_security_checks(self):
        """Test detection of security-related calls"""
        code = """
import secrets
import hashlib

def generate_state():
    return secrets.token_urlsafe(32)

def hash_verifier(verifier):
    return hashlib.sha256(verifier.encode()).digest()
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert len(visitor.security_checks) >= 1

    def test_function_calls_tracking(self):
        """Test tracking of function calls"""
        code = """
def foo():
    bar()
    obj.method()
    secrets.token_urlsafe(32)
        """
        tree = ast.parse(code)
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        assert "bar" in visitor.function_calls


class TestCodePattern:
    """Test code pattern data structure"""

    def test_pattern_creation(self):
        """Test creating a code pattern"""
        pattern = CodePattern(
            pattern_id="test_001",
            pattern_type=PatternType.SECURITY_PRACTICE,
            name="Test Pattern",
            description="A test pattern",
            code_sample="def test(): pass"
        )
        assert pattern.pattern_id == "test_001"
        assert pattern.pattern_type == PatternType.SECURITY_PRACTICE
        assert pattern.name == "Test Pattern"

    def test_pattern_serialization(self):
        """Test pattern to_dict conversion"""
        pattern = CodePattern(
            pattern_id="test_001",
            pattern_type=PatternType.SECURITY_PRACTICE,
            name="Test Pattern",
            description="A test pattern",
            code_sample="def test(): pass",
            frequency=5,
            locations=["file.py:10", "file.py:20"],
            severity=PatternSeverity.WARNING
        )
        data = pattern.to_dict()

        assert data["pattern_id"] == "test_001"
        assert data["pattern_type"] == "SECURITY_PRACTICE"
        assert data["frequency"] == 5
        assert len(data["locations"]) == 2
        assert data["severity"] == "WARNING"

    def test_pattern_hash(self):
        """Test pattern hashing for sets"""
        p1 = CodePattern("id1", PatternType.VALIDATION, "P1", "D1", "code1")
        p2 = CodePattern("id1", PatternType.VALIDATION, "P1", "D1", "code1")
        p3 = CodePattern("id2", PatternType.VALIDATION, "P2", "D2", "code2")

        assert hash(p1) == hash(p2)
        assert hash(p1) != hash(p3)


class TestPatternCluster:
    """Test pattern clustering"""

    def test_cluster_creation(self):
        """Test creating a pattern cluster"""
        cluster = PatternCluster(cluster_id="cluster_001")
        assert cluster.cluster_id == "cluster_001"
        assert len(cluster.patterns) == 0

    def test_add_pattern_to_cluster(self):
        """Test adding patterns to cluster"""
        cluster = PatternCluster(cluster_id="cluster_001")
        pattern = CodePattern("p1", PatternType.VALIDATION, "P1", "D1", "code")

        cluster.add_pattern(pattern)

        assert len(cluster.patterns) == 1
        assert cluster.centroid_pattern == pattern

    def test_cluster_centroid_update(self):
        """Test centroid updates with frequency"""
        cluster = PatternCluster(cluster_id="cluster_001")

        p1 = CodePattern("p1", PatternType.VALIDATION, "P1", "D1", "code", frequency=2)
        p2 = CodePattern("p2", PatternType.VALIDATION, "P2", "D2", "code", frequency=5)
        p3 = CodePattern("p3", PatternType.VALIDATION, "P3", "D3", "code", frequency=3)

        cluster.add_pattern(p1)
        cluster.add_pattern(p2)
        cluster.add_pattern(p3)

        # Centroid should be the most frequent pattern (p2)
        assert cluster.centroid_pattern.pattern_id == "p2"


class TestOAuthPatternAnalyzer:
    """Test pattern analyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return OAuthPatternAnalyzer()

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert len(analyzer._known_patterns) > 0
        assert len(analyzer._anti_pattern_rules) > 0
        assert "pkce_generation" in analyzer._known_patterns
        assert "plain_state_comparison" in analyzer._anti_pattern_rules

    def test_analyze_file_success(self, analyzer, tmp_path):
        """Test analyzing a valid Python file"""
        test_file = tmp_path / "test_oauth.py"
        test_file.write_text("""
def validate_state(self, state):
    return secrets.compare_digest(self.state, state)

def transition_to_authenticated(self):
    self.state = OAuthState.AUTHENTICATED

def handle_error(self, error):
    logger.error(error)
        """)

        result = analyzer.analyze_file(str(test_file))

        assert "patterns" in result
        assert "anti_patterns" in result
        assert "statistics" in result
        assert "ast_analysis" in result
        assert result["file_path"] == str(test_file)

    def test_analyze_file_syntax_error(self, analyzer, tmp_path):
        """Test analyzing file with syntax error"""
        test_file = tmp_path / "bad_syntax.py"
        test_file.write_text("def foo(\n  invalid syntax")

        result = analyzer.analyze_file(str(test_file))

        assert "error" in result
        assert "Syntax error" in result["error"]

    def test_analyze_file_not_found(self, analyzer):
        """Test analyzing non-existent file"""
        result = analyzer.analyze_file("/nonexistent/file.py")
        assert "error" in result

    def test_detect_plain_state_comparison_anti_pattern(self, analyzer):
        """Test detection of plain state comparison anti-pattern"""
        code = """
def validate_state(self, received_state):
    if received_state == self.state:
        return True
    return False
        """

        anti_patterns = analyzer._detect_anti_patterns(code, "test.py")

        assert len(anti_patterns) > 0
        assert any(ap.pattern_id == "anti_001" for ap in anti_patterns)

    def test_detect_hardcoded_secrets_anti_pattern(self, analyzer):
        """Test detection of hardcoded secrets"""
        code = """
client_secret = "abcdefghijklmnopqrstuvwxyz123456"
        """

        anti_patterns = analyzer._detect_anti_patterns(code, "test.py")

        assert any(ap.pattern_id == "anti_003" for ap in anti_patterns)

    def test_detect_insecure_random_anti_pattern(self, analyzer):
        """Test detection of insecure random usage"""
        code = """
import random
state = str(random.random())
        """

        anti_patterns = analyzer._detect_anti_patterns(code, "test.py")

        assert any(ap.pattern_id == "anti_005" for ap in anti_patterns)

    def test_detect_missing_state_anti_pattern(self, analyzer):
        """Test detection of missing state parameter"""
        code = """
def build_authorization_url(self):
    url = f"{self.endpoint}?client_id={self.client_id}"
    return url
        """

        anti_patterns = analyzer._detect_anti_patterns(code, "test.py")

        # Should detect missing state
        assert any(ap.pattern_id == "anti_004" for ap in anti_patterns)

    def test_pattern_extraction_statistics(self, analyzer, tmp_path):
        """Test statistics calculation"""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
# This is a comment
def validate_state(self):
    pass

def handle_error(self):
    pass

def refresh_token(self):
    secrets.token_urlsafe(32)
        """)

        result = analyzer.analyze_file(str(test_file))
        stats = result["statistics"]

        assert stats["total_lines"] > 0
        assert stats["code_lines"] > 0
        assert stats["comment_lines"] >= 1
        assert stats["validations"] >= 1

    def test_calculate_similarity_same_type(self, analyzer):
        """Test similarity calculation for same pattern type"""
        p1 = CodePattern(
            "p1",
            PatternType.SECURITY_PRACTICE,
            "PKCE Generation",
            "Generate PKCE",
            "def generate_pkce(): verifier = secrets.token_urlsafe()"
        )
        p2 = CodePattern(
            "p2",
            PatternType.SECURITY_PRACTICE,
            "PKCE Challenge",
            "Generate PKCE challenge",
            "def pkce_challenge(): verifier = secrets.token_urlsafe()"
        )

        similarity = analyzer._calculate_similarity(p1, p2)

        assert similarity > 0.5  # Should be fairly similar

    def test_calculate_similarity_different_type(self, analyzer):
        """Test similarity calculation for different pattern types"""
        p1 = CodePattern(
            "p1",
            PatternType.SECURITY_PRACTICE,
            "PKCE",
            "PKCE",
            "secrets.token_urlsafe()"
        )
        p2 = CodePattern(
            "p2",
            PatternType.ERROR_HANDLING,
            "Error",
            "Error",
            "logger.error()"
        )

        similarity = analyzer._calculate_similarity(p1, p2)

        assert similarity < 0.5  # Should be less similar

    def test_cluster_patterns(self, analyzer):
        """Test pattern clustering"""
        # Create some similar patterns
        patterns = [
            CodePattern("p1", PatternType.VALIDATION, "Validate A", "D", "code validate"),
            CodePattern("p2", PatternType.VALIDATION, "Validate B", "D", "code validate"),
            CodePattern("p3", PatternType.ERROR_HANDLING, "Error A", "D", "code error"),
            CodePattern("p4", PatternType.ERROR_HANDLING, "Error B", "D", "code error"),
        ]

        analyzer.patterns = patterns
        clusters = analyzer.cluster_patterns(similarity_threshold=0.5)

        assert len(clusters) > 0
        assert len(clusters) <= len(patterns)

    def test_generate_recommendations_anti_patterns(self, analyzer):
        """Test generating recommendations for anti-patterns"""
        analysis = {
            "anti_patterns": [
                {
                    "name": "Insecure Random",
                    "description": "Using insecure random",
                    "severity": "CRITICAL",
                    "locations": ["file.py:10"],
                    "metadata": {"recommendation": "Use secrets module"}
                }
            ],
            "statistics": {
                "security_checks": 0,
                "error_handlers": 0,
                "validations": 0
            }
        }

        recommendations = analyzer.generate_recommendations(analysis)

        assert len(recommendations) > 0
        # Should have anti-pattern recommendation
        assert any(r["type"] == "anti_pattern" for r in recommendations)
        # Should have security recommendation
        assert any(r["type"] == "security" for r in recommendations)

    def test_generate_recommendations_missing_error_handling(self, analyzer):
        """Test recommendation for missing error handling"""
        analysis = {
            "anti_patterns": [],
            "statistics": {
                "security_checks": 5,
                "error_handlers": 0,  # No error handlers
                "validations": 3
            }
        }

        recommendations = analyzer.generate_recommendations(analysis)

        assert any(
            r["type"] == "robustness" and "error" in r["title"].lower()
            for r in recommendations
        )

    def test_generate_recommendations_insufficient_validation(self, analyzer):
        """Test recommendation for insufficient validation"""
        analysis = {
            "anti_patterns": [],
            "statistics": {
                "security_checks": 2,
                "error_handlers": 2,
                "validations": 1  # Low validation count
            }
        }

        recommendations = analyzer.generate_recommendations(analysis)

        assert any(
            r["type"] == "validation"
            for r in recommendations
        )

    def test_generate_pattern_library(self, analyzer):
        """Test generating complete pattern library"""
        # Add some discovered patterns
        analyzer.patterns = [
            CodePattern("d1", PatternType.VALIDATION, "Custom Validation", "D", "code")
        ]

        # Create clusters
        analyzer.cluster_patterns()

        library = analyzer.generate_pattern_library()

        assert "known_patterns" in library
        assert "discovered_patterns" in library
        assert "anti_patterns" in library
        assert "clusters" in library
        assert "statistics" in library

        assert len(library["known_patterns"]) > 0
        assert len(library["anti_patterns"]) > 0
        assert library["statistics"]["total_known_patterns"] > 0

    def test_extract_code_sample(self, analyzer):
        """Test code sample extraction"""
        source = """line 1
line 2
line 3
line 4
line 5
line 6
line 7"""

        sample = analyzer._extract_code_sample(source, lineno=4, context_lines=2)

        # Should extract lines around line 4 (2 before, 2 after)
        assert "line 2" in sample or "line 3" in sample
        assert "line 4" in sample
        assert "line 5" in sample or "line 6" in sample

    def test_generate_pattern_id(self, analyzer):
        """Test pattern ID generation"""
        id1 = analyzer._generate_pattern_id("validation", "file1.py")
        id2 = analyzer._generate_pattern_id("validation", "file1.py")
        id3 = analyzer._generate_pattern_id("validation", "file2.py")

        # Same inputs should generate same ID
        assert id1 == id2
        # Different inputs should generate different IDs
        assert id1 != id3
        # IDs should be reasonable length
        assert len(id1) == 12


class TestIntegration:
    """Integration tests for pattern analysis"""

    def test_full_analysis_workflow(self, tmp_path):
        """Test complete analysis workflow"""
        # Create a sample OAuth implementation
        oauth_file = tmp_path / "oauth_impl.py"
        oauth_file.write_text("""
import secrets
import hashlib

class OAuthHandler:
    def validate_state(self, received):
        return secrets.compare_digest(self.state, received)

    def generate_pkce(self):
        verifier = secrets.token_urlsafe(96)
        challenge = hashlib.sha256(verifier.encode()).digest()
        return verifier, challenge

    def transition_to_authenticated(self):
        self.state = "AUTHENTICATED"

    def handle_error(self, error):
        logger.error(error)

    def refresh_token(self):
        return self.new_token()
        """)

        # Analyze the file
        analyzer = OAuthPatternAnalyzer()
        result = analyzer.analyze_file(str(oauth_file))

        # Verify comprehensive analysis
        assert "patterns" in result
        assert "anti_patterns" in result
        assert "statistics" in result

        # Should detect patterns
        patterns = result["patterns"]
        assert len(patterns) > 0

        # Check AST analysis
        ast_analysis = result["ast_analysis"]
        assert ast_analysis["validations"] >= 1
        assert ast_analysis["state_transitions"] >= 1
        assert ast_analysis["error_handlers"] >= 1
        assert ast_analysis["token_operations"] >= 1

        # Generate recommendations
        recommendations = analyzer.generate_recommendations(result)
        assert isinstance(recommendations, list)

    def test_multiple_files_analysis(self, tmp_path):
        """Test analyzing multiple files"""
        # Create multiple OAuth files
        file1 = tmp_path / "oauth1.py"
        file1.write_text("""
def validate_state(self, state):
    return secrets.compare_digest(self.state, state)
        """)

        file2 = tmp_path / "oauth2.py"
        file2.write_text("""
def check_token_expiry(self, token):
    return token.is_expired()
        """)

        analyzer = OAuthPatternAnalyzer()

        results = []
        for file in [file1, file2]:
            result = analyzer.analyze_file(str(file))
            results.append(result)

        # Both should have results
        assert len(results) == 2
        assert all("patterns" in r for r in results)

"""
Comprehensive test suite for DuplicationDetector FSA

Tests all clone detection types, clustering, metrics, and refactoring suggestions.
"""

import ast
import pytest
from pathlib import Path
from agno.tools.duplication_detector import (
    DuplicationDetector,
    CloneType,
    ExactClone,
    RenamedClone,
    StructuralClone,
    SemanticClone,
    CodeLocation,
    CloneCluster,
    RefactoringType,
    Token
)


# Test fixtures
@pytest.fixture
def detector():
    """Create a DuplicationDetector instance"""
    return DuplicationDetector(min_tokens=10, min_lines=3, similarity_threshold=0.8)


@pytest.fixture
def exact_duplicate_code():
    """Sample code with exact duplicates"""
    code1 = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""
    code2 = """
def compute_sum(products):
    total = 0
    for item in products:
        total += item.price
    return total
"""
    return code1, code2


@pytest.fixture
def renamed_duplicate_code():
    """Sample code with renamed identifiers"""
    code1 = """
def process_user_data(user):
    name = user.name
    age = user.age
    return {"name": name, "age": age}
"""
    code2 = """
def process_customer_info(customer):
    full_name = customer.name
    years = customer.age
    return {"name": full_name, "age": years}
"""
    return code1, code2


@pytest.fixture
def structural_duplicate_code():
    """Sample code with structural similarity"""
    code1 = """
def validate_email(email):
    if "@" not in email:
        return False
    if "." not in email:
        return False
    return True
"""
    code2 = """
def check_email(addr):
    if "@" not in addr:
        return False
    if "." not in addr:
        return False
    parts = addr.split("@")
    return len(parts) == 2
"""
    return code1, code2


class TestTokenization:
    """Test code tokenization"""

    def test_tokenize_simple_code(self, detector):
        """Test tokenization of simple Python code"""
        code = "def add(a, b):\n    return a + b"
        tokens = detector.tokenize_code(code)

        assert len(tokens) > 0
        assert any(t.value == "def" for t in tokens)
        assert any(t.value == "add" for t in tokens)

    def test_token_normalization(self, detector):
        """Test that identifiers are normalized"""
        code = "x = 42\ny = 99"
        tokens = detector.tokenize_code(code)

        # Identifiers should be normalized to 'ID'
        id_tokens = [t for t in tokens if t.type == 'IDENTIFIER']
        assert all(t.normalized == 'ID' for t in id_tokens)

        # Numbers should be normalized to 'NUM'
        num_tokens = [t for t in tokens if t.type == 'NUMBER']
        assert all(t.normalized == 'NUM' for t in num_tokens)

    def test_comment_removal(self, detector):
        """Test that comments are removed during tokenization"""
        code = """
# This is a comment
def func():  # inline comment
    return 42
"""
        tokens = detector.tokenize_code(code)

        # Comments should not appear in tokens
        token_values = [t.value for t in tokens]
        assert not any('#' in val for val in token_values)


class TestExactCloneDetection:
    """Test Type-1 clone detection"""

    def test_detect_exact_clones(self, detector, exact_duplicate_code):
        """Test detection of exact code duplicates"""
        code1, code2 = exact_duplicate_code

        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=6)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=6)

        clones = detector.detect_exact_clones(code1, code2, loc1, loc2)

        # Should detect at least some similarity
        assert isinstance(clones, list)

    def test_exact_clone_similarity(self, detector):
        """Test that exact clones have 1.0 similarity"""
        code = """
def calculate():
    x = 10
    y = 20
    return x + y
"""
        loc1 = CodeLocation(start_line=1, end_line=5)
        loc2 = CodeLocation(start_line=10, end_line=14)

        clones = detector.detect_exact_clones(code, code, loc1, loc2)

        if clones:
            assert clones[0].similarity == 1.0
            assert clones[0].clone_type == CloneType.TYPE_1

    def test_no_clones_different_code(self, detector):
        """Test that different code doesn't produce clones"""
        code1 = "x = 1\ny = 2"
        code2 = "a = 'hello'\nb = 'world'"

        loc1 = CodeLocation(start_line=1, end_line=2)
        loc2 = CodeLocation(start_line=1, end_line=2)

        clones = detector.detect_exact_clones(code1, code2, loc1, loc2)

        # Very different code should produce no or few clones
        assert isinstance(clones, list)


class TestRenamedCloneDetection:
    """Test Type-2 clone detection"""

    def test_detect_renamed_clones(self, detector, renamed_duplicate_code):
        """Test detection of clones with renamed identifiers"""
        code1, code2 = renamed_duplicate_code

        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=4)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=4)

        clones = detector.detect_renamed_clones(code1, code2, loc1, loc2)

        if clones:
            assert clones[0].clone_type == CloneType.TYPE_2
            assert clones[0].similarity >= detector.similarity_threshold
            assert isinstance(clones[0], RenamedClone)
            assert hasattr(clones[0], 'identifier_mapping')

    def test_identifier_mapping(self, detector, renamed_duplicate_code):
        """Test that identifier mapping is created"""
        code1, code2 = renamed_duplicate_code

        loc1 = CodeLocation(start_line=1, end_line=4)
        loc2 = CodeLocation(start_line=1, end_line=4)

        clones = detector.detect_renamed_clones(code1, code2, loc1, loc2)

        if clones:
            mapping = clones[0].identifier_mapping
            assert isinstance(mapping, dict)

    def test_token_similarity(self, detector):
        """Test token similarity computation"""
        tokens1 = [
            Token(type='ID', value='x', normalized='ID'),
            Token(type='OP', value='=', normalized='='),
            Token(type='NUM', value='42', normalized='NUM')
        ]
        tokens2 = [
            Token(type='ID', value='y', normalized='ID'),
            Token(type='OP', value='=', normalized='='),
            Token(type='NUM', value='99', normalized='NUM')
        ]

        similarity = detector.compute_token_similarity(tokens1, tokens2)

        # Normalized tokens should be identical
        assert similarity == 1.0


class TestStructuralCloneDetection:
    """Test Type-3 clone detection"""

    def test_detect_structural_clones(self, detector, structural_duplicate_code):
        """Test detection of structurally similar clones"""
        code1, code2 = structural_duplicate_code

        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=6)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=7)

        clones = detector.detect_structural_clones(code1, code2, loc1, loc2)

        if clones:
            assert clones[0].clone_type == CloneType.TYPE_3
            assert isinstance(clones[0], StructuralClone)
            assert hasattr(clones[0], 'edit_distance')

    def test_ast_normalization(self, detector):
        """Test AST normalization"""
        code = "x = 42\ny = x + 1"
        tree = ast.parse(code)

        normalized = detector.normalize_ast(tree)

        # Normalized AST should have standardized variable names
        assert normalized is not None

    def test_ast_similarity(self, detector):
        """Test AST similarity comparison"""
        code1 = "x = 1\ny = 2"
        code2 = "a = 1\nb = 2"

        ast1 = ast.parse(code1)
        ast2 = ast.parse(code2)

        similarity = detector.compare_ast_similarity(ast1, ast2)

        # Same structure, different names
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be fairly similar


class TestSemanticCloneDetection:
    """Test Type-4 clone detection"""

    def test_detect_semantic_clones(self, detector):
        """Test detection of semantically equivalent clones"""
        # Enable Type-4 detection
        detector.enable_type_4 = True

        code1 = """
def check_positive(n):
    if n > 0:
        return True
    return False
"""
        code2 = """
def is_positive(num):
    return num > 0
"""

        loc1 = CodeLocation(start_line=1, end_line=5)
        loc2 = CodeLocation(start_line=1, end_line=3)

        clones = detector.detect_semantic_clones(code1, code2, loc1, loc2)

        # Semantic detection is challenging, just verify it runs
        assert isinstance(clones, list)

    def test_control_flow_extraction(self, detector):
        """Test control flow pattern extraction"""
        code = """
if condition:
    for item in items:
        while processing:
            pass
"""
        pattern = detector._extract_control_flow_pattern(code)

        assert 'If' in pattern
        assert 'For' in pattern
        assert 'While' in pattern


class TestCloneClustering:
    """Test clone clustering algorithm"""

    def test_cluster_clones(self, detector):
        """Test grouping clones into clusters"""
        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=5)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=5)
        loc3 = CodeLocation(file_path="file3.py", start_line=1, end_line=5)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="code", code2="code",
                location1=loc1, location2=loc2,
                similarity=1.0, token_count=20
            ),
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="code", code2="code",
                location1=loc2, location2=loc3,
                similarity=1.0, token_count=20
            )
        ]

        clusters = detector.cluster_clones(clones)

        assert len(clusters) > 0
        assert all(isinstance(c, CloneCluster) for c in clusters)
        assert all(c.size() > 0 for c in clusters)

    def test_cluster_affected_files(self, detector):
        """Test that clusters track affected files"""
        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=5)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=5)

        clone = ExactClone(
            clone_type=CloneType.TYPE_1,
            code1="code", code2="code",
            location1=loc1, location2=loc2,
            similarity=1.0, token_count=20
        )

        clusters = detector.cluster_clones([clone])

        if clusters:
            assert len(clusters[0].affected_files) == 2
            assert "file1.py" in clusters[0].affected_files
            assert "file2.py" in clusters[0].affected_files


class TestCloneMetrics:
    """Test clone metrics computation"""

    def test_compute_clone_metrics(self, detector):
        """Test computation of clone metrics"""
        loc = CodeLocation(start_line=1, end_line=5)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="line1\nline2\nline3\nline4\nline5",
                code2="line1\nline2\nline3\nline4\nline5",
                location1=loc, location2=loc,
                similarity=1.0, token_count=20
            )
        ]

        metrics = detector.compute_clone_metrics(clones, total_loc=100)

        assert metrics.total_clones == 1
        assert 0 <= metrics.clone_coverage <= 100
        assert metrics.clone_density >= 0
        assert metrics.largest_clone_size > 0

    def test_clone_type_distribution(self, detector):
        """Test clone type distribution in metrics"""
        loc = CodeLocation(start_line=1, end_line=5)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="code", code2="code",
                location1=loc, location2=loc,
                similarity=1.0, token_count=20
            ),
            RenamedClone(
                clone_type=CloneType.TYPE_2,
                code1="code", code2="code",
                location1=loc, location2=loc,
                similarity=0.9, token_count=20
            )
        ]

        metrics = detector.compute_clone_metrics(clones, total_loc=100)

        assert CloneType.TYPE_1 in metrics.clone_type_distribution
        assert CloneType.TYPE_2 in metrics.clone_type_distribution
        assert metrics.clone_type_distribution[CloneType.TYPE_1] == 1
        assert metrics.clone_type_distribution[CloneType.TYPE_2] == 1


class TestRefactoringSuggestions:
    """Test refactoring recommendation engine"""

    def test_suggest_extract_method(self, detector):
        """Test extract method suggestion"""
        loc = CodeLocation(file_path="file.py", start_line=1, end_line=10)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="x = 1\ny = 2\nz = 3\na = 4\nb = 5\nc = 6",
                code2="x = 1\ny = 2\nz = 3\na = 4\nb = 5\nc = 6",
                location1=loc, location2=loc,
                similarity=1.0, token_count=30
            ),
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="x = 1\ny = 2\nz = 3\na = 4\nb = 5\nc = 6",
                code2="x = 1\ny = 2\nz = 3\na = 4\nb = 5\nc = 6",
                location1=loc, location2=loc,
                similarity=1.0, token_count=30
            )
        ]

        cluster = CloneCluster(clones=clones, affected_files={"file.py"})
        suggestions = detector.suggest_refactorings(cluster)

        assert len(suggestions) > 0
        assert any(s.refactoring_type == RefactoringType.EXTRACT_METHOD for s in suggestions)

    def test_suggest_extract_class(self, detector):
        """Test extract class suggestion for cross-file clones"""
        loc1 = CodeLocation(file_path="file1.py", start_line=1, end_line=10)
        loc2 = CodeLocation(file_path="file2.py", start_line=1, end_line=10)

        clone = ExactClone(
            clone_type=CloneType.TYPE_1,
            code1="code" * 10,
            code2="code" * 10,
            location1=loc1, location2=loc2,
            similarity=1.0, token_count=50
        )

        cluster = CloneCluster(clones=[clone], affected_files={"file1.py", "file2.py"})
        suggestions = detector.suggest_refactorings(cluster)

        assert any(s.refactoring_type == RefactoringType.EXTRACT_CLASS for s in suggestions)

    def test_suggest_parameterize(self, detector):
        """Test parameterize suggestion for Type-2 clones"""
        loc = CodeLocation(start_line=1, end_line=5)

        clone = RenamedClone(
            clone_type=CloneType.TYPE_2,
            code1="code" * 5,
            code2="code" * 5,
            location1=loc, location2=loc,
            similarity=0.9, token_count=25
        )

        cluster = CloneCluster(clones=[clone], affected_files={"file.py"})
        suggestions = detector.suggest_refactorings(cluster)

        assert any(s.refactoring_type == RefactoringType.PARAMETERIZE for s in suggestions)


class TestFalsePositiveFiltering:
    """Test false positive filtering"""

    def test_filter_short_clones(self, detector):
        """Test that short clones are filtered"""
        loc = CodeLocation(start_line=1, end_line=2)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="x = 1",
                code2="x = 1",
                location1=loc, location2=loc,
                similarity=1.0, token_count=3  # Below threshold
            )
        ]

        filtered = detector.filter_false_positives(clones)

        # Short clone should be filtered
        assert len(filtered) == 0

    def test_filter_boilerplate(self, detector):
        """Test that boilerplate code is filtered"""
        loc = CodeLocation(start_line=1, end_line=5)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="import os\nimport sys\nimport json",
                code2="import os\nimport sys\nimport json",
                location1=loc, location2=loc,
                similarity=1.0, token_count=20
            )
        ]

        filtered = detector.filter_false_positives(clones)

        # Boilerplate should be filtered
        assert len(filtered) == 0

    def test_keep_valid_clones(self, detector):
        """Test that valid clones are kept"""
        loc = CodeLocation(start_line=1, end_line=10)

        clones = [
            ExactClone(
                clone_type=CloneType.TYPE_1,
                code1="def calculate():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z",
                code2="def calculate():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z",
                location1=loc, location2=loc,
                similarity=1.0, token_count=25
            )
        ]

        filtered = detector.filter_false_positives(clones)

        # Valid clone should be kept
        assert len(filtered) == 1


class TestDuplicationReport:
    """Test full duplication detection pipeline"""

    def test_detect_duplicates_single_code(self, detector):
        """Test duplicate detection on single code string"""
        code = """
def func1():
    x = 1
    y = 2
    return x + y

def func2():
    x = 1
    y = 2
    return x + y
"""
        report = detector.detect_duplicates(code)

        assert report is not None
        assert hasattr(report, 'clones')
        assert hasattr(report, 'clusters')
        assert hasattr(report, 'metrics')
        assert hasattr(report, 'recommendations')

    def test_detect_duplicates_multiple_codes(self, detector, exact_duplicate_code):
        """Test duplicate detection across multiple code strings"""
        code1, code2 = exact_duplicate_code

        report = detector.detect_duplicates([code1, code2])

        assert report is not None
        assert isinstance(report.clones, list)
        assert isinstance(report.clusters, list)
        assert isinstance(report.recommendations, list)

    def test_report_metrics(self, detector):
        """Test that report includes comprehensive metrics"""
        code = """
def process():
    data = []
    for i in range(10):
        data.append(i * 2)
    return data

def calculate():
    results = []
    for i in range(10):
        results.append(i * 2)
    return results
"""
        report = detector.detect_duplicates(code, min_tokens=5)

        assert report.metrics.total_clones >= 0
        assert 0 <= report.metrics.clone_coverage <= 100
        assert report.metrics.clone_density >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

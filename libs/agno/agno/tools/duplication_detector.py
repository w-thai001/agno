"""
Duplication Detector FSA - Advanced Code Clone Detection System

This module provides comprehensive code duplication detection using multiple algorithms:
- Type-1: Exact clones (identical code)
- Type-2: Renamed clones (same structure, different identifiers)
- Type-3: Structural clones (similar with modifications)
- Type-4: Semantic clones (different syntax, same behavior)

Key Features:
- Multi-algorithm clone detection
- Clone clustering and grouping
- Refactoring recommendation engine
- Clone metrics computation
- False positive filtering
- Visualization support
"""

import ast
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import difflib


class CloneType(Enum):
    """Types of code clones"""
    TYPE_1 = "exact"  # Identical code
    TYPE_2 = "renamed"  # Renamed identifiers
    TYPE_3 = "structural"  # Modified structure
    TYPE_4 = "semantic"  # Same semantics, different syntax


class RefactoringType(Enum):
    """Types of refactoring suggestions"""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    PARAMETERIZE = "parameterize"
    TEMPLATE_METHOD = "template_method"


@dataclass
class CodeLocation:
    """Location of code fragment"""
    file_path: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    start_col: int = 0
    end_col: int = 0

    def __str__(self) -> str:
        if self.file_path:
            return f"{self.file_path}:{self.start_line}-{self.end_line}"
        return f"lines {self.start_line}-{self.end_line}"


@dataclass
class Token:
    """Code token with type and value"""
    type: str
    value: str
    normalized: str  # Normalized value for comparison


@dataclass
class Clone:
    """Base class for code clones"""
    clone_type: CloneType
    code1: str
    code2: str
    location1: CodeLocation
    location2: CodeLocation
    similarity: float
    token_count: int = 0

    def size(self) -> int:
        """Get clone size in lines"""
        return len(self.code1.split('\n'))


@dataclass
class ExactClone(Clone):
    """Type-1 clone: identical code fragments"""
    def __post_init__(self):
        self.clone_type = CloneType.TYPE_1


@dataclass
class RenamedClone(Clone):
    """Type-2 clone: renamed identifiers"""
    identifier_mapping: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.clone_type = CloneType.TYPE_2


@dataclass
class StructuralClone(Clone):
    """Type-3 clone: structural similarity with modifications"""
    edit_distance: int = 0
    modifications: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.clone_type = CloneType.TYPE_3


@dataclass
class SemanticClone(Clone):
    """Type-4 clone: semantic equivalence"""
    equivalence_proof: str = ""

    def __post_init__(self):
        self.clone_type = CloneType.TYPE_4


@dataclass
class RefactoringSuggestion:
    """Refactoring recommendation for clone cluster"""
    refactoring_type: RefactoringType
    description: str
    benefit: str
    estimated_loc_reduction: int = 0
    confidence: float = 0.0


@dataclass
class CloneCluster:
    """Group of related clones"""
    clones: List[Clone]
    representative: Optional[Clone] = None
    affected_files: Set[str] = field(default_factory=set)

    def size(self) -> int:
        return len(self.clones)

    def total_duplicated_lines(self) -> int:
        return sum(c.size() for c in self.clones)


@dataclass
class CloneMetrics:
    """Metrics about code clones"""
    total_clones: int
    clone_coverage: float  # Percentage of duplicated code
    clone_density: float  # Clones per KLOC
    largest_clone_size: int
    clone_type_distribution: Dict[CloneType, int] = field(default_factory=dict)
    total_duplicated_lines: int = 0


@dataclass
class CloneEvolution:
    """Track clone evolution across versions"""
    new_clones: List[Clone] = field(default_factory=list)
    removed_clones: List[Clone] = field(default_factory=list)
    modified_clones: List[Clone] = field(default_factory=list)
    persistent_clones: List[Clone] = field(default_factory=list)


@dataclass
class DuplicationReport:
    """Complete duplication analysis report"""
    clones: List[Clone]
    clusters: List[CloneCluster]
    metrics: CloneMetrics
    recommendations: List[RefactoringSuggestion] = field(default_factory=list)
    analysis_timestamp: Optional[str] = None


class DuplicationDetector:
    """
    Advanced code duplication detector with multi-algorithm support.

    Detects code clones using:
    - Token-based comparison (Type-1, Type-2)
    - AST similarity analysis (Type-3)
    - Semantic analysis (Type-4)
    """

    def __init__(
        self,
        min_tokens: int = 50,
        min_lines: int = 6,
        similarity_threshold: float = 0.8,
        enable_type_4: bool = False  # Type-4 detection is expensive
    ):
        """
        Initialize duplication detector.

        Args:
            min_tokens: Minimum token count for clone detection
            min_lines: Minimum line count for clone detection
            similarity_threshold: Minimum similarity score (0.0-1.0)
            enable_type_4: Enable semantic clone detection
        """
        self.min_tokens = min_tokens
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold
        self.enable_type_4 = enable_type_4
        self._cache: Dict[str, Any] = {}

    def detect_duplicates(
        self,
        code: Union[str, List[Path], List[str]],
        min_tokens: Optional[int] = None
    ) -> DuplicationReport:
        """
        Detect all types of code duplicates.

        Args:
            code: Source code string, list of file paths, or list of code strings
            min_tokens: Override minimum token count

        Returns:
            DuplicationReport with clones, clusters, metrics, and recommendations
        """
        min_tok = min_tokens or self.min_tokens

        # Parse input
        code_fragments = self._parse_input(code)

        # Detect all clone types
        all_clones: List[Clone] = []

        # Type-1: Exact clones
        all_clones.extend(self._detect_exact_clones_batch(code_fragments))

        # Type-2: Renamed clones
        all_clones.extend(self._detect_renamed_clones_batch(code_fragments))

        # Type-3: Structural clones
        all_clones.extend(self._detect_structural_clones_batch(code_fragments))

        # Type-4: Semantic clones (optional)
        if self.enable_type_4:
            all_clones.extend(self._detect_semantic_clones_batch(code_fragments))

        # Filter false positives
        filtered_clones = self.filter_false_positives(all_clones)

        # Cluster clones
        clusters = self.cluster_clones(filtered_clones)

        # Compute metrics
        total_loc = sum(len(cf[0].split('\n')) for cf in code_fragments)
        metrics = self.compute_clone_metrics(filtered_clones, total_loc)

        # Generate refactoring suggestions
        recommendations = []
        for cluster in clusters:
            recommendations.extend(self.suggest_refactorings(cluster))

        return DuplicationReport(
            clones=filtered_clones,
            clusters=clusters,
            metrics=metrics,
            recommendations=recommendations
        )

    def _parse_input(self, code: Union[str, List[Path], List[str]]) -> List[Tuple[str, CodeLocation]]:
        """Parse various input formats into code fragments"""
        fragments = []

        if isinstance(code, str):
            # Single code string
            loc = CodeLocation(start_line=1, end_line=len(code.split('\n')))
            fragments.append((code, loc))
        elif isinstance(code, list):
            for idx, item in enumerate(code):
                if isinstance(item, Path):
                    # Read from file
                    content = item.read_text(encoding='utf-8', errors='ignore')
                    loc = CodeLocation(
                        file_path=str(item),
                        start_line=1,
                        end_line=len(content.split('\n'))
                    )
                    fragments.append((content, loc))
                elif isinstance(item, str):
                    # Code string
                    loc = CodeLocation(
                        file_path=f"fragment_{idx}",
                        start_line=1,
                        end_line=len(item.split('\n'))
                    )
                    fragments.append((item, loc))

        return fragments

    def tokenize_code(self, code: str) -> List[Token]:
        """
        Convert code to token sequence.

        Args:
            code: Source code string

        Returns:
            List of tokens with normalized values
        """
        tokens = []

        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)

        # Tokenize using regex
        token_pattern = r'\b\w+\b|[^\w\s]'
        matches = re.finditer(token_pattern, code)

        for match in matches:
            value = match.group()

            # Determine token type
            if value.isidentifier() and value[0].isupper():
                token_type = 'CLASS'
                normalized = 'CLASS'
            elif value.isidentifier():
                token_type = 'IDENTIFIER'
                normalized = 'ID'
            elif value.isdigit():
                token_type = 'NUMBER'
                normalized = 'NUM'
            else:
                token_type = 'OPERATOR'
                normalized = value

            tokens.append(Token(type=token_type, value=value, normalized=normalized))

        return tokens

    def compute_token_similarity(self, tokens1: List[Token], tokens2: List[Token]) -> float:
        """
        Compute similarity between token sequences.

        Uses longest common subsequence ratio.
        """
        seq1 = [t.normalized for t in tokens1]
        seq2 = [t.normalized for t in tokens2]

        matcher = difflib.SequenceMatcher(None, seq1, seq2)
        return matcher.ratio()

    def _detect_exact_clones_batch(self, fragments: List[Tuple[str, CodeLocation]]) -> List[ExactClone]:
        """Detect Type-1 clones across code fragments"""
        clones = []

        for i, (code1, loc1) in enumerate(fragments):
            for code2, loc2 in fragments[i+1:]:
                exact = self.detect_exact_clones(code1, code2, loc1, loc2)
                clones.extend(exact)

        return clones

    def detect_exact_clones(
        self,
        code1: str,
        code2: str,
        loc1: CodeLocation,
        loc2: CodeLocation
    ) -> List[ExactClone]:
        """
        Detect Type-1 clones (exact duplicates).

        Finds identical code fragments after normalization.
        """
        clones = []

        # Normalize: remove whitespace and comments
        normalized1 = self._normalize_code(code1)
        normalized2 = self._normalize_code(code2)

        # Find common substrings
        lines1 = normalized1.split('\n')
        lines2 = normalized2.split('\n')

        # Use sequence matcher to find matching blocks
        matcher = difflib.SequenceMatcher(None, lines1, lines2)

        for block in matcher.get_matching_blocks():
            i, j, size = block

            if size >= self.min_lines:
                clone_code1 = '\n'.join(lines1[i:i+size])
                clone_code2 = '\n'.join(lines2[j:j+size])

                tokens = self.tokenize_code(clone_code1)

                if len(tokens) >= self.min_tokens:
                    clone_loc1 = CodeLocation(
                        file_path=loc1.file_path,
                        start_line=loc1.start_line + i,
                        end_line=loc1.start_line + i + size
                    )
                    clone_loc2 = CodeLocation(
                        file_path=loc2.file_path,
                        start_line=loc2.start_line + j,
                        end_line=loc2.start_line + j + size
                    )

                    clones.append(ExactClone(
                        clone_type=CloneType.TYPE_1,
                        code1=clone_code1,
                        code2=clone_code2,
                        location1=clone_loc1,
                        location2=clone_loc2,
                        similarity=1.0,
                        token_count=len(tokens)
                    ))

        return clones

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison"""
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        # Remove extra whitespace
        code = re.sub(r'\s+', ' ', code)
        # Remove leading/trailing whitespace
        lines = [line.strip() for line in code.split('\n')]
        return '\n'.join(line for line in lines if line)

    def _detect_renamed_clones_batch(self, fragments: List[Tuple[str, CodeLocation]]) -> List[RenamedClone]:
        """Detect Type-2 clones across fragments"""
        clones = []

        for i, (code1, loc1) in enumerate(fragments):
            for code2, loc2 in fragments[i+1:]:
                renamed = self.detect_renamed_clones(code1, code2, loc1, loc2)
                clones.extend(renamed)

        return clones

    def detect_renamed_clones(
        self,
        code1: str,
        code2: str,
        loc1: CodeLocation,
        loc2: CodeLocation
    ) -> List[RenamedClone]:
        """
        Detect Type-2 clones (renamed identifiers).

        Uses token-based comparison with identifier normalization.
        """
        clones = []

        tokens1 = self.tokenize_code(code1)
        tokens2 = self.tokenize_code(code2)

        similarity = self.compute_token_similarity(tokens1, tokens2)

        if similarity >= self.similarity_threshold and len(tokens1) >= self.min_tokens:
            # Build identifier mapping
            id_mapping = self._build_identifier_mapping(tokens1, tokens2)

            clones.append(RenamedClone(
                clone_type=CloneType.TYPE_2,
                code1=code1,
                code2=code2,
                location1=loc1,
                location2=loc2,
                similarity=similarity,
                token_count=len(tokens1),
                identifier_mapping=id_mapping
            ))

        return clones

    def _build_identifier_mapping(self, tokens1: List[Token], tokens2: List[Token]) -> Dict[str, str]:
        """Build mapping between renamed identifiers"""
        mapping = {}

        for t1, t2 in zip(tokens1, tokens2):
            if t1.type == 'IDENTIFIER' and t2.type == 'IDENTIFIER':
                if t1.value != t2.value:
                    mapping[t1.value] = t2.value

        return mapping

    def _detect_structural_clones_batch(self, fragments: List[Tuple[str, CodeLocation]]) -> List[StructuralClone]:
        """Detect Type-3 clones across fragments"""
        clones = []

        for i, (code1, loc1) in enumerate(fragments):
            for code2, loc2 in fragments[i+1:]:
                structural = self.detect_structural_clones(code1, code2, loc1, loc2)
                clones.extend(structural)

        return clones

    def detect_structural_clones(
        self,
        code1: str,
        code2: str,
        loc1: CodeLocation,
        loc2: CodeLocation
    ) -> List[StructuralClone]:
        """
        Detect Type-3 clones (structural similarity).

        Uses AST comparison with tree edit distance.
        """
        clones = []

        try:
            ast1 = ast.parse(code1)
            ast2 = ast.parse(code2)

            # Normalize ASTs
            norm_ast1 = self.normalize_ast(ast1)
            norm_ast2 = self.normalize_ast(ast2)

            # Compute AST similarity
            similarity = self.compare_ast_similarity(norm_ast1, norm_ast2)

            if similarity >= self.similarity_threshold:
                edit_dist = self.compute_tree_edit_distance(norm_ast1, norm_ast2)

                clones.append(StructuralClone(
                    clone_type=CloneType.TYPE_3,
                    code1=code1,
                    code2=code2,
                    location1=loc1,
                    location2=loc2,
                    similarity=similarity,
                    edit_distance=edit_dist,
                    modifications=[]
                ))
        except SyntaxError:
            # Skip invalid syntax
            pass

        return clones

    def normalize_ast(self, tree: ast.AST) -> ast.AST:
        """
        Normalize AST for comparison.

        Renames variables to standard names, removes literals.
        """
        class Normalizer(ast.NodeTransformer):
            def __init__(self):
                self.var_counter = 0
                self.var_map = {}

            def visit_Name(self, node):
                if node.id not in self.var_map:
                    self.var_map[node.id] = f"var_{self.var_counter}"
                    self.var_counter += 1
                node.id = self.var_map[node.id]
                return node

            def visit_Constant(self, node):
                # Normalize constants
                if isinstance(node.value, (int, float)):
                    node.value = 0
                elif isinstance(node.value, str):
                    node.value = ""
                return node

        normalizer = Normalizer()
        return normalizer.visit(tree)

    def compare_ast_similarity(self, ast1: ast.AST, ast2: ast.AST) -> float:
        """
        Compute structural similarity between ASTs.

        Uses node count and structure comparison.
        """
        nodes1 = list(ast.walk(ast1))
        nodes2 = list(ast.walk(ast2))

        if not nodes1 or not nodes2:
            return 0.0

        # Compare node types
        types1 = [type(n).__name__ for n in nodes1]
        types2 = [type(n).__name__ for n in nodes2]

        matcher = difflib.SequenceMatcher(None, types1, types2)
        return matcher.ratio()

    def compute_tree_edit_distance(self, ast1: ast.AST, ast2: ast.AST) -> int:
        """
        Compute tree edit distance between ASTs.

        Simplified version counting node differences.
        """
        nodes1 = list(ast.walk(ast1))
        nodes2 = list(ast.walk(ast2))

        return abs(len(nodes1) - len(nodes2))

    def _detect_semantic_clones_batch(self, fragments: List[Tuple[str, CodeLocation]]) -> List[SemanticClone]:
        """Detect Type-4 clones across fragments"""
        clones = []

        for i, (code1, loc1) in enumerate(fragments):
            for code2, loc2 in fragments[i+1:]:
                semantic = self.detect_semantic_clones(code1, code2, loc1, loc2)
                clones.extend(semantic)

        return clones

    def detect_semantic_clones(
        self,
        code1: str,
        code2: str,
        loc1: CodeLocation,
        loc2: CodeLocation
    ) -> List[SemanticClone]:
        """
        Detect Type-4 clones (semantic equivalence).

        Simplified semantic analysis using control flow patterns.
        """
        clones = []

        try:
            # Extract control flow patterns
            pattern1 = self._extract_control_flow_pattern(code1)
            pattern2 = self._extract_control_flow_pattern(code2)

            # Compare patterns
            if pattern1 and pattern2:
                similarity = difflib.SequenceMatcher(None, pattern1, pattern2).ratio()

                if similarity >= self.similarity_threshold:
                    clones.append(SemanticClone(
                        clone_type=CloneType.TYPE_4,
                        code1=code1,
                        code2=code2,
                        location1=loc1,
                        location2=loc2,
                        similarity=similarity,
                        equivalence_proof=f"Control flow similarity: {similarity:.2f}"
                    ))
        except Exception:
            pass

        return clones

    def _extract_control_flow_pattern(self, code: str) -> List[str]:
        """Extract control flow pattern from code"""
        try:
            tree = ast.parse(code)
            pattern = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                    pattern.append(type(node).__name__)

            return pattern
        except SyntaxError:
            return []

    def cluster_clones(self, clones: List[Clone]) -> List[CloneCluster]:
        """
        Group related clones into clusters.

        Uses similarity-based grouping.
        """
        if not clones:
            return []

        clusters = []
        used = set()

        for i, clone1 in enumerate(clones):
            if i in used:
                continue

            # Start new cluster
            cluster_clones = [clone1]
            used.add(i)

            # Find similar clones
            for j, clone2 in enumerate(clones[i+1:], start=i+1):
                if j in used:
                    continue

                # Check if clones are related
                if self._are_clones_related(clone1, clone2):
                    cluster_clones.append(clone2)
                    used.add(j)

            # Create cluster
            affected_files = set()
            for clone in cluster_clones:
                if clone.location1.file_path:
                    affected_files.add(clone.location1.file_path)
                if clone.location2.file_path:
                    affected_files.add(clone.location2.file_path)

            clusters.append(CloneCluster(
                clones=cluster_clones,
                representative=cluster_clones[0],
                affected_files=affected_files
            ))

        return clusters

    def _are_clones_related(self, clone1: Clone, clone2: Clone) -> bool:
        """Check if two clones are related"""
        # Same type and similar size
        if clone1.clone_type != clone2.clone_type:
            return False

        size_ratio = min(clone1.size(), clone2.size()) / max(clone1.size(), clone2.size())
        return size_ratio >= 0.8

    def compute_clone_metrics(self, clones: List[Clone], total_loc: int) -> CloneMetrics:
        """
        Compute comprehensive clone metrics.

        Args:
            clones: List of detected clones
            total_loc: Total lines of code analyzed

        Returns:
            CloneMetrics with coverage, density, and distribution
        """
        if total_loc == 0:
            total_loc = 1

        total_duplicated_lines = sum(c.size() for c in clones)
        clone_coverage = (total_duplicated_lines / total_loc) * 100
        clone_density = len(clones) / (total_loc / 1000) if total_loc >= 1000 else len(clones)

        largest_clone = max((c.size() for c in clones), default=0)

        # Type distribution
        type_dist = defaultdict(int)
        for clone in clones:
            type_dist[clone.clone_type] += 1

        return CloneMetrics(
            total_clones=len(clones),
            clone_coverage=clone_coverage,
            clone_density=clone_density,
            largest_clone_size=largest_clone,
            clone_type_distribution=dict(type_dist),
            total_duplicated_lines=total_duplicated_lines
        )

    def suggest_refactorings(self, cluster: CloneCluster) -> List[RefactoringSuggestion]:
        """
        Generate refactoring suggestions for clone cluster.

        Analyzes clone patterns and suggests appropriate refactorings.
        """
        suggestions = []

        if not cluster.clones:
            return suggestions

        representative = cluster.representative or cluster.clones[0]
        cluster_size = cluster.size()
        total_dup_lines = cluster.total_duplicated_lines()

        # Extract method suggestion
        if cluster_size >= 2 and representative.size() >= 5:
            suggestions.append(RefactoringSuggestion(
                refactoring_type=RefactoringType.EXTRACT_METHOD,
                description=f"Extract duplicated code into a new method",
                benefit=f"Reduce {total_dup_lines} duplicated lines across {cluster_size} locations",
                estimated_loc_reduction=total_dup_lines - representative.size(),
                confidence=0.9
            ))

        # Extract class suggestion for cross-file duplicates
        if len(cluster.affected_files) > 1:
            suggestions.append(RefactoringSuggestion(
                refactoring_type=RefactoringType.EXTRACT_CLASS,
                description=f"Extract common functionality into utility class",
                benefit=f"Centralize logic used in {len(cluster.affected_files)} files",
                estimated_loc_reduction=total_dup_lines // 2,
                confidence=0.7
            ))

        # Parameterize for Type-2 clones
        if representative.clone_type == CloneType.TYPE_2:
            suggestions.append(RefactoringSuggestion(
                refactoring_type=RefactoringType.PARAMETERIZE,
                description="Parameterize differences in renamed clones",
                benefit="Unify similar code with parameters",
                estimated_loc_reduction=total_dup_lines - representative.size() * 2,
                confidence=0.8
            ))

        return suggestions

    def filter_false_positives(self, clones: List[Clone]) -> List[Clone]:
        """
        Filter out false positive clones.

        Removes:
        - Short clones (below threshold)
        - Boilerplate code
        - Language idioms
        """
        filtered = []

        for clone in clones:
            # Filter short clones
            if clone.size() < self.min_lines:
                continue

            if clone.token_count < self.min_tokens:
                continue

            # Filter boilerplate
            if self._is_boilerplate(clone.code1):
                continue

            # Filter common patterns
            if self._is_common_pattern(clone.code1):
                continue

            filtered.append(clone)

        return filtered

    def _is_boilerplate(self, code: str) -> bool:
        """Check if code is boilerplate"""
        boilerplate_patterns = [
            r'^\s*import\s+',
            r'^\s*from\s+.*\s+import\s+',
            r'^\s*class\s+\w+\s*:',
            r'^\s*def\s+__init__\s*\(',
        ]

        for pattern in boilerplate_patterns:
            if re.match(pattern, code, re.MULTILINE):
                return True

        return False

    def _is_common_pattern(self, code: str) -> bool:
        """Check if code is a common language idiom"""
        # Very short or trivial code
        if len(code.strip().split('\n')) <= 2:
            return True

        return False

    def visualize_clones(self, clones: List[Clone], output: Path) -> bool:
        """
        Generate clone visualization data.

        Creates data structure for heatmap/scatter plot visualization.
        """
        try:
            # Build similarity matrix
            files = set()
            for clone in clones:
                if clone.location1.file_path:
                    files.add(clone.location1.file_path)
                if clone.location2.file_path:
                    files.add(clone.location2.file_path)

            file_list = sorted(files)

            # Create visualization data
            viz_data = {
                'files': file_list,
                'clones': [
                    {
                        'type': clone.clone_type.value,
                        'similarity': clone.similarity,
                        'size': clone.size(),
                        'location1': str(clone.location1),
                        'location2': str(clone.location2),
                    }
                    for clone in clones
                ]
            }

            # Write to file
            import json
            output.write_text(json.dumps(viz_data, indent=2))

            return True
        except Exception:
            return False

    def track_clone_evolution(
        self,
        current: DuplicationReport,
        previous: DuplicationReport
    ) -> CloneEvolution:
        """
        Track clone evolution between versions.

        Identifies new, removed, modified, and persistent clones.
        """
        current_sigs = {self._clone_signature(c): c for c in current.clones}
        previous_sigs = {self._clone_signature(c): c for c in previous.clones}

        new_clones = [c for sig, c in current_sigs.items() if sig not in previous_sigs]
        removed_clones = [c for sig, c in previous_sigs.items() if sig not in current_sigs]
        persistent_clones = [c for sig, c in current_sigs.items() if sig in previous_sigs]

        return CloneEvolution(
            new_clones=new_clones,
            removed_clones=removed_clones,
            persistent_clones=persistent_clones
        )

    def _clone_signature(self, clone: Clone) -> str:
        """Generate unique signature for clone"""
        code_hash = hashlib.md5(clone.code1.encode()).hexdigest()
        return f"{clone.clone_type.value}:{code_hash}:{clone.size()}"

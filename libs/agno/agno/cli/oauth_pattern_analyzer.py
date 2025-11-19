"""
OAuth Pattern Discovery and Analysis System

Automated pattern extraction, classification, and anti-pattern detection for OAuth implementations.
Uses AST parsing, similarity analysis, and statistical methods to identify patterns in FSA code.

Tools:
- AST parsing for code structure analysis
- Vector embeddings for similarity analysis
- Pattern matching for common OAuth patterns
- Statistical analysis for clustering and classification
"""

import ast
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from enum import Enum, auto
import hashlib


logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of OAuth patterns"""
    STATE_TRANSITION = auto()
    ERROR_HANDLING = auto()
    TOKEN_MANAGEMENT = auto()
    SECURITY_PRACTICE = auto()
    VALIDATION = auto()
    ANTI_PATTERN = auto()


class PatternSeverity(Enum):
    """Pattern severity for anti-patterns"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class CodePattern:
    """Represents a discovered code pattern"""
    pattern_id: str
    pattern_type: PatternType
    name: str
    description: str
    code_sample: str
    frequency: int = 1
    locations: List[str] = field(default_factory=list)
    similarity_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    severity: Optional[PatternSeverity] = None

    def __hash__(self):
        return hash(self.pattern_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.name,
            "name": self.name,
            "description": self.description,
            "code_sample": self.code_sample,
            "frequency": self.frequency,
            "locations": self.locations,
            "similarity_score": self.similarity_score,
            "metadata": self.metadata,
            "severity": self.severity.name if self.severity else None
        }


@dataclass
class PatternCluster:
    """Group of similar patterns"""
    cluster_id: str
    patterns: List[CodePattern] = field(default_factory=list)
    centroid_pattern: Optional[CodePattern] = None
    avg_similarity: float = 0.0

    def add_pattern(self, pattern: CodePattern):
        """Add pattern to cluster"""
        self.patterns.append(pattern)
        self._update_centroid()

    def _update_centroid(self):
        """Update cluster centroid (most representative pattern)"""
        if not self.patterns:
            return
        # Most frequent pattern becomes centroid
        self.centroid_pattern = max(self.patterns, key=lambda p: p.frequency)
        self.avg_similarity = sum(p.similarity_score for p in self.patterns) / len(self.patterns)


class OAuthASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting OAuth patterns"""

    def __init__(self):
        self.state_transitions: List[Dict[str, Any]] = []
        self.error_handlers: List[Dict[str, Any]] = []
        self.token_operations: List[Dict[str, Any]] = []
        self.validations: List[Dict[str, Any]] = []
        self.security_checks: List[Dict[str, Any]] = []
        self.function_calls: List[str] = []
        self.class_methods: Dict[str, List[str]] = defaultdict(list)
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition"""
        old_function = self.current_function
        self.current_function = node.name

        if self.current_class:
            self.class_methods[self.current_class].append(node.name)

        # Detect state transition patterns
        if "transition" in node.name.lower() or "state" in node.name.lower():
            self.state_transitions.append({
                "name": node.name,
                "lineno": node.lineno,
                "class": self.current_class,
                "args": [arg.arg for arg in node.args.args]
            })

        # Detect error handling patterns
        if "error" in node.name.lower() or "handle" in node.name.lower():
            self.error_handlers.append({
                "name": node.name,
                "lineno": node.lineno,
                "class": self.current_class
            })

        # Detect token management patterns
        if "token" in node.name.lower() or "refresh" in node.name.lower():
            self.token_operations.append({
                "name": node.name,
                "lineno": node.lineno,
                "class": self.current_class
            })

        # Detect validation patterns
        if "validate" in node.name.lower() or "check" in node.name.lower():
            self.validations.append({
                "name": node.name,
                "lineno": node.lineno,
                "class": self.current_class
            })

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call):
        """Visit function call"""
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Handle method calls like obj.method()
            if isinstance(node.func.value, ast.Name):
                call_name = f"{node.func.value.id}.{node.func.attr}"
                self.function_calls.append(call_name)

                # Detect security-related calls
                if any(sec in call_name.lower() for sec in ["secrets", "hash", "compare_digest", "urlsafe"]):
                    self.security_checks.append({
                        "call": call_name,
                        "lineno": node.lineno,
                        "function": self.current_function,
                        "class": self.current_class
                    })

        self.generic_visit(node)


class OAuthPatternAnalyzer:
    """
    Automated pattern discovery and analysis system

    Analyzes OAuth implementations to extract patterns, detect anti-patterns,
    and provide recommendations.
    """

    def __init__(self):
        self.patterns: List[CodePattern] = []
        self.anti_patterns: List[CodePattern] = []
        self.clusters: List[PatternCluster] = []
        self._known_patterns = self._load_known_patterns()
        self._anti_pattern_rules = self._load_anti_pattern_rules()

    def _load_known_patterns(self) -> Dict[str, CodePattern]:
        """Load library of known OAuth patterns"""
        return {
            "pkce_generation": CodePattern(
                pattern_id="pkce_gen_001",
                pattern_type=PatternType.SECURITY_PRACTICE,
                name="PKCE Challenge Generation",
                description="Secure PKCE code verifier and challenge generation using SHA256",
                code_sample="""
def generate_pkce_challenge(self) -> tuple[str, str]:
    verifier = secrets.token_urlsafe(96)[:128]
    challenge = hashlib.sha256(verifier.encode()).digest()
    challenge_b64 = base64.urlsafe_b64encode(challenge).decode().rstrip('=')
    return verifier, challenge_b64
                """.strip()
            ),
            "state_validation": CodePattern(
                pattern_id="state_val_001",
                pattern_type=PatternType.SECURITY_PRACTICE,
                name="Timing-Safe State Validation",
                description="Use secrets.compare_digest for timing-safe state parameter comparison",
                code_sample="""
def validate_state(self, received_state: str) -> bool:
    return self.state_parameter and secrets.compare_digest(
        self.state_parameter, received_state
    )
                """.strip()
            ),
            "token_expiry_check": CodePattern(
                pattern_id="token_exp_001",
                pattern_type=PatternType.TOKEN_MANAGEMENT,
                name="Token Expiry with Buffer",
                description="Check token expiry with 60-second buffer for clock skew",
                code_sample="""
@property
def is_expired(self) -> bool:
    if not self.expires_in:
        return False
    return time.time() >= (self.issued_at + self.expires_in - 60)
                """.strip()
            ),
            "auto_refresh": CodePattern(
                pattern_id="token_ref_001",
                pattern_type=PatternType.TOKEN_MANAGEMENT,
                name="Automatic Token Refresh",
                description="Automatically refresh expired tokens when accessed",
                code_sample="""
def get_token(self) -> OAuthToken:
    if self.token.is_expired and self.token.refresh_token:
        return self.refresh_access_token()
    return self.token
                """.strip()
            ),
            "state_machine_validation": CodePattern(
                pattern_id="fsm_val_001",
                pattern_type=PatternType.STATE_TRANSITION,
                name="State Transition Validation",
                description="Validate state transitions before executing",
                code_sample="""
def _is_valid_transition(self, from_state: State, to_state: State) -> bool:
    valid_transitions = {
        State.INITIAL: {State.AUTHORIZED, State.ERROR},
        # ... more transitions
    }
    return to_state in valid_transitions.get(from_state, set())
                """.strip()
            )
        }

    def _load_anti_pattern_rules(self) -> Dict[str, CodePattern]:
        """Load anti-pattern detection rules"""
        return {
            "plain_state_comparison": CodePattern(
                pattern_id="anti_001",
                pattern_type=PatternType.ANTI_PATTERN,
                name="Plain String State Comparison",
                description="Using == or != for state parameter comparison is vulnerable to timing attacks",
                code_sample="if received_state == self.state:",
                severity=PatternSeverity.ERROR,
                metadata={"recommendation": "Use secrets.compare_digest() instead"}
            ),
            "no_pkce": CodePattern(
                pattern_id="anti_002",
                pattern_type=PatternType.ANTI_PATTERN,
                name="Missing PKCE for Public Clients",
                description="Public clients should always use PKCE",
                code_sample="# Authorization code flow without PKCE",
                severity=PatternSeverity.CRITICAL,
                metadata={"recommendation": "Use OAuthFlowType.AUTHORIZATION_CODE_PKCE"}
            ),
            "hardcoded_secrets": CodePattern(
                pattern_id="anti_003",
                pattern_type=PatternType.ANTI_PATTERN,
                name="Hardcoded Client Secrets",
                description="Client secrets should not be hardcoded in source code",
                code_sample='client_secret = "hardcoded_secret"',
                severity=PatternSeverity.CRITICAL,
                metadata={"recommendation": "Load from environment variables or secure vault"}
            ),
            "no_state_param": CodePattern(
                pattern_id="anti_004",
                pattern_type=PatternType.ANTI_PATTERN,
                name="Missing State Parameter",
                description="OAuth flows must include state parameter for CSRF protection",
                code_sample="# Authorization URL without state parameter",
                severity=PatternSeverity.CRITICAL,
                metadata={"recommendation": "Always generate and validate state parameter"}
            ),
            "insecure_random": CodePattern(
                pattern_id="anti_005",
                pattern_type=PatternType.ANTI_PATTERN,
                name="Insecure Random Generation",
                description="Using random.random() or similar for security tokens",
                code_sample="state = str(random.random())",
                severity=PatternSeverity.CRITICAL,
                metadata={"recommendation": "Use secrets.token_urlsafe() for cryptographic randomness"}
            ),
            "no_token_expiry": CodePattern(
                pattern_id="anti_006",
                pattern_type=PatternType.ANTI_PATTERN,
                name="No Token Expiry Check",
                description="Not checking if access token has expired",
                code_sample="return self.access_token  # No expiry check",
                severity=PatternSeverity.WARNING,
                metadata={"recommendation": "Always check token expiry before use"}
            )
        }

    def analyze_file(self, file_path: str, source_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a Python file for OAuth patterns

        Args:
            file_path: Path to file
            source_code: Source code (if None, reads from file_path)

        Returns:
            Analysis results
        """
        if source_code is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return {"error": str(e)}

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return {"error": f"Syntax error: {e}"}

        # Visit AST
        visitor = OAuthASTVisitor()
        visitor.visit(tree)

        # Extract patterns
        extracted_patterns = self._extract_patterns_from_ast(visitor, file_path, source_code)

        # Detect anti-patterns
        detected_anti_patterns = self._detect_anti_patterns(source_code, file_path)

        # Calculate statistics
        stats = self._calculate_statistics(visitor, source_code)

        return {
            "file_path": file_path,
            "patterns": [p.to_dict() for p in extracted_patterns],
            "anti_patterns": [p.to_dict() for p in detected_anti_patterns],
            "statistics": stats,
            "ast_analysis": {
                "state_transitions": visitor.state_transitions,
                "error_handlers": visitor.error_handlers,
                "token_operations": visitor.token_operations,
                "validations": visitor.validations,
                "security_checks": visitor.security_checks,
                "class_methods": dict(visitor.class_methods)
            }
        }

    def _extract_patterns_from_ast(self, visitor: OAuthASTVisitor, file_path: str, source_code: str) -> List[CodePattern]:
        """Extract patterns from AST analysis"""
        patterns = []

        # State transition pattern
        if visitor.state_transitions:
            pattern = CodePattern(
                pattern_id=self._generate_pattern_id("state_transition", file_path),
                pattern_type=PatternType.STATE_TRANSITION,
                name="State Transition Implementation",
                description=f"Found {len(visitor.state_transitions)} state transition methods",
                code_sample=self._extract_code_sample(source_code, visitor.state_transitions[0]["lineno"]),
                frequency=len(visitor.state_transitions),
                locations=[f"{file_path}:{t['lineno']}" for t in visitor.state_transitions]
            )
            patterns.append(pattern)

        # Error handling pattern
        if visitor.error_handlers:
            pattern = CodePattern(
                pattern_id=self._generate_pattern_id("error_handling", file_path),
                pattern_type=PatternType.ERROR_HANDLING,
                name="Error Handling Implementation",
                description=f"Found {len(visitor.error_handlers)} error handling methods",
                code_sample=self._extract_code_sample(source_code, visitor.error_handlers[0]["lineno"]),
                frequency=len(visitor.error_handlers),
                locations=[f"{file_path}:{t['lineno']}" for t in visitor.error_handlers]
            )
            patterns.append(pattern)

        # Token management pattern
        if visitor.token_operations:
            pattern = CodePattern(
                pattern_id=self._generate_pattern_id("token_mgmt", file_path),
                pattern_type=PatternType.TOKEN_MANAGEMENT,
                name="Token Management Implementation",
                description=f"Found {len(visitor.token_operations)} token management methods",
                code_sample=self._extract_code_sample(source_code, visitor.token_operations[0]["lineno"]),
                frequency=len(visitor.token_operations),
                locations=[f"{file_path}:{t['lineno']}" for t in visitor.token_operations]
            )
            patterns.append(pattern)

        # Security practices
        if visitor.security_checks:
            pattern = CodePattern(
                pattern_id=self._generate_pattern_id("security", file_path),
                pattern_type=PatternType.SECURITY_PRACTICE,
                name="Security Best Practices",
                description=f"Found {len(visitor.security_checks)} security-related operations",
                code_sample=self._extract_code_sample(source_code, visitor.security_checks[0]["lineno"]),
                frequency=len(visitor.security_checks),
                locations=[f"{file_path}:{t['lineno']}" for t in visitor.security_checks],
                metadata={"security_calls": [s["call"] for s in visitor.security_checks]}
            )
            patterns.append(pattern)

        # Validation pattern
        if visitor.validations:
            pattern = CodePattern(
                pattern_id=self._generate_pattern_id("validation", file_path),
                pattern_type=PatternType.VALIDATION,
                name="Validation Implementation",
                description=f"Found {len(visitor.validations)} validation methods",
                code_sample=self._extract_code_sample(source_code, visitor.validations[0]["lineno"]),
                frequency=len(visitor.validations),
                locations=[f"{file_path}:{t['lineno']}" for t in visitor.validations]
            )
            patterns.append(pattern)

        return patterns

    def _detect_anti_patterns(self, source_code: str, file_path: str) -> List[CodePattern]:
        """Detect anti-patterns in source code"""
        anti_patterns = []

        # Check for plain state comparison
        if re.search(r'if\s+\w+\s*==\s*.*state', source_code) and 'compare_digest' not in source_code:
            ap = self._anti_pattern_rules["plain_state_comparison"]
            ap.locations = [file_path]
            anti_patterns.append(ap)

        # Check for hardcoded secrets
        if re.search(r'client_secret\s*=\s*["\'][^"\']{20,}["\']', source_code):
            ap = self._anti_pattern_rules["hardcoded_secrets"]
            ap.locations = [file_path]
            anti_patterns.append(ap)

        # Check for insecure random
        if 'random.random()' in source_code or 'random.randint' in source_code:
            if 'state' in source_code or 'token' in source_code or 'nonce' in source_code:
                ap = self._anti_pattern_rules["insecure_random"]
                ap.locations = [file_path]
                anti_patterns.append(ap)

        # Check for missing state parameter
        if 'authorization' in source_code.lower() and 'state' not in source_code:
            ap = self._anti_pattern_rules["no_state_param"]
            ap.locations = [file_path]
            anti_patterns.append(ap)

        return anti_patterns

    def _calculate_statistics(self, visitor: OAuthASTVisitor, source_code: str) -> Dict[str, Any]:
        """Calculate code statistics"""
        lines = source_code.split('\n')
        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "state_transitions": len(visitor.state_transitions),
            "error_handlers": len(visitor.error_handlers),
            "token_operations": len(visitor.token_operations),
            "validations": len(visitor.validations),
            "security_checks": len(visitor.security_checks),
            "function_calls": len(visitor.function_calls),
            "unique_function_calls": len(set(visitor.function_calls)),
            "classes": len(visitor.class_methods)
        }

    def _generate_pattern_id(self, pattern_type: str, file_path: str) -> str:
        """Generate unique pattern ID"""
        content = f"{pattern_type}:{file_path}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _extract_code_sample(self, source_code: str, lineno: int, context_lines: int = 3) -> str:
        """Extract code sample around a line number"""
        lines = source_code.split('\n')
        start = max(0, lineno - context_lines - 1)
        end = min(len(lines), lineno + context_lines)
        return '\n'.join(lines[start:end])

    def cluster_patterns(self, similarity_threshold: float = 0.7) -> List[PatternCluster]:
        """
        Cluster similar patterns using similarity analysis

        Args:
            similarity_threshold: Minimum similarity score for clustering

        Returns:
            List of pattern clusters
        """
        if not self.patterns:
            return []

        clusters = []
        unclustered = self.patterns.copy()

        while unclustered:
            # Start new cluster with first unclustered pattern
            seed = unclustered.pop(0)
            cluster = PatternCluster(
                cluster_id=f"cluster_{len(clusters):03d}",
                patterns=[seed]
            )

            # Find similar patterns
            to_remove = []
            for pattern in unclustered:
                similarity = self._calculate_similarity(seed, pattern)
                if similarity >= similarity_threshold:
                    pattern.similarity_score = similarity
                    cluster.add_pattern(pattern)
                    to_remove.append(pattern)

            # Remove clustered patterns
            for pattern in to_remove:
                unclustered.remove(pattern)

            cluster._update_centroid()
            clusters.append(cluster)

        self.clusters = clusters
        logger.info(f"Created {len(clusters)} pattern clusters")
        return clusters

    def _calculate_similarity(self, p1: CodePattern, p2: CodePattern) -> float:
        """
        Calculate similarity between two patterns

        Uses simple vector embedding approximation based on:
        - Pattern type match
        - Code token overlap
        - Metadata similarity
        """
        score = 0.0

        # Pattern type match (40% weight)
        if p1.pattern_type == p2.pattern_type:
            score += 0.4

        # Code token overlap (40% weight)
        tokens1 = set(re.findall(r'\w+', p1.code_sample.lower()))
        tokens2 = set(re.findall(r'\w+', p2.code_sample.lower()))
        if tokens1 and tokens2:
            overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
            score += 0.4 * overlap

        # Name similarity (20% weight)
        name_tokens1 = set(p1.name.lower().split())
        name_tokens2 = set(p2.name.lower().split())
        if name_tokens1 and name_tokens2:
            name_overlap = len(name_tokens1 & name_tokens2) / len(name_tokens1 | name_tokens2)
            score += 0.2 * name_overlap

        return score

    def generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate refactoring recommendations based on analysis

        Args:
            analysis_results: Results from analyze_file()

        Returns:
            List of recommendations
        """
        recommendations = []

        # Anti-pattern recommendations
        for anti_pattern in analysis_results.get("anti_patterns", []):
            recommendations.append({
                "type": "anti_pattern",
                "severity": anti_pattern.get("severity", "WARNING"),
                "title": anti_pattern["name"],
                "description": anti_pattern["description"],
                "recommendation": anti_pattern.get("metadata", {}).get("recommendation", "Review and refactor"),
                "locations": anti_pattern["locations"]
            })

        # Pattern frequency recommendations
        stats = analysis_results.get("statistics", {})

        if stats.get("security_checks", 0) < 2:
            recommendations.append({
                "type": "security",
                "severity": "WARNING",
                "title": "Insufficient Security Checks",
                "description": "Code has few security-related operations",
                "recommendation": "Add state validation, PKCE, and timing-safe comparisons",
                "locations": []
            })

        if stats.get("error_handlers", 0) == 0:
            recommendations.append({
                "type": "robustness",
                "severity": "ERROR",
                "title": "Missing Error Handling",
                "description": "No error handling methods detected",
                "recommendation": "Implement comprehensive error handling for OAuth failures",
                "locations": []
            })

        if stats.get("validations", 0) < 2:
            recommendations.append({
                "type": "validation",
                "severity": "WARNING",
                "title": "Insufficient Validation",
                "description": "Limited validation methods found",
                "recommendation": "Add state, scope, and token validation",
                "locations": []
            })

        return recommendations

    def generate_pattern_library(self) -> Dict[str, Any]:
        """
        Generate comprehensive pattern library

        Returns:
            Pattern library with all discovered and known patterns
        """
        return {
            "known_patterns": {
                pid: pattern.to_dict()
                for pid, pattern in self._known_patterns.items()
            },
            "discovered_patterns": [p.to_dict() for p in self.patterns],
            "anti_patterns": {
                pid: pattern.to_dict()
                for pid, pattern in self._anti_pattern_rules.items()
            },
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "size": len(c.patterns),
                    "avg_similarity": c.avg_similarity,
                    "centroid": c.centroid_pattern.to_dict() if c.centroid_pattern else None
                }
                for c in self.clusters
            ],
            "statistics": {
                "total_known_patterns": len(self._known_patterns),
                "total_discovered_patterns": len(self.patterns),
                "total_anti_patterns": len(self._anti_pattern_rules),
                "total_clusters": len(self.clusters)
            }
        }

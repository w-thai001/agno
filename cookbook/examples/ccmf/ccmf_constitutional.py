"""
CCMF Constitutional Framework - SESSION 1
=========================================

This module defines the constitutional principles and compliance validation
for the Constitutional Cognitive Meta-Framework (CCMF).

The constitutional layer ensures all AI operations adhere to defined principles,
ethical guidelines, and safety constraints.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class ComplianceLevel(Enum):
    """Levels of constitutional compliance."""
    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"
    NON_COMPLIANT = "non_compliant"


class PrincipleCategory(Enum):
    """Categories of constitutional principles."""
    SAFETY = "safety"
    ETHICS = "ethics"
    TRANSPARENCY = "transparency"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    PRIVACY = "privacy"


@dataclass
class ConstitutionalPrinciple:
    """Represents a single constitutional principle."""
    id: str
    name: str
    category: PrincipleCategory
    description: str
    weight: float = 1.0  # Importance weight (0.0 - 1.0)
    mandatory: bool = False  # Must be satisfied
    validation_criteria: List[str] = field(default_factory=list)

    def validate(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate if the principle is satisfied in the given context.

        Args:
            context: Context data for validation

        Returns:
            Tuple of (is_valid, reason)
        """
        # Basic validation logic - can be extended
        if not context:
            return False, "No context provided for validation"

        # Check if validation criteria are met
        for criterion in self.validation_criteria:
            if criterion not in context:
                return False, f"Missing required criterion: {criterion}"

        return True, "Principle validated successfully"


@dataclass
class ComplianceReport:
    """Report of constitutional compliance validation."""
    timestamp: datetime
    overall_compliance: ComplianceLevel
    compliance_score: float  # 0.0 - 1.0
    principles_checked: int
    principles_passed: int
    principles_failed: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'overall_compliance': self.overall_compliance.value,
            'compliance_score': self.compliance_score,
            'principles_checked': self.principles_checked,
            'principles_passed': self.principles_passed,
            'principles_failed': self.principles_failed,
            'violations': self.violations,
            'recommendations': self.recommendations,
            'details': self.details
        }


class ConstitutionalFramework:
    """
    Core constitutional framework for CCMF.

    Manages constitutional principles and validates compliance
    for all AI operations within the framework.
    """

    def __init__(self):
        """Initialize the constitutional framework."""
        self.principles: List[ConstitutionalPrinciple] = []
        self.compliance_history: List[ComplianceReport] = []
        self._initialize_default_principles()

    def _initialize_default_principles(self):
        """Initialize default constitutional principles."""
        default_principles = [
            ConstitutionalPrinciple(
                id="safety_001",
                name="No Harmful Operations",
                category=PrincipleCategory.SAFETY,
                description="Operations must not cause harm to users, systems, or data",
                weight=1.0,
                mandatory=True,
                validation_criteria=["operation_type", "risk_assessment"]
            ),
            ConstitutionalPrinciple(
                id="transparency_001",
                name="Operation Transparency",
                category=PrincipleCategory.TRANSPARENCY,
                description="All operations must be logged and traceable",
                weight=0.9,
                mandatory=True,
                validation_criteria=["logging_enabled", "audit_trail"]
            ),
            ConstitutionalPrinciple(
                id="efficiency_001",
                name="Resource Efficiency",
                category=PrincipleCategory.EFFICIENCY,
                description="Operations should use resources efficiently",
                weight=0.7,
                mandatory=False,
                validation_criteria=["resource_estimate"]
            ),
            ConstitutionalPrinciple(
                id="robustness_001",
                name="Error Handling",
                category=PrincipleCategory.ROBUSTNESS,
                description="Operations must handle errors gracefully",
                weight=0.85,
                mandatory=True,
                validation_criteria=["error_handling", "recovery_strategy"]
            ),
            ConstitutionalPrinciple(
                id="privacy_001",
                name="Data Privacy",
                category=PrincipleCategory.PRIVACY,
                description="Operations must respect data privacy and confidentiality",
                weight=0.95,
                mandatory=True,
                validation_criteria=["data_classification", "privacy_check"]
            ),
            ConstitutionalPrinciple(
                id="ethics_001",
                name="Ethical AI Use",
                category=PrincipleCategory.ETHICS,
                description="AI operations must align with ethical guidelines",
                weight=1.0,
                mandatory=True,
                validation_criteria=["ethical_review"]
            )
        ]

        self.principles.extend(default_principles)

    def add_principle(self, principle: ConstitutionalPrinciple):
        """Add a new constitutional principle."""
        self.principles.append(principle)

    def get_principle(self, principle_id: str) -> Optional[ConstitutionalPrinciple]:
        """Get a principle by ID."""
        for principle in self.principles:
            if principle.id == principle_id:
                return principle
        return None

    def validate_compliance(
        self,
        context: Dict[str, Any],
        required_categories: Optional[List[PrincipleCategory]] = None
    ) -> ComplianceReport:
        """
        Validate constitutional compliance for a given context.

        Args:
            context: Context data for validation
            required_categories: Optional list of principle categories to check

        Returns:
            ComplianceReport with validation results
        """
        principles_to_check = self.principles
        if required_categories:
            principles_to_check = [
                p for p in self.principles
                if p.category in required_categories
            ]

        passed = 0
        failed = 0
        violations = []
        total_weight = 0.0
        compliance_weight = 0.0

        for principle in principles_to_check:
            is_valid, reason = principle.validate(context)
            total_weight += principle.weight

            if is_valid:
                passed += 1
                compliance_weight += principle.weight
            else:
                failed += 1
                violations.append({
                    'principle_id': principle.id,
                    'principle_name': principle.name,
                    'category': principle.category.value,
                    'mandatory': principle.mandatory,
                    'reason': reason
                })

        # Calculate compliance score
        compliance_score = compliance_weight / total_weight if total_weight > 0 else 0.0

        # Determine overall compliance level
        if compliance_score >= 0.95:
            overall_compliance = ComplianceLevel.FULL
        elif compliance_score >= 0.75:
            overall_compliance = ComplianceLevel.PARTIAL
        elif compliance_score >= 0.50:
            overall_compliance = ComplianceLevel.MINIMAL
        else:
            overall_compliance = ComplianceLevel.NON_COMPLIANT

        # Check for mandatory violations
        mandatory_violations = [v for v in violations if v['mandatory']]
        if mandatory_violations:
            overall_compliance = ComplianceLevel.NON_COMPLIANT

        # Generate recommendations
        recommendations = []
        if violations:
            recommendations.append(f"Address {len(violations)} principle violation(s)")
        if mandatory_violations:
            recommendations.append("CRITICAL: Resolve mandatory principle violations")
        if compliance_score < 0.75:
            recommendations.append("Improve compliance score to at least 75%")

        report = ComplianceReport(
            timestamp=datetime.now(),
            overall_compliance=overall_compliance,
            compliance_score=compliance_score,
            principles_checked=len(principles_to_check),
            principles_passed=passed,
            principles_failed=failed,
            violations=violations,
            recommendations=recommendations,
            details={
                'total_weight': total_weight,
                'compliance_weight': compliance_weight,
                'mandatory_violations': len(mandatory_violations)
            }
        )

        self.compliance_history.append(report)
        return report

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get a summary of compliance history."""
        if not self.compliance_history:
            return {'message': 'No compliance history available'}

        total_checks = len(self.compliance_history)
        avg_score = sum(r.compliance_score for r in self.compliance_history) / total_checks

        compliance_levels = {}
        for level in ComplianceLevel:
            count = sum(1 for r in self.compliance_history if r.overall_compliance == level)
            compliance_levels[level.value] = count

        return {
            'total_compliance_checks': total_checks,
            'average_compliance_score': avg_score,
            'compliance_level_distribution': compliance_levels,
            'latest_compliance': self.compliance_history[-1].overall_compliance.value,
            'latest_score': self.compliance_history[-1].compliance_score
        }


# Global instance
constitutional_framework = ConstitutionalFramework()


def validate_operation(operation_context: Dict[str, Any]) -> ComplianceReport:
    """
    Convenience function to validate an operation's constitutional compliance.

    Args:
        operation_context: Context data for the operation

    Returns:
        ComplianceReport with validation results
    """
    return constitutional_framework.validate_compliance(operation_context)


if __name__ == "__main__":
    # Example usage
    print("CCMF Constitutional Framework - Example Usage")
    print("=" * 60)

    # Create a test context
    test_context = {
        'operation_type': 'file_read',
        'risk_assessment': 'low',
        'logging_enabled': True,
        'audit_trail': True,
        'resource_estimate': {'cpu': 'low', 'memory': 'medium'},
        'error_handling': True,
        'recovery_strategy': 'retry_with_backoff',
        'data_classification': 'public',
        'privacy_check': True,
        'ethical_review': True
    }

    # Validate compliance
    report = validate_operation(test_context)

    print(f"\nCompliance Report:")
    print(f"  Overall Compliance: {report.overall_compliance.value}")
    print(f"  Compliance Score: {report.compliance_score:.2%}")
    print(f"  Principles Checked: {report.principles_checked}")
    print(f"  Passed: {report.principles_passed}")
    print(f"  Failed: {report.principles_failed}")

    if report.violations:
        print(f"\n  Violations:")
        for v in report.violations:
            print(f"    - {v['principle_name']}: {v['reason']}")

    if report.recommendations:
        print(f"\n  Recommendations:")
        for rec in report.recommendations:
            print(f"    - {rec}")

    # Show compliance summary
    print(f"\n{'-' * 60}")
    summary = constitutional_framework.get_compliance_summary()
    print(f"\nCompliance Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

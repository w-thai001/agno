"""✅ Code Quality Validator Example

This example demonstrates using the Code Quality Validator FSA to validate
code against standards, security, and best practices.

Run `pip install agno openai` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.fsa.quality_validator import CodeQualityValidator


def main():
    """Demonstrate Code Quality Validator"""

    # Sample code to validate
    sample_code = """
import os

def calculate_total(items):
    # Calculate total price
    total = 0
    for item in items:
        if item['price'] > 0:
            total = total + item['price']
    return total

class UserManager:
    def __init__(self):
        self.api_key = "hardcoded_secret_key_12345"  # Security issue!

    def authenticate(self, username, password):
        # Missing input validation
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        # SQL injection vulnerability!
        return query
"""

    # Create validation agent
    validation_agent = Agent(
        name="QualityAgent",
        model=OpenAIChat(id="gpt-4o"),
        description="Expert at code quality, security, and best practices",
        markdown=True
    )

    # Create validator
    validator = CodeQualityValidator(
        name="PythonValidator",
        validation_agent=validation_agent,
        language="python",
        style_guide="pep8",
        min_overall_score=70.0,
        min_test_coverage=80.0,
        enable_style_check=True,
        enable_security_scan=True,
        debug_mode=True
    )

    # Validate the code
    result = validator.run({
        "code": sample_code,
        "language": "python"
    })

    print("\n" + "=" * 60)
    print("CODE QUALITY VALIDATION RESULTS")
    print("=" * 60)

    print(f"\nValidation Success: {result.success}")
    print(f"Code Passes Quality Standards: {result.passed}")

    print("\n📊 QUALITY METRICS:")
    print(f"   Overall Score: {result.metrics.overall_score:.1f}/100")
    print(f"   Style Score: {result.metrics.style_score:.1f}/100")
    print(f"   Complexity Score: {result.metrics.complexity_score:.1f}/100")
    print(f"   Security Score: {result.metrics.security_score:.1f}/100")
    print(f"   Test Coverage: {result.metrics.test_coverage:.1f}%")
    print(f"   Documentation Score: {result.metrics.documentation_score:.1f}/100")
    print(f"   Maintainability Index: {result.metrics.maintainability_index:.1f}/100")

    print(f"\n🐛 ISSUES FOUND: {len(result.issues)}")
    print(f"   Critical: {result.critical_issues}")
    print(f"   Errors: {result.errors}")
    print(f"   Warnings: {result.warnings}")
    print(f"   Info: {result.info}")
    print(f"   Auto-fixable: {result.auto_fixable_issues}")

    if result.issues:
        print("\n📋 DETAILED ISSUES:")
        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "error": "🟠",
                "warning": "🟡",
                "info": "🔵"
            }
            icon = severity_icon.get(issue.severity.value, "⚪")

            print(f"\n   {i}. {icon} [{issue.severity.value.upper()}] {issue.category.value}")
            print(f"      {issue.description}")
            print(f"      Location: {issue.location}")
            print(f"      Rule: {issue.rule_id}")
            print(f"      Suggestion: {issue.suggestion}")
            if issue.can_auto_fix:
                print(f"      ✨ Auto-fixable!")

    if result.recommendations:
        print("\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"   {i}. {rec}")

    print("\n" + validator.get_quality_report())

    # Show pass/fail
    if result.passed:
        print("\n✅ Code meets quality standards!")
    else:
        print("\n❌ Code does NOT meet quality standards. Please address the issues above.")


if __name__ == "__main__":
    main()

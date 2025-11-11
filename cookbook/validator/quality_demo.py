"""
FSA-2.1: Code Quality Validator - Demonstration

This demo showcases the Code Quality Validator's capabilities including:
- Multi-dimensional code analysis (syntax, style, security, performance, best practices)
- Integration with FSA-1.1 (Prompt Optimizer) for AI-assisted analysis
- Integration with FSA-1.2 (Code Template Library) for template-based validation
- Comprehensive quality scoring and actionable suggestions

The demo validates templates from FSA-1.2 to demonstrate the integrated system.

Run: python cookbook/validator/quality_demo.py
"""

from agno.optimizer import PromptOptimizer
from agno.templates import CodeTemplateLibrary, QualityLevel
from agno.validator import CodeQualityValidator


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_validation_result(result, code_name: str):
    """Print validation result in a formatted way."""
    report = result.report

    print(f"Code: {code_name}")
    print(f"Language: {report.language}")
    print(f"Length: {report.code_length} characters")
    print(f"\nOverall Score: {report.overall_score}/100")
    print(f"Status: {'✓ VALID' if result.is_valid else '✗ INVALID'}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")

    print(f"\nDimension Scores:")
    for dim_name, dim_score in report.dimensions.items():
        status = "✓" if dim_score.score >= 70 else "⚠" if dim_score.score >= 50 else "✗"
        print(f"  {status} {dim_name.replace('_', ' ').title()}: {dim_score.score}/100")

    print(f"\nSummary:")
    print(f"  {report.summary}")

    if result.top_issues:
        print(f"\nTop Issues ({len(result.top_issues)}):")
        for i, issue in enumerate(result.top_issues[:5], 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "ℹ️",
            }.get(issue.severity.value, "•")
            line_info = f" (line {issue.line})" if issue.line else ""
            print(f"  {i}. {severity_icon} [{issue.severity.value.upper()}] {issue.category}{line_info}")
            print(f"     {issue.message}")
            if issue.suggestion:
                print(f"     💡 {issue.suggestion}")

    print()


def demo_basic_validation():
    """Demonstrate basic code validation."""
    print_section("Demo 1: Basic Code Validation")

    validator = CodeQualityValidator()

    # Example 1: Good Python code
    good_python_code = '''
def calculate_average(numbers: list) -> float:
    """
    Calculate the average of a list of numbers.

    Args:
        numbers: List of numeric values

    Returns:
        Average value as float
    """
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")

    try:
        return sum(numbers) / len(numbers)
    except TypeError as e:
        raise TypeError(f"All values must be numeric: {e}")
'''

    print("Validating GOOD Python code:")
    print("-" * 80)
    result = validator.validateCode(good_python_code, "python")
    print_validation_result(result, "calculate_average function")

    # Example 2: Poor Python code with issues
    poor_python_code = '''
def calc(x):
    return eval("sum(x)/len(x)")
'''

    print("\n" + "=" * 80)
    print("Validating POOR Python code:")
    print("-" * 80)
    result = validator.validateCode(poor_python_code, "python")
    print_validation_result(result, "calc function (insecure)")


def demo_template_validation():
    """Demonstrate validation of templates from FSA-1.2."""
    print_section("Demo 2: FSA-1.2 Template Validation")

    validator = CodeQualityValidator()
    library = CodeTemplateLibrary()

    # Get all templates
    templates = library.get_all_templates()

    print(f"Validating {len(templates)} templates from FSA-1.2 Code Library\n")

    results = []

    for template in templates:
        print(f"Validating: {template.name} ({template.language})")
        result = validator.validateCode(template.code, template.language)
        results.append((template, result))
        print(f"  Score: {result.report.overall_score}/100 - {template.quality_level.value.upper()}")

    # Summary table
    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80 + "\n")

    print(f"{'Template Name':<40} {'Language':<12} {'Expected':<12} {'Score':<8}")
    print("-" * 80)

    for template, result in results:
        score = result.report.overall_score
        expected = template.quality_level.value
        status = "✓" if (
            (expected == "excellent" and score >= 90) or
            (expected == "good" and 70 <= score < 90) or
            (expected == "fair" and 50 <= score < 70) or
            (expected == "poor" and score < 50)
        ) else "⚠"

        print(f"{status} {template.name[:38]:<38} {template.language:<12} {expected:<12} {score:<8}")


def demo_template_comparison():
    """Demonstrate comparing code against templates."""
    print_section("Demo 3: Template Comparison")

    validator = CodeQualityValidator()
    library = CodeTemplateLibrary()

    # Get good and poor API templates
    good_template = library.get_template("py_api_good")
    poor_template = library.get_template("py_api_poor")

    if not good_template or not poor_template:
        print("Templates not found!")
        return

    # User's code to validate
    user_code = '''
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/data')
def get_data():
    data = {"key": "value"}
    return jsonify(data)
'''

    print("Comparing user code against templates:\n")

    # Compare with good template
    print("Comparison with GOOD template:")
    print("-" * 80)
    comparison_good = validator.compare_with_template(user_code, "python", "py_api_good")

    print(f"Template: {comparison_good['template']['name']}")
    print(f"Template Score: {comparison_good['template']['score']}/100")
    print(f"User Code Score: {comparison_good['code']['score']}/100")
    print(f"Difference: {comparison_good['score_difference']:+d}")

    print("\nDimension Comparison:")
    for dim, scores in comparison_good['dimension_comparison'].items():
        diff = scores['difference']
        icon = "✓" if diff >= 0 else "✗"
        print(f"  {icon} {dim.replace('_', ' ').title()}: {scores['code_score']} vs {scores['template_score']} ({diff:+d})")

    if comparison_good['lessons_learned']:
        print("\nLessons from Template:")
        for lesson in comparison_good['lessons_learned'][:5]:
            print(f"  • {lesson}")

    # Compare with poor template
    print("\n" + "=" * 80)
    print("Comparison with POOR template:")
    print("-" * 80)
    comparison_poor = validator.compare_with_template(user_code, "python", "py_api_poor")

    print(f"Template: {comparison_poor['template']['name']}")
    print(f"Template Score: {comparison_poor['template']['score']}/100")
    print(f"User Code Score: {comparison_poor['code']['score']}/100")
    print(f"Difference: {comparison_poor['score_difference']:+d}")
    print(f"\n✓ Your code is {comparison_poor['score_difference']} points better than the poor template!")


def demo_security_validation():
    """Demonstrate security-focused validation."""
    print_section("Demo 4: Security Vulnerability Detection")

    validator = CodeQualityValidator()
    library = CodeTemplateLibrary()

    # Test various security issues
    security_tests = [
        ("SQL Injection (Python)", library.get_template("py_db_query_poor").code),
        ("XSS Vulnerability (JavaScript)", library.get_template("js_xss_vulnerable").code),
        ("Safe Database Query (Python)", library.get_template("py_db_query_good").code),
    ]

    for test_name, code in security_tests:
        print(f"\nTesting: {test_name}")
        print("-" * 80)

        # Extract language from code
        language = "python" if "import" in code or "def" in code else "javascript"

        result = validator.validateCode(code, language)

        security_score = result.report.dimensions.get("security")
        if security_score:
            print(f"Security Score: {security_score.score}/100")

            if security_score.issues:
                print(f"\nSecurity Issues Found ({len(security_score.issues)}):")
                for issue in security_score.issues:
                    severity_icon = {
                        "critical": "🔴 CRITICAL",
                        "high": "🟠 HIGH",
                        "medium": "🟡 MEDIUM",
                        "low": "🟢 LOW",
                    }.get(issue.severity.value, "INFO")
                    print(f"  {severity_icon} - {issue.category}")
                    print(f"    {issue.message}")
                    if issue.suggestion:
                        print(f"    Fix: {issue.suggestion}")
            else:
                print("  ✓ No security issues detected")


def demo_dimension_scores():
    """Demonstrate detailed dimension scoring."""
    print_section("Demo 5: Dimension-by-Dimension Analysis")

    validator = CodeQualityValidator()

    # Complex code with various issues
    complex_code = '''
import sqlite3

password="admin123"

def getUserData(id):
    conn=sqlite3.connect('db.db')
    query="SELECT * FROM users WHERE id='"+str(id)+"'"
    result=conn.execute(query)
    x=result.fetchall()
    return x

for i in range(len(data)):
    print(data[i])
'''

    print("Analyzing complex Python code with multiple issues:\n")

    result = validator.validateCode(complex_code, "python")

    print(f"Overall Score: {result.report.overall_score}/100\n")

    # Show each dimension in detail
    for dim_name, dim_score in result.report.dimensions.items():
        print(f"\n{dim_name.replace('_', ' ').title()}: {dim_score.score}/100")
        print("-" * 60)

        if dim_score.issues:
            for issue in dim_score.issues:
                print(f"  • [{issue.severity.value}] {issue.message}")
        else:
            print("  ✓ No issues found")

        if dim_score.recommendations:
            print("  Recommendations:")
            for rec in dim_score.recommendations:
                print(f"    → {rec}")


def demo_suggestions():
    """Demonstrate actionable suggestions."""
    print_section("Demo 6: Actionable Suggestions")

    validator = CodeQualityValidator()

    problematic_code = '''
def process(data):
    result = eval(data)
    query = "SELECT * FROM table WHERE id=" + str(result)
    return query
'''

    print("Getting suggestions for problematic code:\n")

    result = validator.validateCode(problematic_code, "python")

    suggestions = validator.getSuggestions(result, limit=10)

    print(f"Overall Score: {result.report.overall_score}/100\n")
    print(f"Actionable Suggestions ({len(suggestions)}):\n")

    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}\n")


def demo_prompt_optimization():
    """Demonstrate FSA-1.1 Prompt Optimizer integration."""
    print_section("Demo 7: FSA-1.1 Prompt Optimizer Integration")

    validator = CodeQualityValidator()

    sample_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
'''

    print("Generating optimized prompts for different analysis types:\n")

    analysis_types = ["syntax", "security", "performance"]

    for analysis_type in analysis_types:
        print(f"\n{analysis_type.upper()} Analysis Prompt:")
        print("-" * 80)

        try:
            prompt = validator.get_optimized_prompt(sample_code, "python", analysis_type)
            # Show first 300 chars of prompt
            print(prompt[:300] + "...\n")
        except Exception as e:
            print(f"Error: {e}")


def demo_language_support():
    """Demonstrate multi-language support."""
    print_section("Demo 8: Multi-Language Support")

    validator = CodeQualityValidator()

    # Python example
    python_code = '''
def greet(name):
    """Greet a person by name."""
    return f"Hello, {name}!"
'''

    # JavaScript example
    javascript_code = '''
function greet(name) {
    /**
     * Greet a person by name
     * @param {string} name - Person's name
     * @returns {string} Greeting message
     */
    return `Hello, ${name}!`;
}
'''

    languages = [
        ("Python", python_code, "python"),
        ("JavaScript", javascript_code, "javascript"),
    ]

    for lang_name, code, lang_id in languages:
        print(f"\nValidating {lang_name} code:")
        print("-" * 80)

        result = validator.validateCode(code, lang_id)

        print(f"Score: {result.report.overall_score}/100")
        print(f"Status: {'✓ VALID' if result.is_valid else '✗ INVALID'}")

        dimension_summary = ", ".join(
            f"{dim}: {score.score}" for dim, score in result.report.dimensions.items()
        )
        print(f"Dimensions: {dimension_summary}")


def main():
    """Run all demos."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  FSA-2.1: CODE QUALITY VALIDATOR DEMONSTRATION  ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\nIntegrated with:")
    print("  • FSA-1.1: Prompt Optimizer (AI-assisted analysis)")
    print("  • FSA-1.2: Code Template Library (validation test cases)")

    try:
        demo_basic_validation()
        demo_template_validation()
        demo_template_comparison()
        demo_security_validation()
        demo_dimension_scores()
        demo_suggestions()
        demo_prompt_optimization()
        demo_language_support()

        # Final summary
        print_section("Demo Complete!")
        print("The Code Quality Validator successfully demonstrated:")
        print("  ✓ Multi-dimensional code analysis (syntax, style, security, performance, best practices)")
        print("  ✓ Integration with FSA-1.2 Code Template Library")
        print("  ✓ Template comparison and lessons learned")
        print("  ✓ Security vulnerability detection")
        print("  ✓ Actionable suggestions and recommendations")
        print("  ✓ Integration with FSA-1.1 Prompt Optimizer")
        print("  ✓ Multi-language support (Python, JavaScript)")
        print("\nKey Features:")
        print("  • validateCode(code, language) - Comprehensive validation")
        print("  • getQualityScore(result) - Extract quality score")
        print("  • getSuggestions(result) - Get actionable suggestions")
        print("  • compare_with_template() - Compare against templates")
        print("  • get_optimized_prompt() - Generate AI analysis prompts")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

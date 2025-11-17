#!/usr/bin/env python3
"""
Version Manager FSA Demo

This script demonstrates the capabilities of the Version Manager FSA including:
- Semantic version parsing and validation
- Version comparison and compatibility checking
- Migration path generation
- Dependency conflict resolution
- Version bumping with changelog integration
"""

from datetime import datetime
import sys
from pathlib import Path

# Add libs/agno to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "agno"))

from agno.fsa.version_manager import (
    VersionManagerFSA,
    Version,
    Migration,
    Changelog,
    VersionState,
)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_version_parsing():
    """Demonstrate version parsing capabilities."""
    print_header("1. Version Parsing and Validation")

    fsa = VersionManagerFSA()

    # Parse various version formats
    versions = [
        "1.2.3",
        "2.0.0-alpha.1",
        "3.1.4-beta.2+build.123",
        "0.1.0",
        "10.0.0+20231117",
    ]

    print("Parsing semantic versions:")
    for version_str in versions:
        version = fsa.parse_version(version_str)
        print(f"  {version_str:30} -> {version}")
        print(f"    Major: {version.major}, Minor: {version.minor}, Patch: {version.patch}")
        if version.prerelease:
            print(f"    Prerelease: {version.prerelease}")
        if version.metadata:
            print(f"    Metadata: {version.metadata}")
        print()

    # Try invalid version
    print("Attempting to parse invalid version:")
    try:
        fsa.parse_version("invalid.version")
    except ValueError as e:
        print(f"  ✗ Error: {e}")
        print(f"  State: {fsa.state}")


def demo_version_comparison():
    """Demonstrate version comparison."""
    print_header("2. Version Comparison")

    fsa = VersionManagerFSA()

    comparisons = [
        ("1.2.3", "1.2.4"),
        ("2.0.0", "1.9.9"),
        ("1.5.0", "1.5.0"),
        ("3.0.0-alpha", "3.0.0"),
        ("2.1.0", "2.0.5"),
    ]

    print("Comparing versions:")
    for v1_str, v2_str in comparisons:
        v1 = fsa.parse_version(v1_str)
        v2 = fsa.parse_version(v2_str)
        result = fsa.compare_versions(v1, v2)

        if result < 0:
            symbol = "<"
        elif result > 0:
            symbol = ">"
        else:
            symbol = "=="

        print(f"  {v1_str:20} {symbol:3} {v2_str:20}")


def demo_compatibility_checking():
    """Demonstrate version compatibility checking."""
    print_header("3. Version Compatibility Checking")

    fsa = VersionManagerFSA()

    compatibility_tests = [
        ("1.5.0", "1.2.0", "Minor upgrade"),
        ("1.2.5", "1.2.3", "Patch upgrade"),
        ("2.0.0", "1.9.0", "Major version change"),
        ("1.2.0", "1.3.0", "Lower version"),
        ("0.5.2", "0.5.0", "0.x patch upgrade"),
        ("0.6.0", "0.5.0", "0.x minor change"),
    ]

    print("Testing compatibility:")
    for current_str, required_str, description in compatibility_tests:
        current = fsa.parse_version(current_str)
        required = fsa.parse_version(required_str)
        compatible = fsa.is_compatible(current, required)

        status = "✓ Compatible" if compatible else "✗ Incompatible"
        print(f"  {current_str:15} vs {required_str:15} ({description:20}): {status}")


def demo_migration_paths():
    """Demonstrate migration path generation."""
    print_header("4. Migration Path Generation")

    fsa = VersionManagerFSA()

    # Add some custom migrations
    v1_0 = fsa.parse_version("1.0.0")
    v1_5 = fsa.parse_version("1.5.0")
    v2_0 = fsa.parse_version("2.0.0")

    migration1 = Migration(
        from_version=v1_0,
        to_version=v1_5,
        description="Add new features and performance improvements",
        steps=[
            "Update configuration file format",
            "Run database migration script",
            "Update API client libraries",
        ]
    )

    migration2 = Migration(
        from_version=v1_5,
        to_version=v2_0,
        description="Major API redesign",
        breaking_changes=[
            "REST API endpoints restructured",
            "Authentication method changed to OAuth2",
            "Deprecated functions removed",
        ],
        steps=[
            "Review API documentation",
            "Update all API calls to new endpoints",
            "Implement OAuth2 authentication",
            "Remove usage of deprecated functions",
            "Run comprehensive integration tests",
        ]
    )

    fsa.add_migration(migration1)
    fsa.add_migration(migration2)

    # Generate migration paths
    migrations = [
        (v1_0, v1_5),
        (v1_5, v2_0),
        (v1_0, v2_0),
    ]

    print("Migration paths:")
    for from_v, to_v in migrations:
        print(f"\n  Upgrading from {from_v} to {to_v}:")
        path = fsa.get_migration_path(from_v, to_v)

        for i, migration in enumerate(path, 1):
            print(f"\n    Step {i}: {migration.description}")
            print(f"    Version: {migration.from_version} -> {migration.to_version}")

            if migration.breaking_changes:
                print(f"    Breaking Changes:")
                for change in migration.breaking_changes:
                    print(f"      - {change}")

            if migration.steps:
                print(f"    Migration Steps:")
                for step in migration.steps:
                    print(f"      {step}")


def demo_upgrade_validation():
    """Demonstrate upgrade validation."""
    print_header("5. Upgrade Validation")

    fsa = VersionManagerFSA()

    upgrades = [
        ("1.0.0", "1.5.0", "Minor upgrade"),
        ("1.9.9", "2.0.0", "Major upgrade"),
        ("1.2.3", "1.2.3", "Same version"),
    ]

    print("Validating upgrades:")
    for from_str, to_str, description in upgrades:
        from_v = fsa.parse_version(from_str)
        to_v = fsa.parse_version(to_str)

        try:
            is_valid = fsa.validate_upgrade(from_v, to_v)
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"  {from_str:15} -> {to_str:15} ({description:20}): {status}")
        except ValueError as e:
            print(f"  {from_str:15} -> {to_str:15} ({description:20}): ✗ Error: {e}")

    # Try invalid downgrade
    print("\n  Testing downgrade (should fail):")
    try:
        from_v = fsa.parse_version("2.0.0")
        to_v = fsa.parse_version("1.0.0")
        fsa.validate_upgrade(from_v, to_v)
    except ValueError as e:
        print(f"    ✓ Correctly rejected: {e}")


def demo_conflict_resolution():
    """Demonstrate dependency conflict resolution."""
    print_header("6. Dependency Conflict Resolution")

    fsa = VersionManagerFSA()

    # Example 1: Simple dependencies
    print("Example 1: Simple dependencies (no conflicts)")
    dependencies1 = {
        "requests": "2.28.0",
        "numpy": "1.24.0",
        "pandas": "1.5.0",
    }

    print("  Dependencies:")
    for package, version in dependencies1.items():
        print(f"    {package}: {version}")

    resolved1 = fsa.resolve_conflicts(dependencies1)
    print("\n  Resolved versions:")
    for package, version in resolved1.items():
        print(f"    {package}: {version}")

    # Example 2: Constraint-based dependencies
    print("\n\nExample 2: Constraint-based dependencies")
    dependencies2 = {
        "flask": ">=2.0.0",
        "werkzeug": "^2.2.0",
        "jinja2": "~3.0.0",
        "click": "8.1.3",
    }

    print("  Dependencies:")
    for package, constraint in dependencies2.items():
        print(f"    {package}: {constraint}")

    resolved2 = fsa.resolve_conflicts(dependencies2)
    print("\n  Resolved versions:")
    for package, version in resolved2.items():
        print(f"    {package}: {version}")

    # Example 3: Try conflicting versions
    print("\n\nExample 3: Attempting to resolve conflicting versions")
    print("  Note: This is a simplified example. Real conflict detection")
    print("  would require checking actual compatibility between versions.")


def demo_version_bumping():
    """Demonstrate version bumping."""
    print_header("7. Version Bumping")

    fsa = VersionManagerFSA()

    current = fsa.parse_version("1.2.3")

    print(f"Current version: {current}\n")

    bump_types = ["patch", "minor", "major"]

    for bump_type in bump_types:
        new_version = fsa.bump_version(current, bump_type)
        print(f"  Bump {bump_type:10} -> {new_version}")


def demo_changelog():
    """Demonstrate changelog functionality."""
    print_header("8. Changelog Management")

    fsa = VersionManagerFSA()

    # Create versions
    v1_0 = fsa.parse_version("1.0.0")
    v1_1 = fsa.parse_version("1.1.0")
    v1_2 = fsa.parse_version("1.2.0")
    v2_0 = fsa.parse_version("2.0.0")

    # Add changelogs
    changelog_1_1 = Changelog(
        version=v1_1,
        date=datetime(2023, 6, 15),
        changes=[
            "Added user authentication system",
            "Improved error handling",
            "Performance optimizations for database queries",
        ],
        deprecations=[
            "Old session management API (will be removed in 2.0)",
        ]
    )

    changelog_1_2 = Changelog(
        version=v1_2,
        date=datetime(2023, 9, 1),
        changes=[
            "Added export functionality",
            "New dashboard widgets",
            "Enhanced logging capabilities",
        ]
    )

    changelog_2_0 = Changelog(
        version=v2_0,
        date=datetime(2023, 11, 17),
        changes=[
            "Complete UI redesign",
            "New REST API v2",
            "Microservices architecture",
            "Real-time collaboration features",
        ],
        breaking_changes=[
            "API v1 removed",
            "Database schema updated (migration required)",
            "Configuration file format changed",
        ],
        deprecations=[
            "Legacy import format",
        ]
    )

    fsa.add_changelog(changelog_1_1)
    fsa.add_changelog(changelog_1_2)
    fsa.add_changelog(changelog_2_0)

    # Get changelog between versions
    print(f"Changelog from {v1_0} to {v2_0}:\n")

    changelogs = fsa.get_changelog(v1_0, v2_0)

    for changelog in changelogs:
        print(f"  Version {changelog.version} ({changelog.date.strftime('%Y-%m-%d')})")
        print(f"  {'-' * 60}")

        if changelog.changes:
            print(f"  Changes:")
            for change in changelog.changes:
                print(f"    + {change}")

        if changelog.breaking_changes:
            print(f"\n  ⚠ Breaking Changes:")
            for change in changelog.breaking_changes:
                print(f"    ! {change}")

        if changelog.deprecations:
            print(f"\n  Deprecations:")
            for dep in changelog.deprecations:
                print(f"    - {dep}")

        print()


def demo_fsa_states():
    """Demonstrate FSA state transitions."""
    print_header("9. FSA State Transitions")

    fsa = VersionManagerFSA()

    print(f"Initial state: {fsa.state}\n")

    # Parse version
    print("Parsing version '1.2.3'...")
    v1 = fsa.parse_version("1.2.3")
    print(f"  State after parsing: {fsa.state}")

    # Compare versions
    print("\nComparing versions...")
    v2 = fsa.parse_version("2.0.0")
    fsa.compare_versions(v1, v2)
    print(f"  State after comparison: {fsa.state}")

    # Resolve conflicts
    print("\nResolving dependency conflicts...")
    fsa.resolve_conflicts({"package": "1.0.0"})
    print(f"  State after resolution: {fsa.state}")

    # Trigger error
    print("\nAttempting to parse invalid version...")
    try:
        fsa.parse_version("invalid")
    except ValueError:
        pass
    print(f"  State after error: {fsa.state}")
    print(f"  Error message: {fsa.error_message}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Version Manager FSA - Comprehensive Demo".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    try:
        demo_version_parsing()
        demo_version_comparison()
        demo_compatibility_checking()
        demo_migration_paths()
        demo_upgrade_validation()
        demo_conflict_resolution()
        demo_version_bumping()
        demo_changelog()
        demo_fsa_states()

        print_header("Demo Complete!")
        print("The Version Manager FSA successfully demonstrated:")
        print("  ✓ Semantic version parsing and validation")
        print("  ✓ Version comparison and ordering")
        print("  ✓ Compatibility checking with semantic versioning rules")
        print("  ✓ Migration path generation with custom migrations")
        print("  ✓ Upgrade validation and downgrade prevention")
        print("  ✓ Dependency conflict resolution")
        print("  ✓ Automatic version bumping (major/minor/patch)")
        print("  ✓ Changelog management and querying")
        print("  ✓ FSA state transitions and error handling")
        print()

    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

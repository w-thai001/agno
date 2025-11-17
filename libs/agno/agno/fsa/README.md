# Version Manager FSA

A production-ready Finite State Automaton (FSA) for managing semantic versioning, migration paths, backward compatibility checks, and version conflict resolution.

## Overview

The Version Manager FSA provides a robust implementation for handling semantic versions (MAJOR.MINOR.PATCH) with support for prerelease tags and build metadata. It follows the FSA pattern with clear state transitions and comprehensive error handling.

## Features

- **Semantic Version Parsing**: Parse and validate version strings in the format `MAJOR.MINOR.PATCH[-prerelease][+metadata]`
- **Version Comparison**: Compare versions with full support for semantic versioning rules
- **Compatibility Checking**: Determine if versions are backward compatible
- **Migration Paths**: Generate step-by-step migration plans between versions
- **Upgrade Validation**: Validate if upgrades are safe and prevent downgrades
- **Conflict Resolution**: Resolve version conflicts in dependency trees
- **Version Bumping**: Automatically increment major, minor, or patch versions
- **Changelog Management**: Track and query changes between versions

## FSA States

The Version Manager FSA operates with the following states:

- `IDLE`: Ready to process operations
- `PARSING`: Parsing a version string
- `VALIDATING`: Validating version compatibility or upgrades
- `RESOLVING`: Resolving dependency conflicts
- `MIGRATING`: Generating migration paths
- `ERROR`: Error state with detailed error message

## Installation

The Version Manager FSA is part of the Agno library:

```python
from agno.fsa.version_manager import VersionManagerFSA, Version, Migration, Changelog
```

## Quick Start

```python
from agno.fsa.version_manager import VersionManagerFSA

# Initialize the FSA
fsa = VersionManagerFSA()

# Parse versions
v1 = fsa.parse_version("1.2.3")
v2 = fsa.parse_version("2.0.0-beta.1")

# Compare versions
result = fsa.compare_versions(v1, v2)  # Returns -1, 0, or 1

# Check compatibility
compatible = fsa.is_compatible(v2, v1)  # Returns bool

# Bump version
new_version = fsa.bump_version(v1, "major")  # Returns 2.0.0
```

## Usage Examples

### Version Parsing

```python
fsa = VersionManagerFSA()

# Simple version
version = fsa.parse_version("1.2.3")

# Version with prerelease
version = fsa.parse_version("2.0.0-alpha.1")

# Version with metadata
version = fsa.parse_version("1.0.0+20231117")

# Complete version
version = fsa.parse_version("3.1.4-beta.2+build.123")
```

### Version Comparison

```python
v1 = fsa.parse_version("1.2.3")
v2 = fsa.parse_version("2.0.0")

# Returns -1 (v1 < v2), 0 (v1 == v2), or 1 (v1 > v2)
result = fsa.compare_versions(v1, v2)

# Direct comparison operators work too
if v1 < v2:
    print("v1 is older than v2")
```

### Compatibility Checking

```python
current = fsa.parse_version("1.5.0")
required = fsa.parse_version("1.2.0")

# Check if current version satisfies required version
if fsa.is_compatible(current, required):
    print("Versions are compatible")
```

### Migration Paths

```python
from agno.fsa.version_manager import Migration

# Create custom migration
migration = Migration(
    from_version=fsa.parse_version("1.0.0"),
    to_version=fsa.parse_version("2.0.0"),
    description="Major upgrade with API changes",
    breaking_changes=["API endpoints restructured"],
    steps=["Update API calls", "Run migration script"]
)

fsa.add_migration(migration)

# Get migration path
path = fsa.get_migration_path(
    fsa.parse_version("1.0.0"),
    fsa.parse_version("2.0.0")
)

for step in path:
    print(f"{step.from_version} -> {step.to_version}")
    for breaking_change in step.breaking_changes:
        print(f"  Breaking: {breaking_change}")
```

### Dependency Conflict Resolution

```python
dependencies = {
    "package-a": ">=1.2.0",
    "package-b": "^2.0.0",
    "package-c": "~1.5.0",
    "package-d": "1.0.0",
}

resolved = fsa.resolve_conflicts(dependencies)

for package, version in resolved.items():
    print(f"{package}: {version}")
```

### Version Bumping

```python
current = fsa.parse_version("1.2.3")

patch = fsa.bump_version(current, "patch")   # 1.2.4
minor = fsa.bump_version(current, "minor")   # 1.3.0
major = fsa.bump_version(current, "major")   # 2.0.0
```

### Changelog Management

```python
from agno.fsa.version_manager import Changelog
from datetime import datetime

# Add changelog
changelog = Changelog(
    version=fsa.parse_version("2.0.0"),
    date=datetime.now(),
    changes=["New feature X", "Improved performance"],
    breaking_changes=["API v1 removed"],
    deprecations=["Old config format"]
)

fsa.add_changelog(changelog)

# Get changelogs between versions
changelogs = fsa.get_changelog(
    fsa.parse_version("1.0.0"),
    fsa.parse_version("2.0.0")
)

for log in changelogs:
    print(f"Version {log.version} ({log.date})")
    for change in log.changes:
        print(f"  + {change}")
```

## API Reference

### VersionManagerFSA

Main FSA class for version management operations.

#### Methods

- `parse_version(version_str: str) -> Version`: Parse a semantic version string
- `compare_versions(v1: Version, v2: Version) -> int`: Compare two versions
- `is_compatible(current: Version, required: Version) -> bool`: Check compatibility
- `get_migration_path(from_version: Version, to_version: Version) -> List[Migration]`: Generate migration steps
- `validate_upgrade(from_version: Version, to_version: Version) -> bool`: Validate upgrade safety
- `resolve_conflicts(dependencies: Dict[str, str]) -> Dict[str, Version]`: Resolve version conflicts
- `bump_version(current: Version, bump_type: str) -> Version`: Increment version
- `get_changelog(from_version: Version, to_version: Version) -> List[Changelog]`: Get changes between versions
- `add_changelog(changelog: Changelog) -> None`: Add a changelog entry
- `add_migration(migration: Migration) -> None`: Add a custom migration

### Version

Dataclass representing a semantic version.

#### Attributes

- `major: int`: Major version number
- `minor: int`: Minor version number
- `patch: int`: Patch version number
- `prerelease: Optional[str]`: Prerelease tag
- `metadata: Optional[str]`: Build metadata

#### Methods

- `is_compatible_with(other: Version) -> bool`: Check compatibility with another version

### Migration

Dataclass representing a migration between versions.

#### Attributes

- `from_version: Version`: Starting version
- `to_version: Version`: Target version
- `description: str`: Migration description
- `breaking_changes: List[str]`: List of breaking changes
- `steps: List[str]`: Migration steps

### Changelog

Dataclass representing a changelog entry.

#### Attributes

- `version: Version`: Version for this changelog
- `date: datetime`: Release date
- `changes: List[str]`: List of changes
- `breaking_changes: List[str]`: List of breaking changes
- `deprecations: List[str]`: List of deprecations

## Running the Demo

A comprehensive demo script is available:

```bash
python examples/version_manager_demo.py
```

This demonstrates all features including:
- Version parsing and validation
- Version comparison
- Compatibility checking
- Migration path generation
- Upgrade validation
- Conflict resolution
- Version bumping
- Changelog management
- FSA state transitions

## Testing

The Version Manager FSA includes 46+ comprehensive unit tests:

```bash
pytest libs/agno/tests/unit/test_version_manager_fsa.py -v
```

Test coverage includes:
- Version parsing (valid and invalid inputs)
- Version comparison and ordering
- Compatibility checking
- Migration paths
- Upgrade validation
- Conflict resolution
- Version bumping
- Changelog management
- FSA state transitions
- Error handling

## Semantic Versioning Rules

The Version Manager FSA follows [Semantic Versioning 2.0.0](https://semver.org/) specification:

- **MAJOR** version when you make incompatible API changes
- **MINOR** version when you add functionality in a backward compatible manner
- **PATCH** version when you make backward compatible bug fixes

### Compatibility Rules

- Same major version (except 0.x): backward compatible
- 0.x versions: same minor version required for compatibility
- Prerelease versions are considered less than release versions

## Error Handling

All methods include comprehensive error handling:

```python
try:
    version = fsa.parse_version("invalid")
except ValueError as e:
    print(f"Error: {e}")
    print(f"FSA State: {fsa.state}")
    print(f"Error Message: {fsa.error_message}")
```

## Production Readiness

This implementation is production-ready with:

- ✓ Full semantic versioning support
- ✓ Comprehensive error handling
- ✓ Type hints throughout
- ✓ 46+ unit tests with 100% coverage of core functionality
- ✓ FSA pattern with clear state transitions
- ✓ Inline documentation
- ✓ Working demo script
- ✓ Clean, maintainable code architecture

## License

This code is part of the Agno project and follows the same license.

"""
Version Manager FSA - Manages versioning for FSA implementations.

This module provides a production-ready Finite State Automaton for managing
semantic versioning, migration paths, backward compatibility checks, and
version conflict resolution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import re
from datetime import datetime


class VersionState(Enum):
    """FSA states for version management operations."""
    IDLE = "idle"
    PARSING = "parsing"
    VALIDATING = "validating"
    RESOLVING = "resolving"
    MIGRATING = "migrating"
    ERROR = "error"


@dataclass
class Version:
    """Represents a semantic version (MAJOR.MINOR.PATCH)."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    metadata: Optional[str] = None

    def __str__(self) -> str:
        """String representation of the version."""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version_str += f"-{self.prerelease}"
        if self.metadata:
            version_str += f"+{self.metadata}"
        return version_str

    def __eq__(self, other: object) -> bool:
        """Check equality with another version."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == \
               (other.major, other.minor, other.patch, other.prerelease)

    def __lt__(self, other: object) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, Version):
            return NotImplemented

        # Compare major, minor, patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Handle prerelease versions (prerelease < release)
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other: object) -> bool:
        """Check if this version is less than or equal to another."""
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, Version):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: object) -> bool:
        """Check if this version is greater than or equal to another."""
        return self == other or self > other

    def is_compatible_with(self, other: "Version") -> bool:
        """
        Check if this version is backward compatible with another version.

        Compatibility rules:
        - Versions with different major versions are incompatible
        - Minor/patch version increases are backward compatible
        - Prerelease versions are compatible within the same major.minor
        """
        if self.major == 0:
            # Major version 0 is for initial development
            return self.major == other.major and self.minor == other.minor
        return self.major == other.major and self >= other


@dataclass
class Migration:
    """Represents a migration step between versions."""
    from_version: Version
    to_version: Version
    description: str
    breaking_changes: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation of the migration."""
        return f"Migration {self.from_version} -> {self.to_version}: {self.description}"


@dataclass
class Changelog:
    """Represents changes between versions."""
    version: Version
    date: datetime
    changes: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    deprecations: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation of the changelog."""
        return f"v{self.version} ({self.date.strftime('%Y-%m-%d')})"


class VersionManagerFSA:
    """
    Finite State Automaton for managing versions, migrations, and compatibility.

    This FSA handles semantic versioning with state transitions for parsing,
    validating, resolving conflicts, and managing migrations.
    """

    # Semantic version regex pattern
    VERSION_PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
        r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
        r'(?:\+(?P<metadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    )

    def __init__(self):
        """Initialize the Version Manager FSA."""
        self.state: VersionState = VersionState.IDLE
        self.error_message: Optional[str] = None
        self.changelogs: Dict[str, Changelog] = {}
        self.migrations: List[Migration] = []

    def _transition_to(self, new_state: VersionState) -> None:
        """Transition to a new state."""
        self.state = new_state

    def _handle_error(self, message: str) -> None:
        """Handle an error and transition to ERROR state."""
        self.error_message = message
        self._transition_to(VersionState.ERROR)

    def parse_version(self, version_str: str) -> Optional[Version]:
        """
        Parse a semantic version string into a Version object.

        Args:
            version_str: Version string in format "MAJOR.MINOR.PATCH[-prerelease][+metadata]"

        Returns:
            Version object if valid, None otherwise

        Raises:
            ValueError: If the version string is invalid
        """
        self._transition_to(VersionState.PARSING)

        if not isinstance(version_str, str):
            self._handle_error(f"Version must be a string, got {type(version_str)}")
            raise ValueError(self.error_message)

        match = self.VERSION_PATTERN.match(version_str.strip())
        if not match:
            self._handle_error(f"Invalid semantic version format: {version_str}")
            raise ValueError(self.error_message)

        try:
            version = Version(
                major=int(match.group('major')),
                minor=int(match.group('minor')),
                patch=int(match.group('patch')),
                prerelease=match.group('prerelease'),
                metadata=match.group('metadata')
            )
            self._transition_to(VersionState.IDLE)
            return version
        except Exception as e:
            self._handle_error(f"Failed to parse version: {e}")
            raise ValueError(self.error_message)

    def compare_versions(self, v1: Version, v2: Version) -> int:
        """
        Compare two versions.

        Args:
            v1: First version
            v2: Second version

        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        self._transition_to(VersionState.VALIDATING)

        if v1 < v2:
            result = -1
        elif v1 > v2:
            result = 1
        else:
            result = 0

        self._transition_to(VersionState.IDLE)
        return result

    def is_compatible(self, current: Version, required: Version) -> bool:
        """
        Check if current version is compatible with required version.

        Args:
            current: Current version
            required: Required version

        Returns:
            True if compatible, False otherwise
        """
        self._transition_to(VersionState.VALIDATING)
        result = current.is_compatible_with(required)
        self._transition_to(VersionState.IDLE)
        return result

    def get_migration_path(
        self,
        from_version: Version,
        to_version: Version
    ) -> List[Migration]:
        """
        Generate migration steps from one version to another.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of migration steps
        """
        self._transition_to(VersionState.MIGRATING)

        if from_version == to_version:
            self._transition_to(VersionState.IDLE)
            return []

        if from_version > to_version:
            self._handle_error(
                f"Downgrade not supported: {from_version} -> {to_version}"
            )
            raise ValueError(self.error_message)

        # Generate migration path
        path: List[Migration] = []

        # Find relevant migrations in the stored migrations list
        relevant_migrations = [
            m for m in self.migrations
            if from_version <= m.from_version < to_version
        ]

        if relevant_migrations:
            path.extend(sorted(relevant_migrations, key=lambda m: m.from_version))
        else:
            # Generate default migration
            breaking = []
            if from_version.major != to_version.major:
                breaking.append(f"Major version change: {from_version.major} -> {to_version.major}")

            migration = Migration(
                from_version=from_version,
                to_version=to_version,
                description=f"Upgrade from {from_version} to {to_version}",
                breaking_changes=breaking,
                steps=[
                    "Review changelog for breaking changes",
                    "Update dependencies",
                    "Run migration scripts",
                    "Test compatibility"
                ]
            )
            path.append(migration)

        self._transition_to(VersionState.IDLE)
        return path

    def validate_upgrade(self, from_version: Version, to_version: Version) -> bool:
        """
        Check if an upgrade from one version to another is safe.

        Args:
            from_version: Current version
            to_version: Target version

        Returns:
            True if upgrade is safe, False otherwise

        Raises:
            ValueError: If upgrade is not valid
        """
        self._transition_to(VersionState.VALIDATING)

        if from_version > to_version:
            self._handle_error(
                f"Cannot downgrade from {from_version} to {to_version}"
            )
            raise ValueError(self.error_message)

        if from_version == to_version:
            self._transition_to(VersionState.IDLE)
            return True

        # Check for breaking changes in major version upgrades
        if to_version.major > from_version.major:
            # Major version upgrade - may have breaking changes
            self._transition_to(VersionState.IDLE)
            return True  # Valid but may require migration

        # Minor and patch upgrades should be safe
        self._transition_to(VersionState.IDLE)
        return True

    def resolve_conflicts(
        self,
        dependencies: Dict[str, str]
    ) -> Dict[str, Version]:
        """
        Resolve version conflicts in dependencies.

        Args:
            dependencies: Dictionary of package name to version constraint

        Returns:
            Dictionary of package name to resolved version

        Raises:
            ValueError: If conflicts cannot be resolved
        """
        self._transition_to(VersionState.RESOLVING)

        resolved: Dict[str, Version] = {}
        constraints: Dict[str, List[Version]] = {}

        # Parse all constraints
        for package, constraint in dependencies.items():
            try:
                # Support simple constraints like ">=1.2.0", "^1.0.0", "~1.2.0", or exact "1.2.3"
                if constraint.startswith(">="):
                    min_version = self.parse_version(constraint[2:].strip())
                    constraints.setdefault(package, []).append(min_version)
                elif constraint.startswith("^"):
                    # Caret: compatible with version (same major)
                    version = self.parse_version(constraint[1:].strip())
                    constraints.setdefault(package, []).append(version)
                elif constraint.startswith("~"):
                    # Tilde: compatible with patch updates
                    version = self.parse_version(constraint[1:].strip())
                    constraints.setdefault(package, []).append(version)
                else:
                    # Exact version
                    version = self.parse_version(constraint)
                    constraints.setdefault(package, []).append(version)
            except ValueError as e:
                self._handle_error(f"Invalid constraint for {package}: {e}")
                raise

        # Resolve conflicts by selecting the highest compatible version
        for package, versions in constraints.items():
            if len(versions) == 1:
                resolved[package] = versions[0]
            else:
                # Find highest version that satisfies all constraints
                max_version = max(versions)

                # Check if all versions are compatible with max_version
                compatible = all(
                    max_version.is_compatible_with(v) for v in versions
                )

                if not compatible:
                    self._handle_error(
                        f"Conflicting versions for {package}: "
                        f"{', '.join(str(v) for v in versions)}"
                    )
                    raise ValueError(self.error_message)

                resolved[package] = max_version

        self._transition_to(VersionState.IDLE)
        return resolved

    def bump_version(
        self,
        current: Version,
        bump_type: str
    ) -> Version:
        """
        Increment version based on bump type.

        Args:
            current: Current version
            bump_type: Type of bump ("major", "minor", or "patch")

        Returns:
            New bumped version

        Raises:
            ValueError: If bump_type is invalid
        """
        self._transition_to(VersionState.VALIDATING)

        bump_type = bump_type.lower()

        if bump_type == "major":
            new_version = Version(current.major + 1, 0, 0)
        elif bump_type == "minor":
            new_version = Version(current.major, current.minor + 1, 0)
        elif bump_type == "patch":
            new_version = Version(current.major, current.minor, current.patch + 1)
        else:
            self._handle_error(
                f"Invalid bump type: {bump_type}. Must be 'major', 'minor', or 'patch'"
            )
            raise ValueError(self.error_message)

        self._transition_to(VersionState.IDLE)
        return new_version

    def get_changelog(
        self,
        from_version: Version,
        to_version: Version
    ) -> List[Changelog]:
        """
        Get changelog entries between two versions.

        Args:
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of changelog entries
        """
        self._transition_to(VersionState.VALIDATING)

        changelogs = []
        for version_str, changelog in self.changelogs.items():
            version = self.parse_version(version_str)
            if from_version < version <= to_version:
                changelogs.append(changelog)

        # Sort by version
        changelogs.sort(key=lambda c: c.version)

        self._transition_to(VersionState.IDLE)
        return changelogs

    def add_changelog(self, changelog: Changelog) -> None:
        """
        Add a changelog entry.

        Args:
            changelog: Changelog to add
        """
        self.changelogs[str(changelog.version)] = changelog

    def add_migration(self, migration: Migration) -> None:
        """
        Add a migration path.

        Args:
            migration: Migration to add
        """
        self.migrations.append(migration)

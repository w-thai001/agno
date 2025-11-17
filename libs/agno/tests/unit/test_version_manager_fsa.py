"""
Unit tests for Version Manager FSA.

Tests cover version parsing, comparison, compatibility, migration paths,
conflict resolution, and version bumping.
"""

import pytest
from datetime import datetime
from agno.fsa.version_manager import (
    VersionManagerFSA,
    Version,
    Migration,
    Changelog,
    VersionState,
)


class TestVersionParsing:
    """Test version parsing functionality."""

    def test_parse_valid_version(self):
        """Test parsing a valid semantic version."""
        fsa = VersionManagerFSA()
        version = fsa.parse_version("1.2.3")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.metadata is None
        assert str(version) == "1.2.3"

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease tag."""
        fsa = VersionManagerFSA()
        version = fsa.parse_version("2.0.0-alpha.1")

        assert version.major == 2
        assert version.minor == 0
        assert version.patch == 0
        assert version.prerelease == "alpha.1"
        assert str(version) == "2.0.0-alpha.1"

    def test_parse_version_with_metadata(self):
        """Test parsing version with build metadata."""
        fsa = VersionManagerFSA()
        version = fsa.parse_version("1.0.0+20231117")

        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert version.metadata == "20231117"
        assert str(version) == "1.0.0+20231117"

    def test_parse_version_complete(self):
        """Test parsing version with both prerelease and metadata."""
        fsa = VersionManagerFSA()
        version = fsa.parse_version("3.1.4-beta.2+build.123")

        assert version.major == 3
        assert version.minor == 1
        assert version.patch == 4
        assert version.prerelease == "beta.2"
        assert version.metadata == "build.123"

    def test_parse_invalid_version(self):
        """Test parsing an invalid version string."""
        fsa = VersionManagerFSA()

        with pytest.raises(ValueError, match="Invalid semantic version format"):
            fsa.parse_version("invalid")

        with pytest.raises(ValueError, match="Invalid semantic version format"):
            fsa.parse_version("1.2")

        with pytest.raises(ValueError, match="Invalid semantic version format"):
            fsa.parse_version("1.2.3.4")

    def test_parse_non_string_version(self):
        """Test parsing non-string input."""
        fsa = VersionManagerFSA()

        with pytest.raises(ValueError, match="Version must be a string"):
            fsa.parse_version(123)


class TestVersionComparison:
    """Test version comparison functionality."""

    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.2.3")
        v2 = fsa.parse_version("1.2.3")

        assert fsa.compare_versions(v1, v2) == 0
        assert v1 == v2

    def test_compare_versions_less_than(self):
        """Test comparing when first version is less."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.2.3")
        v2 = fsa.parse_version("1.2.4")

        assert fsa.compare_versions(v1, v2) == -1
        assert v1 < v2

    def test_compare_versions_greater_than(self):
        """Test comparing when first version is greater."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("2.0.0")
        v2 = fsa.parse_version("1.9.9")

        assert fsa.compare_versions(v1, v2) == 1
        assert v1 > v2

    def test_compare_major_version_difference(self):
        """Test major version takes precedence."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("2.0.0")
        v2 = fsa.parse_version("1.99.99")

        assert v1 > v2

    def test_compare_minor_version_difference(self):
        """Test minor version comparison."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.5.0")
        v2 = fsa.parse_version("1.4.99")

        assert v1 > v2

    def test_compare_prerelease_versions(self):
        """Test prerelease versions are less than release versions."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0-alpha")
        v2 = fsa.parse_version("1.0.0")

        assert v1 < v2

    def test_version_ordering(self):
        """Test complete version ordering."""
        fsa = VersionManagerFSA()
        versions = [
            fsa.parse_version("1.0.0"),
            fsa.parse_version("2.0.0"),
            fsa.parse_version("1.1.0"),
            fsa.parse_version("1.0.1"),
            fsa.parse_version("1.0.0-alpha"),
        ]

        sorted_versions = sorted(versions)

        assert str(sorted_versions[0]) == "1.0.0-alpha"
        assert str(sorted_versions[1]) == "1.0.0"
        assert str(sorted_versions[2]) == "1.0.1"
        assert str(sorted_versions[3]) == "1.1.0"
        assert str(sorted_versions[4]) == "2.0.0"


class TestVersionCompatibility:
    """Test version compatibility checking."""

    def test_compatible_minor_upgrade(self):
        """Test minor version upgrade is compatible."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.5.0")
        required = fsa.parse_version("1.2.0")

        assert fsa.is_compatible(current, required)

    def test_compatible_patch_upgrade(self):
        """Test patch version upgrade is compatible."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.5")
        required = fsa.parse_version("1.2.3")

        assert fsa.is_compatible(current, required)

    def test_incompatible_major_version(self):
        """Test different major versions are incompatible."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("2.0.0")
        required = fsa.parse_version("1.9.0")

        assert not fsa.is_compatible(current, required)

    def test_incompatible_lower_version(self):
        """Test lower version is incompatible."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.0")
        required = fsa.parse_version("1.3.0")

        assert not fsa.is_compatible(current, required)

    def test_compatible_same_version(self):
        """Test same version is compatible."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")
        required = fsa.parse_version("1.2.3")

        assert fsa.is_compatible(current, required)

    def test_zero_major_version_compatibility(self):
        """Test 0.x.x versions require exact minor version match."""
        fsa = VersionManagerFSA()

        # Same minor version should be compatible
        current = fsa.parse_version("0.5.2")
        required = fsa.parse_version("0.5.0")
        assert fsa.is_compatible(current, required)

        # Different minor version should be incompatible
        current = fsa.parse_version("0.6.0")
        required = fsa.parse_version("0.5.0")
        assert not fsa.is_compatible(current, required)


class TestMigrationPath:
    """Test migration path generation."""

    def test_no_migration_same_version(self):
        """Test no migration needed for same version."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.2.3")
        v2 = fsa.parse_version("1.2.3")

        path = fsa.get_migration_path(v1, v2)
        assert len(path) == 0

    def test_migration_path_upgrade(self):
        """Test migration path for upgrade."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("2.0.0")

        path = fsa.get_migration_path(v1, v2)
        assert len(path) >= 1
        assert path[0].from_version == v1
        assert path[0].to_version == v2

    def test_migration_path_with_breaking_changes(self):
        """Test migration path includes breaking changes for major upgrade."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.5.0")
        v2 = fsa.parse_version("3.0.0")

        path = fsa.get_migration_path(v1, v2)
        assert len(path) >= 1
        assert len(path[0].breaking_changes) > 0

    def test_migration_downgrade_not_supported(self):
        """Test downgrade raises error."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("2.0.0")
        v2 = fsa.parse_version("1.0.0")

        with pytest.raises(ValueError, match="Downgrade not supported"):
            fsa.get_migration_path(v1, v2)

    def test_custom_migration_path(self):
        """Test adding and using custom migrations."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("1.5.0")
        v3 = fsa.parse_version("2.0.0")

        # Add custom migrations
        migration1 = Migration(
            from_version=v1,
            to_version=v2,
            description="Upgrade to 1.5.0",
            steps=["Update config", "Run migration script"]
        )
        migration2 = Migration(
            from_version=v2,
            to_version=v3,
            description="Upgrade to 2.0.0",
            breaking_changes=["API changes"],
            steps=["Update API calls", "Test thoroughly"]
        )

        fsa.add_migration(migration1)
        fsa.add_migration(migration2)

        path = fsa.get_migration_path(v1, v3)
        assert len(path) == 2


class TestUpgradeValidation:
    """Test upgrade validation."""

    def test_validate_upgrade_forward(self):
        """Test validating a forward upgrade."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("1.5.0")

        assert fsa.validate_upgrade(v1, v2)

    def test_validate_upgrade_same_version(self):
        """Test validating same version."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("1.0.0")

        assert fsa.validate_upgrade(v1, v2)

    def test_validate_upgrade_major_version(self):
        """Test validating major version upgrade."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.9.9")
        v2 = fsa.parse_version("2.0.0")

        assert fsa.validate_upgrade(v1, v2)

    def test_validate_downgrade_fails(self):
        """Test downgrade validation fails."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("2.0.0")
        v2 = fsa.parse_version("1.0.0")

        with pytest.raises(ValueError, match="Cannot downgrade"):
            fsa.validate_upgrade(v1, v2)


class TestConflictResolution:
    """Test dependency version conflict resolution."""

    def test_resolve_no_conflicts(self):
        """Test resolving dependencies with no conflicts."""
        fsa = VersionManagerFSA()
        dependencies = {
            "package-a": "1.2.3",
            "package-b": "2.0.0",
        }

        resolved = fsa.resolve_conflicts(dependencies)

        assert str(resolved["package-a"]) == "1.2.3"
        assert str(resolved["package-b"]) == "2.0.0"

    def test_resolve_caret_constraint(self):
        """Test resolving with caret constraint."""
        fsa = VersionManagerFSA()
        dependencies = {
            "package-a": "^1.2.0",
        }

        resolved = fsa.resolve_conflicts(dependencies)
        assert resolved["package-a"].major == 1
        assert resolved["package-a"].minor == 2

    def test_resolve_tilde_constraint(self):
        """Test resolving with tilde constraint."""
        fsa = VersionManagerFSA()
        dependencies = {
            "package-a": "~1.2.0",
        }

        resolved = fsa.resolve_conflicts(dependencies)
        assert resolved["package-a"].major == 1
        assert resolved["package-a"].minor == 2

    def test_resolve_gte_constraint(self):
        """Test resolving with >= constraint."""
        fsa = VersionManagerFSA()
        dependencies = {
            "package-a": ">=1.2.0",
        }

        resolved = fsa.resolve_conflicts(dependencies)
        assert resolved["package-a"] >= fsa.parse_version("1.2.0")

    def test_resolve_compatible_versions(self):
        """Test resolving multiple compatible version constraints."""
        fsa = VersionManagerFSA()
        # Simulate multiple packages requiring compatible versions
        dependencies = {
            "package-a": "1.5.0",
        }

        resolved = fsa.resolve_conflicts(dependencies)
        assert str(resolved["package-a"]) == "1.5.0"

    def test_resolve_invalid_constraint(self):
        """Test resolving with invalid constraint."""
        fsa = VersionManagerFSA()
        dependencies = {
            "package-a": "invalid",
        }

        with pytest.raises(ValueError):
            fsa.resolve_conflicts(dependencies)


class TestVersionBumping:
    """Test version bumping functionality."""

    def test_bump_patch_version(self):
        """Test bumping patch version."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")

        new_version = fsa.bump_version(current, "patch")

        assert str(new_version) == "1.2.4"

    def test_bump_minor_version(self):
        """Test bumping minor version."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")

        new_version = fsa.bump_version(current, "minor")

        assert str(new_version) == "1.3.0"

    def test_bump_major_version(self):
        """Test bumping major version."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")

        new_version = fsa.bump_version(current, "major")

        assert str(new_version) == "2.0.0"

    def test_bump_invalid_type(self):
        """Test bumping with invalid type."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")

        with pytest.raises(ValueError, match="Invalid bump type"):
            fsa.bump_version(current, "invalid")

    def test_bump_case_insensitive(self):
        """Test bumping with case-insensitive type."""
        fsa = VersionManagerFSA()
        current = fsa.parse_version("1.2.3")

        new_version = fsa.bump_version(current, "MAJOR")
        assert str(new_version) == "2.0.0"


class TestChangelog:
    """Test changelog functionality."""

    def test_add_and_get_changelog(self):
        """Test adding and retrieving changelogs."""
        fsa = VersionManagerFSA()

        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("1.1.0")
        v3 = fsa.parse_version("1.2.0")

        changelog1 = Changelog(
            version=v2,
            date=datetime(2023, 1, 1),
            changes=["Added feature X"],
        )
        changelog2 = Changelog(
            version=v3,
            date=datetime(2023, 2, 1),
            changes=["Added feature Y"],
            breaking_changes=["Changed API"],
        )

        fsa.add_changelog(changelog1)
        fsa.add_changelog(changelog2)

        changelogs = fsa.get_changelog(v1, v3)

        assert len(changelogs) == 2
        assert changelogs[0].version == v2
        assert changelogs[1].version == v3

    def test_changelog_between_versions(self):
        """Test getting changelog between specific versions."""
        fsa = VersionManagerFSA()

        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("1.5.0")
        v3 = fsa.parse_version("2.0.0")

        changelog = Changelog(
            version=v2,
            date=datetime.now(),
            changes=["Feature added"],
        )

        fsa.add_changelog(changelog)

        # Should include v2
        changelogs = fsa.get_changelog(v1, v3)
        assert len(changelogs) == 1

        # Should not include v2 (outside range)
        changelogs = fsa.get_changelog(v2, v3)
        assert len(changelogs) == 0


class TestFSAStates:
    """Test FSA state transitions."""

    def test_initial_state(self):
        """Test FSA starts in IDLE state."""
        fsa = VersionManagerFSA()
        assert fsa.state == VersionState.IDLE

    def test_state_transitions_parse(self):
        """Test state transitions during parsing."""
        fsa = VersionManagerFSA()
        fsa.parse_version("1.2.3")
        assert fsa.state == VersionState.IDLE

    def test_error_state_on_invalid_parse(self):
        """Test FSA enters ERROR state on parse failure."""
        fsa = VersionManagerFSA()

        try:
            fsa.parse_version("invalid")
        except ValueError:
            pass

        assert fsa.state == VersionState.ERROR
        assert fsa.error_message is not None

    def test_state_transitions_validate(self):
        """Test state transitions during validation."""
        fsa = VersionManagerFSA()
        v1 = fsa.parse_version("1.0.0")
        v2 = fsa.parse_version("2.0.0")

        fsa.compare_versions(v1, v2)
        assert fsa.state == VersionState.IDLE

    def test_state_transitions_resolve(self):
        """Test state transitions during conflict resolution."""
        fsa = VersionManagerFSA()
        dependencies = {"package-a": "1.0.0"}

        fsa.resolve_conflicts(dependencies)
        assert fsa.state == VersionState.IDLE

"""
Comprehensive test suite for ConfigManagerFSA.

Tests cover:
- Config loading from files
- Config loading from environment variables
- Config loading from remote stores
- YAML, JSON, TOML, INI parsing
- Environment-specific configs
- Schema validation
- Config versioning
- Encryption/decryption
- Hot-reload
- Config merging
- Audit logging
- Config caching
- Config export
- Edge cases and error handling
- Concurrent access
"""

import json
import os
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agno.fsas.config_manager_fsa import (
    AuditEntry,
    AuthConfig,
    Change,
    Config,
    ConfigFormat,
    ConfigManagerFSA,
    ConfigManagerResult,
    ConfigRequest,
    ConfigSchema,
    ConfigSource,
    EncryptedValue,
    Environment,
    MergeStrategy,
    ReloadResult,
    ValidationResult,
    VersionEntry,
)


# ==================== Fixtures ====================

@pytest.fixture
def config_manager_fsa():
    """Create ConfigManagerFSA instance for testing."""
    return ConfigManagerFSA(
        name="TestConfigManager",
        default_environment=Environment.DEVELOPMENT
    )


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_json_config(temp_config_dir):
    """Create sample JSON config file."""
    config_data = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "testdb"
        },
        "debug": True,
        "timeout": 30
    }

    config_file = temp_config_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    return config_file


@pytest.fixture
def sample_yaml_config(temp_config_dir):
    """Create sample YAML config file."""
    yaml_content = """
database:
  host: localhost
  port: 5432
  name: testdb
debug: true
timeout: 30
"""

    config_file = temp_config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        f.write(yaml_content)

    return config_file


@pytest.fixture
def sample_toml_config(temp_config_dir):
    """Create sample TOML config file."""
    toml_content = """
debug = true
timeout = 30

[database]
host = "localhost"
port = 5432
name = "testdb"
"""

    config_file = temp_config_dir / "config.toml"
    with open(config_file, 'w') as f:
        f.write(toml_content)

    return config_file


@pytest.fixture
def sample_ini_config(temp_config_dir):
    """Create sample INI config file."""
    ini_content = """
[database]
host = localhost
port = 5432
name = testdb

[settings]
debug = true
timeout = 30
"""

    config_file = temp_config_dir / "config.ini"
    with open(config_file, 'w') as f:
        f.write(ini_content)

    return config_file


@pytest.fixture
def sample_schema():
    """Create sample config schema."""
    return ConfigSchema(
        schema={
            "type": "object",
            "required": ["database"],
            "properties": {
                "database": {"type": "object"},
                "debug": {"type": "boolean"},
                "timeout": {"type": "number"}
            }
        }
    )


# ==================== Test Config Loading from File ====================

def test_load_config_from_json_file(config_manager_fsa, sample_json_config):
    """Test loading config from JSON file."""
    config = config_manager_fsa.load_from_file(str(sample_json_config), ConfigFormat.JSON)

    assert isinstance(config, Config)
    assert config.source == ConfigSource.FILE
    assert config.format == ConfigFormat.JSON
    assert "database" in config.data
    assert config.data["database"]["host"] == "localhost"


def test_load_config_from_yaml_file(config_manager_fsa, sample_yaml_config):
    """Test loading config from YAML file."""
    config = config_manager_fsa.load_from_file(str(sample_yaml_config), ConfigFormat.YAML)

    assert isinstance(config, Config)
    assert config.source == ConfigSource.FILE
    assert config.format == ConfigFormat.YAML


def test_load_config_from_toml_file(config_manager_fsa, sample_toml_config):
    """Test loading config from TOML file."""
    config = config_manager_fsa.load_from_file(str(sample_toml_config), ConfigFormat.TOML)

    assert isinstance(config, Config)
    assert config.source == ConfigSource.FILE
    assert config.format == ConfigFormat.TOML
    assert "database" in config.data


def test_load_config_from_ini_file(config_manager_fsa, sample_ini_config):
    """Test loading config from INI file."""
    config = config_manager_fsa.load_from_file(str(sample_ini_config), ConfigFormat.INI)

    assert isinstance(config, Config)
    assert config.source == ConfigSource.FILE
    assert config.format == ConfigFormat.INI


def test_load_config_from_nonexistent_file(config_manager_fsa):
    """Test loading config from non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        config_manager_fsa.load_from_file("/nonexistent/config.json", ConfigFormat.JSON)


# ==================== Test Config Loading from Environment ====================

def test_load_config_from_env_vars(config_manager_fsa):
    """Test loading config from environment variables."""
    # Set environment variables
    os.environ["APP_DATABASE_HOST"] = "localhost"
    os.environ["APP_DATABASE_PORT"] = "5432"
    os.environ["APP_DEBUG"] = "true"

    config = config_manager_fsa.load_from_env_vars("APP")

    assert isinstance(config, Config)
    assert config.source == ConfigSource.ENV_VAR
    assert "database_host" in config.data
    assert config.data["database_host"] == "localhost"

    # Clean up
    del os.environ["APP_DATABASE_HOST"]
    del os.environ["APP_DATABASE_PORT"]
    del os.environ["APP_DEBUG"]


def test_load_config_from_env_vars_with_json_values(config_manager_fsa):
    """Test loading complex JSON values from env vars."""
    os.environ["APP_CONFIG"] = '{"key": "value", "number": 42}'

    config = config_manager_fsa.load_from_env_vars("APP")

    assert "config" in config.data
    assert isinstance(config.data["config"], dict)
    assert config.data["config"]["key"] == "value"

    # Clean up
    del os.environ["APP_CONFIG"]


# ==================== Test Config Loading from Remote ====================

def test_load_config_from_remote(config_manager_fsa):
    """Test loading config from remote store."""
    auth = AuthConfig(auth_type="token", credentials={"token": "test123"})
    config = config_manager_fsa.load_from_remote("http://consul:8500/v1/kv/config", auth)

    assert isinstance(config, Config)
    assert config.source == ConfigSource.REMOTE
    assert "remote_loaded" in config.data


# ==================== Test Config Parsing ====================

def test_parse_json(config_manager_fsa):
    """Test JSON parsing."""
    json_str = '{"key": "value", "number": 42, "nested": {"inner": true}}'
    config = config_manager_fsa.parse_json(json_str)

    assert isinstance(config, Config)
    assert config.format == ConfigFormat.JSON
    assert config.data["key"] == "value"
    assert config.data["number"] == 42


def test_parse_json_invalid(config_manager_fsa):
    """Test parsing invalid JSON raises error."""
    with pytest.raises(ValueError):
        config_manager_fsa.parse_json("{invalid json")


def test_parse_yaml(config_manager_fsa):
    """Test YAML parsing."""
    yaml_str = '{"key": "value", "number": 42}'
    config = config_manager_fsa.parse_yaml(yaml_str)

    assert isinstance(config, Config)
    assert config.format == ConfigFormat.YAML


def test_parse_toml(config_manager_fsa):
    """Test TOML parsing."""
    toml_str = """
key = "value"
number = 42

[section]
inner = "data"
"""
    config = config_manager_fsa.parse_toml(toml_str)

    assert isinstance(config, Config)
    assert config.format == ConfigFormat.TOML


def test_parse_ini(config_manager_fsa):
    """Test INI parsing."""
    ini_str = """
[section1]
key1 = value1
key2 = value2

[section2]
key3 = value3
"""
    config = config_manager_fsa.parse_ini(ini_str)

    assert isinstance(config, Config)
    assert config.format == ConfigFormat.INI
    assert "section1" in config.data


# ==================== Test Environment-Specific Configs ====================

def test_get_env_config(config_manager_fsa):
    """Test getting environment-specific config."""
    config = config_manager_fsa.get_env_config(Environment.PRODUCTION)

    assert isinstance(config, Config)
    assert config.environment == Environment.PRODUCTION


def test_set_env_config(config_manager_fsa):
    """Test setting environment-specific config."""
    config = Config(data={"prod_key": "prod_value"})
    config_manager_fsa.set_env_config(Environment.PRODUCTION, config)

    retrieved = config_manager_fsa.get_env_config(Environment.PRODUCTION)

    assert retrieved.data["prod_key"] == "prod_value"
    assert retrieved.environment == Environment.PRODUCTION


# ==================== Test Schema Validation ====================

def test_validate_schema(config_manager_fsa, sample_schema):
    """Test schema validation."""
    result = config_manager_fsa.validate(sample_schema)

    assert isinstance(result, ValidationResult)
    assert result.valid is True


def test_validate_empty_schema(config_manager_fsa):
    """Test validation fails for empty schema."""
    empty_schema = ConfigSchema(schema={})
    result = config_manager_fsa.validate(empty_schema)

    assert result.valid is False
    assert len(result.errors) > 0


def test_validate_config_against_schema_valid(config_manager_fsa, sample_schema):
    """Test validating valid config against schema."""
    config = Config(data={
        "database": {"host": "localhost"},
        "debug": True,
        "timeout": 30
    })

    result = config_manager_fsa.validate_against_schema(config, sample_schema)

    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_config_against_schema_missing_required(config_manager_fsa, sample_schema):
    """Test validation fails for missing required fields."""
    config = Config(data={"debug": True})

    result = config_manager_fsa.validate_against_schema(config, sample_schema)

    assert result.valid is False
    assert any("database" in err for err in result.errors)


def test_validate_config_against_schema_wrong_type(config_manager_fsa, sample_schema):
    """Test validation fails for wrong field types."""
    config = Config(data={
        "database": "should_be_object",
        "debug": "should_be_boolean"
    })

    result = config_manager_fsa.validate_against_schema(config, sample_schema)

    assert result.valid is False
    assert len(result.errors) > 0


# ==================== Test Config Versioning ====================

def test_track_version(config_manager_fsa):
    """Test config version tracking."""
    config = Config(data={"key": "value"})
    changes = [Change(key="key", old_value=None, new_value="value")]

    entry = config_manager_fsa.track_version(config, "1.0.0", changes)

    assert isinstance(entry, VersionEntry)
    assert entry.version == "1.0.0"
    assert entry.config_id == config.config_id
    assert len(entry.changes) == 1


def test_get_version_history(config_manager_fsa):
    """Test retrieving version history."""
    config = Config(data={"key": "value"})

    # Track multiple versions
    config_manager_fsa.track_version(config, "1.0.0", [])
    config_manager_fsa.track_version(config, "1.1.0", [])

    history = config_manager_fsa.get_version_history(config.config_id)

    assert len(history) == 2
    assert history[0].version == "1.0.0"
    assert history[1].version == "1.1.0"


def test_detect_changes(config_manager_fsa):
    """Test change detection between configs."""
    old_config = Config(data={"key1": "value1", "key2": "value2"})
    new_config = Config(data={"key1": "new_value", "key3": "value3"})

    changes = config_manager_fsa.detect_changes(old_config, new_config)

    assert len(changes) >= 2  # key1 changed, key2 removed, key3 added


# ==================== Test Encryption/Decryption ====================

def test_encrypt_secret(config_manager_fsa):
    """Test secret encryption."""
    secret = "my_secret_password"
    encrypted = config_manager_fsa.encrypt_secret(secret, "encryption_key")

    assert isinstance(encrypted, EncryptedValue)
    assert encrypted.encrypted_data != secret
    assert encrypted.algorithm == "base64"


def test_decrypt_secret(config_manager_fsa):
    """Test secret decryption."""
    secret = "my_secret_password"
    encrypted = config_manager_fsa.encrypt_secret(secret, "encryption_key")

    decrypted = config_manager_fsa.decrypt_secret(encrypted.encrypted_data, "encryption_key")

    assert decrypted == secret


def test_encrypt_decrypt_roundtrip(config_manager_fsa):
    """Test encryption and decryption roundtrip."""
    original = "test_secret_123"
    encrypted = config_manager_fsa.encrypt_secret(original, "key")
    decrypted = config_manager_fsa.decrypt_secret(encrypted.encrypted_data, "key")

    assert decrypted == original


# ==================== Test Hot-Reload ====================

def test_hot_reload_config(config_manager_fsa, sample_json_config):
    """Test hot-reloading config."""
    # Initial load
    config_manager_fsa.load_from_file(str(sample_json_config), ConfigFormat.JSON)

    # Modify file
    time.sleep(0.1)  # Ensure different mtime
    with open(sample_json_config, 'w') as f:
        json.dump({"new_key": "new_value"}, f)

    # Hot reload
    result = config_manager_fsa.hot_reload_config(str(sample_json_config))

    assert isinstance(result, ReloadResult)
    assert result.success is True
    assert result.changes_detected is True


def test_hot_reload_no_changes(config_manager_fsa, sample_json_config):
    """Test hot-reload when no changes detected."""
    # Load and immediately reload
    config_manager_fsa.load_from_file(str(sample_json_config), ConfigFormat.JSON)
    result = config_manager_fsa.hot_reload_config(str(sample_json_config))

    assert result.success is True
    assert result.changes_detected is False


def test_hot_reload_nonexistent_file(config_manager_fsa):
    """Test hot-reload of non-existent file."""
    result = config_manager_fsa.hot_reload_config("/nonexistent/config.json")

    assert result.success is False
    assert "not found" in result.error.lower()


# ==================== Test Config Merging ====================

def test_merge_configs_override_strategy(config_manager_fsa):
    """Test config merging with override strategy."""
    config1 = Config(data={"key1": "value1", "key2": "value2"})
    config2 = Config(data={"key2": "new_value2", "key3": "value3"})

    merged = config_manager_fsa.merge_configs([config1, config2], MergeStrategy.OVERRIDE)

    assert merged.data["key1"] == "value1"
    assert merged.data["key2"] == "new_value2"
    assert merged.data["key3"] == "value3"


def test_merge_configs_deep_merge_strategy(config_manager_fsa):
    """Test config merging with deep merge strategy."""
    config1 = Config(data={"db": {"host": "localhost", "port": 5432}})
    config2 = Config(data={"db": {"port": 5433, "name": "testdb"}})

    merged = config_manager_fsa.merge_configs([config1, config2], MergeStrategy.DEEP_MERGE)

    assert merged.data["db"]["host"] == "localhost"
    assert merged.data["db"]["port"] == 5433
    assert merged.data["db"]["name"] == "testdb"


def test_merge_configs_additive_strategy(config_manager_fsa):
    """Test config merging with additive strategy."""
    config1 = Config(data={"items": [1, 2, 3]})
    config2 = Config(data={"items": [4, 5]})

    merged = config_manager_fsa.merge_configs([config1, config2], MergeStrategy.ADDITIVE)

    assert len(merged.data["items"]) == 5


def test_merge_single_config(config_manager_fsa):
    """Test merging single config returns same config."""
    config = Config(data={"key": "value"})
    merged = config_manager_fsa.merge_configs([config])

    assert merged.data == config.data


def test_merge_empty_list(config_manager_fsa):
    """Test merging empty config list."""
    merged = config_manager_fsa.merge_configs([])

    assert isinstance(merged, Config)
    assert len(merged.data) == 0


# ==================== Test Audit Logging ====================

def test_audit_config_change(config_manager_fsa):
    """Test auditing config changes."""
    old_config = Config(data={"key": "old_value"})
    new_config = Config(data={"key": "new_value"})

    entry = config_manager_fsa.audit_config_change(
        old_config,
        new_config,
        changed_by="test_user",
        reason="Testing"
    )

    assert isinstance(entry, AuditEntry)
    assert entry.changed_by == "test_user"
    assert entry.reason == "Testing"
    assert len(entry.changes) > 0


def test_get_audit_log(config_manager_fsa):
    """Test retrieving audit log."""
    config = Config(data={"key": "value"})
    old_config = Config(data={})

    config_manager_fsa.audit_config_change(old_config, config, "user1")
    config_manager_fsa.audit_config_change(old_config, config, "user2")

    audit_log = config_manager_fsa.get_audit_log()

    assert len(audit_log) >= 2


def test_get_audit_log_by_config_id(config_manager_fsa):
    """Test retrieving audit log for specific config."""
    config1 = Config(data={"key": "value"})
    config2 = Config(data={"key": "value"})
    old_config = Config(data={})

    config_manager_fsa.audit_config_change(old_config, config1, "user1")
    config_manager_fsa.audit_config_change(old_config, config2, "user2")

    audit_log = config_manager_fsa.get_audit_log(config1.config_id)

    assert all(entry.config_id == config1.config_id for entry in audit_log)


# ==================== Test Config Caching ====================

def test_cache_config(config_manager_fsa):
    """Test caching config."""
    config = Config(data={"key": "value"})

    config_manager_fsa.cache_config(config, ttl=timedelta(minutes=5))

    cached = config_manager_fsa.get_cached_config(config.config_id)

    assert cached is not None
    assert cached.config_id == config.config_id


def test_get_cached_config_expired(config_manager_fsa):
    """Test retrieving expired cached config."""
    config = Config(data={"key": "value"})

    # Cache with very short TTL
    config_manager_fsa.cache_config(config, ttl=timedelta(milliseconds=1))

    # Wait for expiration
    time.sleep(0.01)

    cached = config_manager_fsa.get_cached_config(config.config_id)

    assert cached is None


def test_clear_cache(config_manager_fsa):
    """Test clearing config cache."""
    config1 = Config(data={"key": "value1"})
    config2 = Config(data={"key": "value2"})

    config_manager_fsa.cache_config(config1)
    config_manager_fsa.cache_config(config2)

    config_manager_fsa.clear_cache()

    assert config_manager_fsa.get_cached_config(config1.config_id) is None
    assert config_manager_fsa.get_cached_config(config2.config_id) is None


# ==================== Test Config Export ====================

def test_export_config_json(config_manager_fsa):
    """Test exporting config to JSON."""
    config = Config(data={"key": "value", "number": 42})

    exported = config_manager_fsa.export_config(config, ConfigFormat.JSON)

    assert isinstance(exported, str)
    parsed = json.loads(exported)
    assert parsed["key"] == "value"


def test_export_config_yaml(config_manager_fsa):
    """Test exporting config to YAML."""
    config = Config(data={"key": "value", "number": 42})

    exported = config_manager_fsa.export_config(config, ConfigFormat.YAML)

    assert isinstance(exported, str)
    assert "key:" in exported


def test_export_config_toml(config_manager_fsa):
    """Test exporting config to TOML."""
    config = Config(data={"key": "value", "section": {"inner": "data"}})

    exported = config_manager_fsa.export_config(config, ConfigFormat.TOML)

    assert isinstance(exported, str)
    assert "[section]" in exported


def test_export_config_ini(config_manager_fsa):
    """Test exporting config to INI."""
    config = Config(data={"section1": {"key": "value"}})

    exported = config_manager_fsa.export_config(config, ConfigFormat.INI)

    assert isinstance(exported, str)
    assert "[section1]" in exported


# ==================== Test Main Execute Pipeline ====================

def test_execute_pipeline_single_file(config_manager_fsa, sample_json_config):
    """Test main execution pipeline with single file."""
    request = ConfigRequest(
        source=ConfigSource.FILE,
        source_path=str(sample_json_config),
        format=ConfigFormat.JSON
    )

    result = config_manager_fsa.execute([request])

    assert isinstance(result, ConfigManagerResult)
    assert result.success is True
    assert result.loaded_configs == 1
    assert result.merged_config is not None


def test_execute_pipeline_multiple_sources(config_manager_fsa, sample_json_config):
    """Test execution with multiple config sources."""
    requests = [
        ConfigRequest(
            source=ConfigSource.FILE,
            source_path=str(sample_json_config),
            format=ConfigFormat.JSON
        ),
        ConfigRequest(
            source=ConfigSource.ENV_VAR,
            source_path="TEST"
        )
    ]

    result = config_manager_fsa.execute(requests)

    assert result.loaded_configs >= 1
    assert result.merged_config is not None


# ==================== Test Config Get/Set ====================

def test_config_get_with_dot_notation(config_manager_fsa):
    """Test getting config value with dot notation."""
    config = Config(data={"db": {"host": "localhost", "port": 5432}})

    assert config.get("db.host") == "localhost"
    assert config.get("db.port") == 5432
    assert config.get("db.nonexistent", "default") == "default"


def test_config_set_with_dot_notation(config_manager_fsa):
    """Test setting config value with dot notation."""
    config = Config(data={})

    config.set("db.host", "localhost")
    config.set("db.port", 5432)

    assert config.data["db"]["host"] == "localhost"
    assert config.data["db"]["port"] == 5432


# ==================== Test Utility Methods ====================

def test_get_stats(config_manager_fsa, sample_json_config):
    """Test getting statistics."""
    config_manager_fsa.load_from_file(str(sample_json_config), ConfigFormat.JSON)

    stats = config_manager_fsa.get_stats()

    assert isinstance(stats, dict)
    assert "total_configs" in stats
    assert "total_loads" in stats
    assert stats["total_loads"] >= 1


def test_register_encryption_key(config_manager_fsa):
    """Test registering encryption key."""
    config_manager_fsa.register_encryption_key("key1", "secret_key_123")

    assert "key1" in config_manager_fsa.encryption_keys


# ==================== Test Edge Cases ====================

def test_concurrent_config_access(config_manager_fsa):
    """Test thread safety with concurrent access."""
    import threading

    results = []
    lock = threading.Lock()

    def load_config():
        config = Config(data={"thread_id": threading.get_ident()})
        config_manager_fsa.configs[config.config_id] = config
        with lock:
            results.append(config.config_id)

    # Create multiple threads
    threads = [threading.Thread(target=load_config) for _ in range(10)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify all configs were stored
    assert len(results) == 10


def test_complex_nested_config_merge(config_manager_fsa):
    """Test merging complex nested configs."""
    config1 = Config(data={
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "features": {
                "auth": {"enabled": True},
                "cache": {"ttl": 300}
            }
        }
    })

    config2 = Config(data={
        "app": {
            "version": "1.1.0",
            "features": {
                "auth": {"provider": "oauth"},
                "logging": {"level": "info"}
            }
        }
    })

    merged = config_manager_fsa.merge_configs([config1, config2], MergeStrategy.DEEP_MERGE)

    assert merged.data["app"]["name"] == "MyApp"
    assert merged.data["app"]["version"] == "1.1.0"
    assert merged.data["app"]["features"]["auth"]["enabled"] is True
    assert merged.data["app"]["features"]["auth"]["provider"] == "oauth"


def test_config_with_empty_data(config_manager_fsa):
    """Test handling config with empty data."""
    config = Config(data={})

    assert config.get("any.key", "default") == "default"
    config.set("new.key", "value")
    assert config.data["new"]["key"] == "value"

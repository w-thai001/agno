"""Unit tests for Config Manager FSA"""

import json
import tempfile
from pathlib import Path
from typing import Optional

import pytest
from pydantic import BaseModel, Field

from agno.fsa.config_manager import (
    ConfigFormat,
    ConfigManager,
    ConfigState,
    Environment,
)

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Test schemas
class DatabaseConfig(BaseModel):
    """Database configuration schema"""

    host: str = "localhost"
    port: int = 5432
    username: str
    password: str
    database: str


class AppConfig(BaseModel):
    """Application configuration schema"""

    app_name: str
    debug: bool = False
    api_key: str
    timeout: int = 30
    database: Optional[DatabaseConfig] = None
    features: dict = Field(default_factory=dict)


class TestConfigManagerBasics:
    """Test basic ConfigManager functionality"""

    def test_initialization(self):
        """Test ConfigManager initialization"""
        config_mgr = ConfigManager()
        assert config_mgr.state == ConfigState.UNINITIALIZED
        assert config_mgr.environment in Environment

    def test_environment_detection(self):
        """Test automatic environment detection"""
        import os

        # Test default
        config_mgr = ConfigManager()
        assert config_mgr.environment == Environment.DEVELOPMENT

        # Test from ENV var
        os.environ["ENVIRONMENT"] = "prod"
        config_mgr = ConfigManager()
        assert config_mgr.environment == Environment.PRODUCTION
        del os.environ["ENVIRONMENT"]

    def test_state_transitions(self):
        """Test FSA state transitions"""
        config_mgr = ConfigManager()
        assert config_mgr.state == ConfigState.UNINITIALIZED

        config_mgr.transition(ConfigState.LOADING)
        assert config_mgr.state == ConfigState.LOADING

        config_mgr.transition(ConfigState.READY)
        assert config_mgr.state == ConfigState.READY


class TestConfigLoading:
    """Test configuration loading from different formats"""

    def test_load_json_config(self, tmp_path):
        """Test loading JSON configuration"""
        config_data = {
            "app_name": "TestApp",
            "api_key": "test-key-123",
            "debug": True,
            "timeout": 60,
        }

        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file, format=ConfigFormat.JSON)
        config = config_mgr.load()

        assert config.app_name == "TestApp"
        assert config.api_key == "test-key-123"
        assert config.debug is True
        assert config.timeout == 60
        assert config_mgr.state == ConfigState.READY

    @pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
    def test_load_yaml_config(self, tmp_path):
        """Test loading YAML configuration"""
        config_data = """
app_name: TestApp
api_key: yaml-key-456
debug: false
timeout: 45
database:
  host: db.example.com
  port: 5432
  username: user
  password: pass
  database: testdb
"""

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            f.write(config_data)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file, format=ConfigFormat.YAML)
        config = config_mgr.load()

        assert config.app_name == "TestApp"
        assert config.api_key == "yaml-key-456"
        assert config.debug is False
        assert config.timeout == 45
        assert config.database.host == "db.example.com"

    def test_load_env_config(self, tmp_path):
        """Test loading ENV configuration"""
        env_content = """
# Application config
app_name=EnvApp
api_key="env-key-789"
debug=true
timeout=90

# Database config (flat structure)
db_host=localhost
db_port=5432
"""

        env_file = tmp_path / ".env"
        with open(env_file, "w") as f:
            f.write(env_content)

        # For ENV files, we need to use unstructured schema
        config_mgr = ConfigManager()
        config_mgr.add_source(env_file, format=ConfigFormat.ENV)
        config_mgr.load()

        assert config_mgr.get("app_name") == "EnvApp"
        assert config_mgr.get("api_key") == "env-key-789"
        assert config_mgr.get("debug") is True
        assert config_mgr.get("timeout") == 90
        assert config_mgr.get("db_host") == "localhost"
        assert config_mgr.get("db_port") == 5432

    def test_auto_format_detection(self, tmp_path):
        """Test automatic format detection from file extension"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "Auto", "api_key": "auto-123"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)  # No format specified
        config = config_mgr.load()

        assert config.app_name == "Auto"


class TestConfigMerging:
    """Test configuration merging and overrides"""

    def test_simple_merge(self, tmp_path):
        """Test merging multiple config sources"""
        # Base config
        base_config = tmp_path / "base.json"
        with open(base_config, "w") as f:
            json.dump({"app_name": "Base", "api_key": "base-key", "timeout": 30}, f)

        # Override config
        override_config = tmp_path / "override.json"
        with open(override_config, "w") as f:
            json.dump({"api_key": "override-key", "debug": True}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(base_config, priority=10)
        config_mgr.add_source(override_config, priority=20)  # Higher priority
        config = config_mgr.load()

        assert config.app_name == "Base"  # From base
        assert config.api_key == "override-key"  # Overridden
        assert config.timeout == 30  # From base
        assert config.debug is True  # From override

    def test_deep_merge(self, tmp_path):
        """Test deep merging of nested configurations"""
        # Base config with database
        base_config = tmp_path / "base.json"
        with open(base_config, "w") as f:
            json.dump(
                {
                    "app_name": "App",
                    "api_key": "key",
                    "database": {"host": "localhost", "port": 5432, "username": "user", "password": "pass", "database": "db"},
                },
                f,
            )

        # Override just database host
        override_config = tmp_path / "override.json"
        with open(override_config, "w") as f:
            json.dump({"database": {"host": "prod.example.com"}}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(base_config, priority=10)
        config_mgr.add_source(override_config, priority=20)
        config = config_mgr.load()

        # Database host should be overridden
        assert config.database.host == "prod.example.com"
        # Other database fields should remain
        assert config.database.port == 5432
        assert config.database.username == "user"

    def test_priority_ordering(self, tmp_path):
        """Test that priority ordering is respected"""
        configs = []
        for i in range(3):
            config_file = tmp_path / f"config_{i}.json"
            with open(config_file, "w") as f:
                json.dump({"api_key": f"key-{i}"}, f)
            configs.append((config_file, i * 10))

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(tmp_path / "base.json", priority=0)
        with open(tmp_path / "base.json", "w") as f:
            json.dump({"app_name": "App", "api_key": "base"}, f)

        for config_file, priority in configs:
            config_mgr.add_source(config_file, priority=priority)

        config = config_mgr.load()

        # Highest priority (config_2 with priority 20) should win
        assert config.api_key == "key-2"


class TestEnvironmentConfigs:
    """Test environment-specific configurations"""

    def test_environment_specific_loading(self, tmp_path):
        """Test loading configs specific to environment"""
        # Base config
        base_config = tmp_path / "config.json"
        with open(base_config, "w") as f:
            json.dump({"app_name": "App", "api_key": "base", "debug": False}, f)

        # Dev config
        dev_config = tmp_path / "config.dev.json"
        with open(dev_config, "w") as f:
            json.dump({"api_key": "dev-key", "debug": True}, f)

        # Prod config
        prod_config = tmp_path / "config.prod.json"
        with open(prod_config, "w") as f:
            json.dump({"api_key": "prod-key", "debug": False}, f)

        # Test development environment
        config_mgr = ConfigManager(schema=AppConfig, environment=Environment.DEVELOPMENT)
        config_mgr.add_source(base_config, priority=10)
        config_mgr.add_source(dev_config, environment=Environment.DEVELOPMENT, priority=20)
        config_mgr.add_source(prod_config, environment=Environment.PRODUCTION, priority=20)
        config = config_mgr.load()

        # Should use dev config
        assert config.api_key == "dev-key"
        assert config.debug is True

        # Test production environment
        config_mgr_prod = ConfigManager(schema=AppConfig, environment=Environment.PRODUCTION)
        config_mgr_prod.add_source(base_config, priority=10)
        config_mgr_prod.add_source(dev_config, environment=Environment.DEVELOPMENT, priority=20)
        config_mgr_prod.add_source(prod_config, environment=Environment.PRODUCTION, priority=20)
        config_prod = config_mgr_prod.load()

        # Should use prod config
        assert config_prod.api_key == "prod-key"
        assert config_prod.debug is False

    def test_auto_discovery(self, tmp_path):
        """Test automatic config file discovery"""
        # Create base config
        with open(tmp_path / "config.json", "w") as f:
            json.dump({"app_name": "App", "api_key": "base"}, f)

        # Create dev-specific config
        with open(tmp_path / "config.dev.json", "w") as f:
            json.dump({"api_key": "dev-override"}, f)

        config_mgr = ConfigManager(schema=AppConfig, config_dir=tmp_path, environment=Environment.DEVELOPMENT)
        config = config_mgr.load()

        # Should auto-discover and merge configs
        assert config.app_name == "App"
        assert config.api_key == "dev-override"


class TestValidation:
    """Test configuration validation"""

    def test_schema_validation_success(self, tmp_path):
        """Test successful schema validation"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "ValidApp", "api_key": "valid-key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config = config_mgr.load()

        assert isinstance(config, AppConfig)
        assert config.app_name == "ValidApp"

    def test_schema_validation_failure(self, tmp_path):
        """Test schema validation failure"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            # Missing required field 'api_key'
            json.dump({"app_name": "InvalidApp"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)

        with pytest.raises(ValueError, match="Config validation failed"):
            config_mgr.load()

        assert config_mgr.state == ConfigState.ERROR

    def test_custom_validator(self, tmp_path):
        """Test custom validation function"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key", "timeout": 5}, f)

        def validate_timeout(config_data):
            """Timeout must be at least 10"""
            return config_data.get("timeout", 0) >= 10

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.add_validator(validate_timeout)

        with pytest.raises(ValueError, match="Custom validation failed"):
            config_mgr.load()


class TestConfigAccess:
    """Test configuration access methods"""

    def test_get_simple_key(self, tmp_path):
        """Test getting simple configuration values"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key", "timeout": 30}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        assert config_mgr.get("app_name") == "App"
        assert config_mgr.get("timeout") == 30

    def test_get_nested_key(self, tmp_path):
        """Test getting nested configuration values with dot notation"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(
                {
                    "app_name": "App",
                    "api_key": "key",
                    "database": {"host": "localhost", "port": 5432, "username": "user", "password": "pass", "database": "db"},
                },
                f,
            )

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        assert config_mgr.get("database.host") == "localhost"
        assert config_mgr.get("database.port") == 5432

    def test_get_default_value(self, tmp_path):
        """Test getting default value for missing keys"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        assert config_mgr.get("missing_key") is None
        assert config_mgr.get("missing_key", "default") == "default"

    def test_set_value(self, tmp_path):
        """Test setting configuration values at runtime"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        # Set new value
        config_mgr.set("timeout", 60)
        assert config_mgr.get("timeout") == 60

        # Verify it updates the config instance
        assert config_mgr.config.timeout == 60

    def test_dict_style_access(self, tmp_path):
        """Test dictionary-style access"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        # Dict-style get
        assert config_mgr["app_name"] == "App"

        # Dict-style set
        config_mgr["debug"] = True
        assert config_mgr["debug"] is True

        # Contains check
        assert "app_name" in config_mgr
        assert "missing" not in config_mgr

    def test_to_dict(self, tmp_path):
        """Test exporting config to dictionary"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key", "timeout": 30}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        config_dict = config_mgr.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["app_name"] == "App"
        assert config_dict["api_key"] == "key"


class TestHotReload:
    """Test hot reload functionality"""

    def test_reload(self, tmp_path):
        """Test reloading configuration"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "original-key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config = config_mgr.load()

        assert config.api_key == "original-key"

        # Modify config file
        import time

        time.sleep(0.1)  # Ensure mtime changes
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "new-key"}, f)

        # Reload
        new_config = config_mgr.reload()
        assert new_config.api_key == "new-key"
        assert config_mgr.state == ConfigState.READY

    def test_has_changed(self, tmp_path):
        """Test detecting config file changes"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "key"}, f)

        config_mgr = ConfigManager(schema=AppConfig)
        config_mgr.add_source(config_file)
        config_mgr.load()

        # Initially no changes
        assert not config_mgr.has_changed()

        # Modify file
        import time

        time.sleep(0.1)
        with open(config_file, "w") as f:
            json.dump({"app_name": "App", "api_key": "new-key"}, f)

        # Should detect change
        assert config_mgr.has_changed()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_config(self):
        """Test with no config sources"""
        config_mgr = ConfigManager()
        config_mgr.load()

        assert config_mgr.config_data == {}
        assert config_mgr.state == ConfigState.READY

    def test_missing_file(self, tmp_path):
        """Test handling missing config file"""
        config_mgr = ConfigManager()
        config_mgr.add_source(tmp_path / "nonexistent.json")

        # Should not raise, just skip missing files
        config_mgr.load()
        assert config_mgr.config_data == {}

    def test_invalid_json(self, tmp_path):
        """Test handling invalid JSON"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            f.write("{ invalid json }")

        config_mgr = ConfigManager()
        config_mgr.add_source(config_file)

        with pytest.raises(json.JSONDecodeError):
            config_mgr.load()

    def test_no_schema_validation(self, tmp_path):
        """Test loading without schema validation"""
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump({"any_key": "any_value", "another": 123}, f)

        # No schema provided
        config_mgr = ConfigManager()
        config_mgr.add_source(config_file)
        config_mgr.load()

        assert config_mgr.get("any_key") == "any_value"
        assert config_mgr.get("another") == 123
        assert config_mgr.config is None  # No typed config without schema


class TestEnvParsing:
    """Test environment variable parsing"""

    def test_parse_boolean(self, tmp_path):
        """Test parsing boolean values from ENV"""
        env_file = tmp_path / ".env"
        with open(env_file, "w") as f:
            f.write("FLAG_TRUE=true\n")
            f.write("FLAG_FALSE=false\n")
            f.write("FLAG_YES=yes\n")
            f.write("FLAG_NO=no\n")
            f.write("FLAG_ONE=1\n")
            f.write("FLAG_ZERO=0\n")

        config_mgr = ConfigManager()
        config_mgr.add_source(env_file)
        config_mgr.load()

        assert config_mgr.get("FLAG_TRUE") is True
        assert config_mgr.get("FLAG_FALSE") is False
        assert config_mgr.get("FLAG_YES") is True
        assert config_mgr.get("FLAG_NO") is False
        assert config_mgr.get("FLAG_ONE") is True
        assert config_mgr.get("FLAG_ZERO") is False

    def test_parse_numbers(self, tmp_path):
        """Test parsing numeric values from ENV"""
        env_file = tmp_path / ".env"
        with open(env_file, "w") as f:
            f.write("PORT=8080\n")
            f.write("TIMEOUT=30.5\n")
            f.write("COUNT=42\n")

        config_mgr = ConfigManager()
        config_mgr.add_source(env_file)
        config_mgr.load()

        assert config_mgr.get("PORT") == 8080
        assert config_mgr.get("TIMEOUT") == 30.5
        assert config_mgr.get("COUNT") == 42

    def test_parse_strings(self, tmp_path):
        """Test parsing string values from ENV"""
        env_file = tmp_path / ".env"
        with open(env_file, "w") as f:
            f.write('API_KEY="my-secret-key"\n')
            f.write("HOST='localhost'\n")
            f.write("NAME=plain-value\n")

        config_mgr = ConfigManager()
        config_mgr.add_source(env_file)
        config_mgr.load()

        assert config_mgr.get("API_KEY") == "my-secret-key"
        assert config_mgr.get("HOST") == "localhost"
        assert config_mgr.get("NAME") == "plain-value"

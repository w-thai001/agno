"""Config Manager FSA - Core Infrastructure Track

A flexible configuration management system with:
- Multi-format support (JSON, YAML, ENV)
- Environment-specific configurations
- Schema validation
- Hot reload capabilities
- Type-safe access
- Config merging and overrides
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ValidationError

from agno.utils.log import logger

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logger.debug("PyYAML not available. YAML config loading will be disabled.")


class ConfigFormat(str, Enum):
    """Supported configuration file formats"""

    JSON = "json"
    YAML = "yaml"
    ENV = "env"


class Environment(str, Enum):
    """Standard deployment environments"""

    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"
    TEST = "test"


class ConfigState(str, Enum):
    """FSA States for Config Manager"""

    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    LOADED = "loaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    MERGING = "merging"
    READY = "ready"
    RELOADING = "reloading"
    ERROR = "error"


T = TypeVar("T", bound=BaseModel)


@dataclass
class ConfigSource:
    """Represents a configuration source"""

    path: Path
    format: ConfigFormat
    environment: Optional[Environment] = None
    priority: int = 0  # Higher priority overrides lower
    data: Dict[str, Any] = field(default_factory=dict)
    last_modified: Optional[float] = None


@dataclass
class ConfigManager(Generic[T]):
    """
    Config Manager FSA - Manages application configuration with state transitions

    FSA States:
        UNINITIALIZED -> LOADING -> LOADED -> VALIDATING -> VALIDATED -> MERGING -> READY
                                                                              ^
                                                                              |
        RELOADING -------------------------------------------------------+

    Example:
        ```python
        from pydantic import BaseModel
        from agno.fsa import ConfigManager, Environment

        class AppConfig(BaseModel):
            api_key: str
            timeout: int = 30

        # Create config manager
        config_mgr = ConfigManager(
            schema=AppConfig,
            config_dir="./config",
            environment=Environment.DEVELOPMENT
        )

        # Load configuration
        config = config_mgr.load()

        # Access config
        print(config.api_key)

        # Hot reload
        new_config = config_mgr.reload()
        ```
    """

    # Configuration schema for validation
    schema: Optional[type[T]] = None

    # Configuration directory
    config_dir: Optional[Union[str, Path]] = None

    # Current environment
    environment: Optional[Environment] = None

    # Configuration sources (files)
    sources: List[ConfigSource] = field(default_factory=list)

    # Merged configuration data
    config_data: Dict[str, Any] = field(default_factory=dict)

    # Validated config instance
    config: Optional[T] = None

    # Current FSA state
    state: ConfigState = ConfigState.UNINITIALIZED

    # Enable hot reload monitoring
    hot_reload: bool = False

    # Custom validators
    validators: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)

    # Environment variable prefix for ENV format
    env_prefix: str = ""

    # Debug mode
    debug: bool = False

    def __post_init__(self):
        """Initialize config manager"""
        if self.config_dir:
            self.config_dir = Path(self.config_dir)

        # Auto-detect environment if not set
        if not self.environment:
            env_name = os.getenv("ENVIRONMENT", os.getenv("ENV", "dev"))
            try:
                self.environment = Environment(env_name.lower())
            except ValueError:
                self.environment = Environment.DEVELOPMENT
                if self.debug:
                    logger.warning(f"Unknown environment '{env_name}', defaulting to development")

    def transition(self, new_state: ConfigState) -> None:
        """Transition to a new FSA state"""
        if self.debug:
            logger.debug(f"ConfigManager FSA: {self.state} -> {new_state}")
        self.state = new_state

    def add_source(
        self,
        path: Union[str, Path],
        format: Optional[ConfigFormat] = None,
        environment: Optional[Environment] = None,
        priority: int = 0,
    ) -> ConfigManager:
        """
        Add a configuration source

        Args:
            path: Path to config file
            format: File format (auto-detected if None)
            environment: Environment this config applies to
            priority: Priority for merging (higher overrides lower)
        """
        path = Path(path)

        # Auto-detect format from extension
        if format is None:
            ext = path.suffix.lower()
            if ext == ".json":
                format = ConfigFormat.JSON
            elif ext in [".yaml", ".yml"]:
                format = ConfigFormat.YAML
            elif ext == ".env":
                format = ConfigFormat.ENV
            else:
                raise ValueError(f"Cannot auto-detect format for {path}. Specify format explicitly.")

        source = ConfigSource(path=path, format=format, environment=environment, priority=priority)
        self.sources.append(source)

        # Sort sources by priority (higher first)
        self.sources.sort(key=lambda s: s.priority, reverse=True)

        return self

    def add_validator(self, validator: Callable[[Dict[str, Any]], bool]) -> ConfigManager:
        """Add a custom validation function"""
        self.validators.append(validator)
        return self

    def load(self, reload: bool = False) -> T:
        """
        Load and validate configuration

        Args:
            reload: Force reload even if already loaded

        Returns:
            Validated configuration instance
        """
        if not reload and self.state == ConfigState.READY and self.config:
            return self.config

        try:
            # Transition: LOADING
            self.transition(ConfigState.RELOADING if reload else ConfigState.LOADING)

            # Auto-discover config files if config_dir is set
            if self.config_dir and not self.sources:
                self._discover_configs()

            # Load all sources
            for source in self.sources:
                self._load_source(source)

            # Transition: LOADED
            self.transition(ConfigState.LOADED)

            # Merge configurations
            self.transition(ConfigState.MERGING)
            self.config_data = self._merge_sources()

            # Validate configuration
            self.transition(ConfigState.VALIDATING)
            self._validate()

            # Transition: VALIDATED
            self.transition(ConfigState.VALIDATED)

            # Create config instance if schema provided
            if self.schema:
                try:
                    self.config = self.schema(**self.config_data)
                except ValidationError as e:
                    self.transition(ConfigState.ERROR)
                    raise ValueError(f"Config validation failed: {e}") from e

            # Transition: READY
            self.transition(ConfigState.READY)

            if self.debug:
                logger.debug(f"Configuration loaded successfully: {len(self.config_data)} keys")

            return self.config

        except Exception as e:
            self.transition(ConfigState.ERROR)
            logger.error(f"Failed to load configuration: {e}")
            raise

    def reload(self) -> T:
        """Hot reload configuration"""
        return self.load(reload=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
        """
        if not self.config_data:
            self.load()

        # Support dot notation for nested keys
        keys = key.split(".")
        value = self.config_data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value (runtime only, not persisted)

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        if not self.config_data:
            self.load()

        # Support dot notation for nested keys
        keys = key.split(".")
        target = self.config_data

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

        # Re-validate if schema exists
        if self.schema:
            try:
                self.config = self.schema(**self.config_data)
            except ValidationError as e:
                logger.warning(f"Config no longer valid after set: {e}")

    def has_changed(self) -> bool:
        """Check if any source files have been modified"""
        for source in self.sources:
            if source.path.exists():
                current_mtime = source.path.stat().st_mtime
                if source.last_modified and current_mtime > source.last_modified:
                    return True
        return False

    def _discover_configs(self) -> None:
        """Auto-discover configuration files in config_dir"""
        if not self.config_dir or not self.config_dir.exists():
            return

        # Priority order: base config < env-specific config < local overrides
        patterns = [
            ("config.json", ConfigFormat.JSON, None, 10),
            ("config.yaml", ConfigFormat.YAML, None, 10),
            ("config.yml", ConfigFormat.YAML, None, 10),
            (".env", ConfigFormat.ENV, None, 10),
            (f"config.{self.environment.value}.json", ConfigFormat.JSON, self.environment, 20),
            (f"config.{self.environment.value}.yaml", ConfigFormat.YAML, self.environment, 20),
            (f"config.{self.environment.value}.yml", ConfigFormat.YAML, self.environment, 20),
            (f".env.{self.environment.value}", ConfigFormat.ENV, self.environment, 20),
            ("config.local.json", ConfigFormat.JSON, None, 30),
            ("config.local.yaml", ConfigFormat.YAML, None, 30),
            (".env.local", ConfigFormat.ENV, None, 30),
        ]

        for filename, format_type, env, priority in patterns:
            file_path = self.config_dir / filename
            if file_path.exists():
                self.add_source(file_path, format=format_type, environment=env, priority=priority)

        if self.debug and self.sources:
            logger.debug(f"Discovered {len(self.sources)} config files in {self.config_dir}")

    def _load_source(self, source: ConfigSource) -> None:
        """Load data from a configuration source"""
        if not source.path.exists():
            if self.debug:
                logger.debug(f"Config file not found: {source.path}")
            return

        try:
            # Update last modified time
            source.last_modified = source.path.stat().st_mtime

            # Load based on format
            if source.format == ConfigFormat.JSON:
                source.data = self._load_json(source.path)

            elif source.format == ConfigFormat.YAML:
                source.data = self._load_yaml(source.path)

            elif source.format == ConfigFormat.ENV:
                source.data = self._load_env(source.path)

            if self.debug:
                logger.debug(f"Loaded config from {source.path}: {len(source.data)} keys")

        except Exception as e:
            logger.error(f"Failed to load {source.path}: {e}")
            raise

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration file"""
        with open(path, "r") as f:
            return json.load(f)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not HAS_YAML:
            raise ImportError("PyYAML is required for YAML config files. Install with: pip install pyyaml")

        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def _load_env(self, path: Path) -> Dict[str, Any]:
        """Load ENV configuration file"""
        config = {}

        with open(path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    # Remove prefix if set
                    if self.env_prefix and key.startswith(self.env_prefix):
                        key = key[len(self.env_prefix) :]

                    # Convert to proper types
                    config[key] = self._parse_env_value(value)

        return config

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to proper type"""
        # Boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String
        return value

    def _merge_sources(self) -> Dict[str, Any]:
        """Merge all configuration sources (higher priority overrides lower)"""
        merged = {}

        # Sources are already sorted by priority (lowest first after reverse)
        for source in reversed(self.sources):
            # Skip if environment-specific and doesn't match
            if source.environment and source.environment != self.environment:
                continue

            # Deep merge
            merged = self._deep_merge(merged, source.data)

        return merged

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate(self) -> None:
        """Run custom validators"""
        for validator in self.validators:
            try:
                if not validator(self.config_data):
                    raise ValueError(f"Custom validation failed: {validator.__name__}")
            except Exception as e:
                raise ValueError(f"Validator {validator.__name__} raised exception: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        if self.config and isinstance(self.config, BaseModel):
            return self.config.model_dump()
        return self.config_data.copy()

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: config['key']"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style setting: config['key'] = value"""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if key exists: 'key' in config"""
        return self.get(key) is not None

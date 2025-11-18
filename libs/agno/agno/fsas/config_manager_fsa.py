"""
Config Manager FSA: Centralized configuration management for FSA systems.

This module provides comprehensive configuration management with support for:
- Multiple config sources (files, environment variables, remote stores)
- Multiple config formats (YAML, JSON, TOML, INI)
- Environment-specific configurations (dev, staging, prod)
- Schema validation with JSON Schema
- Config versioning and change tracking
- Encryption/decryption for sensitive data
- Hot-reload capabilities
- Config merging with precedence rules
- Audit logging for changes
- Config caching with TTL
- Thread-safe operations
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class ConfigFormat(Enum):
    """Supported configuration formats."""
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    INI = "ini"


class ConfigSource(Enum):
    """Configuration sources."""
    FILE = "file"
    ENV_VAR = "env_var"
    REMOTE = "remote"
    DICT = "dict"


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class MergeStrategy(Enum):
    """Config merge strategies."""
    OVERRIDE = "override"  # Later configs override earlier
    DEEP_MERGE = "deep_merge"  # Deep merge nested dicts
    ADDITIVE = "additive"  # Combine values


# ==================== Data Classes ====================

@dataclass
class Config:
    """Represents a configuration."""
    config_id: str = field(default_factory=lambda: str(uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    source: ConfigSource = ConfigSource.DICT
    format: ConfigFormat = ConfigFormat.JSON
    environment: Optional[Environment] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation support."""
        keys = key.split('.')
        value = self.data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set config value with dot notation support."""
        keys = key.split('.')
        data = self.data

        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]

        data[keys[-1]] = value
        self.updated_at = datetime.utcnow()


@dataclass
class ConfigSchema:
    """Schema for config validation."""
    schema_id: str = field(default_factory=lambda: str(uuid4()))
    schema: Dict[str, Any] = field(default_factory=dict)
    strict: bool = True


@dataclass
class ConfigRequest:
    """Request for config loading."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    source: ConfigSource = ConfigSource.FILE
    source_path: str = ""
    format: ConfigFormat = ConfigFormat.JSON
    environment: Optional[Environment] = None
    merge_with_existing: bool = False


@dataclass
class AuthConfig:
    """Authentication configuration for remote sources."""
    auth_type: str = "token"
    credentials: Dict[str, str] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of config validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Change:
    """Represents a config change."""
    change_id: str = field(default_factory=lambda: str(uuid4()))
    key: str = ""
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VersionEntry:
    """Config version entry."""
    version: str = ""
    config_id: str = ""
    changes: List[Change] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    changed_by: str = "system"


@dataclass
class EncryptedValue:
    """Encrypted configuration value."""
    encrypted_data: str = ""
    algorithm: str = "base64"  # Simplified encryption
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReloadResult:
    """Result of config reload."""
    success: bool
    config_path: str = ""
    changes_detected: bool = False
    changes: List[Change] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class AuditEntry:
    """Config change audit entry."""
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    config_id: str = ""
    old_config: Optional[Config] = None
    new_config: Optional[Config] = None
    changes: List[Change] = field(default_factory=list)
    changed_by: str = "system"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""


@dataclass
class ConfigManagerResult:
    """Result of config management pipeline."""
    success: bool
    loaded_configs: int = 0
    failed_configs: int = 0
    merged_config: Optional[Config] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class CacheEntry:
    """Config cache entry."""
    config: Config
    ttl: timedelta
    cached_at: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() - self.cached_at > self.ttl


# ==================== Main FSA Class ====================

class ConfigManagerFSA:
    """
    Config Manager Finite State Automaton.

    Provides centralized configuration management with multi-source support,
    validation, versioning, encryption, and hot-reload capabilities.
    """

    def __init__(
        self,
        name: str = "ConfigManagerFSA",
        default_environment: Environment = Environment.DEVELOPMENT,
    ):
        """
        Initialize Config Manager FSA.

        Args:
            name: Name of the FSA instance
            default_environment: Default environment for configs
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.default_environment = default_environment

        # Config storage
        self.configs: Dict[str, Config] = {}
        self.active_config: Optional[Config] = None

        # Environment-specific configs
        self.env_configs: Dict[Environment, Config] = {}

        # Schema storage
        self.schemas: Dict[str, ConfigSchema] = {}

        # Versioning
        self.version_history: Dict[str, List[VersionEntry]] = defaultdict(list)
        self.current_versions: Dict[str, str] = {}

        # Audit logging
        self.audit_log: List[AuditEntry] = []

        # Caching
        self.config_cache: Dict[str, CacheEntry] = {}
        self.default_ttl = timedelta(minutes=5)

        # File watchers for hot-reload
        self.watched_files: Dict[str, float] = {}  # path -> last_modified

        # Encryption keys
        self.encryption_keys: Dict[str, str] = {}

        # Statistics
        self.total_loads: int = 0
        self.total_reloads: int = 0
        self.total_validations: int = 0

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, config_requests: List[ConfigRequest]) -> ConfigManagerResult:
        """
        Main config management pipeline.

        Args:
            config_requests: List of config requests to process

        Returns:
            ConfigManagerResult with processing statistics
        """
        loaded = 0
        failed = 0
        errors = []
        configs_to_merge = []

        for request in config_requests:
            try:
                # Load config based on source
                if request.source == ConfigSource.FILE:
                    config = self.load_from_file(request.source_path, request.format)
                elif request.source == ConfigSource.ENV_VAR:
                    config = self.load_from_env_vars(request.source_path or "APP")
                elif request.source == ConfigSource.REMOTE:
                    config = self.load_from_remote(request.source_path, AuthConfig())
                else:
                    errors.append(f"Unsupported source: {request.source}")
                    failed += 1
                    continue

                if config:
                    # Set environment
                    if request.environment:
                        config.environment = request.environment

                    # Store config
                    self.configs[config.config_id] = config
                    configs_to_merge.append(config)
                    loaded += 1

                    with self.lock:
                        self.total_loads += 1

            except Exception as e:
                errors.append(f"Error loading config: {str(e)}")
                failed += 1
                logger.error(f"Error loading config: {e}")

        # Merge configs if multiple
        merged_config = None
        if len(configs_to_merge) > 1:
            merged_config = self.merge_configs(configs_to_merge, MergeStrategy.DEEP_MERGE)
            self.active_config = merged_config
        elif len(configs_to_merge) == 1:
            merged_config = configs_to_merge[0]
            self.active_config = merged_config

        return ConfigManagerResult(
            success=failed == 0,
            loaded_configs=loaded,
            failed_configs=failed,
            merged_config=merged_config,
            errors=errors
        )

    # ==================== Validation ====================

    def validate(self, config_schema: ConfigSchema) -> ValidationResult:
        """
        Validate config schema.

        Args:
            config_schema: Schema to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check schema structure
        if not config_schema.schema:
            errors.append("Schema is empty")

        # Check schema has type
        if "type" not in config_schema.schema:
            warnings.append("Schema does not specify type")

        with self.lock:
            self.total_validations += 1

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_against_schema(
        self,
        config: Config,
        schema: ConfigSchema
    ) -> ValidationResult:
        """
        Validate config against schema.

        Args:
            config: Config to validate
            schema: Schema to validate against

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        try:
            # Simplified schema validation
            schema_def = schema.schema

            # Check required fields
            if "required" in schema_def:
                for field in schema_def["required"]:
                    if field not in config.data:
                        errors.append(f"Required field '{field}' is missing")

            # Check properties
            if "properties" in schema_def:
                for prop, prop_schema in schema_def["properties"].items():
                    if prop in config.data:
                        value = config.data[prop]
                        expected_type = prop_schema.get("type")

                        # Type checking
                        if expected_type:
                            if expected_type == "string" and not isinstance(value, str):
                                errors.append(f"Field '{prop}' should be string, got {type(value).__name__}")
                            elif expected_type == "number" and not isinstance(value, (int, float)):
                                errors.append(f"Field '{prop}' should be number, got {type(value).__name__}")
                            elif expected_type == "boolean" and not isinstance(value, bool):
                                errors.append(f"Field '{prop}' should be boolean, got {type(value).__name__}")
                            elif expected_type == "object" and not isinstance(value, dict):
                                errors.append(f"Field '{prop}' should be object, got {type(value).__name__}")
                            elif expected_type == "array" and not isinstance(value, list):
                                errors.append(f"Field '{prop}' should be array, got {type(value).__name__}")

            # Check for extra fields in strict mode
            if schema.strict and "properties" in schema_def:
                for prop in config.data:
                    if prop not in schema_def["properties"]:
                        warnings.append(f"Extra field '{prop}' not in schema")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            logger.error(f"Schema validation error: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Config Loading ====================

    def load_config(self, source: ConfigSource, format: ConfigFormat) -> Config:
        """
        Load config from source.

        Args:
            source: Config source type
            format: Config format

        Returns:
            Loaded Config
        """
        # Generic load method - delegates to specific loaders
        config = Config(source=source, format=format)
        return config

    def load_from_file(self, file_path: str, format: ConfigFormat) -> Config:
        """
        Load config from file.

        Args:
            file_path: Path to config file
            format: Config format

        Returns:
            Loaded Config
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {file_path}")

            with open(path, 'r') as f:
                content = f.read()

            # Parse based on format
            if format == ConfigFormat.YAML:
                config = self.parse_yaml(content)
            elif format == ConfigFormat.JSON:
                config = self.parse_json(content)
            elif format == ConfigFormat.TOML:
                config = self.parse_toml(content)
            elif format == ConfigFormat.INI:
                config = self.parse_ini(content)
            else:
                raise ValueError(f"Unsupported format: {format}")

            config.source = ConfigSource.FILE
            config.format = format
            config.metadata["file_path"] = str(path)

            # Watch file for hot-reload
            self.watched_files[file_path] = path.stat().st_mtime

            logger.info(f"Loaded config from {file_path}")
            return config

        except Exception as e:
            logger.error(f"Error loading config from file: {e}")
            raise

    def load_from_env_vars(self, prefix: str = "APP") -> Config:
        """
        Load config from environment variables.

        Args:
            prefix: Prefix for environment variables

        Returns:
            Config loaded from environment
        """
        config = Config(source=ConfigSource.ENV_VAR, format=ConfigFormat.JSON)

        prefix_with_sep = f"{prefix}_"

        for key, value in os.environ.items():
            if key.startswith(prefix_with_sep):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix_with_sep):].lower()

                # Try to parse as JSON for complex types
                try:
                    parsed_value = json.loads(value)
                    config.data[config_key] = parsed_value
                except json.JSONDecodeError:
                    # Store as string
                    config.data[config_key] = value

        config.metadata["prefix"] = prefix
        logger.info(f"Loaded {len(config.data)} config values from environment variables")
        return config

    def load_from_remote(self, remote_url: str, auth: AuthConfig) -> Config:
        """
        Load config from remote store.

        Args:
            remote_url: URL of remote config store
            auth: Authentication configuration

        Returns:
            Config loaded from remote store
        """
        # Mock implementation - in production would connect to Consul, etcd, AWS SSM, etc.
        config = Config(source=ConfigSource.REMOTE, format=ConfigFormat.JSON)

        config.data = {
            "remote_loaded": True,
            "remote_url": remote_url,
            "loaded_at": datetime.utcnow().isoformat()
        }

        config.metadata["remote_url"] = remote_url
        config.metadata["auth_type"] = auth.auth_type

        logger.info(f"Loaded config from remote: {remote_url}")
        return config

    # ==================== Config Parsing ====================

    def parse_yaml(self, yaml_content: str) -> Config:
        """
        Parse YAML format.

        Args:
            yaml_content: YAML content string

        Returns:
            Parsed Config
        """
        try:
            # Simplified YAML parsing (would use PyYAML in production)
            # For now, assume JSON-like structure
            import json
            data = json.loads(yaml_content.replace("'", '"'))

            config = Config(format=ConfigFormat.YAML, data=data)
            return config
        except Exception as e:
            logger.error(f"Error parsing YAML: {e}")
            # Try alternative parsing
            config = Config(format=ConfigFormat.YAML)
            config.data = {"raw_content": yaml_content}
            return config

    def parse_json(self, json_content: str) -> Config:
        """
        Parse JSON format.

        Args:
            json_content: JSON content string

        Returns:
            Parsed Config
        """
        try:
            data = json.loads(json_content)
            config = Config(format=ConfigFormat.JSON, data=data)
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            raise ValueError(f"Invalid JSON: {e}")

    def parse_toml(self, toml_content: str) -> Config:
        """
        Parse TOML format.

        Args:
            toml_content: TOML content string

        Returns:
            Parsed Config
        """
        # Simplified TOML parsing (would use tomli in production)
        config = Config(format=ConfigFormat.TOML)

        # Basic INI-like parsing
        current_section = None
        for line in toml_content.split('\n'):
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                config.data[current_section] = {}
            elif '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')

                # Try to parse as number or boolean
                try:
                    if value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    else:
                        value = json.loads(value)
                except:
                    pass

                if current_section:
                    config.data[current_section][key] = value
                else:
                    config.data[key] = value

        return config

    def parse_ini(self, ini_content: str) -> Config:
        """
        Parse INI format.

        Args:
            ini_content: INI content string

        Returns:
            Parsed Config
        """
        config = Config(format=ConfigFormat.INI)

        current_section = "default"
        config.data[current_section] = {}

        for line in ini_content.split('\n'):
            line = line.strip()

            if not line or line.startswith(';') or line.startswith('#'):
                continue

            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                config.data[current_section] = {}
            elif '=' in line:
                key, value = line.split('=', 1)
                config.data[current_section][key.strip()] = value.strip()

        return config

    # ==================== Environment Management ====================

    def get_env_config(self, environment: Environment) -> Config:
        """
        Get environment-specific config.

        Args:
            environment: Environment type

        Returns:
            Environment-specific Config
        """
        with self.lock:
            if environment in self.env_configs:
                return self.env_configs[environment]

            # Create new env config
            config = Config(environment=environment)
            self.env_configs[environment] = config
            return config

    def set_env_config(self, environment: Environment, config: Config) -> None:
        """Set environment-specific config."""
        config.environment = environment
        with self.lock:
            self.env_configs[environment] = config

    # ==================== Versioning ====================

    def track_version(
        self,
        config: Config,
        version: str,
        changes: List[Change]
    ) -> VersionEntry:
        """
        Track config changes.

        Args:
            config: Config to version
            version: Version string
            changes: List of changes

        Returns:
            VersionEntry with version info
        """
        entry = VersionEntry(
            version=version,
            config_id=config.config_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )

        with self.lock:
            self.version_history[config.config_id].append(entry)
            self.current_versions[config.config_id] = version

        logger.info(f"Tracked version {version} for config {config.config_id}")
        return entry

    def get_version_history(self, config_id: str) -> List[VersionEntry]:
        """Get version history for config."""
        return self.version_history.get(config_id, [])

    def detect_changes(self, old_config: Config, new_config: Config) -> List[Change]:
        """Detect changes between configs."""
        changes = []

        # Check all keys in both configs
        all_keys = set(old_config.data.keys()) | set(new_config.data.keys())

        for key in all_keys:
            old_value = old_config.data.get(key)
            new_value = new_config.data.get(key)

            if old_value != new_value:
                changes.append(Change(
                    key=key,
                    old_value=old_value,
                    new_value=new_value
                ))

        return changes

    # ==================== Encryption ====================

    def encrypt_secret(self, value: str, encryption_key: str) -> EncryptedValue:
        """
        Encrypt sensitive config.

        Args:
            value: Value to encrypt
            encryption_key: Encryption key

        Returns:
            EncryptedValue with encrypted data
        """
        # Simplified encryption using base64 (use cryptography library in production)
        encrypted_bytes = base64.b64encode(value.encode('utf-8'))
        encrypted_str = encrypted_bytes.decode('utf-8')

        return EncryptedValue(
            encrypted_data=encrypted_str,
            algorithm="base64"
        )

    def decrypt_secret(self, encrypted_value: str, encryption_key: str) -> str:
        """
        Decrypt sensitive config.

        Args:
            encrypted_value: Encrypted value
            encryption_key: Decryption key

        Returns:
            Decrypted string value
        """
        # Simplified decryption using base64
        try:
            decrypted_bytes = base64.b64decode(encrypted_value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting value: {e}")
            raise ValueError(f"Decryption failed: {e}")

    # ==================== Hot-Reload ====================

    def hot_reload_config(self, config_path: str) -> ReloadResult:
        """
        Update config without restart.

        Args:
            config_path: Path to config file

        Returns:
            ReloadResult with reload status
        """
        try:
            path = Path(config_path)

            if not path.exists():
                return ReloadResult(
                    success=False,
                    config_path=config_path,
                    error="File not found"
                )

            # Check if file has been modified
            current_mtime = path.stat().st_mtime
            last_mtime = self.watched_files.get(config_path, 0)

            if current_mtime <= last_mtime:
                return ReloadResult(
                    success=True,
                    config_path=config_path,
                    changes_detected=False
                )

            # Load new config
            # Detect format from extension
            format_map = {
                '.json': ConfigFormat.JSON,
                '.yaml': ConfigFormat.YAML,
                '.yml': ConfigFormat.YAML,
                '.toml': ConfigFormat.TOML,
                '.ini': ConfigFormat.INI
            }
            format = format_map.get(path.suffix, ConfigFormat.JSON)

            new_config = self.load_from_file(config_path, format)

            # Detect changes
            changes = []
            if self.active_config:
                changes = self.detect_changes(self.active_config, new_config)

            # Update active config
            self.active_config = new_config
            self.watched_files[config_path] = current_mtime

            with self.lock:
                self.total_reloads += 1

            logger.info(f"Hot-reloaded config from {config_path}")
            return ReloadResult(
                success=True,
                config_path=config_path,
                changes_detected=len(changes) > 0,
                changes=changes
            )

        except Exception as e:
            logger.error(f"Error hot-reloading config: {e}")
            return ReloadResult(
                success=False,
                config_path=config_path,
                error=str(e)
            )

    # ==================== Config Merging ====================

    def merge_configs(
        self,
        configs: List[Config],
        merge_strategy: MergeStrategy = MergeStrategy.DEEP_MERGE
    ) -> Config:
        """
        Combine layered configs.

        Args:
            configs: List of configs to merge
            merge_strategy: Strategy for merging

        Returns:
            Merged Config
        """
        if not configs:
            return Config()

        if len(configs) == 1:
            return configs[0]

        merged = Config()

        if merge_strategy == MergeStrategy.OVERRIDE:
            # Simple override - later configs win
            for config in configs:
                merged.data.update(config.data)

        elif merge_strategy == MergeStrategy.DEEP_MERGE:
            # Deep merge nested dictionaries
            for config in configs:
                self._deep_merge_dict(merged.data, config.data)

        elif merge_strategy == MergeStrategy.ADDITIVE:
            # Combine values (for lists and sets)
            for config in configs:
                for key, value in config.data.items():
                    if key in merged.data:
                        if isinstance(merged.data[key], list) and isinstance(value, list):
                            merged.data[key].extend(value)
                        elif isinstance(merged.data[key], set) and isinstance(value, set):
                            merged.data[key].update(value)
                        else:
                            merged.data[key] = value
                    else:
                        merged.data[key] = value

        merged.version = "merged"
        merged.metadata["merged_count"] = len(configs)
        merged.metadata["merge_strategy"] = merge_strategy.value

        logger.info(f"Merged {len(configs)} configs using {merge_strategy.value} strategy")
        return merged

    def _deep_merge_dict(self, target: Dict, source: Dict) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge_dict(target[key], value)
            else:
                target[key] = value

    # ==================== Audit Logging ====================

    def audit_config_change(
        self,
        old_config: Config,
        new_config: Config,
        changed_by: str,
        reason: str = ""
    ) -> AuditEntry:
        """
        Log config change.

        Args:
            old_config: Previous config
            new_config: New config
            changed_by: User who made the change
            reason: Reason for change

        Returns:
            AuditEntry with change details
        """
        changes = self.detect_changes(old_config, new_config)

        entry = AuditEntry(
            config_id=new_config.config_id,
            old_config=old_config,
            new_config=new_config,
            changes=changes,
            changed_by=changed_by,
            reason=reason
        )

        with self.lock:
            self.audit_log.append(entry)

        logger.info(f"Audited config change by {changed_by}: {len(changes)} changes")
        return entry

    def get_audit_log(self, config_id: Optional[str] = None) -> List[AuditEntry]:
        """Get audit log entries."""
        if config_id:
            return [entry for entry in self.audit_log if entry.config_id == config_id]
        return self.audit_log

    # ==================== Caching ====================

    def cache_config(self, config: Config, ttl: Optional[timedelta] = None) -> None:
        """
        Cache config for performance.

        Args:
            config: Config to cache
            ttl: Time to live (optional)
        """
        cache_key = config.config_id
        ttl = ttl or self.default_ttl

        entry = CacheEntry(
            config=config,
            ttl=ttl
        )

        with self.lock:
            self.config_cache[cache_key] = entry

        logger.debug(f"Cached config {cache_key} with TTL {ttl}")

    def get_cached_config(self, cache_key: str) -> Optional[Config]:
        """
        Retrieve cached config.

        Args:
            cache_key: Cache key

        Returns:
            Cached Config or None if expired/not found
        """
        with self.lock:
            if cache_key in self.config_cache:
                entry = self.config_cache[cache_key]

                if entry.is_expired():
                    del self.config_cache[cache_key]
                    logger.debug(f"Cache expired for {cache_key}")
                    return None

                logger.debug(f"Cache hit for {cache_key}")
                return entry.config

        return None

    def clear_cache(self) -> None:
        """Clear all cached configs."""
        with self.lock:
            self.config_cache.clear()
        logger.info("Cleared config cache")

    # ==================== Config Export ====================

    def export_config(self, config: Config, format: ConfigFormat) -> str:
        """
        Export config to format.

        Args:
            config: Config to export
            format: Target format

        Returns:
            Exported config as string
        """
        try:
            if format == ConfigFormat.JSON:
                return json.dumps(config.data, indent=2)

            elif format == ConfigFormat.YAML:
                # Simple YAML export
                return self._dict_to_yaml(config.data)

            elif format == ConfigFormat.TOML:
                # Simple TOML export
                return self._dict_to_toml(config.data)

            elif format == ConfigFormat.INI:
                # Simple INI export
                return self._dict_to_ini(config.data)

            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Error exporting config: {e}")
            raise

    def _dict_to_yaml(self, data: Dict, indent: int = 0) -> str:
        """Convert dict to YAML format."""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}{key}:")
                lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{'  ' * indent}{key}:")
                for item in value:
                    lines.append(f"{'  ' * (indent + 1)}- {item}")
            else:
                lines.append(f"{'  ' * indent}{key}: {value}")
        return '\n'.join(lines)

    def _dict_to_toml(self, data: Dict) -> str:
        """Convert dict to TOML format."""
        lines = []

        # Simple values first
        for key, value in data.items():
            if not isinstance(value, dict):
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, bool):
                    lines.append(f'{key} = {str(value).lower()}')
                else:
                    lines.append(f'{key} = {value}')

        # Sections (dicts)
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'\n[{key}]')
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, str):
                        lines.append(f'{subkey} = "{subvalue}"')
                    elif isinstance(subvalue, bool):
                        lines.append(f'{subkey} = {str(subvalue).lower()}')
                    else:
                        lines.append(f'{subkey} = {subvalue}')

        return '\n'.join(lines)

    def _dict_to_ini(self, data: Dict) -> str:
        """Convert dict to INI format."""
        lines = []

        for section, values in data.items():
            lines.append(f'[{section}]')
            if isinstance(values, dict):
                for key, value in values.items():
                    lines.append(f'{key} = {value}')
            lines.append('')

        return '\n'.join(lines)

    # ==================== Utility Methods ====================

    def get_config(self, config_id: str) -> Optional[Config]:
        """Get config by ID."""
        return self.configs.get(config_id)

    def register_encryption_key(self, key_id: str, key: str) -> None:
        """Register encryption key."""
        with self.lock:
            self.encryption_keys[key_id] = key

    def get_stats(self) -> Dict[str, Any]:
        """Get configuration manager statistics."""
        return {
            "total_configs": len(self.configs),
            "total_loads": self.total_loads,
            "total_reloads": self.total_reloads,
            "total_validations": self.total_validations,
            "cached_configs": len(self.config_cache),
            "watched_files": len(self.watched_files),
            "audit_entries": len(self.audit_log)
        }

"""
FSA Production Configuration - Environment-specific settings

Provides configuration management for different deployment environments
with support for rate limiting, logging, monitoring, resource allocation,
and error handling strategies.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Environment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enabled: bool = True
    requests_per_second: int = 100
    burst_size: int = 200
    per_module_limits: Dict[str, int] = field(default_factory=dict)

    def get_module_limit(self, module_name: str) -> int:
        """Get rate limit for specific module"""
        return self.per_module_limits.get(module_name, self.requests_per_second)


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    enable_json_logging: bool = False
    include_trace_id: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    enabled: bool = True
    metrics_port: int = 9090
    health_check_interval_seconds: int = 60
    enable_prometheus: bool = False
    enable_datadog: bool = False
    custom_metrics_enabled: bool = True
    alert_on_failure: bool = True


@dataclass
class ResourceConfig:
    """Resource allocation configuration"""
    max_workers: int = 4
    max_memory_mb: int = 1024
    max_cpu_percent: int = 80
    pipeline_timeout_seconds: int = 300
    stage_timeout_seconds: int = 60
    enable_auto_scaling: bool = False


@dataclass
class CacheConfig:
    """Caching configuration"""
    enabled: bool = True
    ttl_seconds: int = 3600
    max_cache_size_mb: int = 512
    cache_backend: str = "memory"  # memory, redis, memcached
    redis_url: Optional[str] = None
    eviction_policy: str = "lru"  # lru, lfu, fifo


@dataclass
class ErrorHandlingConfig:
    """Error handling and retry configuration"""
    max_retries: int = 3
    retry_backoff_ms: int = 1000
    retry_backoff_multiplier: float = 2.0
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    enable_dead_letter_queue: bool = True
    alert_on_repeated_failures: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_authentication: bool = False
    enable_authorization: bool = False
    api_key_required: bool = False
    enable_rate_limiting: bool = True
    enable_input_validation: bool = True
    enable_output_sanitization: bool = True
    allowed_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class FSAProductionConfig:
    """
    Comprehensive production configuration for FSA Framework

    Provides environment-specific settings for all aspects of FSA operation
    including rate limiting, logging, monitoring, resource allocation,
    caching, error handling, and security.
    """

    environment: Environment = Environment.DEVELOPMENT
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    caching: CacheConfig = field(default_factory=CacheConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_environment(cls, env: Optional[str] = None) -> "FSAProductionConfig":
        """
        Create configuration from environment

        Args:
            env: Environment name (development, staging, production, test)

        Returns:
            FSAProductionConfig instance
        """
        env = env or os.getenv("FSA_ENVIRONMENT", "development")
        environment = Environment(env.lower())

        if environment == Environment.DEVELOPMENT:
            return cls._create_development_config()
        elif environment == Environment.STAGING:
            return cls._create_staging_config()
        elif environment == Environment.PRODUCTION:
            return cls._create_production_config()
        elif environment == Environment.TEST:
            return cls._create_test_config()
        else:
            raise ValueError(f"Unknown environment: {env}")

    @classmethod
    def _create_development_config(cls) -> "FSAProductionConfig":
        """Create development environment configuration"""
        return cls(
            environment=Environment.DEVELOPMENT,
            rate_limiting=RateLimitConfig(
                enabled=False,  # Disabled for dev
                requests_per_second=1000,
            ),
            logging=LoggingConfig(
                level="DEBUG",
                file_path="logs/fsa_dev.log",
                enable_json_logging=False,
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                metrics_port=9090,
                enable_prometheus=False,
            ),
            resources=ResourceConfig(
                max_workers=2,
                max_memory_mb=512,
                pipeline_timeout_seconds=600,
            ),
            caching=CacheConfig(
                enabled=True,
                ttl_seconds=600,
                cache_backend="memory",
            ),
            error_handling=ErrorHandlingConfig(
                max_retries=5,
                circuit_breaker_enabled=False,
            ),
            security=SecurityConfig(
                enable_authentication=False,
                api_key_required=False,
            ),
        )

    @classmethod
    def _create_staging_config(cls) -> "FSAProductionConfig":
        """Create staging environment configuration"""
        return cls(
            environment=Environment.STAGING,
            rate_limiting=RateLimitConfig(
                enabled=True,
                requests_per_second=200,
                burst_size=400,
            ),
            logging=LoggingConfig(
                level="INFO",
                file_path="logs/fsa_staging.log",
                enable_json_logging=True,
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                metrics_port=9090,
                enable_prometheus=True,
                health_check_interval_seconds=30,
            ),
            resources=ResourceConfig(
                max_workers=4,
                max_memory_mb=1024,
                pipeline_timeout_seconds=300,
                enable_auto_scaling=True,
            ),
            caching=CacheConfig(
                enabled=True,
                ttl_seconds=1800,
                max_cache_size_mb=256,
                cache_backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            ),
            error_handling=ErrorHandlingConfig(
                max_retries=3,
                circuit_breaker_enabled=True,
                enable_dead_letter_queue=True,
            ),
            security=SecurityConfig(
                enable_authentication=True,
                enable_authorization=True,
                api_key_required=True,
                enable_rate_limiting=True,
            ),
        )

    @classmethod
    def _create_production_config(cls) -> "FSAProductionConfig":
        """Create production environment configuration"""
        return cls(
            environment=Environment.PRODUCTION,
            rate_limiting=RateLimitConfig(
                enabled=True,
                requests_per_second=100,
                burst_size=200,
                per_module_limits={
                    "multi_step_builder": 50,
                    "rsi_optimizer": 30,
                    "meta_orchestrator": 20,
                },
            ),
            logging=LoggingConfig(
                level="WARNING",
                file_path="/var/log/fsa/production.log",
                enable_json_logging=True,
                include_trace_id=True,
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                metrics_port=9090,
                enable_prometheus=True,
                enable_datadog=True,
                health_check_interval_seconds=60,
                alert_on_failure=True,
            ),
            resources=ResourceConfig(
                max_workers=8,
                max_memory_mb=2048,
                max_cpu_percent=80,
                pipeline_timeout_seconds=300,
                stage_timeout_seconds=60,
                enable_auto_scaling=True,
            ),
            caching=CacheConfig(
                enabled=True,
                ttl_seconds=3600,
                max_cache_size_mb=1024,
                cache_backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                eviction_policy="lru",
            ),
            error_handling=ErrorHandlingConfig(
                max_retries=3,
                retry_backoff_ms=1000,
                retry_backoff_multiplier=2.0,
                circuit_breaker_enabled=True,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout_seconds=60,
                enable_dead_letter_queue=True,
                alert_on_repeated_failures=True,
            ),
            security=SecurityConfig(
                enable_authentication=True,
                enable_authorization=True,
                api_key_required=True,
                enable_rate_limiting=True,
                enable_input_validation=True,
                enable_output_sanitization=True,
                allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
            ),
        )

    @classmethod
    def _create_test_config(cls) -> "FSAProductionConfig":
        """Create test environment configuration"""
        return cls(
            environment=Environment.TEST,
            rate_limiting=RateLimitConfig(
                enabled=False,
            ),
            logging=LoggingConfig(
                level="DEBUG",
                enable_json_logging=False,
            ),
            monitoring=MonitoringConfig(
                enabled=False,
            ),
            resources=ResourceConfig(
                max_workers=1,
                max_memory_mb=256,
                pipeline_timeout_seconds=30,
            ),
            caching=CacheConfig(
                enabled=False,
            ),
            error_handling=ErrorHandlingConfig(
                max_retries=1,
                circuit_breaker_enabled=False,
            ),
            security=SecurityConfig(
                enable_authentication=False,
                api_key_required=False,
            ),
        )

    def apply_logging_config(self) -> None:
        """Apply logging configuration to Python logging system"""
        log_level = getattr(logging, self.logging.level.upper())

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=self.logging.format,
        )

        # Add file handler if specified
        if self.logging.file_path:
            try:
                from logging.handlers import RotatingFileHandler

                # Ensure log directory exists
                log_dir = os.path.dirname(self.logging.file_path)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                file_handler = RotatingFileHandler(
                    self.logging.file_path,
                    maxBytes=self.logging.max_bytes,
                    backupCount=self.logging.backup_count,
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(logging.Formatter(self.logging.format))

                logging.getLogger().addHandler(file_handler)
            except Exception as e:
                logging.warning(f"Failed to setup file logging: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "environment": self.environment.value,
            "rate_limiting": {
                "enabled": self.rate_limiting.enabled,
                "requests_per_second": self.rate_limiting.requests_per_second,
                "burst_size": self.rate_limiting.burst_size,
                "per_module_limits": self.rate_limiting.per_module_limits,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "enable_json_logging": self.logging.enable_json_logging,
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "metrics_port": self.monitoring.metrics_port,
                "health_check_interval_seconds": self.monitoring.health_check_interval_seconds,
            },
            "resources": {
                "max_workers": self.resources.max_workers,
                "max_memory_mb": self.resources.max_memory_mb,
                "max_cpu_percent": self.resources.max_cpu_percent,
            },
            "caching": {
                "enabled": self.caching.enabled,
                "ttl_seconds": self.caching.ttl_seconds,
                "cache_backend": self.caching.cache_backend,
            },
            "error_handling": {
                "max_retries": self.error_handling.max_retries,
                "circuit_breaker_enabled": self.error_handling.circuit_breaker_enabled,
            },
            "security": {
                "enable_authentication": self.security.enable_authentication,
                "api_key_required": self.security.api_key_required,
            },
            "custom_settings": self.custom_settings,
        }


# Global configuration instance
_global_config: Optional[FSAProductionConfig] = None


def get_fsa_config(
    env: Optional[str] = None,
    force_reload: bool = False,
) -> FSAProductionConfig:
    """
    Get the global FSA configuration instance

    Args:
        env: Environment name (overrides FSA_ENVIRONMENT)
        force_reload: Force reload configuration

    Returns:
        FSAProductionConfig instance
    """
    global _global_config

    if _global_config is None or force_reload:
        _global_config = FSAProductionConfig.from_environment(env)
        _global_config.apply_logging_config()

    return _global_config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)"""
    global _global_config
    _global_config = None

"""Errors raised while loading configuration."""


class ConfigError(ValueError):
    """Configuration is missing, malformed, or violates a safety policy."""

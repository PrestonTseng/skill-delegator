"""Errors raised while loading configuration."""


class ConfigError(ValueError):
    """Configuration is missing, malformed, or violates a safety policy."""


class SourceError(ValueError):
    """A source cannot be safely resolved, inventoried, or locked."""

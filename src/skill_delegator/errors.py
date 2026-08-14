"""Errors raised while loading configuration."""


class ConfigError(ValueError):
    """Configuration is missing, malformed, or violates a safety policy."""


class SourceError(ValueError):
    """A source cannot be safely resolved, inventoried, or locked."""


class UpdateError(SourceError):
    """A bounded public update failure containing allow-listed identifiers only."""

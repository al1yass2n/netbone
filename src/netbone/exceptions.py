"""Exception hierarchy for Netbone."""


class NetboneError(Exception):
    """Base class for all package-specific errors."""


class ValidationError(NetboneError):
    """Raised when input data is malformed or missing required values."""


class ConfigurationError(NetboneError):
    """Raised when a pipeline, method, or filter configuration is invalid."""


class CompatibilityError(NetboneError):
    """Raised when an input graph or result is unsupported by this release."""


class UndefinedMetricError(NetboneError):
    """Raised when a requested metric is valid but mathematically undefined."""

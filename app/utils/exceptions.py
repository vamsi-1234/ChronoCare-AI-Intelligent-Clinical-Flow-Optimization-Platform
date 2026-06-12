"""Custom exceptions for ChronoCare AI."""


class ModelNotLoadedError(Exception):
    """Raised when an ML model has not been trained/loaded yet."""
    pass


class InvalidInputError(ValueError):
    """Raised when input data fails business-rule validation."""
    pass


class SimulationError(Exception):
    """Raised when the schedule simulation fails."""
    pass


class OptimizationError(Exception):
    """Raised when schedule optimisation fails or times out."""
    pass


class CacheError(Exception):
    """Raised for non-fatal cache failures (should be caught and logged)."""
    pass

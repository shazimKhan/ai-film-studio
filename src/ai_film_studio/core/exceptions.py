"""Framework exception hierarchy."""


class AIFilmStudioError(Exception):
    """Base error for all framework-level failures."""


class ConfigurationError(AIFilmStudioError):
    """Raised when framework configuration is invalid."""


class ModuleLoadError(AIFilmStudioError):
    """Raised when dynamic module loading fails."""


class AdapterRegistrationError(AIFilmStudioError):
    """Raised when an engine adapter cannot be registered or resolved."""


class BuildError(AIFilmStudioError):
    """Raised when the framework runtime cannot be built."""


class StudioValidationError(AIFilmStudioError):
    """Raised when validation fails at a framework boundary."""


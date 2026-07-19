"""Framework exception hierarchy."""


class AIFilmStudioError(Exception):
    """Base error for all framework-level failures."""


class ConfigurationError(AIFilmStudioError):
    """Raised when framework configuration is invalid."""


class ModuleLoadError(AIFilmStudioError):
    """Raised when dynamic module loading fails."""


class InvalidYAMLError(ModuleLoadError):
    """Raised when a YAML file cannot be parsed."""


class MalformedConfigurationError(ConfigurationError):
    """Raised when a configuration file has the wrong shape."""


class AdapterRegistrationError(AIFilmStudioError):
    """Raised when an engine adapter cannot be registered or resolved."""


class BuildError(AIFilmStudioError):
    """Raised when the framework runtime cannot be built."""


class StudioValidationError(AIFilmStudioError):
    """Raised when validation fails at a framework boundary."""


class PromptCompilationError(AIFilmStudioError):
    """Raised when local prompt compilation cannot complete."""


class SceneFileError(PromptCompilationError):
    """Raised when a scene blueprint file cannot be loaded."""


class AssetNotFoundError(PromptCompilationError):
    """Raised when a referenced reusable asset file cannot be found."""


class UnsupportedEngineError(PromptCompilationError):
    """Raised when a requested engine adapter is not registered."""


class OutputWriteError(PromptCompilationError):
    """Raised when a compiled prompt cannot be written."""

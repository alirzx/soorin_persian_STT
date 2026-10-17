class STTError(Exception):
    code = "stt_error"
    status = 500

class ModelUnavailable(STTError):
    code = "model_unavailable"
    status = 503

class InvalidAudio(STTError):
    code = "invalid_audio"
    status = 422

class Overloaded(STTError):
    code = "capacity_exceeded"
    status = 429

class UnsupportedRuntime(STTError):
    code = "unsupported_runtime"
    status = 422

class ConfigurationError(STTError):
    code = "invalid_configuration"
    status = 503

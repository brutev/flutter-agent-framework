from enum import StrEnum


class ProviderFailureCategory(StrEnum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    PERMANENT = "permanent"
    CAPABILITY = "capability"
    MALFORMED_RESPONSE = "malformed_response"
    CANCELLED = "cancelled"


class ProviderFailure(RuntimeError):
    def __init__(self, message: str, category: ProviderFailureCategory):
        super().__init__(message)
        self.category = category


def classify_provider_failure(exc: Exception) -> ProviderFailureCategory:
    if isinstance(exc, ProviderFailure):
        return exc.category
    text = str(exc).casefold()
    if "429" in text or "rate limit" in text:
        return ProviderFailureCategory.RATE_LIMIT
    if "timeout" in text or "timed out" in text:
        return ProviderFailureCategory.TIMEOUT
    if any(token in text for token in ("502", "503", "504", "temporarily", "connection")):
        return ProviderFailureCategory.TRANSIENT
    if any(token in text for token in ("401", "403", "authentication", "api key", "invalid model")):
        return ProviderFailureCategory.PERMANENT
    return ProviderFailureCategory.TRANSIENT

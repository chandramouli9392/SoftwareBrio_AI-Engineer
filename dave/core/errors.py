"""Typed exceptions raised by DAVE."""

from __future__ import annotations


class DaveError(Exception):
    """Base class for all DAVE exceptions."""


class FetchError(DaveError):
    """Raised when fetching a page fails."""


class CaptchaDetectedError(FetchError):
    """Raised when DAVE detects a CAPTCHA or bot challenge."""


class RobotsDisallowedError(FetchError):
    """Raised when robots.txt disallows fetching a URL and robots are respected."""


class LeadsConfigError(DaveError):
    """Raised when the local-leads source (Apify) is not configured."""


class LeadsRequestError(DaveError):
    """Raised when the local-leads source request fails."""


class ExtractionError(DaveError):
    """Raised when extraction fails."""


class ValidationError(ExtractionError):
    """Raised when extracted data cannot satisfy a schema."""


class LowConfidenceError(ExtractionError):
    """Raised when extraction confidence remains below the configured threshold."""

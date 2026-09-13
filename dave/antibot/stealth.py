"""Polite anti-detection helpers.

DAVE does not solve CAPTCHAs or bypass access controls. It detects challenges and raises clear errors.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

COMMON_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# Strong signals of an actual interstitial/challenge page. These rarely appear
# in normal article prose, so they flag on their own.
CHALLENGE_PAGE_MARKERS = [
    "__cf_chl",
    "cf-challenge",
    "cf-browser-verification",
    "/cdn-cgi/challenge",
    "challenge-platform",
    "checking your browser before",
]

# Weaker signals (widgets and phrases) that also appear on legitimate content
# pages. These only count when the page has little visible text — i.e. it looks
# like a block interstitial rather than a real page that embeds a widget.
SOFT_CAPTCHA_MARKERS = [
    "g-recaptcha",
    "hcaptcha",
    "h-captcha",
    "cf-turnstile",
    "are you human",
    "verify you are human",
    "complete the security check",
    "unusual traffic from your",
]

# Maximum visible-text length (characters) for a page to still be treated as a
# possible interstitial when only soft markers are present.
_INTERSTITIAL_MAX_CHARS = 1500


class UserAgentRotator:
    """Select user agents from a curated pool."""

    def __init__(self, user_agents: list[str] | None = None) -> None:
        self.user_agents = user_agents or COMMON_USER_AGENTS

    def get(self) -> str:
        """Return one user agent."""
        return random.choice(self.user_agents)


@dataclass(slots=True)
class DelayPolicy:
    """Random request delay policy."""

    min_seconds: float = 0.0
    max_seconds: float = 1.5

    def next_delay(self) -> float:
        """Return the next randomized delay."""
        if self.max_seconds < self.min_seconds:
            raise ValueError("max_seconds must be greater than or equal to min_seconds")
        return random.uniform(self.min_seconds, self.max_seconds)


def random_headers(user_agent: str | None = None) -> dict[str, str]:
    """Build browser-like headers."""
    return {
        "User-Agent": user_agent or UserAgentRotator().get(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "en;q=0.7"]),
        "DNT": random.choice(["0", "1"]),
        "Upgrade-Insecure-Requests": "1",
    }


def detect_captcha(html: str, text: str = "") -> bool:
    """Return True when a page appears to be a CAPTCHA or bot-challenge interstitial.

    Strong challenge markers flag on their own. Soft markers (widgets, phrases that
    also occur on legitimate pages) only flag when the page has little visible text,
    so a real article that merely mentions or embeds a CAPTCHA is not blocked.
    """
    lower = html.lower()
    if any(marker in lower for marker in CHALLENGE_PAGE_MARKERS):
        return True
    visible_chars = len(text.strip()) if text else len(re.sub(r"<[^>]+>", " ", html).strip())
    if visible_chars < _INTERSTITIAL_MAX_CHARS and any(marker in lower for marker in SOFT_CAPTCHA_MARKERS):
        return True
    return False

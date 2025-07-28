"""Security page detection service."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class SecurityPageDetector:
    """Detect security/protection pages and provide helpful feedback."""

    SECURITY_PATTERNS = [
        r"browsing activity.*paused.*unusual behavior",
        r"security check.*in progress",
        r"access.*temporarily.*restricted",
        r"please verify.*you.*human",
        r"cloudflare.*(security|checking|challenge)",
        r"ddos.*protection.*active",
        r"bot.*activity.*detected",
        r"automated.*traffic.*blocked",
        r"rate.*limit.*exceeded",
        r"temporarily.*unavailable",
        r"maintenance.*mode",
        r"service.*temporarily.*unavailable",
        r"access.*denied",
        # More specific captcha patterns that indicate actual security challenges
        r"complete.*captcha.*to.*continue",
        r"solve.*captcha.*to.*proceed",
        r"captcha.*required.*to.*access",
        r"verify.*captcha.*below",
        r"please.*complete.*the.*captcha",
        r"captcha.*verification.*required",
    ]

    SECURITY_INDICATORS = [
        "unusual behavior",
        "security check",
        "ddos protection",
        "rate limit",
        "bot detection",
        "automated traffic",
        "verify you are human",
        # Removed generic "captcha" to avoid false positives with form reCAPTCHA
    ]

    @classmethod
    def detect_security_page(
        cls: type[SecurityPageDetector],
        html: str,
        url: str,
    ) -> tuple[bool, str | None]:
        """Detect if the HTML content is a security/protection page.

        Args:
            html: The HTML content to check
            url: The URL being checked (for domain-specific rules)

        Returns:
            Tuple of (is_security_page, detected_reason)

        """
        if not html or len(html.strip()) < 100:
            return True, f"Empty or minimal content from {url}"

        html_lower = html.lower()

        # Check for security patterns
        for pattern in cls.SECURITY_PATTERNS:
            if re.search(pattern, html_lower, re.IGNORECASE):
                return True, f"Security pattern detected: {pattern}"

        # Check for security indicators
        for indicator in cls.SECURITY_INDICATORS:
            if indicator in html_lower:
                return True, f"Security indicator found: {indicator}"

        # Check for very short content (often security pages) - but be less aggressive
        text_content = re.sub(r"<[^>]+>", "", html)
        if len(text_content.strip()) < 200:  # Reduced from 500 to 200
            return True, "Suspiciously short content"

        # Check for common error status in title/headers
        if re.search(r"<title>[^<]*(?:error|403|503|blocked|denied)", html_lower):
            return True, "Error page detected in title"

        # Check for actual blocking captcha (not just form reCAPTCHA)
        # Only flag as security page if it's a standalone captcha challenge
        if cls._is_blocking_captcha_page(html_lower):
            return True, "Standalone captcha challenge detected"

        # Domain-specific checks
        if "cloudflare" in url.lower() and "challenge" in html_lower:
            return True, "Cloudflare challenge page"

        return False, None

    @classmethod
    def _is_blocking_captcha_page(
        cls: type[SecurityPageDetector],
        html_lower: str,
    ) -> bool:
        """Detect if this is actually a blocking captcha page vs a page with form reCAPTCHA.

        Returns True only if the page appears to be primarily a captcha challenge.
        """
        # Skip if this looks like legitimate reCAPTCHA integration for forms
        if any(
            pattern in html_lower
            for pattern in [
                "recaptcha-regmodal",  # Registration modal
                "recaptcha-rsvpmodal",  # RSVP modal
                "recaptcha-giveawaymodal",  # Giveaway modal
                "grecaptcha.render",  # Google reCAPTCHA API usage
                "onload=recaptchaready",  # Standard reCAPTCHA loading
                "form",  # Page contains forms (likely legitimate use)
                "register",  # Registration functionality
                "login",  # Login functionality
                "contact",  # Contact forms
            ]
        ):
            return False

        # Look for actual blocking captcha indicators
        blocking_indicators = [
            # Title suggests it's a captcha page
            r"<title[^>]*>[^<]*(?:captcha|verify|challenge|security)[^<]*</title>",
            # Body content is minimal and captcha-focused
            r"<h1[^>]*>[^<]*(?:complete.*captcha|verify.*human|security.*check)[^<]*</h1>",
            # Direct captcha challenge instructions
            r"(?:complete|solve|verify).*captcha.*(?:continue|proceed|access)",
            # Cloudflare challenge patterns
            r"checking.*browser.*before.*accessing",
            r"ray.*id.*[a-f0-9]{16}",  # Cloudflare Ray ID
        ]

        for pattern in blocking_indicators:
            if re.search(pattern, html_lower, re.IGNORECASE):
                return True

        return False

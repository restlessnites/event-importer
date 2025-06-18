"""Security page detection service."""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class SecurityPageDetector:
    """Detect security/protection pages and provide helpful feedback."""
    
    SECURITY_PATTERNS = [
        r"browsing activity.*paused.*unusual behavior",
        r"security check.*in progress", 
        r"access.*temporarily.*restricted",
        r"please verify.*you.*human",
        r"cloudflare.*checking.*browser",
        r"ddos.*protection.*active",
        r"bot.*activity.*detected",
        r"automated.*traffic.*blocked",
        r"rate.*limit.*exceeded",
        r"temporarily.*unavailable",
        r"maintenance.*mode",
        r"service.*temporarily.*unavailable",
        r"error\s*[45]\d{2}",
        r"page.*not.*found",
        r"access.*denied",
    ]
    
    SECURITY_INDICATORS = [
        "unusual behavior",
        "security check", 
        "cloudflare",
        "ddos protection",
        "rate limit",
        "bot detection",
        "automated traffic",
        "captcha",
        "verify you are human"
    ]
    
    @classmethod
    def detect_security_page(cls, html: str, url: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if the HTML content is a security/protection page.
        
        Returns:
            Tuple of (is_security_page, detected_reason)
        """
        if not html or len(html.strip()) < 100:
            return True, "Empty or minimal content"
        
        html_lower = html.lower()
        
        # Check for security patterns
        for pattern in cls.SECURITY_PATTERNS:
            if re.search(pattern, html_lower, re.IGNORECASE):
                return True, f"Security pattern detected: {pattern}"
        
        # Check for security indicators
        for indicator in cls.SECURITY_INDICATORS:
            if indicator in html_lower:
                return True, f"Security indicator found: {indicator}"
        
        # Check for very short content (often security pages)
        text_content = re.sub(r'<[^>]+>', '', html)
        if len(text_content.strip()) < 500:
            return True, "Suspiciously short content"
        
        # Check for common error status in title/headers
        if re.search(r'<title>[^<]*(?:error|403|404|503|blocked|denied)', html_lower):
            return True, "Error page detected in title"
            
        return False, None
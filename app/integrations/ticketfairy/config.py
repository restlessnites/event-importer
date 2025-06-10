import os
from typing import Optional

# TicketFairy API Configuration
TICKETFAIRY_API_KEY = os.getenv(
    "TICKETFAIRY_API_KEY", 
    "aS5t80tdKb7KzxeQY692sgaK3F6ID7eSknariRtf00ArgPoDtZS14zHurieCdSDl"
)
TICKETFAIRY_API_URL = "https://www.theticketfairy.com/api/draft-events"
TICKETFAIRY_ORIGIN = "https://restlessnites.com"

# Request configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds 
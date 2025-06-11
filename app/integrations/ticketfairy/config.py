import os
import dotenv

dotenv.load_dotenv()

# TicketFairy API Configuration
TICKETFAIRY_API_KEY = os.getenv(
    "TICKETFAIRY_API_KEY"
)

TICKETFAIRY_API_URL = "https://www.theticketfairy.com/api/draft-events"
TICKETFAIRY_ORIGIN = os.getenv("TICKETFAIRY_ORIGIN", "https://restlessnites.com")

# Request configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds 
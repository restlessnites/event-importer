"""Shared HTTP service with session management and consistent error handling."""

import asyncio
import logging
import ssl
import certifi
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import ClientTimeout, ClientSession, ClientResponse

from app.config import get_config, Config
from app.errors import APIError, TimeoutError, RateLimitError, AuthenticationError, handle_errors_async


logger = logging.getLogger(__name__)


class HTTPService:
    """Centralized HTTP client with session management."""

    def __init__(self, config: Config):
        """Initialize HTTP service with configuration."""
        self.config = config
        self._session: Optional[ClientSession] = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> ClientSession:
        """Ensure a session exists, creating one if needed."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    timeout = ClientTimeout(total=self.config.http.timeout)
                    ssl_context = ssl.create_default_context(cafile=certifi.where())
                    connector = aiohttp.TCPConnector(
                        limit=self.config.http.max_connections,
                        limit_per_host=self.config.http.max_keepalive_connections,
                        ssl=ssl_context,
                    )
                    self._session = ClientSession(
                        timeout=timeout,
                        connector=connector,
                        headers={"User-Agent": self.config.http.user_agent},
                    )
                    logger.debug("Created new HTTP session")
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Closed HTTP session")

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    def _handle_response_error(
        self,
        response: ClientResponse,
        service: str,
        error_text: Optional[str] = None,
    ) -> None:
        """Handle HTTP response errors consistently."""
        status = response.status

        # Only raise AuthenticationError for services that require auth
        if status == 401 and service in ["Ticketmaster", "Zyte", "TicketFairy"]:
            raise AuthenticationError(service)
        elif status == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after else None
            raise RateLimitError(service, retry_seconds)
        elif status >= 400:
            message = error_text or f"HTTP {status}"
            raise APIError(service, message, status)

    @asynccontextmanager
    async def _error_handler(self, service: str, url: str):
        """Context manager for consistent error handling."""
        try:
            yield
        except asyncio.TimeoutError:
            logger.error(f"{service} timeout for URL: {url}")
            raise TimeoutError(f"{service} request timed out")
        except aiohttp.ClientError as e:
            logger.error(f"{service} client error for URL {url}: {e}")
            raise APIError(service, str(e))
        except Exception as e:
            logger.error(f"{service} unexpected error for URL {url}: {e}")
            raise

    @handle_errors_async(reraise=True)
    async def head(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> ClientResponse:
        """
        Perform HEAD request with error handling.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            params: Query parameters
            timeout: Override default timeout
            **kwargs: Additional arguments for aiohttp

        Returns:
            The response object

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
        """
        session = await self._ensure_session()

        request_headers = {}
        if headers:
            request_headers.update(headers)

        request_timeout = ClientTimeout(total=timeout or self.config.http.timeout)

        async with self._error_handler(service, url):
            logger.debug(f"{service} HEAD: {url}")

            response = await session.head(
                url,
                headers=request_headers,
                params=params,
                timeout=request_timeout,
                allow_redirects=True,
                **kwargs,
            )

            if response.status >= 400:
                self._handle_response_error(response, service)

            return response

    @handle_errors_async(reraise=True)
    async def get(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> ClientResponse:
        """
        Perform GET request with error handling.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            params: Query parameters
            timeout: Override default timeout
            **kwargs: Additional arguments for aiohttp

        Returns:
            The response object

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
        """
        session = await self._ensure_session()

        request_headers = {}
        if headers:
            request_headers.update(headers)

        request_timeout = ClientTimeout(total=timeout or self.config.http.timeout)

        async with self._error_handler(service, url):
            logger.debug(f"{service} GET: {url}")

            response = await session.get(
                url,
                headers=request_headers,
                params=params,
                timeout=request_timeout,
                **kwargs,
            )

            if response.status >= 400:
                error_text = await response.text()
                self._handle_response_error(response, service, error_text)

            return response

    @handle_errors_async(reraise=True)
    async def post(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> ClientResponse:
        """
        Perform POST request with error handling.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            json: JSON payload
            data: Form data or raw data
            timeout: Override default timeout
            **kwargs: Additional arguments for aiohttp

        Returns:
            The response object

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
        """
        session = await self._ensure_session()

        request_headers = {}
        if headers:
            request_headers.update(headers)

        request_timeout = ClientTimeout(total=timeout or self.config.http.timeout)

        async with self._error_handler(service, url):
            logger.debug(f"{service} POST: {url}")

            response = await session.post(
                url,
                headers=request_headers,
                json=json,
                data=data,
                timeout=request_timeout,
                **kwargs,
            )

            if response.status >= 400:
                error_text = await response.text()
                self._handle_response_error(response, service, error_text)

            return response

    @handle_errors_async(reraise=True)
    async def get_json(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        GET request that returns JSON.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            params: Query parameters
            timeout: Override default timeout
            **kwargs: Additional arguments for get()

        Returns:
            Parsed JSON response
        """
        response = await self.get(
            url,
            service=service,
            headers=headers,
            params=params,
            timeout=timeout,
            **kwargs,
        )
        return await response.json()

    @handle_errors_async(reraise=True)
    async def post_json(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        POST request that returns JSON.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            json: JSON payload
            data: Form data or raw data
            timeout: Override default timeout
            **kwargs: Additional arguments for post()

        Returns:
            Parsed JSON response
        """
        response = await self.post(
            url,
            service=service,
            headers=headers,
            json=json,
            data=data,
            timeout=timeout,
            **kwargs,
        )
        return await response.json()

    @handle_errors_async(reraise=True)
    async def download(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        max_size: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> bytes:
        """
        Download data from URL with size limit.

        Args:
            url: URL to download from
            service: Service name for error messages
            headers: Additional headers
            max_size: Maximum size in bytes
            timeout: Override default timeout
            **kwargs: Additional arguments for aiohttp

        Returns:
            The downloaded data

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
            ValueError: If response exceeds max_size
        """
        response = await self.get(
            url,
            service=service,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

        # Check content length if available
        content_length = response.headers.get("Content-Length")
        if content_length and max_size:
            size = int(content_length)
            if size > max_size:
                raise ValueError(
                    f"Response too large: {size} bytes (max: {max_size} bytes)"
                )

        # Download with size limit
        data = bytearray()
        async for chunk in response.content.iter_chunked(8192):
            data.extend(chunk)
            if max_size and len(data) > max_size:
                raise ValueError(
                    f"Response too large: {len(data)} bytes (max: {max_size} bytes)"
                )

        return bytes(data)

    @handle_errors_async(reraise=True)
    async def stream(
        self,
        url: str,
        *,
        service: str = "HTTP",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream response data.

        Args:
            url: URL to request
            service: Service name for error messages
            headers: Additional headers
            params: Query parameters
            timeout: Override default timeout
            **kwargs: Additional arguments for aiohttp

        Yields:
            Response chunks

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
        """
        response = await self.get(
            url,
            service=service,
            headers=headers,
            params=params,
            timeout=timeout,
            **kwargs,
        )

        async for chunk in response.content.iter_chunked(8192):
            yield chunk


# Global HTTP service instance
_http_service: Optional[HTTPService] = None


def get_http_service() -> HTTPService:
    """Get the global HTTP service instance."""
    global _http_service
    if _http_service is None:
        _http_service = HTTPService(get_config())
    return _http_service


async def close_http_service() -> None:
    """Close the global HTTP service."""
    global _http_service
    if _http_service:
        await _http_service.close()
        _http_service = None

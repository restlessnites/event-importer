"""Shared HTTP service with session management and consistent error handling."""

from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any

import aiohttp
import certifi
from aiohttp import BasicAuth, ClientResponse, ClientSession, ClientTimeout
from typing_extensions import Unpack

from app.config import Config, get_config
from app.errors import (
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    handle_errors_async,
)

logger = logging.getLogger(__name__)


class HTTPService:
    """Centralized HTTP client with session management."""

    def __init__(self: HTTPService, config: Config) -> None:
        """Initialize HTTP service with configuration."""
        self.config = config
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self: HTTPService) -> ClientSession:
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

    async def close(self: HTTPService) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Closed HTTP session")

    async def __aenter__(self: HTTPService) -> HTTPService:
        """Context manager entry."""
        return self

    async def __aexit__(
        self: HTTPService,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        await self.close()

    def _handle_response_error(
        self: HTTPService,
        response: ClientResponse,
        service: str,
        error_text: str | None = None,
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
    async def _error_handler(
        self: HTTPService, service: str, url: str
    ) -> AsyncGenerator[None, None]:
        """Context manager for consistent error handling."""
        try:
            yield
        except asyncio.TimeoutError as e:
            logger.debug(f"{service} timeout for URL: {url}")
            error_msg = f"{service} request timed out"
            raise TimeoutError(error_msg) from e
        except aiohttp.ClientError as e:
            logger.debug(f"{service} client error for URL {url}: {e}")
            raise APIError(service, str(e)) from e
        except Exception as e:
            logger.debug(f"{service} unexpected error for URL {url}: {e}")
            raise

    @handle_errors_async(reraise=True)
    async def head(
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Unpack[dict[str, Any]],
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
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Unpack[dict[str, Any]],
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
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        timeout: float | None = None,
        raise_for_status: bool = True,
        **kwargs: Unpack[dict[str, Any]],
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
            raise_for_status: Whether to raise an exception for non-2xx status codes
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

        # Allow auth to be passed via kwargs and handle it
        auth = kwargs.get("auth")
        if auth and isinstance(auth, tuple):
            kwargs["auth"] = BasicAuth(*auth)

        async with self._error_handler(service, url):
            logger.debug(f"POST to {url} with timeout {request_timeout}s")

            response = await session.post(
                url,
                headers=request_headers,
                json=json,
                data=data,
                timeout=request_timeout,
                **kwargs,
            )

            if raise_for_status and response.status >= 400:
                error_text = await response.text()
                self._handle_response_error(response, service, error_text)

            return response

    @handle_errors_async(reraise=True)
    async def get_json(
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Unpack[dict[str, Any]],
    ) -> dict[str, Any]:
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
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | str | bytes | None = None,
        timeout: float | None = None,
        **kwargs: Unpack[dict[str, Any]],
    ) -> dict[str, Any]:
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
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        max_size: int | None = None,
        timeout: float | None = None,
        verify_ssl: bool = True,
        **kwargs: Unpack[dict[str, Any]],
    ) -> bytes:
        """
        Download binary content from a URL.

        Args:
            url: URL to download from
            service: Service name for error messages
            headers: Additional headers
            max_size: Maximum size in bytes
            timeout: Override default timeout
            verify_ssl: Whether to verify SSL certificate
            **kwargs: Additional arguments for aiohttp

        Returns:
            The downloaded data

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
            ValueError: If response exceeds max_size
        """
        if not headers:
            headers = {"User-Agent": self.config.http.user_agent}

        async with self._error_handler(service, url):
            session = await self._ensure_session()
            async with session.get(
                url,
                headers=headers,
                timeout=timeout or self.config.http.timeout,
                ssl=verify_ssl,
                **kwargs,
            ) as response:
                self._handle_response_error(response, service)

                content_length = response.headers.get("Content-Length")
                if content_length and max_size:
                    size = int(content_length)
                    if size > max_size:
                        error_msg = f"Response too large: {size} bytes (max: {max_size} bytes)"
                        raise ValueError(error_msg)

                # Download with size limit
                data = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    data.extend(chunk)
                    if max_size and len(data) > max_size:
                        error_msg = f"Response too large: {len(data)} bytes (max: {max_size} bytes)"
                        raise ValueError(error_msg)

        return bytes(data)

    @handle_errors_async(reraise=True)
    async def stream(
        self: HTTPService,
        url: str,
        *,
        service: str = "HTTP",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Unpack[dict[str, Any]],
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
_http_service: HTTPService | None = None


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

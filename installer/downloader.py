"""App downloader for installer."""

import hashlib
import stat
from pathlib import Path

import aiohttp
import clicycle
from tenacity import retry, stop_after_attempt, wait_exponential


class AppDownloader:
    """Downloads the Event Importer app."""

    def __init__(self, download_url: str):
        self.download_url = download_url
        self.chunk_size = 8192

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def download(self, destination: Path) -> bool:
        """Download the app with retry logic."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(self.download_url) as response,
        ):
            response.raise_for_status()

            # Get total size for progress bar
            total_size = int(response.headers.get("Content-Length", 0))

            # Download with progress
            temp_path = destination.with_suffix(".tmp")
            downloaded = 0

            with (
                clicycle.progress(
                    total=total_size, description="Downloading Event Importer"
                ) as progress,
                temp_path.open("wb") as file,
            ):
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    file.write(chunk)
                    downloaded += len(chunk)
                    progress.update(len(chunk))

            # Move to final location
            temp_path.rename(destination)

            # Make executable (macOS/Linux)
            destination.chmod(
                destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

            return True

    async def verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum if provided."""
        if not expected_checksum:
            return True

        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        actual = sha256_hash.hexdigest()
        return actual == expected_checksum

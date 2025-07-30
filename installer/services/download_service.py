"""App downloader for installer."""

import hashlib
import shutil
import stat
import subprocess  # noqa: S404
from collections.abc import Callable
from pathlib import Path

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential


class AppDownloader:
    """Downloads the Event Importer app."""

    def __init__(self, download_url: str):
        self.download_url = download_url
        self.chunk_size = 8192

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def download(
        self,
        destination: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> bool:
        """Download the app with retry logic.

        Args:
            destination: Path to download to
            progress_callback: Optional callback(downloaded, total) for progress updates
        """
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        async with (
            aiohttp.ClientSession() as session,
            session.get(self.download_url) as response,
        ):
            response.raise_for_status()

            # Get total size
            total_size = int(response.headers.get("Content-Length", 0))

            # Download to temp file
            is_zip = (
                self.download_url.endswith(".zip") or "dropbox" in self.download_url
            )
            temp_path = destination.with_suffix(".zip.tmp" if is_zip else ".tmp")
            downloaded = 0

            with temp_path.open("wb") as file:
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

            # Handle zip files
            if is_zip:
                self._handle_zip_file(temp_path, destination)
            else:
                # Move to final location
                temp_path.rename(destination)

            # Make executable (macOS/Linux)
            destination.chmod(
                destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

            return True

    def _move_extracted_files(self, source_dir: Path, dest_parent: Path):
        """Move extracted files to destination, overwriting if necessary."""
        for item in source_dir.iterdir():
            target = dest_parent / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))

    def _handle_zip_file(self, temp_path: Path, destination: Path):
        """Extracts a zip file and moves its contents to the destination."""
        temp_extract = destination.parent / "temp_extract"
        if temp_extract.exists():
            shutil.rmtree(temp_extract)

        try:
            # Use system unzip to preserve symlinks
            temp_extract.mkdir(parents=True)
            result = subprocess.run(
                ["unzip", "-o", str(temp_path), "-d", str(temp_extract)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(f"Failed to extract zip: {result.stderr}")

            # Determine the source directory of the app bundle
            extracted_items = list(temp_extract.iterdir())
            source_dir = temp_extract
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]

            # Move contents to the final destination
            self._move_extracted_files(source_dir, destination.parent)
        finally:
            # Clean up temporary extraction directory
            if temp_extract.exists():
                shutil.rmtree(temp_extract)

        # Clean up temporary zip file
        temp_path.unlink()

        # Verify the main binary exists
        if not destination.exists():
            raise FileNotFoundError(
                f"After extraction, could not find {destination}. "
                f"Check that the zip contains the correct app structure."
            )

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

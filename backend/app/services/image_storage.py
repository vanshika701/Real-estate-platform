"""Where uploaded listing images live: Supabase Storage if configured, local disk otherwise."""

import asyncio
from pathlib import Path
from typing import Protocol

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

LOCAL_URL_PREFIX = "/uploads/"


class ImageStorage(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> str:
        """Store the file under `key` and return its public URL."""
        ...

    async def delete(self, url: str) -> None:
        """Remove a previously saved file. Missing files are not an error."""
        ...


class LocalImageStorage:
    """Development fallback: files on disk, served by the app at /uploads."""

    def __init__(self, root: Path) -> None:
        self.root = root

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self.root / key
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return LOCAL_URL_PREFIX + key

    async def delete(self, url: str) -> None:
        if not url.startswith(LOCAL_URL_PREFIX):
            return  # e.g. seeded placeholder URLs we never stored
        path = (self.root / url.removeprefix(LOCAL_URL_PREFIX)).resolve()
        if not path.is_relative_to(self.root.resolve()):
            return  # never follow a URL outside the upload directory
        await asyncio.to_thread(path.unlink, missing_ok=True)


class SupabaseImageStorage:
    """Supabase Storage via its REST API. The bucket must be public for the URLs to load."""

    def __init__(self, base_url: str, service_key: str, bucket: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.bucket = bucket
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}

    def _public_prefix(self) -> str:
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/"

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{key}",
                content=data,
                headers={**self.headers, "Content-Type": content_type},
            )
            response.raise_for_status()
        return self._public_prefix() + key

    async def delete(self, url: str) -> None:
        if not url.startswith(self._public_prefix()):
            return
        key = url.removeprefix(self._public_prefix())
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                "DELETE",
                f"{self.base_url}/storage/v1/object/{self.bucket}",
                json={"prefixes": [key]},
                headers=self.headers,
            )
            response.raise_for_status()


def get_image_storage() -> ImageStorage:
    settings = get_settings()
    if settings.supabase_url and settings.supabase_key:
        return SupabaseImageStorage(
            settings.supabase_url, settings.supabase_key, settings.supabase_bucket
        )
    return LocalImageStorage(Path(settings.upload_dir))

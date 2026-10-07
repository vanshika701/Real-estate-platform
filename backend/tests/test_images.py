from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User
from app.services.image_storage import SupabaseImageStorage
from tests.factories import auth_headers, make_listing, make_user

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 100
GIF = b"GIF89a" + b"\x00" * 100


@pytest.fixture(autouse=True)
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    return tmp_path


async def upload(
    client: AsyncClient,
    listing_id: int,
    user: User,
    data: bytes,
    content_type: str = "image/jpeg",
) -> httpx.Response:
    return await client.post(
        f"/api/v1/listings/{listing_id}/images",
        files={"file": ("photo", data, content_type)},
        headers=auth_headers(user),
    )


@pytest.mark.parametrize(("data", "extension"), [(JPEG, "jpg"), (PNG, "png"), (WEBP, "webp")])
async def test_owner_can_upload_supported_images(
    client: AsyncClient,
    db_session: AsyncSession,
    upload_dir: Path,
    data: bytes,
    extension: str,
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)

    response = await upload(client, listing.id, agent, data)

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith(f"/uploads/listings/{listing.id}/") and url.endswith(f".{extension}")
    assert (upload_dir / url.removeprefix("/uploads/")).read_bytes() == data

    detail = (await client.get(f"/api/v1/listings/{listing.id}")).json()
    assert [img["url"] for img in detail["images"]] == [url]


async def test_images_get_increasing_positions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)

    positions = [(await upload(client, listing.id, agent, JPEG)).json()["position"] for _ in "ab"]

    assert positions == [0, 1]


async def test_file_type_is_checked_from_content_not_header(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)

    # A GIF (and a text file) claiming to be a JPEG.
    for data in (GIF, b"hello, definitely an image"):
        response = await upload(client, listing.id, agent, data, content_type="image/jpeg")
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "unsupported_media_type"


async def test_files_over_5mb_are_rejected(
    client: AsyncClient, db_session: AsyncSession, upload_dir: Path
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)
    too_big = JPEG + b"\x00" * (5 * 1024 * 1024)

    response = await upload(client, listing.id, agent, too_big)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert not any(upload_dir.rglob("*.jpg"))


async def test_exactly_5mb_is_accepted(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)
    exactly_limit = JPEG + b"\x00" * (5 * 1024 * 1024 - len(JPEG))

    response = await upload(client, listing.id, agent, exactly_limit)

    assert response.status_code == 201


async def test_only_owner_can_upload(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    listing = await make_listing(db_session, owner)

    response = await upload(client, listing.id, other, JPEG)

    assert response.status_code == 403


async def test_image_count_is_capped(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_images_per_listing", 2)
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent, image_urls=("http://a", "http://b"))

    response = await upload(client, listing.id, agent, JPEG)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "too_many_images"


async def test_deleting_image_removes_row_and_file(
    client: AsyncClient, db_session: AsyncSession, upload_dir: Path
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)
    image = (await upload(client, listing.id, agent, JPEG)).json()
    path = upload_dir / image["url"].removeprefix("/uploads/")
    assert path.exists()

    response = await client.delete(
        f"/api/v1/listings/{listing.id}/images/{image['id']}", headers=auth_headers(agent)
    )

    assert response.status_code == 204
    assert not path.exists()
    detail = (await client.get(f"/api/v1/listings/{listing.id}")).json()
    assert detail["images"] == []


async def test_deleting_listing_removes_its_files(
    client: AsyncClient, db_session: AsyncSession, upload_dir: Path
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)
    await upload(client, listing.id, agent, JPEG)
    await upload(client, listing.id, agent, PNG)

    await client.delete(f"/api/v1/listings/{listing.id}", headers=auth_headers(agent))

    assert not [p for p in upload_dir.rglob("*") if p.is_file()]


# --- Supabase storage (HTTP mocked) ---------------------------------------------------------


async def test_supabase_storage_uploads_and_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    storage = SupabaseImageStorage("https://proj.supabase.co/", "service-key", "listing-images")

    url = await storage.save("listings/1/a.jpg", JPEG, "image/jpeg")
    await storage.delete(url)

    assert (
        url == "https://proj.supabase.co/storage/v1/object/public/listing-images/listings/1/a.jpg"
    )
    upload_req, delete_req = requests
    assert upload_req.method == "POST"
    assert str(upload_req.url).endswith("/storage/v1/object/listing-images/listings/1/a.jpg")
    assert upload_req.headers["Authorization"] == "Bearer service-key"
    assert upload_req.headers["Content-Type"] == "image/jpeg"
    assert delete_req.method == "DELETE"
    assert delete_req.content == b'{"prefixes":["listings/1/a.jpg"]}'

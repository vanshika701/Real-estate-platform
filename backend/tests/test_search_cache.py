from typing import Any

import pytest
from httpx import AsyncClient, Response
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis, redis_client
from app.main import app
from app.schemas.listings import ListingFilters
from app.services.search_cache import KEY_SET, SearchCache
from tests.factories import auth_headers, listing_payload, make_listing, make_user

URL = "/api/v1/listings"


async def search(client: AsyncClient, **params: Any) -> Response:
    response = await client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return response


async def test_repeat_search_is_served_from_cache(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    await make_listing(db_session, agent)

    first = await search(client, city="Noida")
    second = await search(client, city="Noida")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert first.json() == second.json()


async def test_equivalent_queries_share_a_cache_entry(client: AsyncClient) -> None:
    await search(client, city="Noida", bhk=2)

    # Same filters: different param order, city case, and the default sort made explicit.
    response = await search(client, bhk=2, city="  NOIDA ", sort="newest")

    assert response.headers["X-Cache"] == "HIT"


def test_different_filters_get_different_keys() -> None:
    base = ListingFilters(city="Noida")

    assert SearchCache.key_for(base) != SearchCache.key_for(ListingFilters(city="Pune"))
    assert SearchCache.key_for(base) != SearchCache.key_for(ListingFilters(city="Noida", page=2))


async def test_cache_entries_expire(client: AsyncClient) -> None:
    await search(client, city="Noida")

    key = SearchCache.key_for(ListingFilters(city="Noida"))
    ttl = await redis_client.ttl(key)

    assert 0 < ttl <= get_settings().search_cache_ttl_seconds


async def test_listing_update_invalidates_cached_searches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent, price=8_000_000)
    await search(client)
    await search(client, city="Noida")

    patch = await client.patch(
        f"{URL}/{listing.id}", json={"price": 6_500_000}, headers=auth_headers(agent)
    )
    assert patch.status_code == 200

    after = await search(client)
    assert after.headers["X-Cache"] == "MISS"
    assert after.json()["items"][0]["price"] == 6_500_000
    assert (await search(client, city="Noida")).headers["X-Cache"] == "MISS"
    # The two searches above re-populated the cache; the tracking set holds exactly those keys.
    assert await redis_client.smembers(KEY_SET) == {
        SearchCache.key_for(ListingFilters()),
        SearchCache.key_for(ListingFilters(city="Noida")),
    }


async def test_listing_create_invalidates_cached_searches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    assert (await search(client)).json()["total"] == 0

    await client.post(URL, json=listing_payload(), headers=auth_headers(agent))

    after = await search(client)
    assert after.headers["X-Cache"] == "MISS"
    assert after.json()["total"] == 1


async def test_listing_delete_invalidates_cached_searches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)
    assert (await search(client)).json()["total"] == 1

    await client.delete(f"{URL}/{listing.id}", headers=auth_headers(agent))

    assert (await search(client)).json()["total"] == 0


async def test_cache_disabled_never_serves_hits(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "cache_enabled", False)

    await search(client)
    response = await search(client)

    assert response.headers["X-Cache"] == "MISS"
    assert await redis_client.dbsize() == 0


class _BrokenRedis:
    """Every Redis call fails, as if the server were down."""

    def __getattr__(self, name: str) -> Any:
        def fail(*args: Any, **kwargs: Any) -> Any:
            raise RedisConnectionError("redis is down")

        return fail


async def test_search_still_works_when_redis_is_down(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    await make_listing(db_session, agent)
    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()

    response = await search(client)

    assert response.json()["total"] == 1
    assert response.headers["X-Cache"] == "MISS"

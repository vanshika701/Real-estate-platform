from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ListingStatus, PropertyType, UserRole
from tests.factories import auth_headers, listing_payload, make_listing, make_user

URL = "/api/v1/listings"


async def search(client: AsyncClient, **params: Any) -> dict[str, Any]:
    response = await client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(page: dict[str, Any]) -> list[int]:
    return [item["id"] for item in page["items"]]


# --- search: filters ------------------------------------------------------------------------


async def test_search_returns_only_active_listings(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    active = await make_listing(db_session, agent)
    await make_listing(db_session, agent, status=ListingStatus.SOLD)
    await make_listing(db_session, agent, status=ListingStatus.INACTIVE)

    page = await search(client)

    assert ids(page) == [active.id]
    assert page["total"] == 1


async def test_city_filter_is_case_insensitive(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    noida = await make_listing(db_session, agent, city="Noida")
    await make_listing(db_session, agent, city="Greater Noida")
    await make_listing(db_session, agent, city="Pune")

    assert ids(await search(client, city="nOiDa")) == [noida.id]


async def test_price_range_is_inclusive(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    cheap = await make_listing(db_session, agent, price=4_000_000)
    mid = await make_listing(db_session, agent, price=6_000_000)
    pricey = await make_listing(db_session, agent, price=9_000_000)

    assert set(ids(await search(client, min_price=6_000_000))) == {mid.id, pricey.id}
    assert set(ids(await search(client, max_price=6_000_000))) == {cheap.id, mid.id}
    assert ids(await search(client, min_price=5_000_000, max_price=7_000_000)) == [mid.id]


async def test_bhk_and_property_type_filters(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    two_bhk_flat = await make_listing(db_session, agent, bhk=2)
    await make_listing(db_session, agent, bhk=3)
    villa = await make_listing(db_session, agent, bhk=3, property_type=PropertyType.VILLA)

    assert ids(await search(client, bhk=2)) == [two_bhk_flat.id]
    assert ids(await search(client, property_type="villa")) == [villa.id]
    assert ids(await search(client, bhk=3, property_type="villa")) == [villa.id]


async def test_filters_combine(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    match = await make_listing(db_session, agent, city="Pune", bhk=2, price=7_000_000)
    await make_listing(db_session, agent, city="Pune", bhk=2, price=12_000_000)
    await make_listing(db_session, agent, city="Pune", bhk=3, price=7_000_000)
    await make_listing(db_session, agent, city="Noida", bhk=2, price=7_000_000)

    page = await search(client, city="pune", bhk=2, max_price=10_000_000)

    assert ids(page) == [match.id]


@pytest.mark.parametrize(
    "params",
    [
        {"min_price": 9_000_000, "max_price": 1_000_000},
        {"page_size": 51},
        {"page": 0},
        {"min_price": -1},
        {"sort": "cheapest"},
        {"property_type": "castle"},
    ],
)
async def test_invalid_search_params_are_rejected(
    client: AsyncClient, params: dict[str, Any]
) -> None:
    response = await client.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# --- search: sorting & pagination -----------------------------------------------------------


async def test_sorting(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    old_mid = await make_listing(db_session, agent, price=5_000_000, age_days=10)
    new_high = await make_listing(db_session, agent, price=9_000_000, age_days=1)
    mid_low = await make_listing(db_session, agent, price=2_000_000, age_days=5)

    assert ids(await search(client, sort="price_asc")) == [mid_low.id, old_mid.id, new_high.id]
    assert ids(await search(client, sort="price_desc")) == [new_high.id, old_mid.id, mid_low.id]
    assert ids(await search(client, sort="newest")) == [new_high.id, mid_low.id, old_mid.id]
    assert ids(await search(client)) == ids(await search(client, sort="newest"))  # default


async def test_pagination_reports_total_and_slices_results(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    created = [await make_listing(db_session, agent, price=1_000_000 * (i + 1)) for i in range(5)]
    expected_order = [listing.id for listing in created]

    page1 = await search(client, sort="price_asc", page=1, page_size=2)
    page3 = await search(client, sort="price_asc", page=3, page_size=2)
    beyond = await search(client, sort="price_asc", page=4, page_size=2)

    assert (page1["total"], page1["page"], page1["page_size"]) == (5, 1, 2)
    assert ids(page1) == expected_order[:2]
    assert ids(page3) == expected_order[4:]
    assert beyond["items"] == [] and beyond["total"] == 5


async def test_ties_have_stable_order_across_pages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    for _ in range(6):
        await make_listing(db_session, agent, price=5_000_000)

    seen = [
        *ids(await search(client, sort="price_asc", page=1, page_size=3)),
        *ids(await search(client, sort="price_asc", page=2, page_size=3)),
    ]

    assert len(set(seen)) == 6  # no listing repeated or skipped


async def test_summary_includes_first_image_as_cover(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    await make_listing(db_session, agent, image_urls=("http://img/first", "http://img/second"))
    await make_listing(db_session, agent)

    items = (await search(client, sort="newest"))["items"]

    assert items[0]["cover_image_url"] is None
    assert items[1]["cover_image_url"] == "http://img/first"


# --- detail ---------------------------------------------------------------------------------


async def test_detail_includes_images_and_agent_contact(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent, image_urls=("http://a", "http://b"))

    response = await client.get(f"{URL}/{listing.id}")

    assert response.status_code == 200
    body = response.json()
    assert [img["url"] for img in body["images"]] == ["http://a", "http://b"]
    assert body["agent"] == {
        "id": agent.id,
        "full_name": agent.full_name,
        "email": agent.email,
        "phone": agent.phone,
    }


async def test_detail_404_uses_error_shape(client: AsyncClient) -> None:
    response = await client.get(f"{URL}/9999")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Listing not found"}}


# --- create ---------------------------------------------------------------------------------


async def test_agent_can_create_listing(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)

    response = await client.post(URL, json=listing_payload(), headers=auth_headers(agent))

    assert response.status_code == 201
    body = response.json()
    assert body["agent_id"] == agent.id
    assert body["status"] == "active"
    assert body["images"] == []
    assert ids(await search(client)) == [body["id"]]


async def test_buyer_cannot_create_listing(client: AsyncClient, db_session: AsyncSession) -> None:
    buyer = await make_user(db_session, UserRole.BUYER)

    response = await client.post(URL, json=listing_payload(), headers=auth_headers(buyer))

    assert response.status_code == 403


async def test_anonymous_cannot_create_listing(client: AsyncClient) -> None:
    response = await client.post(URL, json=listing_payload())

    assert response.status_code == 401


@pytest.mark.parametrize(
    "override",
    [
        {"price": 0},
        {"latitude": 91},
        {"title": "    "},
        {"property_type": "castle"},
        {"bhk": -1},
    ],
)
async def test_create_validates_input(
    client: AsyncClient, db_session: AsyncSession, override: dict[str, Any]
) -> None:
    agent = await make_user(db_session)

    response = await client.post(URL, json=listing_payload(**override), headers=auth_headers(agent))

    assert response.status_code == 422


# --- update ---------------------------------------------------------------------------------


async def test_owner_can_partially_update(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent, price=8_000_000, title="Original title")

    response = await client.patch(
        f"{URL}/{listing.id}",
        json={"price": 7_500_000, "status": "sold"},
        headers=auth_headers(agent),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 7_500_000
    assert body["status"] == "sold"
    assert body["title"] == "Original title"  # untouched
    assert body["updated_at"] >= body["created_at"]


async def test_agent_cannot_update_another_agents_listing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    listing = await make_listing(db_session, owner, price=8_000_000)

    response = await client.patch(
        f"{URL}/{listing.id}", json={"price": 1}, headers=auth_headers(other)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    detail = (await client.get(f"{URL}/{listing.id}")).json()
    assert detail["price"] == 8_000_000


async def test_update_rejects_null_for_required_field(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent)

    response = await client.patch(
        f"{URL}/{listing.id}", json={"price": None}, headers=auth_headers(agent)
    )

    assert response.status_code == 422
    assert "price" in response.json()["error"]["message"]


async def test_update_missing_listing_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)

    response = await client.patch(f"{URL}/9999", json={"bhk": 2}, headers=auth_headers(agent))

    assert response.status_code == 404


# --- delete ---------------------------------------------------------------------------------


async def test_owner_can_delete(client: AsyncClient, db_session: AsyncSession) -> None:
    agent = await make_user(db_session)
    listing = await make_listing(db_session, agent, image_urls=("http://img",))

    response = await client.delete(f"{URL}/{listing.id}", headers=auth_headers(agent))

    assert response.status_code == 204
    assert (await client.get(f"{URL}/{listing.id}")).status_code == 404


async def test_agent_cannot_delete_another_agents_listing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    listing = await make_listing(db_session, owner)

    response = await client.delete(f"{URL}/{listing.id}", headers=auth_headers(other))

    assert response.status_code == 403
    assert (await client.get(f"{URL}/{listing.id}")).status_code == 200


# --- agent's own listings -------------------------------------------------------------------


async def test_agent_listings_shows_own_listings_in_every_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent = await make_user(db_session)
    other = await make_user(db_session)
    active = await make_listing(db_session, agent, age_days=2)
    sold = await make_listing(db_session, agent, status=ListingStatus.SOLD, age_days=1)
    await make_listing(db_session, other)

    response = await client.get("/api/v1/agent/listings", headers=auth_headers(agent))

    assert response.status_code == 200
    assert ids(response.json()) == [sold.id, active.id]


async def test_agent_listings_requires_agent_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    buyer = await make_user(db_session, UserRole.BUYER)

    response = await client.get("/api/v1/agent/listings", headers=auth_headers(buyer))

    assert response.status_code == 403

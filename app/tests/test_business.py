import logging
from urllib.parse import urlparse

import httpx
import pytest

from .constants import StaticData

endpoint = "/api/v1/apps/saas/businesses/"


@pytest.mark.asyncio
async def test_business_list_empty(client: httpx.AsyncClient, auth_headers_business):
    # list businesses empty
    response = await client.get(f"{endpoint}", headers=auth_headers_business)

    resp_json = response.json()
    logging.info(f"business_list: {resp_json}")
    assert response.status_code == 200
    assert type(resp_json.get("items")) == list
    assert len(resp_json.get("items")) == 0


@pytest.mark.asyncio
async def test_business_create(client: httpx.AsyncClient, auth_headers_business):
    # create business
    domain = urlparse(str(client.base_url)).netloc
    data = dict(
        name=StaticData.business_name_1,
        domain=domain,
        uid=str(StaticData.business_id_1),
    )
    response = await client.post(
        f"{endpoint}", headers=auth_headers_business, json=data
    )

    resp_json = response.json()
    assert response.status_code == 201
    assert resp_json["name"] == data["name"]
    assert resp_json["domain"] == data["domain"]
    assert resp_json["uid"] != data["uid"]


@pytest.mark.asyncio
async def test_business_list_with_business(
    client: httpx.AsyncClient, auth_headers_business
):
    # list business
    response = await client.get(f"{endpoint}", headers=auth_headers_business)

    resp_json = response.json()
    logging.info(f"business_list: {resp_json}")
    assert response.status_code == 200
    assert type(resp_json.get("items")) == list
    assert len(resp_json.get("items")) > 0
    business = resp_json["items"][0]
    business_id = business.get("uid")
    StaticData.business_id_1 = business_id


@pytest.mark.asyncio
async def test_business_retrieve_no_auth(
    client: httpx.AsyncClient, auth_headers_business
):
    # retrieve business without access token
    response = await client.get(f"{endpoint}{StaticData.business_id_1}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_business_retrieve_not_found(
    client: httpx.AsyncClient, auth_headers_business
):
    # retrieve business not found
    response = await client.get(
        f"{endpoint}{StaticData.business_id_2}", headers=auth_headers_business
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_business_retrieve(client: httpx.AsyncClient, auth_headers_business):
    # retrieve business
    response = await client.get(
        f"{endpoint}{StaticData.business_id_1}", headers=auth_headers_business
    )
    resp_json = response.json()
    logging.info(f"business_retrieve: {resp_json}")
    assert response.status_code == 200
    assert resp_json["uid"] == StaticData.business_id_1


@pytest.mark.asyncio
async def test_business_update(client: httpx.AsyncClient, auth_headers_business):
    # update business
    data = dict(meta_data={"key": "value"})
    response = await client.patch(
        f"{endpoint}{StaticData.business_id_1}",
        headers=auth_headers_business,
        json=data,
    )

    resp_json = response.json()
    logging.info(f"business_update: {resp_json}")
    assert response.status_code == 200
    assert resp_json["uid"] == StaticData.business_id_1
    assert resp_json["meta_data"] == data["meta_data"]

    # retrieve business after update
    response = await client.get(
        f"{endpoint}{StaticData.business_id_1}", headers=auth_headers_business
    )
    resp_json = response.json()
    logging.info(f"business_retrieve: {resp_json}")
    assert response.status_code == 200
    assert resp_json["uid"] == StaticData.business_id_1
    assert resp_json["meta_data"] == data["meta_data"]

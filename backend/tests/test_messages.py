"""
Messages API Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_messages(async_client: AsyncClient):
    """Test get messages endpoint"""
    response = await async_client.get("/api/messages")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_pending_messages(async_client: AsyncClient):
    """Test get pending messages endpoint"""
    response = await async_client.get("/api/messages/pending")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data


@pytest.mark.asyncio
async def test_get_message_not_found(async_client: AsyncClient):
    """Test get non-existent message returns 404"""
    response = await async_client.get("/api/messages/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_pagination(async_client: AsyncClient):
    """Test messages pagination with limit/offset"""
    response = await async_client.get("/api/messages?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "total" in data
    assert isinstance(data["messages"], list)

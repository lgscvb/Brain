"""
Settings API Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings(async_client: AsyncClient):
    """Test get settings endpoint"""
    response = await async_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "AI_PROVIDER" in data
    assert "AUTO_REPLY_MODE" in data


@pytest.mark.asyncio
async def test_verify_password_correct(async_client: AsyncClient):
    """Test password verification with correct password"""
    response = await async_client.post(
        "/api/settings/verify-password",
        json={"password": "test123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True


@pytest.mark.asyncio
async def test_verify_password_incorrect(async_client: AsyncClient):
    """Test password verification with incorrect password"""
    response = await async_client.post(
        "/api/settings/verify-password",
        json={"password": "wrong"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_webhook_url(async_client: AsyncClient):
    """Test get webhook URL endpoint"""
    response = await async_client.get("/api/settings/webhook-url")
    assert response.status_code == 200
    data = response.json()
    assert "webhook_url" in data


@pytest.mark.asyncio
async def test_get_models(async_client: AsyncClient):
    """Test get available models endpoint"""
    response = await async_client.get("/api/settings/models")
    assert response.status_code == 200
    data = response.json()
    assert "openrouter" in data or "anthropic_direct" in data


@pytest.mark.asyncio
async def test_update_settings_without_auth(async_client: AsyncClient):
    """Test update settings without auth fails"""
    response = await async_client.post(
        "/api/settings",
        json={"AUTO_REPLY_MODE": False}
    )
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_update_settings_with_auth(async_client: AsyncClient, admin_headers):
    """Test update settings with auth succeeds"""
    response = await async_client.post(
        "/api/settings",
        json={"AUTO_REPLY_MODE": False},
        headers=admin_headers
    )
    assert response.status_code == 200

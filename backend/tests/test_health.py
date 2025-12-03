"""
Health API Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health endpoint returns 200"""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_health_simple(async_client: AsyncClient):
    """Test simple health check"""
    response = await async_client.get("/api/health/simple")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_version(async_client: AsyncClient):
    """Test version endpoint"""
    response = await async_client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data


@pytest.mark.asyncio
async def test_root(async_client: AsyncClient):
    """Test root endpoint"""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Brain API"
    assert data["status"] == "running"

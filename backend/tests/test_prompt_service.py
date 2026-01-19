"""
Brain - Prompt Service 測試

【測試範圍】
1. Prompt 版本 CRUD 操作
2. 版本啟用/回滾
3. 降級機制（DB 無資料時使用預設值）
4. API 端點整合測試
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.prompt_service import PromptService, get_prompt_service, DEFAULT_PROMPTS


# ============================================================
# Unit Tests - PromptService
# ============================================================

class TestPromptServiceDefaultPrompts:
    """測試預設 Prompt 降級機制"""

    def test_get_default_prompt_returns_security_rules(self):
        """測試取得安全規則預設值"""
        service = PromptService()
        result = service.get_default_prompt("security_rules")
        assert "安全規則" in result
        assert "禁止洩露" in result

    def test_get_default_prompt_returns_router_prompt(self):
        """測試取得 Router Prompt 預設值"""
        service = PromptService()
        result = service.get_default_prompt("router_prompt")
        assert "任務分派" in result
        assert "SIMPLE" in result
        assert "COMPLEX" in result

    def test_get_default_prompt_returns_draft_prompt(self):
        """測試取得 Draft Prompt 預設值"""
        service = PromptService()
        result = service.get_default_prompt("draft_prompt")
        assert "Hour Jungle" in result
        assert "客服助理" in result

    def test_get_default_prompt_returns_empty_for_unknown_key(self):
        """測試未知 key 回傳空字串"""
        service = PromptService()
        result = service.get_default_prompt("unknown_key")
        assert result == ""

    def test_default_prompts_dict_has_all_keys(self):
        """測試 DEFAULT_PROMPTS 包含所有必要的 key"""
        required_keys = [
            "security_rules",
            "router_prompt",
            "draft_prompt",
            "draft_prompt_fallback",
            "modification_analysis_prompt"
        ]
        for key in required_keys:
            assert key in DEFAULT_PROMPTS


class TestPromptServiceGetActivePrompt:
    """測試取得活躍 Prompt"""

    @pytest.mark.anyio
    async def test_returns_default_when_no_active_version(self):
        """測試無活躍版本時回傳預設值"""
        service = PromptService()

        # Mock DB session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_active_prompt(mock_db, "router_prompt")

        # 應該回傳預設值
        assert "任務分派" in result

    @pytest.mark.anyio
    async def test_returns_db_content_when_active_version_exists(self):
        """測試有活躍版本時回傳 DB 內容"""
        service = PromptService()

        # Mock DB session 和 PromptVersion
        mock_version = MagicMock()
        mock_version.content = "這是自訂的 Prompt 內容"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        mock_db.execute.return_value = mock_result

        result = await service.get_active_prompt(mock_db, "router_prompt")

        assert result == "這是自訂的 Prompt 內容"

    @pytest.mark.anyio
    async def test_returns_default_on_db_error(self):
        """測試 DB 錯誤時降級到預設值"""
        service = PromptService()

        # Mock DB session 拋出錯誤
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB connection error")

        result = await service.get_active_prompt(mock_db, "router_prompt")

        # 應該回傳預設值，不是拋出錯誤
        assert "任務分派" in result


class TestPromptServiceCreateVersion:
    """測試建立新版本"""

    @pytest.mark.anyio
    async def test_creates_version_with_next_version_number(self):
        """測試建立新版本時版本號遞增"""
        service = PromptService()

        # Mock DB - 使用 MagicMock 配合 AsyncMock
        mock_db = MagicMock()

        # Mock 查詢最大版本號回傳 2
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 2
        mock_db.execute = AsyncMock(return_value=mock_max_result)

        # Mock commit 和 refresh 為 async
        mock_db.commit = AsyncMock()

        # Mock refresh - 修改傳入的物件
        async def mock_refresh(obj):
            obj.id = 123
            obj.version = 3
            obj.created_at = MagicMock(isoformat=MagicMock(return_value="2024-01-19T10:00:00"))

        mock_db.refresh = mock_refresh

        result = await service.create_version(
            db=mock_db,
            prompt_key="draft_prompt",
            content="新內容",
            description="v3 改進"
        )

        # 驗證 add 被呼叫
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result["version"] == 3

    @pytest.mark.anyio
    async def test_creates_first_version_when_none_exists(self):
        """測試無版本時建立 v1"""
        service = PromptService()

        # Mock DB
        mock_db = MagicMock()

        # Mock 查詢最大版本號回傳 None
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_max_result)

        mock_db.commit = AsyncMock()

        # Mock refresh
        async def mock_refresh(obj):
            obj.id = 1
            obj.version = 1
            obj.created_at = MagicMock(isoformat=MagicMock(return_value="2024-01-19T10:00:00"))

        mock_db.refresh = mock_refresh

        result = await service.create_version(
            db=mock_db,
            prompt_key="new_prompt",
            content="全新內容"
        )

        mock_db.add.assert_called_once()
        assert result["version"] == 1


class TestPromptServiceActivateVersion:
    """測試啟用版本"""

    @pytest.mark.anyio
    async def test_returns_false_when_version_not_found(self):
        """測試版本不存在時回傳 False"""
        service = PromptService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.activate_version(mock_db, "draft_prompt", 999)

        assert result is False

    @pytest.mark.anyio
    async def test_deactivates_other_versions_and_activates_target(self):
        """測試啟用版本時停用其他版本"""
        service = PromptService()

        # Mock target version
        mock_version = MagicMock()
        mock_version.is_active = False

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        mock_db.execute.return_value = mock_result

        result = await service.activate_version(mock_db, "draft_prompt", 2)

        assert result is True
        assert mock_version.is_active is True
        mock_db.commit.assert_called_once()


class TestPromptServiceRollback:
    """測試回滾功能"""

    @pytest.mark.anyio
    async def test_rollback_calls_activate_version(self):
        """測試 rollback 等同於 activate_version"""
        service = PromptService()

        # Mock activate_version
        service.activate_version = AsyncMock(return_value=True)

        result = await service.rollback(MagicMock(), "draft_prompt", 1)

        service.activate_version.assert_called_once()
        assert result is True


class TestPromptServiceDeleteVersion:
    """測試刪除版本"""

    @pytest.mark.anyio
    async def test_cannot_delete_active_version(self):
        """測試不能刪除活躍版本"""
        service = PromptService()

        mock_version = MagicMock()
        mock_version.is_active = True
        mock_version.version = 2

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="不能刪除活躍版本"):
            await service.delete_version(mock_db, "draft_prompt", 2)

    @pytest.mark.anyio
    async def test_cannot_delete_v1(self):
        """測試不能刪除 v1"""
        service = PromptService()

        mock_version = MagicMock()
        mock_version.is_active = False
        mock_version.version = 1

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="不能刪除初始版本"):
            await service.delete_version(mock_db, "draft_prompt", 1)

    @pytest.mark.anyio
    async def test_returns_false_when_version_not_found(self):
        """測試版本不存在時回傳 False"""
        service = PromptService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_version(mock_db, "draft_prompt", 999)

        assert result is False


class TestGetPromptServiceSingleton:
    """測試單例模式"""

    def test_returns_same_instance(self):
        """測試回傳相同實例"""
        # 重置全域變數
        import services.prompt_service as module
        module._prompt_service = None

        service1 = get_prompt_service()
        service2 = get_prompt_service()

        assert service1 is service2


# ============================================================
# Integration Tests - API Endpoints
# ============================================================

class TestPromptAPIEndpoints:
    """測試 Prompt API 端點"""

    @pytest.mark.anyio
    async def test_list_prompts_returns_empty_list_initially(self, async_client):
        """測試初始狀態回傳空列表"""
        response = await async_client.get("/api/prompts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.anyio
    async def test_get_prompt_detail_returns_404_for_nonexistent(self, async_client):
        """測試查詢不存在的 Prompt 回傳 404"""
        response = await async_client.get("/api/prompts/nonexistent_key")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_create_and_get_prompt_version(self, async_client):
        """測試建立並查詢 Prompt 版本"""
        # 建立新版本
        create_response = await async_client.post(
            "/api/prompts/test_prompt",
            json={
                "content": "測試 Prompt 內容",
                "description": "v1 測試版本"
            }
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["version"] == 1
        assert created["is_active"] is False

        # 查詢版本
        get_response = await async_client.get("/api/prompts/test_prompt")
        assert get_response.status_code == 200
        detail = get_response.json()
        assert detail["prompt_key"] == "test_prompt"
        assert len(detail["versions"]) == 1
        assert detail["active_version"] is None  # 尚未啟用

    @pytest.mark.anyio
    async def test_activate_and_rollback_version(self, async_client):
        """測試啟用和回滾版本"""
        # 建立兩個版本
        await async_client.post(
            "/api/prompts/activate_test",
            json={"content": "v1 內容", "description": "v1"}
        )
        await async_client.post(
            "/api/prompts/activate_test",
            json={"content": "v2 內容", "description": "v2"}
        )

        # 啟用 v1
        activate_response = await async_client.put(
            "/api/prompts/activate_test/activate/1"
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["activated_version"] == 1

        # 確認 v1 是活躍版本
        detail = await async_client.get("/api/prompts/activate_test")
        assert detail.json()["active_version"]["version"] == 1

        # 回滾到 v2（其實是啟用 v2）
        rollback_response = await async_client.put(
            "/api/prompts/activate_test/rollback/2"
        )
        assert rollback_response.status_code == 200

        # 確認 v2 現在是活躍版本
        detail = await async_client.get("/api/prompts/activate_test")
        assert detail.json()["active_version"]["version"] == 2

    @pytest.mark.anyio
    async def test_get_active_content_fallback(self, async_client):
        """測試取得活躍內容（含降級）"""
        # 查詢不存在的 Prompt，應該回傳 is_default=True
        response = await async_client.get("/api/prompts/nonexistent/active-content")
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True
        assert data["content"] == ""  # 未知 key 回傳空字串

    @pytest.mark.anyio
    async def test_delete_version_restrictions(self, async_client):
        """測試刪除版本的限制"""
        # 建立並啟用版本
        await async_client.post(
            "/api/prompts/delete_test",
            json={"content": "v1", "description": "v1"}
        )
        await async_client.put("/api/prompts/delete_test/activate/1")

        # 嘗試刪除活躍版本，應該失敗
        delete_response = await async_client.delete(
            "/api/prompts/delete_test/version/1"
        )
        assert delete_response.status_code == 400
        assert "不能刪除" in delete_response.json()["detail"]

    @pytest.mark.anyio
    async def test_compare_versions(self, async_client):
        """測試版本比較"""
        # 建立兩個版本
        await async_client.post(
            "/api/prompts/compare_test",
            json={"content": "版本 1 內容", "description": "v1"}
        )
        await async_client.post(
            "/api/prompts/compare_test",
            json={"content": "版本 2 內容", "description": "v2"}
        )

        # 比較兩個版本
        compare_response = await async_client.get(
            "/api/prompts/compare_test/compare?version_a=1&version_b=2"
        )
        assert compare_response.status_code == 200
        data = compare_response.json()
        assert data["version_a"]["content"] == "版本 1 內容"
        assert data["version_b"]["content"] == "版本 2 內容"

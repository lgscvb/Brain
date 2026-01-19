"""
Brain - API 用量與成本計算測試
測試 AI API 的用量追蹤和成本估算功能
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from api.routes.usage import calculate_cost, log_api_usage, PRICING


# ============================================================
# 純函數測試：calculate_cost
# ============================================================

class TestCalculateCost:
    """測試成本計算函數"""

    def test_claude_sonnet_pricing(self):
        """
        測試 Claude Sonnet 定價

        【定價資訊】
        Claude 3.5 Sonnet: $3/MTok (input), $15/MTok (output)
        PRICING 表中存的是「美分/百萬 token」：300 美分 = $3

        【計算範例】
        1000 input tokens + 500 output tokens
        input_cost = (1000 / 1_000_000) * 300 = 0.3 美分
        output_cost = (500 / 1_000_000) * 1500 = 0.75 美分
        total = 1.05 美分
        result = int(1.05 * 100) = 105（單位：0.01 美分）
        """
        result = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500
        )

        # 預期結果（0.01美分為單位）
        # input: (1000/1M) * 300 = 0.3 美分 = 30 (0.01美分)
        # output: (500/1M) * 1500 = 0.75 美分 = 75 (0.01美分)
        # total: 105 (0.01美分)
        assert result == 105

    def test_gemini_flash_pricing(self):
        """
        測試 Gemini Flash 定價（便宜模型）

        【定價資訊】
        Gemini Flash 1.5: $0.075/MTok (input), $0.30/MTok (output)
        比 Claude 便宜約 40 倍！

        【計算範例】
        10000 input + 5000 output
        input_cost = (10000 / 1M) * 7.5 = 0.075 美分
        output_cost = (5000 / 1M) * 30 = 0.15 美分
        total = 0.225 美分 = 22.5 → 22 (0.01美分)
        """
        result = calculate_cost(
            model="google/gemini-flash-1.5",
            input_tokens=10000,
            output_tokens=5000
        )

        # input: (10000/1M) * 7.5 = 0.075 美分 = 7.5 (0.01美分)
        # output: (5000/1M) * 30 = 0.15 美分 = 15 (0.01美分)
        # total: 22.5 → 22
        assert result == 22

    def test_unknown_model_uses_default_pricing(self):
        """
        測試未知模型使用預設定價

        【為什麼重要】
        新模型發布時可能還沒更新 PRICING 表，
        系統應該使用保守的預設價格（Claude Sonnet 等級）。
        """
        result = calculate_cost(
            model="some-future-unknown-model",
            input_tokens=1000,
            output_tokens=500
        )

        # 應該使用 default 定價
        default = PRICING["default"]
        expected_input = (1000 / 1_000_000) * default["input"]
        expected_output = (500 / 1_000_000) * default["output"]
        expected = int((expected_input + expected_output) * 100)

        assert result == expected

    def test_zero_tokens_returns_zero(self):
        """測試零 token 返回零成本"""
        result = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=0,
            output_tokens=0
        )
        assert result == 0

    def test_large_token_count(self):
        """
        測試大量 token 計算

        【情境】
        處理長文檔時可能有數十萬 token
        確保計算不會溢出或出錯
        """
        result = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=100000,  # 10 萬 input
            output_tokens=50000   # 5 萬 output
        )

        # input: (100000/1M) * 300 = 30 美分 = 3000 (0.01美分)
        # output: (50000/1M) * 1500 = 75 美分 = 7500 (0.01美分)
        # total: 10500
        assert result == 10500

    def test_openrouter_model_variants(self):
        """
        測試 OpenRouter 模型命名

        【背景】
        OpenRouter 使用 "provider/model" 格式命名
        例如 "anthropic/claude-3.5-sonnet"
        """
        # OpenRouter Claude
        result1 = calculate_cost(
            model="anthropic/claude-sonnet-4.5",
            input_tokens=1000,
            output_tokens=500
        )

        # 直連 Claude（應該相同價格）
        result2 = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500
        )

        assert result1 == result2

    def test_haiku_cheaper_than_sonnet(self):
        """
        測試 Haiku 比 Sonnet 便宜

        【定價對比】
        Haiku: $1/$5 per MTok
        Sonnet: $3/$15 per MTok
        Haiku 應該便宜約 3 倍
        """
        tokens = (10000, 5000)

        haiku_cost = calculate_cost(
            model="claude-3-5-haiku-20241022",
            input_tokens=tokens[0],
            output_tokens=tokens[1]
        )

        sonnet_cost = calculate_cost(
            model="claude-3-5-sonnet-20241022",
            input_tokens=tokens[0],
            output_tokens=tokens[1]
        )

        # Haiku 應該更便宜
        assert haiku_cost < sonnet_cost
        # 大約是 3 倍差距
        assert sonnet_cost / haiku_cost > 2.5

    @pytest.mark.parametrize("model,expected_input,expected_output", [
        ("claude-3-5-sonnet-20241022", 300, 1500),
        ("google/gemini-flash-1.5", 7.5, 30),
        ("meta-llama/llama-3.1-8b-instruct", 5, 5),
        ("deepseek/deepseek-chat", 14, 28),
    ])
    def test_pricing_table_values(self, model, expected_input, expected_output):
        """
        參數化測試：驗證 PRICING 表的值

        【為什麼用參數化】
        同一個測試邏輯，不同的輸入值
        如果定價表更新了，測試會自動檢查
        """
        pricing = PRICING.get(model)
        assert pricing is not None, f"模型 {model} 不在 PRICING 表中"
        assert pricing["input"] == expected_input
        assert pricing["output"] == expected_output


# ============================================================
# 資料庫相關測試：log_api_usage
# ============================================================

class TestLogApiUsage:
    """測試 API 用量記錄功能"""

    @pytest.mark.asyncio
    async def test_creates_usage_record(self, async_client):
        """
        測試建立用量記錄

        【流程】
        1. 呼叫 log_api_usage
        2. 檢查返回的 APIUsage 物件
        3. 驗證欄位正確
        """
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            usage = await log_api_usage(
                db=db,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                operation="draft_generation",
                input_tokens=1000,
                output_tokens=500,
                success=True
            )

            # 驗證返回物件
            assert usage.id is not None
            assert usage.provider == "anthropic"
            assert usage.model == "claude-3-5-sonnet-20241022"
            assert usage.operation == "draft_generation"
            assert usage.input_tokens == 1000
            assert usage.output_tokens == 500
            assert usage.total_tokens == 1500
            assert usage.success is True
            assert usage.error_message is None

    @pytest.mark.asyncio
    async def test_calculates_cost_correctly(self, async_client):
        """測試成本計算正確"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            usage = await log_api_usage(
                db=db,
                provider="openrouter",
                model="google/gemini-flash-1.5",
                operation="routing",
                input_tokens=500,
                output_tokens=100,
                success=True
            )

            # 手動計算預期成本
            expected_cost = calculate_cost(
                model="google/gemini-flash-1.5",
                input_tokens=500,
                output_tokens=100
            )

            assert usage.estimated_cost == expected_cost

    @pytest.mark.asyncio
    async def test_records_error(self, async_client):
        """測試記錄錯誤"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            usage = await log_api_usage(
                db=db,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                operation="draft_generation",
                input_tokens=1000,
                output_tokens=0,  # API 錯誤，沒有 output
                success=False,
                error_message="Rate limit exceeded"
            )

            assert usage.success is False
            assert usage.error_message == "Rate limit exceeded"
            assert usage.output_tokens == 0


# ============================================================
# API 端點測試
# ============================================================

class TestUsageStatsEndpoint:
    """測試 /usage/stats 端點"""

    @pytest.mark.asyncio
    async def test_returns_stats_structure(self, async_client: AsyncClient):
        """測試返回正確的統計結構"""
        response = await async_client.get("/api/usage/stats")

        assert response.status_code == 200
        data = response.json()

        # 驗證結構
        assert "period_days" in data
        assert "total" in data
        assert "today" in data
        assert "daily" in data
        assert "by_operation" in data

        # 驗證 total 結構
        total = data["total"]
        assert "input_tokens" in total
        assert "output_tokens" in total
        assert "total_tokens" in total
        assert "estimated_cost_usd" in total
        assert "api_calls" in total
        assert "errors" in total

    @pytest.mark.asyncio
    async def test_stats_with_custom_days(self, async_client: AsyncClient):
        """測試自訂天數參數"""
        response = await async_client.get("/api/usage/stats?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7

    @pytest.mark.asyncio
    async def test_stats_with_data(self, async_client: AsyncClient):
        """測試有資料時的統計"""
        from tests.conftest import TestSessionLocal

        # 先建立一些測試資料
        async with TestSessionLocal() as db:
            await log_api_usage(
                db=db,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                operation="test_operation",
                input_tokens=1000,
                output_tokens=500,
                success=True
            )

        # 查詢統計
        response = await async_client.get("/api/usage/stats")
        assert response.status_code == 200

        data = response.json()
        # 應該有至少 1 筆記錄
        assert data["total"]["api_calls"] >= 1


class TestRecentUsageEndpoint:
    """測試 /usage/recent 端點"""

    @pytest.mark.asyncio
    async def test_returns_recent_records(self, async_client: AsyncClient):
        """測試返回最近記錄"""
        response = await async_client.get("/api/usage/recent")

        assert response.status_code == 200
        data = response.json()
        assert "records" in data

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, async_client: AsyncClient):
        """測試 limit 參數"""
        from tests.conftest import TestSessionLocal

        # 建立多筆資料
        async with TestSessionLocal() as db:
            for i in range(10):
                await log_api_usage(
                    db=db,
                    provider="test",
                    model="test-model",
                    operation=f"test_{i}",
                    input_tokens=100,
                    output_tokens=50,
                    success=True
                )

        # 只取 5 筆
        response = await async_client.get("/api/usage/recent?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["records"]) <= 5


class TestErrorLogsEndpoint:
    """測試 /usage/errors 端點"""

    @pytest.mark.asyncio
    async def test_returns_errors_only(self, async_client: AsyncClient):
        """測試只返回錯誤記錄"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 建立成功記錄
            await log_api_usage(
                db=db,
                provider="test",
                model="test-model",
                operation="success_op",
                input_tokens=100,
                output_tokens=50,
                success=True
            )

            # 建立錯誤記錄
            await log_api_usage(
                db=db,
                provider="test",
                model="test-model",
                operation="failed_op",
                input_tokens=100,
                output_tokens=0,
                success=False,
                error_message="Test error"
            )

        response = await async_client.get("/api/usage/errors")
        assert response.status_code == 200

        data = response.json()
        # 只應該有錯誤記錄
        for error in data["errors"]:
            # 每條記錄都應該有 error_message
            assert error.get("error_message") is not None or error.get("operation") == "failed_op"


# ============================================================
# 整合測試
# ============================================================

class TestUsageIntegration:
    """用量追蹤整合測試"""

    @pytest.mark.asyncio
    async def test_full_usage_flow(self, async_client: AsyncClient):
        """
        測試完整的用量追蹤流程

        【流程】
        1. 記錄 API 呼叫
        2. 查詢統計
        3. 查詢最近記錄
        4. 驗證數據一致
        """
        from tests.conftest import TestSessionLocal

        # 1. 記錄 API 呼叫
        async with TestSessionLocal() as db:
            usage = await log_api_usage(
                db=db,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                operation="integration_test",
                input_tokens=2000,
                output_tokens=1000,
                success=True
            )
            recorded_id = usage.id

        # 2. 查詢最近記錄
        response = await async_client.get("/api/usage/recent?limit=1")
        assert response.status_code == 200

        records = response.json()["records"]
        if records:
            # 最近的記錄應該是我們剛建立的
            latest = records[0]
            assert latest["operation"] == "integration_test"
            assert latest["input_tokens"] == 2000
            assert latest["output_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self, async_client: AsyncClient):
        """
        測試成本追蹤準確性

        【情境】
        記錄多筆不同模型的呼叫，驗證總成本計算正確
        """
        from tests.conftest import TestSessionLocal

        expected_total_cost = 0

        async with TestSessionLocal() as db:
            # Claude Sonnet 呼叫
            usage1 = await log_api_usage(
                db=db,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                operation="test1",
                input_tokens=1000,
                output_tokens=500,
                success=True
            )
            expected_total_cost += usage1.estimated_cost

            # Gemini Flash 呼叫
            usage2 = await log_api_usage(
                db=db,
                provider="openrouter",
                model="google/gemini-flash-1.5",
                operation="test2",
                input_tokens=5000,
                output_tokens=2000,
                success=True
            )
            expected_total_cost += usage2.estimated_cost

        # 查詢統計
        response = await async_client.get("/api/usage/stats")
        data = response.json()

        # 驗證總成本（允許小誤差，因為可能有其他測試的資料）
        # estimated_cost 單位是 0.01 美分，需要轉換
        # total.estimated_cost_usd 是美元
        reported_cost_in_units = data["total"]["estimated_cost_usd"] * 10000

        # 至少應該包含我們記錄的成本
        assert reported_cost_in_units >= expected_total_cost

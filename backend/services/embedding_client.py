"""
Brain - Embedding 客戶端
使用 OpenRouter API 生成向量嵌入（相容 OpenAI SDK）
支援 OpenAI text-embedding-3-small 等模型
"""
from typing import List, Optional
from openai import AsyncOpenAI
from config import settings


class EmbeddingClient:
    """OpenRouter Embedding 客戶端（使用 OpenAI SDK）"""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self):
        """初始化 Embedding 客戶端"""
        self.client = None
        # OpenRouter 需要加上 provider 前綴
        self.model = f"openai/{settings.EMBEDDING_MODEL}"

        # 優先使用 OpenRouter，備用 OpenAI 直連
        if settings.OPENROUTER_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=self.OPENROUTER_BASE_URL
            )
            print(f"✅ Embedding 使用 OpenRouter (model: {self.model})")
        elif settings.OPENAI_API_KEY:
            # 備用：直接使用 OpenAI
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.EMBEDDING_MODEL  # OpenAI 不需要 provider 前綴
            print(f"✅ Embedding 使用 OpenAI 直連 (model: {self.model})")
        else:
            print("⚠️ 警告：未設定 OPENROUTER_API_KEY 或 OPENAI_API_KEY，Embedding 功能將無法使用")

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        生成單個文本的 Embedding

        Args:
            text: 要嵌入的文本

        Returns:
            1536 維的向量列表，如果失敗返回 None
        """
        if not self.client:
            print("❌ Embedding 客戶端未初始化")
            return None

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Embedding 生成失敗: {e}")
            return None

    async def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批次生成多個文本的 Embedding

        Args:
            texts: 要嵌入的文本列表

        Returns:
            向量列表的列表
        """
        if not self.client:
            print("❌ Embedding 客戶端未初始化")
            return [None] * len(texts)

        try:
            # OpenRouter/OpenAI 支援批次請求
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            # 按索引排序結果
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            print(f"❌ 批次 Embedding 生成失敗: {e}")
            return [None] * len(texts)

    def is_available(self) -> bool:
        """檢查 Embedding 服務是否可用"""
        return self.client is not None


# 全域 Embedding 客戶端實例
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """取得 Embedding 客戶端單例"""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client

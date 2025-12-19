"""
新增 CRM 流程知識到 RAG 資料庫
"""
import asyncio
import sys
sys.path.insert(0, '/Users/daihaoting_1/Desktop/code/brain/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import KnowledgeChunk

# 資料庫連線
DATABASE_URL = "sqlite+aiosqlite:///brain.db"

# 新增的知識內容
NEW_KNOWLEDGE = [
    # === 合約流程 ===
    {
        "category": "process",
        "sub_category": "contract_workflow",
        "content": "報價單轉合約流程：1. 客戶確認報價單內容 2. 點選「轉合約」3. 重新填寫完整承租人資訊（公司名稱、負責人、地址、身分證、統編、電話、Email）4. 確認租賃條件（金額、期限、分館）5. 產生合約 PDF",
        "service_type": "contract"
    },
    {
        "category": "process",
        "sub_category": "contract_workflow",
        "content": "合約資訊欄位說明：公司名稱（新設立可能還沒確定）、負責人姓名（自然人）、負責人地址（戶籍地址）、身分證號（外國人用居留證）、公司統編（可為空，新設立公司可能延後提供）、聯絡電話、E-MAIL",
        "service_type": "contract"
    },
    {
        "category": "process",
        "sub_category": "contract_workflow",
        "content": "同一客戶可能有多張合約，對應不同公司或服務項目。例如：王小明（個人）同時有「王草有限公司」和「綠伏特科技」兩張合約，每張合約獨立儲存公司資訊",
        "service_type": "contract"
    },

    # === 續約流程 ===
    {
        "category": "process",
        "sub_category": "renewal",
        "content": "續約流程：舊合約標記為「已續約」狀態，然後建立新合約。新合約可能調整價格或條件。續約不是延長原合約期限，而是建立全新的合約",
        "service_type": "contract"
    },
    {
        "category": "process",
        "sub_category": "renewal",
        "content": "續約進度管理包含四個階段：1. 已通知（renewal_notified）2. 客戶確認續約意願（renewal_confirmed）3. 已繳費（renewal_paid）4. 已簽約（renewal_signed）",
        "service_type": "contract"
    },

    # === 繳費狀態 ===
    {
        "category": "service_info",
        "sub_category": "payment_status",
        "content": "繳費狀態說明：pending（待繳）- 帳單已產生等待繳費；paid（已繳）- 已收到款項；overdue（逾期）- 超過繳費期限未繳；waived（免收）- 因特殊原因免收此筆費用，不計入營收統計",
        "service_type": "payment"
    },
    {
        "category": "process",
        "sub_category": "payment",
        "content": "繳費週期選項：月繳（monthly）、季繳（quarterly，每3個月）、半年繳（semi_annual，每6個月）、年繳（annual，每12個月）、兩年繳（biennial，每24個月）",
        "service_type": "payment"
    },
    {
        "category": "process",
        "sub_category": "payment",
        "content": "押金處理：押金在簽約時收取，退租時返還（扣除任何損壞或欠款）。押金金額通常等於一個月租金或依合約條款約定",
        "service_type": "payment"
    },

    # === 統編相關 ===
    {
        "category": "process",
        "sub_category": "tax_id",
        "content": "新設立公司的統編處理：公司設立需要 7-14 天，設立完成後才會有統一編號。可以先簽約（統編欄位留空），等公司設立完成後再補上統編並重新產生合約 PDF",
        "service_type": "contract"
    },
    {
        "category": "process",
        "sub_category": "tax_id",
        "content": "統一編號格式：8 位數字，用於開立三聯式發票和報稅。如果客戶說「三聯 12345678」，12345678 就是統編",
        "service_type": "invoice"
    },

    # === 分館資訊 ===
    {
        "category": "service_info",
        "sub_category": "branch",
        "content": "Hour Jungle 分館：1. 台中西區大忠（大忠南街55號7F-5）- 法人：光域國際顧問有限公司 2. 台中西區英才（暫定）",
        "service_type": "general"
    },

    # === 服務類型 ===
    {
        "category": "service_info",
        "sub_category": "service_type",
        "content": "服務類型：virtual_office（登記地址 / 虛擬辦公室）、private_office（獨立辦公室）、flex_seat（彈性座位 / 共享辦公桌）、meeting_room（會議室）、shared_space（共享空間）、mailbox（郵件代收）",
        "service_type": "general"
    },
    {
        "category": "service_info",
        "sub_category": "pricing",
        "content": "基本價格參考：登記地址 $3,000/月起、共享辦公桌 $5,000/月起、獨立辦公室 $12,000/月起、會議室 $380/小時起。實際價格需依客戶需求報價",
        "service_type": "general"
    },

    # === CRM 整合 ===
    {
        "category": "service_info",
        "sub_category": "crm_integration",
        "content": "Brain AI 可以查詢的 CRM 資料：客戶基本資料（姓名、電話、Email、公司名稱）、合約資訊（合約編號、類型、金額、期限、狀態）、繳費狀態（待繳金額、逾期金額）。如果客戶有 LINE 綁定，可以自動識別",
        "service_type": "general"
    },

    # === 會議室預約（更新） ===
    {
        "category": "service_info",
        "sub_category": "meeting_room",
        "content": "會議室預約時段：09:00 ~ 18:00，每 30 分鐘為一個時段。非會員需先付款，收到款項後人工完成預約",
        "service_type": "meeting_room"
    },
]


async def main():
    """匯入知識到資料庫"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        added = 0
        for item in NEW_KNOWLEDGE:
            chunk = KnowledgeChunk(
                content=item["content"],
                category=item["category"],
                sub_category=item.get("sub_category"),
                service_type=item.get("service_type"),
                is_active=True,
                extra_data={}
            )
            session.add(chunk)
            added += 1

        await session.commit()
        print(f"✅ 成功新增 {added} 筆知識")


if __name__ == "__main__":
    asyncio.run(main())

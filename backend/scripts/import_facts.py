"""
匯入 hourjungle_facts.md 到知識庫
"""
import httpx
import asyncio

BRAIN_API = "https://brain.yourspce.org/api"

# 知識條目列表
FACTS = [
    {
        "content": """【Hour Jungle 基本資訊】
地址：台中市西區大忠南街55號7樓之5
電話：04-23760282
一樓大門管制密碼：705
Google Maps：https://maps.app.goo.gl/CiYeSsWHZAYQPPrJA
附近停車場：https://www.google.com.tw/maps/search/停車/@24.1406914,120.6528429,16.78z
官網：https://www.hourjungle.com/
營業時間：週一至週五 09:00~18:00，國定假日休息""",
        "category": "fact_sheet",
        "sub_category": "基本資訊",
        "service_type": "general"
    },
    {
        "content": """【共享空間（開放座位/自由座）價格】
- 時租：$80
- 日租：$350
- 月租：$3,000（不用綁年約，月繳月使用）
- 營業時間：週一至週五 09:00~18:00
- 照片：https://drive.google.com/drive/folders/1KHIjOILKQ1OzUoWozjQhXqXv8SiSWlHE""",
        "category": "fact_sheet",
        "sub_category": "空間服務",
        "service_type": "coworking"
    },
    {
        "content": """【獨立辦公室價格】
E辦公室特色：
- 有對外窗、採光通風良好
- 可容6~10人
- 獨立冷氣、自由進出、可自由佈置
- 備有簡單辦公桌椅

價格：
- 年約原價：$18,000/月
- 優惠價：$15,000/月
- 押金：$15,000
- 照片：https://drive.google.com/drive/folders/1oRLXO272fblufH5m-I7OA9pglUeYTx42""",
        "category": "fact_sheet",
        "sub_category": "空間服務",
        "service_type": "private_office"
    },
    {
        "content": """【會議室租借價格】
平日（週一至週五 09:00~18:00）：
- 費用：$380/小時（含稅）
- 人數：8~10人內
- 需提前預約

假日（週六、週日）：
- 費用：$1,650/3小時（含稅），最低起租3小時
- 人數：8~10人內
- 需提前預約
- 照片：https://drive.google.com/drive/folders/1N1NhEJW6nSOI1_BRNeJj5L37OZayt5Xr""",
        "category": "fact_sheet",
        "sub_category": "空間服務",
        "service_type": "meeting_room"
    },
    {
        "content": """【活動場地租借價格】
- 時間：僅限假日（週六 09:00~18:00）
- 費用：$3,600/3小時（含稅）
- 人數：1~30人內
- 需提前預約
- 平日不提供場地外借
- 照片：https://drive.google.com/drive/folders/1GUTK0px_1xgNddB1B3De_AfG6ieb_sHB""",
        "category": "fact_sheet",
        "sub_category": "空間服務",
        "service_type": "event_space"
    },
    {
        "content": """【共用設施】
- 櫃檯代收發信件服務
- 廚房設備：微波爐、冰熱飲水機、冰箱、現煮咖啡、茶包（均可免費使用）
- 會議室空間（採預約制）""",
        "category": "fact_sheet",
        "sub_category": "空間服務",
        "service_type": "facilities"
    },
    {
        "content": """【營業登記（借址登記）價格】
方案價格：
- 兩年合約：$1,490/月（半年繳）
- 一年合約：$1,800/月（年繳）
- 押金：$6,000

服務優勢：
1. 超過百間蝦皮店家登記指定選擇
2. 全台唯一合約內註明：如因我方因素主管機關不予核准，全額退費
3. 可登記使用免用統一發票（限無店面零售業）
4. 獨家蝦皮商城免費健檢，提供金流、物流、包材、BSMI、財稅法一站式解決方案
5. 贈送一年免費稅務諮詢
6. 勞動部 TTQS 認證單位，不定期超過百種創業課程會員免費獨享""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "virtual_office"
    },
    {
        "content": """【營業登記諮詢需確認事項】
在報價前，必須先確認以下資訊：
1. 新設立還是遷址？（已有統編請提供）
2. 從事什麼行業？
3. 目前平均營業額？
4. 會使用統一發票嗎？
5. 預計登記公司還是行號？（新設立適用）""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "virtual_office"
    },
    {
        "content": """【新設立登記代辦費用】
代辦收費：
- 公司登記：$15,000（年營業額400萬以上及特許另報價）
- 行號登記：$8,000

需要資料：
1. 三個中英文名稱並排序
2. 預計要登記營業項目
3. 負責人身分證正反面
4. 預計要登記的資本額""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "company_setup"
    },
    {
        "content": """【變更登記代辦】
可代辦項目：
- 營業地址變更
- 變更負責人
- 變更股東
- 變更營業項目

流程：
1. 經濟部變更登記（含跨縣市遷址、章程變更）
2. 國稅局營業登記地址變更
3. 全程資料準備、文件送件與進度追蹤

所需文件：
1. 負責人身分證影本
2. 公司大小章
3. 公司變更登記表

時程：整個流程約 3~4 週完成""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "company_change"
    },
    {
        "content": """【公司/行號遷址代辦費用】
代辦費用：
- 台中市內：$6,600
- 外縣市：$8,000

諮詢需確認事項：
1. 統編
2. 有使用統一發票嗎？
3. 公司型態（行號/有限公司）
4. 產業類別
5. 預計何時遷址

小建議：跨縣市遷址建議請找代辦""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "relocation"
    },
    {
        "content": """【會計帳服務費用】
- 費用：$2,000/月（收14個月）
- 年度總計：$28,000""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "accounting"
    },
    {
        "content": """【拿信服務】
- 服務時間：上班日下午 13:00~18:00
- 需提前預約""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "mail_pickup"
    },
    {
        "content": """【續約資訊】
續約方案：
- 兩年合約：$1,800/月，半年繳（原$1,490/月）
- 一年合約：$2,000/月，年繳（原$1,800/月）

續約方式：
- 線上續約：提供 PDF 合約，列印簽名後回傳
- 臨櫃續約：至 Hour Jungle 台中館簽署合約

不續約注意事項：
- 需於合約到期日前辦理公司或行號遷出
- 需至國稅局及經濟部完成遷出登記
- 提供遷出證明後辦理押金退還""",
        "category": "fact_sheet",
        "sub_category": "登記服務",
        "service_type": "renewal"
    },
    {
        "content": """【常用營業項目代碼 - 零售業】
- F399040 無店面零售業
- F203010 食品什貨飲料零售業
- F204110 布疋衣著鞋帽傘服飾品零售業
- F206020 日常用品零售業
- F201010 農產品零售業
- F201070 花卉零售業
- F201990 其他農畜水產品零售業
- F205040 家具寢具廚房器具裝設品零售業
- F206010 五金零售業
- F206050 寵物食品及其用品零售業
- F208040 化粧品零售業
- F207030 清潔用品零售業
- F209060 文教樂器育樂用品零售業
- F210010 鐘錶零售業
- F210020 眼鏡零售業
- F214030 汽機車零件配備零售業
- F213030 電腦及事務性機器設備零售業
- F299990 其他零售業
- F399990 其他綜合零售業""",
        "category": "fact_sheet",
        "sub_category": "營業項目代碼",
        "service_type": "business_codes"
    },
    {
        "content": """【常用營業項目代碼 - 服務業】
- I103060 管理顧問業
- I401010 一般廣告服務業
- I199990 其他顧問服務業
- I301010 資訊軟體服務業
- I301020 資料處理服務業
- IZ99990 其他工商服務業
- ZZ99999 除許可業務外，得經營法令非禁止或限制之業務""",
        "category": "fact_sheet",
        "sub_category": "營業項目代碼",
        "service_type": "business_codes"
    },
    {
        "content": """【特別注意事項】
- 有貓咪在場，如賓客怕貓請提前告知
- 開立電子發票，可開統編報帳""",
        "category": "fact_sheet",
        "sub_category": "注意事項",
        "service_type": "general"
    }
]


async def import_facts():
    """匯入所有事實到知識庫"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BRAIN_API}/knowledge/bulk-import",
            json=FACTS
        )

        if response.status_code == 200:
            result = response.json()
            print(f"匯入成功！共匯入 {result['imported']} 條知識")
            if result.get('errors'):
                print(f"錯誤：{result['errors']}")
        else:
            print(f"匯入失敗：{response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(import_facts())

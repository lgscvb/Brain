import { BookOpen, Zap, Users, BarChart, Settings as SettingsIcon } from 'lucide-react'

export default function GuidePage() {
    const steps = [
        {
            title: '1. 設定 API Keys',
            icon: SettingsIcon,
            description: '前往「系統設定」頁面設定您的 Claude API Key 和 LINE 憑證',
            details: [
                '取得 Anthropic API Key: https://console.anthropic.com/',
                '取得 LINE Messaging API 憑證: https://developers.line.biz/console/',
                '設定完成後需要重啟伺服器'
            ]
        },
        {
            title: '2. 配置 LINE Webhook',
            icon: Zap,
            description: '設定 LINE Webhook URL 以接收訊息',
            details: [
                '本地開發: 使用 ngrok 建立公開 URL',
                '執行: ngrok http 8787',
                '在 LINE Console 設定 Webhook URL: <ngrok-url>/webhook/line',
                '啟用 Webhook 並測試連接'
            ]
        },
        {
            title: '3. 開始使用',
            icon: Users,
            description: '系統將自動處理 LINE 訊息並生成回覆草稿',
            details: [
                '客戶透過 LINE 發送訊息',
                'AI 自動分析並生成回覆草稿',
                '人工審核並編輯草稿',
                '發送回覆並記錄學習資料'
            ]
        },
        {
            title: '4. 監控與優化',
            icon: BarChart,
            description: '透過儀表板監控系統效能並持續優化',
            details: [
                '查看待處理訊息數量',
                '追蹤 AI 草稿採用率',
                '分析人工修改模式',
                '持續改善 AI 回覆品質'
            ]
        }
    ]

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl mb-4">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white">使用說明</h2>
                <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                    快速開始使用 Brain AI 輔助客服系統
                </p>
            </div>

            {/* Quick Start Steps */}
            <div className="grid gap-6">
                {steps.map((step, index) => {
                    const Icon = step.icon
                    return (
                        <div
                            key={index}
                            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
                        >
                            <div className="flex items-start space-x-4">
                                <div className="flex-shrink-0">
                                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                                        <Icon className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                                        {step.title}
                                    </h3>
                                    <p className="text-gray-600 dark:text-gray-400 mb-3">
                                        {step.description}
                                    </p>
                                    <ul className="space-y-2">
                                        {step.details.map((detail, detailIndex) => (
                                            <li key={detailIndex} className="flex items-start space-x-2 text-sm text-gray-500 dark:text-gray-400">
                                                <span className="text-blue-500 mt-1">•</span>
                                                <span>{detail}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* System Features */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-8 border border-blue-200 dark:border-blue-800">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">系統特色</h3>
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-lg">🤖</span>
                        </div>
                        <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">AI 自動草稿生成</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">使用 Claude AI 自動生成專業回覆草稿</p>
                        </div>
                    </div>

                    <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-lg">✓</span>
                        </div>
                        <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">人工審核機制</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">所有回覆經人工審核，確保品質</p>
                        </div>
                    </div>

                    <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-lg">📊</span>
                        </div>
                        <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">SPIN 銷售框架</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">整合專業銷售方法論，提升轉換率</p>
                        </div>
                    </div>

                    <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-lg">📈</span>
                        </div>
                        <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">持續學習優化</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">分析修改模式，不斷改善 AI 表現</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Support Links */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">需要協助？</h3>
                <div className="space-y-3">
                    <a href="https://github.com/lgscvb/Brain" target="_blank" rel="noopener noreferrer" className="flex items-center space-x-3 text-blue-600 dark:text-blue-400 hover:underline">
                        <span>📚</span>
                        <span>查看完整文件</span>
                    </a>
                    <a href="https://github.com/lgscvb/Brain/issues" target="_blank" rel="noopener noreferrer" className="flex items-center space-x-3 text-blue-600 dark:text-blue-400 hover:underline">
                        <span>🐛</span>
                        <span>回報問題</span>
                    </a>
                    <a href="https://docs.anthropic.com/" target="_blank" rel="noopener noreferrer" className="flex items-center space-x-3 text-blue-600 dark:text-blue-400 hover:underline">
                        <span>🤖</span>
                        <span>Claude API 文件</span>
                    </a>
                    <a href="https://developers.line.biz/en/docs/messaging-api/" target="_blank" rel="noopener noreferrer" className="flex items-center space-x-3 text-blue-600 dark:text-blue-400 hover:underline">
                        <span>💬</span>
                        <span>LINE Messaging API 文件</span>
                    </a>
                </div>
            </div>
        </div>
    )
}

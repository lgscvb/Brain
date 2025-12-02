import { useState, useEffect } from 'react'
import { Save, Key, RefreshCw, AlertCircle, CheckCircle, ExternalLink, Zap } from 'lucide-react'
import axios from 'axios'

export default function SettingsPage() {
    const [settings, setSettings] = useState({
        ANTHROPIC_API_KEY: '',
        CLAUDE_MODEL: 'claude-sonnet-4-5',
        ENABLE_EXTENDED_THINKING: false,
        THINKING_BUDGET_TOKENS: 10000,
        LINE_CHANNEL_ACCESS_TOKEN: '',
        LINE_CHANNEL_SECRET: '',
        AUTO_REPLY_MODE: false,
    })

    const [status, setStatus] = useState({
        ANTHROPIC_API_KEY_SET: false,
        LINE_CHANNEL_ACCESS_TOKEN_SET: false,
        LINE_CHANNEL_SECRET_SET: false,
        AUTO_REPLY_MODE: false,
    })

    const [webhookInfo, setWebhookInfo] = useState(null)
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)

    useEffect(() => {
        fetchSettings()
        fetchWebhookInfo()
    }, [])

    const fetchSettings = async () => {
        try {
            const response = await axios.get('/api/settings')
            setStatus(response.data)
            // 同步自動回覆模式和模型選擇到 settings
            setSettings(prev => ({
                ...prev,
                AUTO_REPLY_MODE: response.data.AUTO_REPLY_MODE,
                CLAUDE_MODEL: response.data.CLAUDE_MODEL || 'claude-sonnet-4-5',
                ENABLE_EXTENDED_THINKING: response.data.ENABLE_EXTENDED_THINKING || false,
                THINKING_BUDGET_TOKENS: response.data.THINKING_BUDGET_TOKENS || 10000
            }))
        } catch (error) {
            console.error('獲取設定失敗:', error)
        }
    }

    const fetchWebhookInfo = async () => {
        try {
            const response = await axios.get('/api/settings/webhook-url')
            setWebhookInfo(response.data)
        } catch (error) {
            console.error('獲取 webhook 資訊失敗:', error)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setMessage(null)

        try {
            const response = await axios.post('/api/settings', settings)
            setMessage({ type: 'success', text: response.data.message })
            await fetchSettings()

            // 清空輸入欄位
            setSettings({
                ANTHROPIC_API_KEY: '',
                LINE_CHANNEL_ACCESS_TOKEN: '',
                LINE_CHANNEL_SECRET: '',
            })
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.response?.data?.detail || '更新失敗'
            })
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }))
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white">系統設定</h2>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                    配置 API Keys 和 LINE Webhook 設定
                </p>
            </div>

            {/* Alert Message */}
            {message && (
                <div className={`p-4 rounded-lg flex items-start space-x-3 ${message.type === 'success'
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
                    }`}>
                    {message.type === 'success' ? (
                        <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    ) : (
                        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                        <p className="font-medium">{message.text}</p>
                        {message.type === 'success' && (
                            <p className="text-sm mt-1">請重新啟動伺服器以套用新設定</p>
                        )}
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Claude API Section */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <Key className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Claude API</h3>
                        </div>
                        {status.ANTHROPIC_API_KEY_SET && (
                            <span className="px-3 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 text-xs font-medium rounded-full">
                                ✓ 已設定
                            </span>
                        )}
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Anthropic API Key
                            </label>
                            <input
                                type="password"
                                value={settings.ANTHROPIC_API_KEY}
                                onChange={(e) => handleChange('ANTHROPIC_API_KEY', e.target.value)}
                                placeholder={status.ANTHROPIC_API_KEY_SET ? '••••••••••••' : 'sk-ant-...'}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                從 <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center">
                                    Anthropic Console <ExternalLink className="w-3 h-3 ml-1" />
                                </a> 取得您的 API Key
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Claude 模型
                            </label>
                            <select
                                value={settings.CLAUDE_MODEL}
                                onChange={(e) => handleChange('CLAUDE_MODEL', e.target.value)}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                                <optgroup label="Claude 4.5 系列（最新）">
                                    <option value="claude-sonnet-4-5">Claude Sonnet 4.5（推薦，平衡）</option>
                                    <option value="claude-opus-4-5">Claude Opus 4.5（最強，較貴）</option>
                                    <option value="claude-haiku-4-5">Claude Haiku 4.5（快速經濟）</option>
                                </optgroup>
                                <optgroup label="Claude 3.5 系列（舊版）">
                                    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (2024/10)</option>
                                    <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet (2024/06)</option>
                                </optgroup>
                                <optgroup label="Claude 3 系列">
                                    <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                                    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                                    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                                </optgroup>
                            </select>
                            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                選擇不同的 Claude 模型，影響 AI 回覆品質、速度和成本
                            </p>
                        </div>

                        {/* Extended Thinking 設定 */}
                        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                            <label className="flex items-center justify-between cursor-pointer">
                                <div>
                                    <div className="flex items-center space-x-2">
                                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                            Extended Thinking（延伸思考）
                                        </span>
                                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 text-xs font-medium rounded">
                                            進階
                                        </span>
                                    </div>
                                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                        啟用後 AI 會進行更深入的思考，提升複雜問題的回覆品質
                                    </p>
                                </div>
                                <div className="relative inline-block w-12 h-6 transition duration-200 ease-in-out rounded-full">
                                    <input
                                        type="checkbox"
                                        checked={settings.ENABLE_EXTENDED_THINKING}
                                        onChange={(e) => handleChange('ENABLE_EXTENDED_THINKING', e.target.checked)}
                                        className="sr-only peer"
                                    />
                                    <div className={`absolute inset-0 rounded-full transition-colors duration-200 ${settings.ENABLE_EXTENDED_THINKING ? 'bg-purple-600' : 'bg-gray-300 dark:bg-gray-600'}`}></div>
                                    <div className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${settings.ENABLE_EXTENDED_THINKING ? 'transform translate-x-6' : ''}`}></div>
                                </div>
                            </label>

                            {settings.ENABLE_EXTENDED_THINKING && (
                                <div className="mt-4 pl-4 border-l-2 border-purple-500">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Thinking Token 預算
                                    </label>
                                    <input
                                        type="number"
                                        min="1000"
                                        max="100000"
                                        step="1000"
                                        value={settings.THINKING_BUDGET_TOKENS}
                                        onChange={(e) => handleChange('THINKING_BUDGET_TOKENS', parseInt(e.target.value) || 10000)}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                        💡 建議：10,000 tokens（提升品質但增加成本和時間）
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* LINE Configuration Section */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-6 h-6 bg-green-500 rounded flex items-center justify-center">
                                <span className="text-white text-xs font-bold">L</span>
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">LINE Messaging API</h3>
                        </div>
                        {status.LINE_CHANNEL_ACCESS_TOKEN_SET && status.LINE_CHANNEL_SECRET_SET && (
                            <span className="px-3 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 text-xs font-medium rounded-full">
                                ✓ 已設定
                            </span>
                        )}
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Channel Access Token
                            </label>
                            <input
                                type="password"
                                value={settings.LINE_CHANNEL_ACCESS_TOKEN}
                                onChange={(e) => handleChange('LINE_CHANNEL_ACCESS_TOKEN', e.target.value)}
                                placeholder={status.LINE_CHANNEL_ACCESS_TOKEN_SET ? '••••••••••••' : '輸入 LINE Channel Access Token'}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Channel Secret
                            </label>
                            <input
                                type="password"
                                value={settings.LINE_CHANNEL_SECRET}
                                onChange={(e) => handleChange('LINE_CHANNEL_SECRET', e.target.value)}
                                placeholder={status.LINE_CHANNEL_SECRET_SET ? '••••••••••••' : '輸入 LINE Channel Secret'}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>

                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            從 <a href="https://developers.line.biz/console/" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center">
                                LINE Developers Console <ExternalLink className="w-3 h-3 ml-1" />
                            </a> 取得您的 Token 和 Secret
                        </p>
                    </div>
                </div>

                {/* Auto Reply Mode Section */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <Zap className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">自動回覆模式</h3>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings.AUTO_REPLY_MODE}
                                onChange={(e) => handleChange('AUTO_REPLY_MODE', e.target.checked)}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                            <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-300">
                                {settings.AUTO_REPLY_MODE ? '開啟' : '關閉'}
                            </span>
                        </label>
                    </div>

                    <div className="mt-4 space-y-3">
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            {settings.AUTO_REPLY_MODE ? (
                                <span className="flex items-start space-x-2">
                                    <span className="text-green-600 dark:text-green-400">✓</span>
                                    <span><strong>自動模式已啟用：</strong>收到訊息後，系統會自動生成草稿並立即發送給客戶，無需人工審核。適合忙碌時段或半夜使用。</span>
                                </span>
                            ) : (
                                <span className="flex items-start space-x-2">
                                    <span className="text-blue-600 dark:text-blue-400">ℹ</span>
                                    <span><strong>手動模式已啟用：</strong>收到訊息後，系統會生成草稿供您審核，需手動選擇並發送。適合需要精準控制回覆內容的情況。</span>
                                </span>
                            )}
                        </p>

                        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                            <p className="text-xs text-yellow-800 dark:text-yellow-200">
                                <strong>提示：</strong>切換模式後請點擊「儲存設定」並重啟伺服器才會生效。
                            </p>
                        </div>
                    </div>
                </div>

                {/* Webhook URL Section */}
                {webhookInfo && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
                            LINE Webhook URL 設定
                        </h3>

                        {webhookInfo.is_local ? (
                            <div>
                                <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                                    {webhookInfo.message}
                                </p>
                                <ol className="list-decimal list-inside space-y-2 text-sm text-blue-700 dark:text-blue-300">
                                    {webhookInfo.instructions.map((instruction, index) => (
                                        <li key={index}>{instruction}</li>
                                    ))}
                                </ol>
                            </div>
                        ) : (
                            <div>
                                <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                                    請將以下 URL 設定到 LINE Console:
                                </p>
                                <div className="bg-white dark:bg-gray-800 px-4 py-2 rounded-lg font-mono text-sm">
                                    {webhookInfo.webhook_url}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Submit Button */}
                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="w-5 h-5 animate-spin" />
                                <span>儲存中...</span>
                            </>
                        ) : (
                            <>
                                <Save className="w-5 h-5" />
                                <span>儲存設定</span>
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    )
}

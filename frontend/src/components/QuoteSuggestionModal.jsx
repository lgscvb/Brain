import { useState, useEffect } from 'react'
import { X, FileText, Loader2, Check, AlertCircle, ExternalLink, Trash2, Edit3 } from 'lucide-react'
import axios from 'axios'

/**
 * 報價建議 Modal
 *
 * 當使用者點擊「報價單」按鈕時，會先分析對話內容，
 * 顯示 AI 建議的服務項目讓使用者確認後再建立報價單。
 */
export default function QuoteSuggestionModal({
    isOpen,
    onClose,
    lineUserId,
    customerName
}) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [analysis, setAnalysis] = useState(null)
    const [selectedServices, setSelectedServices] = useState([])
    const [creating, setCreating] = useState(false)
    const [createdQuote, setCreatedQuote] = useState(null)

    // 當 Modal 開啟時分析對話
    useEffect(() => {
        if (isOpen && lineUserId) {
            analyzeConversation()
        }
    }, [isOpen, lineUserId])

    // 分析對話
    const analyzeConversation = async () => {
        setLoading(true)
        setError(null)
        setAnalysis(null)
        setSelectedServices([])
        setCreatedQuote(null)

        try {
            const response = await axios.post('/api/quotes/analyze', {
                line_user_id: lineUserId,
                max_messages: 20
            })

            if (response.data.success) {
                setAnalysis(response.data)
                // 預設選擇所有建議的服務
                setSelectedServices(
                    response.data.suggested_services.map(s => s.code)
                )
            } else {
                setError(response.data.message || '分析失敗')
            }
        } catch (err) {
            console.error('Analyze error:', err)
            setError(err.response?.data?.detail || err.message || '分析失敗')
        } finally {
            setLoading(false)
        }
    }

    // 切換服務選擇
    const toggleService = (code) => {
        setSelectedServices(prev => {
            if (prev.includes(code)) {
                return prev.filter(c => c !== code)
            } else {
                return [...prev, code]
            }
        })
    }

    // 計算選擇的服務總金額
    const calculateTotal = () => {
        if (!analysis) return { amount: 0, deposit: 0 }

        let amount = 0
        let deposit = 0

        for (const service of analysis.suggested_services) {
            if (selectedServices.includes(service.code)) {
                amount += service.amount
                deposit += service.deposit
            }
        }

        return { amount, deposit }
    }

    // 建立報價單
    const createQuote = async () => {
        if (selectedServices.length === 0) {
            setError('請至少選擇一項服務')
            return
        }

        setCreating(true)
        setError(null)

        try {
            const response = await axios.post('/api/quotes/create', {
                line_user_id: lineUserId,
                service_codes: selectedServices,
                customer_name: analysis?.customer_name || customerName
            })

            if (response.data.success) {
                setCreatedQuote(response.data)
            } else {
                setError(response.data.message || '建立失敗')
            }
        } catch (err) {
            console.error('Create quote error:', err)
            setError(err.response?.data?.detail || err.message || '建立報價單失敗')
        } finally {
            setCreating(false)
        }
    }

    // 跳轉到 CRM 報價單頁面
    const openInCRM = () => {
        if (createdQuote?.quote_id) {
            window.open(`https://hj.yourspce.org/quotes/${createdQuote.quote_id}`, '_blank')
        }
    }

    // 跳轉到 CRM 報價單建立頁面（手動編輯）
    const openInCRMEdit = () => {
        const params = new URLSearchParams({
            customer_name: analysis?.customer_name || customerName || '',
            line_user_id: lineUserId || '',
            notes: analysis?.customer_needs || ''
        })
        window.open(`https://hj.yourspce.org/quotes/new?${params.toString()}`, '_blank')
    }

    if (!isOpen) return null

    const totals = calculateTotal()

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-2">
                        <FileText className="w-5 h-5 text-green-600" />
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            報價建議
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
                            <p className="text-gray-600 dark:text-gray-400">分析對話中...</p>
                        </div>
                    ) : error ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
                            <p className="text-red-600 dark:text-red-400 text-center">{error}</p>
                            <button
                                onClick={analyzeConversation}
                                className="mt-4 px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                            >
                                重試
                            </button>
                        </div>
                    ) : createdQuote ? (
                        <div className="flex flex-col items-center justify-center py-8">
                            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
                                <Check className="w-6 h-6 text-green-600" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                                報價單建立成功！
                            </h3>
                            <p className="text-gray-600 dark:text-gray-400 mb-4">
                                報價單號碼：{createdQuote.quote_number}
                            </p>
                            <button
                                onClick={openInCRM}
                                className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                            >
                                <span>在 CRM 中查看</span>
                                <ExternalLink className="w-4 h-4" />
                            </button>
                        </div>
                    ) : analysis ? (
                        <div className="space-y-4">
                            {/* 客戶需求總結 */}
                            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-1">
                                    客戶需求分析
                                </h4>
                                <p className="text-sm text-blue-800 dark:text-blue-200">
                                    {analysis.customer_needs || '無法識別明確需求'}
                                </p>
                            </div>

                            {/* 建議服務列表 */}
                            <div>
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    建議服務項目
                                </h4>
                                {analysis.suggested_services.length === 0 ? (
                                    <p className="text-gray-500 dark:text-gray-400 text-sm">
                                        無法從對話中識別適合的服務
                                    </p>
                                ) : (
                                    <div className="space-y-2">
                                        {analysis.suggested_services.map((service) => (
                                            <div
                                                key={service.code}
                                                onClick={() => toggleService(service.code)}
                                                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                                    selectedServices.includes(service.code)
                                                        ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                                                        : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                                                }`}
                                            >
                                                <div className="flex items-start justify-between">
                                                    <div className="flex-1">
                                                        <div className="flex items-center space-x-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedServices.includes(service.code)}
                                                                onChange={() => {}}
                                                                className="w-4 h-4 text-green-600 rounded"
                                                            />
                                                            <span className="font-medium text-gray-900 dark:text-white">
                                                                {service.name}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
                                                            {service.reason}
                                                        </p>
                                                    </div>
                                                    <div className="text-right ml-4">
                                                        <p className="font-semibold text-gray-900 dark:text-white">
                                                            ${service.amount.toLocaleString()}
                                                        </p>
                                                        <p className="text-xs text-gray-500">
                                                            ${service.unit_price.toLocaleString()}/{service.unit} x {service.quantity}
                                                        </p>
                                                        {service.deposit > 0 && (
                                                            <p className="text-xs text-orange-600">
                                                                押金 ${service.deposit.toLocaleString()}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* 總計 */}
                            {analysis.suggested_services.length > 0 && (
                                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600 dark:text-gray-400">服務費用</span>
                                        <span className="font-semibold text-gray-900 dark:text-white">
                                            ${totals.amount.toLocaleString()}
                                        </span>
                                    </div>
                                    {totals.deposit > 0 && (
                                        <div className="flex justify-between items-center mt-1">
                                            <span className="text-gray-600 dark:text-gray-400">押金</span>
                                            <span className="font-semibold text-orange-600">
                                                ${totals.deposit.toLocaleString()}
                                            </span>
                                        </div>
                                    )}
                                    <div className="border-t border-gray-200 dark:border-gray-600 mt-2 pt-2 flex justify-between items-center">
                                        <span className="font-medium text-gray-900 dark:text-white">合計</span>
                                        <span className="text-lg font-bold text-green-600">
                                            ${(totals.amount + totals.deposit).toLocaleString()}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {/* 分析總結 */}
                            {analysis.analysis_summary && (
                                <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                                    {analysis.analysis_summary}
                                </p>
                            )}
                        </div>
                    ) : null}
                </div>

                {/* Footer */}
                {!loading && !createdQuote && analysis && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                            取消
                        </button>
                        <button
                            onClick={openInCRMEdit}
                            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                            <Edit3 className="w-4 h-4" />
                            <span>手動編輯</span>
                        </button>
                        <button
                            onClick={createQuote}
                            disabled={creating || selectedServices.length === 0}
                            className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
                        >
                            {creating ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>建立中...</span>
                                </>
                            ) : (
                                <>
                                    <FileText className="w-4 h-4" />
                                    <span>建立報價單</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {createdQuote && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                        >
                            關閉
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}

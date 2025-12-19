import { useState, useEffect } from 'react'
import { MessageCircle, Send, Check, X, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import axios from 'axios'

/**
 * 草稿修正對話元件
 * 支援多輪對話修正，記錄歷史並可標記接受/拒絕
 */
export default function RefinementChat({
    draftId,
    initialContent,
    onContentUpdate
}) {
    const [isExpanded, setIsExpanded] = useState(false)
    const [instruction, setInstruction] = useState('')
    const [loading, setLoading] = useState(false)
    const [history, setHistory] = useState([])
    const [historyLoading, setHistoryLoading] = useState(false)

    // 載入修正歷史
    useEffect(() => {
        if (draftId && isExpanded) {
            fetchHistory()
        }
    }, [draftId, isExpanded])

    const fetchHistory = async () => {
        if (!draftId) return
        setHistoryLoading(true)
        try {
            const response = await axios.get(`/api/drafts/${draftId}/refinements`)
            setHistory(response.data.refinements || [])
        } catch (error) {
            console.error('載入修正歷史失敗:', error)
        } finally {
            setHistoryLoading(false)
        }
    }

    // 提交修正指令
    const handleSubmit = async () => {
        if (!instruction.trim() || !draftId) return

        setLoading(true)
        try {
            const response = await axios.post(`/api/drafts/${draftId}/refine`, {
                instruction: instruction.trim()
            })

            // 更新歷史
            setHistory(prev => [...prev, response.data])

            // 更新主內容
            if (onContentUpdate && response.data.refined_content) {
                onContentUpdate(response.data.refined_content)
            }

            // 清空輸入
            setInstruction('')
        } catch (error) {
            console.error('修正失敗:', error)
            alert('修正失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setLoading(false)
        }
    }

    // 標記接受/拒絕
    const handleAccept = async (refinementId) => {
        try {
            await axios.post(`/api/drafts/${draftId}/refinements/${refinementId}/accept`)
            setHistory(prev => prev.map(r =>
                r.id === refinementId ? { ...r, is_accepted: true } : r
            ))
        } catch (error) {
            console.error('標記失敗:', error)
        }
    }

    const handleReject = async (refinementId) => {
        try {
            await axios.post(`/api/drafts/${draftId}/refinements/${refinementId}/reject`)
            setHistory(prev => prev.map(r =>
                r.id === refinementId ? { ...r, is_accepted: false } : r
            ))
        } catch (error) {
            console.error('標記失敗:', error)
        }
    }

    // 使用特定版本
    const handleUseVersion = (content) => {
        if (onContentUpdate) {
            onContentUpdate(content)
        }
    }

    if (!draftId) return null

    return (
        <div className="border border-purple-200 dark:border-purple-800 rounded-lg overflow-hidden">
            {/* 標題列 - 可收合 */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/30 hover:bg-purple-100 dark:hover:bg-purple-900/50 transition-colors"
            >
                <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="font-medium text-purple-700 dark:text-purple-300">
                        AI 草稿修正
                    </span>
                    {history.length > 0 && (
                        <span className="text-xs bg-purple-200 dark:bg-purple-800 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full">
                            {history.length} 輪修正
                        </span>
                    )}
                </div>
                {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                )}
            </button>

            {/* 展開的內容 */}
            {isExpanded && (
                <div className="p-3 space-y-3 bg-white dark:bg-gray-800">
                    {/* 修正歷史 */}
                    {historyLoading ? (
                        <div className="text-center py-4 text-gray-500">
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600 mx-auto"></div>
                        </div>
                    ) : history.length > 0 ? (
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                            {history.map((item, index) => (
                                <div
                                    key={item.id}
                                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-2 text-sm"
                                >
                                    {/* 修正指令 */}
                                    <div className="flex items-start space-x-2 mb-2">
                                        <span className="text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                                            第 {item.round_number} 輪
                                        </span>
                                        <p className="text-gray-600 dark:text-gray-400 flex-1">
                                            {item.instruction}
                                        </p>
                                    </div>

                                    {/* 修正結果（可收合顯示） */}
                                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded p-2 mb-2">
                                        <p className="text-gray-700 dark:text-gray-300 line-clamp-3">
                                            {item.refined_content}
                                        </p>
                                    </div>

                                    {/* 操作按鈕 */}
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-2">
                                            {item.is_accepted === true && (
                                                <span className="text-xs text-green-600 dark:text-green-400 flex items-center space-x-1">
                                                    <Check className="w-3 h-3" />
                                                    <span>已接受</span>
                                                </span>
                                            )}
                                            {item.is_accepted === false && (
                                                <span className="text-xs text-red-600 dark:text-red-400 flex items-center space-x-1">
                                                    <X className="w-3 h-3" />
                                                    <span>已拒絕</span>
                                                </span>
                                            )}
                                            {item.is_accepted === null && (
                                                <div className="flex space-x-1">
                                                    <button
                                                        onClick={() => handleAccept(item.id)}
                                                        className="p-1 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 rounded"
                                                        title="接受這個版本"
                                                    >
                                                        <Check className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleReject(item.id)}
                                                        className="p-1 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                                                        title="拒絕這個版本"
                                                    >
                                                        <X className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => handleUseVersion(item.refined_content)}
                                            className="text-xs text-purple-600 hover:text-purple-700 dark:text-purple-400"
                                        >
                                            使用此版本
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
                            <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>輸入指令讓 AI 修正草稿</p>
                            <p className="text-xs mt-1">例如：「語氣更正式一點」、「加入價格資訊」</p>
                        </div>
                    )}

                    {/* 輸入區 */}
                    <div className="flex space-x-2">
                        <input
                            type="text"
                            value={instruction}
                            onChange={(e) => setInstruction(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                            placeholder="輸入修正指令，如「語氣更親切」..."
                            className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                            disabled={loading}
                        />
                        <button
                            onClick={handleSubmit}
                            disabled={loading || !instruction.trim()}
                            className={`px-3 py-2 rounded-lg flex items-center space-x-1 ${
                                loading || !instruction.trim()
                                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    : 'bg-purple-600 hover:bg-purple-700 text-white'
                            }`}
                        >
                            {loading ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Send className="w-4 h-4" />
                            )}
                        </button>
                    </div>

                    {/* 常用指令快捷按鈕 */}
                    <div className="flex flex-wrap gap-1">
                        {['語氣更親切', '更簡潔', '加入價格', '更正式'].map((cmd) => (
                            <button
                                key={cmd}
                                onClick={() => setInstruction(cmd)}
                                className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                            >
                                {cmd}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

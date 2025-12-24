import { useState, useEffect, useId, useRef, useCallback } from 'react'
import { MessageCircle, Send, Check, X, ChevronDown, ChevronUp, Sparkles, BookmarkPlus, Lightbulb } from 'lucide-react'
import axios from 'axios'

/**
 * 草稿修正對話元件
 * 支援多輪對話修正，記錄歷史並可標記接受/拒絕
 *
 * @param {number} draftId - 草稿 ID
 * @param {string} initialContent - 初始內容
 * @param {function} onContentUpdate - 內容更新回調
 * @param {boolean} autoExpand - 是否預設展開（用於獨立第四欄時）
 */
export default function RefinementChat({
    draftId,
    initialContent,
    onContentUpdate,
    autoExpand = false
}) {
    const uniqueId = useId()
    const textareaRef = useRef(null)
    const [isExpanded, setIsExpanded] = useState(autoExpand)
    const [instruction, setInstruction] = useState('')
    const [loading, setLoading] = useState(false)
    const [history, setHistory] = useState([])
    const [historyLoading, setHistoryLoading] = useState(false)

    // 自動調整 textarea 高度
    const adjustTextareaHeight = useCallback(() => {
        const textarea = textareaRef.current
        if (textarea) {
            textarea.style.height = 'auto'
            const minHeight = 80 // 約 4 行
            const maxHeight = 150
            const scrollHeight = textarea.scrollHeight
            textarea.style.height = `${Math.min(Math.max(scrollHeight, minHeight), maxHeight)}px`
        }
    }, [])
    // 知識建議相關 state
    const [knowledgeSuggestion, setKnowledgeSuggestion] = useState(null)
    const [savingKnowledge, setSavingKnowledge] = useState(false)
    const [showManualSave, setShowManualSave] = useState(false)
    const [manualContent, setManualContent] = useState('')
    const [manualCategory, setManualCategory] = useState('faq')

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
        setKnowledgeSuggestion(null)  // 清除之前的建議
        try {
            const response = await axios.post(`/api/drafts/${draftId}/refine`, {
                instruction: instruction.trim()
            })

            // 更新歷史（包含 knowledge_suggestion）
            setHistory(prev => [...prev, response.data])

            // 更新主內容
            if (onContentUpdate && response.data.refined_content) {
                onContentUpdate(response.data.refined_content)
            }

            // 檢查是否有知識建議
            if (response.data.knowledge_suggestion?.detected) {
                setKnowledgeSuggestion({
                    ...response.data.knowledge_suggestion,
                    refinementId: response.data.id
                })
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

    // 儲存知識到知識庫
    const handleSaveKnowledge = async (content, category, refinementId = null) => {
        setSavingKnowledge(true)
        try {
            await axios.post('/api/knowledge/from-refinement', {
                content,
                category,
                refinement_id: refinementId
            })
            // 清除建議
            setKnowledgeSuggestion(null)
            setShowManualSave(false)
            setManualContent('')
            alert('知識已儲存！')
        } catch (error) {
            console.error('儲存知識失敗:', error)
            alert('儲存失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setSavingKnowledge(false)
        }
    }

    // 關閉知識建議（不儲存）
    const handleDismissKnowledge = () => {
        setKnowledgeSuggestion(null)
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

    // 知識分類選項
    const categoryOptions = [
        { value: 'faq', label: '常見問題' },
        { value: 'service_info', label: '服務資訊' },
        { value: 'process', label: '作業流程' },
        { value: 'objection', label: '異議處理' },
        { value: 'customer_info', label: '客戶背景' },
        { value: 'template', label: '回覆模板' }
    ]

    // 知識建議 UI 元件（支援多個知識點）
    const KnowledgeSuggestionBanner = () => {
        if (!knowledgeSuggestion) return null

        // 支援新格式 (items 陣列) 和舊格式 (content/category/reason)
        const items = knowledgeSuggestion.items?.length > 0
            ? knowledgeSuggestion.items
            : knowledgeSuggestion.content
                ? [{ content: knowledgeSuggestion.content, category: knowledgeSuggestion.category, reason: knowledgeSuggestion.reason }]
                : []

        if (items.length === 0) return null

        return (
            <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg p-3 mb-3">
                <div className="flex items-start space-x-2">
                    <Lightbulb className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2">
                            偵測到 {items.length} 個可儲存的知識點
                        </p>

                        {/* 知識點列表 */}
                        <div className="space-y-3">
                            {items.map((item, index) => (
                                <div key={index} className="bg-white dark:bg-gray-800 rounded p-2 border border-amber-200 dark:border-amber-700">
                                    <p className="text-xs text-amber-700 dark:text-amber-300 mb-1">
                                        {item.reason}
                                    </p>
                                    <div className="text-sm text-gray-700 dark:text-gray-300 mb-2 whitespace-pre-wrap">
                                        {item.content}
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-amber-600 dark:text-amber-400">
                                            {categoryOptions.find(c => c.value === item.category)?.label || item.category}
                                        </span>
                                        <button
                                            onClick={() => handleSaveKnowledge(
                                                item.content,
                                                item.category,
                                                knowledgeSuggestion.refinementId
                                            )}
                                            disabled={savingKnowledge}
                                            className="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white text-xs rounded flex items-center space-x-1"
                                        >
                                            {savingKnowledge ? (
                                                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            ) : (
                                                <BookmarkPlus className="w-3 h-3" />
                                            )}
                                            <span>儲存</span>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* 全部略過按鈕 */}
                        <div className="flex justify-end mt-2">
                            <button
                                onClick={handleDismissKnowledge}
                                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                            >
                                全部略過
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 手動儲存知識 Modal
    const ManualSaveModal = () => {
        if (!showManualSave) return null
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowManualSave(false)}>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 w-96 max-w-[90vw]" onClick={e => e.stopPropagation()}>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center space-x-2">
                        <BookmarkPlus className="w-5 h-5 text-purple-600" />
                        <span>儲存為知識</span>
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label htmlFor={`${uniqueId}-manual-content`} className="block text-sm text-gray-600 dark:text-gray-400 mb-1">知識內容</label>
                            <textarea
                                id={`${uniqueId}-manual-content`}
                                name={`${uniqueId}-manual-content`}
                                value={manualContent}
                                onChange={(e) => setManualContent(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm h-24"
                                placeholder="輸入要儲存的知識內容..."
                            />
                        </div>
                        <div>
                            <label htmlFor={`${uniqueId}-manual-category`} className="block text-sm text-gray-600 dark:text-gray-400 mb-1">分類</label>
                            <select
                                id={`${uniqueId}-manual-category`}
                                name={`${uniqueId}-manual-category`}
                                value={manualCategory}
                                onChange={(e) => setManualCategory(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                            >
                                {categoryOptions.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="flex justify-end space-x-2">
                            <button
                                onClick={() => setShowManualSave(false)}
                                className="px-4 py-2 text-gray-600 dark:text-gray-400 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            >
                                取消
                            </button>
                            <button
                                onClick={() => handleSaveKnowledge(manualContent, manualCategory)}
                                disabled={!manualContent.trim() || savingKnowledge}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded disabled:opacity-50"
                            >
                                {savingKnowledge ? '儲存中...' : '儲存'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // autoExpand 模式下不顯示外框和收合按鈕（用於獨立第四欄）
    if (autoExpand) {
        return (
            <div className="p-3 bg-white dark:bg-gray-800 h-full flex flex-col overflow-hidden">
                {/* 知識建議提示 */}
                <KnowledgeSuggestionBanner />

                {/* 修正歷史 - 佔據上半部，可滾動 */}
                {historyLoading ? (
                    <div className="text-center py-4 text-gray-500 flex-shrink-0">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600 mx-auto"></div>
                    </div>
                ) : history.length > 0 ? (
                    <div className="space-y-2 flex-1 overflow-y-auto min-h-0 mb-3">
                        {history.map((item) => (
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

                                {/* 修正結果 - 可滾動查看完整內容 */}
                                <div className="bg-gray-50 dark:bg-gray-700/50 rounded p-2 mb-2 max-h-60 overflow-y-auto">
                                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap text-sm">
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
                    <div className="py-6 text-gray-500 dark:text-gray-400 text-sm text-center flex-shrink-0">
                        <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>輸入指令讓 AI 修正草稿</p>
                        <p className="text-xs mt-1">例如：「語氣更正式一點」</p>
                    </div>
                )}

                {/* 輸入區 - 固定高度 */}
                <div className="flex-shrink-0 space-y-2 border-t border-gray-200 dark:border-gray-700 pt-3">
                    <div className="flex flex-col space-y-2">
                        <textarea
                            ref={textareaRef}
                            id={`${uniqueId}-instruction-expanded`}
                            name={`${uniqueId}-instruction-expanded`}
                            value={instruction}
                            onChange={(e) => {
                                setInstruction(e.target.value)
                                adjustTextareaHeight()
                            }}
                            onKeyDown={(e) => {
                                // Ctrl+Enter 或 Cmd+Enter 送出
                                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                                    e.preventDefault()
                                    handleSubmit()
                                }
                            }}
                            placeholder="輸入修正指令...（Ctrl+Enter 送出）"
                            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                            style={{ minHeight: '80px', maxHeight: '150px' }}
                            disabled={loading}
                        />
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Ctrl+Enter 送出</span>
                            <button
                                onClick={handleSubmit}
                                disabled={loading || !instruction.trim()}
                                className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
                                    loading || !instruction.trim()
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-purple-600 hover:bg-purple-700 text-white'
                                }`}
                            >
                                {loading ? (
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <Send className="w-4 h-4" />
                                        <span>送出修正</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* 常用指令快捷按鈕 + 手動儲存 */}
                    <div className="flex items-center justify-between">
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
                        <button
                            onClick={() => setShowManualSave(true)}
                            className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 rounded hover:bg-purple-200 dark:hover:bg-purple-800 flex items-center space-x-1"
                            title="手動儲存知識"
                        >
                            <BookmarkPlus className="w-3 h-3" />
                            <span>存知識</span>
                        </button>
                    </div>
                </div>
                {/* 手動儲存 Modal */}
                <ManualSaveModal />
            </div>
        )
    }

    // 原本的收合模式（用於三欄佈局或手機版）
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
                    {/* 知識建議提示 */}
                    <KnowledgeSuggestionBanner />

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

                                    {/* 修正結果 - 可滾動查看完整內容 */}
                                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded p-2 mb-2 max-h-32 overflow-y-auto">
                                        <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap text-sm">
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
                    <div className="flex flex-col space-y-2">
                        <textarea
                            id={`${uniqueId}-instruction-collapsed`}
                            name={`${uniqueId}-instruction-collapsed`}
                            value={instruction}
                            onChange={(e) => setInstruction(e.target.value)}
                            onKeyDown={(e) => {
                                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                                    e.preventDefault()
                                    handleSubmit()
                                }
                            }}
                            placeholder="輸入修正指令...&#10;例如：語氣更親切、加入價格資訊&#10;&#10;按 Ctrl+Enter 送出"
                            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                            rows={5}
                            disabled={loading}
                        />
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Ctrl+Enter 送出</span>
                            <button
                                onClick={handleSubmit}
                                disabled={loading || !instruction.trim()}
                                className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
                                    loading || !instruction.trim()
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-purple-600 hover:bg-purple-700 text-white'
                                }`}
                            >
                                {loading ? (
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <Send className="w-4 h-4" />
                                        <span>送出</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* 常用指令快捷按鈕 + 手動儲存 */}
                    <div className="flex items-center justify-between">
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
                        <button
                            onClick={() => setShowManualSave(true)}
                            className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 rounded hover:bg-purple-200 dark:hover:bg-purple-800 flex items-center space-x-1"
                            title="手動儲存知識"
                        >
                            <BookmarkPlus className="w-3 h-3" />
                            <span>存知識</span>
                        </button>
                    </div>
                </div>
            )}
            {/* 手動儲存 Modal */}
            <ManualSaveModal />
        </div>
    )
}

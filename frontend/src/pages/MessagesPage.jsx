import { useState, useEffect, useRef, useCallback, memo } from 'react'
import { MessageSquare, Clock, User, Send, RefreshCw, Archive, ChevronRight, ChevronLeft, X, Bell, BellOff, Volume2, VolumeX, Trash2 } from 'lucide-react'
import axios from 'axios'
import FeedbackPanel from '../components/FeedbackPanel'
import RefinementChat from '../components/RefinementChat'
import notificationService from '../services/notificationService'

// =====================================================
// === 獨立元件定義（避免 React 重新掛載問題）===
// =====================================================

// 工具函數
const getSourceIcon = (source) => {
    if (source === 'line_oa') return '💬'
    if (source === 'email') return '📧'
    if (source === 'phone') return '📞'
    return '💭'
}

const formatTime = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return date.toLocaleString('zh-TW', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

const getStatusBadge = (status) => {
    const styles = {
        pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
        drafted: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
        sent: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
        archived: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
    const labels = {
        pending: '待處理',
        drafted: '已生成草稿',
        sent: '已發送',
        archived: '已封存'
    }
    return (
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[status] || styles.pending}`}>
            {labels[status] || status}
        </span>
    )
}

// === 左欄：對話列表元件 ===
const ConversationListPanel = memo(function ConversationListPanel({
    isMobile = false,
    isCollapsed = false,
    conversations,
    loading,
    selectedConversation,
    onSelectConversation,
    onDeleteConversation,
    onToggleCollapse
}) {
    // 縮小模式：只顯示圖示列表
    if (isCollapsed && !isMobile) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col w-14">
                {/* 展開按鈕 */}
                <button
                    onClick={onToggleCollapse}
                    className="p-3 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    title="展開對話列表"
                >
                    <ChevronRight className="w-5 h-5 text-gray-500 mx-auto" />
                </button>

                {/* 對話圖示列表 */}
                <div className="flex-1 overflow-y-auto">
                    {conversations.map((conv) => (
                        <button
                            key={conv.sender_id}
                            onClick={() => onSelectConversation(conv)}
                            className={`w-full p-2 flex flex-col items-center justify-center hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                                selectedConversation?.sender_id === conv.sender_id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                            }`}
                            title={conv.sender_name}
                        >
                            <span className="text-lg">{getSourceIcon(conv.source)}</span>
                            {conv.unread_count > 0 && (
                                <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full mt-1">
                                    {conv.unread_count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col ${isMobile ? 'h-full' : ''}`}>
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">對話列表</h3>
                    <p className="text-xs text-gray-500 mt-1">{conversations.length} 個對話</p>
                </div>
                {!isMobile && onToggleCollapse && (
                    <button
                        onClick={onToggleCollapse}
                        className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="縮小對話列表"
                    >
                        <ChevronLeft className="w-4 h-4 text-gray-500" />
                    </button>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : conversations.length === 0 ? (
                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                    目前沒有對話
                </div>
            ) : (
                <div className="flex-1 divide-y divide-gray-200 dark:divide-gray-700 overflow-y-auto">
                    {conversations.map((conv) => (
                        <div
                            key={conv.sender_id}
                            className={`relative group ${
                                selectedConversation?.sender_id === conv.sender_id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                            }`}
                        >
                            <button
                                onClick={() => onSelectConversation(conv)}
                                className="w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center space-x-2 min-w-0">
                                        <span>{getSourceIcon(conv.source)}</span>
                                        <span className="font-medium text-gray-900 dark:text-white truncate">
                                            {conv.sender_name}
                                        </span>
                                    </div>
                                    {conv.unread_count > 0 && (
                                        <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full flex-shrink-0">
                                            {conv.unread_count}
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                    {conv.last_message_preview}
                                </p>
                                <div className="flex items-center justify-between mt-1">
                                    <span className="text-xs text-gray-400">
                                        {formatTime(conv.last_message_at)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                        {conv.message_count} 則訊息
                                    </span>
                                </div>
                            </button>
                            {/* 刪除按鈕 - hover 時顯示 */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onDeleteConversation(conv)
                                }}
                                className="absolute top-2 right-2 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                                title="刪除對話"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
})

// === 中欄：聊天式對話介面（合併訊息歷史 + 回覆區）===
const ChatPanel = memo(function ChatPanel({
    isMobile = false,
    idSuffix = '',
    selectedConversation,
    conversationMessages,
    conversationLoading,
    selectedMessage,
    messageDetail,
    detailLoading,
    replyContent,
    sending,
    onSelectMessage,
    onReplyContentChange,
    onSendReply,
    onRegenerate,
    onArchive,
    onBack,
    onFeedbackSubmit
}) {
    const chatContainerRef = useRef(null)

    // 自動滾動到最新訊息
    useEffect(() => {
        if (chatContainerRef.current && conversationMessages.length > 0) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
        }
    }, [conversationMessages])

    // 找出目前選中的訊息（用於顯示回覆區）
    const activeMessage = selectedMessage || (conversationMessages.length > 0 ? conversationMessages[conversationMessages.length - 1] : null)
    const hasDraft = messageDetail?.drafts && messageDetail.drafts.length > 0
    const needsReply = activeMessage && activeMessage.status !== 'sent' && activeMessage.status !== 'archived'

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col ${isMobile ? 'h-full' : ''}`}>
            {/* 標題列 */}
            <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
                {isMobile && (
                    <button
                        onClick={onBack}
                        className="mr-2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                )}
                <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                        {selectedConversation ? selectedConversation.sender_name : '對話'}
                    </h3>
                    {selectedConversation && (
                        <p className="text-xs text-gray-500">{conversationMessages.length} 則訊息</p>
                    )}
                </div>
                {activeMessage && needsReply && (
                    <button
                        onClick={onRegenerate}
                        className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                        title={hasDraft ? '重新生成草稿' : '生成 AI 草稿'}
                    >
                        <RefreshCw className="w-3 h-3" />
                        <span>{hasDraft ? '重新生成' : '生成草稿'}</span>
                    </button>
                )}
            </div>

            {/* 對話歷史區 */}
            {!selectedConversation ? (
                <div className="flex-1 flex items-center justify-center p-8 text-center text-gray-500 dark:text-gray-400">
                    <div>
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>選擇一個對話開始</p>
                    </div>
                </div>
            ) : conversationLoading ? (
                <div className="flex-1 flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <>
                    {/* 聊天訊息列表（舊的在上、新的在下） */}
                    <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-3 space-y-3">
                        {[...conversationMessages].sort((a, b) =>
                            new Date(a.created_at) - new Date(b.created_at)
                        ).map((message) => (
                            <div key={message.id} className="space-y-2">
                                {/* 客戶訊息（靠左） */}
                                <div
                                    onClick={() => onSelectMessage(message)}
                                    className={`max-w-[85%] cursor-pointer transition-all ${
                                        selectedMessage?.id === message.id
                                            ? 'ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-800'
                                            : 'hover:shadow-md'
                                    }`}
                                >
                                    <div className="bg-gray-100 dark:bg-gray-700 rounded-lg rounded-tl-none p-3">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <User className="w-3 h-3 text-gray-500" />
                                            <span className="text-xs text-gray-500">
                                                {formatTime(message.created_at)}
                                            </span>
                                            {getStatusBadge(message.status)}
                                        </div>
                                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                            {message.content}
                                        </p>
                                        {message.drafts && message.drafts.length > 0 && !message.response && (
                                            <p className="text-xs text-blue-500 mt-2 flex items-center space-x-1">
                                                <span>🤖</span>
                                                <span>有 AI 草稿</span>
                                            </p>
                                        )}
                                    </div>
                                </div>

                                {/* Hour Jungle 回覆（靠右） */}
                                {message.response && message.response.final_content && (
                                    <div className="flex justify-end">
                                        <div className="max-w-[85%] bg-green-100 dark:bg-green-900/30 rounded-lg rounded-tr-none p-3">
                                            <div className="flex items-center space-x-2 mb-1">
                                                <span className="text-xs font-medium text-green-600 dark:text-green-400">
                                                    Hour Jungle
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    {formatTime(message.response.sent_at)}
                                                </span>
                                                {message.response.is_modified && (
                                                    <span className="text-xs text-orange-500">已修改</span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                                {message.response.final_content}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* 回覆區（固定在底部）*/}
                    {activeMessage && needsReply && (
                        <div className="border-t border-gray-200 dark:border-gray-700 p-3 space-y-3 flex-shrink-0 bg-gray-50 dark:bg-gray-800/50">
                            {detailLoading ? (
                                <div className="flex items-center justify-center py-4">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                    <span className="ml-2 text-sm text-gray-500">載入中...</span>
                                </div>
                            ) : hasDraft ? (
                                <>
                                    {/* 策略提示 */}
                                    {messageDetail.drafts[0].strategy && (
                                        <div className="text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 rounded p-2">
                                            <span className="font-medium">策略：</span>
                                            {messageDetail.drafts[0].strategy}
                                        </div>
                                    )}

                                    {/* 回覆編輯區 */}
                                    <label htmlFor={`reply-content-${messageDetail.id}${idSuffix}`} className="sr-only">
                                        回覆內容
                                    </label>
                                    <textarea
                                        id={`reply-content-${messageDetail.id}${idSuffix}`}
                                        name={`reply-content-${messageDetail.id}${idSuffix}`}
                                        value={replyContent}
                                        onChange={(e) => onReplyContentChange(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                                        rows={15}
                                        placeholder="編輯回覆內容..."
                                    />

                                    {/* 評分 + 操作按鈕 */}
                                    <div className="flex items-center justify-between">
                                        <FeedbackPanel
                                            draftId={messageDetail.drafts[0].id}
                                            idSuffix={idSuffix}
                                            initialFeedback={{
                                                is_good: messageDetail.drafts[0].is_good,
                                                rating: messageDetail.drafts[0].rating,
                                                feedback_reason: messageDetail.drafts[0].feedback_reason
                                            }}
                                            onFeedbackSubmit={onFeedbackSubmit}
                                            compact={true}
                                        />
                                        <div className="flex space-x-2">
                                            <button
                                                onClick={onArchive}
                                                className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                                            >
                                                <Archive className="w-3 h-3" />
                                                <span>封存</span>
                                            </button>
                                            <button
                                                onClick={onSendReply}
                                                disabled={sending || !replyContent.trim()}
                                                className={`flex items-center space-x-1 px-4 py-1.5 text-sm rounded-lg transition-colors ${
                                                    sending || !replyContent.trim()
                                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                                                }`}
                                            >
                                                {sending ? (
                                                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                ) : (
                                                    <Send className="w-3 h-3" />
                                                )}
                                                <span>{sending ? '發送中...' : '發送'}</span>
                                            </button>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                /* 沒有草稿時顯示生成按鈕 */
                                <div className="text-center py-4">
                                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                                        尚無 AI 草稿
                                    </p>
                                    <button
                                        onClick={onRegenerate}
                                        className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                                    >
                                        <RefreshCw className="w-4 h-4" />
                                        <span>生成草稿</span>
                                    </button>
                                </div>
                            )}

                            {/* 訊息代號 */}
                            {messageDetail && (
                                <p className="text-[10px] text-gray-400 dark:text-gray-500 font-mono">
                                    訊息 #{messageDetail.id}
                                    {messageDetail.drafts?.[0]?.id && ` | 草稿 #${messageDetail.drafts[0].id}`}
                                </p>
                            )}
                        </div>
                    )}

                    {/* 已發送或已封存的訊息 */}
                    {activeMessage && !needsReply && (
                        <div className="border-t border-gray-200 dark:border-gray-700 p-3 text-center text-sm text-gray-500 dark:text-gray-400 flex-shrink-0">
                            {activeMessage.status === 'sent' ? (
                                <span className="text-green-600 dark:text-green-400">✓ 已發送回覆</span>
                            ) : (
                                <span>已封存</span>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    )
})

// === 第四欄：AI 修正對話元件（獨立出來的 RefinementChat）===
const RefinementPanel = memo(function RefinementPanel({
    messageDetail,
    replyContent,
    onReplyContentChange
}) {
    const draftId = messageDetail?.drafts?.[0]?.id

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                    <span>✨</span>
                    <span>AI 草稿修正</span>
                </h3>
                <p className="text-xs text-gray-500 mt-1">輸入指令讓 AI 幫你調整草稿</p>
            </div>

            {!messageDetail ? (
                <div className="flex-1 flex items-center justify-center p-8 text-center text-gray-500 dark:text-gray-400">
                    <div>
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>選擇一則訊息後</p>
                        <p className="text-sm">即可使用 AI 修正功能</p>
                    </div>
                </div>
            ) : !draftId ? (
                <div className="flex-1 flex items-center justify-center p-8 text-center text-gray-500 dark:text-gray-400">
                    <div>
                        <RefreshCw className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>尚無 AI 草稿</p>
                        <p className="text-sm mt-1">請先生成草稿後再使用修正功能</p>
                    </div>
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto">
                    <RefinementChat
                        draftId={draftId}
                        initialContent={replyContent}
                        onContentUpdate={onReplyContentChange}
                        autoExpand={true}
                    />
                </div>
            )}
        </div>
    )
})

// =====================================================
// === 主頁面元件 ===
// =====================================================

export default function MessagesPage() {
    // === 三欄式狀態 ===
    const [conversations, setConversations] = useState([])
    const [selectedConversation, setSelectedConversation] = useState(null)
    const [conversationMessages, setConversationMessages] = useState([])
    const [conversationLoading, setConversationLoading] = useState(false)

    // === 原有狀態 ===
    const [messages, setMessages] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedMessage, setSelectedMessage] = useState(null)
    const [messageDetail, setMessageDetail] = useState(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [filter, setFilter] = useState('all') // pending, drafted, sent, all
    const [replyContent, setReplyContent] = useState('')
    const [sending, setSending] = useState(false)
    const [notificationEnabled, setNotificationEnabled] = useState(notificationService.notificationEnabled)
    const [soundEnabled, setSoundEnabled] = useState(notificationService.soundEnabled)
    const [newMessageCount, setNewMessageCount] = useState(0)
    const isFirstLoad = useRef(true)
    const pollInterval = useRef(null)

    // === 手機版視圖狀態 ===
    const [mobileView, setMobileView] = useState('conversations') // 'conversations' | 'history' | 'detail'

    // === 第一欄縮小狀態 ===
    const [isFirstColumnCollapsed, setIsFirstColumnCollapsed] = useState(false)

    // 請求通知權限
    const requestNotificationPermission = async () => {
        const granted = await notificationService.requestPermission()
        if (granted) {
            setNotificationEnabled(true)
            notificationService.setNotificationEnabled(true)
        }
    }

    // 切換通知
    const toggleNotification = async () => {
        if (!notificationEnabled) {
            await requestNotificationPermission()
        } else {
            setNotificationEnabled(false)
            notificationService.setNotificationEnabled(false)
        }
    }

    // 切換音效
    const toggleSound = () => {
        const newValue = !soundEnabled
        setSoundEnabled(newValue)
        notificationService.setSoundEnabled(newValue)
        if (newValue) {
            notificationService.playSound()
        }
    }

    // === 對話列表 API ===
    const fetchConversations = useCallback(async () => {
        try {
            const response = await axios.get('/api/conversations')
            setConversations(response.data.conversations)
        } catch (error) {
            console.error('獲取對話列表失敗:', error)
        }
    }, [])

    // === 對話訊息 API ===
    const fetchConversationMessages = useCallback(async (senderId, autoSelectLatest = true) => {
        setConversationLoading(true)
        try {
            const response = await axios.get(`/api/conversations/${encodeURIComponent(senderId)}/messages`)
            const messages = response.data.messages
            setConversationMessages(messages)

            // 自動選擇最後一則待處理/已生成草稿的訊息
            if (autoSelectLatest && messages.length > 0) {
                // 優先找待處理或已生成草稿的訊息
                const pendingMsg = [...messages].reverse().find(m =>
                    m.status === 'pending' || m.status === 'drafted'
                )
                const targetMsg = pendingMsg || messages[messages.length - 1]
                setSelectedMessage(targetMsg)
                // 載入訊息詳情
                setDetailLoading(true)
                try {
                    const detailRes = await axios.get(`/api/messages/${targetMsg.id}`)
                    setMessageDetail(detailRes.data)
                    if (detailRes.data.drafts && detailRes.data.drafts.length > 0) {
                        setReplyContent(detailRes.data.drafts[0].content)
                    }
                } catch (err) {
                    console.error('載入訊息詳情失敗:', err)
                } finally {
                    setDetailLoading(false)
                }
            }
        } catch (error) {
            console.error('獲取對話訊息失敗:', error)
        } finally {
            setConversationLoading(false)
        }
    }, [])

    // === 選擇對話 ===
    const handleSelectConversation = useCallback((conversation) => {
        setSelectedConversation(conversation)
        fetchConversationMessages(conversation.sender_id)
        setSelectedMessage(null)
        setMessageDetail(null)
        setMobileView('history')
        // 自動縮小第一欄
        setIsFirstColumnCollapsed(true)
    }, [fetchConversationMessages])

    // === 切換第一欄縮放 ===
    const handleToggleFirstColumn = useCallback(() => {
        setIsFirstColumnCollapsed(prev => !prev)
    }, [])

    // === 選擇訊息 ===
    const fetchMessageDetail = useCallback(async (messageId) => {
        setDetailLoading(true)
        try {
            const response = await axios.get(`/api/messages/${messageId}`)
            setMessageDetail(response.data)
            if (response.data.drafts && response.data.drafts.length > 0) {
                setReplyContent(response.data.drafts[0].content)
            }
        } catch (error) {
            console.error('獲取訊息詳情失敗:', error)
        } finally {
            setDetailLoading(false)
        }
    }, [])

    const handleSelectMessage = useCallback((message) => {
        setSelectedMessage(message)
        fetchMessageDetail(message.id)
        setMobileView('detail')
    }, [fetchMessageDetail])

    // 獲取訊息並檢查新訊息（用於通知）
    const fetchMessagesWithNotification = useCallback(async (showLoading = false) => {
        if (showLoading) setLoading(true)
        try {
            const params = filter === 'all' ? {} : { status: filter }
            const response = await axios.get('/api/messages', { params })
            const newMessages = response.data.messages

            if (isFirstLoad.current) {
                notificationService.resetTracking(newMessages)
                isFirstLoad.current = false
            } else {
                const detected = notificationService.checkNewMessages(newMessages)
                if (detected.length > 0) {
                    setNewMessageCount(prev => prev + detected.length)
                }
            }

            setMessages(newMessages)
        } catch (error) {
            console.error('獲取訊息失敗:', error)
        } finally {
            if (showLoading) setLoading(false)
        }
    }, [filter])

    useEffect(() => {
        // 初始載入
        fetchConversations()
        fetchMessagesWithNotification(true)

        // 設定輪詢
        pollInterval.current = setInterval(() => {
            fetchConversations()
            fetchMessagesWithNotification(false)
        }, 10000)

        return () => {
            if (pollInterval.current) {
                clearInterval(pollInterval.current)
            }
        }
    }, [filter, fetchConversations, fetchMessagesWithNotification])

    const clearNewMessageCount = () => {
        setNewMessageCount(0)
    }

    const fetchMessages = useCallback(async () => {
        setLoading(true)
        try {
            const params = filter === 'all' ? {} : { status: filter }
            const response = await axios.get('/api/messages', { params })
            setMessages(response.data.messages)
            notificationService.resetTracking(response.data.messages)
        } catch (error) {
            console.error('獲取訊息失敗:', error)
        } finally {
            setLoading(false)
        }
    }, [filter])

    const handleSendReply = useCallback(async () => {
        if (!replyContent.trim() || !messageDetail) return

        setSending(true)
        try {
            const draftId = messageDetail.drafts?.[0]?.id || null
            await axios.post(`/api/messages/${messageDetail.id}/send`, {
                content: replyContent,
                draft_id: draftId
            })
            alert('回覆已發送！')
            // 重新載入對話訊息和對話列表（不自動選擇，因為剛發送的已是 sent 狀態）
            if (selectedConversation) {
                fetchConversationMessages(selectedConversation.sender_id, false)
            }
            fetchConversations()
            fetchMessages()
        } catch (error) {
            console.error('發送失敗:', error)
            alert('發送失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setSending(false)
        }
    }, [replyContent, messageDetail, selectedConversation, fetchConversationMessages, fetchConversations, fetchMessages])

    const handleRegenerate = useCallback(async () => {
        if (!messageDetail) return

        try {
            await axios.post(`/api/messages/${messageDetail.id}/regenerate`)
            fetchMessageDetail(messageDetail.id)
        } catch (error) {
            console.error('重新生成失敗:', error)
            alert('重新生成失敗')
        }
    }, [messageDetail, fetchMessageDetail])

    const handleArchive = useCallback(async () => {
        if (!messageDetail) return

        try {
            await axios.post(`/api/messages/${messageDetail.id}/archive`)
            setSelectedMessage(null)
            setMessageDetail(null)
            setMobileView('history')
            if (selectedConversation) {
                fetchConversationMessages(selectedConversation.sender_id)
            }
            fetchConversations()
            fetchMessages()
        } catch (error) {
            console.error('封存失敗:', error)
        }
    }, [messageDetail, selectedConversation, fetchConversationMessages, fetchConversations, fetchMessages])

    // 刪除整個對話
    const handleDeleteConversation = useCallback(async (conversation) => {
        if (!confirm(`確定要刪除 ${conversation.sender_name} 的所有訊息嗎？此操作無法復原。`)) return

        try {
            await axios.delete(`/api/conversations/${encodeURIComponent(conversation.sender_id)}`)
            // 如果刪除的是當前選中的對話，清空選中狀態
            if (selectedConversation?.sender_id === conversation.sender_id) {
                setSelectedConversation(null)
                setConversationMessages([])
                setSelectedMessage(null)
                setMessageDetail(null)
            }
            fetchConversations()
            fetchMessages()
        } catch (error) {
            console.error('刪除對話失敗:', error)
            alert('刪除失敗：' + (error.response?.data?.detail || error.message))
        }
    }, [selectedConversation, fetchConversations, fetchMessages])

    const handleCloseDetail = useCallback(() => {
        setSelectedMessage(null)
        setMessageDetail(null)
    }, [])

    const handleCloseDetailMobile = useCallback(() => {
        setSelectedMessage(null)
        setMessageDetail(null)
        setMobileView('history')
    }, [])

    const handleBackToConversations = useCallback(() => {
        setMobileView('conversations')
    }, [])

    const handleBackToHistory = useCallback(() => {
        setMobileView('history')
    }, [])

    const handleReplyContentChange = useCallback((value) => {
        setReplyContent(value)
    }, [])

    const handleFeedbackSubmit = useCallback(() => {
        if (messageDetail) {
            fetchMessageDetail(messageDetail.id)
        }
    }, [messageDetail, fetchMessageDetail])

    return (
        <div className="h-full flex flex-col">
            {/* 壓縮的標題列 + 篩選器 */}
            <div className="flex-shrink-0 flex items-center justify-between mb-2">
                <div className="flex items-center space-x-4">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                        <span>訊息管理</span>
                        {newMessageCount > 0 && (
                            <span className="px-2 py-0.5 text-xs bg-red-500 text-white rounded-full animate-pulse">
                                {newMessageCount} 新
                            </span>
                        )}
                    </h2>
                    {/* 篩選 Tabs - 移到標題旁邊 */}
                    <div className="hidden sm:flex items-center space-x-1">
                        {[
                            { id: 'pending', label: '待處理' },
                            { id: 'drafted', label: '已生成' },
                            { id: 'sent', label: '已發送' },
                            { id: 'all', label: '全部' }
                        ].map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setFilter(tab.id)}
                                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                                    filter === tab.id
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                                }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="flex items-center space-x-1">
                    {/* 音效開關 */}
                    <button
                        onClick={toggleSound}
                        className={`p-1.5 rounded-md transition-colors ${
                            soundEnabled
                                ? 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-gray-100 text-gray-400 dark:bg-gray-700'
                        }`}
                        title={soundEnabled ? '音效已開啟' : '音效已關閉'}
                    >
                        {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                    </button>

                    {/* 通知開關 */}
                    <button
                        onClick={toggleNotification}
                        className={`p-1.5 rounded-md transition-colors ${
                            notificationEnabled
                                ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                                : 'bg-gray-100 text-gray-400 dark:bg-gray-700'
                        }`}
                        title={notificationEnabled ? '通知已開啟' : '點擊開啟通知'}
                    >
                        {notificationEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
                    </button>

                    {/* 重新整理 */}
                    <button
                        onClick={() => {
                            fetchConversations()
                            fetchMessages()
                            clearNewMessageCount()
                        }}
                        className="p-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                        title="重新整理"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* 手機版篩選（小螢幕顯示）*/}
            <div className="sm:hidden flex space-x-1 overflow-x-auto mb-2">
                {[
                    { id: 'pending', label: '待處理' },
                    { id: 'drafted', label: '已生成' },
                    { id: 'sent', label: '已發送' },
                    { id: 'all', label: '全部' }
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setFilter(tab.id)}
                        className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                            filter === tab.id
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* === 桌面版三欄佈局（聊天 + AI 修正）=== */}
            <div className={`hidden xl:grid gap-3 flex-1 min-h-0 ${
                isFirstColumnCollapsed
                    ? 'xl:grid-cols-[56px_1fr_380px]'
                    : 'xl:grid-cols-[220px_1fr_380px]'
            }`}>
                <ConversationListPanel
                    isCollapsed={isFirstColumnCollapsed}
                    conversations={conversations}
                    loading={loading}
                    selectedConversation={selectedConversation}
                    onSelectConversation={handleSelectConversation}
                    onDeleteConversation={handleDeleteConversation}
                    onToggleCollapse={handleToggleFirstColumn}
                />
                <ChatPanel
                    idSuffix="-xl"
                    selectedConversation={selectedConversation}
                    conversationMessages={conversationMessages}
                    conversationLoading={conversationLoading}
                    selectedMessage={selectedMessage}
                    messageDetail={messageDetail}
                    detailLoading={detailLoading}
                    replyContent={replyContent}
                    sending={sending}
                    onSelectMessage={handleSelectMessage}
                    onReplyContentChange={handleReplyContentChange}
                    onSendReply={handleSendReply}
                    onRegenerate={handleRegenerate}
                    onArchive={handleArchive}
                    onFeedbackSubmit={handleFeedbackSubmit}
                />
                <RefinementPanel
                    messageDetail={messageDetail}
                    replyContent={replyContent}
                    onReplyContentChange={handleReplyContentChange}
                />
            </div>

            {/* === 中型螢幕兩欄佈局（聊天介面，無 AI 修正）=== */}
            <div className={`hidden lg:grid xl:hidden gap-3 flex-1 min-h-0 ${
                isFirstColumnCollapsed
                    ? 'lg:grid-cols-[56px_1fr]'
                    : 'lg:grid-cols-[250px_1fr]'
            }`}>
                <ConversationListPanel
                    isCollapsed={isFirstColumnCollapsed}
                    conversations={conversations}
                    loading={loading}
                    selectedConversation={selectedConversation}
                    onSelectConversation={handleSelectConversation}
                    onDeleteConversation={handleDeleteConversation}
                    onToggleCollapse={handleToggleFirstColumn}
                />
                <ChatPanel
                    idSuffix="-lg"
                    selectedConversation={selectedConversation}
                    conversationMessages={conversationMessages}
                    conversationLoading={conversationLoading}
                    selectedMessage={selectedMessage}
                    messageDetail={messageDetail}
                    detailLoading={detailLoading}
                    replyContent={replyContent}
                    sending={sending}
                    onSelectMessage={handleSelectMessage}
                    onReplyContentChange={handleReplyContentChange}
                    onSendReply={handleSendReply}
                    onRegenerate={handleRegenerate}
                    onArchive={handleArchive}
                    onFeedbackSubmit={handleFeedbackSubmit}
                />
            </div>

            {/* === 手機版層疊導航 === */}
            <div className="lg:hidden flex-1 min-h-0">
                {mobileView === 'conversations' && (
                    <ConversationListPanel
                        isMobile
                        conversations={conversations}
                        loading={loading}
                        selectedConversation={selectedConversation}
                        onSelectConversation={handleSelectConversation}
                        onDeleteConversation={handleDeleteConversation}
                    />
                )}
                {(mobileView === 'history' || mobileView === 'detail') && (
                    <ChatPanel
                        isMobile
                        idSuffix="-mobile"
                        selectedConversation={selectedConversation}
                        conversationMessages={conversationMessages}
                        conversationLoading={conversationLoading}
                        selectedMessage={selectedMessage}
                        messageDetail={messageDetail}
                        detailLoading={detailLoading}
                        replyContent={replyContent}
                        sending={sending}
                        onSelectMessage={handleSelectMessage}
                        onReplyContentChange={handleReplyContentChange}
                        onSendReply={handleSendReply}
                        onRegenerate={handleRegenerate}
                        onArchive={handleArchive}
                        onBack={handleBackToConversations}
                        onFeedbackSubmit={handleFeedbackSubmit}
                    />
                )}
            </div>
        </div>
    )
}

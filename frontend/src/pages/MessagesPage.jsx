import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Clock, User, Send, RefreshCw, Archive, ChevronRight, ThumbsUp, ThumbsDown, Star, X, Bell, BellOff, Volume2, VolumeX } from 'lucide-react'
import axios from 'axios'
import FeedbackPanel from '../components/FeedbackPanel'
import notificationService from '../services/notificationService'

export default function MessagesPage() {
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
            // 測試音效
            notificationService.playSound()
        }
    }

    // 獲取訊息並檢查新訊息
    const fetchMessagesWithNotification = useCallback(async (showLoading = false) => {
        if (showLoading) setLoading(true)
        try {
            const params = filter === 'all' ? {} : { status: filter }
            const response = await axios.get('/api/messages', { params })
            const newMessages = response.data.messages

            // 首次載入時重置追蹤
            if (isFirstLoad.current) {
                notificationService.resetTracking(newMessages)
                isFirstLoad.current = false
            } else {
                // 檢查新訊息
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
        fetchMessagesWithNotification(true)

        // 設定輪詢（每 10 秒檢查一次新訊息）
        pollInterval.current = setInterval(() => {
            fetchMessagesWithNotification(false)
        }, 10000)

        return () => {
            if (pollInterval.current) {
                clearInterval(pollInterval.current)
            }
        }
    }, [filter, fetchMessagesWithNotification])

    // 清除新訊息計數
    const clearNewMessageCount = () => {
        setNewMessageCount(0)
    }

    const fetchMessages = async () => {
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
    }

    const fetchMessageDetail = async (messageId) => {
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
    }

    const handleSelectMessage = (message) => {
        setSelectedMessage(message)
        fetchMessageDetail(message.id)
    }

    const handleSendReply = async () => {
        if (!replyContent.trim() || !messageDetail) return

        setSending(true)
        try {
            const draftId = messageDetail.drafts?.[0]?.id || null
            await axios.post(`/api/messages/${messageDetail.id}/send`, {
                content: replyContent,
                draft_id: draftId
            })
            alert('回覆已發送！')
            setSelectedMessage(null)
            setMessageDetail(null)
            fetchMessages()
        } catch (error) {
            console.error('發送失敗:', error)
            alert('發送失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setSending(false)
        }
    }

    const handleRegenerate = async () => {
        if (!messageDetail) return

        try {
            await axios.post(`/api/messages/${messageDetail.id}/regenerate`)
            fetchMessageDetail(messageDetail.id)
        } catch (error) {
            console.error('重新生成失敗:', error)
            alert('重新生成失敗')
        }
    }

    const handleArchive = async () => {
        if (!messageDetail) return

        try {
            await axios.post(`/api/messages/${messageDetail.id}/archive`)
            setSelectedMessage(null)
            setMessageDetail(null)
            fetchMessages()
        } catch (error) {
            console.error('封存失敗:', error)
        }
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

    const getSourceIcon = (source) => {
        if (source === 'line_oa') return '💬'
        if (source === 'email') return '📧'
        if (source === 'phone') return '📞'
        return '💭'
    }

    const formatTime = (dateString) => {
        const date = new Date(dateString)
        return date.toLocaleString('zh-TW', {
            month: 'numeric',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-3">
                        <span>訊息管理</span>
                        {newMessageCount > 0 && (
                            <span className="px-2 py-1 text-sm bg-red-500 text-white rounded-full animate-pulse">
                                {newMessageCount} 則新訊息
                            </span>
                        )}
                    </h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        審核 AI 草稿，發送回覆給客戶
                    </p>
                </div>
                <div className="flex items-center space-x-2">
                    {/* 音效開關 */}
                    <button
                        onClick={toggleSound}
                        className={`p-2 rounded-lg border transition-colors ${
                            soundEnabled
                                ? 'bg-green-50 border-green-200 text-green-600 dark:bg-green-900/30 dark:border-green-700 dark:text-green-400'
                                : 'bg-gray-50 border-gray-200 text-gray-400 dark:bg-gray-800 dark:border-gray-700'
                        }`}
                        title={soundEnabled ? '音效已開啟' : '音效已關閉'}
                    >
                        {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                    </button>

                    {/* 通知開關 */}
                    <button
                        onClick={toggleNotification}
                        className={`p-2 rounded-lg border transition-colors ${
                            notificationEnabled
                                ? 'bg-blue-50 border-blue-200 text-blue-600 dark:bg-blue-900/30 dark:border-blue-700 dark:text-blue-400'
                                : 'bg-gray-50 border-gray-200 text-gray-400 dark:bg-gray-800 dark:border-gray-700'
                        }`}
                        title={notificationEnabled ? '通知已開啟' : '點擊開啟通知'}
                    >
                        {notificationEnabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                    </button>

                    {/* 重新整理 */}
                    <button
                        onClick={() => {
                            fetchMessages()
                            clearNewMessageCount()
                        }}
                        className="flex items-center space-x-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        <span>重新整理</span>
                    </button>
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex space-x-2">
                {[
                    { id: 'pending', label: '待處理' },
                    { id: 'drafted', label: '已生成草稿' },
                    { id: 'sent', label: '已發送' },
                    { id: 'all', label: '全部' }
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setFilter(tab.id)}
                        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${filter === tab.id
                            ? 'bg-blue-600 text-white'
                            : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Message List */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white">訊息列表</h3>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : messages.length === 0 ? (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                            目前沒有訊息
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
                            {messages.map((message) => (
                                <button
                                    key={message.id}
                                    onClick={() => handleSelectMessage(message)}
                                    className={`w-full p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${selectedMessage?.id === message.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                        }`}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center space-x-2 mb-1">
                                                <span>{getSourceIcon(message.source)}</span>
                                                <span className="font-medium text-gray-900 dark:text-white truncate">
                                                    {message.sender_name}
                                                </span>
                                                {getStatusBadge(message.status)}
                                            </div>
                                            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                                                {message.content}
                                            </p>
                                            <div className="flex items-center space-x-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
                                                <Clock className="w-3 h-3" />
                                                <span>{formatTime(message.created_at)}</span>
                                            </div>
                                        </div>
                                        <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" />
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Message Detail */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900 dark:text-white">訊息詳情</h3>
                        {selectedMessage && (
                            <button
                                onClick={() => {
                                    setSelectedMessage(null)
                                    setMessageDetail(null)
                                }}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        )}
                    </div>

                    {!selectedMessage ? (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>選擇一則訊息查看詳情</p>
                        </div>
                    ) : detailLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : messageDetail ? (
                        <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
                            {/* Original Message */}
                            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                                <div className="flex items-center space-x-2 mb-2">
                                    <User className="w-4 h-4 text-gray-500" />
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {messageDetail.sender_name}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                        {formatTime(messageDetail.created_at)}
                                    </span>
                                </div>
                                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                    {messageDetail.content}
                                </p>
                            </div>

                            {/* AI Draft */}
                            {messageDetail.drafts && messageDetail.drafts.length > 0 && (
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <h4 className="font-medium text-gray-900 dark:text-white flex items-center space-x-2">
                                            <span>🤖</span>
                                            <span>AI 草稿</span>
                                        </h4>
                                        <button
                                            onClick={handleRegenerate}
                                            className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
                                        >
                                            <RefreshCw className="w-4 h-4" />
                                            <span>重新生成</span>
                                        </button>
                                    </div>

                                    {/* Draft Strategy */}
                                    {messageDetail.drafts[0].strategy && (
                                        <div className="text-sm text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                                            <span className="font-medium">策略：</span>
                                            {messageDetail.drafts[0].strategy}
                                        </div>
                                    )}

                                    {/* Editable Reply */}
                                    <textarea
                                        value={replyContent}
                                        onChange={(e) => setReplyContent(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                        rows={6}
                                        placeholder="編輯回覆內容..."
                                    />

                                    {/* Feedback Panel */}
                                    <FeedbackPanel
                                        draftId={messageDetail.drafts[0].id}
                                        initialFeedback={{
                                            is_good: messageDetail.drafts[0].is_good,
                                            rating: messageDetail.drafts[0].rating,
                                            feedback_reason: messageDetail.drafts[0].feedback_reason
                                        }}
                                        onFeedbackSubmit={() => fetchMessageDetail(messageDetail.id)}
                                    />
                                </div>
                            )}

                            {/* Action Buttons */}
                            {messageDetail.status !== 'sent' && messageDetail.status !== 'archived' && (
                                <div className="flex space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                                    <button
                                        onClick={handleSendReply}
                                        disabled={sending || !replyContent.trim()}
                                        className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-colors ${sending || !replyContent.trim()
                                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                                            }`}
                                    >
                                        {sending ? (
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <Send className="w-4 h-4" />
                                        )}
                                        <span>{sending ? '發送中...' : '發送回覆'}</span>
                                    </button>
                                    <button
                                        onClick={handleArchive}
                                        className="flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                    >
                                        <Archive className="w-4 h-4" />
                                        <span>封存</span>
                                    </button>
                                </div>
                            )}

                            {/* Already Sent */}
                            {messageDetail.status === 'sent' && (
                                <div className="text-center py-4 text-green-600 dark:text-green-400">
                                    ✓ 此訊息已發送回覆
                                </div>
                            )}
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    )
}

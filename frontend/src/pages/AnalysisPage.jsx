import { useState, useEffect } from 'react'
import { BarChart3, AlertCircle, Briefcase, AlertTriangle, MessageSquare, TrendingUp, Users, RefreshCw, Calendar } from 'lucide-react'
import axios from 'axios'

export default function AnalysisPage() {
    const [report, setReport] = useState(null)
    const [loading, setLoading] = useState(true)
    const [period, setPeriod] = useState('7d')

    useEffect(() => {
        fetchReport()
    }, [period])

    const fetchReport = async () => {
        setLoading(true)
        try {
            const response = await axios.get('/api/analysis/report')
            setReport(response.data)
        } catch (error) {
            console.error('獲取分析報告失敗:', error)
        } finally {
            setLoading(false)
        }
    }

    const formatDate = (dateString) => {
        if (!dateString) return ''
        return new Date(dateString).toLocaleString('zh-TW', {
            month: 'numeric',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-3">
                            <BarChart3 className="w-8 h-8" />
                            <span>分析報告</span>
                        </h2>
                        <p className="mt-2 text-gray-600 dark:text-gray-400">訊息優先級分析與趨勢統計</p>
                    </div>
                </div>
                <div className="flex items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>
        )
    }

    const summary = report?.summary

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-3">
                        <BarChart3 className="w-8 h-8" />
                        <span>分析報告</span>
                    </h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        訊息優先級分析與趨勢統計
                        {report?.generated_at && (
                            <span className="ml-2 text-xs">（更新於 {formatDate(report.generated_at)}）</span>
                        )}
                    </p>
                </div>
                <button
                    onClick={fetchReport}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    <span>重新分析</span>
                </button>
            </div>

            {/* 行動建議 */}
            {summary?.action_items && summary.action_items.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
                    <h3 className="font-semibold text-amber-800 dark:text-amber-300 mb-2">建議行動</h3>
                    <ul className="space-y-2">
                        {summary.action_items.map((item, idx) => (
                            <li key={idx} className="text-sm text-amber-700 dark:text-amber-400 flex items-start space-x-2">
                                <span className="mt-0.5">•</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* 統計卡片 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                        </div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">緊急訊息</span>
                    </div>
                    <p className="text-3xl font-bold text-red-600 dark:text-red-400">{summary?.urgent_count || 0}</p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                            <Briefcase className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">業務相關</span>
                    </div>
                    <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{summary?.business_count || 0}</p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                        </div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">問題反映</span>
                    </div>
                    <p className="text-3xl font-bold text-orange-600 dark:text-orange-400">{summary?.issue_count || 0}</p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <div className="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                            <MessageSquare className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        </div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">總訊息數</span>
                    </div>
                    <p className="text-3xl font-bold text-gray-700 dark:text-gray-300">{summary?.total_messages || 0}</p>
                </div>
            </div>

            {/* 兩欄佈局：重要訊息 + 每日趨勢 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 重要訊息列表 */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                            <AlertCircle className="w-5 h-5 text-red-500" />
                            <span>需要關注的訊息</span>
                        </h3>
                    </div>
                    <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-80 overflow-y-auto">
                        {[
                            ...(summary?.urgent_messages || []),
                            ...(summary?.business_messages || []),
                            ...(summary?.issue_messages || [])
                        ].length === 0 ? (
                            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                                目前沒有需要特別關注的訊息
                            </div>
                        ) : (
                            [...(summary?.urgent_messages || []),
                             ...(summary?.business_messages || []),
                             ...(summary?.issue_messages || [])]
                            .map((msg) => (
                                <div key={msg.id} className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-gray-900 dark:text-white">
                                            {msg.sender_name}
                                        </span>
                                        <span className={`px-2 py-0.5 text-xs rounded ${
                                            msg.priority_level === 'urgent'
                                                ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                : msg.priority_level === 'business'
                                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                                : 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'
                                        }`}>
                                            {msg.priority_level === 'urgent' ? '緊急' :
                                             msg.priority_level === 'business' ? '業務' : '問題'}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                        {msg.content}
                                    </p>
                                    {msg.priority_reason && (
                                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                            {msg.priority_reason}
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* 每日趨勢 */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                            <TrendingUp className="w-5 h-5 text-blue-500" />
                            <span>每日趨勢（近 7 天）</span>
                        </h3>
                    </div>
                    <div className="p-4">
                        {/* 簡單的柱狀圖 */}
                        <div className="space-y-3">
                            {report?.daily_trends?.map((day, idx) => {
                                const maxCount = Math.max(...report.daily_trends.map(d => d.message_count), 1)
                                const barWidth = (day.message_count / maxCount) * 100

                                return (
                                    <div key={idx} className="flex items-center space-x-3">
                                        <span className="w-12 text-xs text-gray-500 dark:text-gray-400 text-right">
                                            {day.date}
                                        </span>
                                        <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                                                style={{ width: `${Math.max(barWidth, 10)}%` }}
                                            >
                                                <span className="text-xs text-white font-medium">
                                                    {day.message_count}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-1 w-20">
                                            {day.urgent_count > 0 && (
                                                <span className="text-xs text-red-500">{day.urgent_count}🔴</span>
                                            )}
                                            {day.business_count > 0 && (
                                                <span className="text-xs text-blue-500">{day.business_count}💼</span>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* 活躍發送者 */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                        <Users className="w-5 h-5 text-purple-500" />
                        <span>活躍發送者（近 7 天）</span>
                    </h3>
                </div>
                <div className="p-4">
                    <div className="flex flex-wrap gap-2">
                        {report?.top_senders?.map((sender, idx) => (
                            <div
                                key={idx}
                                className="flex items-center space-x-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg"
                            >
                                <span className="text-sm font-medium text-gray-900 dark:text-white">
                                    {sender.name}
                                </span>
                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                    {sender.count} 則
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* 統計細節 */}
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">統計細節</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <span className="text-gray-500 dark:text-gray-400">待處理訊息</span>
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary?.pending_count || 0}</p>
                    </div>
                    <div>
                        <span className="text-gray-500 dark:text-gray-400">一般諮詢</span>
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary?.general_count || 0}</p>
                    </div>
                    <div>
                        <span className="text-gray-500 dark:text-gray-400">低優先級</span>
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary?.low_priority_count || 0}</p>
                    </div>
                    <div>
                        <span className="text-gray-500 dark:text-gray-400">分析時間範圍</span>
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary?.period || '--'}</p>
                    </div>
                </div>
            </div>
        </div>
    )
}

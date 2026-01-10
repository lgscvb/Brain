import { useState, useEffect } from 'react'
import { Activity, MessageSquare, TrendingUp, Clock, AlertCircle, Briefcase, AlertTriangle, ChevronRight } from 'lucide-react'
import axios from 'axios'
import UsagePanel from '../components/UsagePanel'

export default function DashboardPage({ onNavigate }) {
    const [stats, setStats] = useState(null)
    const [settings, setSettings] = useState(null)
    const [loading, setLoading] = useState(true)
    const [analysis, setAnalysis] = useState(null)
    const [analysisLoading, setAnalysisLoading] = useState(true)

    useEffect(() => {
        fetchStats()
        fetchSettings()
        fetchAnalysis()
        const interval = setInterval(fetchStats, 10000) // 每 10 秒更新
        return () => clearInterval(interval)
    }, [])

    const fetchAnalysis = async () => {
        try {
            const response = await axios.get('/api/analysis/summary?period=24h')
            setAnalysis(response.data)
        } catch (error) {
            console.error('獲取分析摘要失敗:', error)
        } finally {
            setAnalysisLoading(false)
        }
    }

    const fetchStats = async () => {
        try {
            const response = await axios.get('/api/stats')
            setStats(response.data)
            setLoading(false)
        } catch (error) {
            console.error('獲取統計失敗:', error)
            setLoading(false)
        }
    }

    const fetchSettings = async () => {
        try {
            const response = await axios.get('/api/settings')
            setSettings(response.data)
        } catch (error) {
            console.error('獲取設定失敗:', error)
        }
    }

    // 從模型 ID 取得顯示名稱
    const getModelDisplayName = (modelId) => {
        if (!modelId) return '未設定'
        // 取最後一段作為名稱，例如 "anthropic/claude-sonnet-4.5" -> "claude-sonnet-4.5"
        const parts = modelId.split('/')
        return parts[parts.length - 1]
    }

    const statCards = stats ? [
        {
            title: '待處理訊息',
            value: stats.pending_count,
            icon: MessageSquare,
            color: 'blue',
            unit: '則'
        },
        {
            title: '今日已發送',
            value: stats.today_sent,
            icon: Activity,
            color: 'green',
            unit: '則'
        },
        {
            title: 'AI 採用率',
            value: `${(100 - stats.modification_rate).toFixed(1)}%`,
            icon: TrendingUp,
            color: 'purple',
            unit: ''
        },
        {
            title: '平均回覆時間',
            value: stats.avg_response_time || '--',
            icon: Clock,
            color: 'orange',
            unit: stats.avg_response_time ? '秒' : ''
        },
    ] : []

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white">儀表板</h2>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                    系統運作狀態總覽
                </p>
            </div>

            {/* Stats Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {statCards.map((stat, index) => {
                        const Icon = stat.icon
                        const colorClasses = {
                            blue: 'from-blue-500 to-blue-600',
                            green: 'from-green-500 to-green-600',
                            purple: 'from-purple-500 to-purple-600',
                            orange: 'from-orange-500 to-orange-600',
                        }

                        return (
                            <div
                                key={index}
                                className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <div className={`w-12 h-12 bg-gradient-to-br ${colorClasses[stat.color]} rounded-xl flex items-center justify-center`}>
                                        <Icon className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                                        {stat.title}
                                    </p>
                                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                        {stat.value}
                                        {stat.unit && <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">{stat.unit}</span>}
                                    </p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* 訊息分析摘要卡片 - 方案 A */}
            {analysisLoading ? (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <div className="animate-pulse flex space-x-4">
                        <div className="flex-1 space-y-3">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                        </div>
                    </div>
                </div>
            ) : analysis && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                            <span>📋</span>
                            <span>訊息分析摘要</span>
                            <span className="text-sm font-normal text-gray-500">（{analysis.period}）</span>
                        </h3>
                        <button
                            onClick={() => onNavigate && onNavigate('analysis')}
                            className="text-sm text-blue-600 hover:text-blue-700 flex items-center space-x-1"
                        >
                            <span>完整報告</span>
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>

                    {/* 行動建議 */}
                    {analysis.action_items && analysis.action_items.length > 0 && (
                        <div className="mb-4 space-y-2">
                            {analysis.action_items.map((item, idx) => (
                                <div key={idx} className="text-sm bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 px-3 py-2 rounded-lg">
                                    {item}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* 分類統計 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
                            <div className="flex items-center space-x-2 mb-1">
                                <AlertCircle className="w-4 h-4 text-red-500" />
                                <span className="text-xs text-red-600 dark:text-red-400">緊急</span>
                            </div>
                            <p className="text-2xl font-bold text-red-700 dark:text-red-300">{analysis.urgent_count}</p>
                        </div>
                        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                            <div className="flex items-center space-x-2 mb-1">
                                <Briefcase className="w-4 h-4 text-blue-500" />
                                <span className="text-xs text-blue-600 dark:text-blue-400">業務</span>
                            </div>
                            <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{analysis.business_count}</p>
                        </div>
                        <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3">
                            <div className="flex items-center space-x-2 mb-1">
                                <AlertTriangle className="w-4 h-4 text-orange-500" />
                                <span className="text-xs text-orange-600 dark:text-orange-400">問題</span>
                            </div>
                            <p className="text-2xl font-bold text-orange-700 dark:text-orange-300">{analysis.issue_count}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                            <div className="flex items-center space-x-2 mb-1">
                                <MessageSquare className="w-4 h-4 text-gray-500" />
                                <span className="text-xs text-gray-600 dark:text-gray-400">一般</span>
                            </div>
                            <p className="text-2xl font-bold text-gray-700 dark:text-gray-300">{analysis.general_count}</p>
                        </div>
                    </div>

                    {/* 重要訊息預覽 */}
                    {(analysis.urgent_messages?.length > 0 || analysis.business_messages?.length > 0) && (
                        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">需要關注的訊息</h4>
                            <div className="space-y-2 max-h-40 overflow-y-auto">
                                {[...analysis.urgent_messages, ...analysis.business_messages].slice(0, 5).map((msg) => (
                                    <div
                                        key={msg.id}
                                        className="flex items-start space-x-2 text-sm bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                                        onClick={() => onNavigate && onNavigate('messages')}
                                    >
                                        <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-xs ${
                                            msg.priority_level === 'urgent'
                                                ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                        }`}>
                                            {msg.priority_level === 'urgent' ? '緊急' : '業務'}
                                        </span>
                                        <span className="font-medium text-gray-900 dark:text-white truncate flex-shrink-0 w-20">
                                            {msg.sender_name}
                                        </span>
                                        <span className="text-gray-600 dark:text-gray-400 truncate">
                                            {msg.content}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* API Usage Panel */}
            <UsagePanel />

            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">快速動作</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <button
                        onClick={() => onNavigate && onNavigate('messages')}
                        className="flex items-center justify-center space-x-2 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                    >
                        <MessageSquare className="w-5 h-5" />
                        <span>查看待處理訊息</span>
                    </button>

                    <a
                        href="/api/docs"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center space-x-2 px-4 py-3 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
                    >
                        <Activity className="w-5 h-5" />
                        <span>API 文件</span>
                    </a>

                    <button
                        onClick={() => onNavigate && onNavigate('feedback')}
                        className="flex items-center justify-center space-x-2 px-4 py-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
                    >
                        <TrendingUp className="w-5 h-5" />
                        <span>AI 回饋統計</span>
                    </button>
                </div>
            </div>

            {/* System Info */}
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">系統資訊</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">版本：</span>
                        <span className="text-gray-900 dark:text-white font-medium">v0.1.0</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">後端 API：</span>
                        <span className="text-green-600 dark:text-green-400 font-medium">● 運行中</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">資料庫：</span>
                        <span className="text-gray-900 dark:text-white font-medium">SQLite</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">AI 模式：</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                            {settings?.ENABLE_ROUTING ? 'LLM Routing' : '單一模型'}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">🧠 複雜任務：</span>
                        <span className="text-gray-900 dark:text-white font-medium text-xs">
                            {getModelDisplayName(settings?.MODEL_SMART)}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">⚡ 簡單任務：</span>
                        <span className="text-gray-900 dark:text-white font-medium text-xs">
                            {getModelDisplayName(settings?.MODEL_FAST)}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    )
}

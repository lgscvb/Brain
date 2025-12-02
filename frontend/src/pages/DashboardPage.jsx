import { useState, useEffect } from 'react'
import { Activity, MessageSquare, TrendingUp, Clock } from 'lucide-react'
import axios from 'axios'
import UsagePanel from '../components/UsagePanel'

export default function DashboardPage({ onNavigate }) {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchStats()
        const interval = setInterval(fetchStats, 10000) // 每 10 秒更新
        return () => clearInterval(interval)
    }, [])

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
                        <span className="text-gray-900 dark:text-white font-medium">LLM Routing</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">🧠 複雜任務：</span>
                        <span className="text-gray-900 dark:text-white font-medium text-xs">Claude Sonnet 4.5</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">⚡ 簡單任務：</span>
                        <span className="text-gray-900 dark:text-white font-medium text-xs">Gemini Flash</span>
                    </div>
                </div>
            </div>
        </div>
    )
}

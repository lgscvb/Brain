import { useState, useEffect } from 'react'
import { DollarSign, Zap, AlertTriangle, TrendingUp, RefreshCw, X } from 'lucide-react'
import axios from 'axios'

export default function UsagePanel() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [showErrorModal, setShowErrorModal] = useState(false)
    const [errorLogs, setErrorLogs] = useState([])
    const [loadingErrors, setLoadingErrors] = useState(false)

    useEffect(() => {
        fetchUsageStats()
    }, [])

    const fetchUsageStats = async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await axios.get('/api/usage/stats')
            setStats(response.data)
        } catch (err) {
            console.error('Failed to fetch usage stats:', err)
            setError('Unable to load usage data')
        } finally {
            setLoading(false)
        }
    }

    const fetchErrorLogs = async () => {
        setLoadingErrors(true)
        try {
            const response = await axios.get('/api/usage/errors')
            setErrorLogs(response.data.errors || [])
            setShowErrorModal(true)
        } catch (err) {
            console.error('Failed to fetch error logs:', err)
        } finally {
            setLoadingErrors(false)
        }
    }

    const handleCheckLogs = () => {
        if ((stats?.total?.errors || 0) > 0) {
            fetchErrorLogs()
        }
    }

    const formatTokens = (tokens) => {
        if (tokens >= 1000000) {
            return `${(tokens / 1000000).toFixed(2)}M`
        } else if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(1)}K`
        }
        return tokens.toString()
    }

    const formatCost = (cost) => {
        if (cost < 0.01) {
            return `$${cost.toFixed(4)}`
        }
        return `$${cost.toFixed(2)}`
    }

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-center py-8 text-gray-500">
                    <AlertTriangle className="w-5 h-5 mr-2" />
                    <span>{error}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center">
                        <Zap className="w-4 h-4 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">API 用量監控</h3>
                </div>
                <button
                    onClick={fetchUsageStats}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className="w-4 h-4" />
                </button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {/* Today's Cost */}
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
                        <span className="text-sm text-green-700 dark:text-green-300">Today</span>
                    </div>
                    <p className="text-2xl font-bold text-green-800 dark:text-green-200">
                        {formatCost(stats?.today?.estimated_cost_usd || 0)}
                    </p>
                    <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                        {formatTokens(stats?.today?.total_tokens || 0)} tokens
                    </p>
                </div>

                {/* Monthly Cost */}
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        <span className="text-sm text-blue-700 dark:text-blue-300">30 Days</span>
                    </div>
                    <p className="text-2xl font-bold text-blue-800 dark:text-blue-200">
                        {formatCost(stats?.total?.estimated_cost_usd || 0)}
                    </p>
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                        {formatTokens(stats?.total?.total_tokens || 0)} tokens
                    </p>
                </div>

                {/* API Calls */}
                <div className="bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-900/20 dark:to-violet-900/20 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        <span className="text-sm text-purple-700 dark:text-purple-300">Calls</span>
                    </div>
                    <p className="text-2xl font-bold text-purple-800 dark:text-purple-200">
                        {stats?.total?.api_calls || 0}
                    </p>
                    <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                        {stats?.today?.api_calls || 0} today
                    </p>
                </div>

                {/* Errors */}
                <div className={`rounded-lg p-4 ${(stats?.total?.errors || 0) > 0
                    ? 'bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20'
                    : 'bg-gradient-to-br from-gray-50 to-slate-50 dark:from-gray-700/20 dark:to-slate-700/20'
                    }`}>
                    <div className="flex items-center space-x-2 mb-2">
                        <AlertTriangle className={`w-4 h-4 ${(stats?.total?.errors || 0) > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`} />
                        <span className={`text-sm ${(stats?.total?.errors || 0) > 0 ? 'text-red-700 dark:text-red-300' : 'text-gray-600 dark:text-gray-400'}`}>Errors</span>
                    </div>
                    <p className={`text-2xl font-bold ${(stats?.total?.errors || 0) > 0 ? 'text-red-800 dark:text-red-200' : 'text-gray-700 dark:text-gray-300'}`}>
                        {stats?.total?.errors || 0}
                    </p>
                    {(stats?.total?.errors || 0) > 0 ? (
                        <button
                            onClick={handleCheckLogs}
                            disabled={loadingErrors}
                            className="text-xs mt-1 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline cursor-pointer disabled:opacity-50"
                        >
                            {loadingErrors ? 'Loading...' : 'Check logs'}
                        </button>
                    ) : (
                        <p className="text-xs mt-1 text-gray-500">All good</p>
                    )}
                </div>
            </div>

            {/* Daily Usage Chart (Simple Bar) */}
            {stats?.daily && stats.daily.length > 0 && (
                <div className="mt-6">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">7 Days Usage</h4>
                    <div className="flex items-end justify-between h-20 gap-1">
                        {stats.daily.map((day, index) => {
                            const maxTokens = Math.max(...stats.daily.map(d => d.tokens || 1))
                            const height = ((day.tokens || 0) / maxTokens) * 100
                            return (
                                <div key={index} className="flex-1 flex flex-col items-center">
                                    <div
                                        className="w-full bg-gradient-to-t from-blue-500 to-indigo-500 rounded-t transition-all duration-300"
                                        style={{ height: `${Math.max(height, 4)}%` }}
                                        title={`${day.date}: ${formatTokens(day.tokens)} tokens, ${formatCost(day.cost)}`}
                                    />
                                    <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">{day.date}</span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Token Breakdown */}
            {stats?.total && (
                <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-500 dark:text-gray-400">Input Tokens</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                            {formatTokens(stats.total.input_tokens || 0)}
                        </span>
                    </div>
                    <div className="flex justify-between text-sm mt-2">
                        <span className="text-gray-500 dark:text-gray-400">Output Tokens</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                            {formatTokens(stats.total.output_tokens || 0)}
                        </span>
                    </div>
                </div>
            )}

            {/* Error Logs Modal */}
            {showErrorModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <AlertTriangle className="w-5 h-5 text-red-500" />
                                錯誤日誌 ({errorLogs.length})
                            </h3>
                            <button
                                onClick={() => setShowErrorModal(false)}
                                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-4 overflow-y-auto max-h-[60vh]">
                            {errorLogs.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">沒有錯誤記錄</p>
                            ) : (
                                <div className="space-y-3">
                                    {errorLogs.map((log) => (
                                        <div
                                            key={log.id}
                                            className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3"
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-xs font-medium text-red-800 dark:text-red-300 bg-red-100 dark:bg-red-800/30 px-2 py-0.5 rounded">
                                                    {log.operation}
                                                </span>
                                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                                    {new Date(log.created_at).toLocaleString('zh-TW')}
                                                </span>
                                            </div>
                                            <p className="text-sm text-red-700 dark:text-red-300 font-mono break-all">
                                                {log.error_message || '未知錯誤'}
                                            </p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                {log.provider} / {log.model}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

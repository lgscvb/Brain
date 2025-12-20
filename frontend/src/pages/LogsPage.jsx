import { useState, useEffect, useId } from 'react'
import { FileText, Trash2, RefreshCw, Search, Filter, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import axios from 'axios'

export default function LogsPage() {
    const uniqueId = useId()
    const [logs, setLogs] = useState([])
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(false)
    const [logType, setLogType] = useState('main')
    const [levelFilter, setLevelFilter] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [autoRefresh, setAutoRefresh] = useState(false)

    useEffect(() => {
        fetchLogs()
        fetchStats()
    }, [logType, levelFilter])

    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(fetchLogs, 5000)
            return () => clearInterval(interval)
        }
    }, [autoRefresh, logType, levelFilter, searchQuery])

    const fetchLogs = async () => {
        setLoading(true)
        try {
            const params = {
                log_type: logType,
                limit: 100,
            }
            if (levelFilter) params.level = levelFilter
            if (searchQuery) params.search = searchQuery

            const response = await axios.get('/api/logs', { params })
            setLogs(response.data.logs)
        } catch (error) {
            console.error('獲取日誌失敗:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchStats = async () => {
        try {
            const response = await axios.get('/api/logs/stats')
            setStats(response.data)
        } catch (error) {
            console.error('獲取統計失敗:', error)
        }
    }

    const handleClearLogs = async () => {
        if (!confirm(`確定要清空 ${logType === 'main' ? '主要' : '錯誤'} 日誌嗎？`)) {
            return
        }

        try {
            await axios.delete(`/api/logs/clear?log_type=${logType}`)
            fetchLogs()
            fetchStats()
        } catch (error) {
            console.error('清空日誌失敗:', error)
        }
    }

    const handleSearch = () => {
        fetchLogs()
    }

    const getLevelIcon = (level) => {
        switch (level) {
            case 'ERROR':
                return <AlertCircle className="w-4 h-4 text-red-500" />
            case 'WARNING':
                return <AlertTriangle className="w-4 h-4 text-yellow-500" />
            case 'INFO':
                return <Info className="w-4 h-4 text-blue-500" />
            default:
                return <Info className="w-4 h-4 text-gray-500" />
        }
    }

    const getLevelColor = (level) => {
        switch (level) {
            case 'ERROR':
                return 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
            case 'WARNING':
                return 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200'
            case 'INFO':
                return 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
            default:
                return 'bg-gray-50 dark:bg-gray-900/20 text-gray-800 dark:text-gray-200'
        }
    }

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">系統日誌</h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        查看系統運作記錄與錯誤訊息
                    </p>
                </div>
                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => setAutoRefresh(!autoRefresh)}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${autoRefresh
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            }`}
                    >
                        <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
                        <span>{autoRefresh ? '自動更新中' : '自動更新'}</span>
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">主要日誌</p>
                                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                    {stats.main_log.lines || 0} 行
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {formatFileSize(stats.main_log.size)}
                                </p>
                            </div>
                            <FileText className="w-8 h-8 text-blue-500" />
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">錯誤日誌</p>
                                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                    {stats.error_log.lines || 0} 行
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {formatFileSize(stats.error_log.size)}
                                </p>
                            </div>
                            <AlertCircle className="w-8 h-8 text-red-500" />
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Log Type */}
                    <div>
                        <label htmlFor={`${uniqueId}-log-type`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            日誌類型
                        </label>
                        <select
                            id={`${uniqueId}-log-type`}
                            name={`${uniqueId}-log-type`}
                            value={logType}
                            onChange={(e) => setLogType(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                            <option value="main">主要日誌</option>
                            <option value="error">錯誤日誌</option>
                        </select>
                    </div>

                    {/* Level Filter */}
                    <div>
                        <label htmlFor={`${uniqueId}-level-filter`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            等級篩選
                        </label>
                        <select
                            id={`${uniqueId}-level-filter`}
                            name={`${uniqueId}-level-filter`}
                            value={levelFilter}
                            onChange={(e) => setLevelFilter(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                            <option value="">全部</option>
                            <option value="INFO">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                        </select>
                    </div>

                    {/* Search */}
                    <div className="md:col-span-2">
                        <label htmlFor={`${uniqueId}-search`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            搜尋關鍵字
                        </label>
                        <div className="flex space-x-2">
                            <input
                                id={`${uniqueId}-search`}
                                name={`${uniqueId}-search`}
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                                placeholder="輸入關鍵字搜尋..."
                                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <button
                                onClick={handleSearch}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                            >
                                <Search className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-2 mt-4">
                    <button
                        onClick={fetchLogs}
                        disabled={loading}
                        className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        <span>重新整理</span>
                    </button>
                    <button
                        onClick={handleClearLogs}
                        className="flex items-center space-x-2 px-4 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900/20 dark:hover:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg transition-colors"
                    >
                        <Trash2 className="w-4 h-4" />
                        <span>清空日誌</span>
                    </button>
                </div>
            </div>

            {/* Logs List */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        日誌記錄 ({logs.length})
                    </h3>
                </div>

                <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
                        </div>
                    ) : logs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                            <FileText className="w-12 h-12 mb-2" />
                            <p>沒有日誌記錄</p>
                        </div>
                    ) : (
                        logs.map((log, index) => (
                            <div
                                key={index}
                                className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50transition-colors"
                            >
                                <div className="flex items-start space-x-3">
                                    <div className="flex-shrink-0 mt-1">
                                        {getLevelIcon(log.level)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColor(log.level)}`}>
                                                {log.level}
                                            </span>
                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                                {log.timestamp}
                                            </span>
                                            <span className="text-xs text-gray-400 dark:text-gray-500">
                                                {log.logger}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-900 dark:text-white font-mono break-all">
                                            {log.message}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}

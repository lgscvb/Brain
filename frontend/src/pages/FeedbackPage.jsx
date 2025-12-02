import { useState, useEffect } from 'react'
import { ThumbsUp, ThumbsDown, Star, TrendingUp, BarChart3, Download } from 'lucide-react'
import axios from 'axios'

/**
 * FeedbackPage - AI 回饋統計頁面
 *
 * 顯示所有 AI 草稿的回饋統計，用於追蹤 AI 品質和改進方向。
 */
export default function FeedbackPage() {
    const [stats, setStats] = useState(null)
    const [feedbacks, setFeedbacks] = useState([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('all') // all, positive, negative

    useEffect(() => {
        fetchData()
    }, [filter])

    const fetchData = async () => {
        setLoading(true)
        try {
            // 獲取統計資料
            const statsResponse = await axios.get('/api/feedback/stats')
            setStats(statsResponse.data)

            // 獲取回饋列表
            const params = {}
            if (filter === 'positive') params.is_good = true
            if (filter === 'negative') params.is_good = false

            const listResponse = await axios.get('/api/feedback/list', { params })
            setFeedbacks(listResponse.data.feedbacks)
        } catch (error) {
            console.error('獲取回饋資料失敗:', error)
        } finally {
            setLoading(false)
        }
    }

    const exportTrainingData = async () => {
        try {
            const response = await axios.get('/api/feedback/training-data')
            const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `training-data-${new Date().toISOString().slice(0, 10)}.json`
            a.click()
            URL.revokeObjectURL(url)
        } catch (error) {
            console.error('匯出失敗:', error)
            alert('匯出失敗')
        }
    }

    const getRatingColor = (rating) => {
        if (rating >= 4) return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30'
        if (rating >= 3) return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30'
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">AI 回饋管理</h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        追蹤 AI 草稿品質，收集改進回饋
                    </p>
                </div>
                <button
                    onClick={exportTrainingData}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                    <Download className="w-4 h-4" />
                    <span>匯出訓練資料</span>
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <>
                    {/* Stats Cards */}
                    {stats && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            {/* 總回饋數 */}
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                                        <BarChart3 className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">總回饋數</p>
                                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                    {stats.total_feedbacks}
                                    <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">筆</span>
                                </p>
                            </div>

                            {/* 正面回饋 */}
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center">
                                        <ThumbsUp className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">正面回饋</p>
                                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                    {stats.positive_count}
                                    <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">筆</span>
                                </p>
                            </div>

                            {/* 負面回饋 */}
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                                        <ThumbsDown className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">負面回饋</p>
                                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                    {stats.negative_count}
                                    <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">筆</span>
                                </p>
                            </div>

                            {/* 平均評分 */}
                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center">
                                        <Star className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">平均評分</p>
                                <p className="text-3xl font-bold text-gray-900 dark:text-white">
                                    {stats.avg_rating || '--'}
                                    <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">/ 5</span>
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Rating Distribution */}
                    {stats && (
                        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">評分分布</h3>
                            <div className="space-y-3">
                                {[5, 4, 3, 2, 1].map((star) => {
                                    const count = stats.rating_distribution[star] || 0
                                    const total = Object.values(stats.rating_distribution).reduce((a, b) => a + b, 0)
                                    const percentage = total > 0 ? (count / total) * 100 : 0

                                    return (
                                        <div key={star} className="flex items-center space-x-3">
                                            <div className="flex items-center space-x-1 w-20">
                                                <span className="text-sm text-gray-600 dark:text-gray-400">{star}</span>
                                                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                                            </div>
                                            <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-yellow-400 rounded-full transition-all duration-500"
                                                    style={{ width: `${percentage}%` }}
                                                />
                                            </div>
                                            <span className="text-sm text-gray-500 dark:text-gray-400 w-16 text-right">
                                                {count} 筆
                                            </span>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    {/* Feedback List */}
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">回饋列表</h3>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setFilter('all')}
                                        className={`px-3 py-1 text-sm rounded-lg transition-colors ${filter === 'all'
                                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                    >
                                        全部
                                    </button>
                                    <button
                                        onClick={() => setFilter('positive')}
                                        className={`px-3 py-1 text-sm rounded-lg transition-colors ${filter === 'positive'
                                                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                    >
                                        正面
                                    </button>
                                    <button
                                        onClick={() => setFilter('negative')}
                                        className={`px-3 py-1 text-sm rounded-lg transition-colors ${filter === 'negative'
                                                ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                    >
                                        負面
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                            {feedbacks.length === 0 ? (
                                <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                                    目前沒有回饋資料
                                </div>
                            ) : (
                                feedbacks.map((feedback) => (
                                    <div key={feedback.draft_id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center space-x-3 mb-2">
                                                    {/* Good/Bad indicator */}
                                                    {feedback.is_good !== null && (
                                                        <span className={`flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium ${feedback.is_good
                                                                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                                : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                            }`}>
                                                            {feedback.is_good ? (
                                                                <><ThumbsUp className="w-3 h-3" /><span>好</span></>
                                                            ) : (
                                                                <><ThumbsDown className="w-3 h-3" /><span>不好</span></>
                                                            )}
                                                        </span>
                                                    )}

                                                    {/* Rating */}
                                                    {feedback.rating && (
                                                        <span className={`flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium ${getRatingColor(feedback.rating)}`}>
                                                            <Star className="w-3 h-3" />
                                                            <span>{feedback.rating}/5</span>
                                                        </span>
                                                    )}

                                                    {/* Time */}
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        {feedback.feedback_at && new Date(feedback.feedback_at).toLocaleString('zh-TW')}
                                                    </span>
                                                </div>

                                                {/* Draft content preview */}
                                                <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 mb-2">
                                                    {feedback.content}
                                                </p>

                                                {/* Feedback reason */}
                                                {feedback.feedback_reason && (
                                                    <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">改進建議：</p>
                                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                                            {feedback.feedback_reason}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* Improvement tags */}
                                                {feedback.improvement_tags && feedback.improvement_tags.length > 0 && (
                                                    <div className="mt-2 flex flex-wrap gap-1">
                                                        {feedback.improvement_tags.map((tag, index) => (
                                                            <span
                                                                key={index}
                                                                className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded"
                                                            >
                                                                {tag}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

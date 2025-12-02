import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Star, Send } from 'lucide-react'
import axios from 'axios'

/**
 * FeedbackPanel - AI 草稿回饋元件
 *
 * 用於收集人工對 AI 草稿的評價，支援 AI 自我進化系統。
 *
 * Props:
 *   - draftId: 草稿 ID
 *   - initialFeedback: 初始回饋資料（可選）
 *   - onFeedbackSubmit: 回饋提交後的回呼函數
 *   - compact: 是否使用精簡模式（只顯示 thumbs up/down）
 */
export default function FeedbackPanel({
    draftId,
    initialFeedback = {},
    onFeedbackSubmit,
    compact = false
}) {
    const [isGood, setIsGood] = useState(initialFeedback.is_good)
    const [rating, setRating] = useState(initialFeedback.rating || 0)
    const [feedbackReason, setFeedbackReason] = useState(initialFeedback.feedback_reason || '')
    const [hoveredStar, setHoveredStar] = useState(0)
    const [submitting, setSubmitting] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [showDetails, setShowDetails] = useState(false)

    const handleThumbClick = async (good) => {
        setIsGood(good)

        // 如果點不好，展開詳細回饋區
        if (!good) {
            setShowDetails(true)
        }

        // 快速回饋：直接提交
        if (good) {
            await submitFeedback({ is_good: good })
        }
    }

    const handleStarClick = (star) => {
        setRating(star)
    }

    const submitFeedback = async (feedbackData = {}) => {
        setSubmitting(true)
        try {
            const payload = {
                is_good: feedbackData.is_good ?? isGood,
                rating: feedbackData.rating ?? rating || null,
                feedback_reason: feedbackData.feedback_reason ?? feedbackReason || null
            }

            await axios.post(`/api/drafts/${draftId}/feedback`, payload)

            setSubmitted(true)
            if (onFeedbackSubmit) {
                onFeedbackSubmit(payload)
            }
        } catch (error) {
            console.error('回饋提交失敗:', error)
            alert('回饋提交失敗，請稍後再試')
        } finally {
            setSubmitting(false)
        }
    }

    const handleSubmitDetails = () => {
        submitFeedback({
            is_good: isGood,
            rating: rating,
            feedback_reason: feedbackReason
        })
    }

    // 精簡模式：只顯示 thumbs up/down
    if (compact) {
        return (
            <div className="flex items-center space-x-2">
                <button
                    onClick={() => handleThumbClick(true)}
                    disabled={submitting || submitted}
                    className={`p-2 rounded-lg transition-colors ${isGood === true
                            ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                            : 'text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                        } ${submitting || submitted ? 'opacity-50 cursor-not-allowed' : ''}`}
                    title="這個回覆很好"
                >
                    <ThumbsUp className="w-5 h-5" />
                </button>
                <button
                    onClick={() => handleThumbClick(false)}
                    disabled={submitting || submitted}
                    className={`p-2 rounded-lg transition-colors ${isGood === false
                            ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                            : 'text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                        } ${submitting || submitted ? 'opacity-50 cursor-not-allowed' : ''}`}
                    title="這個回覆需要改進"
                >
                    <ThumbsDown className="w-5 h-5" />
                </button>
                {submitted && (
                    <span className="text-xs text-green-600 dark:text-green-400">
                        已記錄
                    </span>
                )}
            </div>
        )
    }

    // 完整模式
    return (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    這個草稿如何？
                </h4>
                {submitted && (
                    <span className="text-xs text-green-600 dark:text-green-400 flex items-center">
                        <span className="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                        回饋已記錄
                    </span>
                )}
            </div>

            {/* 快速回饋：好/不好 */}
            <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-500 dark:text-gray-400">快速評價：</span>
                <button
                    onClick={() => handleThumbClick(true)}
                    disabled={submitting}
                    className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-colors ${isGood === true
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                            : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-green-50 dark:hover:bg-green-900/20 border border-gray-200 dark:border-gray-600'
                        }`}
                >
                    <ThumbsUp className="w-4 h-4" />
                    <span>好</span>
                </button>
                <button
                    onClick={() => handleThumbClick(false)}
                    disabled={submitting}
                    className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-colors ${isGood === false
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                            : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-900/20 border border-gray-200 dark:border-gray-600'
                        }`}
                >
                    <ThumbsDown className="w-4 h-4" />
                    <span>不好</span>
                </button>
            </div>

            {/* 詳細回饋（點不好後展開，或手動展開） */}
            {(showDetails || isGood === false) && (
                <div className="space-y-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    {/* 星級評分 */}
                    <div className="flex items-center space-x-3">
                        <span className="text-sm text-gray-500 dark:text-gray-400">詳細評分：</span>
                        <div className="flex items-center space-x-1">
                            {[1, 2, 3, 4, 5].map((star) => (
                                <button
                                    key={star}
                                    onClick={() => handleStarClick(star)}
                                    onMouseEnter={() => setHoveredStar(star)}
                                    onMouseLeave={() => setHoveredStar(0)}
                                    disabled={submitting}
                                    className="focus:outline-none"
                                >
                                    <Star
                                        className={`w-6 h-6 transition-colors ${star <= (hoveredStar || rating)
                                                ? 'fill-yellow-400 text-yellow-400'
                                                : 'text-gray-300 dark:text-gray-600'
                                            }`}
                                    />
                                </button>
                            ))}
                        </div>
                        {rating > 0 && (
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                {rating} / 5
                            </span>
                        )}
                    </div>

                    {/* 修改原因 */}
                    <div>
                        <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">
                            哪裡需要改進？（選填）
                        </label>
                        <textarea
                            value={feedbackReason}
                            onChange={(e) => setFeedbackReason(e.target.value)}
                            placeholder="例如：語氣太正式、缺少具體資訊、表達不夠清晰..."
                            className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                            rows={3}
                            disabled={submitting}
                        />
                    </div>

                    {/* 提交按鈕 */}
                    <div className="flex justify-end">
                        <button
                            onClick={handleSubmitDetails}
                            disabled={submitting || submitted}
                            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${submitted
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                                } ${submitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {submitting ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : submitted ? (
                                <>
                                    <span>已送出</span>
                                </>
                            ) : (
                                <>
                                    <Send className="w-4 h-4" />
                                    <span>送出回饋</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}

            {/* 展開詳細回饋按鈕 */}
            {!showDetails && isGood !== false && (
                <button
                    onClick={() => setShowDetails(true)}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                    詳細評分
                </button>
            )}
        </div>
    )
}

import { useState, useEffect, useRef } from 'react'
import { ThumbsUp, ThumbsDown, Star } from 'lucide-react'
import axios from 'axios'

/**
 * FeedbackPanel - AI 草稿回饋元件（簡化版）
 *
 * 用於收集人工對 AI 草稿的快速評價。
 * 如需具體改進，請使用右側的「AI 草稿修正」功能。
 *
 * Props:
 *   - draftId: 草稿 ID
 *   - idSuffix: ID 後綴（用於區分桌面/手機版，避免重複 ID）
 *   - initialFeedback: 初始回饋資料（可選）
 *   - onFeedbackSubmit: 回饋提交後的回呼函數
 *   - compact: 是否使用精簡模式（只顯示 thumbs up/down）
 */
export default function FeedbackPanel({
    draftId,
    idSuffix = '',
    initialFeedback = {},
    onFeedbackSubmit,
    compact = false
}) {
    const [isGood, setIsGood] = useState(initialFeedback.is_good)
    const [rating, setRating] = useState(initialFeedback.rating || 0)
    const [hoveredStar, setHoveredStar] = useState(0)
    const [submitting, setSubmitting] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [showDetails, setShowDetails] = useState(false)

    // 用 ref 追蹤前一個 draftId，避免輪詢時重置狀態
    const prevDraftId = useRef(null)

    // 只在 draftId 真正改變時重置狀態
    useEffect(() => {
        if (prevDraftId.current !== draftId) {
            prevDraftId.current = draftId
            setIsGood(initialFeedback.is_good)
            setRating(initialFeedback.rating || 0)
            setShowDetails(false)
            setSubmitted(false)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [draftId])

    // 唯一 ID 用於 accessibility
    const feedbackId = `feedback-${draftId}${idSuffix}`

    const handleThumbClick = async (good) => {
        setIsGood(good)

        // 如果點不好，展開星級評分
        if (!good) {
            setShowDetails(true)
        } else {
            // 點好直接提交
            await submitFeedback({ is_good: good })
        }
    }

    const handleStarClick = async (star) => {
        setRating(star)
        // 選擇星級後自動提交
        await submitFeedback({ is_good: isGood, rating: star })
    }

    const submitFeedback = async (feedbackData = {}) => {
        setSubmitting(true)
        try {
            const payload = {
                is_good: feedbackData.is_good ?? isGood,
                rating: (feedbackData.rating ?? rating) || null,
                feedback_reason: null  // 不再收集文字回饋
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
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 space-y-3">
            <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    這個草稿如何？
                </h4>
                {submitted && (
                    <span className="text-xs text-green-600 dark:text-green-400 flex items-center">
                        <span className="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                        已記錄
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

            {/* 星級評分（點不好後展開） */}
            {(showDetails || isGood === false) && (
                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-3">
                        <span id={`${feedbackId}-rating-label`} className="text-sm text-gray-500 dark:text-gray-400">
                            評分：
                        </span>
                        <div
                            className="flex items-center space-x-1"
                            role="group"
                            aria-labelledby={`${feedbackId}-rating-label`}
                        >
                            {[1, 2, 3, 4, 5].map((star) => (
                                <button
                                    key={star}
                                    type="button"
                                    onClick={() => handleStarClick(star)}
                                    onMouseEnter={() => setHoveredStar(star)}
                                    onMouseLeave={() => setHoveredStar(0)}
                                    disabled={submitting}
                                    className="focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded"
                                    aria-label={`${star} 星`}
                                    aria-pressed={rating === star}
                                >
                                    <Star
                                        className={`w-5 h-5 transition-colors ${star <= (hoveredStar || rating)
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
                    {/* 提示使用 RefinementChat */}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                        💡 需要具體改進？請使用右側「AI 草稿修正」功能
                    </p>
                </div>
            )}
        </div>
    )
}

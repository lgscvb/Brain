import { useState, useEffect } from 'react'
import { X, Camera, Loader2, Check, AlertCircle, Image } from 'lucide-react'
import axios from 'axios'

/**
 * 照片分類選項
 */
const PHOTO_CATEGORIES = [
    {
        key: 'all',
        label: '全部照片',
        description: '發送所有環境照片（最多 10 張）',
        icon: '🖼️'
    },
    {
        key: 'exterior',
        label: '大樓外觀',
        description: '明錩大樓外觀照片',
        icon: '🏢'
    },
    {
        key: 'private_office',
        label: '獨立辦公室',
        description: 'D辦、E辦等獨立辦公室空間',
        icon: '🚪'
    },
    {
        key: 'coworking',
        label: '共享空間',
        description: '共享辦公區域與櫃檯',
        icon: '👥'
    },
    {
        key: 'facilities',
        label: '設施',
        description: '廁所、事務機等公共設施',
        icon: '🚿'
    }
]

/**
 * 照片發送 Modal
 *
 * 讓客服選擇照片分類，發送環境照片給客戶
 */
export default function PhotoSendModal({
    isOpen,
    onClose,
    lineUserId,
    customerName
}) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [success, setSuccess] = useState(false)
    const [selectedCategory, setSelectedCategory] = useState(null)
    const [photoStatus, setPhotoStatus] = useState(null)

    // 當 Modal 開啟時，取得照片狀態
    useEffect(() => {
        if (isOpen) {
            fetchPhotoStatus()
            // 重置狀態
            setError(null)
            setSuccess(false)
            setSelectedCategory(null)
        }
    }, [isOpen])

    // 取得照片狀態（各分類數量）
    const fetchPhotoStatus = async () => {
        try {
            const response = await axios.get('/api/photos/status')
            if (response.data.success) {
                setPhotoStatus(response.data)
            }
        } catch (err) {
            console.error('Fetch photo status error:', err)
        }
    }

    // 發送照片
    const sendPhotos = async () => {
        if (!selectedCategory || !lineUserId) return

        setLoading(true)
        setError(null)

        try {
            const response = await axios.post('/api/photos/send', {
                line_user_id: lineUserId,
                category: selectedCategory
            })

            if (response.data.success) {
                setSuccess(true)
            } else {
                setError(response.data.error || '發送失敗')
            }
        } catch (err) {
            console.error('Send photos error:', err)
            setError(err.response?.data?.detail || err.message || '發送照片失敗')
        } finally {
            setLoading(false)
        }
    }

    // 取得分類的照片數量
    const getCategoryCount = (key) => {
        if (!photoStatus?.category_counts) return 0
        if (key === 'all') return photoStatus.total_photos
        return photoStatus.category_counts[key] || 0
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full max-h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-2">
                        <Camera className="w-5 h-5 text-purple-600" />
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            發送環境照片
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {success ? (
                        // 發送成功
                        <div className="flex flex-col items-center justify-center py-8">
                            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
                                <Check className="w-6 h-6 text-green-600" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                                照片已發送！
                            </h3>
                            <p className="text-gray-600 dark:text-gray-400 text-center">
                                已將環境照片發送給 {customerName || '客戶'}
                            </p>
                        </div>
                    ) : error ? (
                        // 發送失敗
                        <div className="flex flex-col items-center justify-center py-8">
                            <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
                            <p className="text-red-600 dark:text-red-400 text-center mb-4">{error}</p>
                            <button
                                onClick={() => {
                                    setError(null)
                                    setSelectedCategory(null)
                                }}
                                className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                            >
                                重試
                            </button>
                        </div>
                    ) : (
                        // 分類選單
                        <div className="space-y-3">
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                                選擇要發送的照片分類給 <span className="font-medium text-gray-900 dark:text-white">{customerName || '客戶'}</span>
                            </p>

                            {PHOTO_CATEGORIES.map((category) => {
                                const count = getCategoryCount(category.key)
                                const isSelected = selectedCategory === category.key
                                const isDisabled = count === 0

                                return (
                                    <button
                                        key={category.key}
                                        onClick={() => !isDisabled && setSelectedCategory(category.key)}
                                        disabled={isDisabled}
                                        className={`w-full p-3 rounded-lg border text-left transition-all ${
                                            isDisabled
                                                ? 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 opacity-50 cursor-not-allowed'
                                                : isSelected
                                                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                                                    : 'border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50/50 dark:hover:bg-purple-900/10'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <span className="text-xl">{category.icon}</span>
                                                <div>
                                                    <p className={`font-medium ${
                                                        isSelected
                                                            ? 'text-purple-700 dark:text-purple-300'
                                                            : 'text-gray-900 dark:text-white'
                                                    }`}>
                                                        {category.label}
                                                    </p>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                                        {category.description}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                <span className={`text-sm px-2 py-0.5 rounded ${
                                                    isDisabled
                                                        ? 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                                                        : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                                                }`}>
                                                    {count} 張
                                                </span>
                                                {isSelected && (
                                                    <div className="w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center">
                                                        <Check className="w-3 h-3 text-white" />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </button>
                                )
                            })}

                            {/* 提示 */}
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
                                * LINE 訊息最多可顯示 10 張照片，超過時會自動選取代表性照片
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {!success && !error && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                            取消
                        </button>
                        <button
                            onClick={sendPhotos}
                            disabled={loading || !selectedCategory}
                            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>發送中...</span>
                                </>
                            ) : (
                                <>
                                    <Image className="w-4 h-4" />
                                    <span>發送照片</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {(success || error) && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                        >
                            關閉
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}

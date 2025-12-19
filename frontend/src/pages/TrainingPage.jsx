import { useState, useEffect } from 'react'
import { Download, Database, TrendingUp, FileJson, RefreshCw } from 'lucide-react'
import axios from 'axios'

/**
 * 訓練資料管理頁面
 * 顯示統計資訊、匯出 SFT/RLHF/DPO 格式資料
 */
export default function TrainingPage() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [exporting, setExporting] = useState(false)
    const [exportResult, setExportResult] = useState(null)

    // 載入統計資料
    useEffect(() => {
        fetchStats()
    }, [])

    const fetchStats = async () => {
        setLoading(true)
        try {
            const response = await axios.get('/api/training/stats')
            setStats(response.data)
        } catch (error) {
            console.error('載入統計失敗:', error)
        } finally {
            setLoading(false)
        }
    }

    // 匯出訓練資料
    const handleExport = async (exportType) => {
        setExporting(true)
        setExportResult(null)
        try {
            const response = await axios.post('/api/training/export', {
                export_type: exportType,
                include_refinements: true,
                include_responses: true
            })
            setExportResult(response.data)

            // 下載 JSON 檔案
            const blob = new Blob([JSON.stringify(response.data.data, null, 2)], {
                type: 'application/json'
            })
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `brain_training_${exportType}_${new Date().toISOString().slice(0, 10)}.json`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)

            // 重新載入統計
            fetchStats()
        } catch (error) {
            console.error('匯出失敗:', error)
            alert('匯出失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setExporting(false)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                        訓練資料管理
                    </h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        匯出 AI 學習資料，用於模型微調
                    </p>
                </div>
                <button
                    onClick={fetchStats}
                    className="flex items-center space-x-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                    <RefreshCw className="w-4 h-4" />
                    <span>重新整理</span>
                </button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900/50 rounded-lg">
                            <Database className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">總回覆數</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                {stats?.total_responses || 0}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="p-3 bg-orange-100 dark:bg-orange-900/50 rounded-lg">
                            <TrendingUp className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">修改率</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                {stats?.modification_rate || 0}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-lg">
                            <RefreshCw className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">修正對話</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                {stats?.total_refinements || 0}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="p-3 bg-green-100 dark:bg-green-900/50 rounded-lg">
                            <FileJson className="w-6 h-6 text-green-600 dark:text-green-400" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">預估 SFT 記錄</p>
                            <p className="text-2xl font-bold text-gray-900 dark:text-white">
                                {stats?.estimated_sft_records || 0}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Export Section */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        匯出訓練資料
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        選擇格式匯出資料，用於模型微調
                    </p>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* SFT Export */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                        <div className="flex items-center space-x-3 mb-3">
                            <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-lg">
                                <FileJson className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 dark:text-white">SFT 格式</h4>
                                <p className="text-xs text-gray-500">Supervised Fine-Tuning</p>
                            </div>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            instruction + input + output 格式，適用於 LoRA、QLoRA 微調
                        </p>
                        <button
                            onClick={() => handleExport('sft')}
                            disabled={exporting}
                            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {exporting ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            <span>匯出 SFT</span>
                        </button>
                    </div>

                    {/* RLHF Export */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                        <div className="flex items-center space-x-3 mb-3">
                            <div className="p-2 bg-orange-100 dark:bg-orange-900/50 rounded-lg">
                                <FileJson className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 dark:text-white">RLHF 格式</h4>
                                <p className="text-xs text-gray-500">Reinforcement Learning</p>
                            </div>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            prompt + chosen + rejected 格式，適用於 PPO 訓練
                        </p>
                        <button
                            onClick={() => handleExport('rlhf')}
                            disabled={exporting}
                            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {exporting ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            <span>匯出 RLHF</span>
                        </button>
                    </div>

                    {/* DPO Export */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                        <div className="flex items-center space-x-3 mb-3">
                            <div className="p-2 bg-purple-100 dark:bg-purple-900/50 rounded-lg">
                                <FileJson className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 dark:text-white">DPO 格式</h4>
                                <p className="text-xs text-gray-500">Direct Preference Optimization</p>
                            </div>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            含評分的偏好對格式，適用於 DPO 訓練
                        </p>
                        <button
                            onClick={() => handleExport('dpo')}
                            disabled={exporting}
                            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {exporting ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            <span>匯出 DPO</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Export Result */}
            {exportResult && (
                <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <div className="flex items-center space-x-2">
                        <FileJson className="w-5 h-5 text-green-600 dark:text-green-400" />
                        <span className="font-medium text-green-700 dark:text-green-300">
                            匯出成功！
                        </span>
                    </div>
                    <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                        格式：{exportResult.export_type.toUpperCase()} |
                        記錄數：{exportResult.record_count} |
                        匯出 ID：#{exportResult.export_id}
                    </p>
                </div>
            )}

            {/* Recent Exports */}
            {stats?.recent_exports && stats.recent_exports.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                            最近匯出記錄
                        </h3>
                    </div>
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {stats.recent_exports.map((exp) => (
                            <div key={exp.id} className="p-4 flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                    <div className={`p-2 rounded-lg ${
                                        exp.type === 'sft' ? 'bg-blue-100 dark:bg-blue-900/50' :
                                        exp.type === 'rlhf' ? 'bg-orange-100 dark:bg-orange-900/50' :
                                        'bg-purple-100 dark:bg-purple-900/50'
                                    }`}>
                                        <FileJson className={`w-4 h-4 ${
                                            exp.type === 'sft' ? 'text-blue-600 dark:text-blue-400' :
                                            exp.type === 'rlhf' ? 'text-orange-600 dark:text-orange-400' :
                                            'text-purple-600 dark:text-purple-400'
                                        }`} />
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-900 dark:text-white">
                                            {exp.type.toUpperCase()} 匯出
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {new Date(exp.created_at).toLocaleString('zh-TW')}
                                        </p>
                                    </div>
                                </div>
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {exp.count} 筆記錄
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

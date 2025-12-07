import { useState, useEffect, useCallback } from 'react'
import { Link2, Search, User, Building2, Phone, RefreshCw, Check, X, ChevronRight, AlertCircle, Users } from 'lucide-react'
import axios from 'axios'

export default function UidAlignmentPage() {
    // 統計資料
    const [stats, setStats] = useState(null)
    const [statsLoading, setStatsLoading] = useState(true)

    // 未匹配的 LINE 發送者
    const [unmatchedSenders, setUnmatchedSenders] = useState([])
    const [sendersLoading, setSendersLoading] = useState(true)
    const [senderSearch, setSenderSearch] = useState('')

    // 無 UID 的 CRM 客戶
    const [customersWithoutUid, setCustomersWithoutUid] = useState([])
    const [customersLoading, setCustomersLoading] = useState(true)
    const [customerSearch, setCustomerSearch] = useState('')

    // 選擇狀態
    const [selectedSender, setSelectedSender] = useState(null)
    const [selectedCustomer, setSelectedCustomer] = useState(null)
    const [linking, setLinking] = useState(false)

    // 載入統計
    const fetchStats = useCallback(async () => {
        setStatsLoading(true)
        try {
            const response = await axios.get('/api/uid-alignment/stats')
            setStats(response.data)
        } catch (error) {
            console.error('載入統計失敗:', error)
        } finally {
            setStatsLoading(false)
        }
    }, [])

    // 載入未匹配發送者
    const fetchUnmatchedSenders = useCallback(async () => {
        setSendersLoading(true)
        try {
            const response = await axios.get('/api/uid-alignment/unmatched-senders', {
                params: { search: senderSearch || undefined }
            })
            setUnmatchedSenders(response.data.items)
        } catch (error) {
            console.error('載入未匹配發送者失敗:', error)
        } finally {
            setSendersLoading(false)
        }
    }, [senderSearch])

    // 載入無 UID 客戶
    const fetchCustomersWithoutUid = useCallback(async () => {
        setCustomersLoading(true)
        try {
            const response = await axios.get('/api/uid-alignment/customers-without-uid', {
                params: { search: customerSearch || undefined }
            })
            setCustomersWithoutUid(response.data.items)
        } catch (error) {
            console.error('載入客戶失敗:', error)
        } finally {
            setCustomersLoading(false)
        }
    }, [customerSearch])

    useEffect(() => {
        fetchStats()
        fetchUnmatchedSenders()
        fetchCustomersWithoutUid()
    }, [])

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchUnmatchedSenders()
        }, 300)
        return () => clearTimeout(timer)
    }, [senderSearch])

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchCustomersWithoutUid()
        }, 300)
        return () => clearTimeout(timer)
    }, [customerSearch])

    // 連結 UID
    const handleLink = async () => {
        if (!selectedSender || !selectedCustomer) return

        setLinking(true)
        try {
            await axios.post('/api/uid-alignment/link', {
                customer_id: selectedCustomer.id,
                line_user_id: selectedSender.sender_id
            })

            // 重新載入
            setSelectedSender(null)
            setSelectedCustomer(null)
            fetchStats()
            fetchUnmatchedSenders()
            fetchCustomersWithoutUid()

            alert('連結成功！')
        } catch (error) {
            console.error('連結失敗:', error)
            alert('連結失敗：' + (error.response?.data?.detail || error.message))
        } finally {
            setLinking(false)
        }
    }

    const formatTime = (dateString) => {
        if (!dateString) return ''
        const date = new Date(dateString)
        return date.toLocaleDateString('zh-TW', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-3">
                        <Link2 className="w-8 h-8" />
                        <span>UID 對齊</span>
                    </h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        將 LINE User ID 與 CRM 客戶進行手動配對
                    </p>
                </div>
                <button
                    onClick={() => {
                        fetchStats()
                        fetchUnmatchedSenders()
                        fetchCustomersWithoutUid()
                    }}
                    className="flex items-center space-x-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    <span>重新整理</span>
                </button>
            </div>

            {/* 統計卡片 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">Brain 發送者</span>
                        <Users className="w-5 h-5 text-blue-500" />
                    </div>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                        {statsLoading ? '...' : stats?.brain_unique_senders || 0}
                    </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">CRM 客戶</span>
                        <Building2 className="w-5 h-5 text-green-500" />
                    </div>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                        {statsLoading ? '...' : stats?.crm_total_customers || 0}
                    </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">已綁定</span>
                        <Check className="w-5 h-5 text-green-500" />
                    </div>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-2">
                        {statsLoading ? '...' : stats?.crm_with_line_uid || 0}
                    </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">未綁定</span>
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                    </div>
                    <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 mt-2">
                        {statsLoading ? '...' : stats?.crm_without_line_uid || 0}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                        綁定率: {statsLoading ? '...' : `${stats?.alignment_rate || 0}%`}
                    </p>
                </div>
            </div>

            {/* 操作提示 */}
            {selectedSender && selectedCustomer && (
                <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className="text-sm">
                            <span className="text-gray-600 dark:text-gray-400">準備連結：</span>
                            <span className="font-medium text-blue-600 dark:text-blue-400 ml-2">
                                {selectedSender.sender_name}
                            </span>
                            <ChevronRight className="inline w-4 h-4 mx-2 text-gray-400" />
                            <span className="font-medium text-green-600 dark:text-green-400">
                                {selectedCustomer.name} ({selectedCustomer.legacy_id})
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => {
                                setSelectedSender(null)
                                setSelectedCustomer(null)
                            }}
                            className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                        >
                            取消
                        </button>
                        <button
                            onClick={handleLink}
                            disabled={linking}
                            className={`px-4 py-1.5 text-sm rounded-lg flex items-center space-x-2 ${
                                linking
                                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700'
                            }`}
                        >
                            {linking ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <Link2 className="w-4 h-4" />
                            )}
                            <span>{linking ? '連結中...' : '確認連結'}</span>
                        </button>
                    </div>
                </div>
            )}

            {/* 雙欄佈局 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 左欄：未匹配的 LINE 發送者 */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                            <span className="text-xl">💬</span>
                            <span>未匹配的 LINE 發送者</span>
                            <span className="text-sm font-normal text-gray-500">({unmatchedSenders.length})</span>
                        </h3>
                        <div className="mt-3 relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={senderSearch}
                                onChange={(e) => setSenderSearch(e.target.value)}
                                placeholder="搜尋發送者名稱..."
                                className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>

                    <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-200 dark:divide-gray-700">
                        {sendersLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            </div>
                        ) : unmatchedSenders.length === 0 ? (
                            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                                <Check className="w-12 h-12 mx-auto mb-3 text-green-500" />
                                <p>所有發送者都已匹配！</p>
                            </div>
                        ) : (
                            unmatchedSenders.map((sender) => (
                                <button
                                    key={sender.sender_id}
                                    onClick={() => setSelectedSender(sender)}
                                    className={`w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                                        selectedSender?.sender_id === sender.sender_id
                                            ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500'
                                            : ''
                                    }`}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-gray-900 dark:text-white">
                                            {sender.sender_name}
                                        </span>
                                        <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                                            {sender.message_count} 則訊息
                                        </span>
                                    </div>
                                    {sender.last_message_preview && (
                                        <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                            {sender.last_message_preview}
                                        </p>
                                    )}
                                    <div className="flex items-center justify-between mt-1 text-xs text-gray-400">
                                        <span>首次: {formatTime(sender.first_message_at)}</span>
                                        <span>最後: {formatTime(sender.last_message_at)}</span>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* 右欄：無 UID 的 CRM 客戶 */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                            <span className="text-xl">👤</span>
                            <span>CRM 客戶（無 LINE UID）</span>
                            <span className="text-sm font-normal text-gray-500">({customersWithoutUid.length})</span>
                        </h3>
                        <div className="mt-3 relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={customerSearch}
                                onChange={(e) => setCustomerSearch(e.target.value)}
                                placeholder="搜尋客戶名稱、公司、電話..."
                                className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>

                    <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-200 dark:divide-gray-700">
                        {customersLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            </div>
                        ) : customersWithoutUid.length === 0 ? (
                            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                                <Check className="w-12 h-12 mx-auto mb-3 text-green-500" />
                                <p>所有客戶都已綁定 LINE UID！</p>
                            </div>
                        ) : (
                            customersWithoutUid.map((customer) => (
                                <button
                                    key={customer.id}
                                    onClick={() => setSelectedCustomer(customer)}
                                    className={`w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                                        selectedCustomer?.id === customer.id
                                            ? 'bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500'
                                            : ''
                                    }`}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center space-x-2">
                                            <span className="text-xs font-mono text-gray-500 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                                                {customer.legacy_id}
                                            </span>
                                            <span className="font-medium text-gray-900 dark:text-white">
                                                {customer.name}
                                            </span>
                                        </div>
                                    </div>
                                    {customer.company_name && (
                                        <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                                            <Building2 className="w-3 h-3" />
                                            <span>{customer.company_name}</span>
                                        </div>
                                    )}
                                    {customer.phone && (
                                        <div className="flex items-center space-x-1 text-sm text-gray-500">
                                            <Phone className="w-3 h-3" />
                                            <span>{customer.phone}</span>
                                        </div>
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* 使用說明 */}
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">使用說明</h4>
                <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-decimal list-inside">
                    <li>左側顯示在 Brain 收到訊息但尚未與 CRM 配對的 LINE 用戶</li>
                    <li>右側顯示 CRM 中尚未綁定 LINE UID 的客戶</li>
                    <li>點選左側的發送者，再點選右側對應的客戶</li>
                    <li>確認無誤後，點擊「確認連結」完成配對</li>
                </ol>
            </div>
        </div>
    )
}

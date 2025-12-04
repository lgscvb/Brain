import { useState, useEffect } from 'react'
import { Book, Search, Plus, Edit2, Trash2, Upload, Filter, ChevronLeft, ChevronRight, X, Save } from 'lucide-react'
import axios from 'axios'

/**
 * KnowledgePage - 知識庫管理頁面
 *
 * 功能：
 * - 顯示知識條目列表
 * - 分類篩選
 * - 關鍵字搜尋
 * - 新增/編輯/刪除知識
 * - 批次匯入
 */
export default function KnowledgePage() {
    const [items, setItems] = useState([])
    const [stats, setStats] = useState(null)
    const [categories, setCategories] = useState([])
    const [loading, setLoading] = useState(true)

    // 篩選狀態
    const [selectedCategory, setSelectedCategory] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [page, setPage] = useState(1)
    const [pageSize] = useState(20)
    const [total, setTotal] = useState(0)

    // Modal 狀態
    const [showModal, setShowModal] = useState(false)
    const [showImportModal, setShowImportModal] = useState(false)
    const [editingItem, setEditingItem] = useState(null)
    const [formData, setFormData] = useState({
        content: '',
        category: 'spin_question',
        sub_category: '',
        service_type: '',
        metadata: {}
    })

    // 匯入狀態
    const [importData, setImportData] = useState('')
    const [importing, setImporting] = useState(false)

    // 分類名稱對應
    const categoryNames = {
        spin_question: 'SPIN 問題庫',
        value_prop: '價值主張',
        objection: '異議處理',
        faq: '常見問題',
        service_info: '服務資訊',
        tactics: '銷售技巧',
        scenario: '情境範例',
        example_response: '對話範例'
    }

    // 服務類型對應
    const serviceTypes = {
        address_service: '營業登記地址',
        coworking: '共享辦公',
        private_office: '獨立辦公室',
        meeting_room: '會議室'
    }

    useEffect(() => {
        fetchData()
    }, [page, selectedCategory, searchQuery])

    useEffect(() => {
        fetchStats()
        fetchCategories()
    }, [])

    const fetchData = async () => {
        setLoading(true)
        try {
            const params = {
                page,
                page_size: pageSize
            }
            if (selectedCategory) params.category = selectedCategory
            if (searchQuery) params.search = searchQuery

            const response = await axios.get('/api/knowledge', { params })
            setItems(response.data.items)
            setTotal(response.data.total)
        } catch (error) {
            console.error('獲取知識列表失敗:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchStats = async () => {
        try {
            const response = await axios.get('/api/knowledge/stats')
            setStats(response.data)
        } catch (error) {
            console.error('獲取統計失敗:', error)
        }
    }

    const fetchCategories = async () => {
        try {
            const response = await axios.get('/api/knowledge/categories')
            setCategories(response.data.categories)
        } catch (error) {
            console.error('獲取分類失敗:', error)
        }
    }

    const handleCreate = () => {
        setEditingItem(null)
        setFormData({
            content: '',
            category: 'spin_question',
            sub_category: '',
            service_type: '',
            metadata: {}
        })
        setShowModal(true)
    }

    const handleEdit = (item) => {
        setEditingItem(item)
        setFormData({
            content: item.content,
            category: item.category,
            sub_category: item.sub_category || '',
            service_type: item.service_type || '',
            metadata: item.metadata || {}
        })
        setShowModal(true)
    }

    const handleDelete = async (id) => {
        if (!confirm('確定要刪除此知識條目嗎？')) return

        try {
            await axios.delete(`/api/knowledge/${id}`)
            fetchData()
            fetchStats()
        } catch (error) {
            console.error('刪除失敗:', error)
            alert('刪除失敗')
        }
    }

    const handleSave = async () => {
        if (!formData.content.trim()) {
            alert('請輸入內容')
            return
        }

        try {
            if (editingItem) {
                await axios.put(`/api/knowledge/${editingItem.id}`, formData)
            } else {
                await axios.post('/api/knowledge', formData)
            }
            setShowModal(false)
            fetchData()
            fetchStats()
        } catch (error) {
            console.error('儲存失敗:', error)
            alert('儲存失敗')
        }
    }

    const handleImport = async () => {
        if (!importData.trim()) {
            alert('請輸入 JSON 資料')
            return
        }

        setImporting(true)
        try {
            const data = JSON.parse(importData)
            const items = Array.isArray(data) ? data : [data]

            const response = await axios.post('/api/knowledge/bulk-import', items)
            alert(`匯入完成！成功: ${response.data.imported} 筆，失敗: ${response.data.errors.length} 筆`)
            setShowImportModal(false)
            setImportData('')
            fetchData()
            fetchStats()
        } catch (error) {
            console.error('匯入失敗:', error)
            alert('匯入失敗：' + (error.message || 'JSON 格式錯誤'))
        } finally {
            setImporting(false)
        }
    }

    const totalPages = Math.ceil(total / pageSize)

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">知識庫管理</h2>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        管理 RAG 系統的知識條目，支援 SPIN 問題、價值主張、異議處理等
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <button
                        onClick={() => setShowImportModal(true)}
                        className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                    >
                        <Upload className="w-4 h-4" />
                        <span>批次匯入</span>
                    </button>
                    <button
                        onClick={handleCreate}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        <span>新增知識</span>
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                                <Book className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500 dark:text-gray-400">總數</p>
                                <p className="text-xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                                <span className="text-white text-sm font-bold">{stats.active}</span>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500 dark:text-gray-400">啟用中</p>
                                <p className="text-xl font-bold text-green-600 dark:text-green-400">{stats.active}</p>
                            </div>
                        </div>
                    </div>
                    {Object.entries(stats.by_category || {}).slice(0, 4).map(([cat, count]) => (
                        <div key={cat} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                            <div>
                                <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{categoryNames[cat] || cat}</p>
                                <p className="text-xl font-bold text-gray-900 dark:text-white">{count}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex flex-wrap items-center gap-4">
                    {/* Search */}
                    <div className="flex-1 min-w-[200px] relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            id="knowledge-search"
                            name="knowledge-search"
                            type="text"
                            placeholder="搜尋知識內容..."
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value)
                                setPage(1)
                            }}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Category Filter */}
                    <div className="flex items-center space-x-2">
                        <Filter className="w-4 h-4 text-gray-400" />
                        <select
                            id="knowledge-category-filter"
                            name="knowledge-category-filter"
                            value={selectedCategory}
                            onChange={(e) => {
                                setSelectedCategory(e.target.value)
                                setPage(1)
                            }}
                            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">全部分類</option>
                            {categories.map((cat) => (
                                <option key={cat.id} value={cat.id}>{cat.name}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Knowledge List */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    </div>
                ) : items.length === 0 ? (
                    <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                        {searchQuery || selectedCategory ? '沒有符合條件的知識條目' : '知識庫目前是空的，點擊「新增知識」開始建立'}
                    </div>
                ) : (
                    <>
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                            {items.map((item) => (
                                <div key={item.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 min-w-0 mr-4">
                                            {/* Tags */}
                                            <div className="flex flex-wrap items-center gap-2 mb-2">
                                                <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs rounded font-medium">
                                                    {categoryNames[item.category] || item.category}
                                                </span>
                                                {item.sub_category && (
                                                    <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded">
                                                        {item.sub_category}
                                                    </span>
                                                )}
                                                {item.service_type && (
                                                    <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs rounded">
                                                        {serviceTypes[item.service_type] || item.service_type}
                                                    </span>
                                                )}
                                                {!item.is_active && (
                                                    <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 text-xs rounded">
                                                        已停用
                                                    </span>
                                                )}
                                            </div>

                                            {/* Content */}
                                            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                                                {item.content}
                                            </p>

                                            {/* Time */}
                                            <p className="mt-1 text-xs text-gray-400">
                                                更新於 {new Date(item.updated_at).toLocaleString('zh-TW')}
                                            </p>
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={() => handleEdit(item)}
                                                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                                title="編輯"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(item.id)}
                                                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                                title="刪除"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    共 {total} 筆，第 {page} / {totalPages} 頁
                                </p>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        disabled={page === 1}
                                        className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <ChevronLeft className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                        disabled={page === totalPages}
                                        className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <ChevronRight className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Edit/Create Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {editingItem ? '編輯知識' : '新增知識'}
                            </h3>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            {/* Content */}
                            <div>
                                <label htmlFor="knowledge-content" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    內容 *
                                </label>
                                <textarea
                                    id="knowledge-content"
                                    name="knowledge-content"
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    rows={5}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                    placeholder="輸入知識內容..."
                                />
                            </div>

                            {/* Category */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="knowledge-category" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        分類 *
                                    </label>
                                    <select
                                        id="knowledge-category"
                                        name="knowledge-category"
                                        value={formData.category}
                                        onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                    >
                                        {Object.entries(categoryNames).map(([id, name]) => (
                                            <option key={id} value={id}>{name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label htmlFor="knowledge-sub-category" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        子分類
                                    </label>
                                    <input
                                        id="knowledge-sub-category"
                                        name="knowledge-sub-category"
                                        type="text"
                                        value={formData.sub_category}
                                        onChange={(e) => setFormData({ ...formData, sub_category: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                        placeholder="例如: S, P, I, N"
                                    />
                                </div>
                            </div>

                            {/* Service Type */}
                            <div>
                                <label htmlFor="knowledge-service-type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    服務類型
                                </label>
                                <select
                                    id="knowledge-service-type"
                                    name="knowledge-service-type"
                                    value={formData.service_type}
                                    onChange={(e) => setFormData({ ...formData, service_type: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="">通用（不限服務）</option>
                                    {Object.entries(serviceTypes).map(([id, name]) => (
                                        <option key={id} value={id}>{name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="flex items-center justify-end space-x-3 p-4 border-t border-gray-200 dark:border-gray-700">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSave}
                                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                            >
                                <Save className="w-4 h-4" />
                                <span>儲存</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Import Modal */}
            {showImportModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                批次匯入知識
                            </h3>
                            <button
                                onClick={() => setShowImportModal(false)}
                                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                <p className="text-sm text-blue-700 dark:text-blue-300">
                                    請輸入 JSON 格式的知識資料。支援單個物件或陣列。
                                </p>
                                <pre className="mt-2 text-xs text-blue-600 dark:text-blue-400 overflow-x-auto">
{`[
  {
    "content": "知識內容",
    "category": "spin_question",
    "sub_category": "S",
    "service_type": "address_service"
  }
]`}
                                </pre>
                            </div>

                            <textarea
                                id="knowledge-import-data"
                                name="knowledge-import-data"
                                value={importData}
                                onChange={(e) => setImportData(e.target.value)}
                                rows={12}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-blue-500"
                                placeholder="貼上 JSON 資料..."
                            />
                        </div>

                        <div className="flex items-center justify-end space-x-3 p-4 border-t border-gray-200 dark:border-gray-700">
                            <button
                                onClick={() => setShowImportModal(false)}
                                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleImport}
                                disabled={importing}
                                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-colors"
                            >
                                {importing ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                                        <span>匯入中...</span>
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-4 h-4" />
                                        <span>匯入</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

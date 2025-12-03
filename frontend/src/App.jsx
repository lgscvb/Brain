import { useState } from 'react'
import { Settings, BookOpen, Activity, MessageSquare, FileText, ThumbsUp, Database } from 'lucide-react'
import SettingsPage from './pages/SettingsPage'
import GuidePage from './pages/GuidePage'
import DashboardPage from './pages/DashboardPage'
import LogsPage from './pages/LogsPage'
import FeedbackPage from './pages/FeedbackPage'
import MessagesPage from './pages/MessagesPage'
import KnowledgePage from './pages/KnowledgePage'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

  const navigation = [
    { id: 'dashboard', name: '儀表板', icon: Activity },
    { id: 'messages', name: '訊息管理', icon: MessageSquare },
    { id: 'knowledge', name: '知識庫', icon: Database },
    { id: 'feedback', name: 'AI 回饋', icon: ThumbsUp },
    { id: 'logs', name: '系統日誌', icon: FileText },
    { id: 'settings', name: '系統設定', icon: Settings },
    { id: 'guide', name: '使用說明', icon: BookOpen },
  ]

  const renderPage = () => {
    switch (currentPage) {
      case 'settings':
        return <SettingsPage />
      case 'guide':
        return <GuidePage />
      case 'logs':
        return <LogsPage />
      case 'feedback':
        return <FeedbackPage />
      case 'messages':
        return <MessagesPage />
      case 'knowledge':
        return <KnowledgePage />
      case 'dashboard':
      default:
        return <DashboardPage onNavigate={setCurrentPage} />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-xl">🧠</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Brain</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Hour Jungle AI 輔助客服系統</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-3 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 text-xs font-medium rounded-full">
                ● 運行中
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${isActive
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300'
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lng:px-8 py-8">
        {renderPage()}
      </main>

      {/* Footer */}
      <footer className="mt-12 py-6 border-t border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Brain v0.1.0 - Hour Jungle AI 輔助客服系統</p>
        </div>
      </footer>
    </div>
  )
}

export default App

import { useState } from 'react'
import { Settings, BookOpen, Activity, MessageSquare, FileText, ThumbsUp, Database, Link2, GraduationCap } from 'lucide-react'
import SettingsPage from './pages/SettingsPage'
import GuidePage from './pages/GuidePage'
import DashboardPage from './pages/DashboardPage'
import LogsPage from './pages/LogsPage'
import FeedbackPage from './pages/FeedbackPage'
import MessagesPage from './pages/MessagesPage'
import KnowledgePage from './pages/KnowledgePage'
import UidAlignmentPage from './pages/UidAlignmentPage'
import TrainingPage from './pages/TrainingPage'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

  const navigation = [
    { id: 'dashboard', name: '儀表板', icon: Activity },
    { id: 'messages', name: '訊息管理', icon: MessageSquare },
    { id: 'uid-alignment', name: 'UID 對齊', icon: Link2 },
    { id: 'knowledge', name: '知識庫', icon: Database },
    { id: 'training', name: '訓練資料', icon: GraduationCap },
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
      case 'uid-alignment':
        return <UidAlignmentPage />
      case 'training':
        return <TrainingPage />
      case 'dashboard':
      default:
        return <DashboardPage onNavigate={setCurrentPage} />
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* 合併的 Header + Navigation（單行）*/}
      <header className="flex-shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-[1600px] mx-auto px-4 flex items-center justify-between">
          {/* Logo + Title */}
          <div className="flex items-center space-x-2 py-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">🧠</span>
            </div>
            <span className="font-bold text-gray-900 dark:text-white">Brain</span>
            <span className="hidden sm:inline text-xs text-gray-400 dark:text-gray-500">|</span>
            <span className="hidden sm:inline text-xs text-gray-500 dark:text-gray-400">Hour Jungle AI</span>
          </div>

          {/* Navigation */}
          <nav className="flex items-center space-x-1 overflow-x-auto">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors ${isActive
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden lg:inline">{item.name}</span>
                </button>
              )
            })}
          </nav>

          {/* Status */}
          <div className="flex items-center">
            <span className="px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400 text-xs font-medium rounded-full">
              ● 運行中
            </span>
          </div>
        </div>
      </header>

      {/* Main Content - 佔滿剩餘空間 */}
      <main className="flex-1 overflow-hidden max-w-[1600px] w-full mx-auto px-4 py-3">
        {renderPage()}
      </main>
    </div>
  )
}

export default App

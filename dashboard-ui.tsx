import React, { useState } from 'react';
import { MessageSquare, Mail, Phone, Send, Edit3, Check, Clock, AlertCircle, TrendingUp, Zap } from 'lucide-react';

export default function OmnichannelDashboard() {
  const [selectedMessage, setSelectedMessage] = useState(0);
  const [selectedDraft, setSelectedDraft] = useState(1);
  const [editedContent, setEditedContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const messages = [
    {
      id: 1,
      source: 'line_oa',
      customer: '王小明',
      content: '請問登記地址多少錢？可以開發票嗎？',
      time: '2分鐘前',
      priority: 'high',
      customerInfo: {
        type: '首次諮詢',
        source: 'GA廣告',
        history: '無'
      }
    },
    {
      id: 2,
      source: 'email',
      customer: '陳美玲',
      content: '我們公司想了解共享辦公室方案，約10人左右',
      time: '15分鐘前',
      priority: 'high',
      customerInfo: {
        type: '企業客戶',
        source: '轉介紹',
        history: '上週有來訪參觀'
      }
    },
    {
      id: 3,
      source: 'phone',
      customer: '0912-xxx-xxx',
      content: '[語音轉文字] 我想問一下你們那個虛擬辦公室可以登記公司嗎...',
      time: '30分鐘前',
      priority: 'medium',
      customerInfo: {
        type: '個人創業',
        source: '未知',
        history: '首次來電'
      }
    }
  ];

  const drafts = [
    {
      version: 'A',
      label: '直接報價型',
      content: '您好！Hour Jungle 虛擬登記地址方案為 $10,000/月，包含信件代收、90天免費稅務諮詢。可以開立發票沒問題！請問您預計什麼時候需要完成登記呢？',
      recommended: false
    },
    {
      version: 'B',
      label: 'SPIN 問診型',
      content: '您好！感謝您的詢問 😊\n\n想先請教一下，您目前是要新設立公司，還是現有公司要變更地址呢？這樣我可以給您更精準的建議～',
      recommended: true
    },
    {
      version: 'C',
      label: '簡短回覆型',
      content: '您好！登記地址 $10,000/月，可開發票。需要進一步了解嗎？',
      recommended: false
    }
  ];

  const strategy = {
    stage: 'Situation（情境了解）',
    reasoning: '客戶是首次諮詢且來自廣告，應先了解需求再報價，避免價格導向',
    nextAction: '了解公司型態後，引導預約參觀',
    risk: '直接報價可能讓客戶只比價，流失率高'
  };

  const sourceIcon = {
    line_oa: <MessageSquare className="w-4 h-4 text-green-500" />,
    email: <Mail className="w-4 h-4 text-blue-500" />,
    phone: <Phone className="w-4 h-4 text-orange-500" />
  };

  const currentMessage = messages[selectedMessage];
  const currentDraft = drafts[selectedDraft];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Zap className="w-8 h-8 text-yellow-400" />
            <h1 className="text-2xl font-bold">Hour Jungle Brain</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              3 則待處理
            </div>
            <div className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              AI 學習中：87% 準確率
            </div>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* 左側：訊息列表 */}
          <div className="col-span-3 bg-gray-800 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-gray-400 mb-3">待處理訊息</h2>
            <div className="space-y-2">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id}
                  onClick={() => setSelectedMessage(idx)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedMessage === idx 
                      ? 'bg-blue-600/30 border border-blue-500' 
                      : 'bg-gray-700/50 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {sourceIcon[msg.source]}
                      <span className="font-medium text-sm">{msg.customer}</span>
                    </div>
                    <span className="text-xs text-gray-400">{msg.time}</span>
                  </div>
                  <p className="text-xs text-gray-300 truncate">{msg.content}</p>
                  {msg.priority === 'high' && (
                    <span className="inline-block mt-1 text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                      高優先
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 中間：訊息詳情 + 草稿 */}
          <div className="col-span-6 space-y-4">
            {/* 原始訊息 */}
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                {sourceIcon[currentMessage.source]}
                <span className="font-semibold">{currentMessage.customer}</span>
                <span className="text-xs text-gray-400">• {currentMessage.time}</span>
              </div>
              <div className="bg-gray-700 rounded-lg p-3">
                <p>{currentMessage.content}</p>
              </div>
            </div>

            {/* AI 策略建議 */}
            <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 rounded-lg p-4 border border-purple-500/30">
              <h3 className="text-sm font-semibold text-purple-300 mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                AI 策略建議
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-400">SPIN 階段：</span>
                  <span className="text-white ml-1">{strategy.stage}</span>
                </div>
                <div>
                  <span className="text-gray-400">建議行動：</span>
                  <span className="text-white ml-1">{strategy.nextAction}</span>
                </div>
              </div>
              <p className="text-xs text-gray-300 mt-2">
                💡 {strategy.reasoning}
              </p>
              <p className="text-xs text-yellow-400 mt-1">
                ⚠️ 風險提醒：{strategy.risk}
              </p>
            </div>

            {/* 草稿選擇 */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">選擇回覆草稿</h3>
              <div className="space-y-2 mb-4">
                {drafts.map((draft, idx) => (
                  <div
                    key={draft.version}
                    onClick={() => {
                      setSelectedDraft(idx);
                      setEditedContent(draft.content);
                      setIsEditing(false);
                    }}
                    className={`p-3 rounded-lg cursor-pointer transition-all ${
                      selectedDraft === idx
                        ? 'bg-blue-600/30 border border-blue-500'
                        : 'bg-gray-700/50 hover:bg-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-gray-600 px-2 py-0.5 rounded">
                          {draft.version}
                        </span>
                        <span className="text-sm font-medium">{draft.label}</span>
                        {draft.recommended && (
                          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                            推薦
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 編輯區 */}
              <div className="border border-gray-600 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400">
                    {isEditing ? '編輯中...' : '預覽'}
                  </span>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    <Edit3 className="w-3 h-3" />
                    {isEditing ? '完成編輯' : '編輯'}
                  </button>
                </div>
                {isEditing ? (
                  <textarea
                    value={editedContent || currentDraft.content}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full bg-gray-700 rounded p-2 text-sm min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-sm whitespace-pre-wrap">
                    {editedContent || currentDraft.content}
                  </p>
                )}
              </div>

              {/* 發送按鈕 */}
              <div className="flex gap-2 mt-4">
                <button className="flex-1 bg-green-600 hover:bg-green-500 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors">
                  <Send className="w-4 h-4" />
                  發送
                </button>
                <button className="px-4 bg-gray-600 hover:bg-gray-500 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors">
                  <Clock className="w-4 h-4" />
                  稍後
                </button>
              </div>
            </div>
          </div>

          {/* 右側：客戶資訊 */}
          <div className="col-span-3 space-y-4">
            {/* CRM 資訊 */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">客戶背景</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">類型</span>
                  <span>{currentMessage.customerInfo.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">來源</span>
                  <span>{currentMessage.customerInfo.source}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">歷史</span>
                  <span>{currentMessage.customerInfo.history}</span>
                </div>
              </div>
            </div>

            {/* 學習記錄 */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">📈 學習記錄</h3>
              <div className="space-y-2 text-xs">
                <div className="bg-gray-700/50 p-2 rounded">
                  <p className="text-green-400">✓ 上次類似情境</p>
                  <p className="text-gray-300">SPIN 問診 → 成交率 65%</p>
                </div>
                <div className="bg-gray-700/50 p-2 rounded">
                  <p className="text-yellow-400">⚡ 你的偏好</p>
                  <p className="text-gray-300">傾向加入 emoji、語氣親切</p>
                </div>
                <div className="bg-gray-700/50 p-2 rounded">
                  <p className="text-blue-400">📊 本週修改率</p>
                  <p className="text-gray-300">23% (下降中 ↓)</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

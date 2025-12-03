/**
 * Brain - 通知服務
 * 處理網頁通知和音效提醒
 */

class NotificationService {
  constructor() {
    this.permission = 'default'
    this.audioContext = null
    this.notificationSound = null
    this.lastMessageCount = 0
    this.lastMessageIds = new Set()
    this.soundEnabled = true
    this.notificationEnabled = true

    // 初始化
    this.init()
  }

  async init() {
    // 檢查通知權限
    if ('Notification' in window) {
      this.permission = Notification.permission
    }

    // 初始化音效
    this.initSound()

    // 從 localStorage 讀取設定
    this.loadSettings()
  }

  loadSettings() {
    const settings = localStorage.getItem('brain_notification_settings')
    if (settings) {
      const parsed = JSON.parse(settings)
      this.soundEnabled = parsed.soundEnabled ?? true
      this.notificationEnabled = parsed.notificationEnabled ?? true
    }
  }

  saveSettings() {
    localStorage.setItem('brain_notification_settings', JSON.stringify({
      soundEnabled: this.soundEnabled,
      notificationEnabled: this.notificationEnabled
    }))
  }

  setSoundEnabled(enabled) {
    this.soundEnabled = enabled
    this.saveSettings()
  }

  setNotificationEnabled(enabled) {
    this.notificationEnabled = enabled
    this.saveSettings()
  }

  initSound() {
    try {
      // 使用 Web Audio API 建立提示音
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
    } catch (e) {
      console.warn('Web Audio API 不支援:', e)
    }
  }

  /**
   * 請求通知權限
   */
  async requestPermission() {
    if (!('Notification' in window)) {
      console.warn('此瀏覽器不支援通知')
      return false
    }

    if (Notification.permission === 'granted') {
      this.permission = 'granted'
      return true
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission()
      this.permission = permission
      return permission === 'granted'
    }

    return false
  }

  /**
   * 播放提示音效
   * 使用 Web Audio API 生成清脆的提示音
   */
  playSound() {
    if (!this.soundEnabled || !this.audioContext) return

    try {
      // 恢復被暫停的音頻上下文
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume()
      }

      const oscillator = this.audioContext.createOscillator()
      const gainNode = this.audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(this.audioContext.destination)

      // 設定音調 (兩聲短促的提示音)
      oscillator.frequency.setValueAtTime(880, this.audioContext.currentTime) // A5
      oscillator.frequency.setValueAtTime(1047, this.audioContext.currentTime + 0.1) // C6
      oscillator.type = 'sine'

      // 設定音量漸變
      gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3)

      oscillator.start(this.audioContext.currentTime)
      oscillator.stop(this.audioContext.currentTime + 0.3)
    } catch (e) {
      console.warn('播放音效失敗:', e)
    }
  }

  /**
   * 播放更明顯的提示音（新訊息）
   */
  playNewMessageSound() {
    if (!this.soundEnabled || !this.audioContext) return

    try {
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume()
      }

      // 第一聲
      const osc1 = this.audioContext.createOscillator()
      const gain1 = this.audioContext.createGain()
      osc1.connect(gain1)
      gain1.connect(this.audioContext.destination)
      osc1.frequency.value = 523.25 // C5
      osc1.type = 'sine'
      gain1.gain.setValueAtTime(0.4, this.audioContext.currentTime)
      gain1.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.15)
      osc1.start(this.audioContext.currentTime)
      osc1.stop(this.audioContext.currentTime + 0.15)

      // 第二聲
      const osc2 = this.audioContext.createOscillator()
      const gain2 = this.audioContext.createGain()
      osc2.connect(gain2)
      gain2.connect(this.audioContext.destination)
      osc2.frequency.value = 659.25 // E5
      osc2.type = 'sine'
      gain2.gain.setValueAtTime(0.4, this.audioContext.currentTime + 0.15)
      gain2.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3)
      osc2.start(this.audioContext.currentTime + 0.15)
      osc2.stop(this.audioContext.currentTime + 0.3)

      // 第三聲
      const osc3 = this.audioContext.createOscillator()
      const gain3 = this.audioContext.createGain()
      osc3.connect(gain3)
      gain3.connect(this.audioContext.destination)
      osc3.frequency.value = 783.99 // G5
      osc3.type = 'sine'
      gain3.gain.setValueAtTime(0.4, this.audioContext.currentTime + 0.3)
      gain3.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5)
      osc3.start(this.audioContext.currentTime + 0.3)
      osc3.stop(this.audioContext.currentTime + 0.5)
    } catch (e) {
      console.warn('播放新訊息音效失敗:', e)
    }
  }

  /**
   * 顯示網頁通知
   */
  showNotification(title, options = {}) {
    if (!this.notificationEnabled) return
    if (this.permission !== 'granted') return

    const defaultOptions = {
      icon: '/brain-icon.png',
      badge: '/brain-icon.png',
      tag: 'brain-notification',
      renotify: true,
      requireInteraction: false,
      silent: true, // 我們用自己的音效
      ...options
    }

    try {
      const notification = new Notification(title, defaultOptions)

      notification.onclick = () => {
        window.focus()
        notification.close()
        if (options.onClick) {
          options.onClick()
        }
      }

      // 5 秒後自動關閉
      setTimeout(() => notification.close(), 5000)

      return notification
    } catch (e) {
      console.warn('顯示通知失敗:', e)
    }
  }

  /**
   * 檢查新訊息並發送通知
   */
  checkNewMessages(messages) {
    if (!messages || messages.length === 0) return []

    const currentIds = new Set(messages.map(m => m.id))
    const newMessages = []

    // 找出新訊息
    messages.forEach(msg => {
      if (!this.lastMessageIds.has(msg.id) && msg.status === 'pending') {
        newMessages.push(msg)
      }
    })

    // 更新記錄
    this.lastMessageIds = currentIds
    this.lastMessageCount = messages.length

    // 如果有新訊息，發送通知
    if (newMessages.length > 0) {
      this.notifyNewMessages(newMessages)
    }

    return newMessages
  }

  /**
   * 發送新訊息通知
   */
  notifyNewMessages(newMessages) {
    // 播放音效
    this.playNewMessageSound()

    // 顯示網頁通知
    if (newMessages.length === 1) {
      const msg = newMessages[0]
      this.showNotification('🧠 Brain - 新訊息', {
        body: `${msg.sender_name}: ${msg.content.substring(0, 50)}${msg.content.length > 50 ? '...' : ''}`,
        tag: `brain-message-${msg.id}`
      })
    } else {
      this.showNotification('🧠 Brain - 新訊息', {
        body: `收到 ${newMessages.length} 則新訊息`,
        tag: 'brain-messages-multiple'
      })
    }
  }

  /**
   * 重置訊息追蹤（用於初始載入）
   */
  resetTracking(messages) {
    this.lastMessageIds = new Set(messages.map(m => m.id))
    this.lastMessageCount = messages.length
  }
}

// 單例模式
const notificationService = new NotificationService()
export default notificationService

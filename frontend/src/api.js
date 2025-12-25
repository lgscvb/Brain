import axios from 'axios'

// 設定 axios 預設 baseURL
// 開發環境用 Vite proxy（空字串）
// 正式環境用環境變數指定的 URL
const baseURL = import.meta.env.VITE_API_BASE_URL || ''

axios.defaults.baseURL = baseURL

export default axios

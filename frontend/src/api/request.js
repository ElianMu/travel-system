import axios from 'axios'
import { ElMessage } from 'element-plus'

// 后端配置了 API_KEY 时，构建前端需提供相同的 VITE_API_KEY
const API_KEY = import.meta.env.VITE_API_KEY
export const AUTH_HEADERS = API_KEY ? { 'X-API-Key': API_KEY } : {}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  headers: AUTH_HEADERS,
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    ElMessage.error(err.response?.data?.message || '请求失败')
    return Promise.reject(err)
  },
)

export default request

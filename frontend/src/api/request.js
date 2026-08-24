import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    ElMessage.error(err.response?.data?.detail || '请求失败')
    return Promise.reject(err)
  },
)

export default request

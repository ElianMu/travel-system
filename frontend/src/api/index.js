import request from './request'

export const searchAttractions = (params) => request.get('/search/attractions', { params })
export const searchRoutes = (params) => request.get('/search/routes', { params })
export const searchInfo = (params) => request.get('/search/info', { params })
export const importDocument = (formData) =>
  request.post('/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getImportTask = (id) => request.get(`/import/tasks/${id}`)
export const listDocuments = (params) => request.get('/documents', { params })
export const getDocumentDetail = (id) => request.get(`/documents/${id}`)
export const deleteDocument = (id) => request.delete(`/documents/${id}`)

export const chat = (data) => request.post('/chat', data)
export const listSessions = () => request.get('/sessions')
export const createSession = (title) => request.post('/sessions', null, { params: { title } })
export const getMessages = (sessionId) => request.get(`/sessions/${sessionId}/messages`)
export const deleteSession = (sessionId) => request.delete(`/sessions/${sessionId}`)

/**
 * 流式问答（fetch + ReadableStream 读取 SSE）。
 * 回调：onToken(delta)、onCitations(citations)、onFallbackAnswer(answer)
 */
export async function chatStream({ query, sessionId }, onToken, onCitations, onFallbackAnswer) {
  const resp = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  })
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = JSON.parse(line.slice(6))
      if (data.delta != null) onToken(data.delta)
      else if (data.citations != null) onCitations(data.citations)
      else if (data.answer != null) onFallbackAnswer(data.answer)
    }
  }
}

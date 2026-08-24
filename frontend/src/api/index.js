import request from './request'

export const searchAttractions = (params) => request.get('/search/attractions', { params })
export const searchRoutes = (params) => request.get('/search/routes', { params })
export const searchInfo = (params) => request.get('/search/info', { params })
export const importDocument = (formData) =>
  request.post('/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getImportTask = (id) => request.get(`/import/tasks/${id}`)
export const listDocuments = (params) => request.get('/documents', { params })

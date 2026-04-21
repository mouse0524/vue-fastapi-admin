import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getCaptcha: () => request.get('/base/captcha', { noNeedToken: true }),
  getPublicConfig: () => request.get('/base/public_config', { noNeedToken: true }),
  getWorkbenchStats: () => request.get('/base/workbench_stats'),
  sendEmailCode: (data = {}) => request.post('/base/send_email_code', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),
  // ticket
  uploadTicketAttachment: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/ticket/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  createTicket: (data = {}) => request.post('/ticket/create', data),
  getTicketPrefill: () => request.get('/ticket/prefill'),
  getTicketList: (params = {}) => request.get('/ticket/list', { params }),
  getTicketById: (params = {}) => request.get('/ticket/get', { params }),
  reviewTicket: (data = {}) => request.post('/ticket/review', data),
  techActionTicket: (data = {}) => request.post('/ticket/tech/action', data),
  downloadTicketAttachment: (params = {}) => request.get('/ticket/attachment/download', { params }),
  resubmitTicket: (data = {}) => request.post('/ticket/resubmit', data),
  getTicketActions: (params = {}) => request.get('/ticket/actions', { params }),
  uploadPublicTicketAttachment: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/public/ticket/upload', formData, {
      noNeedToken: true,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  createPublicTicket: (data = {}) => request.post('/public/ticket/create', data, { noNeedToken: true }),
  // partner
  channelRegister: (data = {}) =>
    request.post('/partner/register', { ...data, register_type: 'channel' }, { noNeedToken: true }),
  userRegister: (data = {}) =>
    request.post('/partner/register', { ...data, register_type: 'user' }, { noNeedToken: true }),
  getPartnerRegisterList: (params = {}) => {
    const query = { ...params }
    if (query.register_type === 'all' || query.register_type === '' || query.register_type == null) {
      delete query.register_type
    } else {
      query.register_type = String(query.register_type)
    }
    if (query.reviewed == null || query.reviewed === '') {
      delete query.reviewed
    }
    if (!query.keyword) delete query.keyword
    return request.get('/partner/register/list', { params: query })
  },
  reviewPartnerRegister: (data = {}) => request.post('/partner/register/review', data),
  // settings
  getSystemSettings: () => request.get('/settings/get'),
  updateSystemSettings: (data = {}) => request.post('/settings/update', data),
  testWebdavConnection: (data = {}) => request.post('/settings/webdav/test', data),
  uploadSiteLogo: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/settings/upload_logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  // webdav
  webdavList: (params = {}) => request.get('/webdav/list', { params }),
  webdavCreateShare: (data = {}) => request.post('/webdav/share/create', data),
  webdavShareList: (params = {}) => request.get('/webdav/share/list', { params }),
  webdavShareDelete: (data = {}) => request.post('/webdav/share/delete', data),
  // kb
  kbSpaceList: (params = {}) => request.get('/kb/space/list', { params }),
  kbSpaceCreate: (data = {}) => request.post('/kb/space/create', data),
  kbSpaceUpdate: (data = {}) => request.post('/kb/space/update', data),
  kbDocumentList: (params = {}) => request.get('/kb/document/list', { params }),
  kbDocumentCreate: (data = {}) => request.post('/kb/document/create', data),
  kbDocumentReparse: (data = {}) => request.post('/kb/document/reparse', null, { params: data }),
  kbDocumentProcessPending: (params = {}) => request.post('/kb/document/process_pending', null, { params }),
  kbDocumentDelete: (data = {}) => request.post('/kb/document/delete', data),
  kbDocumentUpload: (spaceId, file, title = '') => {
    const formData = new FormData()
    formData.append('file', file)
    const query = `space_id=${encodeURIComponent(spaceId)}&title=${encodeURIComponent(title || '')}`
    return request.post(`/kb/document/upload?${query}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  kbSessionList: (params = {}) => request.get('/kb/session/list', { params }),
  kbSessionCreate: (data = {}) => request.post('/kb/session/create', data),
  kbSessionMessages: (params = {}) => request.get('/kb/session/messages', { params }),
  kbChatAsk: (data = {}) => request.post('/kb/chat/ask', data),
  kbFeedbackCreate: (data = {}) => request.post('/kb/feedback/create', data),
  kbFeedbackList: (params = {}) => request.get('/kb/feedback/list', { params }),
  kbLlmLogList: (params = {}) => request.get('/kb/llm/log/list', { params }),
  kbLlmTest: () => request.get('/kb/llm/test'),
}

let _token = null

export function setToken(t) { _token = t }

const BASE = '/api'

async function req(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (_token) headers['Authorization'] = `Bearer ${_token}`
  const res = await fetch(BASE + url, { ...options, headers })
  if (!res.ok) {
    if (res.status === 401) {
      const { default: app } = await import('./App')
      if (app?.handleLogout) app.handleLogout()
    }
    throw new Error(await res.text())
  }
  return res.json()
}

export const api = {
  setToken,
  getTopics: () => req('/topics'),
  createTopic: (title) => req('/topics', { method: 'POST', body: JSON.stringify({ title }) }),
  deleteTopic: (id) => req(`/topics/${id}`, { method: 'DELETE' }),

  getChats: (topicId) => req(`/topics/${topicId}/chats`),
  createChat: (topicId, title) => req('/chats', { method: 'POST', body: JSON.stringify({ topic_id: topicId, title }) }),
  deleteChat: (id) => req(`/chats/${id}`, { method: 'DELETE' }),

  getMessages: (chatId) => req(`/chats/${chatId}/messages`),
  sendMessage: (chatId, content, kbId) => {
    let url = `/chats/${chatId}/messages`
    if (kbId) url += `?kb_id=${kbId}`
    return req(url, { method: 'POST', body: JSON.stringify({ content }) })
  },

  getKnowledgebases: () => req('/knowledgebases'),
  createKnowledgebase: (data) => req('/knowledgebases', { method: 'POST', body: JSON.stringify(data) }),
  deleteKnowledgebase: (id) => req(`/knowledgebases/${id}`, { method: 'DELETE' }),
  getKbFiles: (id) => req(`/knowledgebases/${id}/files`),
  importToKb: (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetch(`/api/knowledgebases/${id}/import`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${_token}` },
      body: formData,
    }).then(r => r.json())
  },
}

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
  sendMessage: (chatId, content) => req(`/chats/${chatId}/messages`, { method: 'POST', body: JSON.stringify({ content }) }),
}

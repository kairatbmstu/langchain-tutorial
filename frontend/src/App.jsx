import React, { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import AuthPage from './components/AuthPage'
import { api } from './api'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [userId, setUserId] = useState(() => parseInt(localStorage.getItem('userId') || '0'))
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('userEmail') || '')

  const [topics, setTopics] = useState([])
  const [activeTopicId, setActiveTopicId] = useState(null)
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [messages, setMessages] = useState([])
  const [sending, setSending] = useState(false)
  const [driveConnected, setDriveConnected] = useState(false)

  api.setToken(token)

  const handleAuth = (newToken, newUserId, newEmail) => {
    localStorage.setItem('token', newToken)
    localStorage.setItem('userId', newUserId)
    localStorage.setItem('userEmail', newEmail)
    setToken(newToken)
    setUserId(newUserId)
    setUserEmail(newEmail)
    api.setToken(newToken)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('userEmail')
    setToken(null)
    setUserId(0)
    setUserEmail('')
    api.setToken(null)
    setTopics([])
    setChats([])
    setMessages([])
  }

  const loadTopics = useCallback(async () => {
    if (!token) return
    try {
      const data = await api.getTopics()
      setTopics(data)
    } catch { handleLogout() }
  }, [token])

  const loadChats = useCallback(async (topicId) => {
    if (!topicId) return
    try {
      const data = await api.getChats(topicId)
      setChats(data)
    } catch (e) { console.error(e) }
  }, [])

  const loadMessages = useCallback(async (chatId) => {
    if (!chatId) return
    try {
      const data = await api.getMessages(chatId)
      setMessages(data)
    } catch (e) { console.error(e) }
  }, [])

  useEffect(() => { loadTopics() }, [token])
  useEffect(() => { loadChats(activeTopicId) }, [activeTopicId, token])
  useEffect(() => { loadMessages(activeChatId) }, [activeChatId, token])

  useEffect(() => {
    if (!token) return
    ;(async () => {
      try {
        const res = await fetch('/api/drive/status', { headers: { Authorization: `Bearer ${token}` } })
        const data = await res.json()
        setDriveConnected(data.connected)
      } catch {}
    })()
  }, [token])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('drive') === 'connected') {
      setDriveConnected(true)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const handleCreateTopic = async () => {
    const topic = await api.createTopic('New Topic')
    setTopics((prev) => [topic, ...prev])
    setActiveTopicId(topic.id)
  }

  const handleDeleteTopic = async (id) => {
    await api.deleteTopic(id)
    setTopics((prev) => prev.filter((t) => t.id !== id))
    if (activeTopicId === id) { setActiveTopicId(null); setActiveChatId(null) }
  }

  const handleCreateChat = async () => {
    if (!activeTopicId) return
    const chat = await api.createChat(activeTopicId, 'New Chat')
    setChats((prev) => [chat, ...prev])
    setActiveChatId(chat.id)
    setMessages([])
  }

  const handleDeleteChat = async (id) => {
    await api.deleteChat(id)
    setChats((prev) => prev.filter((c) => c.id !== id))
    if (activeChatId === id) { setActiveChatId(null); setMessages([]) }
  }

  const handleSend = async (content) => {
    let chatId = activeChatId
    if (!chatId) {
      let topicId = activeTopicId
      if (!topicId) {
        const topic = await api.createTopic('New Topic')
        setTopics((prev) => [topic, ...prev])
        setActiveTopicId(topic.id)
        topicId = topic.id
      }
      const chat = await api.createChat(topicId, 'New Chat')
      setChats((prev) => [chat, ...prev])
      setActiveChatId(chat.id)
      chatId = chat.id
    }

    setSending(true)
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content, chat_id: chatId }])

    try {
      const result = await api.sendMessage(chatId, content)
      setMessages((prev) => [...prev, result.assistant_message])
      loadChats(activeTopicId)
    } catch (e) { console.error(e) }
    setSending(false)
  }

  const handleUpload = async (file) => {
    let chatId = activeChatId
    if (!chatId) {
      let topicId = activeTopicId
      if (!topicId) {
        const topic = await api.createTopic('New Topic')
        setTopics((prev) => [topic, ...prev])
        setActiveTopicId(topic.id)
        topicId = topic.id
      }
      const chat = await api.createChat(topicId, 'New Chat')
      setChats((prev) => [chat, ...prev])
      setActiveChatId(chat.id)
      chatId = chat.id
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('chat_id', chatId)

    try {
      const result = await fetch('/api/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const data = await result.json()
      const msg = `\u{1F4C4} Uploaded **${data.original_name}** (${data.text_length} chars extracted). You can now ask me questions about it.`
      setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content: `Uploaded: ${data.original_name}` }])
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content: msg }])
    } catch (e) { console.error(e) }
  }

  if (!token) {
    return <AuthPage onAuth={handleAuth} />
  }

  return (
    <div className="app">
      <Sidebar
        topics={topics}
        activeTopicId={activeTopicId}
        onSelectTopic={(id) => { setActiveTopicId(id); setActiveChatId(null) }}
        onCreateTopic={handleCreateTopic}
        onDeleteTopic={handleDeleteTopic}
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onCreateChat={handleCreateChat}
        onDeleteChat={handleDeleteChat}
        userEmail={userEmail}
        onLogout={handleLogout}
        driveConnected={driveConnected}
        token={token}
      />
      <ChatArea
        messages={messages}
        sending={sending}
        onSend={handleSend}
        onUpload={handleUpload}
        chatTitle={chats.find((c) => c.id === activeChatId)?.title}
      />
    </div>
  )
}

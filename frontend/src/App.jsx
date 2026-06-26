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

  const [knowledgebases, setKnowledgebases] = useState([])
  const [activeKbId, setActiveKbId] = useState(null)
  const [kbFiles, setKbFiles] = useState({})

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
    setKnowledgebases([])
    setActiveKbId(null)
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

  const loadKbs = useCallback(async () => {
    if (!token) return
    try {
      const data = await api.getKnowledgebases()
      setKnowledgebases(data)
    } catch (e) { console.error(e) }
  }, [token])

  const loadKbFiles = useCallback(async (kbId) => {
    try {
      const data = await api.getKbFiles(kbId)
      setKbFiles((prev) => ({ ...prev, [kbId]: data }))
    } catch (e) { console.error(e) }
  }, [])

  useEffect(() => { loadTopics() }, [token])
  useEffect(() => { loadKbs() }, [token])
  useEffect(() => { loadChats(activeTopicId) }, [activeTopicId, token])
  useEffect(() => { loadMessages(activeChatId) }, [activeChatId, token])
  useEffect(() => { if (activeKbId) loadKbFiles(activeKbId) }, [activeKbId])

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
      const result = await api.sendMessage(chatId, content, activeKbId)
      setMessages((prev) => [...prev, { ...result.assistant_message, tool_calls: result.tool_calls }])
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

  const handleCreateKb = async () => {
    const name = prompt('Knowledgebase name:')
    if (!name) return
    const mode = prompt('Retrieval mode (fulltext / vector / hybrid):', 'hybrid')
    try {
      const kb = await api.createKnowledgebase({ name, retrieval_mode: mode || 'hybrid' })
      setKnowledgebases((prev) => [...prev, kb])
    } catch (e) { alert('Failed to create KB: ' + e.message) }
  }

  const handleDeleteKb = async (id) => {
    if (!confirm('Delete this knowledgebase?')) return
    await api.deleteKnowledgebase(id)
    setKnowledgebases((prev) => prev.filter((k) => k.id !== id))
    if (activeKbId === id) setActiveKbId(null)
  }

  const handleImportToKb = async (kbId, file) => {
    try {
      const result = await api.importToKb(kbId, file)
      if (result.status === 'completed') {
        alert(`Imported "${file.name}" — ${result.chunks} chunks created`)
        loadKbFiles(kbId)
      } else if (result.status === 'skipped') {
        alert(`Skipped — "${file.name}" already exists in this knowledgebase`)
      } else {
        alert(`Import failed: ${result.error}`)
      }
    } catch (e) { alert('Import error: ' + e.message) }
  }

  const activeKb = knowledgebases.find((k) => k.id === activeKbId) || null

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
        knowledgebases={knowledgebases}
        activeKbId={activeKbId}
        onSelectKb={setActiveKbId}
        onCreateKb={handleCreateKb}
        onDeleteKb={handleDeleteKb}
        onImportToKb={handleImportToKb}
        kbFiles={kbFiles}
      />
      <ChatArea
        messages={messages}
        sending={sending}
        onSend={handleSend}
        onUpload={handleUpload}
        chatTitle={chats.find((c) => c.id === activeChatId)?.title}
        activeKb={activeKb}
      />
    </div>
  )
}

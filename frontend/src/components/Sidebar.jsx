import React, { useCallback } from 'react'

export default function Sidebar({
  topics, activeTopicId, onSelectTopic, onCreateTopic, onDeleteTopic,
  chats, activeChatId, onSelectChat, onCreateChat, onDeleteChat,
  userEmail, onLogout, driveConnected, token,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>LlamaChat</h2>
        <p className="sidebar-user">{userEmail} <button className="link-small" onClick={onLogout}>logout</button></p>
        <p className="sidebar-account">
          {driveConnected
            ? <span className="drive-connected">✓ Drive connected</span>
            : <button className="btn-connect-drive" onClick={async () => {
              const res = await fetch('/api/drive/auth', { headers: { Authorization: `Bearer ${token}` } })
              const data = await res.json()
              if (data.auth_url) window.location.href = data.auth_url
            }}>+ Connect Google Drive</button>
          }
        </p>
        <button className="btn-new" onClick={onCreateChat}>+ New Chat</button>
      </div>

      <div className="sidebar-section">
        <h3>Topics</h3>
        <button className="btn-small" onClick={onCreateTopic}>+ Add Topic</button>
        <ul className="topic-list">
          {topics.map((t) => (
            <li
              key={t.id}
              className={t.id === activeTopicId ? 'active' : ''}
              onClick={() => onSelectTopic(t.id)}
            >
              <span className="topic-title">{t.title}</span>
              <button className="btn-icon" onClick={(e) => { e.stopPropagation(); onDeleteTopic(t.id) }}>×</button>
            </li>
          ))}
        </ul>
      </div>

      {activeTopicId && (
        <div className="sidebar-section">
          <h3>Chats</h3>
          <ul className="chat-list">
            {chats.map((c) => (
              <li
                key={c.id}
                className={c.id === activeChatId ? 'active' : ''}
                onClick={() => onSelectChat(c.id)}
              >
                <span className="chat-title">{c.title}</span>
                <button className="btn-icon" onClick={(e) => { e.stopPropagation(); onDeleteChat(c.id) }}>×</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  )
}

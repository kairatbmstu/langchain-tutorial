import React, { useState, useRef } from 'react'

const ACCEPT_TYPES = ".pdf,.docx,.pptx,.html,.htm,.csv,.xls,.xlsx,.json,.txt,.md,.png,.jpg,.jpeg,.gif,.webp"

export default function Sidebar({
  topics, activeTopicId, onSelectTopic, onCreateTopic, onDeleteTopic,
  chats, activeChatId, onSelectChat, onCreateChat, onDeleteChat,
  userEmail, onLogout, driveConnected, token,
  knowledgebases, activeKbId, onSelectKb, onCreateKb, onDeleteKb, onImportToKb, kbFiles,
}) {
  const fileRefs = useRef({})

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

      <div className="sidebar-section">
        <h3>Knowledgebases</h3>
        <button className="btn-small" onClick={onCreateKb}>+ Create KB</button>
        <ul className="kb-list">
          {knowledgebases.map((kb) => (
            <li
              key={kb.id}
              className={kb.id === activeKbId ? 'active' : ''}
              onClick={() => onSelectKb(kb.id)}
            >
              <div className="kb-info">
                <span className="kb-name">{kb.name}</span>
                <span className="kb-mode">{kb.retrieval_mode}</span>
              </div>
              <div className="kb-actions">
                <button className="btn-icon" onClick={(e) => {
                  e.stopPropagation()
                  fileRefs.current[kb.id]?.click()
                }} title="Import file">+</button>
                <button className="btn-icon" onClick={(e) => { e.stopPropagation(); onDeleteKb(kb.id) }} title="Delete KB">×</button>
              </div>
              <input
                ref={(el) => fileRefs.current[kb.id] = el}
                type="file"
                accept={ACCEPT_TYPES}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) onImportToKb(kb.id, f)
                  e.target.value = ''
                }}
                style={{ display: 'none' }}
              />
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}

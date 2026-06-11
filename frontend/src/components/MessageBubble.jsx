import React from 'react'

export default function MessageBubble({ role, content }) {
  return (
    <div className={`message ${role}`}>
      <div className="avatar">{role === 'user' ? 'U' : 'AI'}</div>
      <div className="bubble">{content}</div>
    </div>
  )
}

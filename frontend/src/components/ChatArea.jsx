import React, { useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import InputBar from './InputBar'

export default function ChatArea({ messages, sending, onSend, onUpload, chatTitle }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <main className="chat-area">
      <header className="chat-header">
        <h1>{chatTitle || 'ChatGPT Clone'}</h1>
      </header>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome">
            <p>Ask me anything! I have web search capabilities.</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {sending && (
          <div className="message assistant">
            <div className="bubble typing">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <InputBar onSend={onSend} onUpload={onUpload} disabled={sending} />
    </main>
  )
}

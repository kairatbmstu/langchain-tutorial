import React, { useState } from 'react'

export default function MessageBubble({ role, content, toolCalls }) {
  const [showTools, setShowTools] = useState(false)

  return (
    <div className={`message ${role}`}>
      <div className="avatar">{role === 'user' ? 'U' : 'AI'}</div>
      <div className="bubble-area">
        <div className="bubble">{content}</div>
        {toolCalls && toolCalls.length > 0 && (
          <div className="tool-calls">
            <button className="tool-toggle" onClick={() => setShowTools(!showTools)}>
              {showTools ? '▾' : '▸'} {toolCalls.length} tool call{toolCalls.length > 1 ? 's' : ''}
            </button>
            {showTools && (
              <div className="tool-log">
                {toolCalls.map((tc, i) => (
                  <div key={i} className="tool-entry">
                    <span className="tool-name">{tc.tool}</span>
                    <span className="tool-args">{JSON.stringify(tc.args)}</span>
                    {tc.result && <div className="tool-result">{tc.result}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

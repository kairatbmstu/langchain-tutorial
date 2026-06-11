import React, { useState, useRef } from 'react'

export default function InputBar({ onSend, onUpload, disabled }) {
  const [text, setText] = useState('')
  const fileRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!text.trim() || disabled) return
    onSend(text.trim())
    setText('')
  }

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (onUpload) await onUpload(file)
    e.target.value = ''
  }

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      <button type="button" className="btn-attach" onClick={() => fileRef.current?.click()} disabled={disabled}>
        📎
      </button>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Message Llama 3.1..."
        disabled={disabled}
      />
      <button type="submit" disabled={!text.trim() || disabled}>Send</button>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf"
        onChange={handleFile}
        style={{ display: 'none' }}
      />
    </form>
  )
}

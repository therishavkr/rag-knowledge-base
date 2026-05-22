import { useState, useEffect } from "react"
import axios from "axios"
import config from "../config"

function Chat({ refreshTrigger }) {
  const [messages, setMessages] = useState([])
  const [chatHistory, setChatHistory] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [availableDocs, setAvailableDocs] = useState([])
  const [selectedDocs, setSelectedDocs] = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [mode, setMode] = useState("ai")



  // Load available documents on mount
useEffect(() => {
  fetchDocuments()
}, [refreshTrigger])

  

const fetchDocuments = async () => {
  try {
    setDocsLoading(true)
    await new Promise(resolve => setTimeout(resolve, 800))
    const res = await axios.get(`${config.BASE_URL}/documents`)
    
    setAvailableDocs(res.data.documents)
  } catch (err) {
    console.error("Could not fetch documents")
  } finally {
    setDocsLoading(false)
  }
}

  const toggleDoc = (doc) => {
    setSelectedDocs(prev =>
      prev.includes(doc)
        ? prev.filter(d => d !== doc)
        : [...prev, doc]
    )
  }

  const deleteDoc = async (doc) => {
  try {
    await axios.delete(`${config.BASE_URL}/documents/${doc}`)
    setAvailableDocs(prev => prev.filter(d => d !== doc))
    setSelectedDocs(prev => prev.filter(d => d !== doc))
  } catch (err) {
    alert("Failed to delete document.")
  }
}

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = { role: "user", text: input }
    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post(`${config.BASE_URL}/ask`, {
        question: input,
        chat_history: chatHistory,
        selected_docs: selectedDocs,
        mode: mode
      })

      const botMessage = {
        role: "bot",
        text: res.data.answer,
        sources: res.data.sources
      }

      setMessages(prev => [...prev, botMessage])
      setChatHistory(prev => [...prev, {
        question: input,
        answer: res.data.answer
      }])

    } catch (err) {
      setMessages(prev => [...prev, {
        role: "bot",
        text: "Something went wrong. Please try again."
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage()
  }

  const clearChat = () => {
    setMessages([])
    setChatHistory([])
  }

  return (
    <div className="chat-box">
      <div className="chat-header">
        <h2>💬 Ask Your Documents</h2>
        {messages.length > 0 && (
          <button className="clear-btn" onClick={clearChat}>Clear Chat</button>
        )}
      </div>

      {/* Document Selector */}
      {availableDocs.length > 0 && (
        <div className="doc-selector">
  <div className="doc-selector-header">
    <p>Search in:</p>
    {docsLoading && <span style={{fontSize: "0.8rem", color: "#888"}}>updating...</span>}
    <button className="refresh-btn" onClick={fetchDocuments}>🔄</button>
  </div>
  <div className="doc-tags">
  <button
    className={`doc-tag ${selectedDocs.length === 0 ? "active" : ""}`}
    onClick={() => setSelectedDocs([])}
  >
    All Documents
  </button>
  {availableDocs.map((doc, i) => (
    <div key={i} className="doc-tag-wrapper">
      <button
        className={`doc-tag ${selectedDocs.includes(doc) ? "active" : ""}`}
        onClick={() => toggleDoc(doc)}
      >
        📄 {doc.replace("doc_", "").replace(/_/g, " ")}
      </button>
      <button
        className="delete-doc-btn"
        onClick={() => deleteDoc(doc)}
        title="Remove from knowledge base"
      >
        ✕
      </button>
    </div>
  ))}
</div>
</div>
      )}

      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-state">Upload a PDF and start asking questions!</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <p>{msg.text}</p>
            {msg.sources && msg.sources.length > 0 && (
              <div className="sources">
                📌 Sources: {msg.sources.join(", ")}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message bot"><p>Thinking...</p></div>
        )}
      </div>

      {/* Mode Toggle */}
<div className="mode-toggle">
  <button
    className={`mode-btn ${mode === "ai" ? "active" : ""}`}
    onClick={() => setMode("ai")}
  >
    🧠 AI Answer
  </button>
  <button
    className={`mode-btn ${mode === "search" ? "active" : ""}`}
    onClick={() => setMode("search")}
  >
    🔍 Raw Search
  </button>
</div>

      <div className="input-row">
        <input
          type="text"
          placeholder="Ask something about your documents..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>Send</button>
      </div>
    </div>
  )
}

export default Chat
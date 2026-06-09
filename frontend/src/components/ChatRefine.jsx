import { useState } from "react"
import axios from "axios"
import config from "../config"

export default function ChatRefine({
  profile,
  previousPreferences,
  suggestedQuestions,
  onUpdateRecommendations,
}) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Ask me to refine your recommendations — try filtering by slot, credits, or topic." }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  async function sendMessage(text) {
    const msg = text.trim()
    if (!msg) return
    setInput("")
    const newMsgs = [...messages, { role: "user", content: msg }]
    setMessages(newMsgs)
    setLoading(true)

    try {
      const res = await axios.post(`${config.BASE_URL}/api/v1/chat-recommend`, {
        message: msg,
        profile,
        previous_preferences: previousPreferences,
        chat_history: newMsgs.slice(-8).map(m => ({ role: m.role, content: m.content })),
      })
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: res.data.reply }
      ])
      if (res.data.updated_recommendations) {
        onUpdateRecommendations(res.data.updated_recommendations)
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card chat-refine">
      <h3 className="card-title">💬 Refine with Chat</h3>

      {suggestedQuestions.length > 0 && (
        <div className="suggested-qs">
          {suggestedQuestions.map((q, i) => (
            <button key={i} className="suggested-q" onClick={() => sendMessage(q)}>
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <p>{m.content}</p>
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <span className="spinner-sm" /> Thinking…
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="e.g. only show 9-credit courses in slot B…"
          onKeyDown={e => e.key === "Enter" && !loading && sendMessage(input)}
          disabled={loading}
        />
        <button
          className="btn-primary"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}

import { useState, useEffect, useRef } from "react"
import axios from "axios"
import config from "../config"

const WORKLOAD_OPTIONS = [
  { value: "light", label: "Light", desc: "Fewer credits, less intensive" },
  { value: "medium", label: "Medium", desc: "Balanced workload" },
  { value: "heavy", label: "Heavy", desc: "Advanced / research-level" },
]

export default function PreferencesForm({ profile, gradeCardData, onRecommendationsReady, onBack }) {
  const [interests, setInterests] = useState("")
  const [workload, setWorkload] = useState("medium")
  const [minorTarget, setMinorTarget] = useState("")
  const [creditBudget, setCreditBudget] = useState(64)
  const [freeText, setFreeText] = useState("")
  const [minors, setMinors] = useState([])
  const [loading, setLoading] = useState(false)
  const [slowHint, setSlowHint] = useState(false)
  const [error, setError] = useState("")
  const slowTimer = useRef(null)

  useEffect(() => {
    axios.get(`${config.BASE_URL}/api/v1/minors`)
      .then(res => setMinors(res.data.minors || []))
      .catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")
    setSlowHint(false)
    setLoading(true)
    slowTimer.current = setTimeout(() => setSlowHint(true), 4000)
    try {
      const res = await axios.post(`${config.BASE_URL}/api/v1/preferences`, {
        profile,
        interests,
        workload_preference: workload,
        minor_target: minorTarget || null,
        credit_budget: creditBudget,
        free_text: freeText,
      })
      onRecommendationsReady(res.data, {
        interests,
        workload_preference: workload,
        minor_target: minorTarget || null,
        credit_budget: creditBudget,
        free_text: freeText,
      })
    } catch (err) {
      setError(err.response?.data?.detail || "Recommendation failed. Please try again.")
    } finally {
      setLoading(false)
      setSlowHint(false)
      clearTimeout(slowTimer.current)
    }
  }

  const occupiedSlots = gradeCardData?.occupied_slots || []

  return (
    <div className="card">
      {/* Profile summary bar */}
      <div className="profile-bar">
        <div className="profile-bar-left">
          <div className="profile-avatar">{profile.name?.[0] || "?"}</div>
          <div>
            <p className="profile-name">{profile.name}</p>
            <p className="profile-meta">
              {profile.dept_code} · Semester {profile.next_semester} · CGPA {profile.cgpa}
            </p>
          </div>
        </div>
        <div className="slot-chips">
          {occupiedSlots.length > 0 && (
            <>
              <span className="chip chip-warn">Occupied slots: </span>
              {occupiedSlots.map(s => (
                <span key={s} className="chip chip-slot">{s}</span>
              ))}
            </>
          )}
        </div>
      </div>

      <h2 className="card-title">⚙️ Set Your Preferences</h2>

      <form onSubmit={handleSubmit} className="prefs-form">
        <div className="form-group">
          <label>What topics interest you?</label>
          <textarea
            value={interests}
            onChange={e => setInterests(e.target.value)}
            placeholder="e.g. machine learning, signal processing, economics, robotics…"
            rows={3}
          />
        </div>

        <div className="form-group">
          <label>Preferred workload</label>
          <div className="workload-toggle">
            {WORKLOAD_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`workload-btn ${workload === opt.value ? "active" : ""}`}
                onClick={() => setWorkload(opt.value)}
              >
                <span className="workload-label">{opt.label}</span>
                <span className="workload-desc">{opt.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Minor stream (optional)</label>
          <select value={minorTarget} onChange={e => setMinorTarget(e.target.value)}>
            <option value="">— No specific minor —</option>
            {minors.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="form-group form-row">
          <div className="form-col">
            <label>Credit budget per semester</label>
            <input
              type="number"
              min={9}
              max={80}
              value={creditBudget}
              onChange={e => setCreditBudget(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Additional notes (optional)</label>
          <textarea
            value={freeText}
            onChange={e => setFreeText(e.target.value)}
            placeholder="e.g. I want to avoid courses with programming assignments…"
            rows={2}
          />
        </div>

        {error && <p className="error-msg">⚠️ {error}</p>}

        <div className="form-actions">
          <button type="button" className="btn-ghost" onClick={onBack}>← Back</button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? (
              <><span className="spinner-sm" /> Finding best courses…</>
            ) : (
              "🎯 Get Recommendations"
            )}
          </button>
        </div>
        {slowHint && (
          <p className="loading-hint">
            ⏳ Searching course catalog and ranking with AI — usually 5–10 seconds…
          </p>
        )}
      </form>
    </div>
  )
}

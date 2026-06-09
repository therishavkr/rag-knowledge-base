import { useState, useRef } from "react"
import axios from "axios"
import config from "../config"

export default function GradeCardUpload({ onProfileReady }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const fileRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.")
      return
    }
    setError("")
    setLoading(true)
    try {
      const form = new FormData()
      form.append("file", file)
      const res = await axios.post(`${config.BASE_URL}/api/v1/grade-card`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      onProfileReady(res.data.profile, {
        mandatory_courses: res.data.mandatory_courses,
        occupied_slots: res.data.occupied_slots,
        credit_summary: res.data.credit_summary,
        suggested_questions: res.data.suggested_questions,
      })
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to parse grade card. Please ensure it is a valid IITM grade card PDF."
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2 className="card-title">📄 Upload Grade Card</h2>
      <p className="card-desc">
        Upload your latest IITM grade card PDF. We'll extract your courses, CGPA, and
        department automatically.
      </p>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${loading ? "loading" : ""}`}
        onClick={() => !loading && fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          handleFile(e.dataTransfer.files[0])
        }}
      >
        {loading ? (
          <>
            <div className="spinner" />
            <p>Parsing your grade card…</p>
          </>
        ) : (
          <>
            <span className="drop-icon">📂</span>
            <p>Drag &amp; drop your grade card PDF here, or <strong>click to browse</strong></p>
            <p className="drop-hint">Supports IITM linear grade card format</p>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={e => handleFile(e.target.files?.[0])}
        />
      </div>

      {error && <p className="error-msg">⚠️ {error}</p>}

      <div className="info-chips">
        <span className="chip">✓ Roll number &amp; dept auto-detected</span>
        <span className="chip">✓ CGPA extracted</span>
        <span className="chip">✓ Course history parsed</span>
        <span className="chip">✓ No data stored on server</span>
      </div>
    </div>
  )
}

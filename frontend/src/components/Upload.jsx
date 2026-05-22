import { useState } from "react"
import axios from "axios"

function Upload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState([])

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setUploading(true)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await axios.post("http://localhost:8000/upload", formData)
      setUploadedFiles(prev => [...prev, res.data.filename])
      onUploadSuccess(res.data.filename)
    } catch (err) {
      alert("Upload failed. Is your backend running?")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-box">
      <h2>📂 Upload Documents</h2>

      <label className="upload-btn">
        {uploading ? "Uploading..." : "Choose PDF"}
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={uploading}
          hidden
        />
      </label>

      {uploadedFiles.length > 0 && (
        <div className="file-list">
          <p>Uploaded:</p>
          {uploadedFiles.map((f, i) => (
            <span key={i} className="file-tag">📄 {f}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export default Upload
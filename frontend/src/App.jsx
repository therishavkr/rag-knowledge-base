import { useState } from "react"
import Upload from "./components/Upload"
import Chat from "./components/Chat"

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleUploadSuccess = () => {
    setRefreshTrigger(prev => prev + 1)  // increment to trigger refresh
  }

  return (
    <div className="app">
      <header>
        <h1>🧠 RAG Knowledge Base</h1>
        <p>Upload documents and chat with them using AI</p>
      </header>

      <main>
        <Upload onUploadSuccess={handleUploadSuccess} />
        <Chat refreshTrigger={refreshTrigger} />
      </main>
    </div>
  )
}

export default App
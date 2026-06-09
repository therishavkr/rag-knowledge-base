import { useState } from "react"
import Upload from "./components/Upload"
import Chat from "./components/Chat"
import GradeCardUpload from "./components/GradeCardUpload"
import PreferencesForm from "./components/PreferencesForm"
import RecommendationPanel from "./components/RecommendationPanel"
import SemesterGrid from "./components/SemesterGrid"
import CreditTracker from "./components/CreditTracker"
import ChatRefine from "./components/ChatRefine"

function App() {
  const [view, setView] = useState("planner")
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Planner state
  const [plannerStep, setPlannerStep] = useState("upload") // "upload" | "prefs" | "results"
  const [profile, setProfile] = useState(null)
  const [gradeCardData, setGradeCardData] = useState(null)   // {mandatory_courses, occupied_slots, credit_summary}
  const [recommendations, setRecommendations] = useState(null)
  const [selectedElectives, setSelectedElectives] = useState(
    () => JSON.parse(localStorage.getItem("slc_selected_electives") || "[]")
  )
  const [currentPrefs, setCurrentPrefs] = useState(null)

  function handleProfileReady(profileData, gcData) {
    setProfile(profileData)
    setGradeCardData(gcData)
    setPlannerStep("prefs")
  }

  function handleRecommendationsReady(result, prefs) {
    setRecommendations(result)
    setCurrentPrefs(prefs)
    setSelectedElectives([])
    localStorage.removeItem("slc_selected_electives")
    setPlannerStep("results")
  }

  function handleAddElective(course) {
    setSelectedElectives(prev => {
      if (prev.find(c => c.course_no === course.course_no)) return prev
      const updated = [...prev, course]
      localStorage.setItem("slc_selected_electives", JSON.stringify(updated))
      return updated
    })
  }

  function handleRemoveElective(courseNo) {
    setSelectedElectives(prev => {
      const updated = prev.filter(c => c.course_no !== courseNo)
      localStorage.setItem("slc_selected_electives", JSON.stringify(updated))
      return updated
    })
  }

  function handleUpdateRecommendations(newResult) {
    if (newResult) setRecommendations(newResult)
  }

  function handleReset() {
    setProfile(null)
    setGradeCardData(null)
    setRecommendations(null)
    setSelectedElectives([])
    setCurrentPrefs(null)
    setPlannerStep("upload")
    localStorage.removeItem("slc_selected_electives")
  }

  return (
    <div className="app">
      <header>
        <h1>🎓 IITM Course Planner</h1>
        <p>Upload your grade card, set preferences, and plan your ideal semester</p>
        <div className="tab-bar">
          <button
            className={`tab-btn ${view === "planner" ? "active" : ""}`}
            onClick={() => setView("planner")}
          >
            📅 Course Planner
          </button>
          <button
            className={`tab-btn ${view === "rag" ? "active" : ""}`}
            onClick={() => setView("rag")}
          >
            🧠 Document Chat
          </button>
        </div>
      </header>

      <main>
        {view === "planner" && (
          <>
            {plannerStep === "upload" && (
              <GradeCardUpload onProfileReady={handleProfileReady} />
            )}

            {plannerStep === "prefs" && profile && (
              <PreferencesForm
                profile={profile}
                gradeCardData={gradeCardData}
                onRecommendationsReady={handleRecommendationsReady}
                onBack={handleReset}
              />
            )}

            {plannerStep === "results" && recommendations && profile && (
              <>
                <div className="results-header">
                  <div>
                    <h2>Semester {profile.next_semester} Plan</h2>
                    <p className="results-subtitle">
                      {profile.name} · {profile.dept_code} · CGPA {profile.cgpa}
                    </p>
                  </div>
                  <button className="btn-ghost" onClick={handleReset}>↩ Start Over</button>
                </div>

                <SemesterGrid
                  mandatoryCourses={recommendations.mandatory_courses}
                  selectedElectives={selectedElectives}
                  onRemoveElective={handleRemoveElective}
                />

                <div className="results-columns">
                  <RecommendationPanel
                    recommendations={recommendations}
                    selectedElectives={selectedElectives}
                    onAddElective={handleAddElective}
                    onRemoveElective={handleRemoveElective}
                  />
                  <div className="results-sidebar">
                    <CreditTracker
                      creditSummary={recommendations.credit_summary}
                      selectedElectives={selectedElectives}
                    />
                    {currentPrefs && (
                      <ChatRefine
                        profile={profile}
                        previousPreferences={currentPrefs}
                        suggestedQuestions={gradeCardData?.suggested_questions || []}
                        onUpdateRecommendations={handleUpdateRecommendations}
                      />
                    )}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {view === "rag" && (
          <>
            <Upload onUploadSuccess={() => setRefreshTrigger(p => p + 1)} />
            <Chat refreshTrigger={refreshTrigger} />
          </>
        )}
      </main>
    </div>
  )
}

export default App

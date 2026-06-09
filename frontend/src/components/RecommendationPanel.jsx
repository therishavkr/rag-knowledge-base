export default function RecommendationPanel({
  recommendations,
  selectedElectives,
  onAddElective,
  onRemoveElective,
}) {
  const { recommended_electives = [], also_consider = [], minor_progress } = recommendations
  const selectedNos = new Set(selectedElectives.map(c => c.course_no))

  function CourseCard({ course, showExplanation }) {
    const isAdded = selectedNos.has(course.course_no)
    return (
      <div className={`course-card ${isAdded ? "added" : ""}`}>
        <div className="course-card-top">
          <div>
            <span className="course-code">{course.course_no}</span>
            {course.minor_aligned && <span className="badge badge-minor">★ Minor</span>}
            <h4 className="course-name">{course.course_name}</h4>
          </div>
          <button
            className={`add-btn ${isAdded ? "remove" : "add"}`}
            onClick={() => isAdded ? onRemoveElective(course.course_no) : onAddElective(course)}
          >
            {isAdded ? "✓ Added" : "+ Add"}
          </button>
        </div>
        <div className="course-meta">
          <span className="badge badge-slot">Slot {course.slot}</span>
          <span className="badge badge-credit">{course.credits} credits</span>
          {course.instructor && (
            <span className="course-instructor">👤 {course.instructor}</span>
          )}
        </div>
        {showExplanation && course.explanation && (
          <p className="course-explanation">💡 {course.explanation}</p>
        )}
      </div>
    )
  }

  return (
    <div className="recommendation-panel">
      <div className="panel-section">
        <h3 className="panel-title">🎯 Recommended Electives</h3>
        <p className="panel-subtitle">AI-ranked based on your profile and interests</p>
        {recommended_electives.length === 0 ? (
          <div className="empty-state">
            No electives found matching your constraints. Try relaxing your filters.
          </div>
        ) : (
          recommended_electives.map(c => (
            <CourseCard key={c.course_no} course={c} showExplanation={true} />
          ))
        )}
      </div>

      {also_consider.length > 0 && (
        <div className="panel-section">
          <h3 className="panel-title">📋 Also Consider</h3>
          {also_consider.map(c => (
            <CourseCard key={c.course_no} course={c} showExplanation={false} />
          ))}
        </div>
      )}

      {minor_progress && (
        <div className="panel-section minor-progress-box">
          <h3 className="panel-title">🏅 Minor Progress — {minor_progress.minor_name}</h3>
          <p>
            <strong>{minor_progress.completed}</strong> / {minor_progress.total_courses} courses completed
          </p>
          {minor_progress.remaining_codes.length > 0 && (
            <p className="minor-remaining">
              Still needed: {minor_progress.remaining_codes.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

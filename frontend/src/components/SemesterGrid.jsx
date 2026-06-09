export default function SemesterGrid({ mandatoryCourses, selectedElectives, onRemoveElective }) {
  // Build slot → courses map
  const slotMap = {}

  for (const c of mandatoryCourses) {
    if (!c.slot) continue
    if (!slotMap[c.slot]) slotMap[c.slot] = []
    slotMap[c.slot].push({ ...c, type: "mandatory" })
  }

  for (const c of selectedElectives) {
    if (!c.slot) continue
    if (!slotMap[c.slot]) slotMap[c.slot] = []
    slotMap[c.slot].push({ ...c, type: "elective" })
  }

  const allSlots = Object.keys(slotMap).sort()

  const totalMandatoryCredits = mandatoryCourses.reduce((s, c) => s + (c.credits || 0), 0)
  const totalElectiveCredits = selectedElectives.reduce((s, c) => s + (c.credits || 0), 0)
  const totalCredits = totalMandatoryCredits + totalElectiveCredits

  // Detect conflicts: slots with more than one entry
  const conflictSlots = new Set(
    allSlots.filter(s => slotMap[s].length > 1)
  )

  if (allSlots.length === 0) {
    return (
      <div className="card semester-grid-card">
        <p className="empty-state">
          No courses scheduled yet. Add electives from the recommendation panel below.
        </p>
      </div>
    )
  }

  return (
    <div className="card semester-grid-card">
      <div className="grid-header">
        <h3>📅 Semester Schedule</h3>
        <div className="credit-counter">
          <span className={totalCredits > 64 ? "over-budget" : ""}>
            {totalCredits} credits
          </span>
          <span className="credit-limit"> / 64 cap</span>
          <span className="credit-breakdown">
            ({totalMandatoryCredits} mandatory + {totalElectiveCredits} elective)
          </span>
        </div>
      </div>

      <div className="slot-grid">
        {allSlots.map(slot => {
          const courses = slotMap[slot]
          const hasConflict = conflictSlots.has(slot)
          return (
            <div key={slot} className={`slot-row ${hasConflict ? "conflict" : ""}`}>
              <div className="slot-label">
                Slot {slot}
                {hasConflict && <span className="conflict-badge">⚠ Clash</span>}
              </div>
              <div className="slot-courses">
                {courses.map((c, i) => (
                  <div key={i} className={`slot-course-chip ${c.type}`}>
                    <span className="chip-code">{c.course_no}</span>
                    <span className="chip-name">{c.course_name}</span>
                    <span className="chip-credits">{c.credits}cr</span>
                    {c.type === "elective" && (
                      <button
                        className="chip-remove"
                        onClick={() => onRemoveElective(c.course_no)}
                        title="Remove from plan"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid-legend">
        <span className="legend-item mandatory">■ Mandatory</span>
        <span className="legend-item elective">■ Elective</span>
        <span className="legend-item conflict">⚠ Slot clash</span>
      </div>
    </div>
  )
}

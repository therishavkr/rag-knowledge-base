export default function CreditTracker({ creditSummary, selectedElectives }) {
  if (!creditSummary) return null

  const electiveCredits = selectedElectives.reduce((s, c) => s + (c.credits || 0), 0)

  const categories = Object.entries(creditSummary).filter(
    ([, v]) => v.required > 0
  )

  return (
    <div className="card credit-tracker">
      <h3 className="card-title">📊 Credit Tracker</h3>
      <p className="card-desc">Program-wide progress across all categories</p>

      <table className="credit-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Earned</th>
            <th>Required</th>
            <th>Remaining</th>
          </tr>
        </thead>
        <tbody>
          {categories.map(([key, v]) => {
            const pct = Math.min(100, Math.round((v.earned / v.required) * 100))
            const done = v.remaining === 0
            return (
              <tr key={key} className={done ? "row-done" : ""}>
                <td className="cat-label">{v.label}</td>
                <td className="cat-num">{v.earned}</td>
                <td className="cat-num">{v.required}</td>
                <td className={`cat-num ${done ? "done" : "pending"}`}>
                  {done ? "✓" : v.remaining}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {electiveCredits > 0 && (
        <p className="credit-note">
          + {electiveCredits} credits from your selected electives this semester
        </p>
      )}
    </div>
  )
}

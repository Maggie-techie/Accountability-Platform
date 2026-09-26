import { CheckCircle2, AlertTriangle, Copy, FileWarning } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { KpiCard } from '../../components/Insights'
import { useState, useEffect } from 'react'
import APIService from '../../services/api'

export default function DataValidation() {
  const [stats, setStats] = useState({
    validRecords: 0,
    missingValues: 0,
    duplicateRecords: 0,
    invalidFormats: 0
  })
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [apiError, setApiError] = useState(null)

  useEffect(() => {
    const fetchValidationData = async () => {
      try {
        setLoading(true)
        setApiError(null)

        // Try to fetch validation data from API
        const response = await fetch(`${APIService.baseURL}/validation`)

        if (!response.ok) {
          if (response.status === 404) {
            // Validation endpoint doesn't exist, show informative message
            setApiError('Validation data endpoint not available. Using mock data for demonstration.')
            // Fall back to mock data
            setMockData()
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }
        } else {
          // Successfully fetched validation data
          const data = await response.json()
          setStats(data.stats || {
            validRecords: 0,
            missingValues: 0,
            duplicateRecords: 0,
            invalidFormats: 0
          })
          setIssues(data.issues || [])
        }
      } catch (err) {
        console.error('Error fetching validation data:', err)
        setApiError(err.message || 'Failed to load validation data')
        // Fall back to mock data on error
        setMockData()
      } finally {
        setLoading(false)
      }
    }

    // Mock data function for fallback
    const setMockData = () => {
      setStats({
        validRecords: 4187,
        missingValues: 9,
        duplicateRecords: 4,
        invalidFormats: 3
      })
      setIssues([
        { id: 1, type: 'Inconsistent financial year', record: 'Mathira allocation row 14', detail: '"FY2024-25" should be "2024/25"', icon: FileWarning, tone: 'watch' },
        { id: 2, type: 'Duplicate record', record: 'Nyeri Town audit finding row 8', detail: 'Matches existing record AF-003', icon: Copy, tone: 'watch' },
        { id: 3, type: 'Missing value', record: 'Dept Spending Tracker row 22', detail: 'q3_spend_kshm is empty', icon: AlertTriangle, tone: 'risk' },
      ])
    }

    fetchValidationData()
  }, [])

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Data validation</h1>
        <p className="text-ink-muted mb-6">Loading validation data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Data validation</h1>
        <p className="text-ink-danger mb-6">{error}</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Data validation</h1>
      <p className="text-ink-muted mb-6">Review data-quality issues before they go live on the public platform.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Valid records" value={stats.validRecords.toLocaleString()} changeTone="up" />
        <KpiCard label="Missing values" value={stats.missingValues} changeTone="down" />
        <KpiCard label="Duplicate records" value={stats.duplicateRecords} changeTone="down" />
        <KpiCard label="Invalid formats" value={stats.invalidFormats} changeTone="down" />
      </div>

      {apiError && (
        <div className="mb-4 p-3 bg-clay-50 border border-clay-100 rounded text-sm text-clay-600">
          {apiError}
        </div>
      )}

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Open issues</h3>
        {issues.length === 0 ? (
          <p className="text-ink-muted">No issues found.</p>
        ) : (
          <ul className="divide-y divide-line">
            {issues.map((i) => (
              <li key={i.id} className="py-4 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={`h-8 w-8 rounded flex items-center justify-center shrink-0 ${i.tone === 'risk' ? 'bg-clay-50 text-clay-500' : 'bg-gold-50 text-gold-500'}`}>
                    <i.icon size={15} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-ink">{i.type}</p>
                    <p className="text-xs text-ink-muted mt-0.5">{i.record}</p>
                    <p className="text-xs text-ink-faint mt-0.5">{i.detail}</p>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="secondary">Fix</Button>
                  <Button size="sm" variant="ghost">Ignore</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="flex items-center gap-2 text-sm text-forest-700 mt-4 pt-4 border-t border-line">
          <CheckCircle2 size={16} /> All other records passed validation and are ready to import.
        </div>
      </Card>
    </div>
  )
}

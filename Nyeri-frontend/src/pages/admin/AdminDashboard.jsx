import { useState, useEffect, useCallback } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { CheckCircle2, BrainCircuit, AlertTriangle } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { KpiCard } from '../../components/Insights'
import APIService from '../../services/api'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// The API wraps payloads as { success, data }. Unwrap safely.
const unwrap = (json) => (json && typeof json === 'object' && 'data' in json ? json.data : json)

// Always return an array, whatever shape the backend sends.
const toArray = (value, ...keys) => {
  if (Array.isArray(value)) return value
  for (const key of keys) {
    if (Array.isArray(value?.[key])) return value[key]
  }
  return []
}

const fmt = (n) => Number(n ?? 0).toLocaleString()

// Count imports per weekday (Mon..Sun) from import history dates.
const buildWeeklyImports = (imports) => {
  const counts = Object.fromEntries(DAYS.map((d) => [d, 0]))
  const now = new Date()
  const weekAgo = new Date(now)
  weekAgo.setDate(now.getDate() - 6)
  weekAgo.setHours(0, 0, 0, 0)

  imports.forEach((imp) => {
    const raw = imp?.date ?? imp?.created_at
    const d = raw ? new Date(raw) : null
    if (!d || Number.isNaN(d.getTime()) || d < weekAgo || d > now) return
    const label = DAYS[(d.getDay() + 6) % 7] // JS: Sunday = 0
    counts[label] += 1
  })

  return DAYS.map((day) => ({ day, imports: counts[day] }))
}

export default function AdminDashboard() {
  const [adminSummary, setAdminSummary] = useState(null)
  const [importHistory, setImportHistory] = useState([])
  const [anomaliesData, setAnomaliesData] = useState([])
  const [weeklyImports, setWeeklyImports] = useState(DAYS.map((day) => ({ day, imports: 0 })))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null) // fatal: summary failed
  const [warnings, setWarnings] = useState([]) // non-fatal: partial failures
  const [reloadKey, setReloadKey] = useState(0)

  const retry = useCallback(() => setReloadKey((k) => k + 1), [])

  useEffect(() => {
    let cancelled = false

    const token = localStorage.getItem('authToken')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const getJson = async (path) => {
      const res = await fetch(`${APIService.baseURL}${path}`, { headers })
      if (!res.ok) throw new Error(`${path} returned ${res.status}`)
      return unwrap(await res.json())
    }

    const load = async () => {
      setLoading(true)
      setError(null)
      const newWarnings = []

      try {
        // Summary is required; the rest are best-effort.
        const [summaryResult, importsResult, anomaliesResult] = await Promise.allSettled([
          getJson('/admin/summary'),
          getJson('/admin/import-history'),
          getJson('/anomalies'),
        ])

        if (cancelled) return

        if (summaryResult.status === 'rejected') {
          throw new Error(`Failed to fetch summary: ${summaryResult.reason?.message ?? 'unknown error'}`)
        }
        const summary = summaryResult.value ?? {}

        // Import history
        let imports = []
        if (importsResult.status === 'fulfilled') {
          imports = toArray(importsResult.value, 'importHistory', 'imports', 'history')
        } else {
          newWarnings.push('Import history is unavailable.')
          console.warn('Import history failed:', importsResult.reason)
        }

        // Anomalies: general endpoint first, then a constituency fallback
        let anomalies = []
        if (anomaliesResult.status === 'fulfilled') {
          anomalies = toArray(anomaliesResult.value, 'anomalies')
        }

        if (anomalies.length === 0) {
          try {
            const constituencies = toArray(await getJson('/constituency/'), 'constituencies')

            const results = await Promise.all(
              constituencies.slice(0, 5).map((c) => {
                const slug = c?.slug ?? c?.constituency_slug
                if (!slug) return Promise.resolve([])
                return getJson(`/ai/mp/${slug}/anomalies`)
                  .then((data) => toArray(data, 'anomalies'))
                  .catch(() => [])
              })
            )
            anomalies = results.flat()
          } catch (err) {
            console.warn('Could not fetch anomalies from constituencies:', err)
            newWarnings.push('Anomaly data is unavailable.')
          }
        }

        if (cancelled) return

        setAdminSummary(summary)
        setImportHistory(imports)
        setAnomaliesData(anomalies)
        setWeeklyImports(buildWeeklyImports(imports))
        setWarnings(newWarnings)
      } catch (err) {
        if (cancelled) return
        console.error('Error fetching dashboard data:', err)
        setError(`Failed to load dashboard data: ${err.message}`)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
        <p className="text-ink-muted mb-6">Loading admin dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
        <p className="text-ink-danger mb-6">{error}</p>
        <button onClick={retry} className="btn btn-outline">
          Try again
        </button>
      </div>
    )
  }

  if (!adminSummary) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
        <p className="text-ink-muted mb-6">No dashboard data available.</p>
      </div>
    )
  }

  // Derived values from the real API fields
  const totalLeaders = (adminSummary.total_mps ?? 0) + (adminSummary.total_governors ?? 0)
  const totalRecords = (adminSummary.total_allocations ?? 0) + (adminSummary.total_audit_findings ?? 0)

  const highSeverityCount = anomaliesData.filter(
    (a) => String(a?.severity ?? '').toLowerCase() === 'high'
  ).length

  const recentFindings = toArray(adminSummary.recent_findings)
  const flaggedRecent = recentFindings.filter((f) => f?.finding_type === 'misappropriation').length

  // Prefer backend values if they are ever added; otherwise derive or show a neutral default.
  const validationStatus =
    adminSummary.validation_status ??
    adminSummary.validationStatus ??
    (flaggedRecent > 0 ? 'Attention needed' : 'No issues flagged')
  const modelStatus = adminSummary.model_status ?? adminSummary.modelStatus ?? 'Not connected'
  const lastTrained = adminSummary.last_trained ?? adminSummary.lastTrained

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
      <p className="text-ink-muted mb-6">System overview and recent activity.</p>

      {warnings.length > 0 && (
        <div className="mb-6 rounded border border-line bg-gold-50 px-4 py-3 text-sm text-ink">
          {warnings.join(' ')}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total leaders" value={totalLeaders} />
        <KpiCard label="Constituencies tracked" value={adminSummary.total_constituencies ?? 0} />
        <KpiCard label="Records in database" value={fmt(totalRecords)} />
        <KpiCard label="Detected anomalies" value={highSeverityCount} changeTone="down" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0">
            <CheckCircle2 size={18} />
          </div>
          <div>
            <p className="text-sm text-ink-muted">Data validation status</p>
            <p className="font-semibold text-ink">{validationStatus}</p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0">
            <BrainCircuit size={18} />
          </div>
          <div>
            <p className="text-sm text-ink-muted">AI model status</p>
            <p className="font-semibold text-ink">
              {modelStatus}
              {lastTrained && <> &middot; last trained {lastTrained}</>}
            </p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-gold-50 text-gold-500 flex items-center justify-center shrink-0">
            <AlertTriangle size={18} />
          </div>
          <div>
            <p className="text-sm text-ink-muted">High-severity anomalies</p>
            <p className="font-semibold text-ink">{highSeverityCount} need review</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-serif font-semibold text-lg mb-4">Recent imports</h3>
          {importHistory.length === 0 ? (
            <p className="text-sm text-ink-muted">No imports recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted border-b border-line">
                  <th className="py-2 font-medium">File</th>
                  <th className="py-2 font-medium">Category</th>
                  <th className="py-2 font-medium">Records</th>
                  <th className="py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {importHistory.map((imp, i) => {
                  const status = String(imp?.status ?? 'Unknown')
                  return (
                    <tr key={imp?.id ?? imp?._id ?? i} className="border-b border-line last:border-0">
                      <td className="py-2.5 pr-2 text-ink">{imp?.filename ?? '—'}</td>
                      <td className="py-2.5 pr-2 text-ink-muted">{imp?.category ?? '—'}</td>
                      <td className="py-2.5 pr-2 text-ink-muted">{fmt(imp?.records)}</td>
                      <td className="py-2.5">
                        <Badge tone={status.startsWith('Completed') ? 'good' : 'risk'}>{status}</Badge>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Imports this week</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyImports}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 11, fill: '#5B6560' }}
                  axisLine={{ stroke: '#E2E5E1' }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: '#5B6560' }}
                  axisLine={false}
                  tickLine={false}
                />
                <RTooltip contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Bar dataKey="imports" fill="#14532D" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}
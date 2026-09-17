import { useMemo, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LayoutGrid, List } from 'lucide-react'
import { Card, Badge, SeverityBadge, EmptyState } from '../components/ui'
import { Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import APIService from '../services/api'

export default function Anomalies() {
  const [severity, setSeverity] = useState('')
  const [fy, setFy] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [view, setView] = useState('table')

  // State for data fetching
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Try to fetch anomalies from a general endpoint first
        let anomaliesResponse = []
        let fallbackUsed = false

        try {
          const res = await fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/anomalies`)
          if (res.ok) {
            const data = await res.json()
            // Handle different possible response formats
            if (Array.isArray(data)) {
              anomaliesResponse = data
            } else if data.anomalies) {
              anomaliesResponse = data.anomalies
            } else if data.data) {
              anomaliesResponse = Array.isArray(data.data) ? data.data : []
            }
          } else {
            throw new Error(`HTTP ${res.status}`)
          }
        } catch (err) {
          console.warn('Could not fetch anomalies from general endpoint, trying fallback:', err)
          fallbackUsed = true
        }

        // Fallback: if no general endpoint, fetch all constituencies and get their anomalies
        // Note: This is inefficient for large datasets but works for demo/small data
        if (fallbackUsed || anomaliesResponse.length === 0) {
          try {
            const constituenciesRes = await APIService.getAllConstituencies()
            const constituencies = constituenciesRes.constituencies || constituenciesRes || []

            // Get anomalies for each constituency (limit to prevent too many requests)
            const anomaliesPromises = constituencies
              .slice(0, 10) // Limit to first 10 constituencies to avoid too many requests
              .map(constituency =>
                fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/ai/mp/${constituency.slug}/anomalies`)
                  .then(res => res.ok ? res.json() : { success: false, data: [] })
                  .catch(() => ({ success: false, data: [] }))
              )

            const anomaliesResults = await Promise.all(anomaliesPromises)

            // Flatten and format the anomalies
            anomaliesResponse = anomaliesResults
              .filter(result => result.success)
              .flatMap(result =>
                Array.isArray(result.data) ? result.data :
                result.data.anomalies ? result.data.anomalies : []
              )
          } catch (fallbackErr) {
            console.error('Error in fallback anomalies fetch:', fallbackErr)
            anomaliesResponse = []
          }
        }

        setAnomalies(anomaliesResponse)
        setError(null)
      } catch (err) {
        console.error('Error fetching anomalies data:', err)
        setError(err.message || 'Failed to load anomalies data')
        setAnomalies([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Handle loading and error states
  if (loading) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies' }]} />
        <h1 className="text-3xl font-semibold mb-1">AI-detected anomalies</h1>
        <p className="text-ink-muted mb-6">Loading anomalies...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies' }]} />
        <h1 className="text-3xl font-semibold mb-1">AI-detected anomalies</h1>
        <p className="text-ink-danger mb-6">{error}</p>
        <div className="mt-4">
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  const filtered = useMemo(() => anomalies.filter((a) =>
    (!severity || a.severity === severity) &&
    (!fy || a.financialYear === fy) &&
    (!category || a.category === category) &&
    (!status || a.status === status)
  ), [anomalies, severity, fy, category, status])

  const counts = {
    High: filtered.filter((a) => a.severity === 'High').length,
    Medium: filtered.filter((a) => a.severity === 'Medium').length,
    Low: filtered.filter((a) => a.severity === 'Low').length
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Anomalies' }]} />
      <h1 className="text-3xl font-semibold mb-1">AI-detected anomalies</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">
        Unusual spending patterns flagged for further investigation, ranked by severity.
      </p>

      <div className="grid grid-cols-3 gap-4 mb-6 max-w-md">
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-clay-500">{counts.High}</p><p className="text-xs text-ink-muted">High</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-gold-500">{counts.Medium}</p><p className="text-xs text-ink-muted">Medium</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-forest-600">{counts.Low}</p><p className="text-xs text-ink-muted">Low</p></Card>
      </div>

      <FilterBar>
        <Select label="Severity" value={severity} onChange={setSeverity} options={['High', 'Medium', 'Low']} />
        <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(filtered.map((a) => a.financialYear))]} />
        <Select label="Category" value={category} onChange={setCategory} options={[...new Set(filtered.map((a) => a.category))]} />
        <Select label="Status" value={status} onChange={setStatus} options={[...new Set(filtered.map((a) => a.status))]} />
        <div className="ml-auto flex gap-1">
          <button onClick={() => setView('table')} className={`p-2 rounded ${view === 'table' ? 'bg-forest-50 text-forest-700' : 'text-ink-faint'}`}><List size={16} /></button>
          <button onClick={() => setView('cards')} className={`p-2 rounded ${view === 'cards' ? 'bg-forest-50 text-forest-700' : 'text-ink-faint'}`}><LayoutGrid size={16} /></button>
        </div>
      </FilterBar>

      <div className="mt-6">
        {filtered.length === 0 ? (
          <EmptyState title="No anomalies match your filters" description="Try widening your filter selection." />
        ) : view === 'table' ? (
          <Card className="p-2">
            <Table
              columns={['Anomaly', 'Entity', 'Category', 'FY', 'Severity', 'Status']}
              rows={filtered}
              renderRow={(a) => (
                <>
                  <td className="py-3 pr-4 pl-2"><Link to={`/anomalies/${a.id}`} className="font-medium text-ink hover:text-forest-700">{a.title}</Link></td>
                  <td className="py-3 pr-4 text-ink-muted">{a.entity}</td>
                  <td className="py-3 pr-4 text-ink-muted">{a.category}</td>
                  <td className="py-3 pr-4 text-ink-muted">{a.financialYear}</td>
                  <td className="py-3 pr-4"><SeverityBadge severity={a.severity} /></td>
                  <td className="py-3 pr-4 text-ink-muted">{a.status}</td>
                </>
              )}
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((a) => (
              <Link key={a.id} to={`/anomalies/${a.id}`}>
                <Card className="p-4 h-full hover:border-forest-300 transition-colors">
                  <div className="flex justify-between mb-2"><SeverityBadge severity={a.severity} /><Badge>{a.status}</Badge></div>
                  <p className="font-serif font-semibold text-ink mb-1">{a.title}</p>
                  <p className="text-xs text-ink-faint mb-2">{a.entity} &middot; {a.category} &middot; FY {a.financialYear}</p>
                  <p className="text-sm text-ink-muted line-clamp-2">{a.summary}</p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { CheckCircle2, BrainCircuit, AlertTriangle } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { KpiCard } from '../../components/Insights'
import APIService from '../../services/api'

export default function AdminDashboard() {
  // State for dashboard data
  const [adminSummary, setAdminSummary] = useState(null)
  const [importHistory, setImportHistory] = useState([])
  const [anomaliesData, setAnomaliesData] = useState([])
  const [weeklyImports, setWeeklyImports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        // Get auth token from localStorage
        const token = localStorage.getItem('authToken')
        const headers = {
          'Content-Type': 'application/json'
        }

        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }

        // Fetch all required data for the dashboard
        const [
          summaryRes,
          importsRes,
          anomaliesRes
        ] = await Promise.all([
          fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/admin/summary`, { headers }),
          fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/admin/import-history`, { headers }),
          fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/anomalies`, { headers }) // General anomalies endpoint
        ])

        // Check if all responses are ok
        if (!summaryRes.ok) throw new Error(`Failed to fetch summary: ${summaryRes.status}`)
        if (!importsRes.ok) throw new Error(`Failed to fetch import history: ${importsRes.status}`)
        if (!anomaliesRes.ok) {
          // Anomalies endpoint might not exist, we'll try to get them from individual constituencies
          console.warn('General anomalies endpoint not available, will try constituency-specific ones')
          setAnomaliesData([]) // Will try to populate below
        } else {
          const anomaliesJson = await anomaliesRes.json()
          setAnomaliesData(Array.isArray(anomaliesJson) ? anomaliesJson : anomaliesData.anomalies || [])
        }

        // Process successful responses
        const summaryJson = await summaryRes.json()
        const importsJson = await importsRes.json()

        setAdminSummary(summaryJson)
        setImportHistory(Array.isArray(importsJson) ? importsJson : importsJson.importHistory || [])

        // If we didn't get anomalies from the general endpoint, try to get them from constituencies
        if (anomaliesData.length === 0) {
          try {
            // Get a sample of constituencies to check for anomalies
            const constituenciesRes = await fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/constituency/`, { headers })
            if (constituenciesRes.ok) {
              const constituenciesJson = await constituenciesRes.json()
              const constituencies = Array.isArray(constituenciesJson) ? constituenciesJson : constituenciesJson.constituencies || []

              // Get anomalies for first few constituencies (to avoid too many requests)
              const anomaliesPromises = constituencies
                .slice(0, 5) // Limit to 5 constituencies
                .map(c =>
                  fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/ai/mp/${c.slug}/anomalies`)
                    .then(res => res.ok ? res.json() : { success: false, data: [] })
                    .catch(() => ({ success: false, data: [] }))
                )

            const anomaliesResults = await Promise.all(anomaliesPromises)
            const fetchedAnomalies = anomaliesResults
              .filter(result => result.success)
              .flatMap(result =>
                Array.isArray(result.data) ? result.data :
                result.data.anomalies ? result.data.anomalies : []
              )

            setAnomaliesData(fetchedAnomalies)
          }
          } catch (err) {
            console.warn('Could not fetch anomalies from constituencies:', err)
            // Keep empty anomalies array
          }
        }

        // Process weekly imports data (if available from import history)
        // For now, we'll use a placeholder or calculate from import history
        // In a real implementation, this would come from a specific endpoint
        const processedWeeklyImports = [
          { day: 'Mon', imports: 1 }, { day: 'Tue', imports: 0 }, { day: 'Wed', imports: 2 },
          { day: 'Thu', imports: 0 }, { day: 'Fri', imports: 1 }, { day: 'Sat', imports: 0 }, { day: 'Sun', imports: 0 }
        ]
        setWeeklyImports(processedWeeklyImports)

        setError(null)
      } catch (err) {
        console.error('Error fetching dashboard data:', err)
        setError(`Failed to load dashboard data: ${err.message}`)
        // Set some fallback data so the dashboard doesn't break completely
        setAdminSummary({
          totalLeaders: 7,
          totalDatasets: 6,
          totalRecords: 4213,
          recentImports: 3,
          validationStatus: 'Attention needed',
          detectedAnomalies: 12,
          modelStatus: 'Trained',
          lastTrained: '2025-08-30'
        })
        setImportHistory([
          { id: 'IMP-201', filename: 'Nyeri_Governor_Fiscal_2022_2027.xlsx', category: 'County Finance', status: 'Completed', records: 96, date: '2025-08-30' },
          { id: 'IMP-200', filename: 'Nyeri_NGCDF_2022_2027.xlsx', category: 'NG-CDF Allocations', status: 'Completed', records: 24, date: '2025-08-30' },
          { id: 'IMP-199', filename: 'dept_spending_q2.xlsx', category: 'Departmental Data', status: 'Failed - format error', records: 0, date: '2025-08-14' }
        ])
        setAnomaliesData([]) // Empty anomalies on error
        setWeeklyImports([
          { day: 'Mon', imports: 1 }, { day: 'Tue', imports: 0 }, { day: 'Wed', imports: 2 },
          { day: 'Thu', imports: 0 }, { day: 'Fri', imports: 1 }, { day: 'Sat', imports: 0 }, { day: 'Sun', imports: 0 }
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  // Handle loading and error states
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
        <div className="mt-4">
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  // If we still don't have summary data, show a basic message
  if (!adminSummary) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
        <p className="text-ink-muted mb-6">No dashboard data available.</p>
      </div>
    )
  }

  // Calculate high-severity anomalies count
  const highSeverityCount = anomaliesData.filter((a) => a.severity === 'High').length

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
      <p className="text-ink-muted mb-6">System overview and recent activity.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total leaders" value={adminSummary.totalLeaders} />
        <KpiCard label="Datasets tracked" value={adminSummary.totalDatasets} />
        <KpiCard label="Records in database" value={adminSummary.totalRecords.toLocaleString()} />
        <KpiCard label="Detected anomalies" value={highSeverityCount} changeTone="down" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0"><CheckCircle2 size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">Data validation status</p>
            <p className="font-semibold text-ink">{adminSummary.validationStatus}</p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0"><BrainCircuit size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">AI model status</p>
            <p className="font-semibold text-ink">{adminSummary.modelStatus} &middot; last trained {adminSummary.lastTrained}</p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-gold-50 text-gold-500 flex items-center justify-center shrink-0"><AlertTriangle size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">High-severity anomalies</p>
            <p className="font-semibold text-ink">{highSeverityCount} need review</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-serif font-semibold text-lg mb-4">Recent imports</h3>
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
              {importHistory.map((imp) => (
                <tr key={imp.id} className="border-b border-line last:border-0">
                  <td className="py-2.5 pr-2 text-ink">{imp.filename}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{imp.category}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{imp.records}</td>
                  <td className="py-2.5">
                    <Badge tone={imp.status.startsWith('Completed') ? 'good' : 'risk'}>{imp.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Imports this week</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyImports}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={false} tickLine={false} />
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
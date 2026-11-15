import { useState, useEffect, useCallback } from 'react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge, Button, Toast } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import { FileDown } from 'lucide-react'
import APIService from '../services/api'


const SEV_COLORS = { High: '#A6431F', Medium: '#C08A28', Low: '#2E6B44' }
const CHART_COLORS = ['#14532D', '#A6431F', '#C08A28', '#2E6B44', '#5B6560', '#6E9E7C']

export default function AccountabilityDashboard() {
  const [constituencies, setConstituencies] = useState([])
  const [governorData, setGovernorData] = useState(null)
  const [countyFinances, setCountyFinances] = useState([])
  const [departments, setDepartments] = useState([])
  const [countyAuditFindings, setCountyAuditFindings] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Fetch all required data in parallel
        const [
          constituenciesData,
          governorResponse,
          financesResponse,
          departmentsResponse,
          auditResponse,
          anomaliesResponse
        ] = await Promise.all([
          APIService.getAllConstituencyScores(),
          APIService.getGovernorProfile(),
          APIService.getCountyFinances(),
          APIService.getDepartmentData(),
          APIService.getCountyAuditFindings(),
          fetch(`${APIService.baseURL}/ai/county/narrative`).then(r => r.json()).catch(() => ({ success: false }))
        ])

        setConstituencies(constituenciesData)
        setGovernorData(governorResponse)
        setCountyFinances(financesResponse)
        setDepartments(departmentsResponse)
        setCountyAuditFindings(auditResponse.audit_findings || auditResponse || [])

        // Parse anomalies from AI response
        if (anomaliesResponse && anomaliesResponse.success && anomaliesResponse.data) {
          const narrative = anomaliesResponse.data.narrative_fields || {}
          if (narrative.findings && Array.isArray(narrative.findings)) {
            setAnomalies(narrative.findings)
          }
        }

        setError(null)
      } catch (err) {
        setError(err.message || 'Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const avgScore = constituencies.length > 0
    ? Math.round(constituencies.reduce((a, c) => a + (c.accountabilityScore || 0), 0) / constituencies.length)
    : 0

  const totalFlagged = countyAuditFindings.reduce((a, f) => {
    const amount = f.amount_flagged_kshm || f.amount_at_risk || 0
    return a + (typeof amount === 'number' ? amount : 0)
  }, 0)

  const severityCounts = ['High', 'Medium', 'Low'].map((s) => ({
    name: s, value: anomalies.filter((a) => a.severity === s).length,
  }))

  const departmentsBelowTarget = departments.filter((d) => d.status !== 'On Track').length

  // Build allocation trend data from county finances
  const allocationTrendData = countyFinances.map(f => ({
    fy: f.financial_year,
    'Equitable Share': f.equitable_share_kshb || 0,
    'Conditional Grants': f.conditional_grants_kshb || 0,
    'Own Source Revenue': f.osr_kshb || 0,
    'Expenditure': f.expenditure_kshb || 0
  }))

  // Download governor PDF report
  const handleDownloadGovernorReport = useCallback(async () => {
    if (!governorData) return

    try {
      setToast({ type: 'info', message: 'Generating governor report...' })
      const blob = await APIService.downloadGovernorPDFReport(governorData.governor || governorData.name)

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const leaderName = (governorData.name || 'governor').replace(/\s+/g, '_')
      a.download = `${leaderName}_accountability_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setToast({ type: 'success', message: 'Governor report downloaded successfully!' })
    } catch (err) {
      console.error('Error downloading governor report:', err)
      setToast({ type: 'error', message: err.message || 'Failed to generate governor report' })
    }
  }, [governorData])

  if (loading) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Accountability' }]} />
        <h1 className="text-3xl font-semibold mb-1">Accountability dashboard</h1>
        <p className="text-ink-muted mb-6 max-w-2xl">Loading dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Accountability' }]} />
        <h1 className="text-3xl font-semibold mb-1">Accountability dashboard</h1>
        <p className="text-ink-danger mb-6">{error}</p>
      </div>
    )
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Accountability' }]} />

      {/* Header with Governor Report Download */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-semibold mb-1">Accountability dashboard</h1>
          <p className="text-ink-muted mb-6 max-w-2xl">A county-wide view of financial performance, audit findings and AI-detected anomalies.</p>
        </div>
        {governorData && (
          <Button onClick={handleDownloadGovernorReport} className="md:ml-auto">
            <FileDown size={16} /> Download Governor Accountability Report
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Avg. constituency score" value={avgScore} sub="out of 100" />
        <KpiCard label="Total flagged amount" value={`KSh ${totalFlagged.toFixed(1)}M`} changeTone="down" />
        <KpiCard label="Active anomalies" value={String(anomalies.filter((a) => a.status !== 'Reviewed - no issue').length)} />
        <KpiCard label="Departments below target" value={String(departmentsBelowTarget)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-serif font-semibold text-lg mb-4">County financial trend</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={allocationTrendData}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="Equitable Share" stroke={CHART_COLORS[0]} strokeWidth={2} dot={{ r: 2.5 }} />
                <Line type="monotone" dataKey="Conditional Grants" stroke={CHART_COLORS[1]} strokeWidth={2} dot={{ r: 2.5 }} />
                <Line type="monotone" dataKey="Own Source Revenue" stroke={CHART_COLORS[2]} strokeWidth={2} dot={{ r: 2.5 }} />
                <Line type="monotone" dataKey="Expenditure" stroke={CHART_COLORS[3]} strokeWidth={2} dot={{ r: 2.5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Anomalies by severity</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={severityCounts} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                  {severityCounts.map((s) => <Cell key={s.name} fill={SEV_COLORS[s.name]} />)}
                </Pie>
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 text-xs mt-2">
            {severityCounts.map((s) => (
              <span key={s.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: SEV_COLORS[s.name] }} /> {s.name} ({s.value})
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-6 mb-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Constituency comparison</h3>
        <Table
          columns={['Constituency', 'MP', 'Score', 'Allocation FY24/25', 'Audit Opinion', 'Findings']}
          rows={constituencies}
          keyField="_id"
          renderRow={(c) => (
            <>
              <td className="py-3 pr-4 font-medium text-ink">{c.name}</td>
              <td className="py-3 pr-4 text-ink-muted">{c.mp}</td>
              <td className="py-3 pr-4"><Badge tone={c.accountabilityScore >= 70 ? 'good' : c.accountabilityScore >= 55 ? 'watch' : 'risk'}>{c.accountabilityScore}</Badge></td>
              <td className="py-3 pr-4 text-ink-muted">KSh {c.totalAllocationKshm.toFixed(1)}M</td>
              <td className="py-3 pr-4 text-ink-muted">{c.auditStatus}</td>
              <td className="py-3 pr-4 text-ink-muted">{c.misappropriationCount} flagged</td>
            </>
          )}
        />
      </Card>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={departments}>
              <CartesianGrid stroke="#E2E5E1" vertical={false} />
              <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} interval={0} angle={-15} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} unit="%" />
              <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
              <Bar dataKey="absorption_rate" name="Absorption %" fill="#14532D" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
          duration={5000}
        />
      )}
    </div>
  )
}

import { useState, useCallback } from 'react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge, Button, Toast } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import { FileDown } from 'lucide-react'
import APIService from '../services/api'
import { useSharedAsyncData } from '../hooks/useAsyncData.jsx'


const SEV_COLORS = { High: '#A6431F', Medium: '#C08A28', Low: '#2E6B44' }
const CHART_COLORS = ['#14532D', '#A6431F', '#C08A28', '#2E6B44', '#5B6560', '#6E9E7C']

// Fetch data independently with persistent caching
const { data: constituencies, isLoading: constLoading, error: constError } = useSharedAsyncData(
  'accountability-constituencies',
  () => APIService.getAllConstituencyScores(),
  { cacheTime: 10 * 60 * 1000 }
)

const { data: governorData, isLoading: govLoading, error: govError } = useSharedAsyncData(
  'accountability-governor',
  () => APIService.getGovernorProfile(),
  { cacheTime: 10 * 60 * 1000 }
)

const { data: countyFinances, isLoading: financeLoading } = useSharedAsyncData(
  'accountability-finances',
  () => APIService.getCountyFinances(),
  { cacheTime: 10 * 60 * 1000 }
)

const { data: departmentsResponse, isLoading: deptLoading } = useSharedAsyncData(
  'accountability-departments',
  () => APIService.getDepartmentData(),
  { cacheTime: 10 * 60 * 1000 }
)
const departments = departmentsResponse?.departments || departmentsResponse || []

const { data: auditResponse, isLoading: auditLoading } = useSharedAsyncData(
  'accountability-audit',
  () => APIService.getCountyAuditFindings(),
  { cacheTime: 5 * 60 * 1000 }
)
const countyAuditFindings = auditResponse?.audit_findings || auditResponse || []

const { data: findingsClassifierResponse, isLoading: anomaliesLoading } = useSharedAsyncData(
  'accountability-anomalies',
  () => APIService.getCountyFindingsClassifier().catch(() => ({ success: false })),
  { cacheTime: 5 * 60 * 1000 }
)
const anomalies = (findingsClassifierResponse?.success && findingsClassifierResponse.data?.narrative_fields?.findings) || []

const loading = constLoading || govLoading || financeLoading || deptLoading || auditLoading || anomaliesLoading
const error = constError || govError

export default function AccountabilityDashboard() {
  const [toast, setToast] = useState(null)

  const avgScore = constituencies?.length > 0
    ? Math.round(constituencies.reduce((a, c) => a + (c.accountabilityScore || 0), 0) / constituencies.length)
    : 0

  const totalFlagged = countyAuditFindings?.reduce((a, f) => {
    const amount = f.amount_flagged_kshm || f.amount_at_risk || 0
    const numAmount = typeof amount === 'number' ? amount : (typeof amount === 'string' ? parseFloat(amount) : 0)
    return a + (isNaN(numAmount) ? 0 : numAmount)
  }, 0) || 0

  const severityCounts = ['High', 'Medium', 'Low'].map((s) => ({
    name: s, value: anomalies?.filter((a) => a.severity === s).length || 0,
  }))

  const departmentsBelowTarget = departments?.filter((d) => d.status !== 'On Track').length || 0

  // Build allocation trend data from county finances (now pivoted by the API)
  const allocationTrendData = countyFinances?.map(f => ({
    fy: f.financial_year || 'N/A',
    'Equitable Share': f.equitable_share_kshb || 0,
    'Conditional Grants': f.conditional_grants_kshb || 0,
    'Own Source Revenue': f.osr_kshb || 0,
    'Expenditure': f.expenditure_kshb || 0
  })) || []

  // Normalize department data for chart - handle both absorption_rate and absorptionRate
  const normalizedDepartments = departments?.map(d => ({
    ...d,
    absorption_rate: d.absorption_rate ?? d.absorptionRate ?? 0,
    department: d.department || d.name || 'Unknown'
  })) || []

  // Download county-wide aggregated PDF report (Governor + all Constituencies)
  const handleDownloadCountyReport = useCallback(async () => {
    try {
      setToast({ type: 'info', message: 'Generating Nyeri County accountability report...' })
      const blob = await APIService.downloadCountyPDFReport()

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'Nyeri_County_Accountability_Report.pdf'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setToast({ type: 'success', message: 'County report downloaded successfully!' })
    } catch (err) {
      console.error('Error downloading county report:', err)
      setToast({ type: 'error', message: err.message || 'Failed to generate county report' })
    }
  }, [])

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

      {/* Header with County Report Download */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-semibold mb-1">Accountability dashboard</h1>
          <p className="text-ink-muted mb-6 max-w-2xl">A county-wide view of financial performance, audit findings and AI-detected anomalies.</p>
        </div>
        <Button onClick={handleDownloadCountyReport} className="md:ml-auto">
          <FileDown size={16} /> Download Nyeri County Accountability Report
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Avg. constituency score" value={avgScore} sub="out of 100" />
        <KpiCard label="Total flagged amount" value={`KSh ${(isNaN(totalFlagged) ? 0 : totalFlagged).toFixed(1)}M`} changeTone="down" />
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
          renderRow={(c) => {
            const allocation = (c.totalAllocationKshm ?? c.totalAllocation ?? 0)
            const misCount = c.misappropriationCount ?? c.misappropriation_count ?? 0
            const auditStatus = c.auditStatus ?? c.audit_status ?? 'N/A'
            const score = c.accountabilityScore ?? 0
            const scoreTone = score >= 70 ? 'good' : score >= 55 ? 'watch' : 'risk'
            return (
              <>
                <td className="py-3 pr-4 font-medium text-ink">{c.name || 'Unknown'}</td>
                <td className="py-3 pr-4 text-ink-muted">{c.mp?.name || c.mp || 'N/A'}</td>
                <td className="py-3 pr-4"><Badge tone={scoreTone}>{score}</Badge></td>
                <td className="py-3 pr-4 text-ink-muted">KSh {allocation.toFixed(1)}M</td>
                <td className="py-3 pr-4 text-ink-muted">{auditStatus}</td>
                <td className="py-3 pr-4 text-ink-muted">{misCount} flagged</td>
              </>
            )
          }}
        />
      </Card>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={normalizedDepartments} layout="vertical">
              <CartesianGrid stroke="#E2E5E1" horizontal={false} />
              <YAxis type="category" dataKey="department" tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} width={160} />
              <XAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} unit="%" />
              <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
              <Bar dataKey="absorption_rate" name="Absorption %" fill="#14532D" radius={[0, 3, 3, 0]} />
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

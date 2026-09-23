import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import APIService from '../services/api'

export default function CountyDashboard() {
  // State for data fetching
  const [governor, setGovernor] = useState(null)
  const [countyFinances, setCountyFinances] = useState(null)
  const [departments, setDepartments] = useState([])
  const [auditFindings, setAuditFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Fetch all required data in parallel
        const [
          governorResponse,
          financesResponse,
          departmentsResponse,
          auditResponse
        ] = await Promise.all([
          APIService.getGovernorProfile(),
          APIService.getCountyFinances(),
          APIService.getDepartmentData(),
          APIService.getCountyAuditFindings()
        ])

        if (governorResponse) {
          setGovernor(governorResponse)
        }

        if (financesResponse) {
          // The finances endpoint returns an array, but we need to transform it to match the mock data structure
          // Mock data: { revenueSources: [...], budgetVsExpenditure: [...], developmentVsRecurrent: [...] }
          // We need to see what the actual API returns and transform accordingly
          setCountyFinances(financesResponse)
        }

        if (departmentsResponse) {
          setDepartments(departmentsResponse.departments || departmentsResponse || [])
        }

        if (auditResponse) {
          setAuditFindings(auditResponse.audit_findings || auditResponse || [])
        }

        setError(null)
      } catch (err) {
        console.error('Error fetching county dashboard data:', err)
        setError(err.message || 'Failed to load county dashboard data')
        setGovernor(null)
        setCountyFinances(null)
        setDepartments([])
        setAuditFindings([])
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
        <Breadcrumbs items={[{ label: 'County' }]} />
        <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
        <p className="text-ink-muted mb-6">Loading county overview...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'County' }]} />
        <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
        <p className="text-ink-danger mb-6">{error}</p>
        <div className="mt-4">
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  // If we don't have essential data, show empty state
  if (!governor) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'County' }]} />
        <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
        <p className="text-ink-muted mb-6">No governor data available.</p>
      </div>
    )
  }

  // Transform county finances data to match expected format if needed
  // const countyFindings = auditFindings.filter((f) => f.entityType === 'department')
  //const isSourcesRow = (f) => f.category?.trim().startsWith('Sources')
  //const countyFindings = auditFindings.filter((f) => !isSourcesRow(f))
  // Default transformations if API doesn't return expected format
  const revenueSources = countyFinances?.revenueSources || [
    { source: 'Equitable Share', amountKshb: 5.8 },
    { source: 'Conditional Grants', amountKshb: 1.2 },
    { source: 'Own-Source Revenue', amountKshb: 0.74 },
  ]

  const budgetVsExpenditure = countyFinances?.budgetVsExpenditure || [
    { fy: '2022/23', budget: 7.1, expenditure: 6.4 },
    { fy: '2023/24', budget: 7.4, expenditure: 6.9 },
    { fy: '2024/25', budget: 7.8, expenditure: 7.2 },
    { fy: '2025/26', budget: 8.0, expenditure: 3.6 },
  ]

  const developmentVsRecurrent = countyFinances?.developmentVsRecurrent || [
    { fy: '2023/24', development: 2.6, recurrent: 4.3 },
    { fy: '2024/25', development: 2.9, recurrent: 4.3 },
    { fy: '2025/26', development: 1.4, recurrent: 2.2 },
  ]
  // Transform county finances data to match expected format if needed
const isSourcesRow = (f) => f.category?.trim().startsWith('Sources')
const countyFindings = auditFindings.filter((f) => !isSourcesRow(f))

// countyFinances is a flat array of { revenue_source, amount_kshb, financial_year, ... }
const latestFy = countyFinances?.length
  ? [...new Set(countyFinances.map((f) => f.financial_year))].sort().slice(-1)[0]
  : null

const latestRevenue = countyFinances
  ? countyFinances.filter((f) => f.financial_year === latestFy)
  : []

const totalRevenue = latestRevenue.reduce((sum, r) => sum + (r.amount_kshb || 0), 0)
const equitableShare = latestRevenue.find((r) => r.revenue_source === 'Equitable Share')?.amount_kshb || 0
const ownSourceRevenue = latestRevenue.find((r) => r.revenue_source?.startsWith('Own Source Revenue'))?.amount_kshb || 0

// Revenue-by-source trend across all fiscal years (real data, replaces budgetVsExpenditure)
const revenueByYear = countyFinances
  ? Object.values(
      countyFinances.reduce((acc, r) => {
        if (!acc[r.financial_year]) acc[r.financial_year] = { fy: r.financial_year }
        acc[r.financial_year][r.revenue_source] = r.amount_kshb
        return acc
      }, {})
    ).sort((a, b) => a.fy.localeCompare(b.fy))
  : []

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'County' }]} />
      <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
      <p className="text-ink-muted mb-6">Financial performance and accountability indicators for the county government.</p>

      <Card className="p-5 mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif font-semibold">MK</div>
          <div>
            <p className="font-serif font-semibold text-ink">{governor.name}</p>
            <p className="text-sm text-ink-muted">Governor &middot; {governor.party} &middot; {governor.tenure}</p>
          </div>
        </div>
        <Link to={`/leaders/${governor._id || governor.id}`} className="text-sm text-forest-700 hover:underline">View full profile &rarr;</Link>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label={`FY${latestFy || '—'} Budget`} value={`KSh ${totalRevenue.toFixed(2)}B`} />
        <KpiCard label="Equitable Share" value={`KSh ${equitableShare.toFixed(2)}B`} sub={totalRevenue ? `${((equitableShare / totalRevenue) * 100).toFixed(0)}% of revenue` : ''} />
        <KpiCard label="Own-Source Revenue" value={`KSh ${ownSourceRevenue.toFixed(2)}B`} />
        <KpiCard label="Open audit findings" value={String(countyFindings.length)} changeTone="down" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Revenue by source (KSh Billions)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={revenueByYear}>
                  <CartesianGrid stroke="#E2E5E1" vertical={false} />
                  <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                  <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="Equitable Share" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Conditional Grants" stroke="#8A928C" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Development vs. recurrent (KSh Billions)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={developmentVsRecurrent}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="recurrent" name="Recurrent" fill="#C7CFC9" radius={[3, 3, 0, 0]} />
                <Bar dataKey="development" name="Development" fill="#14532D" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <Card className="p-6 mb-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption, FY2024/25</h3>
        <Table
          columns={['Department', 'Approved Budget', 'Q3 Spend', 'Absorption', 'Status']}
          rows={departments}
          keyField="_id"
          renderRow={(d) => (
            <>
              <td className="py-3 pr-4 font-medium text-ink">{d.department}</td>
              <td className="py-3 pr-4 text-ink-muted">KSh {d.approved_budget_kshm}M</td>
              <td className="py-3 pr-4 text-ink-muted">KSh {d.q3_spend_kshm}M</td>
              <td className="py-3 pr-4 text-ink-muted">{d.absorption_rate}%</td>
              <td className="py-3 pr-4">
                <Badge tone={d.status === 'On Track' ? 'good' : d.status === 'Behind' ? 'watch' : 'risk'}>{d.status}</Badge>
              </td>
            </>
          )}
        />
      </Card>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Auditor-General findings, county departments</h3>
        <p className="text-3xl font-serif font-semibold text-ink">{countyFindings.length}</p>
        <p className="text-sm text-ink-muted mt-1">Open audit findings across county departments</p>
      </Card>
    </div>
  )
}
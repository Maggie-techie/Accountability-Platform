import { useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'

export default function ConstituencyProfile() {
  const { slug } = useParams()

  // State for data fetching
  const [constituency, setConstituency] = useState(null)
  const [allocationTrend, setAllocationTrend] = useState([])
  const [auditFindings, setAuditFindings] = useState([])
  const [anomaliesData, setAnomaliesData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!slug) {
        setError('Constituency slug is required')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        // Fetch all required data
        let constituencyResponse = null
        let allocationsResponse = null
        let auditResponse = null
        let anomaliesResponse = { success: false, data: [] }

        try {
          constituencyResponse = await APIService.getConstituencyBySlug(slug)
        } catch (err) {
          console.error('Error fetching constituency:', err)
        }

        try {
          allocationsResponse = await APIService.getConstituencyAllocations(slug)
        } catch (err) {
          console.error('Error fetching allocations:', err)
        }

        try {
          auditResponse = await APIService.getConstituencyAuditFindings(slug)
        } catch (err) {
          console.error('Error fetching audit findings:', err)
        }

        // Fetch anomalies from AI endpoint
        try {
          const res = await fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/ai/mp/${slug}/anomalies`)
          anomaliesResponse = await res.json()
        } catch (err) {
          console.warn('Could not fetch anomalies from AI endpoint:', err)
          // Fallback to empty anomalies
        }

        if (constituencyResponse) {
          setConstituency(constituencyResponse)
        }

        // Process allocations data for chart
        // We need to transform allocations to match the mock allocationTrend format:
        // [{ fy: '2022/23', Kieni: 165.7, Mathira: 151.9, Othaya: 118.0, Tetu: 131.3, 'Mukurwe-ini': 110.2, 'Nyeri Town': 120.8 }, ...]

        if (allocationsResponse && allocationsResponse.allocations) {
          // Group allocations by fiscal year and constituency
          const allocationsByYear = {}

          // First, let's get all constituencies to know what we're dealing with
          // For now, we'll process what we have
          allocationsResponse.allocations.forEach(alloc => {
            const fy = alloc.fy_key || alloc.financial_year || 'Unknown'
            if (!allocationsByYear[fy]) {
              allocationsByYear[fy] = { fy }
            }

            // Assuming the allocation record has amount and references to constituency
            const constituencyIdentifier = alloc.constituency_slug ||
                                         alloc.name ||
                                         (alloc.entity && alloc.entity.name) ||
                                         'unknown'

            const amount = alloc.amount_kshm || alloc.amount || alloc.allocated_amount || 0

            if (constituencyIdentifier && constituencyIdentifier !== 'unknown') {
              allocationsByYear[fy][constituencyIdentifier] = amount
            }
          })

          // Convert to array format expected by chart
          // We need to ensure all constituencies are represented for each year
          // For simplicity, we'll use the data as-is and enhance later if needed
          const trendArray = Object.keys(allocationsByYear)
            .map(fy => ({
              fy,
              ...allocationsByYear[fy]
            }))
            .sort((a, b) => {
              // Sort by fiscal year (assuming format like "2022/23")
              const yearA = parseInt(a.fy.split('/')[0])
              const yearB = parseInt(b.fy.split('/')[0])
              return yearA - yearB
            })

          setAllocationTrend(trendArray)
        } else {
          setAllocationTrend([])
        }

        if (auditResponse && auditResponse.audit_findings) {
          setAuditFindings(auditResponse.audit_findings)
        } else {
          setAuditFindings([])
        }

        if (anomaliesResponse && anomaliesResponse.success) {
          // Handle different possible response formats from AI endpoint
          if (Array.isArray(anomaliesResponse.data)) {
            setAnomaliesData(anomaliesResponse.data)
          } else if (anomaliesResponse.anomalies) {
            setAnomaliesData(anomaliesResponse.anomalies)
          } else {
            setAnomaliesData([])
          }
        } else {
          setAnomaliesData([])
        }

        setError(null)
      } catch (err) {
        console.error('Error fetching constituency profile data:', err)
        setError(err.message || 'Failed to load constituency data')
        setConstituency(null)
        setAllocationTrend([])
        setAuditFindings([])
        setAnomaliesData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [slug])

  // Handle loading and error states
  if (loading) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">
        Loading constituency profile...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center">
        <h2 className="text-2xl font-semibold text-ink-danger mb-4">Error loading constituency</h2>
        <p className="text-ink-muted">{error}</p>
        <Link to="/constituencies" className="text-forest-600 hover:underline">
          ← Back to constituencies
        </Link>
      </div>
    )
  }

  if (!constituency) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">
        Constituency not found.
      </div>
    )
  }

  // Ensure we have at least some allocation trend data for the chart
  const chartData = allocationTrend.length > 0 ? allocationTrend : [
    { fy: '2022/23', allocation: constituency.totalAllocationKshm || 0 },
    { fy: '2023/24', allocation: constituency.totalAllocationKshm || 0 },
    { fy: '2024/25', allocation: constituency.totalAllocationKshm || 0 },
    { fy: '2025/26', allocation: constituency.totalAllocationKshm || 0 }
  ]

  // Filter findings and anomalies for this constituency (though they should already be filtered by backend)
  const findings = auditFindings.filter((f) =>
    f.entity?.toLowerCase().includes(constituency.name?.toLowerCase() || '') ||
    constituency.name?.toLowerCase().includes(f.entity?.toLowerCase() || '') ||
    f.entityType === 'constituency'
  )

  const constAnomalies = anomaliesData.filter((a) =>
    a.entity?.toLowerCase().includes(constituency.name?.toLowerCase() || '') ||
    constituency.name?.toLowerCase().includes(a.entity?.toLowerCase() || '') ||
    a.entityType === 'Constituency' ||
    a.entityType === 'constituency'
  )

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Constituencies', to: '/constituencies' }, { label: constituency.name }]} />

      <Card className="p-6 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-semibold text-ink">{constituency.name} Constituency</h1>
          <p className="text-ink-muted">MP: <Link to={`/leaders/${constituency.slug}`} className="text-forest-700 hover:underline">{constituency.mp?.name}</Link> &middot; {constituency.mp?.party}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-2xl font-serif font-semibold text-forest-700">{constituency.accountabilityScore || 0}</p>
            <p className="text-xs text-ink-muted">Accountability score</p>
          </div>
          <Button variant="secondary"><FileDown size={16} /> Download report</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">NG-CDF allocation by year</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#E2E5E1" vertical={false} />
                  <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                  <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                  {/* We need to determine what the line should represent - for now using a placeholder */}
                  {/* In reality, we'd need to know which constituency this is for the line data */}
                  <Line type="monotone" dataKey="fy" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Audit findings</h3>
            {findings.length === 0 ? (
              <p className="text-sm text-ink-muted">No findings recorded for {constituency.name} in the current dataset.</p>
            ) : (
              <ul className="space-y-3">
                {findings.map((f) => (
                  <li key={f.id} className="flex justify-between gap-3 text-sm border-b border-line pb-3 last:border-0">
                    <div>
                      <p className="font-medium text-ink">{f.category}</p>
                      <p className="text-ink-muted mt-0.5">{f.finding}</p>
                      <p className="text-xs text-ink-faint mt-1">FY {f.financialYear} &middot; KSh {f.amountKshm}M</p>
                    </div>
                    <Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-3">Development / project information</h3>
            <p className="text-sm text-ink-muted">
              NG-CDF-funded projects include bursary disbursement to needy students, classroom construction,
              and water infrastructure. Project-level completion tracking will expand as more source data is digitised.
            </p>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Detected anomalies</h3>
            {constAnomalies.length === 0 ? (
              <p className="text-sm text-ink-muted">No anomalies currently flagged.</p>
            ) : (
              <ul className="space-y-3">
                {constAnomalies.map((a) => (
                  <li key={a.id} className="text-sm border-b border-line pb-3 last:border-0">
                    <div className="flex justify-between gap-2">
                      <Link to={`/anomalies/${a.id}`} className="font-medium text-ink hover:text-forest-700">{a.title}</Link>
                    </div>
                    <Badge tone={a.severity === 'High' ? 'risk' : a.severity === 'Medium' ? 'watch' : 'good'} className="mt-1.5">{a.severity}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}
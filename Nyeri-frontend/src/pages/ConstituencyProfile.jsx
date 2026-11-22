import { useParams, Link } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown } from 'lucide-react'
import { Card, Badge, Button, Toast } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'
import { useSharedAsyncData } from '../hooks/useAsyncData.jsx'

export default function ConstituencyProfile() {
  const { slug } = useParams()
  const [toast, setToast] = useState(null)

  // Fetch data independently with persistent caching (slug-specific keys)
  const { data: constituency, isLoading: constLoading, error: constError } = useSharedAsyncData(
    `constituency-profile-${slug}`,
    () => slug ? APIService.getConstituencyBySlug(slug) : Promise.resolve(null),
    { cacheTime: 10 * 60 * 1000, immediate: !!slug }
  )

  const { data: allocationsResponse, isLoading: allocLoading } = useSharedAsyncData(
    `constituency-allocations-${slug}`,
    () => slug ? APIService.getConstituencyAllocations(slug) : Promise.resolve(null),
    { cacheTime: 10 * 60 * 1000, immediate: !!slug }
  )

  const { data: auditResponse, isLoading: auditLoading } = useSharedAsyncData(
    `constituency-audit-${slug}`,
    () => slug ? APIService.getConstituencyAuditFindings(slug) : Promise.resolve(null),
    { cacheTime: 10 * 60 * 1000, immediate: !!slug }
  )
  const auditFindings = auditResponse?.audit_findings || auditResponse || []

  const { data: scoreResponse, isLoading: scoreLoading } = useSharedAsyncData(
    `constituency-score-${slug}`,
    () => slug ? APIService.getConstituencyScore(slug) : Promise.resolve(null),
    { cacheTime: 10 * 60 * 1000, immediate: !!slug }
  )
  const accountabilityScore = scoreResponse?.score

  // Fetch anomalies from AI endpoint
  const { data: anomaliesResponse, isLoading: anomaliesLoading } = useSharedAsyncData(
    `constituency-anomalies-${slug}`,
    async () => {
      if (!slug) return { success: false, data: [] }
      try {
        const res = await fetch(`${APIService.baseURL}/ai/mp/${slug}/anomalies`)
        if (res.ok) {
          return await res.json()
        } else {
          const errorData = await res.json().catch(() => ({}))
          return { success: false, error: errorData.error || 'Failed to fetch anomalies' }
        }
      } catch (err) {
        return { success: false, error: err.message }
      }
    },
    { cacheTime: 10 * 60 * 1000, immediate: !!slug }
  )
  const anomaliesData = (anomaliesResponse?.success && anomaliesResponse.data) || []

  // Process allocations data for chart
  const [allocationTrend, setAllocationTrend] = useState([])

  // Helper to convert slug to proper constituency name for chart keys
  const slugToChartKey = (slug) => {
    const map = {
      'kieni': 'Kieni',
      'mathira': 'Mathira',
      'othaya': 'Othaya',
      'tetu': 'Tetu',
      'mukurweini': 'Mukurwe-ini',
      'nyeri_town': 'Nyeri Town',
    }
    return map[slug] || slug
  }

  useEffect(() => {
    if (allocationsResponse && allocationsResponse.allocations) {
      // Group allocations by fiscal year and constituency
      const allocationsByYear = {}

      allocationsResponse.allocations.forEach(alloc => {
        const fy = alloc.fy_key || alloc.financial_year || 'Unknown'
        if (!allocationsByYear[fy]) {
          allocationsByYear[fy] = { fy }
        }

        const constituencyIdentifier = alloc.constituency_slug ||
                                     alloc.name ||
                                     (alloc.entity && alloc.entity.name) ||
                                     'unknown'

        const amount = alloc.amount_kshm || alloc.amount || alloc.allocated_amount || 0

        if (constituencyIdentifier && constituencyIdentifier !== 'unknown') {
          const chartKey = slugToChartKey(constituencyIdentifier)
          allocationsByYear[fy][chartKey] = amount
        }
      })

      const trendArray = Object.keys(allocationsByYear)
        .map(fy => ({
          fy,
          ...allocationsByYear[fy]
        }))
        .sort((a, b) => {
          const yearA = parseInt(a.fy.split('/')[0])
          const yearB = parseInt(b.fy.split('/')[0])
          return yearA - yearB
        })

      setAllocationTrend(trendArray)
    } else {
      setAllocationTrend([])
    }
  }, [allocationsResponse])

  const loading = constLoading || allocLoading || auditLoading || scoreLoading || anomaliesLoading
  const error = constError

  // Download PDF report
  const handleDownloadReport = useCallback(async () => {
    if (!slug || !constituency) return

    try {
      setToast({ type: 'info', message: 'Generating report...' })
      const blob = await APIService.downloadConstituencyPDFReport(slug)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const mpName = constituency.mp?.name || constituency.name || 'constituency'
      a.download = `${mpName.replace(/\s+/g, '_')}_accountability_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setToast({ type: 'success', message: 'Report downloaded successfully!' })
    } catch (err) {
      console.error('Error downloading report:', err)
      setToast({ type: 'error', message: err.message || 'Failed to generate report' })
    }
  }, [slug, constituency])

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

  // Use the allocationTrend state (populated from API response in fetchData)

  // Determine the constituency key for chart data (matches allocationTrend format)
  const constituencyChartKey = constituency.name === 'Mukurwe-ini' ? 'Mukurwe-ini' : constituency.name

  const chartData = allocationTrend

  // Filter findings and anomalies for this constituency (though they should already be filtered by backend)
  const findings = auditFindings

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
            <p className="text-2xl font-serif font-semibold text-forest-700">{accountabilityScore ?? 0}</p>
            <p className="text-xs text-ink-muted">Accountability score</p>
          </div>
          <Button variant="secondary" onClick={handleDownloadReport}><FileDown size={16} /> Download report</Button>
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
                  <Line type="monotone" dataKey={constituencyChartKey} stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
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
                  <li key={f.id || f._id} className="flex justify-between gap-3 text-sm border-b border-line pb-3 last:border-0">
                    <div>
                      <p className="font-medium text-ink">{f.id}</p>
                      <p className="text-ink-muted mt-0.5">{f.finding || f.note}</p>
                      {f.mp_name && (
                       <p className="text-xs text-ink-faint mt-1">{f.mp_name}</p> 
                      )}
                    </div>
                    <Badge tone={f.finding_type?.toLowerCase() === 'misappropriation' ? 'risk' : 'good'}>
                      {f.finding_type?.toLowerCase() === 'misappropriation' ? 'Misappropriation' : 'Correct appropriation'}
                    </Badge>
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
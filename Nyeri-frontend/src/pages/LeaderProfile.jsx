import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown, MessageCircleQuestion } from 'lucide-react'
import { Card, Badge, Button, Toast } from '../components/ui'
import { Breadcrumbs, Tabs } from '../components/DataDisplay'
import { ScoreGauge, AIDisclaimer } from '../components/Insights'
import { LEADER_PHOTOS } from '../utils/leaderPhotos'
import APIService from '../services/api'
import { useSharedAsyncData } from '../hooks/useAsyncData.jsx'

// Governor-specific AI modules, with a readable title for each.
const GOVERNOR_AI_MODULES = [
  { key: 'fiscal_health', title: 'Fiscal health' },
  { key: 'dept_absorption', title: 'Department budget absorption' },
  { key: 'osr_analysis', title: 'Own-Source Revenue analysis' },
  { key: 'department_flags', title: 'Department risk flags' },
  { key: 'top_risks', title: 'Top county risks' },
]

// MP/constituency-specific AI modules.
const MP_AI_MODULES = [
  { key: 'anomalies', title: 'Anomaly detection' },
  { key: 'risk_score', title: 'Risk score' },
  { key: 'risk_level', title: 'Risk level' },
  { key: 'summary', title: 'Performance summary' },
  { key: 'peer_rank', title: 'Peer ranking' },
  { key: 'citizen_actions', title: 'Recommended citizen actions' },
]


function getTotalAllocationTrend(constituency) {
  const allocations = constituency?.allocations_ksm || {}
  return Object.entries(allocations).map(([fy, amount]) => ({
    fy: fy.replace('FY', '').replace('_', '/'),
    allocation: amount || 0,
  }))
}

// Turns a narrative_fields key like "risk_level" into "Risk level" for generic rendering.
function toLabel(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function LeaderProfile() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState('Verified Source Data')
  const [toast, setToast] = useState(null)

  // Fetch data independently with persistent caching (slug-specific keys)
  const { data: governorData, isLoading: govLoading, error: govError } = useSharedAsyncData(
    'governor-profile',
    () => APIService.getGovernorProfile(),
    { cacheTime: 10 * 60 * 1000 }
  )

  const { data: constituenciesResponse, isLoading: constLoading } = useSharedAsyncData(
    'all-constituencies',
    () => APIService.getAllConstituencies(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const constituenciesData = constituenciesResponse?.constituencies || constituenciesResponse || []

  const { data: governorScoreResponse, isLoading: govScoreLoading } = useSharedAsyncData(
    'governor-score',
    () => APIService.getGovernorScore(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const governorScore = governorScoreResponse?.score

  const { data: countyFinances, isLoading: financeLoading } = useSharedAsyncData(
    'county-finances',
    () => APIService.getCountyFinances(),
    { cacheTime: 10 * 60 * 1000 }
  )

  // Compute leader type and constituency from fetched data
  const isGovernor = Boolean(
    governorData &&
    slug &&
    (slug === governorData._id || slug === governorData.id)
  )
  const constituency = constituenciesData.find((c) => c.slug === slug || c._id === slug)

  // Fetch constituency score if MP
  const { data: constituencyScoreResponse, isLoading: constScoreLoading } = useSharedAsyncData(
    isGovernor ? 'dummy-constituency-score' : `constituency-score-${slug}`,
    () => isGovernor ? Promise.resolve(null) : APIService.getConstituencyScore(slug).catch(() => null),
    { cacheTime: 10 * 60 * 1000, immediate: !isGovernor && !!slug }
  )
  const constituencyScore = constituencyScoreResponse?.score ?? null

  // Fetch audit findings
  const { data: auditResponse, isLoading: auditLoading } = useSharedAsyncData(
    isGovernor ? 'county-audit-findings' : `constituency-audit-${slug}`,
    () => isGovernor
      ? APIService.getCountyAuditFindings()
      : APIService.getConstituencyAuditFindings(slug),
    { cacheTime: 10 * 60 * 1000 }
  )
  const auditFindings = (auditResponse?.audit_findings || auditResponse) || []

  // Fetch AI module data - defined inside component to access `slug` from useParams
  const fetchAiModule = useCallback(async (key, isGov) => {
    try {
      const url = isGov
        ? `${APIService.baseURL}/ai/governor/${key}`
        : `${APIService.baseURL}/ai/mp/${slug}/${key}`
      const res = await fetch(url)
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        console.warn(`AI module ${key} returned error:`, res.status, errorData)
        return null
      }
      const json = await res.json()
      if (json?.success && json.data) {
        return { narrative_fields: json.data.narrative_fields || {}, chart_data: json.data.chart_data || {} }
      }
      return null
    } catch (err) {
      console.warn(`Could not fetch AI module for key ${key}:`, err)
      return null
    }
  }, [slug])

  // Fetch AI modules
  const moduleList = useMemo(() => isGovernor ? GOVERNOR_AI_MODULES : MP_AI_MODULES, [isGovernor])

  const { data: aiModuleResults, isLoading: aiLoading } = useSharedAsyncData(
    isGovernor ? 'governor-ai-modules' : `mp-ai-modules-${slug}`,
    async () => {
      const results = await Promise.all(
        moduleList.map(async ({ key, title }) => {
          const data = await fetchAiModule(key, isGovernor)
          return data ? { key, title, ...data } : null
        })
      )
      return results.filter(Boolean)
    },
    { cacheTime: 10 * 60 * 1000 }
  )

  // Download PDF report
  const handleDownloadReport = useCallback(async () => {
    if (!slug) return

    try {
      setToast({ type: 'info', message: 'Generating report...' })
      let blob
      if (isGovernor && governorData) {
        blob = await APIService.downloadGovernorPDFReport(governorData.governor || governorData.name)
      } else if (constituency) {
        blob = await APIService.downloadConstituencyPDFReport(constituency.slug)
      } else {
        setToast({ type: 'error', message: 'Unable to generate report - leader not found' })
        return
      }

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const leaderName = isGovernor
        ? (governorData?.name || 'governor').replace(/\s+/g, '_')
        : (constituency?.mp?.name || constituency?.name || 'mp').replace(/\s+/g, '_')
      a.download = `${leaderName}_accountability_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setToast({ type: 'success', message: 'Report downloaded successfully!' })
    } catch (err) {
      console.error('Error downloading report:', err)
      setToast({ type: 'error', message: err.message || 'Failed to generate report' })
    }
  }, [slug, isGovernor, governorData, constituency])

  const loading = govLoading || constLoading || govScoreLoading || financeLoading || constScoreLoading || auditLoading || aiLoading
  const error = govError

  if (loading) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">
        Loading leader profile...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center">
        <h2 className="text-2xl font-semibold text-ink-danger mb-4">Error loading leader</h2>
        <p className="text-ink-muted">{error}</p>
        <Link to="/leaders" className="text-forest-600 hover:underline">
          ← Back to leaders
        </Link>
      </div>
    )
  }

  if (!isGovernor && !constituency) {
    return <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">Leader not found.</div>
  }

  const name = isGovernor ? governorData.name : constituency.mp?.name
  const position = isGovernor ? 'Governor' : 'Member of Parliament'
  const party = isGovernor ? governorData.party : (constituency.mp?.party || constituency.party)
  const place = isGovernor ? (governorData.county || 'Nyeri County') : constituency.name
  const score = isGovernor ? governorScore : constituencyScore

  const photoKey = isGovernor ? 'governor' : constituency.slug
  const photo = LEADER_PHOTOS[photoKey]


  const findings = auditFindings
  const trend = !isGovernor ? getTotalAllocationTrend(constituency) : []

  // Handle new pivoted format from /api/governor/finances (one doc per FY with equitable_share_kshb, conditional_grants_kshb, etc.)
  const revenueByYear = (Array.isArray(countyFinances) && countyFinances.length)
    ? countyFinances.map((fyData) => ({
        fy: fyData.financial_year,
        'Equitable Share': fyData.equitable_share_kshb || 0,
        'Conditional Grants': fyData.conditional_grants_kshb || 0,
        'Own Source Revenue': fyData.osr_kshb || 0,
        Expenditure: fyData.expenditure_kshb || 0,
        Development: fyData.development_kshb || 0,
        Recurrent: fyData.recurrent_kshb || 0
      })).sort((a, b) => a.fy.localeCompare(b.fy))
    : []

  console.log('DEBUG:', { slug, isGovernor, constituencySlug: constituency?.slug, photoKey })

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Leaders', to: '/leaders' }, { label: name }]} />

      {/* Header */}
      <Card className="p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-6 md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="h-20 w-20 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif text-2xl font-semibold shrink-0">
              {photo ? (
                <img
                src={photo}
                alt={name || 'Leader photo'}
                className="h-full w-full object-cover"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            ) : (
              name?.split(' ').slice(-1)[0]?.[0] || '?'
              )}
            </div>
            <div>
              <h1 className="text-2xl font-serif font-semibold text-ink">{name}</h1>
              <p className="text-ink-muted">{position} &middot; {party}</p>
              <p className="text-sm text-ink-faint">{place}</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <ScoreGauge score={score} size={104} />
            <div className="hidden lg:block max-w-[220px] text-sm text-ink-muted">
              Score weighs audit clarity, spending absorption and anomaly frequency over the past two financial years.
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-3 mt-6 pt-6 border-t border-line">
          <Button onClick={handleDownloadReport}><FileDown size={16} /> Generate Accountability Report</Button>
          <Button variant="secondary" onClick={() => navigate(`/assistant?about=${encodeURIComponent(name || '')}`)}>
            <MessageCircleQuestion size={16} /> Ask AI about this leader
          </Button>
        </div>
      </Card>

      <Tabs tabs={['Verified Source Data', 'Audit Findings', 'AI Analysis']} active={tab} onChange={setTab} />

      <div className="pt-6">
        {tab === 'Verified Source Data' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card className="p-6">
                <h3 className="font-serif font-semibold text-lg mb-4">
                  {isGovernor ? 'County financial performance' : 'NG-CDF allocation trend'}
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={isGovernor ? revenueByYear : trend}>
                      <CartesianGrid stroke="#E2E5E1" vertical={false} />
                      <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                      <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                      {isGovernor ? (
                        <>
                          <Line type="monotone" dataKey="Equitable Share" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                          <Line type="monotone" dataKey="Conditional Grants" stroke="#8A928C" strokeWidth={2} dot={{ r: 3 }} />
                        </>
                      ) : (
                        <Line type="monotone" dataKey="allocation" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                      )}           
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card className="p-6">
                <h3 className="font-serif font-semibold text-lg mb-3">Development information</h3>
                <p className="text-sm text-ink-muted">
                  {isGovernor
                    ? 'County development projects span health, water, roads, agriculture and education. See the County Dashboard for full departmental absorption figures.'
                    : `NG-CDF-funded projects in ${constituency.name} include bursary disbursement, classroom construction and water infrastructure. Detailed project-level tracking is being expanded.`}
                </p>
              </Card>
            </div>
            <Card className="p-6 h-fit">
              <h3 className="font-serif font-semibold mb-3">Evidence sources</h3>
              <ul className="text-sm text-ink-muted space-y-2 list-disc pl-4">
                <li>Office of the Auditor-General constituency/county reports</li>
                <li>National Treasury / NG-CDF Board disbursement records</li>
                <li>Nyeri County fiscal reports, FY2022/23 &ndash; FY2025/26</li>
              </ul>
            </Card>
          </div>
        )}
        
        {tab === 'Audit Findings' && (() => {
          const isSourcesRow = (f) => f.category?.trim().startsWith('Sources')
          const realFindings = findings.filter((f) => !isSourcesRow(f))
          const sourcesRow = findings.find(isSourcesRow)

          return (
          <div className="space-y-4">
            {realFindings.length === 0 && <p className="text-sm text-ink-muted">No audit findings recorded for this leader in the current dataset.</p>}
            {realFindings.map((f) => (
              <Card key={f._id} className="p-5">
                {isGovernor ? (
                  <>
                    <div className="flex justify-between gap-3 mb-2">
                      <p className="font-medium text-ink whitespace-pre-line">{f.category}</p>
                      <Badge tone={f.finding_type?.toLowerCase() === 'misappropriation' ? 'risk' : 'good'}>
                        {f.finding_type?.toLowerCase() === 'misappropriation' ? 'Misappropriation' : 'Correct appropriation'}
                      </Badge>
                    </div>
                    <p className="text-sm text-ink-muted">{f.misappropriation_notes}</p>
                    {f.recommendation && (
                      <p className="text-sm text-ink-muted mt-2">{f.recommendation}</p>
                    )}
                    <p className="text-xs text-ink-faint mt-2">
                      {[f.financial_year, f.severity, f.amount_flagged_kshm ? `Ksh ${f.amount_flagged_kshm}M flagged` : null]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="flex justify-between gap-3 mb-2">
                      <p className="font-medium text-ink">{f.id}</p>
                      <Badge tone={f.finding_type?.toLowerCase() === 'misappropriation' ? 'risk' : 'good'}>
                        {f.finding_type?.toLowerCase() === 'misappropriation' ? 'Misappropriation' : 'Correct appropriation'}
                      </Badge>
                    </div>
                      <p className="text-sm text-ink-muted">{f.finding || f.note}</p>
                        {f.mp_name && (
                        <p className="text-xs text-ink-faint mt-2">{f.mp_name}</p>
                        )}
                  </>
                )}
              </Card>
            ))}

            {sourcesRow && (
              <p className="text-xs text-ink-faint pt-2 border-t border-line whitespace-pre-line">
                {sourcesRow.category}
              </p>
            )}
          </div>
          )
        })()} 


        {tab === 'AI Analysis' && (
          <div className="space-y-6">
            <AIDisclaimer />

            {aiModuleResults.length === 0 ? (
              <p className="text-sm text-ink-muted">
                {isGovernor
                  ? 'No AI analysis currently available for the county.'
                  : 'No AI analysis currently available for this constituency.'}
              </p>
            ) : (
              aiModuleResults.map((mod) => (
                <Card key={mod.key} className="p-6">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-4">
                    {mod.title}
                  </p>

                  {Object.entries(mod.narrative_fields).length === 0 ? (
                    <p className="text-sm text-ink-muted">No narrative analysis returned for this module.</p>
                  ) : (
                    <div className="space-y-4">
                      {Object.entries(mod.narrative_fields).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-sm font-medium text-ink">{toLabel(key)}</p>
                          <div className="text-sm text-ink-muted mt-0.5">
                            {Array.isArray(value) ? (
                              <ul className="list-disc pl-4 space-y-1">
                                {value.map((item, idx) => (
                                  <li key={idx}>
                                    {typeof item === 'object' && item !== null ? (
                                      <>
                                        <p className="font-medium">{item.title || item.name || item.department || 'Item'}</p>
                                        {item.description && <p>{item.description}</p>}
                                        {item.severity && <p className="text-xs">Severity: {item.severity}</p>}
                                        {item.flag_type && <p className="text-xs">Type: {item.flag_type}</p>}
                                        {item.amount_at_risk && <p className="text-xs">Amount at risk: {item.amount_at_risk}</p>}
                                        {item.recommended_action && <p className="text-xs">Action: {item.recommended_action}</p>}
                                        {item.narrative && <p className="text-xs">{item.narrative}</p>}
                                        {item.rating && <p className="text-xs">Rating: {item.rating}</p>}
                                        {item.performance && <p className="text-xs">Performance: {item.performance}</p>}
                                        {item.target !== undefined && item.actual !== undefined && (
                                          <p className="text-xs">Target: {item.target}, Actual: {item.actual}</p>
                                        )}
                                      </>
                                    ) : (
                                      String(item)
                                    )}
                                  </li>
                                ))}
                              </ul>
                            ) : typeof value === 'object' && value !== null ? (
                              <pre className="whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded">{JSON.stringify(value, null, 2)}</pre>
                            ) : (
                              String(value)
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              ))
            )}
          </div>
        )}
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
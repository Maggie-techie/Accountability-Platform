import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown, MessageCircleQuestion } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs, Tabs } from '../components/DataDisplay'
import { ScoreGauge, LimeChart, AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'

function getTotalAllocationTrend(constituency) {
  const allocations = constituency?.allocations_ksm || {}
  return Object.entries(allocations).map(([fy, amount]) => ({
    fy: fy.replace('FY', '').replace('_', '/'),
    allocation: amount || 0,
  }))
}

export default function LeaderProfile() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState('Verified Source Data')

  const [governorData, setGovernorData] = useState(null)
  const [constituenciesData, setConstituenciesData] = useState([])
  const [auditFindings, setAuditFindings] = useState([])
  const [anomaliesData, setAnomaliesData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [governorResponse, constituenciesResponse, auditResponse] = await Promise.all([
          APIService.getGovernorProfile(),
          APIService.getAllConstituencies(),
          APIService.getCountyAuditFindings(),
        ])

        setGovernorData(governorResponse)
        setConstituenciesData(constituenciesResponse.constituencies || constituenciesResponse)
        setAuditFindings(auditResponse.audit_findings || auditResponse || [])

        try {
          const res = await fetch(`http://localhost:5000/api/ai/mp/${slug}/anomalies`)
          const anomaliesResponse = await res.json()
          if (anomaliesResponse?.success && Array.isArray(anomaliesResponse.data)) {
            setAnomaliesData(anomaliesResponse.data)
          } else {
            setAnomaliesData([])
          }
        } catch (err) {
          console.warn('Could not fetch anomalies from AI endpoint:', err)
          setAnomaliesData([])
        }

        setError(null)
      } catch (err) {
        console.error('Error fetching leader profile data:', err)
        setError(err.message || 'Failed to load leader data')
        setGovernorData(null)
        setConstituenciesData([])
        setAuditFindings([])
        setAnomaliesData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [slug])

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

  // Match either the governor (_id or legacy id) or a constituency (slug or _id)
  const isGovernor = governorData && (slug === governorData._id || slug === governorData.id)
  const constituency = constituenciesData.find((c) => c.slug === slug || c._id === slug)

  if (!isGovernor && !constituency) {
    return <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">Leader not found.</div>
  }

  const name = isGovernor ? governorData.name : constituency.mp?.name
  const position = isGovernor ? 'Governor' : 'Member of Parliament'
  const party = isGovernor ? governorData.party : (constituency.mp?.party || constituency.party)
  const place = isGovernor ? (governorData.county || 'Nyeri County') : constituency.name
  const score = isGovernor ? governorData.accountabilityScore : constituency.accountabilityScore

  const findings = auditFindings.filter((f) =>
    isGovernor
      ? f.entityType === 'department'
      : f.entity?.toLowerCase().includes((constituency.name || '').toLowerCase())
  )
  const relatedAnomalies = anomaliesData.filter((a) =>
    isGovernor
      ? a.entityType === 'Department'
      : a.entity?.toLowerCase().includes((constituency.name || '').toLowerCase())
  )
  const trend = !isGovernor ? getTotalAllocationTrend(constituency) : []

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Leaders', to: '/leaders' }, { label: name }]} />

      {/* Header */}
      <Card className="p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-6 md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="h-20 w-20 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif text-2xl font-semibold shrink-0">
              {name?.split(' ').slice(-1)[0]?.[0] || '?'}
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
          <Button><FileDown size={16} /> Generate Accountability Report</Button>
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
                    <LineChart data={isGovernor ? [] : trend}>
                      <CartesianGrid stroke="#E2E5E1" vertical={false} />
                      <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                      <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                      <Line type="monotone" dataKey="allocation" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
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

        {tab === 'Audit Findings' && (
          <div className="space-y-4">
            {findings.length === 0 && <p className="text-sm text-ink-muted">No audit findings recorded for this leader in the current dataset.</p>}
            {findings.map((f) => (
              <Card key={f.id || f._id} className="p-5">
                <div className="flex justify-between gap-3 mb-2">
                  <p className="font-medium text-ink">{f.category}</p>
                  <Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge>
                </div>
                <p className="text-sm text-ink-muted">{f.finding}</p>
                <p className="text-xs text-ink-faint mt-2">FY {f.financialYear} &middot; KSh {f.amountKshm}M flagged</p>
              </Card>
            ))}
          </div>
        )}

        {tab === 'AI Analysis' && (
          <div className="space-y-6">
            <AIDisclaimer />
            {relatedAnomalies.length === 0 && <p className="text-sm text-ink-muted">No anomalies currently detected for this leader.</p>}
            {relatedAnomalies.map((a) => (
              <Card key={a.id || a._id} className="p-6">
                <div className="flex justify-between gap-3 mb-3">
                  <div>
                    <p className="font-serif font-semibold text-ink">{a.title}</p>
                    <p className="text-xs text-ink-faint">{a.category} &middot; FY {a.financialYear}</p>
                  </div>
                  <Badge tone={a.severity === 'High' ? 'risk' : a.severity === 'Medium' ? 'watch' : 'good'}>{a.severity}</Badge>
                </div>
                <p className="text-sm text-ink-muted mb-4">{a.summary}</p>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-2">LIME explanation</p>
                <LimeChart features={a.limeFeatures} />
                <Link to={`/anomalies/${a.id || a._id}`} className="inline-block mt-4 text-sm text-forest-700 hover:underline">
                  Open full investigation &rarr;
                </Link>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
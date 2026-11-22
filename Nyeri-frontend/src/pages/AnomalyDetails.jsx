import { useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown, Eye } from 'lucide-react'
import { Card, Badge, SeverityBadge, Button, EmptyState } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { LimeChart, AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'

export default function AnomalyDetails() {
  const { id } = useParams()
  const [anomaly, setAnomaly] = useState(null)
  const [relatedFinding, setRelatedFinding] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!id) {
        setError('Anomaly ID is required')
        setLoading(false)
        return
      }

      try {
        setLoading(true)

        // First, try to fetch from the anomalies list page data
        // We'll need to fetch all anomalies to find the matching one
        // Since anomalies come from multiple sources, we fetch from the AI endpoints

        // Try to extract constituency slug from ID (format: mp-ai-{slug}-{year}-{index})
        let constituencySlug = null
        let anomalyType = null

        if (id.startsWith('mp-ai-')) {
          anomalyType = 'ai'
          const parts = id.split('-')
          constituencySlug = parts[2] // mp-ai-{slug}-{year}-{index}
        } else if (id.startsWith('gnn-')) {
          anomalyType = 'gnn'
          const parts = id.split('-')
          constituencySlug = parts[1]
        } else if (id.startsWith('audit-constituency-')) {
          anomalyType = 'audit'
          const parts = id.split('-')
          constituencySlug = parts[2]
        } else if (id.startsWith('gov-risk-') || id.startsWith('gov-flag-')) {
          anomalyType = 'governor'
        } else if (id.startsWith('audit-county-')) {
          anomalyType = 'county-audit'
        }

        let foundAnomaly = null
        let foundFinding = null

        if (anomalyType === 'ai' && constituencySlug) {
          // Fetch MP AI anomalies
          const res = await APIService.getMPAIAnomalies(constituencySlug)
          if (res?.success && res.data) {
            const anomalies = res.data.narrative_fields?.anomalies || []
            const summary = res.data.narrative_fields?.summary || ''
            const matching = anomalies.find((a, i) => `mp-ai-${constituencySlug}-${a.year || 'unknown'}-${i}` === id)
            if (matching) {
              foundAnomaly = {
                id,
                title: matching.title || 'Flagged anomaly',
                entity: constituencySlug,
                category: matching.category || 'Uncategorized',
                financialYear: matching.year || 'Unknown',
                severity: matching.severity || 'Medium',
                status: 'Flagged',
                summary: matching.description || summary,
                sourceType: 'AI',
                sourceLabel: 'MP AI Analysis',
                expected: matching.expected || 0,
                observed: matching.observed || 0,
                unit: matching.unit || 'KSh M',
                limeFeatures: matching.limeFeatures || []
              }
            }
          }
        } else if (anomalyType === 'gnn' && constituencySlug) {
          // Fetch GNN anomalies
          try {
            const res = await fetch(`${APIService.baseURL}/ai/mp/${constituencySlug}/gnn_anomalies`)
            if (res.ok) {
              const json = await res.json()
              if (json?.success && json.data) {
                const anomalies = json.data || []
                const matching = anomalies.find((a, i) => `gnn-${constituencySlug}-${a.metadata?.fiscal_year || 'unknown'}-${i}` === id)
                if (matching) {
                  foundAnomaly = {
                    id,
                    title: matching.explanation || 'GNN Detected Anomaly',
                    entity: constituencySlug,
                    category: 'ML Detection',
                    financialYear: matching.metadata?.fiscal_year || 'Unknown',
                    severity: matching.anomaly_score > 0.8 ? 'High' : matching.anomaly_score > 0.5 ? 'Medium' : 'Low',
                    status: 'Detected',
                    summary: `Anomaly score: ${matching.anomaly_score?.toFixed(2) || 'N/A'}, Rank: ${matching.anomaly_rank || 'N/A'}. ${matching.features?.financial ? `Allocation: KSh ${matching.features.financial.total_allocation_kshm?.toLocaleString()}M` : ''}`,
                    sourceType: 'ML',
                    sourceLabel: 'GNN Model',
                    expected: 0,
                    observed: matching.anomaly_score || 0,
                    unit: 'score',
                    limeFeatures: []
                  }
                }
              }
            }
          } catch (err) {
            console.warn('Could not fetch GNN anomalies:', err)
          }
        } else if (anomalyType === 'audit' && constituencySlug) {
          // Fetch constituency audit findings
          try {
            const res = await fetch(`${APIService.baseURL}/constituency/audit/${constituencySlug}`)
            if (res.ok) {
              const json = await res.json()
              const findings = json.audit_findings || json || []
              const matching = findings.find((f, i) => `audit-constituency-${constituencySlug}-${f.id || f._id || i}` === id)
              if (matching) {
                foundAnomaly = {
                  id,
                  title: matching.note || matching.finding || matching.misappropriation_notes || 'Misappropriation found',
                  entity: constituencySlug,
                  category: matching.category || matching.severity || 'Audit',
                  financialYear: matching.financial_year || matching.fy_reviewed || 'Unknown',
                  severity: matching.severity === 'Adverse' ? 'High' : matching.severity === 'Qualified' ? 'Medium' : 'High',
                  status: 'Confirmed',
                  summary: matching.recommendation || matching.misappropriation_notes || '',
                  sourceType: 'Audit',
                  sourceLabel: 'Constituency Audit Finding',
                  expected: 0,
                  observed: matching.amount_flagged_kshm || matching.amount_at_risk || 0,
                  unit: 'KSh M',
                  limeFeatures: []
                }
                foundFinding = matching
              }
            }
          } catch (err) {
            console.warn('Could not fetch audit findings:', err)
          }
        } else if (anomalyType === 'governor') {
          // Fetch governor top risks
          try {
            const res = await APIService.getGovernorTopRisks()
            if (res?.success && res.data) {
              const risks = res.data.narrative_fields?.risks || []
              const matching = risks.find((r, i) => `gov-risk-${r.title?.replace(/\s+/g, '-').toLowerCase() || 'unknown'}-${i}` === id)
              if (matching) {
                foundAnomaly = {
                  id,
                  title: matching.title || 'Government Risk',
                  entity: 'County Government',
                  category: matching.category || 'Governance',
                  financialYear: 'Current',
                  severity: matching.severity || 'Medium',
                  status: 'Identified',
                  summary: matching.description || matching.mitigation || '',
                  sourceType: 'Risk',
                  sourceLabel: 'Governor Risk Analysis',
                  expected: 0,
                  observed: 0,
                  unit: '',
                  limeFeatures: []
                }
              }
            }
          } catch (err) {
            console.warn('Could not fetch governor risks:', err)
          }
        } else if (anomalyType === 'county-audit') {
          // Fetch county audit findings
          try {
            const res = await APIService.getCountyAuditFindings()
            const findings = res?.audit_findings || res || []
            const matching = findings.find((f, i) => `audit-county-${f.id || f._id || i}` === id)
            if (matching) {
              foundAnomaly = {
                id,
                title: matching.note || matching.finding || matching.misappropriation_notes || 'Misappropriation found',
                entity: 'Nyeri County',
                category: matching.category || matching.severity || 'Audit',
                financialYear: matching.financial_year || matching.fy_reviewed || 'Unknown',
                severity: matching.severity === 'Adverse' ? 'High' : matching.severity === 'Qualified' ? 'Medium' : 'High',
                status: 'Confirmed',
                summary: matching.recommendation || matching.misappropriation_notes || '',
                sourceType: 'Audit',
                sourceLabel: 'County Audit Finding',
                expected: 0,
                observed: matching.amount_flagged_kshm || matching.amount_at_risk || 0,
                unit: 'KSh M',
                limeFeatures: []
              }
              foundFinding = matching
            }
          } catch (err) {
            console.warn('Could not fetch county audit findings:', err)
          }
        }

        if (foundAnomaly) {
          setAnomaly(foundAnomaly)
          if (foundFinding) {
            setRelatedFinding(foundFinding)
          }
          setError(null)
        } else {
          setError('Anomaly not found')
        }
      } catch (err) {
        console.error('Error fetching anomaly details:', err)
        setError(err.message || 'Failed to load anomaly details')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [id])

  if (loading) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies', to: '/anomalies' }, { label: id }]} />
        <div className="text-center text-ink-muted">Loading anomaly details...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies', to: '/anomalies' }, { label: id }]} />
        <div className="text-center text-ink-danger">{error}</div>
        <Link to="/anomalies" className="inline-block mt-4 text-forest-700 hover:underline">&larr; Back to anomalies</Link>
      </div>
    )
  }

  if (!anomaly) {
    return (
      <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">Anomaly not found.</div>
    )
  }

  const chartData = [
    { name: 'Expected', value: anomaly.expected },
    { name: 'Observed', value: anomaly.observed },
  ]

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Anomalies', to: '/anomalies' }, { label: anomaly.id }]} />

      <Card className="p-6 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div>
            <p className="text-xs text-ink-faint mb-1">{anomaly.id}</p>
            <h1 className="text-2xl font-serif font-semibold text-ink">{anomaly.title}</h1>
            <p className="text-ink-muted mt-1">{anomaly.entity} &middot; {anomaly.category} &middot; FY {anomaly.financialYear}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <SeverityBadge severity={anomaly.severity} />
            <Badge>{anomaly.status}</Badge>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary"><Eye size={16} /> View source data</Button>
          <Button><FileDown size={16} /> Generate report</Button>
        </div>
      </Card>

      <Alert className="mb-6" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Expected vs. observed</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                  <CartesianGrid stroke="#E2E5E1" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 13, fill: '#1C1F1D' }} axisLine={false} tickLine={false} width={80} />
                  <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} formatter={(v) => `${v} ${anomaly.unit}`} />
                  <Bar dataKey="value" fill="#8A928C" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-sm text-ink-muted mt-2">
              Expected: <span className="font-medium text-ink">{anomaly.expected} {anomaly.unit}</span> &middot;
              {' '}Observed: <span className="font-medium text-clay-500">{anomaly.observed} {anomaly.unit}</span>
            </p>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-3">AI-generated interpretation</h3>
            <p className="text-sm text-ink-muted">{anomaly.summary}</p>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">LIME explanation</h3>
            <p className="text-sm text-ink-muted mb-4">
              These are the features that most influenced the AI model's classification of this pattern as anomalous.
            </p>
            <LimeChart features={anomaly.limeFeatures} />
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Related audit finding</h3>
            {relatedFinding ? (
              <div className="text-sm">
                <p className="font-medium text-ink">{relatedFinding.category}</p>
                <p className="text-ink-muted mt-1">{relatedFinding.finding}</p>
                <Badge tone={relatedFinding.severity === 'High' ? 'risk' : 'watch'} className="mt-2">{relatedFinding.severity}</Badge>
              </div>
            ) : (
              <p className="text-sm text-ink-muted">No linked Auditor-General finding yet. This anomaly was detected independently by the AI model.</p>
            )}
          </Card>
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Related profile</h3>
            {anomaly.entity !== 'County Government' && anomaly.entity !== 'Nyeri County' ? (
              <Link to={`/constituencies/${anomaly.entity}`} className="text-sm text-forest-700 hover:underline">
                View {anomaly.entity} constituency profile &rarr;
              </Link>
            ) : (
              <Link to="/county" className="text-sm text-forest-700 hover:underline">
                View county profile &rarr;
              </Link>
            )}
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}

function Alert() {
  return (
    <div className="rounded-md border border-gold-100 bg-gold-50 p-4 text-sm text-ink-muted mb-2">
      <span className="font-semibold text-ink">An anomaly is an indicator of an unusual pattern</span> and does not
      by itself establish fraud, corruption or wrongdoing.
    </div>
  )
}

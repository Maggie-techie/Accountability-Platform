import { useMemo, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LayoutGrid, List, Brain, AlertTriangle, Database, Zap } from 'lucide-react'
import { Card, Badge, SeverityBadge, EmptyState } from '../components/ui'
import { Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import APIService from '../services/api'

// Source type colors and icons
const SOURCE_STYLES = {
  'AI': { color: '#14532D', bg: '#F0F5F0', icon: Brain, label: 'AI Detected' },
  'ML': { color: '#A6431F', bg: '#FDF0ED', icon: Zap, label: 'ML/GNN Detected' },
  'Audit': { color: '#2E6B44', bg: '#E8F5E8', icon: Database, label: 'Audit Finding' },
  'Risk': { color: '#C08A28', bg: '#FEF9E7', icon: AlertTriangle, label: 'Risk Flag' }
}

// Transform MP AI anomalies to common format
function transformMPAIAnomalies(constituency, aiData) {
  const anomalies = aiData?.narrative_fields?.anomalies || []
  const summary = aiData?.narrative_fields?.summary || ''

  return anomalies.map((anomaly, i) => ({
    id: `mp-ai-${constituency.slug}-${anomaly.year || 'unknown'}-${i}`,
    title: anomaly.title || 'Flagged anomaly',
    entity: constituency.name,
    category: anomaly.category || 'Uncategorized',
    financialYear: anomaly.year || 'Unknown',
    severity: anomaly.severity || 'Medium',
    status: 'Flagged',
    summary: anomaly.description || summary,
    sourceType: 'AI',
    sourceLabel: 'MP AI Analysis'
  }))
}

// Transform Governor top risks to common format
function transformGovernorRisks(aiData) {
  const risks = aiData?.narrative_fields?.risks || []
  return risks.map((risk, i) => ({
    id: `gov-risk-${risk.title?.replace(/\s+/g, '-').toLowerCase() || 'unknown'}-${i}`,
    title: risk.title || 'Government Risk',
    entity: 'County Government',
    category: risk.category || 'Governance',
    financialYear: 'Current',
    severity: risk.severity || 'Medium',
    status: 'Identified',
    summary: risk.description || risk.mitigation || '',
    sourceType: 'Risk',
    sourceLabel: 'Governor Risk Analysis'
  }))
}

// Transform Governor department flags to common format
function transformDepartmentFlags(aiData) {
  const flags = aiData?.narrative_fields?.flags || []
  return flags.map((flag, i) => ({
    id: `gov-flag-${flag.department?.replace(/\s+/g, '-').toLowerCase() || 'unknown'}-${i}`,
    title: `${flag.department || 'Department'} - ${flag.flag_type || 'Flag'}`,
    entity: 'County Government',
    category: flag.flag_type || 'Department',
    financialYear: 'Current',
    severity: flag.severity || 'Medium',
    status: 'Flagged',
    summary: flag.description || '',
    sourceType: 'Risk',
    sourceLabel: 'Department Flag'
  }))
}

// Transform audit findings (misappropriation) to common format
function transformAuditFindings(findings, entityName, entityType) {
  return findings
    .filter(f => f.finding_type?.toLowerCase() === 'misappropriation')
    .map((f, i) => ({
      id: `audit-${entityType}-${entityName.replace(/\s+/g, '-')}-${f.id || f._id || i}`,
      title: f.note || f.finding || f.misappropriation_notes || 'Misappropriation found',
      entity: entityName,
      category: f.category || f.severity || 'Audit',
      financialYear: f.financial_year || f.fy_reviewed || 'Unknown',
      severity: f.severity === 'Adverse' ? 'High' : f.severity === 'Qualified' ? 'Medium' : 'High',
      status: 'Confirmed',
      summary: f.recommendation || f.misappropriation_notes || '',
      amount: f.amount_flagged_kshm || f.amount_at_risk,
      sourceType: 'Audit',
      sourceLabel: `${entityType} Audit Finding`
    }))
}

// Transform GNN anomalies to common format
function transformGNNAnomalies(constituency, gnnData) {
  const anomalies = gnnData?.data || []
  return anomalies.map((a, i) => ({
    id: `gnn-${constituency.slug}-${a.metadata?.fiscal_year || 'unknown'}-${i}`,
    title: a.explanation || 'GNN Detected Anomaly',
    entity: constituency.name,
    category: 'ML Detection',
    financialYear: a.metadata?.fiscal_year || 'Unknown',
    severity: a.anomaly_score > 0.8 ? 'High' : a.anomaly_score > 0.5 ? 'Medium' : 'Low',
    status: 'Detected',
    summary: `Anomaly score: ${a.anomaly_score?.toFixed(2) || 'N/A'}, Rank: ${a.anomaly_rank || 'N/A'}. ${a.features?.financial ? `Allocation: KSh ${a.features.financial.total_allocation_kshm?.toLocaleString()}M` : ''}`,
    sourceType: 'ML',
    sourceLabel: 'GNN Model'
  }))
}

export default function Anomalies() {
  const [severity, setSeverity] = useState('')
  const [fy, setFy] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [view, setView] = useState('table')

  // State for data fetching
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)

        // Fetch all required data in parallel
        const [
          constituenciesRes,
          governorTopRisksRes,
          governorDeptFlagsRes,
          countyAuditRes
        ] = await Promise.all([
          APIService.getAllConstituencies(),
          APIService.getGovernorTopRisks().catch(() => ({ success: false })),
          APIService.getGovernorDepartmentFlags().catch(() => ({ success: false })),
          APIService.getCountyAuditFindings().catch(() => ({ audit_findings: [] }))
        ])

        const constituencies = constituenciesRes.constituencies || constituenciesRes || []

        // Fetch MP AI anomalies and GNN anomalies for each constituency
        const mpResults = await Promise.all(
          constituencies.map(async (c) => {
            const results = []

            // MP AI Anomalies
            try {
              const res = await APIService.getMPAIAnomalies(c.slug)
              if (res?.success && res.data) {
                results.push(...transformMPAIAnomalies(c, res.data))
              }
            } catch (err) {
              console.warn(`Could not fetch AI anomalies for ${c.slug}:`, err)
            }

            // GNN Anomalies
            try {
              const res = await fetch(`${APIService.baseURL}/ai/mp/${c.slug}/gnn_anomalies`)
              if (res.ok) {
                const json = await res.json()
                if (json?.success && json.data) {
                  results.push(...transformGNNAnomalies(c, json))
                }
              }
            } catch (err) {
              console.warn(`Could not fetch GNN anomalies for ${c.slug}:`, err)
            }

            // Constituency Audit Findings
            try {
              const res = await fetch(`${APIService.baseURL}/constituency/audit/${c.slug}`)
              if (res.ok) {
                const json = await res.json()
                const findings = json.audit_findings || json || []
                results.push(...transformAuditFindings(findings, c.name, 'Constituency'))
              }
            } catch (err) {
              console.warn(`Could not fetch audit findings for ${c.slug}:`, err)
            }

            return results
          })
        )

        // Transform Governor risks
        const governorRisks = []
        if (governorTopRisksRes?.success && governorTopRisksRes.data) {
          governorRisks.push(...transformGovernorRisks(governorTopRisksRes.data))
        }
        if (governorDeptFlagsRes?.success && governorDeptFlagsRes.data) {
          governorRisks.push(...transformDepartmentFlags(governorDeptFlagsRes.data))
        }

        // Transform County Audit Findings
        const countyAuditFindings = countyAuditRes?.audit_findings || countyAuditRes || []
        const countyAudit = transformAuditFindings(countyAuditFindings, 'Nyeri County', 'County')

        // Combine all anomalies
        const allAnomalies = [
          ...mpResults.flat(),
          ...governorRisks,
          ...countyAudit
        ]

        setAnomalies(allAnomalies)
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

  // All hooks must run unconditionally, on every render, before any early return.
  const filtered = useMemo(() => anomalies.filter((a) =>
    (!severity || a.severity === severity) &&
    (!fy || a.financialYear === fy) &&
    (!category || a.category === category) &&
    (!status || a.status === status) &&
    (!sourceType || a.sourceType === sourceType)
  ), [anomalies, severity, fy, category, status, sourceType])

  // All hooks must run unconditionally, before any early returns
  const counts = useMemo(() => ({
    High: filtered.filter((a) => a.severity === 'High').length,
    Medium: filtered.filter((a) => a.severity === 'Medium').length,
    Low: filtered.filter((a) => a.severity === 'Low').length
  }), [filtered])

  const sourceCounts = useMemo(() => {
    const counts = {}
    filtered.forEach(a => {
      counts[a.sourceType] = (counts[a.sourceType] || 0) + 1
    })
    return counts
  }, [filtered])

  // Handle loading and error states
  if (loading) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies' }]} />
        <h1 className="text-3xl font-semibold mb-1">All County Financial Anomalies (ML & AI)</h1>
        <p className="text-ink-muted mb-6">Loading anomalies...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Anomalies' }]} />
        <h1 className="text-3xl font-semibold mb-1">All County Financial Anomalies (ML & AI)</h1>
        <p className="text-ink-danger mb-6">{error}</p>
        <div className="mt-4">
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Anomalies' }]} />
      <h1 className="text-3xl font-semibold mb-1">All County Financial Anomalies (ML & AI)</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">
        Comprehensive view of anomalies detected across AI analysis, ML models, audit findings, and risk assessments.
      </p>

      {/* Summary Cards - Severity */}
      <div className="grid grid-cols-3 gap-4 mb-4 max-w-md">
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-clay-500">{counts.High}</p><p className="text-xs text-ink-muted">High</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-gold-500">{counts.Medium}</p><p className="text-xs text-ink-muted">Medium</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-serif font-semibold text-forest-600">{counts.Low}</p><p className="text-xs text-ink-muted">Low</p></Card>
      </div>

      {/* Summary Cards - Source Types */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 max-w-2xl">
        {Object.entries(SOURCE_STYLES).map(([key, style]) => (
          <Card key={key} className="p-3 text-center" style={{ backgroundColor: style.bg }}>
            <style.icon size={20} className="mx-auto mb-1" style={{ color: style.color }} />
            <p className="text-lg font-serif font-semibold" style={{ color: style.color }}>{sourceCounts[key] || 0}</p>
            <p className="text-xs text-ink-muted">{style.label}</p>
          </Card>
        ))}
      </div>

      <FilterBar>
        <Select label="Severity" value={severity} onChange={setSeverity} options={['High', 'Medium', 'Low']} />
        <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(filtered.map((a) => a.financialYear))]} />
        <Select label="Category" value={category} onChange={setCategory} options={[...new Set(filtered.map((a) => a.category))]} />
        <Select label="Status" value={status} onChange={setStatus} options={[...new Set(filtered.map((a) => a.status))]} />
        <Select label="Source" value={sourceType} onChange={setSourceType} options={['AI', 'ML', 'Audit', 'Risk']} />
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
              columns={['Anomaly', 'Entity', 'Category', 'FY', 'Severity', 'Status', 'Source']}
              rows={filtered}
              keyField="id"
              renderRow={(a) => {
                const sourceStyle = SOURCE_STYLES[a.sourceType] || SOURCE_STYLES['AI']
                return (
                  <>
                    <td className="py-3 pr-4 pl-2"><Link to={`/anomalies/${a.id}`} className="font-medium text-ink hover:text-forest-700">{a.title}</Link></td>
                    <td className="py-3 pr-4 text-ink-muted">{a.entity}</td>
                    <td className="py-3 pr-4 text-ink-muted">{a.category}</td>
                    <td className="py-3 pr-4 text-ink-muted">{a.financialYear}</td>
                    <td className="py-3 pr-4"><SeverityBadge severity={a.severity} /></td>
                    <td className="py-3 pr-4 text-ink-muted">{a.status}</td>
                    <td className="py-3 pr-4">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: sourceStyle.bg, color: sourceStyle.color }}>
                        <sourceStyle.icon size={10} /> {sourceStyle.label}
                      </span>
                    </td>
                  </>
                )
              }}
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((a) => {
              const sourceStyle = SOURCE_STYLES[a.sourceType] || SOURCE_STYLES['AI']
              return (
                <Link key={a.id} to={`/anomalies/${a.id}`}>
                  <Card className="p-4 h-full hover:border-forest-300 transition-colors">
                    <div className="flex justify-between mb-2">
                      <SeverityBadge severity={a.severity} />
                      <Badge>{a.status}</Badge>
                    </div>
                    <p className="font-serif font-semibold text-ink mb-1">{a.title}</p>
                    <p className="text-xs text-ink-faint mb-2">{a.entity} &middot; {a.category} &middot; FY {a.financialYear}</p>
                    <p className="text-sm text-ink-muted line-clamp-2">{a.summary}</p>
                    <div className="mt-2 pt-2 border-t border-line">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: sourceStyle.bg, color: sourceStyle.color }}>
                        <sourceStyle.icon size={10} /> {sourceStyle.label}
                      </span>
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
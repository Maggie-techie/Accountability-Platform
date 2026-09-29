import { useMemo, useState, useEffect, useCallback } from 'react'
import { Pencil, Trash2, Eye, Plus } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { SearchBar } from '../../components/Filters'
import { Pagination, Table, usePagination } from '../../components/DataDisplay'
import APIService from '../../services/api'

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const configs = {
  leaders: { title: 'Leaders' },
  constituencies: { title: 'Constituencies' },
  financial: { title: 'County Finances' },
  allocations: { title: 'NG-CDF Allocations' },
  audit: { title: 'Audit Findings' },
  departments: { title: 'Departmental Data' },
}

// Backend paths per entity. NOTE: trailing slashes match Flask routes that are
// defined with '/', which avoids the 308 redirect that breaks CORS preflights.
const endpoints = {
  constituencies: '/constituency/',
  financial: '/governor/finances',
  allocations: '/constituency/allocations',
  audit: '/governor/audit',
  departments: '/governor/departments',
}

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------
// The API wraps payloads as { success, data }.
const unwrap = (json) =>
  json && typeof json === 'object' && !Array.isArray(json) && 'data' in json ? json.data : json

// Always return an array, whatever shape the backend sends.
const toArray = (value, ...keys) => {
  if (Array.isArray(value)) return value
  for (const key of keys) {
    if (Array.isArray(value?.[key])) return value[key]
  }
  return []
}

// Collapse stray newlines/whitespace that come from the source spreadsheets.
const clean = (v) => (v == null || v === '' ? null : String(v).replace(/\s+/g, ' ').trim())

const fmtNum = (n) => {
  const num = Number(n)
  return n == null || n === '' || !Number.isFinite(num) ? '—' : num.toLocaleString()
}

// "Hon. John Kaguchia (UDA)" -> "UDA"
const partyFromName = (name) => {
  const m = /\(([^)]+)\)\s*$/.exec(name ?? '')
  return m ? m[1] : null
}

const stripParty = (name) => (name ? String(name).replace(/\s*\([^)]*\)\s*$/, '') : name)

const scoreTone = (score) => (score >= 70 ? 'good' : score >= 55 ? 'watch' : 'risk')

// ---------------------------------------------------------------------------
// Normalizers: turn whatever the API returns into one predictable row shape
// ---------------------------------------------------------------------------
const normalizeGovernor = (g, i) => ({
  _key: g?.id ?? g?._id ?? g?.slug ?? `gov-${i}`,
  name: g?.name ?? g?.governor ?? g?.governor_name ?? '—',
  position: 'Governor',
  party: g?.party ?? partyFromName(g?.governor) ?? '—',
  place: g?.county ?? '—',
  score: g?.accountabilityScore ?? g?.accountability_score ?? g?.score ?? null,
})

const normalizeConstituency = (c, i) => {
  const rawMp = c?.mp ?? c?.mp_name
  return {
    _key: c?.slug ?? c?.constituency_slug ?? c?.id ?? c?._id ?? `const-${i}`,
    name: c?.name ?? c?.constituency ?? '—',
    mp: stripParty(rawMp) ?? '—',
    party: c?.party ?? partyFromName(rawMp) ?? '—',
    county: c?.county ?? 'Nyeri',
    auditStatus: c?.auditStatus ?? c?.audit_status ?? 'Qualified',
    score: c?.accountabilityScore ?? c?.accountability_score ?? c?.score ?? null,
  }
}

const normalizeFinancial = (r, i) => ({
  _key: r?.id ?? r?._id ?? `fin-${i}`,
  fy: clean(r?.fy ?? r?.fy_display ?? r?.financial_year ?? r?.financialYear) ?? 'Unknown',
  budget: r?.budget ?? r?.amountKshb ?? r?.budget_kshb ?? null,
  expenditure: r?.expenditure ?? r?.exp ?? r?.expenditure_kshb ?? null,
})

const normalizeAudit = (r, i) => ({
  _key: r?.id ?? r?._id ?? `audit-${i}`,
  entity: clean(r?.entity ?? r?.constituency ?? r?.governor ?? r?.county) ?? 'Unknown',
  category: clean(r?.category ?? r?.finding_type) ?? 'Unknown',
  fy: clean(r?.fy_display ?? r?.financial_year ?? r?.financialYear) ?? 'Unknown',
  amount: r?.amount_flagged_kshm ?? r?.amountKshm ?? r?.amount ?? null,
  severity: clean(r?.severity ?? r?.finding_type) ?? '—',
})

const normalizeDepartment = (r, i) => ({
  _key: r?.id ?? r?._id ?? `dept-${i}-${r?.department ?? ''}`,
  department: clean(r?.department) ?? 'Unknown',
  fy: clean(r?.financialYear ?? r?.financial_year ?? r?.fy) ?? 'Unknown',
  budget: r?.approvedBudgetKshm ?? r?.budgetKshm ?? r?.budget_kshm ?? null,
  absorption: r?.absorptionRate ?? r?.absorption_rate ?? null,
  status: clean(r?.status) ?? '—',
})

// Allocations arrive either flat (one row per constituency per FY) or already
// wide (one row per FY). Normalize both into { fy, values: { [constituency]: amount } }.
const META_KEYS = new Set(['_id', 'id', 'fy', 'fy_key', 'fy_display', 'financial_year', 'financialYear'])

const normalizeAllocations = (rows) => {
  const isFlat = rows.some(
    (r) => (r?.constituency ?? r?.constituency_name) != null && (r?.amount_kshm ?? r?.amountKshm) != null
  )

  if (isFlat) {
    const byFy = new Map()
    rows.forEach((r) => {
      const fy = clean(r?.fy_display ?? r?.fy ?? r?.financial_year ?? r?.fy_key) ?? 'Unknown'
      const name = clean(r?.constituency ?? r?.constituency_name) ?? 'Unknown'
      const amount = r?.amount_kshm ?? r?.amountKshm
      if (!byFy.has(fy)) byFy.set(fy, { _key: fy, fy, values: {} })
      byFy.get(fy).values[name] = amount
    })
    return [...byFy.values()].sort((a, b) => String(b.fy).localeCompare(String(a.fy)))
  }

  return rows.map((r, i) => ({
    _key: r?.id ?? r?._id ?? r?.fy ?? `alloc-${i}`,
    fy: clean(r?.fy ?? r?.fy_display ?? r?.financial_year) ?? 'Unknown',
    values: Object.fromEntries(Object.entries(r ?? {}).filter(([k]) => !META_KEYS.has(k))),
  }))
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
// Keying by entity remounts the inner component when the tab changes, so rows
// fetched for one entity are never rendered with another entity's renderer.
export default function AdminDataManagement({ entity }) {
  return <AdminDataManagementInner key={entity} entity={entity} />
}

function AdminDataManagementInner({ entity }) {
  const config = configs[entity]
  const title = config?.title ?? 'Data'
  const lowerTitle = title.toLowerCase()

  const [data, setData] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  const retry = useCallback(() => setReloadKey((k) => k + 1), [])

  // Fetch
  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    const load = async () => {
      setQ('')
      setWarning(null)

      if (!config) {
        setData([])
        setError('Invalid entity type')
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      const token = localStorage.getItem('authToken')
      // Only send Authorization when we have a token. Skipping Content-Type on
      // GETs also avoids unnecessary CORS preflights.
      const headers = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      const getJson = async (path) => {
        const res = await fetch(`${APIService.baseURL}${path}`, { headers, signal: controller.signal })
        if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`)
        return unwrap(await res.json())
      }

      try {
        let rows = []

        if (entity === 'leaders') {
          const [govResult, constResult] = await Promise.allSettled([
            getJson('/governor/'),
            getJson('/constituency/'),
          ])

          if (govResult.status === 'rejected' && constResult.status === 'rejected') {
            throw govResult.reason
          }

          const failed = []

          let governors = []
          if (govResult.status === 'fulfilled') {
            const v = govResult.value
            governors = toArray(v, 'governors', 'governor')
            // A single-governor endpoint may return one object instead of a list
            if (governors.length === 0 && v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length) {
              governors = [v]
            }
          } else {
            failed.push('governor')
          }

          let constituencies = []
          if (constResult.status === 'fulfilled') {
            constituencies = toArray(constResult.value, 'constituencies')
          } else {
            failed.push('constituencies')
          }

          if (failed.length) setWarning(`Could not load: ${failed.join(', ')}.`)

          rows = [
            ...governors.map(normalizeGovernor),
            ...constituencies.map((c, i) => {
              const n = normalizeConstituency(c, i)
              return {
                _key: `mp-${n._key}`,
                name: n.mp,
                position: 'MP',
                party: n.party,
                place: n.name,
                score: n.score,
              }
            }),
          ]
        } else {
          const raw = await getJson(endpoints[entity])

          switch (entity) {
            case 'constituencies':
              rows = toArray(raw, 'constituencies').map(normalizeConstituency)
              break
            case 'financial':
              rows = toArray(raw, 'finances', 'financial_data', 'years').map(normalizeFinancial)
              break
            case 'allocations':
              rows = normalizeAllocations(toArray(raw, 'allocations'))
              break
            case 'audit':
              rows = toArray(raw, 'audit_findings', 'findings').map(normalizeAudit)
              break
            case 'departments':
              rows = toArray(raw, 'departments').map(normalizeDepartment)
              break
            default:
              throw new Error('Unknown entity type')
          }
        }

        if (!cancelled) setData(rows)
      } catch (err) {
        if (cancelled || err?.name === 'AbortError') return
        console.error(`Error fetching ${entity} data:`, err)
        setError(`Failed to load ${lowerTitle}: ${err.message}`)
        setData([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [entity, config, lowerTitle, reloadKey])

  // All hooks must run before any early return, so these live up here.
  const filtered = useMemo(() => {
    if (!q) return data
    const needle = q.toLowerCase()
    return data.filter((r) => JSON.stringify(r).toLowerCase().includes(needle))
  }, [data, q])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 8)

  // Constituency columns for the allocations table come from the data itself.
  const allocationCols = useMemo(() => {
    if (entity !== 'allocations') return []
    const names = new Set()
    data.forEach((r) => Object.keys(r.values ?? {}).forEach((n) => names.add(n)))
    return [...names].sort()
  }, [entity, data])

  const header = (
    <div className="flex items-center justify-between mb-1">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <Button size="sm">
        <Plus size={15} /> Add record
      </Button>
    </div>
  )

  if (loading) {
    return (
      <div>
        {header}
        <p className="text-ink-muted mb-6">Loading {lowerTitle}...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        {header}
        <p className="text-ink-danger mb-6">{error}</p>
        <button onClick={retry} className="btn btn-outline">
          Try again
        </button>
      </div>
    )
  }

  return (
    <div>
      {header}
      <p className="text-ink-muted mb-6">Search, review and manage {lowerTitle} records.</p>

      {warning && (
        <div className="mb-4 rounded border border-line bg-gold-50 px-4 py-3 text-sm text-ink">{warning}</div>
      )}

      <div className="mb-4 max-w-sm">
        <SearchBar value={q} onChange={setQ} placeholder={`Search ${lowerTitle}`} />
      </div>

      {filtered.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm text-ink-muted">
            {data.length === 0 ? `No ${lowerTitle} data available.` : `No ${lowerTitle} match "${q}".`}
          </p>
        </Card>
      ) : (
        <>
          <Card className="p-2">
            <Table
              columns={getColumnsForEntity(entity, allocationCols)}
              rows={pageItems}
              keyField="_key"
              renderRow={(row) => (
                <>
                  {renderCells(entity, row, allocationCols)}
                  <td className="py-3 pr-2 pl-4">
                    <div className="flex gap-1">
                      <IconBtn icon={Eye} label="View" />
                      <IconBtn icon={Pencil} label="Edit" />
                      <IconBtn icon={Trash2} label="Delete" danger />
                    </div>
                  </td>
                </>
              )}
            />
          </Card>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Entity-specific table config
// ---------------------------------------------------------------------------
function getColumnsForEntity(entity, allocationCols) {
  switch (entity) {
    case 'leaders':
      return ['Name', 'Position', 'Party', 'Place', 'Score', 'Actions']
    case 'constituencies':
      return ['Name', 'MP', 'County', 'Audit status', 'Score', 'Actions']
    case 'financial':
      return ['Financial Year', 'Budget (KShB)', 'Expenditure (KShB)', 'Actions']
    case 'allocations':
      return ['Financial Year', ...allocationCols.map((c) => `${c} (KShM)`), 'Actions']
    case 'audit':
      return ['Entity', 'Category', 'FY', 'Amount (KShM)', 'Severity', 'Actions']
    case 'departments':
      return ['Department', 'FY', 'Budget (KShM)', 'Absorption', 'Status', 'Actions']
    default:
      return ['Actions']
  }
}

function ScoreBadge({ score }) {
  if (score == null || Number.isNaN(Number(score))) {
    return <span className="text-ink-muted">—</span>
  }
  return <Badge tone={scoreTone(Number(score))}>{score}</Badge>
}

function renderCells(entity, row, allocationCols) {
  switch (entity) {
    case 'leaders':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.position}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.party}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.place}</td>
          <td className="py-3 pr-4">
            <ScoreBadge score={row.score} />
          </td>
        </>
      )
    case 'constituencies':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.mp}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.county}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.auditStatus}</td>
          <td className="py-3 pr-4">
            <ScoreBadge score={row.score} />
          </td>
        </>
      )
    case 'financial':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.budget)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.expenditure)}</td>
        </>
      )
    case 'allocations':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy}</td>
          {allocationCols.map((name) => (
            <td key={name} className="py-3 pr-4 text-ink-muted">
              {fmtNum(row.values?.[name])}
            </td>
          ))}
        </>
      )
    case 'audit': {
      const sev = String(row.severity ?? '').toLowerCase()
      const tone = sev.includes('high') || sev.includes('misappropriation') ? 'risk' : 'watch'
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.entity}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.category}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.amount)}</td>
          <td className="py-3 pr-4">
            <Badge tone={tone}>{row.severity}</Badge>
          </td>
        </>
      )
    }
    case 'departments':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.department}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.budget)}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.absorption == null ? '—' : `${row.absorption}%`}</td>
          <td className="py-3 pr-4">
            <Badge tone={row.status === 'On Track' ? 'good' : row.status === 'Behind' ? 'watch' : 'risk'}>
              {row.status}
            </Badge>
          </td>
        </>
      )
    default:
      return <td colSpan={5}>No data rendering available</td>
  }
}

function IconBtn({ icon: Icon, label, danger }) {
  return (
    <button
      type="button"
      title={label}
      className={`p-1.5 rounded hover:bg-ink/5 ${danger ? 'text-clay-500' : 'text-ink-muted'}`}
    >
      <Icon size={14} />
    </button>
  )
}
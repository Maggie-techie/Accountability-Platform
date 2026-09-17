import { useMemo, useState } from 'react'
import { Pencil, Trash2, Eye, Plus } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { SearchBar } from '../../components/Filters'
import { Table, Pagination, usePagination } from '../../components/DataDisplay'
import { constituencies, auditFindings, departments, allocationTrend, governor } from '../../data/mockData'

const configs = {
  leaders: {
    title: 'Leaders',
    columns: ['Name', 'Position', 'Party', 'Place', 'Score'],
    rows: [
      { id: governor.id, name: governor.name, position: 'Governor', party: governor.party, place: 'Nyeri County', score: governor.accountabilityScore },
      ...constituencies.map((c) => ({ id: c.slug, name: c.mp, position: 'MP', party: c.party, place: c.name, score: c.accountabilityScore })),
    ],
    renderRow: (r) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{r.name}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.position}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.party}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.place}</td>
        <td className="py-3 pr-4"><Badge tone={r.score >= 70 ? 'good' : r.score >= 55 ? 'watch' : 'risk'}>{r.score}</Badge></td>
      </>
    ),
  },
  constituencies: {
    title: 'Constituencies',
    columns: ['Name', 'MP', 'County', 'Audit status', 'Score'],
    rows: constituencies,
    keyField: 'slug',
    renderRow: (c) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{c.name}</td>
        <td className="py-3 pr-4 text-ink-muted">{c.mp}</td>
        <td className="py-3 pr-4 text-ink-muted">Nyeri</td>
        <td className="py-3 pr-4 text-ink-muted">{c.auditStatus}</td>
        <td className="py-3 pr-4"><Badge tone={c.accountabilityScore >= 70 ? 'good' : c.accountabilityScore >= 55 ? 'watch' : 'risk'}>{c.accountabilityScore}</Badge></td>
      </>
    ),
  },
  financial: {
    title: 'County Finances',
    columns: ['Financial Year', 'Budget (KShB)', 'Expenditure (KShB)'],
    rows: [
      { id: '2022/23', fy: '2022/23', budget: 7.1, exp: 6.4 },
      { id: '2023/24', fy: '2023/24', budget: 7.4, exp: 6.9 },
      { id: '2024/25', fy: '2024/25', budget: 7.8, exp: 7.2 },
      { id: '2025/26', fy: '2025/26', budget: 8.0, exp: 3.6 },
    ],
    renderRow: (r) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{r.fy}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.budget}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.exp}</td>
      </>
    ),
  },
  allocations: {
    title: 'NG-CDF Allocations',
    columns: ['Financial Year', 'Kieni', 'Mathira', 'Othaya', 'Tetu'],
    rows: allocationTrend.map((r, i) => ({ id: i, ...r })),
    renderRow: (r) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{r.fy}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.Kieni}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.Mathira}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.Othaya}</td>
        <td className="py-3 pr-4 text-ink-muted">{r.Tetu}</td>
      </>
    ),
  },
  audit: {
    title: 'Audit Findings',
    columns: ['Entity', 'Category', 'FY', 'Amount (KShM)', 'Severity'],
    rows: auditFindings,
    renderRow: (f) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{f.entity}</td>
        <td className="py-3 pr-4 text-ink-muted">{f.category}</td>
        <td className="py-3 pr-4 text-ink-muted">{f.financialYear}</td>
        <td className="py-3 pr-4 text-ink-muted">{f.amountKshm}</td>
        <td className="py-3 pr-4"><Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge></td>
      </>
    ),
  },
  departments: {
    title: 'Departmental Data',
    columns: ['Department', 'FY', 'Budget (KShM)', 'Absorption', 'Status'],
    rows: departments,
    keyField: 'department',
    renderRow: (d) => (
      <>
        <td className="py-3 pr-4 font-medium text-ink">{d.department}</td>
        <td className="py-3 pr-4 text-ink-muted">{d.financialYear}</td>
        <td className="py-3 pr-4 text-ink-muted">{d.approvedBudgetKshm}</td>
        <td className="py-3 pr-4 text-ink-muted">{d.absorptionRate}%</td>
        <td className="py-3 pr-4"><Badge tone={d.status === 'On Track' ? 'good' : d.status === 'Behind' ? 'watch' : 'risk'}>{d.status}</Badge></td>
      </>
    ),
  },
}

export default function AdminDataManagement({ entity }) {
  const config = configs[entity]
  const [q, setQ] = useState('')
  const filtered = useMemo(() => {
    if (!q) return config.rows
    return config.rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q.toLowerCase()))
  }, [q, config.rows])
  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 8)

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-semibold">{config.title}</h1>
        <Button size="sm"><Plus size={15} /> Add record</Button>
      </div>
      <p className="text-ink-muted mb-6">Search, review and manage {config.title.toLowerCase()} records.</p>

      <div className="mb-4 max-w-sm"><SearchBar value={q} onChange={setQ} placeholder={`Search ${config.title.toLowerCase()}`} /></div>

      <Card className="p-2">
        <Table
          columns={[...config.columns, 'Actions']}
          rows={pageItems}
          keyField={config.keyField || 'id'}
          renderRow={(row) => (
            <>
              {config.renderRow(row)}
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
    </div>
  )
}

function IconBtn({ icon: Icon, label, danger }) {
  return (
    <button
      title={label}
      className={`p-1.5 rounded hover:bg-ink/5 ${danger ? 'text-clay-500' : 'text-ink-muted'}`}
    >
      <Icon size={14} />
    </button>
  )
}

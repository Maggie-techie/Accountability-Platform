import { useMemo, useState } from 'react'
import { FileText, Download, Eye } from 'lucide-react'
import { Card, Button, EmptyState } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'
import { reports } from '../data/mockData'

const categories = [...new Set(reports.map((r) => r.category))]

export default function Reports() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [fy, setFy] = useState('')

  const filtered = useMemo(() => reports.filter((r) =>
    (!q || r.title.toLowerCase().includes(q.toLowerCase())) &&
    (!category || r.category === category) &&
    (!fy || r.financialYear === fy)
  ), [q, category, fy])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 6)

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Reports' }]} />
      <h1 className="text-3xl font-semibold mb-1">Report library</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Accountability, budget, NG-CDF and audit reports, ready to view or download.</p>

      <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search reports" /></div>
      <FilterBar>
        <Select label="Report type" value={category} onChange={setCategory} options={categories} />
        <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(reports.map((r) => r.financialYear))]} />
      </FilterBar>

      {filtered.length === 0 ? (
        <EmptyState title="No reports match your search" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            {pageItems.map((r) => (
              <Card key={r.id} className="p-5 flex gap-4">
                <div className="h-11 w-11 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0">
                  <FileText size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink leading-snug">{r.title}</p>
                  <p className="text-xs text-ink-faint mt-1">{r.category} &middot; {r.entity} &middot; FY {r.financialYear}</p>
                  <p className="text-xs text-ink-faint">Published {r.datePublished}</p>
                  <div className="flex gap-3 mt-3">
                    <Button size="sm" variant="ghost"><Eye size={14} /> View</Button>
                    <Button size="sm" variant="secondary"><Download size={14} /> Download PDF</Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

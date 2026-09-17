import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, Badge, Button } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'
import { EmptyState } from '../components/ui'
import { governor, constituencies, scoreCategory } from '../data/mockData'

const allLeaders = [
  { id: governor.id, name: governor.name, position: 'Governor', party: governor.party, place: 'Nyeri County', score: governor.accountabilityScore, summary: governor.summary },
  ...constituencies.map((c) => ({
    id: c.slug, name: c.mp, position: 'Member of Parliament', party: c.party, place: c.name,
    score: c.accountabilityScore, summary: `Oversees NG-CDF allocation of KSh ${c.totalAllocationKshm.toFixed(1)}M for ${c.name}.`,
  })),
]

export default function Leaders() {
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const [position, setPosition] = useState('')
  const [place, setPlace] = useState('')

  const filtered = useMemo(() => {
    return allLeaders.filter((l) =>
      (!q || l.name.toLowerCase().includes(q.toLowerCase()) || l.place.toLowerCase().includes(q.toLowerCase())) &&
      (!position || l.position === position) &&
      (!place || l.place === place)
    )
  }, [q, position, place])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 9)

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Leaders' }]} />
      <h1 className="text-3xl font-semibold mb-2">Leaders directory</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Browse every elected leader covered by the platform, with an at-a-glance accountability score.</p>

      <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search by name or place" /></div>

      <FilterBar>
        <Select label="Position" value={position} onChange={setPosition} options={['Governor', 'Member of Parliament']} />
        <Select label="Constituency / County" value={place} onChange={setPlace} options={['Nyeri County', ...constituencies.map((c) => c.name)]} />
      </FilterBar>

      {filtered.length === 0 ? (
        <EmptyState title="No leaders match your search" description="Try a different name, or clear your filters." />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {pageItems.map((l) => {
              const { tone } = scoreCategory(l.score)
              return (
                <Card key={l.id} className="p-4 flex flex-col">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="h-12 w-12 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif font-semibold shrink-0">
                      {l.name.split(' ').slice(-1)[0][0]}
                    </div>
                    <div className="min-w-0">
                      <p className="font-serif font-semibold text-ink truncate">{l.name}</p>
                      <p className="text-xs text-ink-muted">{l.position} &middot; {l.party}</p>
                      <p className="text-xs text-ink-faint">{l.place}</p>
                    </div>
                  </div>
                  <p className="text-sm text-ink-muted flex-1">{l.summary}</p>
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-line">
                    <Badge tone={tone}>Score {l.score}</Badge>
                    <Link to={`/leaders/${l.id}`}>
                      <Button size="sm" variant="secondary">View Profile</Button>
                    </Link>
                  </div>
                </Card>
              )
            })}
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

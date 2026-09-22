import { useMemo, useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, Badge, Button } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'
import { EmptyState } from '../components/ui'
import { scoreCategory } from '../data/mockData'
import APIService from '../services/api'

export default function Leaders() {
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const [position, setPosition] = useState('')
  const [place, setPlace] = useState('')

  // State for data fetching
  const [governorData, setGovernorData] = useState(null)
  const [constituenciesData, setConstituenciesData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Fetch governor data and constituencies data in parallel
        const [governorResponse, constituenciesResponse] = await Promise.all([
          APIService.getGovernorProfile(),
          APIService.getAllConstituencies()
        ])

        setGovernorData(governorResponse)
        setConstituenciesData(constituenciesResponse.constituencies || constituenciesResponse)
        setError(null)
      } catch (err) {
        setError(err.message || 'Failed to load leaders data')
        setGovernorData(null)
        setConstituenciesData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])
  
  // Create allLeaders array from fetched data (similar to original logic)
  const allLeaders = useMemo(() => {
    const leaders = []

    // Add governor if data exists
    if (governorData) {
      leaders.push({
        id: governorData._id || governorData.id,
        name: governorData.name,
        position: 'Governor',
        party: governorData.party,
        place: governorData.county,
        score: governorData.accountabilityScore,
        summary: governorData.summary
      })
    }

    // Add MPs from constituencies data
    constituenciesData.forEach((c) => {
      const allocation = c.allocations_ksm || {}
      const totalAllocation = Object.values(allocation).reduce((sum, val) => sum + (val || 0), 0)

      leaders.push({
        id: c.slug,
        name: c.mp?.name,
        position: 'Member of Parliament',
        party: c.mp?.party,
        place: c.name,
        score: c.accountabilityScore,
        summary: `Oversees NG-CDF allocation of KSh ${totalAllocation.toFixed(1)}M for ${c.name}.`,
      })
    })

    return leaders
  }, [governorData, constituenciesData])
  
  const filtered = useMemo(() => {
    return allLeaders.filter((l) =>
      (!q || l.name.toLowerCase().includes(q.toLowerCase()) || l.place.toLowerCase().includes(q.toLowerCase())) &&
      (!position || l.position === position) &&
      (!place || l.place === place)
    )
  }, [q, position, place, allLeaders])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 9)

  // Handle case where data is still loading or there was an error
  if (loading) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Leaders' }]} />
        <h1 className="text-3xl font-semibold mb-2">Leaders directory</h1>
        <p className="text-ink-muted mb-6 max-w-2xl">Loading leaders...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
        <Breadcrumbs items={[{ label: 'Leaders' }]} />
        <h1 className="text-3xl font-semibold mb-2">Leaders directory</h1>
        <p className="text-ink-danger mb-6">{error}</p>
        <button onClick={() => window.location.reload()} className="btn btn-outline">
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Leaders' }]} />
      <h1 className="text-3xl font-semibold mb-2">Leaders directory</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Browse every elected leader covered by the platform, with an at-a-glance accountability score.</p>

      <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search by name or place" /></div>

      <FilterBar>
        <Select label="Position" value={position} onChange={setPosition} options={['Governor', 'Member of Parliament']} />
        <Select label="Constituency / County" value={place} onChange={setPlace} options={['Nyeri County', ...constituenciesData.map((c) => c.name)]} />
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
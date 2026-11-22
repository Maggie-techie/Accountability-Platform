import { useState, useEffect} from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Database, Cpu, MessageSquareText, ScrollText, ShieldCheck, AlertCircle } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { SearchBar } from '../components/Filters'
import { AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'
import { LEADER_PHOTOS } from '../utils/leaderPhotos'
import { useAsyncData, Skeleton, AsyncContent } from '../hooks/useAsyncData'


export default function Home() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [searchError, setSearchError] = useState(null)
  const [isSearching, setIsSearching] = useState(false)

  // Fetch data independently - each renders as it arrives
  const { data: governor, isLoading: govLoading, error: govError, refresh: refreshGov } = useAsyncData(
    'governor-profile',
    () => APIService.getGovernorProfile(),
    { cacheTime: 10 * 60 * 1000 }
  )

  const { data: constituenciesData, isLoading: constLoading, refresh: refreshConst } = useAsyncData(
    'all-constituencies',
    () => APIService.getAllConstituencies(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const constituencies = constituenciesData?.constituencies || constituenciesData || []

  const { data: auditResponse, isLoading: auditLoading } = useAsyncData(
    'county-audit-findings',
    () => APIService.getCountyAuditFindings(),
    { cacheTime: 5 * 60 * 1000 }
  )
  const auditFindings = auditResponse?.audit_findings || auditResponse || []

  const { data: countyFinances, isLoading: financeLoading } = useAsyncData(
    'county-finances',
    () => APIService.getCountyFinances(),
    { cacheTime: 10 * 60 * 1000 }
  )

  const anyLoading = govLoading || constLoading || auditLoading || financeLoading
  const anyError = govError

  // Search handler - checks for constituency first, then falls back to leader search
  const handleSearch = async (e) => {
    e.preventDefault()
    const query = q.trim()
    if (!query) return

    setIsSearching(true)
    setSearchError(null)

    try {
      // First, check if query matches a constituency (by name or slug, case-insensitive)
      const matchedConstituency = constituencies.find((c) =>
        c.name.toLowerCase() === query.toLowerCase() ||
        c.slug.toLowerCase() === query.toLowerCase() ||
        c.name.toLowerCase().includes(query.toLowerCase()) ||
        query.toLowerCase().includes(c.name.toLowerCase())
      )

      if (matchedConstituency) {
        // Redirect to constituency profile page
        navigate(`/constituencies/${matchedConstituency.slug}`)
      } else {
        // No constituency match - search leaders
        navigate(`/leaders?q=${encodeURIComponent(query)}`)
      }
    } catch (err) {
      console.error('Search error:', err)
      setSearchError('Search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }
  
  // Handle both old format (rows with revenue_source) and new pivoted format
  const latestFy = (Array.isArray(countyFinances) && countyFinances.length)
    ? [...new Set(countyFinances.map((f) => f.financial_year))].sort().slice(-1)[0]
    : null

  // Get revenue sources for the latest FY - works with both formats
  const revenueSources = (Array.isArray(countyFinances) && latestFy)
    ? (() => {
        const fyData = countyFinances.find((f) => f.financial_year === latestFy)
        if (!fyData) return []

        // New pivoted format: check for individual revenue fields
        const sources = []
        if (fyData.equitable_share_kshb) sources.push({ revenue_source: 'Equitable Share', amount_kshb: fyData.equitable_share_kshb, _id: 'equitable' })
        if (fyData.conditional_grants_kshb) sources.push({ revenue_source: 'Conditional Grants', amount_kshb: fyData.conditional_grants_kshb, _id: 'conditional' })
        if (fyData.osr_kshb) sources.push({ revenue_source: 'Own Source Revenue', amount_kshb: fyData.osr_kshb, _id: 'osr' })
        if (fyData.expenditure_kshb) sources.push({ revenue_source: 'Expenditure', amount_kshb: fyData.expenditure_kshb, _id: 'expenditure' })
        if (fyData.development_kshb) sources.push({ revenue_source: 'Development', amount_kshb: fyData.development_kshb, _id: 'development' })
        if (fyData.recurrent_kshb) sources.push({ revenue_source: 'Recurrent', amount_kshb: fyData.recurrent_kshb, _id: 'recurrent' })

        // Fallback to old format (rows with revenue_source)
        if (sources.length === 0 && fyData.revenue_source) {
          return countyFinances.filter((f) => f.financial_year === latestFy)
        }
        return sources
      })()
    : []

  return (
    <div>
      {/* Hero - renders immediately, no data dependency */}
      <section className="border-b border-line bg-white">
        <div className="max-w-content mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="max-w-2xl">
            <Badge tone="info">Nyeri County</Badge>
            <h1 className="mt-4 text-4xl sm:text-5xl leading-[1.1] font-semibold text-ink">
              Where does Nyeri's public money go?
            </h1>
            <p className="mt-5 text-lg text-ink-muted max-w-xl">
              We pull together county budgets, NG-CDF allocations and Auditor-General findings, then use
              AI to surface unusual patterns and explain them in plain language, so any resident can follow the money.
            </p>
            <form onSubmit={handleSearch} className="mt-8 max-w-lg">
              <SearchBar value={q} onChange={setQ} placeholder="Search a leader, constituency or governance topic" size="lg" disabled={isSearching} />
              {searchError && (
                <div className="mt-3 flex items-center gap-2 text-sm text-ink-danger" role="alert">
                  <AlertCircle size={16} />
                  <span>{searchError}</span>
                </div>
              )}
            </form>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button size="lg" onClick={() => navigate('/accountability')}>
                Explore Accountability <ArrowRight size={16} />
              </Button>
              <Button size="lg" variant="secondary" onClick={() => navigate('/assistant')}>
                Ask the AI Assistant
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Key stats - static "6" + dynamic audit findings count */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Constituencies covered" value="6" />
        <Stat label="FY2024/25 county budget" value="KSh 7.8B" />
        <AsyncContent
          isLoading={auditLoading}
          error={null}
          skeleton={<Stat label="Open audit findings" value={<Skeleton variant="kpi" />} />}
        >
          <Stat label="Open audit findings" value={String(auditFindings.length)} />
        </AsyncContent>
      </section>

      {/* Governor overview - waits for governor data */}
      <AsyncContent
        isLoading={govLoading}
        error={govError}
        onRetry={refreshGov}
        skeleton={
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <Skeleton variant="avatar" />
              <div className="space-y-2">
                <Skeleton variant="title" className="w-1/4" />
                <Skeleton variant="text" className="w-1/3" />
              </div>
            </div>
          </Card>
        }
      >
        {governor && (
          <section className="max-w-content mx-auto px-4 sm:px-6 py-6">
            <Card className="p-6 flex flex-col sm:flex-row sm:items-center gap-6 justify-between">
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif text-xl font-semibold shrink-0 relative overflow-hidden">
                  {(() => {
                    const photo = LEADER_PHOTOS.governor;
                    if (photo) {
                      return (
                        <img
                          src={photo}
                          alt={`${governor.name} photo`}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            e.currentTarget.onerror = null;
                            e.currentTarget.src = '';
                            e.currentTarget.alt = '';
                          }}
                        />
                      );
                    }
                    // Fallback to initials
                    return governor.name.split(' ').slice(-1)[0][0];
                  })()}
                </div>
                <div>
                  <p className="text-xs text-ink-faint uppercase tracking-wide">County Governor</p>
                  <p className="font-serif text-lg font-semibold text-ink">{governor.name}</p>
                  <p className="text-sm text-ink-muted">{governor.party} &middot; {governor.tenure}</p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <p className="text-2xl font-serif font-semibold text-forest-700">{governor.accountabilityScore}</p>
                  <p className="text-xs text-ink-muted">Accountability score</p>
                </div>
                <Button variant="secondary" onClick={() => navigate(`/leaders/${governor.id || governor._id}`)}>View profile</Button>
              </div>
            </Card>
          </section>
        )}
      </AsyncContent>

      {/* Constituency cards - waits for constituencies data */}
      <AsyncContent
        isLoading={constLoading}
        error={null}
        onRetry={refreshConst}
        skeleton={
          <section className="max-w-content mx-auto px-4 sm:px-6 py-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold">The six constituencies</h2>
              <Link to="/constituencies" className="text-sm text-forest-700 hover:underline">View all &rarr;</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1,2,3,4,5,6].map(i => (
                <Card key={i} className="p-4 h-full">
                  <div className="flex items-center justify-between mb-2">
                    <Skeleton variant="title" className="w-1/2" />
                    <Skeleton variant="badge" />
                  </div>
                  <Skeleton variant="text" className="w-1/3" />
                  <Skeleton variant="text" className="w-1/2" />
                </Card>
              ))}
            </div>
          </section>
        }
      >
        {constituencies.length > 0 && (
          <section className="max-w-content mx-auto px-4 sm:px-6 py-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold">The six constituencies</h2>
              <Link to="/constituencies" className="text-sm text-forest-700 hover:underline">View all &rarr;</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {constituencies.map((c) => {
                const totalAllocation = Object.values(c.allocations_ksm || {}).reduce((sum, v) => sum + (v || 0), 0)
                return(
                <Link key={c.slug} to={`/constituencies/${c.slug}`}>
                  <Card className="p-4 h-full hover:border-forest-300 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-serif font-semibold text-ink">{c.name}</p>
                      <Badge tone={c.audit_status === 'Unqualified' ? 'good' : c.audit_status === 'Qualified' ? 'watch' : 'risk'}>
                        {c.audit_status}
                      </Badge>
                    </div>
                    <p className="text-sm text-ink-muted">{c.mp?.name}</p>
                    <p className="text-xs text-ink-faint mt-2">Total NG-CDF allocation (all years): {totalAllocation.toFixed(1)}M</p>
                  </Card>
                </Link>
              )
              })}
            </div>
          </section>
        )}
      </AsyncContent>

      {/* Financial snapshot + recent findings - wait for finances & audit data */}
      <AsyncContent
        isLoading={financeLoading || auditLoading}
        error={null}
        skeleton={
          <section className="max-w-content mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">County financial snapshot, FY2024/25</h3>
              <dl className="space-y-3">
                {[1,2,3].map(i => (
                  <div key={i} className="flex justify-between text-sm border-b border-line pb-2 last:border-0">
                    <dt className="text-ink-muted"><Skeleton variant="text" className="w-24" /></dt>
                    <dd className="font-medium text-ink"><Skeleton variant="text" className="w-20" /></dd>
                  </div>
                ))}
              </dl>
            </Card>
            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Recent Auditor-General findings</h3>
              <ul className="space-y-3">
                {[1,2,3].map(i => (
                  <li key={i} className="text-sm border-b border-line pb-3 last:border-0">
                    <div className="flex justify-between gap-2">
                      <span className="font-medium text-ink"><Skeleton variant="text" className="w-32" /></span>
                      <Skeleton variant="badge" />
                    </div>
                    <Skeleton variant="text" className="w-1/2" />
                  </li>
                ))}
              </ul>
            </Card>
          </section>
        }
      >
        {countyFinances && (
          <section className="max-w-content mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">County financial snapshot, FY2024/25</h3>
              <dl className="space-y-3">
                {revenueSources.map((r) => (
                  <div key={r._id} className="flex justify-between text-sm border-b border-line pb-2 last:border-0">
                    <dt className="text-ink-muted">{r.revenue_source}</dt>
                    <dd className="font-medium text-ink">KSh {r.amount_kshb}B</dd>
                  </div>
                ))}
              </dl>
              <Link to="/county" className="inline-block mt-4 text-sm text-forest-700 hover:underline">
                Full county dashboard &rarr;
              </Link>
            </Card>

            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Recent Auditor-General findings</h3>
              <ul className="space-y-3">
                {auditFindings.slice(0, 3).map((f) => (
                  <li key={f._id} className="text-sm border-b border-line pb-3 last:border-0">
                    <div className="flex justify-between gap-2">
                      <span className="font-medium text-ink">{f.entity}</span>
                      <Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge>
                    </div>
                    <p className="text-ink-muted mt-1">{f.finding}</p>
                  </li>
                ))}
              </ul>
              <Link to="/anomalies" className="inline-block mt-4 text-sm text-forest-700 hover:underline">
                See detected anomalies &rarr;
              </Link>
            </Card>
          </section>
        )}
      </AsyncContent>

      {/* How it works */}
      <section className="bg-white border-y border-line">
        <div className="max-w-content mx-auto px-4 sm:px-6 py-14">
          <h2 className="text-2xl font-semibold mb-8">How it works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <HowStep icon={Database} step="1" title="Data" text="Budgets, NG-CDF allocations and audit reports are pulled from public sources into one place." />
            <HowStep icon={Cpu} step="2" title="Analysis" text="AI models trained on governance data look for spending patterns that fall outside the expected range." />
            <HowStep icon={MessageSquareText} step="3" title="AI Explanation" text="Every flagged pattern comes with a plain-language explanation of exactly why it was flagged." />
            <HowStep icon={ScrollText} step="4" title="Accountability" text="Residents, journalists and oversight bodies get evidence-backed starting points to investigate further." />
          </div>
        </div>
      </section>

      {/* Trust / disclaimer */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-12 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck size={18} className="text-forest-600" />
            <h3 className="font-serif font-semibold text-lg">Where the data comes from</h3>
          </div>
          <p className="text-sm text-ink-muted">
            All source records are drawn from publicly published documents: Office of the Auditor-General reports,
            National Treasury / NG-CDF Board disbursement records, and Nyeri County fiscal reports. Every figure
            on this platform links back to its original document.
          </p>
        </Card>
        <AIDisclaimer />
      </section>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="border-l-2 border-forest-700 pl-3">
      <p className="text-2xl font-serif font-semibold text-ink">{value}</p>
      <p className="text-xs text-ink-muted mt-0.5">{label}</p>
    </div>
  )
}

function HowStep({ icon: Icon, step, title, text }) {
  return (
    <div>
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-forest-700 text-white mb-3">
        <Icon size={18} />
      </div>
      <p className="text-xs text-ink-faint mb-1">Step {step}</p>
      <p className="font-semibold text-ink mb-1">{title}</p>
      <p className="text-sm text-ink-muted">{text}</p>
    </div>
  )
}

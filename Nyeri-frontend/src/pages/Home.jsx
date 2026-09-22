import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Search, Database, Cpu, MessageSquareText, ScrollText, ShieldCheck } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { SearchBar } from '../components/Filters'
import { AIDisclaimer } from '../components/Insights'
import { governor, constituencies, auditFindings, anomalies, countyFinances } from '../data/mockData'

export default function Home() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  return (
    <div>
      {/* Hero */}
      <section className="border-b border-line bg-white">
        <div className="max-w-content mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="max-w-2xl">
            <Badge tone="info">Nyeri County</Badge>
            <h1 className="mt-4 text-4xl sm:text-5xl leading-[1.1] font-semibold text-ink">
              Where does Nyeri's public money actually go?
            </h1>
            <p className="mt-5 text-lg text-ink-muted max-w-xl">
              We pull together county budgets, NG-CDF allocations and Auditor-General findings, then use
              AI to surface unusual patterns and explain them in plain language, so any resident can follow the money.
            </p>
            <form
              onSubmit={(e) => { e.preventDefault(); navigate(`/leaders?q=${encodeURIComponent(q)}`) }}
              className="mt-8 max-w-lg"
            >
              <SearchBar value={q} onChange={setQ} placeholder="Search a leader, constituency or governance topic" size="lg" />
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

      {/* Key stats */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Constituencies covered" value="6" />
        <Stat label="FY2024/25 county budget" value="KSh 7.8B" />
        <Stat label="Open audit findings" value={String(auditFindings.length)} />
        <Stat label="AI-flagged anomalies" value={String(anomalies.length)} />
      </section>

      {/* Governor overview */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-6">
        <Card className="p-6 flex flex-col sm:flex-row sm:items-center gap-6 justify-between">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif text-xl font-semibold shrink-0">
              MK
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
            <Button variant="secondary" onClick={() => navigate(`/leaders/${governor.id}`)}>View profile</Button>
          </div>
        </Card>
      </section>

      {/* Constituency cards */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold">The six constituencies</h2>
          <Link to="/constituencies" className="text-sm text-forest-700 hover:underline">View all &rarr;</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {constituencies.map((c) => (
            <Link key={c.slug} to={`/constituencies/${c.slug}`}>
              <Card className="p-4 h-full hover:border-forest-300 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-serif font-semibold text-ink">{c.name}</p>
                  <Badge tone={c.accountabilityScore >= 70 ? 'good' : c.accountabilityScore >= 55 ? 'watch' : 'risk'}>
                    {c.accountabilityScore}
                  </Badge>
                </div>
                <p className="text-sm text-ink-muted">{c.mp}</p>
                <p className="text-xs text-ink-faint mt-2">FY2024/25 allocation: KSh {c.totalAllocationKshm.toFixed(1)}M</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Financial snapshot + recent findings */}
      <section className="max-w-content mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">County financial snapshot, FY2024/25</h3>
          <dl className="space-y-3">
            {countyFinances.revenueSources.map((r) => (
              <div key={r.source} className="flex justify-between text-sm border-b border-line pb-2 last:border-0">
                <dt className="text-ink-muted">{r.source}</dt>
                <dd className="font-medium text-ink">KSh {r.amountKshb}B</dd>
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
              <li key={f.id} className="text-sm border-b border-line pb-3 last:border-0">
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

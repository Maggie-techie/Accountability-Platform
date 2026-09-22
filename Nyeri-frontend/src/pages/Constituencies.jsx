import { Link } from 'react-router-dom'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { constituencies, scoreCategory } from '../data/mockData'

export default function Constituencies() {
  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Constituencies' }]} />
      <h1 className="text-3xl font-semibold mb-1">The six constituencies of Nyeri</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">
        Kieni, Mathira, Othaya, Tetu, Mukurwe-ini and Nyeri Town each receive their own NG-CDF allocation, audited independently.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {constituencies.map((c) => {
          const { tone } = scoreCategory(c.accountabilityScore)
          return (
            <Link key={c.slug} to={`/constituencies/${c.slug}`}>
              <Card className="p-5 h-full hover:border-forest-300 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-serif font-semibold text-lg text-ink">{c.name}</h3>
                  <Badge tone={tone}>{c.accountabilityScore}</Badge>
                </div>
                <p className="text-sm text-ink-muted">{c.mp} &middot; {c.party}</p>
                <div className="mt-4 pt-3 border-t border-line grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-ink-faint text-xs">FY24/25 Allocation</p>
                    <p className="font-medium text-ink">KSh {c.totalAllocationKshm.toFixed(1)}M</p>
                  </div>
                  <div>
                    <p className="text-ink-faint text-xs">Audit opinion</p>
                    <p className="font-medium text-ink">{c.auditStatus}</p>
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

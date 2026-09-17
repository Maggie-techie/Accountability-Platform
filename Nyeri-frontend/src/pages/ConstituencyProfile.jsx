import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'
import { constituencies, allocationTrend, auditFindings, anomalies } from '../data/mockData'

export default function ConstituencyProfile() {
  const { slug } = useParams()
  const c = constituencies.find((x) => x.slug === slug)
  if (!c) return <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">Constituency not found.</div>

  const trend = allocationTrend.map((row) => ({ fy: row.fy, allocation: row[c.name] }))
  const findings = auditFindings.filter((f) => f.entity.toLowerCase().includes(c.name.toLowerCase()))
  const constAnomalies = anomalies.filter((a) => a.entity.toLowerCase().includes(c.name.toLowerCase()))

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Constituencies', to: '/constituencies' }, { label: c.name }]} />

      <Card className="p-6 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-semibold text-ink">{c.name} Constituency</h1>
          <p className="text-ink-muted">MP: <Link to={`/leaders/${c.slug}`} className="text-forest-700 hover:underline">{c.mp}</Link> &middot; {c.party}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-2xl font-serif font-semibold text-forest-700">{c.accountabilityScore}</p>
            <p className="text-xs text-ink-muted">Accountability score</p>
          </div>
          <Button variant="secondary"><FileDown size={16} /> Download report</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">NG-CDF allocation by year</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend}>
                  <CartesianGrid stroke="#E2E5E1" vertical={false} />
                  <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                  <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                  <Line type="monotone" dataKey="allocation" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Audit findings</h3>
            {findings.length === 0 ? (
              <p className="text-sm text-ink-muted">No findings recorded for {c.name} in the current dataset.</p>
            ) : (
              <ul className="space-y-3">
                {findings.map((f) => (
                  <li key={f.id} className="flex justify-between gap-3 text-sm border-b border-line pb-3 last:border-0">
                    <div>
                      <p className="font-medium text-ink">{f.category}</p>
                      <p className="text-ink-muted mt-0.5">{f.finding}</p>
                      <p className="text-xs text-ink-faint mt-1">FY {f.financialYear} &middot; KSh {f.amountKshm}M</p>
                    </div>
                    <Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-3">Development / project information</h3>
            <p className="text-sm text-ink-muted">
              NG-CDF-funded projects include bursary disbursement to needy students, classroom construction,
              and water infrastructure. Project-level completion tracking will expand as more source data is digitised.
            </p>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Detected anomalies</h3>
            {constAnomalies.length === 0 ? (
              <p className="text-sm text-ink-muted">No anomalies currently flagged.</p>
            ) : (
              <ul className="space-y-3">
                {constAnomalies.map((a) => (
                  <li key={a.id} className="text-sm border-b border-line pb-3 last:border-0">
                    <div className="flex justify-between gap-2">
                      <Link to={`/anomalies/${a.id}`} className="font-medium text-ink hover:text-forest-700">{a.title}</Link>
                    </div>
                    <Badge tone={a.severity === 'High' ? 'risk' : a.severity === 'Medium' ? 'watch' : 'good'} className="mt-1.5">{a.severity}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}

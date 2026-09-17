import { useParams, Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileDown, Eye } from 'lucide-react'
import { Card, Badge, SeverityBadge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { LimeChart, AIDisclaimer } from '../components/Insights'
import { anomalies, auditFindings } from '../data/mockData'

export default function AnomalyDetails() {
  const { id } = useParams()
  const anomaly = anomalies.find((a) => a.id === id)
  if (!anomaly) return <div className="max-w-content mx-auto px-6 py-16 text-center text-ink-muted">Anomaly not found.</div>

  const relatedFinding = auditFindings.find((f) => f.id === anomaly.relatedFindingId)
  const chartData = [
    { name: 'Expected', value: anomaly.expected },
    { name: 'Observed', value: anomaly.observed },
  ]

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Anomalies', to: '/anomalies' }, { label: anomaly.id }]} />

      <Card className="p-6 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div>
            <p className="text-xs text-ink-faint mb-1">{anomaly.id}</p>
            <h1 className="text-2xl font-serif font-semibold text-ink">{anomaly.title}</h1>
            <p className="text-ink-muted mt-1">{anomaly.entity} &middot; {anomaly.category} &middot; FY {anomaly.financialYear}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <SeverityBadge severity={anomaly.severity} />
            <Badge>{anomaly.status}</Badge>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary"><Eye size={16} /> View source data</Button>
          <Button><FileDown size={16} /> Generate report</Button>
        </div>
      </Card>

      <Alert className="mb-6" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Expected vs. observed</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                  <CartesianGrid stroke="#E2E5E1" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 13, fill: '#1C1F1D' }} axisLine={false} tickLine={false} width={80} />
                  <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} formatter={(v) => `${v} ${anomaly.unit}`} />
                  <Bar dataKey="value" fill="#8A928C" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-sm text-ink-muted mt-2">
              Expected: <span className="font-medium text-ink">{anomaly.expected} {anomaly.unit}</span> &middot;
              {' '}Observed: <span className="font-medium text-clay-500">{anomaly.observed} {anomaly.unit}</span>
            </p>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-3">AI-generated interpretation</h3>
            <p className="text-sm text-ink-muted">{anomaly.summary}</p>
          </Card>

          <Card className="p-6">
            <h3 className="font-serif font-semibold text-lg mb-4">LIME explanation</h3>
            <p className="text-sm text-ink-muted mb-4">
              These are the features that most influenced the AI model's classification of this pattern as anomalous.
            </p>
            <LimeChart features={anomaly.limeFeatures} />
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Related audit finding</h3>
            {relatedFinding ? (
              <div className="text-sm">
                <p className="font-medium text-ink">{relatedFinding.category}</p>
                <p className="text-ink-muted mt-1">{relatedFinding.finding}</p>
                <Badge tone={relatedFinding.severity === 'High' ? 'risk' : 'watch'} className="mt-2">{relatedFinding.severity}</Badge>
              </div>
            ) : (
              <p className="text-sm text-ink-muted">No linked Auditor-General finding yet. This anomaly was detected independently by the AI model.</p>
            )}
          </Card>
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Related profile</h3>
            <Link to={`/constituencies/${anomaly.entity.toLowerCase().split(' ')[0]}`} className="text-sm text-forest-700 hover:underline">
              View {anomaly.entity} profile &rarr;
            </Link>
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}

function Alert() {
  return (
    <div className="rounded-md border border-gold-100 bg-gold-50 p-4 text-sm text-ink-muted mb-2">
      <span className="font-semibold text-ink">An anomaly is an indicator of an unusual pattern</span> and does not
      by itself establish fraud, corruption or wrongdoing.
    </div>
  )
}

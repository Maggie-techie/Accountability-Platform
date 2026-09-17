import { BrainCircuit, CheckCircle2, RefreshCw, History } from 'lucide-react'
import { Card, Badge, Button, Alert } from '../../components/ui'
import { KpiCard } from '../../components/Insights'

const trainingHistory = [
  { date: '2025-08-30', records: 4213, accuracy: '91.2%', status: 'Completed' },
  { date: '2025-06-14', records: 3980, accuracy: '89.7%', status: 'Completed' },
  { date: '2025-03-02', records: 3401, accuracy: '87.5%', status: 'Completed' },
]

export default function AIModelManagement() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">AI / ML model management</h1>
      <p className="text-ink-muted mb-6">Monitor and retrain the anomaly-detection model.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Model status" value="Trained" />
        <KpiCard label="Last trained" value="Aug 30, 2025" />
        <KpiCard label="Records processed" value="4,213" />
        <KpiCard label="Model accuracy" value="91.2%" changeTone="up" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif font-semibold text-lg">Current model</h3>
            <Badge tone="good"><CheckCircle2 size={12} /> Healthy</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm mb-6">
            <Row label="Dataset used" value="Nyeri governance dataset v4" />
            <Row label="Anomaly detection" value="Active" />
            <Row label="Classification results" value="12 flagged this cycle" />
            <Row label="LIME explanations" value="Available for all flags" />
          </dl>
          <Alert tone="info" title="Retraining recommended">
            New audit findings have been imported since the last training run. Retraining will incorporate them.
          </Alert>
          <Button className="mt-4"><RefreshCw size={16} /> Trigger retraining now</Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <History size={16} className="text-ink-faint" />
            <h3 className="font-semibold">Training history</h3>
          </div>
          <ul className="space-y-3 text-sm">
            {trainingHistory.map((t) => (
              <li key={t.date} className="border-b border-line pb-3 last:border-0">
                <p className="font-medium text-ink">{t.date}</p>
                <p className="text-ink-muted text-xs mt-0.5">{t.records.toLocaleString()} records &middot; {t.accuracy} accuracy</p>
                <Badge tone="good" className="mt-1.5">{t.status}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div>
      <dt className="text-ink-faint text-xs">{label}</dt>
      <dd className="text-ink font-medium mt-0.5">{value}</dd>
    </div>
  )
}

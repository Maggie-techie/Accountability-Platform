import { Server, Database, KeyRound, Users2, Activity } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'

export default function SystemManagement() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">System management</h1>
      <p className="text-ink-muted mb-6">Environment, database and access settings.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Server size={16} className="text-ink-faint" /><h3 className="font-semibold">Service status</h3></div>
          <ul className="space-y-3 text-sm">
            <StatusRow label="Flask API" status="Online" />
            <StatusRow label="MongoDB" status="Online" />
            <StatusRow label="AI model service (Ollama)" status="Online" />
          </ul>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Database size={16} className="text-ink-faint" /><h3 className="font-semibold">Database</h3></div>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>Database: <span className="text-ink font-medium">Accountability</span></li>
            <li>Collections: <span className="text-ink font-medium">8</span></li>
            <li>Total documents: <span className="text-ink font-medium">4,213</span></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Run backup now</Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Users2 size={16} className="text-ink-faint" /><h3 className="font-semibold">Admin users</h3></div>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between"><span className="text-ink">admin@nyeri-accountability.org</span><Badge tone="good">Active</Badge></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Add admin user</Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><KeyRound size={16} className="text-ink-faint" /><h3 className="font-semibold">Security</h3></div>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>JWT session length: <span className="text-ink font-medium">Long-lived (demo)</span></li>
            <li>Last secret rotation: <span className="text-ink font-medium">Not yet rotated</span></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Rotate JWT secret</Button>
        </Card>
      </div>
    </div>
  )
}

function StatusRow({ label, status }) {
  return (
    <li className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-ink"><Activity size={13} className="text-forest-600" /> {label}</span>
      <Badge tone="good">{status}</Badge>
    </li>
  )
}

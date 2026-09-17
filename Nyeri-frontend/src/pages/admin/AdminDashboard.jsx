import { BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Database, Users, FileWarning, BrainCircuit, UploadCloud, CheckCircle2, AlertTriangle } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { KpiCard } from '../../components/Insights'
import { adminSummary, importHistory, anomalies } from '../../data/mockData'

const weeklyImports = [
  { day: 'Mon', imports: 1 }, { day: 'Tue', imports: 0 }, { day: 'Wed', imports: 2 },
  { day: 'Thu', imports: 0 }, { day: 'Fri', imports: 1 }, { day: 'Sat', imports: 0 }, { day: 'Sun', imports: 0 },
]

export default function AdminDashboard() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Admin dashboard</h1>
      <p className="text-ink-muted mb-6">System overview and recent activity.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total leaders" value={adminSummary.totalLeaders} />
        <KpiCard label="Datasets tracked" value={adminSummary.totalDatasets} />
        <KpiCard label="Records in database" value={adminSummary.totalRecords.toLocaleString()} />
        <KpiCard label="Detected anomalies" value={adminSummary.detectedAnomalies} changeTone="down" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0"><CheckCircle2 size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">Data validation status</p>
            <p className="font-semibold text-ink">{adminSummary.validationStatus}</p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0"><BrainCircuit size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">AI model status</p>
            <p className="font-semibold text-ink">{adminSummary.modelStatus} &middot; last trained {adminSummary.lastTrained}</p>
          </div>
        </Card>
        <Card className="p-5 flex items-start gap-4">
          <div className="h-10 w-10 rounded bg-gold-50 text-gold-500 flex items-center justify-center shrink-0"><AlertTriangle size={18} /></div>
          <div>
            <p className="text-sm text-ink-muted">High-severity anomalies</p>
            <p className="font-semibold text-ink">{anomalies.filter((a) => a.severity === 'High').length} need review</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-serif font-semibold text-lg mb-4">Recent imports</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted border-b border-line">
                <th className="py-2 font-medium">File</th>
                <th className="py-2 font-medium">Category</th>
                <th className="py-2 font-medium">Records</th>
                <th className="py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {importHistory.map((imp) => (
                <tr key={imp.id} className="border-b border-line last:border-0">
                  <td className="py-2.5 pr-2 text-ink">{imp.filename}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{imp.category}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{imp.records}</td>
                  <td className="py-2.5">
                    <Badge tone={imp.status.startsWith('Completed') ? 'good' : 'risk'}>{imp.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Imports this week</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyImports}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                <RTooltip contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Bar dataKey="imports" fill="#14532D" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}

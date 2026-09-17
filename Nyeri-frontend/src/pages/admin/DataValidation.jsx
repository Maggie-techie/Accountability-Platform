import { CheckCircle2, AlertTriangle, Copy, FileWarning } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { KpiCard } from '../../components/Insights'

const issues = [
  { id: 1, type: 'Inconsistent financial year', record: 'Mathira allocation row 14', detail: '"FY2024-25" should be "2024/25"', icon: FileWarning, tone: 'watch' },
  { id: 2, type: 'Duplicate record', record: 'Nyeri Town audit finding row 8', detail: 'Matches existing record AF-003', icon: Copy, tone: 'watch' },
  { id: 3, type: 'Missing value', record: 'Dept Spending Tracker row 22', detail: 'q3_spend_kshm is empty', icon: AlertTriangle, tone: 'risk' },
]

export default function DataValidation() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Data validation</h1>
      <p className="text-ink-muted mb-6">Review data-quality issues before they go live on the public platform.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Valid records" value="4,187" changeTone="up" />
        <KpiCard label="Missing values" value="9" changeTone="down" />
        <KpiCard label="Duplicate records" value="4" changeTone="down" />
        <KpiCard label="Invalid formats" value="3" changeTone="down" />
      </div>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Open issues</h3>
        <ul className="divide-y divide-line">
          {issues.map((i) => (
            <li key={i.id} className="py-4 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className={`h-8 w-8 rounded flex items-center justify-center shrink-0 ${i.tone === 'risk' ? 'bg-clay-50 text-clay-500' : 'bg-gold-50 text-gold-500'}`}>
                  <i.icon size={15} />
                </div>
                <div>
                  <p className="text-sm font-medium text-ink">{i.type}</p>
                  <p className="text-xs text-ink-muted mt-0.5">{i.record}</p>
                  <p className="text-xs text-ink-faint mt-0.5">{i.detail}</p>
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <Button size="sm" variant="secondary">Fix</Button>
                <Button size="sm" variant="ghost">Ignore</Button>
              </div>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2 text-sm text-forest-700 mt-4 pt-4 border-t border-line">
          <CheckCircle2 size={16} /> All other records passed validation and are ready to import.
        </div>
      </Card>
    </div>
  )
}

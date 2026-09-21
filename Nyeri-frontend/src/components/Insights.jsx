import { TrendingUp, TrendingDown, ShieldAlert, Sparkles, FileText, Quote } from 'lucide-react'
import { Card, Badge } from './ui'
import { scoreCategory } from '../data/mockData'

export function KpiCard({ label, value, change, changeTone = 'neutral', sub }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="text-2xl font-serif font-semibold text-ink mt-1">{value}</p>
      {change && (
        <p className={`mt-1 flex items-center gap-1 text-xs font-medium ${
          changeTone === 'up' ? 'text-forest-600' : changeTone === 'down' ? 'text-clay-500' : 'text-ink-muted'
        }`}>
          {changeTone === 'up' && <TrendingUp size={13} />}
          {changeTone === 'down' && <TrendingDown size={13} />}
          {change}
        </p>
      )}
      {sub && <p className="text-xs text-ink-faint mt-1">{sub}</p>}
    </Card>
  )
}

export function ScoreGauge({ score, size = 128 }) {
  const safeScore = Number.isFinite(score) ? score : 0
  const { label, tone } = scoreCategory(safeScore)
  const toneColor = { good: '#14532D', watch: '#A87620', risk: '#A6431F' }[tone]
  const circumference = 2 * Math.PI * 52
  const offset = circumference - (score / 100) * circumference
  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} viewBox="0 0 120 120" className="-rotate-90">
        <circle cx="60" cy="60" r="52" fill="none" stroke="#E2E5E1" strokeWidth="10" />
        <circle
          cx="60" cy="60" r="52" fill="none" stroke={toneColor} strokeWidth="10"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        />
      </svg>
      <div className="-mt-[76px] flex flex-col items-center">
        <span className="text-3xl font-serif font-semibold text-ink">
          {Number.isFinite(score) ? score : '—'}
        </span>
        <span className="text-xs text-ink-muted">out of 100</span>
      </div>
      <Badge tone={tone} className="mt-3">{label}</Badge>
    </div>
  )
}

export function AIDisclaimer({ compact = false }) {
  if (compact) {
    return (
      <p className="flex items-start gap-2 text-xs text-ink-muted bg-gold-50 border border-gold-100 rounded p-2.5">
        <ShieldAlert size={14} className="mt-0.5 shrink-0 text-gold-500" />
        AI results are indicators for investigation, not proof of wrongdoing.
      </p>
    )
  }
  return (
    <div className="flex items-start gap-3 rounded-md border border-gold-100 bg-gold-50 p-4 text-sm">
      <ShieldAlert size={18} className="mt-0.5 shrink-0 text-gold-500" />
      <p className="text-ink-muted">
        <span className="font-semibold text-ink">An anomaly is an indicator, not a verdict.</span> It flags an
        unusual pattern that may warrant further investigation. It does not by itself establish fraud, corruption,
        or wrongdoing.
      </p>
    </div>
  )
}

export function EvidenceChain({ result, explanation, sources }) {
  return (
    <div className="space-y-3">
      <ChainStep icon={Sparkles} label="Result" tone="forest">{result}</ChainStep>
      <ChainStep icon={Quote} label="Explanation" tone="gold">{explanation}</ChainStep>
      <ChainStep icon={FileText} label="Evidence / source">
        <ul className="list-disc pl-4 space-y-0.5">
          {sources.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      </ChainStep>
      <AIDisclaimer compact />
    </div>
  )
}

function ChainStep({ icon: Icon, label, tone = 'neutral', children }) {
  const colors = { forest: 'text-forest-600 bg-forest-50', gold: 'text-gold-500 bg-gold-50', neutral: 'text-ink-muted bg-ink/5' }
  return (
    <div className="flex gap-3">
      <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${colors[tone]}`}>
        <Icon size={14} />
      </div>
      <div className="text-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-0.5">{label}</p>
        <div className="text-ink-muted">{children}</div>
      </div>
    </div>
  )
}

export function LimeChart({ features }) {
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.weight)))
  return (
    <div className="space-y-2.5">
      {features.map((f) => {
        const pct = (Math.abs(f.weight) / maxAbs) * 100
        const positive = f.weight >= 0
        return (
          <div key={f.feature} className="text-sm">
            <div className="flex justify-between mb-1">
              <span className="text-ink-muted">{f.feature}</span>
              <span className={positive ? 'text-clay-500' : 'text-forest-600'}>{positive ? '+' : ''}{f.weight.toFixed(2)}</span>
            </div>
            <div className="h-2 rounded-full bg-ink/5 overflow-hidden">
              <div
                className={`h-full rounded-full ${positive ? 'bg-clay-400' : 'bg-forest-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      })}
      <p className="text-xs text-ink-faint pt-1">
        Bars pushing right (clay) increased the anomaly score; bars pushing left (green) decreased it.
      </p>
    </div>
  )
}

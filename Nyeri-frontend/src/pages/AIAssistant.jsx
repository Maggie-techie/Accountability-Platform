import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Send, Sparkles, Bot, User, FileText } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'

const suggested = [
  "What was Nyeri County's development expenditure?",
  'What are the major audit findings?',
  'Which constituencies have unusual expenditure patterns?',
  'How did departmental budget absorption change?',
  "Explain this leader's accountability score.",
]

const mockAnswer = {
  question: 'Which constituencies have unusual expenditure patterns?',
  answer:
    'Two constituencies currently show flagged spending patterns. Mathira has an unusual spike in bursary disbursement in FY2023/24 (71.5M observed vs. 42.0M expected), and Tetu shows a contractor paid in full before a completion certificate was recorded for a water project in FY2024/25.',
  figures: [
    { label: 'Mathira bursary disbursement (observed)', value: 'KSh 71.5M' },
    { label: 'Mathira bursary disbursement (expected)', value: 'KSh 42.0M' },
  ],
  related: [
    { label: 'Mathira Constituency profile', to: '/constituencies/mathira' },
    { label: 'Anomaly AN-1042 investigation', to: '/anomalies/AN-1042' },
  ],
  sources: ['Nyeri NG-CDF Allocation Records, FY2022/23-2025/26', 'Office of the Auditor-General, Mathira Constituency Report FY2023/24'],
}

export default function AIAssistant() {
  const [params] = useSearchParams()
  const about = params.get('about')
  const [messages, setMessages] = useState(
    about
      ? [{ role: 'assistant', type: 'text', content: `You're asking about ${about}. Try a specific question below, e.g. "Explain ${about}'s accountability score."` }]
      : [{ role: 'assistant', type: 'text', content: 'Ask me anything about Nyeri County governance data — budgets, NG-CDF, audits or anomalies. I answer only in English, using the platform’s verified records.' }]
  )
  const [input, setInput] = useState('')

  function ask(question) {
    setMessages((m) => [...m, { role: 'user', type: 'text', content: question }, { role: 'assistant', type: 'answer', data: { ...mockAnswer, question } }])
    setInput('')
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'AI Assistant' }]} />
      <div className="flex items-center gap-2 mb-1">
        <Sparkles size={20} className="text-forest-600" />
        <h1 className="text-3xl font-semibold">English AI Assistant</h1>
      </div>
      <p className="text-ink-muted mb-6 max-w-2xl">
        A governance investigative assistant. It answers in English only, grounded in the platform's source records.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <Card className="p-0 overflow-hidden flex flex-col h-[600px]">
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {messages.map((m, i) => <Message key={i} m={m} />)}
            </div>
            <div className="border-t border-line p-3">
              <form
                onSubmit={(e) => { e.preventDefault(); if (input.trim()) ask(input.trim()) }}
                className="flex gap-2"
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a governance question in English…"
                  className="flex-1 rounded border border-line px-4 py-2.5 text-sm outline-none focus:border-forest-600"
                />
                <Button type="submit"><Send size={16} /></Button>
              </form>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-3">Suggested questions</p>
            <div className="flex flex-col gap-2">
              {suggested.map((q) => (
                <button key={q} onClick={() => ask(q)} className="text-left text-sm text-forest-700 hover:underline">
                  {q}
                </button>
              ))}
            </div>
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}

function Message({ m }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-md bg-forest-700 text-white rounded-lg rounded-tr-sm px-4 py-2.5 text-sm">{m.content}</div>
        <div className="h-7 w-7 rounded-full bg-forest-100 text-forest-700 flex items-center justify-center shrink-0"><User size={14} /></div>
      </div>
    )
  }
  return (
    <div className="flex gap-2">
      <div className="h-7 w-7 rounded-full bg-forest-700 text-white flex items-center justify-center shrink-0"><Bot size={14} /></div>
      <div className="max-w-lg">
        {m.type === 'text' ? (
          <div className="bg-ink/5 rounded-lg rounded-tl-sm px-4 py-2.5 text-sm text-ink">{m.content}</div>
        ) : (
          <Card className="p-4">
            <p className="text-sm text-ink mb-3">{m.data.answer}</p>
            {m.data.figures?.length > 0 && (
              <div className="grid grid-cols-2 gap-2 mb-3">
                {m.data.figures.map((f) => (
                  <div key={f.label} className="bg-forest-50 rounded p-2 text-xs">
                    <p className="text-ink-faint">{f.label}</p>
                    <p className="font-semibold text-forest-700">{f.value}</p>
                  </div>
                ))}
              </div>
            )}
            {m.data.related?.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {m.data.related.map((r) => (
                  <Link key={r.to} to={r.to}><Badge tone="info">{r.label}</Badge></Link>
                ))}
              </div>
            )}
            <div className="border-t border-line pt-2.5 mt-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-1.5 flex items-center gap-1.5">
                <FileText size={12} /> Sources used
              </p>
              <ul className="text-xs text-ink-muted space-y-0.5 list-disc pl-4">
                {m.data.sources.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

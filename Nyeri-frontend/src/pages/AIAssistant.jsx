import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Send, Sparkles, Bot, User, FileText } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'

// Suggested questions
const suggested = [
  "What was Nyeri County's development expenditure?",
  'What are the major audit findings?',
  'Which constituencies have unusual expenditure patterns?',
  'How did departmental budget absorption change?',
  "Explain this leader's accountability score.",
]

// Helper function to determine which AI endpoint to call based on the question
function getAIEndpointAndParams(question) {
  const lowerQuestion = question.toLowerCase()

  // Default to a general county narrative if no specific match
  let endpoint = '/ai/county/narrative'
  let params = {}
  let method = 'GET'

  // Check for specific patterns in the question
  if (lowerQuestion.includes('development expenditure') ||
      lowerQuestion.includes('budget vs expenditure') ||
      lowerQuestion.includes('development vs recurrent')) {
    endpoint = '/ai/governor/fiscal_health'
  } else if (lowerQuestion.includes('audit findings') ||
             lowerQuestion.includes('major audit') ||
             lowerQuestion.includes('audit')) {
    endpoint = '/ai/findings/classifier'
    method = 'POST'
    // We would need to pass specific finding text, but for now use general
  } else if (lowerQuestion.includes('unusual expenditure patterns') ||
             lowerQuestion.includes('unusual spending') ||
             lowerQuestion.includes('anomalies')) {
    // For anomalies, we'd need to specify a constituency or get general ones
    // Let's check if they mentioned a specific constituency
    const constituencies = ['kieni', 'mathira', 'othaya', 'tetu', 'mukurwe-ini', 'nyeri town']
    const mentionedConstituency = constituencies.find(c =>
      lowerQuestion.includes(c) ||
      lowerQuestion.includes(c.replace('-', ' '))
    )

    if (mentionedConstituency) {
      endpoint = `/ai/mp/${mentionedConstituency}/anomalies`
    } else {
      // Default to first constituency or get county-level anomalies if available
      endpoint = `/ai/mp/kieni/anomalies` // Default to Kieni
    }
  } else if (lowerQuestion.includes('departmental budget absorption') ||
             lowerQuestion.includes('absorption rate') ||
             lowerQuestion.includes('department absorption')) {
    endpoint = '/ai/governor/dept_absorption'
  } else if (lowerQuestion.includes('leader.*accountability score') ||
             lowerQuestion.includes('explain.*score') ||
             lowerQuestion.includes('accountability score')) {
    // Check if they mentioned a specific leader
    const constituencies = ['kieni', 'mathira', 'othaya', 'tetu', 'mukurwe-ini', 'nyeri town']
    const mentionedConstituency = constituencies.find(c =>
      lowerQuestion.includes(c) ||
      lowerQuestion.includes(c.replace('-', ' '))
    )

    if (mentionedConstituency) {
      endpoint = `/ai/mp/${mentionedConstituency}/summary`
    } else {
      // Default to governor's score or general summary
      endpoint = '/ai/governor/fiscal_health' // This gives a score
    }
  } else if (lowerQuestion.includes('compare') ||
             lowerQuestion.includes('vs ') ||
             lowerQuestion.includes('versus')) {
    endpoint = '/ai/compare'
    method = 'POST'
    // This would need more complex parsing to extract what to compare
  }

  return { endpoint, params, method }
}

// Helper function to format AI response to match what the component expects
function formatAIResponse(aiData, question) {
  // If we got an error or invalid response, return a fallback
  if (!aiData || !aiData.success) {
    return {
      question,
      answer: "I'm unable to retrieve specific information at the moment. Please try again later.",
      figures: [],
      related: [],
      sources: ['System unable to fetch data']
    }
  }

  // Extract data from AI response
  const data = aiData.data || {}

  // Try to extract meaningful information from the AI response
  let answer = "I've analyzed the data and here's what I found."
  let figures = []
  let related = []
  let sources = ['Nyeri County Governance Platform']

  // Try to get a summary from narrative fields
  if (data.narrative_fields) {
    if (data.narrative_fields.summary) {
      answer = data.narrative_fields.summary
    } else if (data.narrative_fields.health_level) {
      answer = `The fiscal health assessment is: ${data.narrative_fields.health_level}.`
    } else if (data.narrative_fields.risk_level) {
      answer = `The risk level assessment is: ${data.narrative_fields.risk_level}.`
    }
  }

  // Try to extract chart data for figures
  if (data.chart_data) {
    // Look for numeric values we can display as figures
    Object.entries(data.chart_data).forEach(([key, value]) => {
      if (typeof value === 'number') {
        figures.push({
          label: key.replace('_', ' ').replace(/([A-Z])/g, ' $1').trim(),
          value: `${value.toLocaleString()} ` + (key.includes('score') ? '' : 'units')
        })
      } else if (Array.isArray(value)) {
        // Handle arrays - take first few items if they look like metrics
        value.slice(0, 3).forEach((item, index) => {
          if (item && typeof item === 'object') {
            const label = item.label || item.name || item.constituent || `Item ${index + 1}`
            const val = item.value || item.score || item.amount || item.health || 'N/A'
            figures.push({
              label: String(label),
              value: String(val)
            })
          }
        })
      }
    })
  }

  // If we still don't have good figures, create some from the answer or use defaults
  if (figures.length === 0) {
    // Try to extract numbers from the answer
    const numberMatches = answer.match(/\d+(?:\.\d+)?/g)
    if (numberMatches) {
      numberMatches.slice(0, 3).forEach((num, index) => {
        figures.push({
          label: `Metric ${index + 1}`,
          value: num
        })
      })
    }
  }

  // Try to extract related links
  if (data.related) {
    related = data.related
  } else if (data.chart_data && data.chart_data.constituency_risk_scores) {
    related = data.chart_data.constituency_risk_scores.map((item, index) => ({
      label: `${item.name || `Constituency ${index + 1}`} Risk Score`,
      to: `/constituencies/${item.slug || item.name.toLowerCase().replace(/\s+/g, '-')}`
    }))
  } else {
    // Add some default related links
    related = [
      { label: 'Nyeri County Overview', to: '/county' },
      { label: 'Constituencies List', to: '/constituencies' },
      { label: 'Leaders Directory', to: '/leaders' }
    ]
  }

  return {
    question,
    answer,
    figures,
    related,
    sources
  }
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
  const [loading, setLoading] = useState(false)

  function ask(question) {
    // Add user message to chat
    setMessages((m) => [...m, { role: 'user', type: 'text', content: question }])
    setInput('')
    setLoading(true)

    // Determine which AI endpoint to call
    const { endpoint, params: aiParams, method } = getAIEndpointAndParams(question)

    // Make the API call
    const fetchAIData = async () => {
      try {
        let response

        if (method === 'POST') {
          // For POST requests, we need to send data in the body
          // This is simplified - in reality we'd need to extract more specific params from the question
          response = await fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              // Extract any specific IDs or parameters from the question
              ...aiParams,
              // Add question context for the AI
              question_context: question
            })
          })
        } else {
          // For GET requests
          const queryParams = new URLSearchParams(aiParams).toString()
          const url = `${APIService.__API_BASE_URL || 'http://localhost:5000/api'}${endpoint}${queryParams ? '?' + queryParams : ''}`
          response = await fetch(url)
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const aiData = await response.json()

        // Format the response to match what our component expects
        const formattedData = formatAIResponse(aiData, question)

        // Add assistant response to chat
        setMessages((m) => [...m, { role: 'assistant', type: 'answer', data: formattedData }])
      } catch (err) {
        console.error('Error calling AI API:', err)
        // Add error message to chat
        setMessages((m) => [...m, {
          role: 'assistant',
          type: 'text',
          content: `I'm sorry, I encountered an error while trying to answer your question. Please try again or rephrase your question. Error: ${err.message}`
        }])
      } finally {
        setLoading(false)
      }
    }

    fetchAIData()
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
              {messages.map((m, i) => (
                <div key={i}>
                  {m.role === 'user' ? (
                    <div className="flex justify-end gap-2">
                      <div className="max-w-md bg-forest-700 text-white rounded-lg rounded-tr-sm px-4 py-2.5 text-sm">{m.content}</div>
                      <div className="h-7 w-7 rounded-full bg-forest-100 text-forest-700 flex items-center justify-center shrink-0"><User size={14} /></div>
                    </div>
                  ) : (
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
                  )}
                </div>
              ))}
            </div>
            <div className="border-t border-line p-3">
              <form
                onSubmit={(e) => { e.preventDefault(); if (input.trim()) ask(input.trim()) }}
                className="flex gap-2"
                disabled={loading}
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a governance question in English…"
                  className={`flex-1 rounded border border-line px-4 py-2.5 text-sm outline-none focus:border-forest-600 ${loading ? 'opacity-50' : ''}`}
                  disabled={loading}
                />
                <Button type="submit" disabled={loading}>
                  {loading ? 'Analyzing...' : <Send size={16} />}
                </Button>
              </form>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-3">Suggested questions</p>
            <div className="flex flex-col gap-2">
              {suggested.map((q) => (
                <button key={q} onClick={() => ask(q)} disabled={loading} className={`text-left text-sm text-forest-700 hover:underline ${loading ? 'opacity-50' : ''}`}>
                  {q}
                </button>
              ))}
            </div>
          </div>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}
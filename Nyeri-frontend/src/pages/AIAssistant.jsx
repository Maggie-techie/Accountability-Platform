import { useState, useRef, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Send, Sparkles, Bot, User, FileText } from 'lucide-react'
import { Card, Badge, Button } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'
import APIService from '../services/api'

// Suggested questions
const suggested = [
  "Who is the MP for Kieni?",
  "Who is the Governor of Nyeri County?",
  "List all MPs in Nyeri County",
  "What is the budget for Othaya constituency?",
  "Audit findings for Mathira",
  "Nyeri County budget breakdown",
  "What was Nyeri County's development expenditure?",
  'What are the major audit findings?',
  'Which constituencies have unusual expenditure patterns?',
  'How did departmental budget absorption change?',
  "Explain this leader's accountability score.",
]

// Helper function to handle simple factual questions directly from the database
async function handleSimpleQuestion(question) {
  const lowerQuestion = question.toLowerCase()
  const constituencies = [
    { name: 'Kieni', slug: 'kieni' },
    { name: 'Mathira', slug: 'mathira' },
    { name: 'Othaya', slug: 'othaya' },
    { name: 'Tetu', slug: 'tetu' },
    { name: 'Mukurwe-ini', slug: 'mukurweini' },
    { name: 'Nyeri Town', slug: 'nyeri_town' },
  ]

  // 1. Who is the MP / leader of [constituency]?
  const mpMatch = lowerQuestion.match(/(?:who is the (?:mp|member of parliament|leader|representative) of|who represents|mp (?:for|of))\s+([a-z\s\-]+)/i)
  if (mpMatch) {
    const query = mpMatch[1].trim().toLowerCase().replace(/\s+/g, '_').replace(/-/, '')
    const matched = constituencies.find(c => c.slug === query || c.name.toLowerCase() === query)
    if (matched) {
      const mpData = await APIService.getMPByConstituency(matched.slug)
      if (mpData?.name) {
        return {
          answer: `The Member of Parliament for ${matched.name} Constituency is **${mpData.name}** (${mpData.party || 'Party not specified'}).`,
          figures: [],
          related: [{ label: `${matched.name} Profile`, to: `/constituencies/${matched.slug}` }],
          sources: ['NG-CDF Board / Constituency Records']
        }
      }
    }
    return { answer: `I couldn't find an MP for "${mpMatch[1]}". Please check the constituency name.`, figures: [], related: [], sources: [] }
  }

  // 2. Who is the governor?
  if (lowerQuestion.includes('who is the governor') || lowerQuestion === 'governor' || lowerQuestion.includes('county governor')) {
    const govData = await APIService.getGovernorProfile()
    if (govData?.name) {
      return {
        answer: `The Governor of Nyeri County is **${govData.name}** (${govData.party || 'Party not specified'}), serving since ${govData.tenure || 'tenure not specified'}.`,
        figures: [],
        related: [{ label: 'Governor Profile', to: `/leaders/${govData.id || govData._id}` }, { label: 'County Dashboard', to: '/county' }],
        sources: ['County Government Records']
      }
    }
    return { answer: 'Unable to fetch governor information at the moment.', figures: [], related: [], sources: [] }
  }

  // 3. List all MPs / leaders
  if (lowerQuestion.includes('list all') && (lowerQuestion.includes('mp') || lowerQuestion.includes('member of parliament') || lowerQuestion.includes('leaders'))) {
    const allScores = await APIService.getAllConstituencyScores()
    const leaders = allScores.map(c => `• ${c.mp?.name} — ${c.name} Constituency (${c.mp?.party || 'Party not specified'})`).join('\n')
    return {
      answer: `**Nyeri County Members of Parliament:**\n${leaders}`,
      figures: [],
      related: [{ label: 'All Leaders', to: '/leaders' }],
      sources: ['NG-CDF Board / Constituency Records']
    }
  }

  // 4. What is the allocation for [constituency]?
  const allocMatch = lowerQuestion.match(/(?:allocation|budget|funding|ng.?cdf).*(?:for|of)\s+([a-z\s\-]+)/i)
  if (allocMatch) {
    const query = allocMatch[1].trim().toLowerCase().replace(/\s+/g, '_').replace(/-/, '')
    const matched = constituencies.find(c => c.slug === query || c.name.toLowerCase() === query)
    if (matched) {
      const allocData = await APIService.getConstituencyAllocations(matched.slug)
      if (allocData?.allocations?.length) {
        const latest = allocData.allocations.sort((a, b) => (b.fy_key || '').localeCompare(a.fy_key || ''))[0]
        const total = allocData.allocations.reduce((sum, a) => sum + (a.amount_kshm || 0), 0)
        return {
          answer: `**${matched.name} Constituency NG-CDF Allocation:**\nLatest FY (${latest?.fy_key || 'N/A'}): KSh ${latest?.amount_kshm?.toLocaleString() || 0}M\nAll-time total: KSh ${total.toLocaleString()}M`,
          figures: [{ label: 'Latest FY Allocation', value: `KSh ${latest?.amount_kshm || 0}M` }, { label: 'Total Allocation', value: `KSh ${total}M` }],
          related: [{ label: `${matched.name} Profile`, to: `/constituencies/${matched.slug}` }],
          sources: ['NG-CDF Board Disbursement Records']
        }
      }
    }
    return { answer: `I couldn't find allocation data for "${allocMatch[1]}".`, figures: [], related: [], sources: [] }
  }

  // 5. What are the audit findings for [constituency]?
  const auditMatch = lowerQuestion.match(/(?:audit findings|findings).*(?:for|of)\s+([a-z\s\-]+)/i)
  if (auditMatch) {
    const query = auditMatch[1].trim().toLowerCase().replace(/\s+/g, '_').replace(/-/, '')
    const matched = constituencies.find(c => c.slug === query || c.name.toLowerCase() === query)
    if (matched) {
      const auditData = await APIService.getConstituencyAuditFindings(matched.slug)
      const findings = auditData?.audit_findings || auditData || []
      if (findings.length) {
        const misap = findings.filter(f => f.finding_type?.toLowerCase() === 'misappropriation')
        return {
          answer: `**${matched.name} Constituency Audit Findings:**\nTotal findings: ${findings.length}\nMisappropriation findings: ${misap.length}\n\n${findings.slice(0, 3).map(f => `• ${f.finding_type || 'Finding'}: ${f.finding || f.note || 'No details'}`).join('\n')}${findings.length > 3 ? '\n...and more' : ''}`,
          figures: [{ label: 'Total Findings', value: findings.length }, { label: 'Misappropriations', value: misap.length }],
          related: [{ label: `${matched.name} Profile`, to: `/constituencies/${matched.slug}` }, { label: 'All Anomalies', to: '/anomalies' }],
          sources: ['Office of the Auditor-General Reports']
        }
      }
    }
    return { answer: `No audit findings found for "${auditMatch[1]}".`, figures: [], related: [], sources: [] }
  }

  // 6. County budget / finances
  if (lowerQuestion.includes('county budget') || lowerQuestion.includes('county finances') || lowerQuestion.includes('county revenue')) {
    const finances = await APIService.getCountyFinances()
    if (finances?.length) {
      const latest = finances.sort((a, b) => (b.financial_year || '').localeCompare(a.financial_year || ''))[0]
      const sources = []
      if (latest.equitable_share_kshb) sources.push(`Equitable Share: KSh ${latest.equitable_share_kshb}B`)
      if (latest.conditional_grants_kshb) sources.push(`Conditional Grants: KSh ${latest.conditional_grants_kshb}B`)
      if (latest.osr_kshb) sources.push(`Own Source Revenue: KSh ${latest.osr_kshb}B`)
      return {
        answer: `**Nyeri County Finances (${latest?.financial_year || 'Latest FY'}):**\n${sources.join('\n')}`,
        figures: sources.map(s => ({ label: s.split(':')[0], value: s.split(':')[1].trim() })),
        related: [{ label: 'County Dashboard', to: '/county' }],
        sources: ['Nyeri County Fiscal Reports / National Treasury']
      }
    }
    return { answer: 'Unable to fetch county finances at the moment.', figures: [], related: [], sources: [] }
  }

  return null // Not a simple question
}

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
      : [{ role: 'assistant', type: 'text', content: 'Ask me anything about Nyeri County governance data - budgets, NG-CDF, audits or anomalies. I answer only in English, using the platform\'s verified records.' }]
  )
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // Ref for the messages container to enable auto-scroll
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function ask(question) {
    // Add user message to chat
    setMessages((m) => [...m, { role: 'user', type: 'text', content: question }])
    setInput('')
    setLoading(true)

    // First, try to handle simple factual questions directly
    const fetchAnswer = async () => {
      try {
        // Check for simple questions we can answer from the database
        const simpleAnswer = await handleSimpleQuestion(question)
        if (simpleAnswer) {
          setMessages((m) => [...m, { role: 'assistant', type: 'answer', data: { ...simpleAnswer, question } }])
          setLoading(false)
          return
        }

        // Otherwise, use AI endpoints for analytical questions
        const { endpoint, params: aiParams, method } = getAIEndpointAndParams(question)

        let response

        if (method === 'POST') {
          // For POST requests, we need to send data in the body
          response = await fetch(`${APIService.baseURL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ...aiParams,
              question_context: question
            })
          })
        } else {
          // For GET requests
          const queryParams = new URLSearchParams(aiParams).toString()
          const url = `${APIService.baseURL}${endpoint}${queryParams ? '?' + queryParams : ''}`
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

    fetchAnswer()
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
              {/* Sentinel div for auto-scroll */}
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t border-line p-3">
              <form
                onSubmit={(e) => { e.preventDefault(); if (input.trim()) ask(input.trim()) }}
                className="flex gap-2"
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a governance question in English..."
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
          </Card>
          <AIDisclaimer compact />
        </div>
      </div>
    </div>
  )
}
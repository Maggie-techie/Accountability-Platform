import { useState, useEffect, useCallback } from 'react'
import { CheckCircle2, RefreshCw, History, Search } from 'lucide-react'
import { Card, Badge, Button, Alert } from '../../components/ui'
import { KpiCard } from '../../components/Insights'
import APIService from '../../services/api'

const fmt = (n) => (n == null || Number.isNaN(Number(n)) ? '—' : Number(n).toLocaleString())

const fmtDate = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString()
}

// Backend errors look like { error, details } where details may be a string or an object.
const errText = (json, fallback) => {
  const d = json?.details
  const detail = typeof d === 'string' ? d : d?.message ?? (d ? JSON.stringify(d) : '')
  return [json?.error, detail].filter(Boolean).join(' — ') || fallback
}

const authHeaders = () => {
  const headers = {}
  const token = localStorage.getItem('authToken')
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export default function AIModelManagement() {
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [alert, setAlert] = useState(null) // { tone, text }
  const [detection, setDetection] = useState(null) // array of anomalies

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${APIService.baseURL}/anomalies/gnn/status`, { headers: authHeaders() })
      const json = await res.json().catch(() => ({}))
      if (!res.ok || json.success === false) throw new Error(errText(json, `HTTP ${res.status}`))
      setStatus(json.data ?? null)
      setStatusError(null)
    } catch (err) {
      console.error('Error fetching AI model status:', err)
      setStatusError(err.message || 'Failed to load model status')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      await fetchStatus()
      if (!cancelled) setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [fetchStatus])

  const handleRetrain = async () => {
    setTraining(true)
    setDetection(null)
    setAlert({ tone: 'info', text: 'Training started. This can take a little while...' })
    try {
      const res = await fetch(`${APIService.baseURL}/anomalies/gnn/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok || json.success === false) throw new Error(errText(json, `HTTP ${res.status}`))

      setAlert({ tone: 'good', text: 'Training completed successfully.' })
      await fetchStatus()
    } catch (err) {
      console.error('Error triggering model retrain:', err)
      setAlert({ tone: 'risk', text: `Training failed: ${err.message}` })
    } finally {
      setTraining(false)
    }
  }

  const handleDetect = async () => {
    setDetecting(true)
    setAlert(null)
    try {
      const res = await fetch(`${APIService.baseURL}/anomalies/gnn/detect`, { headers: authHeaders() })
      const json = await res.json().catch(() => ({}))
      if (!res.ok || json.success === false) throw new Error(errText(json, `HTTP ${res.status}`))

      setDetection(Array.isArray(json.data?.anomalies) ? json.data.anomalies : [])
      await fetchStatus() // detection auto-trains if the model was untrained
    } catch (err) {
      console.error('Error running anomaly detection:', err)
      setAlert({ tone: 'risk', text: `Detection failed: ${err.message}` })
    } finally {
      setDetecting(false)
    }
  }

  const modelStatus = statusError
    ? 'Error'
    : !status
      ? 'Unknown'
      : !status.model_available
        ? 'Unavailable'
        : status.is_trained
          ? 'Trained'
          : 'Not trained'

  const history = Array.isArray(status?.history) ? status.history : []
  const busy = training || detecting

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">AI / ML model management</h1>
        <p className="text-ink-muted mb-6">Loading model status...</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">AI / ML model management</h1>
      <p className="text-ink-muted mb-6">Monitor, retrain and run the anomaly-detection model.</p>

      {statusError && (
        <div className="mb-6 rounded border border-line bg-gold-50 px-4 py-3 text-sm text-ink flex items-center justify-between gap-4">
          <span>Could not load model status: {statusError}</span>
          <button onClick={fetchStatus} className="btn btn-outline">
            Retry
          </button>
        </div>
      )}

      {status && status.model_available === false && (
        <div className="mb-6 rounded border border-line bg-gold-50 px-4 py-3 text-sm text-ink">
          GNN dependencies are not installed on the server, so training and detection are unavailable.
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Model status" value={modelStatus} />
        <KpiCard label="Last trained" value={fmtDate(status?.trained_at)} />
        <KpiCard label="Graph nodes" value={fmt(status?.num_nodes)} />
        <KpiCard
          label="Validation AUC"
          value={status?.val_auc != null ? Number(status.val_auc).toFixed(3) : '—'}
          changeTone="up"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif font-semibold text-lg">Current model</h3>
            <Badge tone={modelStatus === 'Trained' ? 'good' : modelStatus === 'Error' ? 'risk' : 'watch'}>
              <CheckCircle2 size={12} /> {modelStatus}
            </Badge>
          </div>

          <dl className="grid grid-cols-2 gap-4 text-sm mb-6">
            <div>
              <dt className="text-ink-faint text-xs">Model type</dt>
              <dd className="text-ink font-medium mt-0.5">Graph variational autoencoder (GVAE)</dd>
            </div>
            <div>
              <dt className="text-ink-faint text-xs">Graph edges</dt>
              <dd className="text-ink font-medium mt-0.5">{fmt(status?.num_edges)}</dd>
            </div>
            <div>
              <dt className="text-ink-faint text-xs">Embedding size</dt>
              <dd className="text-ink font-medium mt-0.5">{fmt(status?.model_parameters?.embedding_dim)}</dd>
            </div>
            <div>
              <dt className="text-ink-faint text-xs">Epochs &middot; final loss</dt>
              <dd className="text-ink font-medium mt-0.5">
                {fmt(status?.epochs)} &middot; {status?.final_loss != null ? Number(status.final_loss).toFixed(4) : '—'}
              </dd>
            </div>
          </dl>

          {alert && <Alert tone={alert.tone}>{alert.text}</Alert>}

          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={handleRetrain} disabled={busy || status?.model_available === false}>
              <RefreshCw size={16} className={training ? 'animate-spin' : ''} />{' '}
              {training ? 'Training...' : 'Trigger retraining now'}
            </Button>
            <Button onClick={handleDetect} disabled={busy || status?.model_available === false}>
              <Search size={16} /> {detecting ? 'Detecting...' : 'Run anomaly detection'}
            </Button>
          </div>

          {detection && (
            <div className="mt-6">
              <h4 className="font-semibold text-sm mb-2">Top anomalies ({detection.length})</h4>
              {detection.length === 0 ? (
                <p className="text-sm text-ink-muted">No anomalies detected.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {detection.map((a) => (
                    <li key={a.node_id} className="border-b border-line pb-3 last:border-0">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium text-ink">
                          #{a.anomaly_rank} &middot; {a.node_type === 'governor_year' ? 'County' : 'Constituency'}
                        </p>
                        <Badge tone={a.anomaly_score >= 0.7 ? 'risk' : 'watch'}>
                          {Number(a.anomaly_score).toFixed(2)}
                        </Badge>
                      </div>
                      <p className="text-ink-muted text-xs mt-1">{a.explanation}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <History size={16} className="text-ink-faint" />
            <h3 className="font-semibold">Training history</h3>
          </div>
          {history.length === 0 ? (
            <p className="text-sm text-ink-muted">No training runs recorded yet.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {history.map((t, i) => (
                <li key={`${t.date}-${i}`} className="border-b border-line pb-3 last:border-0">
                  <p className="font-medium text-ink">{fmtDate(t.date)}</p>
                  <p className="text-ink-muted text-xs mt-0.5">
                    {fmt(t.nodes)} nodes &middot; AUC {t.val_auc != null ? Number(t.val_auc).toFixed(3) : '—'}
                  </p>
                  <Badge tone={t.status === 'Completed' ? 'good' : 'risk'}>{t.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
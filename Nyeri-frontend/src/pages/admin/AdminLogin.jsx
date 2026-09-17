import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Landmark, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '../../components/ui'
import APIService from '../../services/api'

export default function AdminLogin() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login') // login | forgot | sent
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    if (!email || !password) {
      setError('Enter both your email and password to continue.')
      setLoading(false)
      return
    }

    // Call the actual authentication API
    APIService.login(email, password)
      .then(response => {
        if (response.access_token) {
          // Store the token (in real app, you'd store it securely)
          localStorage.setItem('authToken', response.access_token)
          // Also store user info if needed
          localStorage.setItem('adminName', response.admin || email)
          localStorage.setItem('userName', response.name || '')

          // Navigate to admin dashboard
          navigate('/admin')
        } else {
          setError('Login failed: No token received')
          setLoading(false)
        }
      })
      .catch(err => {
        console.error('Login error:', err)
        setError('Invalid credentials or server error')
        setLoading(false)
      })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <span className="flex h-11 w-11 items-center justify-center rounded bg-forest-700 text-white mb-3">
            <Landmark size={20} />
          </span>
          <p className="font-serif font-semibold text-lg text-ink">Nyeri Accountability Platform</p>
          <p className="text-sm text-ink-muted">Admin sign in</p>
        </div>

        <div className="bg-white border border-line rounded-md shadow-card p-6">
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              {error && (
                <div className="flex items-start gap-2 rounded bg-clay-50 border border-clay-100 p-3 text-sm text-clay-600">
                  <AlertCircle size={16} className="mt-0.5 shrink-0" /> {error}
                </div>
              )}
              <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="admin@nyeri-accountability.org" />
              <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
              <Button type="submit" className="w-full justify-center" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign in'}
              </Button>
              <button type="button" onClick={() => setMode('forgot')} className="text-sm text-forest-700 hover:underline w-full text-center">
                Forgot password?
              </button>
            </form>
          )}

          {mode === 'forgot' && (
            <form onSubmit={(e) => { e.preventDefault(); setMode('sent') }} className="space-y-4">
              <p className="text-sm text-ink-muted">Enter your admin email and we'll send a reset link.</p>
              <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="admin@nyeri-accountability.org" />
              <Button type="submit" className="w-full justify-center">Send reset link</Button>
              <button type="button" onClick={() => setMode('login')} className="text-sm text-ink-muted hover:text-ink w-full text-center">
                Back to sign in
              </button>
            </form>
          )}

          {mode === 'sent' && (
            <div className="text-center py-4">
              <CheckCircle2 size={28} className="mx-auto text-forest-600 mb-3" />
              <p className="font-medium text-ink mb-1">Check your email</p>
              <p className="text-sm text-ink-muted mb-4">If that address has an admin account, a reset link is on its way.</p>
              <button onClick={() => setMode('login')} className="text-sm text-forest-700 hover:underline">Back to sign in</button>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-ink-faint mt-6">
          Public users don't need an account. <Link to="/" className="text-forest-700 hover:underline">Browse governance data &rarr;</Link>
        </p>
      </div>
    </div>
  )
}

function Field({ label, type, value, onChange, placeholder }) {
  return (
    <label className="block text-sm">
      <span className="text-ink-muted text-xs">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded border border-line px-3 py-2.5 text-sm outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600"
      />
    </label>
  )
}
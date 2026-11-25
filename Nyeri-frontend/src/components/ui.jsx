import { AlertTriangle, CheckCircle2, Info, XCircle, Loader2, Inbox, X } from 'lucide-react'
import { useEffect } from 'react'

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }) {
  const base = 'inline-flex items-center justify-center gap-2 rounded font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none'
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' }
  const variants = {
    primary: 'bg-forest-700 text-white hover:bg-forest-800',
    secondary: 'bg-white text-forest-700 border border-forest-700 hover:bg-forest-50',
    ghost: 'text-ink hover:bg-black/5',
    danger: 'bg-clay-500 text-white hover:bg-clay-600',
    link: 'text-forest-700 underline-offset-4 hover:underline p-0',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Badge({ tone = 'neutral', children, className = '' }) {
  const tones = {
    neutral: 'bg-ink/5 text-ink-muted',
    good: 'bg-forest-50 text-forest-700',
    watch: 'bg-gold-50 text-gold-500',
    risk: 'bg-clay-50 text-clay-500',
    info: 'bg-forest-50 text-forest-600',
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}>
      {children}
    </span>
  )
}

export function SeverityBadge({ severity }) {
  const map = { High: 'risk', Medium: 'watch', Low: 'good' }
  return <Badge tone={map[severity] || 'neutral'}>{severity} severity</Badge>
}

export function Card({ className = '', children, as: As = 'div', ...props }) {
  return (
    <As className={`bg-surface border border-ink/20 rounded-md shadow-lg ${className}`} {...props}>
      {children}
    </As>
  )
}

export function Alert({ tone = 'info', title, children }) {
  const icons = { info: Info, warning: AlertTriangle, success: CheckCircle2, danger: XCircle }
  const Icon = icons[tone] || Info
  const tones = {
    info: 'bg-forest-50 border-forest-100 text-forest-800',
    warning: 'bg-gold-50 border-gold-100 text-gold-500',
    success: 'bg-forest-50 border-forest-100 text-forest-700',
    danger: 'bg-clay-50 border-clay-100 text-clay-600',
  }
  return (
    <div className={`flex gap-3 rounded-md border p-4 text-sm ${tones[tone]}`}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div>
        {title && <p className="font-semibold mb-0.5">{title}</p>}
        <div className="text-ink-muted">{children}</div>
      </div>
    </div>
  )
}

export function EmptyState({ title = 'Nothing here yet', description, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6 text-ink-muted">
      <Icon size={32} className="mb-3 text-ink-faint" />
      <p className="font-medium text-ink">{title}</p>
      {description && <p className="text-sm mt-1 max-w-sm">{description}</p>}
    </div>
  )
}

export function LoadingState({ label = 'Loading data…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-ink-muted">
      <Loader2 size={26} className="animate-spin mb-3 text-forest-600" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', description = 'We could not load this data. Try again in a moment.', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <XCircle size={28} className="mb-3 text-clay-500" />
      <p className="font-medium text-ink">{title}</p>
      <p className="text-sm text-ink-muted mt-1 max-w-sm">{description}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Toast({ type = 'info', message, onClose, duration = 5000 }) {
  const icons = {
    info: <Info size={18} className="text-forest-600" />,
    warning: <AlertTriangle size={18} className="text-gold-500" />,
    success: <CheckCircle2 size={18} className="text-forest-600" />,
    error: <XCircle size={18} className="text-clay-500" />,
  }
  const backgrounds = {
    info: 'bg-forest-50 border-forest-200',
    warning: 'bg-gold-50 border-gold-200',
    success: 'bg-forest-50 border-forest-200',
    error: 'bg-clay-50 border-clay-200',
  }
  const Icon = icons[type] || icons.info

  if (typeof window !== 'undefined' && duration > 0) {
    setTimeout(() => onClose && onClose(), duration)
  }

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-md border shadow-lg animate-slide-in ${backgrounds[type]}`}>
      {Icon}
      <span className="text-sm font-medium text-ink">{message}</span>
      <button onClick={onClose} className="ml-2 text-ink-muted hover:text-ink">
        <X size={16} />
      </button>
    </div>
  )
}

export function Modal({ isOpen, onClose, title, children, size = 'md', showClose = true }) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  if (!isOpen) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in" onClick={onClose}>
      <div
        className={`w-full ${sizes[size]} bg-surface border border-ink/20 rounded-lg shadow-xl animate-slide-up`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink/10">
          <h3 className="font-semibold text-lg text-ink">{title}</h3>
          {showClose && (
            <button onClick={onClose} className="p-1 rounded hover:bg-ink/5 text-ink-muted transition-colors">
              <XCircle size={20} />
            </button>
          )}
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

export function Input({ label, error, ...props }) {
  const id = props.id || props.name
  return (
    <div className="mb-4">
      {label && <label htmlFor={id} className="block text-sm font-medium text-ink mb-1">{label}</label>}
      <input
        id={id}
        className={`w-full px-3 py-2 rounded border bg-surface text-ink placeholder-ink-muted transition-colors ${
          error ? 'border-clay-500 focus:border-clay-500 focus:ring-clay-500/20' : 'border-ink/20 focus:border-forest-500 focus:ring-forest-500/20'
        }`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-clay-500">{error}</p>}
    </div>
  )
}

export function Select({ label, options, error, ...props }) {
  const id = props.id || props.name
  return (
    <div className="mb-4">
      {label && <label htmlFor={id} className="block text-sm font-medium text-ink mb-1">{label}</label>}
      <select
        id={id}
        className={`w-full px-3 py-2 rounded border bg-surface text-ink transition-colors ${
          error ? 'border-clay-500 focus:border-clay-500 focus:ring-clay-500/20' : 'border-ink/20 focus:border-forest-500 focus:ring-forest-500/20'
        }`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-clay-500">{error}</p>}
    </div>
  )
}

export function Textarea({ label, error, rows = 3, ...props }) {
  const id = props.id || props.name
  return (
    <div className="mb-4">
      {label && <label htmlFor={id} className="block text-sm font-medium text-ink mb-1">{label}</label>}
      <textarea
        id={id}
        rows={rows}
        className={`w-full px-3 py-2 rounded border bg-surface text-ink placeholder-ink-muted transition-colors resize-none ${
          error ? 'border-clay-500 focus:border-clay-500 focus:ring-clay-500/20' : 'border-ink/20 focus:border-forest-500 focus:ring-forest-500/20'
        }`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-clay-500">{error}</p>}
    </div>
  )
}

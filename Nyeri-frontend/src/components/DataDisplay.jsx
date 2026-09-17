import { useState } from 'react'
import { ChevronRight, ChevronLeft, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

export function Table({ columns, rows, keyField = 'id', renderRow }) {
  if (!rows || rows.length === 0) {
    return <div className="py-10 text-center text-sm text-ink-muted">No records match your filters.</div>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-ink-muted">
            {columns.map((c) => (
              <th key={c} className="py-2.5 pr-4 font-medium whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[keyField]} className="border-b border-line last:border-0 hover:bg-forest-50/40">
              {renderRow(row)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 border-b border-line overflow-x-auto">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
            active === t ? 'border-forest-700 text-forest-700' : 'border-transparent text-ink-muted hover:text-ink'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

export function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-between pt-4">
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="inline-flex items-center gap-1 text-sm text-ink-muted disabled:opacity-40 hover:text-ink"
      >
        <ChevronLeft size={16} /> Previous
      </button>
      <span className="text-sm text-ink-muted">Page {page} of {totalPages}</span>
      <button
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
        className="inline-flex items-center gap-1 text-sm text-ink-muted disabled:opacity-40 hover:text-ink"
      >
        Next <ChevronRight size={16} />
      </button>
    </div>
  )
}

export function usePagination(items, pageSize = 8) {
  const [page, setPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))
  const pageItems = items.slice((page - 1) * pageSize, page * pageSize)
  return { page, setPage, totalPages, pageItems }
}

export function Breadcrumbs({ items }) {
  return (
    <nav className="flex items-center gap-1.5 text-sm text-ink-muted mb-4">
      <Link to="/" className="hover:text-ink"><Home size={14} /></Link>
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <ChevronRight size={14} className="text-ink-faint" />
          {item.to ? (
            <Link to={item.to} className="hover:text-ink">{item.label}</Link>
          ) : (
            <span className="text-ink">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}

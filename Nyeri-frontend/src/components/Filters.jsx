import { Search, SlidersHorizontal } from 'lucide-react'

export function SearchBar({ value, onChange, placeholder = 'Search…', size = 'md' }) {
  const sizes = { md: 'py-2.5 text-sm', lg: 'py-4 text-base' }
  return (
    <div className="relative w-full">
      <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full rounded-md border border-line bg-white pl-11 pr-4 ${sizes[size]} outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600`}
      />
    </div>
  )
}

export function Select({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-ink-muted text-xs">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-line bg-white px-3 py-2 text-sm outline-none focus:border-forest-600"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  )
}

export function FilterBar({ children }) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border border-line bg-white p-4">
      <SlidersHorizontal size={16} className="hidden sm:block text-ink-faint mb-2" />
      {children}
    </div>
  )
}

import { useState } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import { Menu, X, Landmark, Shield } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/leaders', label: 'Leaders' },
  { to: '/county', label: 'County' },
  { to: '/constituencies', label: 'Constituencies' },
  { to: '/accountability', label: 'Accountability' },
  { to: '/anomalies', label: 'Anomalies' },
  { to: '/reports', label: 'Reports' },
  { to: '/assistant', label: 'AI Assistant' },
  { to: '/about', label: 'About' },
]

export default function PublicLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 bg-paper/95 backdrop-blur border-b border-line">
        <div className="max-w-content mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <span className="flex h-8 w-8 items-center justify-center rounded bg-forest-700 text-white">
              <Landmark size={16} />
            </span>
            <span className="font-serif font-semibold text-ink leading-tight text-[15px]">
              Nyeri Accountability<span className="block text-[11px] font-sans font-normal text-ink-muted -mt-0.5">Governance Platform</span>
            </span>
          </Link>

          <nav className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-2 rounded text-sm font-medium transition-colors ${
                    isActive ? 'text-forest-700 bg-forest-50' : 'text-ink-muted hover:text-ink'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden lg:flex items-center">
            <Link to="/admin/login" className="text-sm text-ink-muted hover:text-ink flex items-center gap-1.5">
              <Shield size={14} /> Admin
            </Link>
          </div>

          <button className="lg:hidden p-2 text-ink" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {open && (
          <nav className="lg:hidden border-t border-line bg-paper px-4 py-3 flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `px-3 py-2.5 rounded text-sm font-medium ${isActive ? 'text-forest-700 bg-forest-50' : 'text-ink-muted'}`
                }
              >
                {item.label}
              </NavLink>
            ))}
            <Link to="/admin/login" className="px-3 py-2.5 text-sm text-ink-muted flex items-center gap-1.5">
              <Shield size={14} /> Admin
            </Link>
          </nav>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <Footer />
    </div>
  )
}

function Footer() {
  return (
    <footer className="border-t border-line bg-white mt-20">
      <div className="max-w-content mx-auto px-4 sm:px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="col-span-2">
          <p className="font-serif font-semibold text-ink mb-2">Nyeri Accountability Platform</p>
          <p className="text-sm text-ink-muted max-w-sm">
            An independent civic-technology project making Nyeri County's public financial records
            easier to find, understand and investigate. Not affiliated with the county government.
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-3">Platform</p>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li><Link to="/accountability" className="hover:text-ink">Accountability Dashboard</Link></li>
            <li><Link to="/anomalies" className="hover:text-ink">Anomalies</Link></li>
            <li><Link to="/reports" className="hover:text-ink">Reports</Link></li>
            <li><Link to="/assistant" className="hover:text-ink">AI Assistant</Link></li>
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-3">Sources</p>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>Office of the Auditor-General</li>
            <li>National Treasury / NG-CDF Board</li>
            <li>Nyeri County Fiscal Reports</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line py-4 text-center text-xs text-ink-faint">
        Built as a final-year civic-technology project. Data indicators require independent verification.
      </div>
    </footer>
  )
}

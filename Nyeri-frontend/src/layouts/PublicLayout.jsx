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
      <header className="sticky top-0 z-30 bg-ink backdrop-blur border-b border-line/50">
        <div className="max-w-content mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <span className="flex h-8 w-8 items-center justify-center rounded bg-forest-700 text-white">
              <Landmark size={16} />
            </span>
            <span className="font-serif font-semibold text-white leading-tight text-[15px]">
              Nyeri Accountability<span className="block text-[11px] font-sans font-normal text-white/60 -mt-0.5">Governance Platform</span>
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
                    isActive ? 'text-forest-700 bg-forest-50/30' : 'text-white/60 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden lg:flex items-center">
            <Link to="/admin/login" className="text-sm text-white/60 hover:text-white flex items-center gap-1.5">
              <Shield size={14} /> Admin
            </Link>
          </div>

          <button className="lg:hidden p-2 text-white/60" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {open && (
          <nav className="lg:hidden border-t border-line/50 bg-ink/50 px-4 py-3 flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `px-3 py-2.5 rounded text-sm font-medium ${isActive ? 'text-forest-700 bg-forest-50/30' : 'text-white/60'}`
                }
              >
                {item.label}
              </NavLink>
            ))}
            <Link to="/admin/login" className="px-3 py-2.5 text-sm text-white/60 flex items-center gap-1.5">
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
    <footer className="border-t border-line/50 bg-ink mt-20">
      <div className="max-w-content mx-auto px-4 sm:px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="col-span-2">
          <p className="font-serif font-semibold text-white mb-2">Nyeri Accountability Platform</p>
          <p className="text-sm text-white/60 max-w-sm">
            An independent civic-technology project making Nyeri County's public financial records
            easier to find, understand and investigate. Not affiliated with the county government.
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/30 mb-3">Platform</p>
          <ul className="space-y-2 text-sm text-white/60">
            <li><Link to="/accountability" className="hover:text-white">Accountability Dashboard</Link></li>
            <li><Link to="/anomalies" className="hover:text-white">Anomalies</Link></li>
            <li><Link to="/reports" className="hover:text-white">Reports</Link></li>
            <li><Link to="/assistant" className="hover:text-white">AI Assistant</Link></li>
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/30 mb-3">Sources</p>
          <ul className="space-y-2 text-sm text-white/60">
            <li>Office of the Auditor-General</li>
            <li>National Treasury / NG-CDF Board</li>
            <li>Nyeri County Fiscal Reports</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line/50 py-4 text-center text-xs text-white/30">
        Built as a final-year civic-technology project. Data indicators require independent verification.
      </div>
    </footer>
  )
}

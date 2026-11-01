import { useState, useRef, useEffect } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import { Menu, X, Landmark, Shield, ChevronDown, Users, Building2, FileText, Cpu, Sparkles } from 'lucide-react'

// Navigation structure with dropdown groups
const navGroups = [
  {
    label: 'Home',
    to: '/',
    icon: null,
    isSingle: true,
  },
  {
    label: 'Leaders',
    icon: Users,
    items: [
      { to: '/leaders', label: 'All Leaders' },
      { to: '/county', label: 'County Government' },
      { to: '/constituencies', label: 'Constituencies' },
    ],
  },
  {
    label: 'Analysis',
    icon: FileText,
    items: [
      { to: '/accountability', label: 'Accountability Dashboard' },
      { to: '/anomalies', label: 'Anomalies' },
      { to: '/reports', label: 'Reports' },
    ],
  },
  {
    label: 'Tools',
    icon: Cpu,
    items: [
      { to: '/assistant', label: 'AI Assistant' },
      { to: '/about', label: 'About' },
    ],
  },
]

function Dropdown({ group, isMobile = false }) {
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Close dropdown when clicking outside (desktop only)
  useEffect(() => {
    if (!isMobile) {
      const handleClickOutside = (e) => {
        if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
          setOpen(false)
        }
      }
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isMobile])

  if (group.isSingle) {
    return (
      <NavLink
        to={group.to}
        end={group.to === '/'}
        className={({ isActive }) =>
          `px-3 py-2 rounded text-sm font-medium transition-colors ${
            isActive ? 'text-forest-700 bg-forest-50/30' : 'text-white/60 hover:text-white'
          }`
        }
      >
        {group.label}
      </NavLink>
    )
  }

  const Icon = group.icon

  return (
    <div ref={dropdownRef} className="relative" onMouseEnter={() => !isMobile && setOpen(true)} onMouseLeave={() => !isMobile && setOpen(false)}>
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium transition-colors ${
          isMobile ? 'w-full text-left text-white/60 hover:text-white' : 'text-white/60 hover:text-white'
        }`}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Icon size={14} className="text-white/60" />
        {group.label}
        <ChevronDown size={12} className={`text-white/60 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className={`absolute top-full left-0 mt-1 min-w-[180px] rounded-lg bg-ink border border-line/50 shadow-lg py-1 z-40 ${isMobile ? 'static w-full bg-ink/50 border-t border-line/50 shadow-none mt-0' : ''}`}>
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block px-4 py-2.5 text-sm transition-colors ${
                  isActive ? 'text-forest-700 bg-forest-50/30' : 'text-white/60 hover:text-white hover:bg-white/5'
                }${isMobile ? ' rounded-none' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PublicLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)

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

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1">
            {navGroups.map((group) => (
              <Dropdown key={group.label} group={group} isMobile={false} />
            ))}
          </nav>

          <div className="hidden lg:flex items-center">
            <Link to="/admin/login" className="text-sm text-white/60 hover:text-white flex items-center gap-1.5">
              <Shield size={14} /> Admin
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button className="lg:hidden p-2 text-white/60" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileOpen && (
          <nav className="lg:hidden border-t border-line/50 bg-ink/50 px-4 py-3 flex flex-col gap-1">
            {navGroups.map((group) => (
              <Dropdown
                key={group.label}
                group={group}
                isMobile={true}
              />
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
import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Users, MapPin, Wallet, ClipboardList, FileWarning,
  Building2, UploadCloud, ShieldCheck, BrainCircuit, Settings, LogOut, Landmark,
} from 'lucide-react'

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/leaders', label: 'Leaders', icon: Users },
  { to: '/admin/constituencies', label: 'Constituencies', icon: MapPin },
  { to: '/admin/financial-data', label: 'Financial Data', icon: Wallet },
  { to: '/admin/allocations', label: 'Allocations', icon: ClipboardList },
  { to: '/admin/audit-findings', label: 'Audit Findings', icon: FileWarning },
  { to: '/admin/departmental-data', label: 'Departmental Data', icon: Building2 },
  { to: '/admin/upload', label: 'Dataset Upload', icon: UploadCloud },
  { to: '/admin/validation', label: 'Data Validation', icon: ShieldCheck },
  { to: '/admin/model', label: 'AI/ML Model', icon: BrainCircuit },
  { to: '/admin/system', label: 'System Management', icon: Settings },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex bg-paper">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-line bg-forest-800 text-white">
        <div className="flex items-center gap-2 px-5 h-16 border-b border-white/10">
          <span className="flex h-8 w-8 items-center justify-center rounded bg-white/10">
            <Landmark size={16} />
          </span>
          <span className="font-serif font-semibold text-sm leading-tight">
            Nyeri Platform<span className="block text-[11px] font-sans font-normal text-white/60">Admin</span>
          </span>
        </div>
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium transition-colors ${
                  isActive ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <Icon size={16} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t border-white/10">
          <button
            onClick={() => navigate('/admin/login')}
            className="flex w-full items-center gap-3 px-3 py-2.5 rounded text-sm font-medium text-white/70 hover:bg-white/5 hover:text-white"
          >
            <LogOut size={16} /> Log out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-line/50 bg-ink flex items-center justify-between px-4 sm:px-6">
          <Link to="/" className="text-sm text-white/60 hover:text-white">&larr; Back to public site</Link>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 text-xs font-semibold">
              AD
            </div>
            <span className="text-sm text-white/60 hidden sm:block">Admin User</span>
          </div>
        </header>
        <main className="flex-1 p-4 sm:p-6 max-w-[1400px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

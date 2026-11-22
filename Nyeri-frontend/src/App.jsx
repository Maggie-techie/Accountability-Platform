import { Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import PublicLayout from './layouts/PublicLayout'
import AdminLayout from './layouts/AdminLayout'

import Home from './pages/Home'
import Leaders from './pages/Leaders'
import LeaderProfile from './pages/LeaderProfile'
import CountyDashboard from './pages/CountyDashboard'
import Constituencies from './pages/Constituencies'
import ConstituencyProfile from './pages/ConstituencyProfile'
import AccountabilityDashboard from './pages/AccountabilityDashboard'
import Anomalies from './pages/Anomalies'
import AnomalyDetails from './pages/AnomalyDetails'
import Reports from './pages/Reports'
import About from './pages/About'

import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminDataManagement from './pages/admin/AdminDataManagement'
import DatasetUpload from './pages/admin/DatasetUpload'
import DataValidation from './pages/admin/DataValidation'
import AIModelManagement from './pages/admin/AIModelManagement'
import SystemManagement from './pages/admin/SystemManagement'

// Lazy-load heavy pages (AI Assistant has model dependencies)
const AIAssistant = lazy(() => import('./pages/AIAssistant'))

function PageFallback() {
  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-16 text-center">
      <div className="animate-pulse flex items-center justify-center gap-2 text-forest-700">
        <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="text-lg font-medium">Loading AI Assistant…</span>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/leaders" element={<Leaders />} />
        <Route path="/leaders/:slug" element={<LeaderProfile />} />
        <Route path="/county" element={<CountyDashboard />} />
        <Route path="/constituencies" element={<Constituencies />} />
        <Route path="/constituencies/:slug" element={<ConstituencyProfile />} />
        <Route path="/accountability" element={<AccountabilityDashboard />} />
        <Route path="/anomalies" element={<Anomalies />} />
        <Route path="/anomalies/:id" element={<AnomalyDetails />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/assistant" element={
          <Suspense fallback={<PageFallback />}>
            <AIAssistant />
          </Suspense>
        } />
        <Route path="/about" element={<About />} />
      </Route>

      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="leaders" element={<AdminDataManagement entity="leaders" />} />
        <Route path="constituencies" element={<AdminDataManagement entity="constituencies" />} />
        <Route path="financial-data" element={<AdminDataManagement entity="financial" />} />
        <Route path="allocations" element={<AdminDataManagement entity="allocations" />} />
        <Route path="audit-findings" element={<AdminDataManagement entity="audit" />} />
        <Route path="departmental-data" element={<AdminDataManagement entity="departments" />} />
        <Route path="upload" element={<DatasetUpload />} />
        <Route path="validation" element={<DataValidation />} />
        <Route path="model" element={<AIModelManagement />} />
        <Route path="system" element={<SystemManagement />} />
      </Route>
    </Routes>
  )
}

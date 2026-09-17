import { Routes, Route } from 'react-router-dom'
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
import AIAssistant from './pages/AIAssistant'
import About from './pages/About'

import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminDataManagement from './pages/admin/AdminDataManagement'
import DatasetUpload from './pages/admin/DatasetUpload'
import DataValidation from './pages/admin/DataValidation'
import AIModelManagement from './pages/admin/AIModelManagement'
import SystemManagement from './pages/admin/SystemManagement'

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
        <Route path="/assistant" element={<AIAssistant />} />
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

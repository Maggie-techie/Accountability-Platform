import { useMemo, useState, useEffect, useCallback } from 'react'
import { Pencil, Trash2, Eye, Plus, X, Loader2 } from 'lucide-react'
import { Card, Badge, Button, Input, Select, Modal, Toast } from '../../components/ui'
import { SearchBar } from '../../components/Filters'
import { Pagination, Table, usePagination } from '../../components/DataDisplay'
import { useSharedAsyncData } from '../../hooks/useAsyncData'
import APIService from '../../services/api'

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const configs = {
  leaders: { title: 'Leaders', singular: 'Leader' },
  constituencies: { title: 'Constituencies', singular: 'Constituency' },
  financial: { title: 'County Finances', singular: 'Finance Record' },
  allocations: { title: 'NG-CDF Allocations', singular: 'Allocation' },
  audit: { title: 'Audit Findings', singular: 'Audit Finding' },
  departments: { title: 'Departmental Data', singular: 'Department' },
}

// Backend paths per entity. NOTE: trailing slashes match Flask routes that are
// defined with '/', which avoids the 308 redirect that breaks CORS preflights.
const endpoints = {
  constituencies: '/constituency/',
  financial: '/governor/finances',
  allocations: '/constituency/allocations',
  audit: '/governor/audit',
  departments: '/governor/departments',
}

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------
// The API wraps payloads as { success, data }.
const unwrap = (json) =>
  json && typeof json === 'object' && !Array.isArray(json) && 'data' in json ? json.data : json

// Always return an array, whatever shape the backend sends.
const toArray = (value, ...keys) => {
  if (Array.isArray(value)) return value
  for (const key of keys) {
    if (Array.isArray(value?.[key])) return value[key]
  }
  return []
}

// Collapse stray newlines/whitespace that come from the source spreadsheets.
const clean = (v) => (v == null || v === '' ? null : String(v).replace(/\s+/g, ' ').trim())

const fmtNum = (n) => {
  const num = Number(n)
  return n == null || n === '' || !Number.isFinite(num) ? '—' : num.toLocaleString()
}

// "Hon. John Kaguchia (UDA)" -> "UDA"
const partyFromName = (name) => {
  const m = /\(([^)]+)\)\s*$/.exec(name ?? '')
  return m ? m[1] : null
}

const stripParty = (name) => (name ? String(name).replace(/\s*\([^)]*\)\s*$/, '') : name)

const scoreTone = (score) => (score >= 70 ? 'good' : score >= 55 ? 'watch' : 'risk')

// ---------------------------------------------------------------------------
// Normalizers: turn whatever the API returns into one predictable row shape
// ---------------------------------------------------------------------------
const normalizeGovernor = (g, i) => ({
  _key: g?.id ?? g?._id ?? g?.slug ?? `gov-${i}`,
  name: g?.name ?? g?.governor ?? g?.governor_name ?? '—',
  position: 'Governor',
  party: g?.party ?? partyFromName(g?.governor) ?? '—',
  place: g?.county ?? '—',
  score: g?.accountabilityScore ?? g?.accountability_score ?? g?.score ?? null,
})

const normalizeConstituency = (c, i) => {
  // Handle mp field that could be string or object { name, party }
  const rawMp = c?.mp ?? c?.mp_name
  const mpName = typeof rawMp === 'object' ? rawMp?.name : rawMp
  const mpParty = typeof rawMp === 'object' ? rawMp?.party : undefined

  return {
    _key: c?.slug ?? c?.constituency_slug ?? c?.id ?? c?._id ?? `const-${i}`,
    name: c?.name ?? c?.constituency ?? '—',
    mp: stripParty(mpName) ?? '—',
    party: c?.party ?? mpParty ?? partyFromName(mpName) ?? '—',
    county: c?.county ?? 'Nyeri',
    auditStatus: c?.auditStatus ?? c?.audit_status ?? 'Qualified',
    score: c?.accountabilityScore ?? c?.accountability_score ?? c?.score ?? null,
  }
}

const normalizeFinancial = (r, i) => ({
  _key: r?.id ?? r?._id ?? `fin-${i}`,
  fy: clean(r?.fy ?? r?.fy_display ?? r?.financial_year ?? r?.financialYear) ?? 'Unknown',
  // Handle pivoted format from /governor/finances
  budget: r?.budget ?? r?.amountKshb ?? r?.budget_kshb ??
          (r?.equitable_share_kshb ? r.equitable_share_kshb + (r.conditional_grants_kshb || 0) + (r.osr_kshb || 0) : null),
  expenditure: r?.expenditure ?? r?.exp ?? r?.expenditure_kshb ?? r?.total_expenditure_kshb ?? null,
  // Also include pivoted fields for display
  equitableShare: r?.equitable_share_kshb ?? null,
  conditionalGrants: r?.conditional_grants_kshb ?? null,
  osr: r?.osr_kshb ?? null,
  development: r?.development_kshb ?? null,
  recurrent: r?.recurrent_kshb ?? null,
})

const normalizeAudit = (r, i) => ({
  _key: r?.id ?? r?._id ?? `audit-${i}`,
  entity: clean(r?.entity ?? r?.constituency ?? r?.governor ?? r?.county) ?? 'Unknown',
  category: clean(r?.category ?? r?.finding_type) ?? 'Unknown',
  fy: clean(r?.fy_display ?? r?.financial_year ?? r?.financialYear) ?? 'Unknown',
  amount: r?.amount_flagged_kshm ?? r?.amountKshm ?? r?.amount ?? null,
  severity: clean(r?.severity ?? r?.finding_type) ?? '—',
})

const normalizeDepartment = (r, i) => ({
  _key: r?.id ?? r?._id ?? `dept-${i}-${r?.department ?? ''}`,
  department: clean(r?.department) ?? 'Unknown',
  fy: clean(r?.financialYear ?? r?.financial_year ?? r?.fy) ?? 'Unknown',
  budget: r?.approvedBudgetKshm ?? r?.budgetKshm ?? r?.budget_kshm ?? null,
  absorption: r?.absorptionRate ?? r?.absorption_rate ?? null,
  status: clean(r?.status) ?? '—',
})

// Allocations arrive either flat (one row per constituency per FY) or already
// wide (one row per FY). Normalize both into { fy, values: { [constituency]: amount } }.
const META_KEYS = new Set(['_id', 'id', 'fy', 'fy_key', 'fy_display', 'financial_year', 'financialYear'])

// Helper to convert slug to proper constituency name for chart keys
const slugToChartKey = (slug) => {
  const map = {
    'kieni': 'Kieni',
    'mathira': 'Mathira',
    'othaya': 'Othaya',
    'tetu': 'Tetu',
    'mukurweini': 'Mukurwe-ini',
    'nyeri_town': 'Nyeri Town',
  }
  return map[slug] || slug
}

const normalizeAllocations = (rows) => {
  const isFlat = rows.some(
    (r) => (r?.constituency ?? r?.constituency_name ?? r?.constituency_slug) != null && (r?.amount_kshm ?? r?.amountKshm) != null
  )

  if (isFlat) {
    const byFy = new Map()
    rows.forEach((r) => {
      const fy = clean(r?.fy_display ?? r?.fy ?? r?.financial_year ?? r?.fy_key) ?? 'Unknown'
      // Handle both slug and name
      const rawName = clean(r?.constituency ?? r?.constituency_name ?? r?.constituency_slug) ?? 'Unknown'
      const name = slugToChartKey(rawName)
      const amount = r?.amount_kshm ?? r?.amountKshm
      if (!byFy.has(fy)) byFy.set(fy, { _key: fy, fy, values: {} })
      byFy.get(fy).values[name] = amount
    })
    return [...byFy.values()].sort((a, b) => String(b.fy).localeCompare(String(a.fy)))
  }

  return rows.map((r, i) => ({
    _key: r?.id ?? r?._id ?? r?.fy ?? `alloc-${i}`,
    fy: clean(r?.fy ?? r?.fy_display ?? r?.financial_year) ?? 'Unknown',
    values: Object.fromEntries(Object.entries(r ?? {}).filter(([k]) => !META_KEYS.has(k))),
  }))
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
// Keying by entity remounts the inner component when the tab changes, so rows
// fetched for one entity are never rendered with another entity's renderer.
export default function AdminDataManagement({ entity }) {
  return <AdminDataManagementInner key={entity} entity={entity} />
}

function AdminDataManagementInner({ entity }) {
  const config = configs[entity]
  const title = config?.title ?? 'Data'
  const singularTitle = config?.singular ?? 'Record'
  const lowerTitle = title.toLowerCase()

  // CRUD modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [isViewModalOpen, setIsViewModalOpen] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [formData, setFormData] = useState({})
  const [formErrors, setFormErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [toasts, setToasts] = useState([])
  const [searchQuery, setSearchQuery] = useState('')

  // Use shared async data hook with 10-minute cache (matching backend TTL)
  // Leaders entity is special - fetches from multiple endpoints
  const cacheKey = `admin-${entity}`
  const { data, isLoading, error, refresh } = useSharedAsyncData(cacheKey, async () => {
    // Leaders: fetch governor + constituencies + scores
    if (entity === 'leaders') {
      const token = localStorage.getItem('authToken')
      const headers = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      const getJson = async (path) => {
        const res = await fetch(`${APIService.baseURL}${path}`, { headers })
        if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`)
        return unwrap(await res.json())
      }

      const [govResult, constResult, govScoreResult] = await Promise.allSettled([
        getJson('/governor/'),
        getJson('/constituency/'),
        getJson('/governor/score'),
      ])

      if (govResult.status === 'rejected' && constResult.status === 'rejected') {
        throw govResult.reason
      }

      let governors = []
      let governorScore = null
      if (govResult.status === 'fulfilled') {
        const v = govResult.value
        const govData = v?.data ?? v
        governors = toArray(govData, 'governors', 'governor')
        if (governors.length === 0 && govData && typeof govData === 'object' && !Array.isArray(govData) && Object.keys(govData).length) {
          governors = [govData]
        }
      }

      if (govScoreResult.status === 'fulfilled') {
        const v = govScoreResult.value
        const scoreData = v?.data ?? v
        governorScore = scoreData?.score ?? null
      }

      let constituencies = []
      if (constResult.status === 'fulfilled') {
        const v = constResult.value
        const constData = v?.data ?? v
        constituencies = toArray(constData, 'constituencies', 'data', 'results') || []
        if (constituencies.length === 0 && Array.isArray(constData)) {
          constituencies = constData
        }
      }

      // Fetch MP scores in parallel for each constituency
      const constituencyScores = {}
      if (constituencies.length > 0) {
        const scorePromises = constituencies
          .filter(c => c?.slug)
          .map(c => getJson(`/constituency/${c.slug}/score`)
            .then(res => ({ slug: c.slug, score: (res?.data ?? res)?.score }))
            .catch(() => ({ slug: c.slug, score: null }))
          )
        const scoreResults = await Promise.all(scorePromises)
        scoreResults.forEach(r => {
          if (r.slug && r.score != null) {
            constituencyScores[r.slug] = r.score
          }
        })
      }

      return {
        governors,
        constituencies,
        governorScore,
        constituencyScores
      }
    }

    // Other entities: single endpoint
    const token = localStorage.getItem('authToken')
    const headers = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${APIService.baseURL}${endpoints[entity]}`, { headers })
    if (!res.ok) throw new Error(`${endpoints[entity]} returned HTTP ${res.status}`)

    const json = await res.json()
    return unwrap(json)
  }, { cacheTime: 10 * 60 * 1000 }) // 10 min cache to match backend

  // Post-process data based on entity type
  const processedData = useMemo(() => {
    if (!data) return []

    let rows = []

    if (entity === 'leaders') {
      const { governors, constituencies, governorScore, constituencyScores } = data
      rows = [
        ...governors.map((g, i) => {
          const n = normalizeGovernor(g, i)
          return {
            ...n,
            score: governorScore ?? n.score,
          }
        }),
        ...constituencies.map((c, i) => {
          const n = normalizeConstituency(c, i)
          const fetchedScore = constituencyScores[c?.slug] ?? n.score
          return {
            _key: `mp-${n._key}`,
            name: n.mp,
            position: 'MP',
            party: n.party,
            place: n.name,
            score: fetchedScore,
          }
        }),
      ]
      return rows
    }

    const raw = data
    switch (entity) {
      case 'constituencies':
        rows = toArray(raw, 'constituencies').map(normalizeConstituency)
        break
      case 'financial':
        rows = toArray(raw, 'finances', 'financial_data', 'years').map(normalizeFinancial)
        break
      case 'allocations':
        const allocData = toArray(raw, 'allocations') || (Array.isArray(raw) ? raw : [])
        rows = normalizeAllocations(allocData)
        break
      case 'audit':
        rows = toArray(raw, 'audit_findings', 'findings').map(normalizeAudit)
        break
      case 'departments':
        rows = toArray(raw, 'departments').map(normalizeDepartment)
        break
      default:
        return []
    }
    return rows
  }, [data, entity])

  const retry = useCallback(() => refresh(), [refresh])

  // Toast helpers
  const showToast = useCallback((type, message) => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, type, message }])
    if (type !== 'error') {
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
    }
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // Get empty form state for each entity type
  const getEmptyForm = useCallback((entity) => {
    const forms = {
      constituencies: { name: '', county: 'Nyeri', slug: '' },
      financial: { fy: '', equitable_share_kshb: '', conditional_grants_kshb: '', osr_kshb: '', expenditure_kshb: '', development_kshb: '', recurrent_kshb: '' },
      allocations: { fy: '', constituency: '', amount_kshm: '' },
      audit: { entity: '', category: '', fy: '', amount_flagged_kshm: '', severity: 'Medium', finding_type: 'Misappropriation' },
      departments: { department: '', financial_year: '', approved_budget_kshm: '', absorption_rate: '', status: 'On Track' },
    }
    return forms[entity] || {}
  }, [])

  // Normalize form data for API
  const normalizeFormForApi = useCallback((entity, data, isUpdate = false) => {
    const normalized = { ...data }
    switch (entity) {
      case 'constituencies':
        if (!isUpdate) {
          normalized.slug = data.name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
        }
        break
      case 'financial':
        // Convert to numbers
        ;['equitable_share_kshb', 'conditional_grants_kshb', 'osr_kshb', 'expenditure_kshb', 'development_kshb', 'recurrent_kshb'].forEach(k => {
          if (normalized[k]) normalized[k] = parseFloat(normalized[k])
        })
        break
      case 'allocations':
        normalized.amount_kshm = parseFloat(normalized.amount_kshm)
        break
      case 'audit':
        normalized.amount_flagged_kshm = parseFloat(normalized.amount_flagged_kshm)
        break
      case 'departments':
        normalized.approved_budget_kshm = parseFloat(normalized.approved_budget_kshm)
        normalized.absorption_rate = parseFloat(normalized.absorption_rate)
        break
    }
    return normalized
  }, [])

  // Validate form
  const validateForm = useCallback((entity, data) => {
    const errors = {}
    switch (entity) {
      case 'constituencies':
        if (!data.name?.trim()) errors.name = 'Name is required'
        break
      case 'financial':
        if (!data.fy?.trim()) errors.fy = 'Financial year is required'
        break
      case 'allocations':
        if (!data.fy?.trim()) errors.fy = 'Financial year is required'
        if (!data.constituency?.trim()) errors.constituency = 'Constituency is required'
        if (!data.amount_kshm) errors.amount_kshm = 'Amount is required'
        break
      case 'audit':
        if (!data.entity?.trim()) errors.entity = 'Entity is required'
        if (!data.category?.trim()) errors.category = 'Category is required'
        if (!data.fy?.trim()) errors.fy = 'Financial year is required'
        break
      case 'departments':
        if (!data.department?.trim()) errors.department = 'Department is required'
        if (!data.financial_year?.trim()) errors.financial_year = 'Financial year is required'
        break
    }
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }, [])

  // CRUD handlers
  const handleAddClick = useCallback(() => {
    if (entity === 'leaders') {
      showToast('info', 'Leaders data is derived from Governor and Constituencies. Edit those entities directly.')
      return
    }
    setFormData(getEmptyForm(entity))
    setFormErrors({})
    setIsAddModalOpen(true)
  }, [entity, getEmptyForm, showToast])

  const handleViewClick = useCallback((record) => {
    setSelectedRecord(record)
    setIsViewModalOpen(true)
  }, [])

  const handleEditClick = useCallback((record) => {
    if (entity === 'leaders') {
      showToast('info', 'Leaders data is derived from Governor and Constituencies. Edit those entities directly.')
      return
    }
    setSelectedRecord(record)
    // Pre-populate form with record data
    const formValues = { ...record }
    // Remove internal keys
    delete formValues._key
    setFormData(formValues)
    setFormErrors({})
    setIsEditModalOpen(true)
  }, [entity, showToast])

  const handleDeleteClick = useCallback((record) => {
    if (entity === 'leaders') {
      showToast('info', 'Leaders data is derived from Governor and Constituencies. Edit those entities directly.')
      return
    }
    setSelectedRecord(record)
    setIsDeleteModalOpen(true)
  }, [entity, showToast])

  const handleFormChange = useCallback((e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
    // Clear error for this field
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: null }))
    }
  }, [formErrors])

  const handleFormSubmit = useCallback(async (e) => {
    e.preventDefault()
    if (!validateForm(entity, formData)) return

    setSubmitting(true)
    const normalizedData = normalizeFormForApi(entity, formData, isEditModalOpen)

    try {
      let result
      if (isEditModalOpen && selectedRecord) {
        // Update
        switch (entity) {
          case 'constituencies':
            result = await APIService.updateConstituency(selectedRecord._key, normalizedData)
            break
          case 'financial':
            result = await APIService.updateFinance(selectedRecord._key, normalizedData)
            break
          case 'allocations':
            result = await APIService.updateAllocation(selectedRecord._key, normalizedData)
            break
          case 'audit':
            result = await APIService.updateCountyAuditFinding(selectedRecord._key, normalizedData)
            break
          case 'departments':
            result = await APIService.updateDepartment(selectedRecord._key, normalizedData)
            break
        }
        showToast('success', 'Record updated successfully')
      } else {
        // Create
        switch (entity) {
          case 'constituencies':
            result = await APIService.createConstituency(normalizedData)
            break
          case 'financial':
            result = await APIService.createFinance(normalizedData)
            break
          case 'allocations':
            result = await APIService.createAllocation(normalizedData)
            break
          case 'audit':
            result = await APIService.createCountyAuditFinding(normalizedData)
            break
          case 'departments':
            result = await APIService.createDepartment(normalizedData)
            break
        }
        showToast('success', 'Record created successfully')
      }

      // Close modals and refresh data
      setIsAddModalOpen(false)
      setIsEditModalOpen(false)
      setSelectedRecord(null)
      setFormData({})
      setReloadKey(k => k + 1)
    } catch (err) {
      console.error(`Error ${isEditModalOpen ? 'updating' : 'creating'} ${entity}:`, err)
      showToast('error', `Failed to ${isEditModalOpen ? 'update' : 'create'} record: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }, [entity, formData, isEditModalOpen, selectedRecord, normalizeFormForApi, validateForm, showToast])

  const handleDeleteConfirm = useCallback(async () => {
    if (!selectedRecord) return

    setSubmitting(true)
    try {
      switch (entity) {
        case 'constituencies':
          await APIService.deleteConstituency(selectedRecord._key)
          break
        case 'financial':
          await APIService.deleteFinance(selectedRecord._key)
          break
        case 'allocations':
          await APIService.deleteAllocation(selectedRecord._key)
          break
        case 'audit':
          await APIService.deleteCountyAuditFinding(selectedRecord._key)
          break
        case 'departments':
          await APIService.deleteDepartment(selectedRecord._key)
          break
      }
      showToast('success', 'Record deleted successfully')
      setIsDeleteModalOpen(false)
      setSelectedRecord(null)
      setReloadKey(k => k + 1)
    } catch (err) {
      console.error(`Error deleting ${entity}:`, err)
      showToast('error', `Failed to delete record: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }, [entity, selectedRecord, showToast])

  const closeAllModals = useCallback(() => {
    setIsAddModalOpen(false)
    setIsEditModalOpen(false)
    setIsDeleteModalOpen(false)
    setIsViewModalOpen(false)
    setSelectedRecord(null)
    setFormData({})
    setFormErrors({})
  }, [])

  // Form rendering per entity (moved inside component for access to hooks/state)
  const renderFormFields = useCallback((entity) => {
    // Helper to get field-specific props
    const fieldProps = (name) => ({
      onChange: handleFormChange,
      error: formErrors[name]
    })

    // Leaders entity is read-only (derived from governor + constituencies)
    if (entity === 'leaders') {
      return <p className="text-ink-muted">Leaders data is derived from Governor and Constituencies. Edit those entities directly to modify leader information.</p>
    }

    switch (entity) {
      case 'constituencies':
        return (
          <>
            <Input label="Constituency Name" name="name" value={formData.name} {...fieldProps('name')} placeholder="e.g., Kieni" />
            <Input label="County" name="county" value={formData.county} {...fieldProps('county')} placeholder="Nyeri" />
            {!isEditModalOpen && (
              <Input label="Slug (auto-generated)" name="slug" value={formData.slug} readOnly {...fieldProps('slug')} placeholder="Auto-generated from name" />
            )}
          </>
        )

      case 'financial':
        return (
          <>
            <Input label="Financial Year" name="fy" value={formData.fy} {...fieldProps('fy')} placeholder="e.g., 2023/2024" />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Equitable Share (KSh Billions)" name="equitable_share_kshb" type="number" step="0.1" value={formData.equitable_share_kshb} {...fieldProps('equitable_share_kshb')} placeholder="e.g., 8.5" />
              <Input label="Conditional Grants (KSh Billions)" name="conditional_grants_kshb" type="number" step="0.1" value={formData.conditional_grants_kshb} {...fieldProps('conditional_grants_kshb')} placeholder="e.g., 1.2" />
              <Input label="Own Source Revenue (KSh Billions)" name="osr_kshb" type="number" step="0.1" value={formData.osr_kshb} {...fieldProps('osr_kshb')} placeholder="e.g., 0.8" />
              <Input label="Total Expenditure (KSh Billions)" name="expenditure_kshb" type="number" step="0.1" value={formData.expenditure_kshb} {...fieldProps('expenditure_kshb')} placeholder="e.g., 9.2" />
              <Input label="Development (KSh Billions)" name="development_kshb" type="number" step="0.1" value={formData.development_kshb} {...fieldProps('development_kshb')} placeholder="e.g., 3.5" />
              <Input label="Recurrent (KSh Billions)" name="recurrent_kshb" type="number" step="0.1" value={formData.recurrent_kshb} {...fieldProps('recurrent_kshb')} placeholder="e.g., 5.7" />
            </div>
          </>
        )

      case 'allocations':
        return (
          <>
            <Input label="Financial Year" name="fy" value={formData.fy} {...fieldProps('fy')} placeholder="e.g., 2023/2024" />
            <Select label="Constituency" name="constituency" value={formData.constituency} {...fieldProps('constituency')} options={[
              { value: 'kieni', label: 'Kieni' },
              { value: 'mathira', label: 'Mathira' },
              { value: 'othaya', label: 'Othaya' },
              { value: 'tetu', label: 'Tetu' },
              { value: 'mukurweini', label: 'Mukurwe-ini' },
              { value: 'nyeri_town', label: 'Nyeri Town' },
            ]} />
            <Input label="Amount (KSh Millions)" name="amount_kshm" type="number" step="0.1" value={formData.amount_kshm} {...fieldProps('amount_kshm')} placeholder="e.g., 125.5" />
          </>
        )

      case 'audit':
        return (
          <>
            <Input label="Entity" name="entity" value={formData.entity} {...fieldProps('entity')} placeholder="e.g., Kieni Constituency" />
            <Select label="Category" name="category" value={formData.category} {...fieldProps('category')} options={[
              { value: 'Misappropriation', label: 'Misappropriation' },
              { value: 'Procurement Irregularity', label: 'Procurement Irregularity' },
              { value: 'Non-compliance', label: 'Non-compliance' },
              { value: 'Other', label: 'Other' },
            ]} />
            <Input label="Financial Year" name="fy" value={formData.fy} {...fieldProps('fy')} placeholder="e.g., 2023/2024" />
            <Input label="Amount Flagged (KSh Millions)" name="amount_flagged_kshm" type="number" step="0.1" value={formData.amount_flagged_kshm} {...fieldProps('amount_flagged_kshm')} placeholder="e.g., 12.5" />
            <Select label="Severity" name="severity" value={formData.severity} {...fieldProps('severity')} options={[
              { value: 'Low', label: 'Low' },
              { value: 'Medium', label: 'Medium' },
              { value: 'High', label: 'High' },
            ]} />
            <Select label="Finding Type" name="finding_type" value={formData.finding_type} {...fieldProps('finding_type')} options={[
              { value: 'Misappropriation', label: 'Misappropriation' },
              { value: 'Procurement', label: 'Procurement' },
              { value: 'Compliance', label: 'Compliance' },
              { value: 'Other', label: 'Other' },
            ]} />
          </>
        )

      case 'departments':
        return (
          <>
            <Input label="Department" name="department" value={formData.department} {...fieldProps('department')} placeholder="e.g., Health Services" />
            <Input label="Financial Year" name="financial_year" value={formData.financial_year} {...fieldProps('financial_year')} placeholder="e.g., 2023/2024" />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Approved Budget (KSh Millions)" name="approved_budget_kshm" type="number" step="0.1" value={formData.approved_budget_kshm} {...fieldProps('approved_budget_kshm')} placeholder="e.g., 250.0" />
              <Input label="Absorption Rate (%)" name="absorption_rate" type="number" step="0.1" min="0" max="100" value={formData.absorption_rate} {...fieldProps('absorption_rate')} placeholder="e.g., 85.5" />
            </div>
            <Select label="Status" name="status" value={formData.status} {...fieldProps('status')} options={[
              { value: 'On Track', label: 'On Track' },
              { value: 'Behind', label: 'Behind' },
              { value: 'At Risk', label: 'At Risk' },
            ]} />
          </>
        )

      default:
        return <p className="text-ink-muted">No form available for this entity type.</p>
    }
  }, [handleFormChange, formErrors, formData, isEditModalOpen])

  // Filter data based on search query
  const filtered = useMemo(() => {
    if (!searchQuery) return processedData
    const needle = searchQuery.toLowerCase()
    return processedData.filter((r) => JSON.stringify(r).toLowerCase().includes(needle))
  }, [processedData, searchQuery])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 8)

  // Constituency columns for the allocations table come from the data itself.
  const allocationCols = useMemo(() => {
    if (entity !== 'allocations') return []
    const names = new Set()
    processedData.forEach((r) => Object.keys(r.values ?? {}).forEach((n) => names.add(n)))
    return [...names].sort()
  }, [entity, processedData])

  const header = (
    <div className="flex items-center justify-between mb-1">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {entity !== 'leaders' && (
        <Button size="sm" onClick={handleAddClick}>
          <Plus size={15} /> Add record
        </Button>
      )}
    </div>
  )

  if (error) {
    return (
      <div>
        {header}
        <p className="text-ink-danger mb-6">{error}</p>
        <button onClick={retry} className="btn btn-outline">
          Try again
        </button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div>
        {header}
        <p className="text-ink-muted mb-6">Loading {lowerTitle}...</p>
      </div>
    )
  }

  return (
    <div>
      {header}
      <p className="text-ink-muted mb-6">Search, review and manage {lowerTitle} records.</p>

      <div className="mb-4 max-w-sm">
        <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder={`Search ${lowerTitle}`} />
      </div>

      {filtered.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm text-ink-muted">
            {processedData.length === 0 ? `No ${lowerTitle} data available.` : `No ${lowerTitle} match "${searchQuery}".`}
          </p>
        </Card>
      ) : (
        <>
          <Card className="p-2">
            <Table
              columns={getColumnsForEntity(entity, allocationCols)}
              rows={pageItems}
              keyField="_key"
              renderRow={(row) => (
                <>
                  {renderCells(entity, row, allocationCols)}
                  <td className="py-3 pr-2 pl-4">
                    <div className="flex gap-1">
                      <IconBtn icon={Eye} label="View" onClick={() => handleViewClick(row)} />
                      <IconBtn icon={Pencil} label="Edit" onClick={() => handleEditClick(row)} />
                      <IconBtn icon={Trash2} label="Delete" danger onClick={() => handleDeleteClick(row)} />
                    </div>
                  </td>
                </>
              )}
            />
          </Card>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}

      {/* Modals */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title={`Add ${singularTitle}`}
        size="lg"
      >
        <form onSubmit={handleFormSubmit} className="space-y-4">
          {renderFormFields(entity)}
          <div className="flex justify-end gap-3 pt-4 border-t border-ink/10">
            <Button type="button" variant="secondary" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting && <Loader2 size={16} className="animate-spin mr-2" />}
              {submitting ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isEditModalOpen}
        onClose={() => { setIsEditModalOpen(false); setSelectedRecord(null); }}
        title={`Edit ${singularTitle}`}
        size="lg"
      >
        <form onSubmit={handleFormSubmit} className="space-y-4">
          {renderFormFields(entity)}
          <div className="flex justify-end gap-3 pt-4 border-t border-ink/10">
            <Button type="button" variant="secondary" onClick={() => { setIsEditModalOpen(false); setSelectedRecord(null); }}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting && <Loader2 size={16} className="animate-spin mr-2" />}
              {submitting ? 'Saving...' : 'Update'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => { setIsDeleteModalOpen(false); setSelectedRecord(null); }}
        title={`Delete ${singularTitle}`}
        size="sm"
      >
        <p className="text-ink-muted mb-6">Are you sure you want to delete this record? This action cannot be undone.</p>
        {selectedRecord && (
          <div className="mb-4 p-3 bg-ink/5 rounded text-sm font-medium text-ink">
            {selectedRecord.name || selectedRecord.fy || selectedRecord.entity || selectedRecord.department || 'Selected record'}
          </div>
        )}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => { setIsDeleteModalOpen(false); setSelectedRecord(null); }}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDeleteConfirm} disabled={submitting}>
            {submitting && <Loader2 size={16} className="animate-spin mr-2" />}
            {submitting ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Modal>

      <Modal
        isOpen={isViewModalOpen}
        onClose={() => { setIsViewModalOpen(false); setSelectedRecord(null); }}
        title={`View ${singularTitle} Details`}
        size="lg"
      >
        {selectedRecord && renderViewDetails(entity, selectedRecord)}
        <div className="flex justify-end pt-4 border-t border-ink/10">
          <Button variant="secondary" onClick={() => { setIsViewModalOpen(false); setSelectedRecord(null); }}>
            Close
          </Button>
        </div>
      </Modal>

      {/* Toasts */}
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          type={toast.type}
          message={toast.message}
          onClose={() => dismissToast(toast.id)}
          duration={toast.type === 'error' ? 0 : 5000}
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Entity-specific table config
// ---------------------------------------------------------------------------
function getColumnsForEntity(entity, allocationCols) {
  switch (entity) {
    case 'leaders':
      return ['Name', 'Position', 'Party', 'Place', 'Score', 'Actions']
    case 'constituencies':
      return ['Name', 'MP', 'County', 'Audit status', 'Score', 'Actions']
    case 'financial':
      return ['Financial Year', 'Equitable Share (KShB)', 'Cond. Grants (KShB)', 'OSR (KShB)', 'Expenditure (KShB)', 'Development (KShB)', 'Recurrent (KShB)', 'Actions']
    case 'allocations':
      return ['Financial Year', ...allocationCols.map((c) => `${c} (KShM)`), 'Actions']
    case 'audit':
      return ['Entity', 'Category', 'FY', 'Amount (KShM)', 'Severity', 'Actions']
    case 'departments':
      return ['Department', 'FY', 'Budget (KShM)', 'Absorption', 'Status', 'Actions']
    default:
      return ['Actions']
  }
}

function ScoreBadge({ score }) {
  if (score == null || Number.isNaN(Number(score))) {
    return <span className="text-ink-muted">—</span>
  }
  return <Badge tone={scoreTone(Number(score))}>{score}</Badge>
}

function renderCells(entity, row, allocationCols) {
  switch (entity) {
    case 'leaders':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.position}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.party}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.place}</td>
          <td className="py-3 pr-4">
            <ScoreBadge score={row.score} />
          </td>
        </>
      )
    case 'constituencies':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.mp}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.county}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.auditStatus}</td>
          <td className="py-3 pr-4">
            <ScoreBadge score={row.score} />
          </td>
        </>
      )
    case 'financial':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.equitableShare)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.conditionalGrants)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.osr)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.expenditure)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.development)}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.recurrent)}</td>
        </>
      )
    case 'allocations':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy}</td>
          {allocationCols.map((name) => (
            <td key={name} className="py-3 pr-4 text-ink-muted">
              {fmtNum(row.values?.[name])}
            </td>
          ))}
        </>
      )
    case 'audit': {
      const sev = String(row.severity ?? '').toLowerCase()
      const tone = sev.includes('high') || sev.includes('misappropriation') ? 'risk' : 'watch'
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.entity}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.category}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.amount)}</td>
          <td className="py-3 pr-4">
            <Badge tone={tone}>{row.severity}</Badge>
          </td>
        </>
      )
    }
    case 'departments':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.department}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.fy}</td>
          <td className="py-3 pr-4 text-ink-muted">{fmtNum(row.budget)}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.absorption == null ? '—' : `${row.absorption}%`}</td>
          <td className="py-3 pr-4">
            <Badge tone={row.status === 'On Track' ? 'good' : row.status === 'Behind' ? 'watch' : 'risk'}>
              {row.status}
            </Badge>
          </td>
        </>
      )
    default:
      return <td colSpan={5}>No data rendering available</td>
  }
}

function IconBtn({ icon: Icon, label, danger, onClick }) {
  return (
    <button
      type="button"
      title={label}
      onClick={onClick}
      className={`p-1.5 rounded hover:bg-ink/5 ${danger ? 'text-clay-500' : 'text-ink-muted'}`}
    >
      <Icon size={14} />
    </button>
  )
}

function renderViewDetails(entity, record) {
  const fields = { ...record }
  delete fields._key

  return (
    <dl className="grid grid-cols-2 gap-4 text-sm">
      {Object.entries(fields).map(([key, value]) => (
        <div key={key} className="col-span-1">
          <dt className="text-ink-muted">{key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</dt>
          <dd className="font-medium text-ink">{value == null || value === '' ? '—' : String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}
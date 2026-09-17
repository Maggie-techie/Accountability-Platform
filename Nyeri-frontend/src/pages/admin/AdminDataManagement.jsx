import { useMemo, useState, useEffect } from 'react'
import { Pencil, Trash2, Eye, Plus } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { SearchBar } from '../../components/Filters'
import { Table, Pagination, usePagination } from '../../components/DataDisplay'
import APIService from '../../services/api'

// Configuration for different entity types
const configs = {
  leaders: {
    title: 'Leaders',
    endpoint: 'leaders', // We'll construct the actual endpoint based on this
    needsAuth: true
  },
  constituencies: {
    title: 'Constituencies',
    endpoint: 'constituencies',
    needsAuth: true
  },
  financial: {
    title: 'County Finances',
    endpoint: 'financial-data',
    needsAuth: true
  },
  allocations: {
    title: 'NG-CDF Allocations',
    endpoint: 'allocations',
    needsAuth: true
  },
  audit: {
    title: 'Audit Findings',
    endpoint: 'audit-findings',
    needsAuth: true
  },
  departments: {
    title: 'Departmental Data',
    endpoint: 'departmental-data',
    needsAuth: true
  }
}

export default function AdminDataManagement({ entity }) {
  const config = configs[entity]
  const [data, setData] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!config) {
        setError('Invalid entity type')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        // Get auth token from localStorage
        const token = localStorage.getItem('authToken')

        // Construct headers with auth token if needed
        const headers = {
          'Content-Type': 'application/json'
        }

        if (config.needsAuth && token) {
          headers['Authorization'] = `Bearer ${token}`
        }

        // Map entity to actual API endpoints
        let apiEndpoint = ''
        switch (entity) {
          case 'leaders':
            // For leaders, we need to get both governor and constituencies
            const [governorRes, constituenciesRes] = await Promise.all([
              fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/governor/governor`, { headers }),
              fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}/constituency/`, { headers })
            ])

            const governorData = await governorRes.json()
            const constituenciesData = await constituenciesRes.json()
            const constituenciesList = constituenciesData.constituencies || constituenciesData || []

            // Combine into leaders format
            setData([
              {
                id: governorData.id,
                name: governorData.name,
                position: 'Governor',
                party: governorData.party,
                place: governorData.county,
                score: governorData.accountabilityScore
              },
              ...constituenciesData.map(c => ({
                id: c.slug,
                name: c.mp,
                position: 'MP',
                party: c.party,
                place: c.name,
                score: c.accountabilityScore
              }))
            ])
            return

          case 'constituencies':
            apiEndpoint = '/constituency/'
            break
          case 'financial':
            apiEndpoint = '/governor/governor/finances'
            break
          case 'allocations':
            apiEndpoint = '/constituency/allocations'
            break
          case 'audit':
            apiEndpoint = '/governor/governor/audit'
            break
          case 'departments':
            apiEndpoint = '/governor/governor/departments'
            break
          default:
            setError('Unknown entity type')
            setLoading(false)
            return
        }

        // For non-leaders entities, fetch from the API
        if (apiEndpoint) {
          const res = await fetch(`${APIService.__API_BASE_URL || 'http://localhost:5000/api'}${apiEndpoint}`, { headers })

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`)
          }

          const data = await res.json()

          // Transform data based on entity type
          let transformedData = []
          switch (entity) {
            case 'constituencies':
              transformedData = data.constituencies || data || []
              break
            case 'financial':
              // Transform finances data to match expected format
              // This would need to match what the frontend expects for display
              transformedData = data || []
              break
            case 'allocations':
              transformedData = data.allocations || data || []
              break
            case 'audit':
              transformedData = data.audit_findings || data || []
              break
            case 'departments':
              transformedData = data.departments || data || []
              break
            default:
              transformedData = data || []
          }

          setData(transformedData)
        }

        setError(null)
      } catch (err) {
        console.error(`Error fetching ${entity} data:`, err)
        setError(`Failed to load ${config.title.toLowerCase()}: ${err.message}`)
        setData([]) // Clear data on error
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [entity, config])

  // Handle loading and error states
  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-semibold">{config.title}</h1>
          <Button size="sm"><Plus size={15} /> Add record</Button>
        </div>
        <p className="text-ink-muted mb-6">Loading {config.title.toLowerCase()}...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-semibold">{config.title}</h1>
          <Button size="sm"><Plus size={15} /> Add record</Button>
        </div>
        <p className="text-ink-danger mb-6">{error}</p>
        <div className="mt-4">
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  // If we have no data, show empty state
  if (data.length === 0) {
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-semibold">{config.title}</h1>
          <Button size="sm"><Plus size={15} /> Add record</Button>
        </div>
        <p className="text-ink-muted mb-6">No {config.title.toLowerCase()} data available.</p>
      </div>
    )
  }

  const filtered = useMemo(() => {
    if (!q) return data
    return data.filter((r) => JSON.stringify(r).toLowerCase().includes(q.toLowerCase()))
  }, [data, q])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 8)

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-semibold">{config.title}</h1>
        <Button size="sm"><Plus size={15} /> Add record</Button>
      </div>
      <p className="text-ink-muted mb-6">Search, review and manage {config.title.toLowerCase()} records.</p>

      <div className="mb-4 max-w-sm"><SearchBar value={q} onChange={setQ} placeholder={`Search ${config.title.toLowerCase()}`} /></div>

      <Card className="p-2">
        <Table
          columns={getColumnsForEntity(entity)}
          rows={pageItems}
          keyField={getKeyFieldForEntity(entity)}
          renderRow={(row) => (
            <>
              {getRenderRowForEntity(entity, row)}
              <td className="py-3 pr-2 pl-4">
                <div className="flex gap-1">
                  <IconBtn icon={Eye} label="View" />
                  <IconBtn icon={Pencil} label="Edit" />
                  <IconBtn icon={Trash2} label="Delete" danger />
                </div>
              </td>
            </>
          )}
        />
      </div>
      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}

// Helper functions to get entity-specific configurations
function getColumnsForEntity(entity) {
  switch (entity) {
    case 'leaders':
      return ['Name', 'Position', 'Party', 'Place', 'Score', 'Actions']
    case 'constituencies':
      return ['Name', 'MP', 'County', 'Audit status', 'Score', 'Actions']
    case 'financial':
      return ['Financial Year', 'Budget (KShB)', 'Expenditure (KShB)', 'Actions']
    case 'allocations':
      return ['Financial Year', 'Kieni', 'Mathira', 'Othaya', 'Tetu', 'Actions']
    case 'audit':
      return ['Entity', 'Category', 'FY', 'Amount (KShM)', 'Severity', 'Actions']
    case 'departments':
      return ['Department', 'FY', 'Budget (KShM)', 'Absorption', 'Status', 'Actions']
    default:
      return ['Actions']
  }
}

function getKeyFieldForEntity(entity) {
  switch (entity) {
    case 'leaders':
      return 'id'
    case 'constituencies':
      return 'slug'
    case 'financial':
      return 'id'
    case 'allocations':
      return 'id'
    case 'audit':
      return 'id'
    case 'departments':
      return 'department'
    default:
      return 'id'
  }
}

function getRenderRowForEntity(entity, row) {
  switch (entity) {
    case 'leaders':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.position}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.party}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.place}</td>
          <td className="py-3 pr-4"><Badge tone={row.score >= 70 ? 'good' : row.score >= 55 ? 'watch' : 'risk'}>{row.score}</Badge></td>
        </>
      )
    case 'constituencies':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.name}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.mp}</td>
          <td className="py-3 pr-4 text-ink-muted">Nyeri</td>
          <td className="py-3 pr-4 text-ink-muted">{row.auditStatus || 'Qualified'}</td>
          <td className="py-3 pr-4"><Badge tone={row.score >= 70 ? 'good' : row.score >= 55 ? 'watch' : 'risk'}>{row.score}</Badge></td>
        </>
      )
    case 'financial':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy || row.financial_year || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.budget || row.amountKshb || 0}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.expenditure || row.exp || 0}</td>
        </>
      )
    case 'allocations':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.fy || row.financial_year || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.Kieni || 0}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.Mathira || 0}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.Othaya || 0}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.Tetu || 0}</td>
        </>
      )
    case 'audit':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.entity || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.category || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.financialYear || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.amountKshm || row.amount || 0}</td>
          <td className="py-3 pr-4"><Badge tone={row.severity === 'High' ? 'risk' : 'watch'}>{row.severity}</Badge></td>
        </>
      )
    case 'departments':
      return (
        <>
          <td className="py-3 pr-4 font-medium text-ink">{row.department || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.financialYear || 'Unknown'}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.approvedBudgetKshm || row.budgetKshm || 0}</td>
          <td className="py-3 pr-4 text-ink-muted">{row.absorptionRate || 0}%</td>
          <td className="py-3 pr-4"><Badge tone={row.status === 'On Track' ? 'good' : row.status === 'Behind' ? 'watch' : 'risk'}>{row.status}</Badge></td>
        </>
      )
    default:
      return <>
        <td colSpan="5">No data rendering available</td>
      </>
  }
}

function IconBtn({ icon: Icon, label, danger }) {
  return (
    <button
      title={label}
      className={`p-1.5 rounded hover:bg-ink/5 ${danger ? 'text-clay-500' : 'text-ink-muted'}`}
    >
      <Icon size={14} />
    </button>
  )
}
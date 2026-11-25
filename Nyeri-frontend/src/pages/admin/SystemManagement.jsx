import { Server, Database, KeyRound, Users2, Activity, Plus, X, Loader2 } from 'lucide-react'
import { Card, Badge, Button, Input, Modal } from '../../components/ui'
import { useState, useEffect, useCallback } from 'react'
import APIService from '../../services/api'

export default function SystemManagement() {
  const [serviceStatus, setServiceStatus] = useState({
    flaskApi: 'Unknown',
    mongodb: 'Unknown',
    aiModelService: 'Unknown'
  })
  const [databaseInfo, setDatabaseInfo] = useState({
    databaseName: 'Unknown',
    collectionsCount: 0,
    totalDocuments: 0
  })
  const [adminUsers, setAdminUsers] = useState([])
  const [securityInfo, setSecurityInfo] = useState({
    jwtSessionLength: 'Long-lived (demo)',
    lastSecretRotation: 'Not yet rotated'
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAddAdminModal, setShowAddAdminModal] = useState(false)
  const [newAdminEmail, setNewAdminEmail] = useState('')
  const [addingAdmin, setAddingAdmin] = useState(false)
  const [addAdminError, setAddAdminError] = useState('')

  const fetchAdminUsers = useCallback(async () => {
    try {
      const response = await APIService.getAdminUsers()
      if (response.success && response.data) {
        setAdminUsers(response.data)
      }
    } catch (err) {
      console.error('Error fetching admin users:', err)
    }
  }, [])

  useEffect(() => {
    const fetchSystemData = async () => {
      try {
        setLoading(true)

        // Fetch service status
        const [flaskResponse, mongodbResponse, aiResponse] = await Promise.all([
          fetch(`${APIService.baseURL}/../health`), // Root health endpoint
          fetch(`${APIService.baseURL}/admin/summary`), // Admin summary for DB info
          fetch(`${APIService.baseURL}/ai/health`) // AI health endpoint
        ])

        // Parse Flask API status
        const flaskApiStatus = flaskResponse.ok ? 'Online' : 'Offline'

        // Parse MongoDB status - if we can get admin summary, MongoDB is working
        const mongodbStatus = mongodbResponse.ok ? 'Online' : 'Offline'

        // Parse AI service status
        const aiData = await aiResponse.json()
        const aiModelServiceStatus = aiResponse.ok && aiData.status === 'healthy' ? 'Online' : 'Offline'

        setServiceStatus({
          flaskApi: flaskApiStatus,
          mongodb: mongodbStatus,
          aiModelService: aiModelServiceStatus
        })

        // Parse database info from admin summary
        if (mongodbResponse.ok) {
          const adminSummary = await mongodbResponse.json()
          if (adminSummary.success && adminSummary.data) {
            const { total_constituencies, total_governors, total_mps, total_allocations, total_audit_findings } = adminSummary.data

            // Calculate total documents (sum of all main collections)
            const totalDocuments = total_constituencies + total_governors + total_mps + total_allocations + total_audit_findings

            setDatabaseInfo({
              databaseName: 'Accountability', // This would normally come from env/config
              collectionsCount: 5, // We know of 5 main collections from the summary
              totalDocuments: totalDocuments
            })
          }
        }

        // Fetch admin users from backend
        await fetchAdminUsers()

        setError(null)
      } catch (err) {
        console.error('Error fetching system management data:', err)
        setError('Failed to load system management data')

        // Set fallback values
        setServiceStatus({
          flaskApi: 'Unknown',
          mongodb: 'Unknown',
          aiModelService: 'Unknown'
        })
        setDatabaseInfo({
          databaseName: 'Unknown',
          collectionsCount: 0,
          totalDocuments: 0
        })
        setAdminUsers([])
      } finally {
        setLoading(false)
      }
    }

    fetchSystemData()
  }, [fetchAdminUsers])

  const handleAddAdmin = async () => {
    if (!newAdminEmail.trim()) {
      setAddAdminError('Email is required')
      return
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(newAdminEmail.trim())) {
      setAddAdminError('Please enter a valid email address')
      return
    }

    setAddingAdmin(true)
    setAddAdminError('')

    try {
      const response = await APIService.createAdminUser(newAdminEmail.trim())
      if (response.success) {
        setShowAddAdminModal(false)
        setNewAdminEmail('')
        await fetchAdminUsers() // Refresh the list
      } else {
        setAddAdminError(response.error || 'Failed to create admin user')
      }
    } catch (err) {
      console.error('Error creating admin user:', err)
      setAddAdminError(err.message || 'Failed to create admin user')
    } finally {
      setAddingAdmin(false)
    }
  }

  const handleDeleteAdmin = async (email) => {
    if (!window.confirm(`Are you sure you want to remove ${email} as an admin user?`)) {
      return
    }

    try {
      const response = await APIService.deleteAdminUser(email)
      if (response.success) {
        await fetchAdminUsers() // Refresh the list
      } else {
        alert(response.error || 'Failed to delete admin user')
      }
    } catch (err) {
      console.error('Error deleting admin user:', err)
      alert(err.message || 'Failed to delete admin user')
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">System management</h1>
        <p className="text-ink-muted mb-6">Loading system data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">System management</h1>
        <p className="text-ink-danger mb-6">{error}</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">System management</h1>
      <p className="text-ink-muted mb-6">Environment, database and access settings.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Server size={16} className="text-ink-faint" /><h3 className="font-semibold">Service status</h3></div>
          <ul className="space-y-3 text-sm">
            <StatusRow label="Flask API" status={serviceStatus.flaskApi} />
            <StatusRow label="MongoDB" status={serviceStatus.mongodb} />
            <StatusRow label="AI model service (Ollama)" status={serviceStatus.aiModelService} />
          </ul>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Database size={16} className="text-ink-faint" /><h3 className="font-semibold">Database</h3></div>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>Database: <span className="text-ink font-medium">{databaseInfo.databaseName}</span></li>
            <li>Collections: <span className="text-ink font-medium">{databaseInfo.collectionsCount}</span></li>
            <li>Total documents: <span className="text-ink font-medium">{databaseInfo.totalDocuments.toLocaleString()}</span></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Run backup now</Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Users2 size={16} className="text-ink-faint" /><h3 className="font-semibold">Admin users</h3></div>
          <ul className="space-y-2 text-sm">
            {adminUsers.map((user, index) => (
              <li key={index} className="flex justify-between items-center">
                <span className="text-ink">{user.email}</span>
                <div className="flex items-center gap-2">
                  <Badge tone={user.status === 'Active' ? 'good' : 'risk'}>{user.status}</Badge>
                  {adminUsers.length > 1 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteAdmin(user.email)}
                      className="text-ink-danger hover:text-ink-danger"
                      aria-label="Remove admin user"
                    >
                      <X size={14} />
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Button size="sm" variant="secondary" className="mt-4" onClick={() => setShowAddAdminModal(true)}>
            <Plus size={14} className="mr-1" /> Add admin user
          </Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><KeyRound size={16} className="text-ink-faint" /><h3 className="font-semibold">Security</h3></div>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>JWT session length: <span className="text-ink font-medium">{securityInfo.jwtSessionLength}</span></li>
            <li>Last secret rotation: <span className="text-ink font-medium">{securityInfo.lastSecretRotation}</span></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Rotate JWT secret</Button>
        </Card>
      </div>

      {/* Add Admin User Modal */}
      <Modal
        isOpen={showAddAdminModal}
        onClose={() => { setShowAddAdminModal(false); setNewAdminEmail(''); setAddAdminError(''); }}
        title="Add Admin User"
      >
        <div className="space-y-4">
          <p className="text-ink-muted text-sm">Enter the email address of the new admin user.</p>
          <Input
            type="email"
            value={newAdminEmail}
            onChange={(e) => { setNewAdminEmail(e.target.value); setAddAdminError(''); }}
            placeholder="karongo27@gmail.com"
            disabled={addingAdmin}
          />
          {addAdminError && (
            <p className="text-sm text-ink-danger">{addAdminError}</p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => { setShowAddAdminModal(false); setNewAdminEmail(''); setAddAdminError(''); }} disabled={addingAdmin}>
              Cancel
            </Button>
            <Button onClick={handleAddAdmin} disabled={addingAdmin}>
              {addingAdmin ? (
                <>
                  <Loader2 size={14} className="mr-1 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add admin user'
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function StatusRow({ label, status }) {
  return (
    <li className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-ink"><Activity size={13} className="text-forest-600" /> {label}</span>
      <Badge tone={status === 'Online' ? 'good' : status === 'Offline' ? 'risk' : 'watch'}>
        {status}
      </Badge>
    </li>
  )
}
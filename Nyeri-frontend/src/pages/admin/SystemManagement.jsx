import { Server, Database, KeyRound, Users2, Activity, Plus, X, Loader2, UserCheck } from 'lucide-react'
import { Card, Badge, Button, Input, Modal } from '../../components/ui'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSharedAsyncData } from '../../hooks/useAsyncData'
import APIService from '../../services/api'

export default function SystemManagement() {
  const [showAddAdminModal, setShowAddAdminModal] = useState(false)
  const [newAdminEmail, setNewAdminEmail] = useState('')
  const [addingAdmin, setAddingAdmin] = useState(false)
  const [addAdminError, setAddAdminError] = useState('')

  // Fetch service status
  const { data: serviceStatus, isLoading: serviceLoading, error: serviceError, refresh: refreshService } = useSharedAsyncData(
    'system-service-status',
    async () => {
      const [flaskResponse, mongodbResponse, aiResponse] = await Promise.all([
        fetch(`${APIService.baseURL}/../health`),
        fetch(`${APIService.baseURL}/admin/summary`),
        fetch(`${APIService.baseURL}/ai/health`)
      ])

      const flaskApiStatus = flaskResponse.ok ? 'Online' : 'Offline'
      const mongodbStatus = mongodbResponse.ok ? 'Online' : 'Offline'
      const aiData = await aiResponse.json()
      const aiModelServiceStatus = aiResponse.ok && aiData.status === 'healthy' ? 'Online' : 'Offline'

      return {
        flaskApi: flaskApiStatus,
        mongodb: mongodbStatus,
        aiModelService: aiModelServiceStatus
      }
    },
    { cacheTime: 10 * 60 * 1000 }
  )

  // Fetch database info
  const { data: databaseInfo, isLoading: dbLoading } = useSharedAsyncData(
    'system-database-info',
    async () => {
      const response = await fetch(`${APIService.baseURL}/admin/summary`)
      if (!response.ok) throw new Error('Failed to fetch admin summary')

      const adminSummary = await response.json()
      if (!adminSummary.success || !adminSummary.data) {
        return { databaseName: 'Unknown', collectionsCount: 0, totalDocuments: 0 }
      }

      const { total_constituencies, total_governors, total_mps, total_allocations, total_audit_findings } = adminSummary.data
      const totalDocuments = total_constituencies + total_governors + total_mps + total_allocations + total_audit_findings

      return {
        databaseName: 'Accountability',
        collectionsCount: 5,
        totalDocuments
      }
    },
    { cacheTime: 10 * 60 * 1000 }
  )

  // Fetch current logged-in admin user
  const { data: currentUser, isLoading: userLoading } = useSharedAsyncData(
    'current-admin-user',
    () => APIService.getCurrentUser(),
    { cacheTime: 10 * 60 * 1000 }
  )

  // Fetch all admin users
  const { data: adminUsersData, isLoading: usersLoading, error: usersError, refresh: refreshUsers } = useSharedAsyncData(
    'admin-users-list',
    () => APIService.getAdminUsers(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const adminUsers = adminUsersData?.data || []

  const anyLoading = serviceLoading || dbLoading || userLoading || usersLoading
  const anyError = serviceError || usersError

  const handleAddAdmin = async () => {
    if (!newAdminEmail.trim()) {
      setAddAdminError('Email is required')
      return
    }

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
        await refreshUsers()
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
        await refreshUsers()
      } else {
        alert(response.error || 'Failed to delete admin user')
      }
    } catch (err) {
      console.error('Error deleting admin user:', err)
      alert(err.message || 'Failed to delete admin user')
    }
  }

  // Build display list: current user first (with Active banner), then other admins
  const displayUsers = useMemo(() => {
    const users = []

    // Add current user first if available
    if (currentUser?.data) {
      users.push({
        email: currentUser.data.email,
        name: currentUser.data.name,
        status: currentUser.data.status,
        isCurrent: true
      })
    }

    // Add other admin users (avoid duplicates)
    adminUsers.forEach((user) => {
      const isDuplicate = currentUser?.data && user.email === currentUser.data.email
      if (!isDuplicate) {
        users.push({
          email: user.email,
          name: user.name || user.email.split('@')[0],
          status: user.status,
          isCurrent: false
        })
      }
    })

    return users
  }, [currentUser, adminUsers])

  if (anyLoading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">System management</h1>
        <p className="text-ink-muted mb-6">Loading system data...</p>
      </div>
    )
  }

  if (anyError) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-1">System management</h1>
        <p className="text-ink-danger mb-6">{anyError}</p>
        <button onClick={() => window.location.reload()} className="btn btn-outline">
          Try again
        </button>
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
            <StatusRow label="Flask API" status={serviceStatus?.flaskApi ?? 'Unknown'} />
            <StatusRow label="MongoDB" status={serviceStatus?.mongodb ?? 'Unknown'} />
            <StatusRow label="AI model service (Ollama)" status={serviceStatus?.aiModelService ?? 'Unknown'} />
          </ul>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Database size={16} className="text-ink-faint" /><h3 className="font-semibold">Database</h3></div>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>Database: <span className="text-ink font-medium">{databaseInfo?.databaseName ?? 'Unknown'}</span></li>
            <li>Collections: <span className="text-ink font-medium">{databaseInfo?.collectionsCount ?? 0}</span></li>
            <li>Total documents: <span className="text-ink font-medium">{(databaseInfo?.totalDocuments ?? 0).toLocaleString()}</span></li>
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Run backup now</Button>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4"><Users2 size={16} className="text-ink-faint" /><h3 className="font-semibold">Admin users</h3></div>
          <ul className="space-y-2 text-sm">
            {displayUsers.map((user, index) => (
              <li key={index} className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className="text-ink">{user.email}</span>
                  {user.isCurrent && (
                    <div className="flex items-center gap-1">
                      <UserCheck size={14} className="text-forest-600" />
                      <Badge tone="good" className="text-xs">Active (you)</Badge>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!user.isCurrent && (
                    <Badge tone={user.status === 'Active' ? 'good' : 'risk'}>{user.status}</Badge>
                  )}
                  {!user.isCurrent && displayUsers.length > 1 && (
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
            <li>JWT session length: <span className="text-ink font-medium">Long-lived (demo)</span></li>
            <li>Last secret rotation: <span className="text-ink font-medium">Not yet rotated</span></li>
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
import { Server, Database, KeyRound, Users2, Activity } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { useState, useEffect } from 'react'
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
    jwtSessionLength: 'Unknown',
    lastSecretRotation: 'Unknown'
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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

        // For admin users, we don't have a specific endpoint, so we'll show placeholder info
        // In a real implementation, this would come from an /api/admin/users endpoint
        setAdminUsers([
          { email: 'admin@nyeri-accountability.org', status: 'Active' }
        ])

        // Set security info based on known configurations
        setSecurityInfo({
          jwtSessionLength: 'Long-lived (demo)',
          lastSecretRotation: 'Not yet rotated'
        })

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
        setSecurityInfo({
          jwtSessionLength: 'Unknown',
          lastSecretRotation: 'Unknown'
        })
      } finally {
        setLoading(false)
      }
    }

    fetchSystemData()
  }, [])

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
              <li key={index} className="flex justify-between">
                <span className="text-ink">{user.email}</span>
                <Badge tone={user.status === 'Active' ? 'good' : 'risk'}>{user.status}</Badge>
              </li>
            ))}
          </ul>
          <Button size="sm" variant="secondary" className="mt-4">Add admin user</Button>
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
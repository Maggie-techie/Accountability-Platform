import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import { LEADER_PHOTOS } from '../utils/leaderPhotos'
import APIService from '../services/api'
import { useAsyncData, Skeleton, AsyncContent } from '../hooks/useAsyncData.jsx'

export default function CountyDashboard() {
  // Fetch data independently - each renders as it arrives
  const { data: governor, isLoading: govLoading, error: govError, refresh: refreshGov } = useAsyncData(
    'governor-profile',
    () => APIService.getGovernorProfile(),
    { cacheTime: 10 * 60 * 1000 }
  )

  const { data: countyFinances, isLoading: financeLoading, refresh: refreshFinance } = useAsyncData(
    'county-finances',
    () => APIService.getCountyFinances(),
    { cacheTime: 10 * 60 * 1000 }
  )

  const { data: departmentsResponse, isLoading: deptLoading, refresh: refreshDept } = useAsyncData(
    'department-data',
    () => APIService.getDepartmentData(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const departments = departmentsResponse?.departments || departmentsResponse || []

  const { data: auditResponse, isLoading: auditLoading, refresh: refreshAudit } = useAsyncData(
    'county-audit-findings',
    () => APIService.getCountyAuditFindings(),
    { cacheTime: 5 * 60 * 1000 }
  )
  const auditFindings = auditResponse?.audit_findings || auditResponse || []

  // Transform county finances data to match expected format if needed
  const isSourcesRow = (f) => f.category?.trim().startsWith('Sources')
  const countyFindings = auditFindings.filter((f) => !isSourcesRow(f))

  // countyFinances is now pivoted: array of { financial_year, equitable_share_kshb, conditional_grants_kshb, osr_kshb, ... }
  const latestFy = countyFinances?.length
    ? [...new Set(countyFinances.map((f) => f.financial_year))].sort().slice(-1)[0]
    : null

  const latestRevenue = countyFinances
    ? countyFinances.find((f) => f.financial_year === latestFy)
    : null

  const equitableShare = latestRevenue?.equitable_share_kshb || 0
  const conditionalGrants = latestRevenue?.conditional_grants_kshb || 0
  const ownSourceRevenue = latestRevenue?.osr_kshb || 0
  const totalRevenue = equitableShare + conditionalGrants + ownSourceRevenue

  // Revenue-by-source trend across all fiscal years (real data from pivoted API response)
  const revenueByYear = countyFinances
    ? countyFinances
        .map((f) => ({
          fy: f.financial_year,
          'Equitable Share': f.equitable_share_kshb || 0,
          'Conditional Grants': f.conditional_grants_kshb || 0,
          'Own Source Revenue': f.osr_kshb || 0,
        }))
        .sort((a, b) => a.fy.localeCompare(b.fy))
    : []

  
  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'County' }]} />
      <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
      <p className="text-ink-muted mb-6">Financial performance and accountability indicators for the county government.</p>

      {/* Governor header - loads independently */}
      <AsyncContent
        isLoading={govLoading}
        error={govError}
        onRetry={refreshGov}
        skeleton={
          <Card className="p-5 mb-6">
            <div className="flex items-center gap-4">
              <Skeleton variant="avatar" className="h-14 w-14" />
              <div className="space-y-2">
                <Skeleton variant="title" className="w-1/3" />
                <Skeleton variant="text" className="w-1/4" />
              </div>
            </div>
          </Card>
        }
      >
        {governor && (
          <Card className="p-5 mb-6 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="h-14 w-14 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif font-semibold relative overflow-hidden">
                {LEADER_PHOTOS.governor ? (
                  <img
                    src={LEADER_PHOTOS.governor}
                    alt={`${governor.name} photo`}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      e.currentTarget.onerror = null;
                      e.currentTarget.src = '';
                      e.currentTarget.alt = '';
                    }}
                  />
                ) : (
                  'MK'
                )}
              </div>
              <div>
                <p className="font-serif font-semibold text-ink">{governor.name}</p>
                <p className="text-sm text-ink-muted">Governor &middot; {governor.party} &middot; {governor.tenure}</p>
              </div>
            </div>
            <Link to={`/leaders/${governor._id || governor.id}`} className="text-sm text-forest-700 hover:underline">View full profile &rarr;</Link>
          </Card>
        )}
      </AsyncContent>

      {/* KPI Cards - each section loads independently */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <AsyncContent isLoading={financeLoading} skeleton={<KpiCard label="Budget" value={<Skeleton variant="kpi" />} />}>
          <KpiCard label={`FY${latestFy || '—'} Budget`} value={`KSh ${totalRevenue.toFixed(2)}B`} />
        </AsyncContent>
        <AsyncContent isLoading={financeLoading} skeleton={<KpiCard label="Equitable Share" value={<Skeleton variant="kpi" />} />}>
          <KpiCard label="Equitable Share" value={`KSh ${equitableShare.toFixed(2)}B`} sub={totalRevenue ? `${((equitableShare / totalRevenue) * 100).toFixed(0)}% of revenue` : ''} />
        </AsyncContent>
        <AsyncContent isLoading={financeLoading} skeleton={<KpiCard label="Conditional Grants" value={<Skeleton variant="kpi" />} />}>
          <KpiCard label="Conditional Grants" value={`KSh ${conditionalGrants.toFixed(2)}B`} sub={totalRevenue ? `${((conditionalGrants / totalRevenue) * 100).toFixed(0)}% of revenue` : ''} />
        </AsyncContent>
        <AsyncContent isLoading={financeLoading} skeleton={<KpiCard label="Own-Source Revenue" value={<Skeleton variant="kpi" />} />}>
          <KpiCard label="Own-Source Revenue" value={`KSh ${ownSourceRevenue.toFixed(2)}B`} sub={totalRevenue ? `${((ownSourceRevenue / totalRevenue) * 100).toFixed(0)}% of revenue` : ''} />
        </AsyncContent>
        <AsyncContent isLoading={auditLoading} skeleton={<KpiCard label="Open audit findings" value={<Skeleton variant="kpi" />} />}>
          <KpiCard label="Open audit findings" value={String(countyFindings.length)} changeTone="down" />
        </AsyncContent>
      </div>

      {/* Charts - wait for finance data */}
      <AsyncContent
        isLoading={financeLoading}
        skeleton={
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <Card className="p-6 h-[300px]">
              <h3 className="font-serif font-semibold text-lg mb-4">Revenue by source</h3>
              <Skeleton variant="chart" />
            </Card>
            <Card className="p-6 h-[300px]">
              <h3 className="font-serif font-semibold text-lg mb-4">Development vs. recurrent</h3>
              <Skeleton variant="chart" />
            </Card>
          </div>
        }
      >
        {countyFinances && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Revenue by source (KSh Billions)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={revenueByYear}>
                    <CartesianGrid stroke="#E2E5E1" vertical={false} />
                    <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                    <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="monotone" dataKey="Equitable Share" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="Conditional Grants" stroke="#8A928C" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="Own Source Revenue" stroke="#2E7D32" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Development vs. recurrent (KSh Billions)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={developmentVsRecurrent}>
                    <CartesianGrid stroke="#E2E5E1" vertical={false} />
                    <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                    <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="recurrent" name="Recurrent" fill="#C7CFC9" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="development" name="Development" fill="#14532D" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        )}
      </AsyncContent>

      {/* Departmental absorption - wait for dept data */}
      <AsyncContent
        isLoading={deptLoading}
        error={null}
        onRetry={refreshDept}
        skeleton={
          <Card className="p-6 mb-6">
            <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption, FY2024/25</h3>
            <div className="space-y-3">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="flex gap-4">
                  <Skeleton variant="text" className="w-40" />
                  <Skeleton variant="text" className="w-24" />
                  <Skeleton variant="text" className="w-24" />
                  <Skeleton variant="text" className="w-20" />
                  <Skeleton variant="badge" />
                </div>
              ))}
            </div>
          </Card>
        }
      >
        {departments.length > 0 && (
          <>
            <Card className="p-6 mb-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption, FY2024/25</h3>
              <Table
                columns={['Department', 'Approved Budget', 'Q3 Spend', 'Absorption', 'Status']}
                rows={departments}
                keyField="_id"
                renderRow={(d) => (
                  <>
                    <td className="py-3 pr-4 font-medium text-ink">{d.department}</td>
                    <td className="py-3 pr-4 text-ink-muted">KSh {d.approved_budget_kshm}M</td>
                    <td className="py-3 pr-4 text-ink-muted">KSh {d.q3_spend_kshm}M</td>
                    <td className="py-3 pr-4 text-ink-muted">{d.absorption_rate}%</td>
                    <td className="py-3 pr-4">
                      <Badge tone={d.status === 'On Track' ? 'good' : d.status === 'Behind' ? 'watch' : 'risk'}>{d.status}</Badge>
                    </td>
                  </>
                )}
              />
            </Card>

            <Card className="p-6">
              <h3 className="font-serif font-semibold text-lg mb-4">Auditor-General findings, county departments</h3>
              <p className="text-3xl font-serif font-semibold text-ink">{countyFindings.length}</p>
              <p className="text-sm text-ink-muted mt-1">Open audit findings across county departments</p>
            </Card>
          </>
        )}
      </AsyncContent>
    </div>
  )
}
import { Link } from 'react-router-dom'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import { governor, countyFinances, departments, auditFindings } from '../data/mockData'

export default function CountyDashboard() {
  const countyFindings = auditFindings.filter((f) => f.entityType === 'department')
  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'County' }]} />
      <h1 className="text-3xl font-semibold mb-1">Nyeri County overview</h1>
      <p className="text-ink-muted mb-6">Financial performance and accountability indicators for the county government.</p>

      <Card className="p-5 mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-full bg-forest-100 flex items-center justify-center text-forest-700 font-serif font-semibold">MK</div>
          <div>
            <p className="font-serif font-semibold text-ink">{governor.name}</p>
            <p className="text-sm text-ink-muted">Governor &middot; {governor.party} &middot; {governor.tenure}</p>
          </div>
        </div>
        <Link to={`/leaders/${governor.id}`} className="text-sm text-forest-700 hover:underline">View full profile &rarr;</Link>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="FY2025/26 Budget" value="KSh 8.0B" />
        <KpiCard label="Equitable Share" value="KSh 5.8B" sub="72% of revenue" />
        <KpiCard label="Own-Source Revenue" value="KSh 0.74B" change="+8% YoY" changeTone="up" />
        <KpiCard label="Open audit findings" value={String(countyFindings.length)} changeTone="down" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Budget vs. expenditure (KSh Billions)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={countyFinances.budgetVsExpenditure}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="budget" name="Budget" stroke="#8A928C" strokeDasharray="4 3" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="expenditure" name="Expenditure" stroke="#14532D" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Development vs. recurrent (KSh Billions)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countyFinances.developmentVsRecurrent}>
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

      <Card className="p-6 mb-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption, FY2024/25</h3>
        <Table
          columns={['Department', 'Approved Budget', 'Q3 Spend', 'Absorption', 'Status']}
          rows={departments}
          renderRow={(d) => (
            <>
              <td className="py-3 pr-4 font-medium text-ink">{d.department}</td>
              <td className="py-3 pr-4 text-ink-muted">KSh {d.approvedBudgetKshm}M</td>
              <td className="py-3 pr-4 text-ink-muted">KSh {d.q3SpendKshm}M</td>
              <td className="py-3 pr-4 text-ink-muted">{d.absorptionRate}%</td>
              <td className="py-3 pr-4">
                <Badge tone={d.status === 'On Track' ? 'good' : d.status === 'Behind' ? 'watch' : 'risk'}>{d.status}</Badge>
              </td>
            </>
          )}
        />
      </Card>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Auditor-General findings, county departments</h3>
        <ul className="space-y-3">
          {countyFindings.map((f) => (
            <li key={f.id} className="flex justify-between gap-3 text-sm border-b border-line pb-3 last:border-0">
              <div>
                <p className="font-medium text-ink">{f.entity} &middot; {f.category}</p>
                <p className="text-ink-muted mt-0.5">{f.finding}</p>
              </div>
              <Badge tone={f.severity === 'High' ? 'risk' : 'watch'}>{f.severity}</Badge>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

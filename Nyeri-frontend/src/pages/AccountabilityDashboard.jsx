import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs, Table } from '../components/DataDisplay'
import { KpiCard } from '../components/Insights'
import { constituencies, allocationTrend, departments, anomalies, auditFindings } from '../data/mockData'
import APIService from '../services/api'


const severityCounts = ['High', 'Medium', 'Low'].map((s) => ({
  name: s, value: anomalies.filter((a) => a.severity === s).length,
}))
const SEV_COLORS = { High: '#A6431F', Medium: '#C08A28', Low: '#2E6B44' }

export default function AccountabilityDashboard() {
  const avgScore = Math.round(constituencies.reduce((a, c) => a + c.accountabilityScore, 0) / constituencies.length)
  const totalFlagged = auditFindings.reduce((a, f) => a + f.amountKshm, 0)

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Accountability' }]} />
      <h1 className="text-3xl font-semibold mb-1">Accountability dashboard</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">A county-wide view of financial performance, audit findings and AI-detected anomalies.</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Avg. constituency score" value={avgScore} sub="out of 100" />
        <KpiCard label="Total flagged amount" value={`KSh ${totalFlagged.toFixed(1)}M`} changeTone="down" />
        <KpiCard label="Active anomalies" value={String(anomalies.filter((a) => a.status !== 'Reviewed - no issue').length)} />
        <KpiCard label="Departments below target" value={String(departments.filter((d) => d.status !== 'On Track').length)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-serif font-semibold text-lg mb-4">NG-CDF allocation trend, all constituencies</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={allocationTrend}>
                <CartesianGrid stroke="#E2E5E1" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} />
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {constituencies.map((c, i) => (
                  <Line key={c.slug} type="monotone" dataKey={c.name}
                    stroke={['#14532D', '#A6431F', '#C08A28', '#2E6B44', '#5B6560', '#6E9E7C'][i]}
                    strokeWidth={2} dot={{ r: 2.5 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-6">
          <h3 className="font-serif font-semibold text-lg mb-4">Anomalies by severity</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={severityCounts} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                  {severityCounts.map((s) => <Cell key={s.name} fill={SEV_COLORS[s.name]} />)}
                </Pie>
                <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 text-xs mt-2">
            {severityCounts.map((s) => (
              <span key={s.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: SEV_COLORS[s.name] }} /> {s.name} ({s.value})
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-6 mb-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Constituency comparison</h3>
        <Table
          columns={['Constituency', 'MP', 'Score', 'Allocation FY24/25', 'Audit Opinion', 'Findings']}
          rows={constituencies}
          keyField="_id"
          renderRow={(c) => (
            <>
              <td className="py-3 pr-4 font-medium text-ink">{c.name}</td>
              <td className="py-3 pr-4 text-ink-muted">{c.mp}</td>
              <td className="py-3 pr-4"><Badge tone={c.accountabilityScore >= 70 ? 'good' : c.accountabilityScore >= 55 ? 'watch' : 'risk'}>{c.accountabilityScore}</Badge></td>
              <td className="py-3 pr-4 text-ink-muted">KSh {c.totalAllocationKshm.toFixed(1)}M</td>
              <td className="py-3 pr-4 text-ink-muted">{c.auditStatus}</td>
              <td className="py-3 pr-4 text-ink-muted">{c.misappropriationCount} flagged</td>
            </>
          )}
        />
      </Card>

      <Card className="p-6">
        <h3 className="font-serif font-semibold text-lg mb-4">Departmental absorption</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={departments}>
              <CartesianGrid stroke="#E2E5E1" vertical={false} />
              <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#5B6560' }} axisLine={{ stroke: '#E2E5E1' }} tickLine={false} interval={0} angle={-15} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 12, fill: '#5B6560' }} axisLine={false} tickLine={false} unit="%" />
              <RTooltip contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: '#E2E5E1' }} />
              <Bar dataKey="absorptionRate" name="Absorption %" fill="#14532D" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}

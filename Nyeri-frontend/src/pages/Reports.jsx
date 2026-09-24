import { useMemo, useState, useEffect } from 'react'
import { FileText, Download, Eye } from 'lucide-react'
import { Card, Button, EmptyState } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'
import { reports } from '../data/mockData'

const categories = [...new Set(reports.map((r) => r.category))]

export default function Reports() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [fy, setFy] = useState('')

  // Report generation state
  const [reportType, setReportType] = useState('governor') // governor, constituency
  const [selectedGovernor, setSelectedGovernor] = useState('')
  const [selectedConstituency, setSelectedConstituency] = useState('')
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportGenerated, setReportGenerated] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)
  const [reportError, setReportError] = useState(null)

  const filtered = useMemo(() => reports.filter((r) =>
    (!q || r.title.toLowerCase().includes(q.toLowerCase())) &&
    (!category || r.category === category) &&
    (!fy || r.financialYear === fy)
  ), [q, category, fy])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 6)

  const generateReport = async () => {
    if (!selectedGovernor && !selectedConstituency) {
      setReportError('Please select a governor or constituency')
      return
    }

    setGeneratingReport(true)
    setReportError(null)
    setReportGenerated(false)
    setDownloadUrl(null)

    try {
      let response
      if (reportType === 'governor' && selectedGovernor) {
        response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/reports/governor/${encodeURIComponent(selectedGovernor)}?format=excel`, {
          method: 'GET',
        })
      } else if (reportType === 'constituency' && selectedConstituency) {
        response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/reports/constituency/${encodeURIComponent(selectedConstituency)}?format=excel`, {
          method: 'GET',
        })
      }

      if (!response.ok) {
        throw new Error(`Failed to generate report: ${response.statusText}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      setDownloadUrl(url)
      setReportGenerated(true)
    } catch (error) {
      setReportError(error.message)
      console.error('Error generating report:', error)
    } finally {
      setGeneratingReport(false)
    }
  }

  const handleDownload = () => {
    if (downloadUrl) {
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `report_${new Date().toISOString().slice(0,10)}.xlsx`
      link.click()
      window.URL.revokeObjectURL(downloadUrl)
      setDownloadUrl(null)
      setReportGenerated(false)
    }
  }

  // Fetch governors and constituencies for dropdowns
  const [governors, setGovernors] = useState([])
  const [constituenciesList, setConstituenciesList] = useState([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch governors (we'll use mock data since we don't have a governor list endpoint)
        setGovernors([
          { value: 'Mutahi Kahiga', label: 'Mutahi Kahiga' },
          // Add more governors as needed
        ])

        // Fetch constituencies using direct fetch
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/constituency/`)
        if (response.ok) {
          const data = await response.json()
          if (data && data.constituencies) {
            setConstituenciesList(
              data.constituencies.map(c => ({
                value: c.slug,
                label: c.name
              }))
            )
          }
        } else {
          throw new Error('Failed to fetch constituencies')
        }
      } catch (error) {
        console.error('Error fetching dropdown data:', error)
        // Fallback to mock data - we'll load it synchronously for now since we're already in an async context
        // but we can't use await here, so we'll use a different approach
        try {
          // Since we can't use await in catch, we'll load the mock data differently
          // For now, let's just use hardcoded fallback data
          setGovernors([
            { value: 'Mutahi Kahiga', label: 'Mutahi Kahiga' },
          ])
          setConstituenciesList([
            { value: 'kieni', label: 'Kieni' },
            { value: 'mathira', label: 'Mathira' },
            { value: 'othaya', label: 'Othaya' },
            { value: 'tetu', label: 'Tetu' },
            { value: 'mukurweini', label: 'Mukurwe-ini' },
            { value: 'nyeri_town', label: 'Nyeri Town' }
          ])
        } catch (e) {
          console.error('Failed to set fallback data:', e);
          setGovernors([
            { value: 'Mutahi Kahiga', label: 'Mutahi Kahiga' },
          ])
          setConstituenciesList([])
        }
      }
    }

    fetchData()
  }, [])

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Reports' }]} />
      <h1 className="text-3xl font-semibold mb-1">Report library</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Accountability, budget, NG-CDF and audit reports, ready to view or download.</p>

      {/* Report Generation Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-2xl font-semibold mb-4">Generate New Report</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-ink mb-2">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-4 py-2 border border-ink-faint rounded-md focus:ring-2 focus:ring-forest-500 focus:border-forest-500"
              disabled={generatingReport}
            >
              <option value="governor">Governor Report</option>
              <option value="constituency">Constituency Report</option>
            </select>
          </div>

          {reportType === 'governor' && (
            <div>
              <label className="block text-sm font-medium text-ink mb-2">Select Governor</label>
              <select
                value={selectedGovernor}
                onChange={(e) => setSelectedGovernor(e.target.value)}
                className="w-full px-4 py-2 border border-ink-faint rounded-md focus:ring-2 focus:ring-forest-500 focus:border-forest-500"
                disabled={generatingReport}
              >
                <option value="">Select a governor</option>
                {governors.map(gov => (
                  <option key={gov.value} value={gov.value}>{gov.label}</option>
                ))}
              </select>
            </div>
          )}

          {reportType === 'constituency' && (
            <div>
              <label className="block text-sm font-medium text-ink mb-2">Select Constituency</label>
              <select
                value={selectedConstituency}
                onChange={(e) => setSelectedConstituency(e.target.value)}
                className="w-full px-4 py-2 border border-ink-faint rounded-md focus:ring-2 focus:ring-forest-500 focus:border-forest-500"
                disabled={generatingReport}
              >
                <option value="">Select a constituency</option>
                {constituenciesList.map(con => (
                  <option key={con.value} value={con.value}>{con.label}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex flex-col items-end justify-end">
            <Button
              size="lg"
              variant={generatingReport ? 'secondary' : 'primary'}
              onClick={generateReport}
              disabled={generatingReport || (!selectedGovernor && !selectedConstituency)}
              className="w-full md:w-auto"
            >
              {generatingReport ? 'Generating...' : 'Generate Report'}
            </Button>
          </div>
        </div>

        {reportError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800">
            {reportError}
          </div>
        )}

        {reportGenerated && !generatingReport && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md text-green-800 flex items-center gap-3">
            <Download size={20} className="flex-shrink-0" />
            <div>
              <p className="font-medium">Report generated successfully!</p>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleDownload}
                className="mt-2"
              >
                Download Excel Report
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Existing Report Library Section */}
      <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search reports" /></div>
      <FilterBar>
        <Select label="Report type" value={category} onChange={setCategory} options={categories} />
        <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(reports.map((r) => r.financialYear))]} />
      </FilterBar>

      {filtered.length === 0 ? (
        <EmptyState title="No reports match your search" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            {pageItems.map((r) => (
              <Card key={r.id} className="p-5 flex gap-4">
                <div className="h-11 w-11 rounded bg-forest-50 text-forest-700 flex items-center justify-center shrink-0">
                  <FileText size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink leading-snug">{r.title}</p>
                  <p className="text-xs text-ink-faint mt-1">{r.category} &middot; {r.entity} &middot; FY {r.financialYear}</p>
                  <p className="text-xs text-ink-faint">Published {r.datePublished}</p>
                  <div className="flex gap-3 mt-3">
                    <Button size="sm" variant="ghost"><Eye size={14} /> View</Button>
                    <Button size="sm" variant="secondary"><Download size={14} /> Download PDF</Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

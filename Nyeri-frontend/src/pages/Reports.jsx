import { useMemo, useState, useEffect } from 'react'
import { FileText, Download, Eye } from 'lucide-react'
import { Card, Button } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'

export default function Reports() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [fy, setFy] = useState('')

  // State for fetched reports
  const [reportsList, setReportsList] = useState([])

  // Fetch reports from backend
  useEffect(() => {
    const fetchReports = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/reports/`)
        if (response.ok) {
          const data = await response.json()
          setReportsList(data.reports || [])
        } else {
          console.warn('Failed to fetch reports from API')
          // Fallback to empty array - no mock data
          setReportsList([])
        }
      } catch (err) {
        console.error('Error fetching reports:', err)
        // Fallback to empty array - no mock data
        setReportsList([])
      }
    }

    fetchReports()
  }, [])

  const filtered = useMemo(() => reportsList.filter((r) =>
    (!q || r.title.toLowerCase().includes(q.toLowerCase())) &&
    (!category || r.category === category) &&
    (!fy || r.financialYear === fy)
  ), [q, category, fy, reportsList])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 6)

  // Function to generate downloadable content for a report
  const generateReportContent = (report) => {
    // Create a simple text representation of the report
    const content = `
Accountability Platform Report
==============================

Title: ${report.title}
Category: ${report.category}
Entity: ${report.entity}
Financial Year: ${report.financialYear}
Published: ${report.datePublished}

This is a sample report from the Accountability Platform.
In a real implementation, this would contain detailed data about:
- Financial expenditures and revenues
- Audit findings and recommendations
- Project implementation status
- Performance metrics

Report ID: ${report.id}
Generated for demonstration purposes.
    `.trim()

    return content
  }

  // Function to handle download
  const handleDownload = (report) => {
    const content = generateReportContent(report)
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = `${report.title.replace(/\s+/g, '_')}_${report.financialYear}.txt`
    link.click()

    // Clean up
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Reports' }]} />
      <h1 className="text-3xl font-semibold mb-1">Report library</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Accountability, budget, NG-CDF and audit reports, ready to view or download.</p>

      <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search reports" /></div>
      <FilterBar>
        <Select label="Report type" value={category} onChange={setCategory} options={[...new Set(reportsList.map((r) => r.category))]} />
        <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(reportsList.map((r) => r.financialYear))]} />
      </FilterBar>

      {filtered.length === 0 ? (
        <div className="text-center py-8 text-ink-muted">
          No reports available. Please check back later or contact support.
        </div>
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
                    <Button size="sm" variant="secondary" onClick={() => handleDownload(r)}>
                      <Download size={14} /> Download
                    </Button>
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

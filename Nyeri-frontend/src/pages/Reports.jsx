import { useMemo, useState, useEffect } from 'react'
import { FileText, Download, Eye, AlertCircle } from 'lucide-react'
import { Card, Button, Toast } from '../components/ui'
import { SearchBar, Select, FilterBar } from '../components/Filters'
import { Breadcrumbs, Pagination, usePagination } from '../components/DataDisplay'
import APIService from '../services/api'
import { useSharedAsyncData } from '../hooks/useAsyncData.jsx'


export default function Reports() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [fy, setFy] = useState('')
  const [toast, setToast] = useState(null)

  // Fetch reports from backend with persistent caching
  const { data: reportsData, isLoading: loading, error } = useSharedAsyncData(
    'reports-list',
    async () => {
      const response = await fetch(`${APIService.baseURL}/reports/`)
      if (response.ok) {
        const data = await response.json()
        // The API returns the list directly, not wrapped in {reports: [...]}
        return Array.isArray(data) ? data : (data.reports || data.data || [])
      } else {
        console.warn('Failed to fetch reports from API:', response.status)
        throw new Error('Failed to load reports')
      }
    },
    { cacheTime: 10 * 60 * 1000 }
  )
  const reportsList = reportsData || []

  const filtered = useMemo(() => reportsList.filter((r) =>
    (!q || r.title.toLowerCase().includes(q.toLowerCase())) &&
    (!category || r.category === category) &&
    (!fy || r.financialYear === fy)
  ), [q, category, fy, reportsList])

  const { page, setPage, totalPages, pageItems } = usePagination(filtered, 6)

  // Download report based on its type
  const handleDownload = async (report) => {
    try {
      setToast({ type: 'info', message: `Generating ${report.title}...` })

      let blob
      let filename

      switch (report.reportType) {
        case 'governor': {
          const governorName = report.reportParams?.governor_name
          if (!governorName) throw new Error('Governor name not specified')
          blob = await APIService.downloadGovernorPDFReport(governorName)
          filename = `${governorName.replace(/\s+/g, '_')}_accountability_report.pdf`
          break
        }
        case 'constituency': {
          const constituencySlug = report.reportParams?.constituency_slug
          if (!constituencySlug) throw new Error('Constituency slug not specified')
          blob = await APIService.downloadConstituencyPDFReport(constituencySlug)
          filename = `${constituencySlug}_accountability_report.pdf`
          break
        }
        case 'audit_findings': {
          const response = await fetch(`${APIService.baseURL}/reports/audit/findings`)
          if (!response.ok) {
            const err = await response.json().catch(() => ({}))
            throw new Error(err.error || err.details || 'Failed to generate audit report')
          }
          blob = await response.blob()
          filename = `nyeri_county_audit_findings_report.pdf`
          break
        }
        case 'financial_summary': {
          const response = await fetch(`${APIService.baseURL}/reports/financial/summary`)
          if (!response.ok) {
            const err = await response.json().catch(() => ({}))
            throw new Error(err.error || err.details || 'Failed to generate financial report')
          }
          blob = await response.blob()
          filename = `nyeri_county_financial_summary_report.pdf`
          break
        }
        default:
          throw new Error(`Unknown report type: ${report.reportType}`)
      }

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)

      setToast({ type: 'success', message: `${report.title} downloaded successfully!` })
    } catch (err) {
      console.error('Error downloading report:', err)
      setToast({ type: 'error', message: err.message || 'Failed to download report' })
    }
  }

  // View report (navigate to a detail page or open in new tab)
  const handleView = (report) => {
    // For now, just show a toast. Could navigate to a detail page or open PDF in new tab
    setToast({ type: 'info', message: `View functionality for ${report.title} coming soon` })
  }

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Reports' }]} />
      <h1 className="text-3xl font-semibold mb-1">Report library</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">Accountability, budget, NG-CDF and audit reports, ready to view or download.</p>

      {loading && (
        <div className="text-center py-8 text-ink-muted">
          Loading reports...
        </div>
      )}

      {error && !loading && (
        <div className="text-center py-8">
          <AlertCircle className="mx-auto h-12 w-12 text-clay-500 mb-4" />
          <p className="text-ink-danger mb-4">{error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-outline">
            Try again
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="mb-4"><SearchBar value={q} onChange={setQ} placeholder="Search reports" /></div>
          <FilterBar>
            <Select label="Report type" value={category} onChange={setCategory} options={[...new Set(reportsList.map((r) => r.category))]} />
            <Select label="Financial year" value={fy} onChange={setFy} options={[...new Set(reportsList.map((r) => r.financialYear))]} />
          </FilterBar>

          {filtered.length === 0 ? (
            <div className="text-center py-8 text-ink-muted">
              No reports match your filters.
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
                        <Button size="sm" variant="ghost" onClick={() => handleView(r)}>
                          <Eye size={14} /> View
                        </Button>
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
        </>
      )}

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
          duration={5000}
        />
      )}
    </div>
  )
}
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, Badge } from '../components/ui'
import { Breadcrumbs, EmptyState } from '../components/DataDisplay'
import APIService from '../services/api'
import { useAsyncData, Skeleton, AsyncContent } from '../hooks/useAsyncData.jsx'

function scoreCategory(score) {
  if (score >= 75) return { label: 'Strong', tone: 'good' }
  if (score >= 55) return { label: 'Moderate', tone: 'watch' }
  return { label: 'Needs Attention', tone: 'risk' }
}

export default function Constituencies() {
  const { data: constituenciesData, isLoading, error, refresh } = useAsyncData(
    'all-constituency-scores',
    () => APIService.getAllConstituencyScores(),
    { cacheTime: 10 * 60 * 1000 }
  )
  const constituencies = constituenciesData || []

  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'Constituencies' }]} />
      <h1 className="text-3xl font-semibold mb-1">The six constituencies of Nyeri</h1>
      <p className="text-ink-muted mb-6 max-w-2xl">
        Kieni, Mathira, Othaya, Tetu, Mukurwe-ini and Nyeri Town each receive their own NG-CDF allocation, audited independently.
      </p>

      <AsyncContent
        isLoading={isLoading}
        error={error}
        onRetry={refresh}
        emptyMessage="No constituencies found"
        skeleton={
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1,2,3,4,5,6].map(i => (
              <Card key={i} className="p-5 h-full">
                <div className="flex items-center justify-between mb-2">
                  <Skeleton variant="title" className="w-1/2" />
                  <Skeleton variant="badge" />
                </div>
                <Skeleton variant="text" className="w-1/3" />
                <div className="mt-4 pt-3 border-t border-line grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <Skeleton variant="text" className="w-full" />
                    <Skeleton variant="text" className="w-3/4" />
                  </div>
                  <div>
                    <Skeleton variant="text" className="w-full" />
                    <Skeleton variant="text" className="w-3/4" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        }
      >
        {constituencies.length === 0 ? (
          <EmptyState title="No constituencies found" description="No constituency data is currently available." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {constituencies.map((c) => {
              const { tone } = scoreCategory(c.accountabilityScore ?? 0)
              const totalAllocation = Object.values(c.allocations_ksm || {}).reduce((sum, v) => sum + (v || 0), 0)
              const mpName = c.mp?.name || c.mp || 'Unknown'
              const mpParty = c.mp?.party || 'Unknown'
              return (
                <Link key={c.slug} to={`/constituencies/${c.slug}`}>
                  <Card className="p-5 h-full hover:border-forest-300 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-serif font-semibold text-lg text-ink">{c.name}</h3>
                      <Badge tone={tone}>{c.accountabilityScore ?? '—'}</Badge>
                    </div>
                    <p className="text-sm text-ink-muted">{mpName} &middot; {mpParty}</p>
                    <div className="mt-4 pt-3 border-t border-line grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-ink-faint text-xs">Total Allocation</p>
                        <p className="font-medium text-ink">KSh {totalAllocation.toFixed(1)}M</p>
                      </div>
                      <div>
                        <p className="text-ink-faint text-xs">Audit opinion</p>
                        <p className="font-medium text-ink">{c.auditStatus || 'Unknown'}</p>
                      </div>
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>
        )}
      </AsyncContent>
    </div>
  )
}

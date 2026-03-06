import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan, getScanOpportunities } from '../api'
import type { Scan, Opportunity } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import OpportunityCard from '../components/OpportunityCard'

const TYPE_OPTIONS = [
  { value: 'all', label: 'All types' },
  { value: 'invisible', label: 'Invisible' },
  { value: 'competitor_dominated', label: 'Competitor Dominated' },
  { value: 'partial_visibility', label: 'Partial Visibility' },
  { value: 'negative_sentiment', label: 'Negative Sentiment' },
]

export default function Opportunities() {
  const { id } = useParams<{ id: string }>()
  const scanId = Number(id)
  const [scan, setScan] = useState<Scan | null>(null)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('all')

  useEffect(() => {
    async function load() {
      try {
        const [s, o] = await Promise.all([getScan(scanId), getScanOpportunities(scanId)])
        setScan(s)
        setOpportunities(o)
      } catch {
        // handled by empty state
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <LoadingSpinner text="Loading opportunities..." />
  if (!scan) return <p className="text-gray-500">Scan not found.</p>

  const filtered = typeFilter === 'all'
    ? opportunities
    : opportunities.filter((o) => o.opportunity_type === typeFilter)

  const typeCounts: Record<string, number> = {}
  for (const o of opportunities) {
    typeCounts[o.opportunity_type] = (typeCounts[o.opportunity_type] ?? 0) + 1
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Opportunities</h1>
          <p className="text-sm text-gray-500 mt-1">
            {opportunities.length} opportunities found &middot;{' '}
            {new Date(scan.started_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/scans/${scanId}`}
            className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            View Results
          </Link>
          <Link
            to={`/projects/${scan.project_id}`}
            className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Back to Project
          </Link>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {TYPE_OPTIONS.slice(1).map((t) => (
          <button
            key={t.value}
            onClick={() => setTypeFilter(typeFilter === t.value ? 'all' : t.value)}
            className={`rounded-lg border p-3 text-left transition-colors ${
              typeFilter === t.value
                ? 'border-indigo-300 bg-indigo-50'
                : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
          >
            <p className="text-2xl font-bold text-gray-900">{typeCounts[t.value] ?? 0}</p>
            <p className="text-xs text-gray-500">{t.label}</p>
          </button>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {TYPE_OPTIONS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          Showing {filtered.length} of {opportunities.length}
        </span>
      </div>

      {/* Opportunity cards */}
      <div className="space-y-4">
        {filtered.map((o) => (
          <OpportunityCard key={o.id} opportunity={o} />
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400 text-sm">
            No opportunities match the selected filter.
          </div>
        )}
      </div>
    </div>
  )
}

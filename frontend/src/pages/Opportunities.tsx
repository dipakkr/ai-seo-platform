import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getScan, getScanOpportunities } from '../api'
import type { Opportunity, Scan } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'

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
        const [scanData, scanOpportunities] = await Promise.all([
          getScan(scanId),
          getScanOpportunities(scanId),
        ])
        setScan(scanData)
        setOpportunities(scanOpportunities)
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [id])

  const filtered = useMemo(() => {
    if (typeFilter === 'all') return opportunities
    return opportunities.filter((opportunity) => opportunity.opportunity_type === typeFilter)
  }, [typeFilter, opportunities])

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const opportunity of opportunities) {
      counts[opportunity.opportunity_type] = (counts[opportunity.opportunity_type] ?? 0) + 1
    }
    return counts
  }, [opportunities])

  if (loading) return <LoadingSpinner text="Loading opportunities..." />
  if (!scan) return <p className="text-sm text-neutral-500">Scan not found.</p>

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <section className="surface p-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-neutral-400 font-semibold">Opportunity Engine</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">Recommended Next Moves</h1>
            <p className="text-sm text-neutral-500 mt-1">
              {opportunities.length} opportunities · {new Date(scan.started_at).toLocaleDateString()}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link to={`/scans/${scanId}`} className="btn-secondary h-10 px-4 rounded-md text-sm font-medium">
              Result Matrix
            </Link>
            <Link to={`/projects/${scan.project_id}`} className="btn-primary h-10 px-4 rounded-md text-sm font-medium">
              Back to Project
            </Link>
          </div>
        </div>
      </section>

      <section className="surface p-5 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {TYPE_OPTIONS.slice(1).map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setTypeFilter(typeFilter === type.value ? 'all' : type.value)}
              className={`rounded-md border p-3 text-left ${
                typeFilter === type.value
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-white text-neutral-800 border-neutral-200 hover:bg-neutral-50'
              }`}
            >
              <p className="text-xl font-semibold">{typeCounts[type.value] ?? 0}</p>
              <p className={`text-xs mt-1 ${typeFilter === type.value ? 'text-neutral-300' : 'text-neutral-500'}`}>
                {type.label}
              </p>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-900"
          >
            {TYPE_OPTIONS.map((type) => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <p className="text-xs text-neutral-400">Showing {filtered.length} of {opportunities.length}</p>
        </div>
      </section>

      <section className="space-y-3">
        {filtered.map((opportunity) => (
          <article key={opportunity.id} className="surface p-4">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-2">
              <h3 className="text-sm font-semibold text-neutral-900 max-w-2xl">
                "{opportunity.query_text ?? `Query #${opportunity.query_id}`}"
              </h3>
              <span className="inline-flex h-6 items-center rounded-md border border-neutral-200 px-2 text-xs text-neutral-600">
                {opportunity.opportunity_type}
              </span>
            </div>

            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <Metric label="Impact" value={opportunity.impact_score.toFixed(1)} />
              <Metric label="Gap" value={`${(opportunity.visibility_gap * 100).toFixed(0)}%`} />
              <Metric
                label="Competitors"
                value={opportunity.competitors_visible.length ? opportunity.competitors_visible.join(', ') : '--'}
              />
              <Metric
                label="Missing Providers"
                value={opportunity.providers_missing.length ? opportunity.providers_missing.join(', ') : '--'}
              />
            </div>

            {opportunity.recommendation && (
              <p className="mt-3 rounded-md bg-neutral-50 border border-neutral-200 px-3 py-2 text-sm text-neutral-600 leading-relaxed">
                {opportunity.recommendation}
              </p>
            )}
          </article>
        ))}

        {filtered.length === 0 && (
          <div className="surface p-8 text-center text-sm text-neutral-400">
            No opportunities match the current filter.
          </div>
        )}
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-muted p-2.5">
      <p className="text-[11px] uppercase tracking-wide text-neutral-400 font-semibold">{label}</p>
      <p className="mt-1 text-sm text-neutral-800 break-words">{value}</p>
    </div>
  )
}

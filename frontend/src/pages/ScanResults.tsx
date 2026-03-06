import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan, getScanResults } from '../api'
import type { Scan, ScanResult } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import VisibilityGauge from '../components/VisibilityGauge'

const PROVIDERS = ['chatgpt', 'perplexity', 'gemini', 'claude'] as const
const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

type ProviderFilter = string | 'all'
type MentionFilter = 'all' | 'mentioned' | 'missing'

export default function ScanResults() {
  const { id } = useParams<{ id: string }>()
  const scanId = Number(id)
  const [scan, setScan] = useState<Scan | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>('all')
  const [mentionFilter, setMentionFilter] = useState<MentionFilter>('all')
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [s, r] = await Promise.all([getScan(scanId), getScanResults(scanId)])
        setScan(s)
        setResults(r)
      } catch {
        // handled by empty state
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <LoadingSpinner text="Loading results..." />
  if (!scan) return <p className="text-gray-500">Scan not found.</p>

  // Group results by query
  const queryMap = new Map<number, { text: string; results: Map<string, ScanResult> }>()
  for (const r of results) {
    if (!queryMap.has(r.query_id)) {
      queryMap.set(r.query_id, {
        text: r.query_text ?? `Query #${r.query_id}`,
        results: new Map(),
      })
    }
    queryMap.get(r.query_id)!.results.set(r.provider, r)
  }

  // Available providers in this scan
  const activeProviders = PROVIDERS.filter((p) =>
    results.some((r) => r.provider === p)
  )

  // Filter
  const queryEntries = [...queryMap.entries()].filter(([, q]) => {
    if (providerFilter !== 'all') {
      const pr = q.results.get(providerFilter)
      if (!pr) return false
      if (mentionFilter === 'mentioned' && !pr.brand_mentioned) return false
      if (mentionFilter === 'missing' && pr.brand_mentioned) return false
      return true
    }
    if (mentionFilter === 'mentioned') {
      return [...q.results.values()].some((r) => r.brand_mentioned)
    }
    if (mentionFilter === 'missing') {
      return [...q.results.values()].some((r) => !r.brand_mentioned)
    }
    return true
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Scan Results</h1>
            {scan.visibility_score != null && (
              <VisibilityGauge score={scan.visibility_score} size="sm" />
            )}
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(scan.started_at).toLocaleDateString()} &middot;{' '}
            {scan.completed_queries} queries &middot; {activeProviders.map((p) => providerLabels[p]).join(', ')}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/scans/${scanId}/opportunities`}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            View Opportunities
          </Link>
          <Link
            to={`/projects/${scan.project_id}`}
            className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Back to Project
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 items-center">
        <select
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">All providers</option>
          {activeProviders.map((p) => (
            <option key={p} value={p}>{providerLabels[p]}</option>
          ))}
        </select>
        <select
          value={mentionFilter}
          onChange={(e) => setMentionFilter(e.target.value as MentionFilter)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">All results</option>
          <option value="mentioned">Mentioned</option>
          <option value="missing">Missing</option>
        </select>
        <span className="text-xs text-gray-400">{queryEntries.length} queries</span>
      </div>

      {/* Results table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-2 text-left">Query</th>
              {activeProviders.map((p) => (
                <th key={p} className="px-4 py-2 text-center">{providerLabels[p]}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {queryEntries.map(([qId, q]) => (
              <>
                <tr
                  key={qId}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpandedRow(expandedRow === qId ? null : qId)}
                >
                  <td className="px-4 py-2.5 text-gray-700 max-w-xs truncate">{q.text}</td>
                  {activeProviders.map((p) => {
                    const r = q.results.get(p)
                    if (!r) {
                      return <td key={p} className="px-4 py-2.5 text-center text-gray-300">--</td>
                    }
                    return (
                      <td key={p} className="px-4 py-2.5 text-center">
                        {r.brand_mentioned ? (
                          <span className="inline-flex items-center gap-1 text-green-600">
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            {r.brand_position ? `#${r.brand_position}` : 'Yes'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-500">
                            <span className="w-2 h-2 rounded-full bg-red-400" />
                            No
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
                {expandedRow === qId && (
                  <tr key={`${qId}-detail`}>
                    <td colSpan={1 + activeProviders.length} className="bg-gray-50 px-4 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {activeProviders.map((p) => {
                          const r = q.results.get(p)
                          if (!r) return null
                          return (
                            <div key={p} className="border border-gray-200 rounded-lg p-3 bg-white">
                              <h4 className="text-xs font-semibold text-gray-500 mb-1">{providerLabels[p]}</h4>
                              {r.brand_context && (
                                <p className="text-xs text-gray-700 mb-2 leading-relaxed">
                                  ...{r.brand_context}...
                                </p>
                              )}
                              {r.competitors_mentioned.length > 0 && (
                                <p className="text-xs text-gray-500">
                                  Competitors: {r.competitors_mentioned.join(', ')}
                                </p>
                              )}
                              {r.citations.length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                  Citations: {r.citations.length} {r.brand_cited && '(your site cited)'}
                                </p>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
        {queryEntries.length === 0 && (
          <div className="p-8 text-center text-gray-400 text-sm">No results match your filters.</div>
        )}
      </div>
    </div>
  )
}

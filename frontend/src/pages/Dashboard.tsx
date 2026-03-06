import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getProject, getScan, getScanResults, getScanOpportunities,
  triggerScan, getProjectHistory, scanSingleQuery,
} from '../api'
import type { SingleQueryResult } from '../api'
import type { ProjectWithQueries, Scan, ScanResult, Opportunity } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import VisibilityGauge from '../components/VisibilityGauge'
import LLMBreakdown, { CategoryBreakdown } from '../components/LLMBreakdown'
import OpportunityCard from '../components/OpportunityCard'
import StatusBadge, { scanStatusVariant, intentBadgeVariant } from '../components/StatusBadge'

const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

export default function Dashboard() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<ProjectWithQueries | null>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [latestScan, setLatestScan] = useState<Scan | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAllQueries, setShowAllQueries] = useState(false)

  // Per-query scan state
  const [scanningQueryId, setScanningQueryId] = useState<number | null>(null)
  const [queryResults, setQueryResults] = useState<Record<number, SingleQueryResult[]>>({})
  const [expandedQueryId, setExpandedQueryId] = useState<number | null>(null)

  const projectId = Number(id)

  useEffect(() => {
    loadProject()
  }, [id])

  async function loadProject() {
    setLoading(true)
    try {
      const [proj, history] = await Promise.all([
        getProject(projectId),
        getProjectHistory(projectId),
      ])
      setProject(proj)
      setScans(history)

      const completed = history.find((s) => s.status === 'completed')
      if (completed) {
        setLatestScan(completed)
        const [res, opps] = await Promise.all([
          getScanResults(completed.id),
          getScanOpportunities(completed.id),
        ])
        setResults(res)
        setOpportunities(opps)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }

  async function handleScan() {
    setScanning(true)
    setError(null)
    try {
      const resp = await triggerScan(projectId)
      const scanId = resp.scan_id

      if (resp.status === 'completed') {
        const [scan, res, opps] = await Promise.all([
          getScan(scanId),
          getScanResults(scanId),
          getScanOpportunities(scanId),
        ])
        setLatestScan(scan)
        setResults(res)
        setOpportunities(opps)
        setScans((prev) => [scan, ...prev])
        return
      }

      let scan = await getScan(scanId)
      while (scan.status === 'pending' || scan.status === 'running') {
        await new Promise((r) => setTimeout(r, 2000))
        scan = await getScan(scanId)
      }

      setLatestScan(scan)
      if (scan.status === 'completed') {
        const [res, opps] = await Promise.all([
          getScanResults(scanId),
          getScanOpportunities(scanId),
        ])
        setResults(res)
        setOpportunities(opps)
        setScans((prev) => [scan, ...prev])
      } else if (scan.status === 'failed') {
        setError(scan.error_message || 'Scan failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  async function handleQueryScan(queryId: number) {
    setScanningQueryId(queryId)
    setExpandedQueryId(queryId)
    try {
      const resp = await scanSingleQuery(queryId)
      setQueryResults((prev) => ({ ...prev, [queryId]: resp.results }))
    } catch (err) {
      setError(err instanceof Error ? err.message : `Query scan failed`)
    } finally {
      setScanningQueryId(null)
    }
  }

  if (loading) return <LoadingSpinner text="Loading project..." />
  if (!project) return <p className="text-gray-500">Project not found.</p>

  const hasResults = results.length > 0
  const activeQueries = project.queries.filter((q) => q.is_active)
  const queriesByCategory = activeQueries.reduce((acc, q) => {
    acc[q.intent_category] = (acc[q.intent_category] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  const displayQueries = showAllQueries ? activeQueries : activeQueries.slice(0, 10)

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.brand_name}</h1>
          <p className="text-sm text-gray-500 mt-1">{project.url}</p>
          {project.category && (
            <p className="text-sm text-gray-400 mt-0.5">{project.category}</p>
          )}
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {scanning ? 'Scanning...' : hasResults ? 'Re-scan All' : 'Run Full Scan'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-500 hover:text-red-700">dismiss</button>
        </div>
      )}

      {scanning && (
        <LoadingSpinner text="Scanning LLMs... this may take a few minutes." />
      )}

      {/* Pre-scan: explain what will happen */}
      {!hasResults && !scanning && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-indigo-900 mb-2">Ready to scan</h2>
          <p className="text-sm text-indigo-700 leading-relaxed">
            Click <strong>Run Full Scan</strong> to check all {activeQueries.length} queries, or click the
            scan button on any individual query below to test it first.
          </p>
        </div>
      )}

      {/* Score + Breakdowns (post-scan) */}
      {hasResults && latestScan && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col items-center justify-center">
            <h2 className="text-sm font-semibold text-gray-500 mb-4">AI Visibility Score</h2>
            <VisibilityGauge score={latestScan.visibility_score ?? 0} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <LLMBreakdown results={results} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <CategoryBreakdown
              results={results}
              queries={project.queries.map((q) => ({ id: q.id, intent_category: q.intent_category }))}
            />
          </div>
        </div>
      )}

      {/* Top Opportunities (post-scan) */}
      {opportunities.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">Top Opportunities</h2>
            {latestScan && (
              <Link
                to={`/scans/${latestScan.id}/opportunities`}
                className="text-sm text-indigo-600 hover:text-indigo-800"
              >
                View all ({opportunities.length})
              </Link>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {opportunities.slice(0, 4).map((o) => (
              <OpportunityCard key={o.id} opportunity={o} />
            ))}
          </div>
        </div>
      )}

      {/* Scan History (post-scan) */}
      {scans.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Scan History</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Date</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Score</th>
                  <th className="px-4 py-2 text-left">Queries</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {scans.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-700">
                      {new Date(s.started_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge label={s.status} variant={scanStatusVariant(s.status)} />
                    </td>
                    <td className="px-4 py-2.5 font-medium text-gray-900">
                      {s.visibility_score != null ? Math.round(s.visibility_score) : '--'}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">
                      {s.completed_queries}/{s.total_queries}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {s.status === 'completed' && (
                        <Link
                          to={`/scans/${s.id}`}
                          className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                        >
                          View Results
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Generated Queries with per-row scan */}
      {activeQueries.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">
              Generated Queries
              <span className="ml-2 text-sm font-normal text-gray-400">({activeQueries.length})</span>
            </h2>
            <div className="flex gap-2 text-xs">
              {Object.entries(queriesByCategory).map(([cat, count]) => (
                <span key={cat} className="text-gray-500">
                  {cat}: {count}
                </span>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Query</th>
                  <th className="px-4 py-2 text-left">Intent</th>
                  <th className="px-4 py-2 text-left">Volume</th>
                  <th className="px-4 py-2 text-center w-28">Scan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {displayQueries.map((q) => {
                  const qResults = queryResults[q.id]
                  const isScanning = scanningQueryId === q.id
                  const isExpanded = expandedQueryId === q.id
                  const hasQueryResults = qResults && qResults.length > 0

                  return (
                    <QueryRow
                      key={q.id}
                      query={q}
                      isScanning={isScanning}
                      isExpanded={isExpanded}
                      hasQueryResults={hasQueryResults}
                      qResults={qResults}
                      onScan={() => handleQueryScan(q.id)}
                      onToggle={() => setExpandedQueryId(isExpanded ? null : q.id)}
                    />
                  )
                })}
              </tbody>
            </table>
            {activeQueries.length > 10 && (
              <div className="border-t border-gray-100 px-4 py-2 text-center">
                <button
                  onClick={() => setShowAllQueries(!showAllQueries)}
                  className="text-sm text-indigo-600 hover:text-indigo-800"
                >
                  {showAllQueries ? 'Show less' : `Show all ${activeQueries.length} queries`}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Brand Profile */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Brand Profile</h2>
        <div className="bg-white rounded-xl border border-gray-200 p-6 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Description</span>
            <p className="text-gray-700 mt-0.5">{project.description || 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Target Audience</span>
            <p className="text-gray-700 mt-0.5">{project.target_audience || 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Competitors</span>
            <p className="text-gray-700 mt-0.5">{project.competitors.length ? project.competitors.join(', ') : 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Features</span>
            <p className="text-gray-700 mt-0.5">{project.features.length ? project.features.join(', ') : 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Aliases</span>
            <p className="text-gray-700 mt-0.5">{project.brand_aliases.length ? project.brand_aliases.join(', ') : 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Active Queries</span>
            <p className="text-gray-700 mt-0.5">{activeQueries.length}</p>
          </div>
        </div>
      </div>
    </div>
  )
}


// --- Per-query row component ---

interface QueryRowProps {
  query: { id: number; text: string; intent_category: string; search_volume: number | null }
  isScanning: boolean
  isExpanded: boolean
  hasQueryResults: boolean
  qResults: SingleQueryResult[] | undefined
  onScan: () => void
  onToggle: () => void
}

function QueryRow({ query, isScanning, isExpanded, hasQueryResults, qResults, onScan, onToggle }: QueryRowProps) {
  return (
    <>
      <tr className="hover:bg-gray-50">
        <td className="px-4 py-2.5 text-gray-700">
          <span
            className={hasQueryResults ? 'cursor-pointer hover:text-indigo-600' : ''}
            onClick={hasQueryResults ? onToggle : undefined}
          >
            {query.text}
            {hasQueryResults && (
              <span className="ml-1.5 text-gray-400 text-xs">{isExpanded ? '▾' : '▸'}</span>
            )}
          </span>
        </td>
        <td className="px-4 py-2.5">
          <StatusBadge
            label={query.intent_category}
            variant={intentBadgeVariant(query.intent_category)}
          />
        </td>
        <td className="px-4 py-2.5 text-gray-500">
          {query.search_volume != null ? query.search_volume.toLocaleString() : '--'}
        </td>
        <td className="px-4 py-2.5 text-center">
          {isScanning ? (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
              <span className="w-3 h-3 border border-gray-300 border-t-indigo-600 rounded-full animate-spin" />
              Scanning...
            </span>
          ) : hasQueryResults ? (
            <div className="flex items-center justify-center gap-1">
              {qResults!.map((r) => (
                <span
                  key={r.provider}
                  title={`${providerLabels[r.provider] ?? r.provider}: ${r.brand_mentioned ? 'Mentioned' : 'Not mentioned'}`}
                  className={`w-2.5 h-2.5 rounded-full ${r.brand_mentioned ? 'bg-green-500' : 'bg-red-400'}`}
                />
              ))}
              <button
                onClick={onScan}
                className="ml-1.5 text-xs text-gray-400 hover:text-indigo-600"
                title="Re-scan this query"
              >
                ↻
              </button>
            </div>
          ) : (
            <button
              onClick={onScan}
              className="px-3 py-1 text-xs font-medium text-indigo-600 border border-indigo-200 rounded-md hover:bg-indigo-50 transition-colors"
            >
              Scan
            </button>
          )}
        </td>
      </tr>
      {isExpanded && hasQueryResults && (
        <tr>
          <td colSpan={4} className="bg-gray-50 px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {qResults!.map((r) => (
                <div key={r.provider} className="border border-gray-200 rounded-lg p-3 bg-white">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold text-gray-700">
                      {providerLabels[r.provider] ?? r.provider}
                    </h4>
                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${r.brand_mentioned ? 'text-green-600' : 'text-red-500'}`}>
                      <span className={`w-2 h-2 rounded-full ${r.brand_mentioned ? 'bg-green-500' : 'bg-red-400'}`} />
                      {r.brand_mentioned
                        ? r.brand_position
                          ? `Mentioned (#${r.brand_position})`
                          : 'Mentioned'
                        : 'Not mentioned'}
                    </span>
                  </div>

                  {r.brand_context && (
                    <p className="text-xs text-gray-600 mb-2 leading-relaxed bg-gray-50 rounded p-2">
                      ...{r.brand_context}...
                    </p>
                  )}

                  {r.brand_sentiment && (
                    <p className="text-xs text-gray-500 mb-1">
                      Sentiment: <span className={
                        r.brand_sentiment === 'positive' ? 'text-green-600' :
                        r.brand_sentiment === 'negative' ? 'text-red-600' : 'text-gray-600'
                      }>{r.brand_sentiment}</span>
                    </p>
                  )}

                  {r.competitors_mentioned.length > 0 && (
                    <p className="text-xs text-gray-500 mb-1">
                      Competitors: <span className="text-gray-700">{r.competitors_mentioned.join(', ')}</span>
                    </p>
                  )}

                  {r.citations.length > 0 && (
                    <p className="text-xs text-gray-500 mb-1">
                      Citations: {r.citations.length}
                      {r.brand_cited && <span className="ml-1 text-green-600 font-medium">(your site cited)</span>}
                    </p>
                  )}

                  {r.latency_ms != null && (
                    <p className="text-xs text-gray-400 mt-1">{r.latency_ms}ms</p>
                  )}

                  {r.error && (
                    <p className="text-xs text-red-500 mt-1">Provider returned an error</p>
                  )}

                  {!r.brand_context && !r.error && r.raw_response && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                        View full response
                      </summary>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                        {r.raw_response}
                      </p>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

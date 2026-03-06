import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  addQuery,
  deleteQuery,
  getProject,
  getProjectHistory,
  getScan,
  getScanRankings,
  getScanResults,
  scanSingleQuery,
  triggerScan,
  updateQuery,
} from '../api'
import type { SingleQueryResult } from '../api'
import type { ProjectWithQueries, QueryRankings, Scan, ScanResult } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge, { intentBadgeVariant, scanStatusVariant } from '../components/StatusBadge'
import { getIntegrationKeys } from '../integrations'

const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

const INTENTS = ['discovery', 'comparison', 'problem', 'recommendation'] as const

type ViewMode = 'rankings' | 'raw'

export default function Dashboard() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)

  const [project, setProject] = useState<ProjectWithQueries | null>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [latestScan, setLatestScan] = useState<Scan | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [rankings, setRankings] = useState<QueryRankings[]>([])

  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('rankings')
  const [expandedRankingQueryId, setExpandedRankingQueryId] = useState<number | null>(null)

  const [newQueryText, setNewQueryText] = useState('')
  const [newQueryIntent, setNewQueryIntent] = useState<(typeof INTENTS)[number]>('discovery')
  const [queryMutationLoading, setQueryMutationLoading] = useState(false)

  const [scanningQueryId, setScanningQueryId] = useState<number | null>(null)
  const [queryResults, setQueryResults] = useState<Record<number, SingleQueryResult[]>>({})
  const [expandedQueryId, setExpandedQueryId] = useState<number | null>(null)

  useEffect(() => {
    void loadProject()
  }, [id])

  async function loadProject() {
    setLoading(true)
    setError(null)
    try {
      const [proj, history] = await Promise.all([getProject(projectId), getProjectHistory(projectId)])
      setProject(proj)
      setScans(history)

      const completed = history.find((s) => s.status === 'completed')
      if (completed) {
        setLatestScan(completed)
        const [scanResults, scanRankings] = await Promise.all([
          getScanResults(completed.id),
          getScanRankings(completed.id),
        ])
        setResults(scanResults)
        setRankings(scanRankings)
      } else {
        setLatestScan(null)
        setResults([])
        setRankings([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }

  async function runFullScan() {
    setScanning(true)
    setError(null)
    try {
      const resp = await triggerScan(projectId)
      const scanId = resp.scan_id

      if (resp.status === 'completed') {
        const [scan, scanResults, scanRankings] = await Promise.all([
          getScan(scanId),
          getScanResults(scanId),
          getScanRankings(scanId),
        ])
        setLatestScan(scan)
        setResults(scanResults)
        setRankings(scanRankings)
        setScans((prev) => [scan, ...prev])
        return
      }

      let scan = await getScan(scanId)
      while (scan.status === 'pending' || scan.status === 'running') {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        scan = await getScan(scanId)
      }

      setLatestScan(scan)
      if (scan.status === 'completed') {
        const [scanResults, scanRankings] = await Promise.all([
          getScanResults(scanId),
          getScanRankings(scanId),
        ])
        setResults(scanResults)
        setRankings(scanRankings)
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

  async function handleAddQuery() {
    const text = newQueryText.trim()
    if (!text) return

    setQueryMutationLoading(true)
    setError(null)
    try {
      await addQuery(projectId, text, newQueryIntent)
      setNewQueryText('')
      await loadProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add query')
    } finally {
      setQueryMutationLoading(false)
    }
  }

  async function handleDeleteQuery(queryId: number) {
    if (!window.confirm('Delete this query?')) return
    setQueryMutationLoading(true)
    setError(null)
    try {
      await deleteQuery(queryId)
      await loadProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete query')
    } finally {
      setQueryMutationLoading(false)
    }
  }

  async function handleToggleQuery(queryId: number, isActive: boolean) {
    setQueryMutationLoading(true)
    setError(null)
    try {
      await updateQuery(queryId, { is_active: isActive })
      await loadProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update query')
    } finally {
      setQueryMutationLoading(false)
    }
  }

  async function handleQueryScan(queryId: number) {
    setScanningQueryId(queryId)
    setExpandedQueryId(queryId)
    setError(null)
    try {
      const resp = await scanSingleQuery(queryId)
      setQueryResults((prev) => ({ ...prev, [queryId]: resp.results }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Single-query scan failed')
    } finally {
      setScanningQueryId(null)
    }
  }

  const stats = useMemo(() => {
    const activeQueries = project?.queries.filter((q) => q.is_active).length ?? 0
    const providers = new Set(results.map((r) => r.provider))
    const configuredKeys = getIntegrationKeys()
    const configuredProviders = [
      configuredKeys.openai_api_key,
      configuredKeys.anthropic_api_key,
      configuredKeys.google_api_key,
      configuredKeys.perplexity_api_key,
    ].filter((key) => key.trim().length > 0).length
    const mentions = results.filter((r) => r.brand_mentioned).length
    const mentionRate = results.length ? Math.round((mentions / results.length) * 100) : 0

    return {
      activeQueries,
      providers: providers.size > 0 ? providers.size : configuredProviders,
      mentionRate,
      latestScore: latestScan?.visibility_score != null ? Math.round(latestScan.visibility_score) : null,
    }
  }, [project, results, latestScan])

  const hasResults = rankings.length > 0

  const resultsLookup = useMemo(() => {
    const map = new Map<string, ScanResult>()
    for (const r of results) {
      map.set(`${r.query_id}:${r.provider}`, r)
    }
    return map
  }, [results])

  const rawRows = useMemo(() => {
    const map = new Map<number, { text: string; providers: Map<string, ScanResult> }>()
    const queryTextById = new Map<number, string>((project?.queries ?? []).map((q) => [q.id, q.text]))

    for (const r of results) {
      if (!map.has(r.query_id)) {
        map.set(r.query_id, {
          text: queryTextById.get(r.query_id) ?? `Query #${r.query_id}`,
          providers: new Map(),
        })
      }
      map.get(r.query_id)!.providers.set(r.provider, r)
    }

    return [...map.entries()]
  }, [results, project?.queries])

  if (loading) return <LoadingSpinner text="Loading workspace..." />
  if (!project) return <p className="text-sm text-neutral-500">Project not found.</p>

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <section className="surface p-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-neutral-400 font-semibold">Project</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">{project.brand_name}</h1>
            <p className="text-sm text-neutral-500 mt-1 break-all">{project.url}</p>
          </div>
          <button
            onClick={runFullScan}
            disabled={scanning}
            className="btn-primary h-10 px-4 rounded-md text-sm font-medium disabled:opacity-50"
            type="button"
          >
            {scanning ? 'Scanning...' : hasResults ? 'Re-run Scan' : 'Run Scan'}
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Active Queries" value={String(stats.activeQueries)} />
          <StatCard label="Providers Covered" value={String(stats.providers)} />
          <StatCard label="Mention Rate" value={`${stats.mentionRate}%`} />
          <StatCard label="Visibility Score" value={stats.latestScore == null ? '--' : String(stats.latestScore)} />
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
      </section>

      <section className="surface p-5">
        <h2 className="text-base font-semibold text-neutral-900">Query Management</h2>
        <p className="text-sm text-neutral-500 mt-1">Add, scan, activate, and maintain tracked prompts.</p>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_180px_120px] gap-2">
          <input
            value={newQueryText}
            onChange={(e) => setNewQueryText(e.target.value)}
            placeholder="Add a new query"
            className="h-10 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-900"
          />
          <select
            value={newQueryIntent}
            onChange={(e) => setNewQueryIntent(e.target.value as (typeof INTENTS)[number])}
            className="h-10 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-900"
          >
            {INTENTS.map((intent) => (
              <option key={intent} value={intent}>{intent}</option>
            ))}
          </select>
          <button
            onClick={handleAddQuery}
            disabled={queryMutationLoading || !newQueryText.trim()}
            className="btn-secondary h-10 px-3 rounded-md text-sm font-medium disabled:opacity-40"
            type="button"
          >
            Add Query
          </button>
        </div>

        <div className="mt-4 overflow-x-auto border border-neutral-200 rounded-md">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-neutral-500 text-xs uppercase">
              <tr>
                <th className="px-3 py-2 text-left">Query</th>
                <th className="px-3 py-2 text-left">Intent</th>
                <th className="px-3 py-2 text-left">Volume</th>
                <th className="px-3 py-2 text-left">Active</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {project.queries.map((query) => {
                const qResults = queryResults[query.id] ?? []
                const isExpanded = expandedQueryId === query.id

                return (
                  <Fragment key={query.id}>
                    <tr className="hover:bg-neutral-50">
                      <td className="px-3 py-2.5 text-neutral-800">{query.text}</td>
                      <td className="px-3 py-2.5">
                        <StatusBadge label={query.intent_category} variant={intentBadgeVariant(query.intent_category)} />
                      </td>
                      <td className="px-3 py-2.5 text-neutral-500">{query.search_volume ?? '--'}</td>
                      <td className="px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={query.is_active}
                          onChange={(e) => handleToggleQuery(query.id, e.target.checked)}
                          disabled={queryMutationLoading}
                        />
                      </td>
                      <td className="px-3 py-2.5 text-right space-x-1">
                        <button
                          onClick={() => handleQueryScan(query.id)}
                          disabled={scanningQueryId === query.id}
                          className="btn-secondary h-8 px-2 rounded text-xs disabled:opacity-40"
                          type="button"
                        >
                          {scanningQueryId === query.id ? 'Scanning...' : 'Scan'}
                        </button>
                        <button
                          onClick={() => setExpandedQueryId(isExpanded ? null : query.id)}
                          disabled={!qResults.length}
                          className="btn-secondary h-8 px-2 rounded text-xs disabled:opacity-40"
                          type="button"
                        >
                          Details
                        </button>
                        <button
                          onClick={() => handleDeleteQuery(query.id)}
                          disabled={queryMutationLoading}
                          className="h-8 px-2 rounded text-xs border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-40"
                          type="button"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>

                    {isExpanded && qResults.length > 0 && (
                      <tr>
                        <td colSpan={5} className="bg-neutral-50 px-3 py-3">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {qResults.map((result) => (
                              <div key={result.provider} className="surface-muted p-3">
                                <p className="text-xs font-semibold text-neutral-700">
                                  {providerLabels[result.provider] ?? result.provider}
                                </p>
                                <p className="text-xs text-neutral-600 mt-1 leading-relaxed">
                                  {result.brands_ranked.slice(0, 5).map((brand) => (
                                    <span
                                      key={brand.name}
                                      className={brand.is_your_brand ? 'mr-1 rounded bg-neutral-900 px-1 text-white' : 'mr-1'}
                                    >
                                      {brand.position ? `${brand.position}. ` : ''}{brand.name}
                                    </span>
                                  ))}
                                </p>
                                {result.raw_response && (
                                  <details className="mt-2">
                                    <summary className="text-xs text-neutral-500 cursor-pointer">Full response</summary>
                                    <p className="text-xs text-neutral-600 mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                      {result.raw_response}
                                    </p>
                                  </details>
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {hasResults && latestScan && (
        <section className="surface p-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-neutral-900">Visibility Rankings</h2>
              <p className="text-sm text-neutral-500">Scan #{latestScan.id} aggregated across providers</p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('rankings')}
                className={`h-8 px-3 rounded-md text-xs font-medium border ${viewMode === 'rankings' ? 'bg-neutral-900 text-white border-neutral-900' : 'bg-white text-neutral-700 border-neutral-200'}`}
                type="button"
              >
                Rankings
              </button>
              <button
                onClick={() => setViewMode('raw')}
                className={`h-8 px-3 rounded-md text-xs font-medium border ${viewMode === 'raw' ? 'bg-neutral-900 text-white border-neutral-900' : 'bg-white text-neutral-700 border-neutral-200'}`}
                type="button"
              >
                Raw
              </button>
              <Link to={`/scans/${latestScan.id}`} className="text-xs text-neutral-600 hover:text-neutral-900">
                Open Detail View
              </Link>
            </div>
          </div>

          {viewMode === 'rankings' ? (
            <div className="mt-4 overflow-x-auto border border-neutral-200 rounded-md">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 text-neutral-500 text-xs uppercase">
                  <tr>
                    <th className="px-3 py-2 text-left">Query</th>
                    <th className="px-3 py-2 text-left">#1</th>
                    <th className="px-3 py-2 text-left">#2</th>
                    <th className="px-3 py-2 text-left">#3</th>
                    <th className="px-3 py-2 text-left">#4</th>
                    <th className="px-3 py-2 text-left">#5</th>
                    <th className="px-3 py-2 text-left">You</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {rankings.map((row) => {
                    const topFive = row.rankings.slice(0, 5)
                    const yourPositions = Object.values(row.per_provider)
                      .flat()
                      .filter((b) => b.is_your_brand && b.position != null)
                      .map((b) => b.position as number)
                    const yourPosition = yourPositions.length ? Math.min(...yourPositions) : null

                    return (
                      <Fragment key={row.query_id}>
                        <tr
                          className="hover:bg-neutral-50 cursor-pointer"
                          onClick={() => setExpandedRankingQueryId(expandedRankingQueryId === row.query_id ? null : row.query_id)}
                        >
                          <td className="px-3 py-2.5 text-neutral-800 max-w-xs truncate">{row.query_text}</td>
                          {[0, 1, 2, 3, 4].map((idx) => {
                            const brand = topFive[idx]
                            return (
                              <td key={idx} className="px-3 py-2.5 text-neutral-700">
                                {brand ? (
                                  <span className={brand.is_your_brand ? 'rounded bg-neutral-900 px-1.5 py-0.5 text-white text-xs font-medium' : ''}>
                                    {brand.name}
                                  </span>
                                ) : (
                                  <span className="text-neutral-300">--</span>
                                )}
                              </td>
                            )
                          })}
                          <td className="px-3 py-2.5 font-semibold text-neutral-900">
                            {yourPosition ? `#${yourPosition}` : 'Missing'}
                          </td>
                        </tr>

                        {expandedRankingQueryId === row.query_id && (
                          <tr>
                            <td colSpan={7} className="bg-neutral-50 px-3 py-3">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {Object.entries(row.per_provider).map(([provider, brands]) => {
                                  const detail = resultsLookup.get(`${row.query_id}:${provider}`)
                                  return (
                                    <div key={provider} className="surface-muted p-3">
                                      <p className="text-xs font-semibold text-neutral-700">
                                        {providerLabels[provider] ?? provider}
                                      </p>
                                      <p className="text-xs text-neutral-600 mt-1">
                                        {brands.map((brand) => (
                                          <span
                                            key={brand.name}
                                            className={brand.is_your_brand ? 'mr-1 rounded bg-neutral-900 px-1 text-white' : 'mr-1'}
                                          >
                                            {brand.position ? `${brand.position}. ` : ''}{brand.name}
                                          </span>
                                        ))}
                                      </p>
                                      {detail?.raw_response && (
                                        <details className="mt-2">
                                          <summary className="text-xs text-neutral-500 cursor-pointer">Full response</summary>
                                          <p className="text-xs text-neutral-600 mt-1 whitespace-pre-wrap max-h-40 overflow-y-auto">
                                            {detail.raw_response}
                                          </p>
                                        </details>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto border border-neutral-200 rounded-md">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 text-neutral-500 text-xs uppercase">
                  <tr>
                    <th className="px-3 py-2 text-left">Query</th>
                    <th className="px-3 py-2 text-left">Provider</th>
                    <th className="px-3 py-2 text-left">Mention</th>
                    <th className="px-3 py-2 text-left">Position</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {rawRows.flatMap(([queryId, row]) =>
                    [...row.providers.values()].map((result) => (
                      <tr key={`${queryId}:${result.provider}`}>
                        <td className="px-3 py-2.5 text-neutral-800">{row.text}</td>
                        <td className="px-3 py-2.5 text-neutral-600">{providerLabels[result.provider] ?? result.provider}</td>
                        <td className="px-3 py-2.5 text-neutral-700">{result.brand_mentioned ? 'Yes' : 'No'}</td>
                        <td className="px-3 py-2.5 text-neutral-600">{result.brand_position ? `#${result.brand_position}` : '--'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {scans.length > 0 && (
        <section className="surface p-5">
          <h2 className="text-base font-semibold text-neutral-900">Scan History</h2>
          <div className="mt-3 overflow-x-auto border border-neutral-200 rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-neutral-500 text-xs uppercase">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Score</th>
                  <th className="px-3 py-2 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {scans.map((scan) => (
                  <tr key={scan.id}>
                    <td className="px-3 py-2.5 text-neutral-700">{new Date(scan.started_at).toLocaleDateString()}</td>
                    <td className="px-3 py-2.5">
                      <StatusBadge label={scan.status} variant={scanStatusVariant(scan.status)} />
                    </td>
                    <td className="px-3 py-2.5 text-neutral-700">
                      {scan.visibility_score != null ? Math.round(scan.visibility_score) : '--'}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {scan.status === 'completed' ? (
                        <Link to={`/scans/${scan.id}`} className="text-xs text-neutral-600 hover:text-neutral-900">
                          Open
                        </Link>
                      ) : (
                        <span className="text-xs text-neutral-400">--</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-muted p-3">
      <p className="text-[11px] uppercase tracking-wide text-neutral-400 font-semibold">{label}</p>
      <p className="mt-1 text-xl font-semibold text-neutral-900">{value}</p>
    </div>
  )
}

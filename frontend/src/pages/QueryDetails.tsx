import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowUpRight, ChevronDown, ChevronUp, Loader2, Zap } from 'lucide-react'
import { getProject, getProjectHistory, getScanResults, scanSingleQuery } from '../api'
import type { SingleQueryResult } from '../api'
import type { ProjectWithQueries, Scan, ScanResult } from '../types'
import HighlightedText from '../components/HighlightedText'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge, { intentBadgeVariant } from '../components/StatusBadge'

const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
  grok: 'Grok',
}

// ── Single provider response strip ──────────────────────────────────────────
function ProviderStrip({
  provider,
  mentioned,
  position,
  response,
  competitors,
  highlightTerms,
  label,
}: {
  provider: string
  mentioned: boolean
  position: number | null
  response: string
  competitors: string[]
  highlightTerms: string[]
  label?: string
}) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className={`border-l-2 pl-4 ${mentioned ? 'border-emerald-400' : 'border-red-300'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-neutral-800">
            {providerLabels[provider] ?? provider}
          </span>
          {label && <span className="text-[10px] text-neutral-400">{label}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
            mentioned
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-red-50 text-red-500'
          }`}>
            {mentioned ? (position ? `#${position}` : 'Mentioned') : 'Not mentioned'}
          </span>
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="text-neutral-300 hover:text-neutral-600 transition-colors"
          >
            {collapsed
              ? <ChevronDown className="w-3.5 h-3.5" />
              : <ChevronUp className="w-3.5 h-3.5" />
            }
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {competitors.length > 0 && (
            <p className="text-[11px] text-neutral-400 mb-2">
              Mentions: <span className="text-neutral-600 font-medium">{competitors.slice(0, 5).join(', ')}</span>
            </p>
          )}
          {response ? (
            <div className="max-h-52 overflow-y-auto rounded-md bg-neutral-50 px-3 py-2.5">
              <HighlightedText
                className="text-[11px] text-neutral-600 leading-relaxed whitespace-pre-wrap block"
                text={response}
                terms={highlightTerms}
              />
            </div>
          ) : (
            <p className="text-[11px] text-neutral-400 italic">No response recorded.</p>
          )}
        </>
      )}
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function QueryDetails() {
  const { id, queryId } = useParams<{ id: string; queryId: string }>()
  const projectId = Number(id)
  const qid = Number(queryId)

  const [project, setProject] = useState<ProjectWithQueries | null>(null)
  const [history, setHistory] = useState<Scan[]>([])
  const [resultsByScan, setResultsByScan] = useState<Record<number, ScanResult[]>>({})
  const [singleScanResults, setSingleScanResults] = useState<SingleQueryResult[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedScanId, setExpandedScanId] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [proj, scans] = await Promise.all([getProject(projectId), getProjectHistory(projectId)])
        setProject(proj)
        const completed = scans.filter((s) => s.status === 'completed')
        setHistory(completed)

        const entries = await Promise.all(
          completed.slice(0, 12).map(async (scan) => {
            const rows = await getScanResults(scan.id, { queryId: qid })
            return [scan.id, rows] as const
          })
        )
        setResultsByScan(Object.fromEntries(entries))
        if (completed.length > 0) setExpandedScanId(completed[0].id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load query details')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [projectId, qid])

  const query = project?.queries.find((q) => q.id === qid)

  const highlightTerms = useMemo(() => {
    if (!project) return []
    let domain = project.url
    try { domain = new URL(project.url).hostname.replace(/^www\./, '') } catch { /* */ }
    return [project.brand_name, domain, ...project.brand_aliases].filter(Boolean)
  }, [project])

  async function handleSingleScan() {
    setScanning(true)
    setError(null)
    setSingleScanResults(null)
    try {
      const resp = await scanSingleQuery(qid)
      setSingleScanResults(resp.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scan query')
    } finally {
      setScanning(false)
    }
  }

  const positionTrend = useMemo(() => history.map((scan) => {
    const rows = resultsByScan[scan.id] ?? []
    const mentioned = rows.filter((r) => r.brand_mentioned).length
    return {
      scanId: scan.id,
      date: new Date(scan.started_at),
      mentioned,
      total: rows.length,
    }
  }), [history, resultsByScan])

  if (loading) return <LoadingSpinner text="Loading query details…" />
  if (!project || !query) return <p className="text-sm text-neutral-500">Query not found.</p>

  return (
    <div className="max-w-4xl mx-auto space-y-0">

      {/* ── HEADER ───────────────────────────────────────────────────────── */}
      <div className="pb-5">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-xs text-neutral-400 mb-3">
          <Link to={`/projects/${projectId}`} className="hover:text-neutral-700 transition-colors">
            {project.brand_name}
          </Link>
          <span>/</span>
          <StatusBadge label={query.intent_category} variant={intentBadgeVariant(query.intent_category)} />
        </div>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-neutral-900 leading-snug">
              "{query.text}"
            </h1>
            {query.search_volume != null && query.search_volume > 0 && (
              <p className="mt-1 text-xs text-neutral-400">
                ~{query.search_volume.toLocaleString()} monthly searches
              </p>
            )}
          </div>

          <button
            onClick={handleSingleScan}
            disabled={scanning}
            type="button"
            className="flex-shrink-0 flex items-center gap-1.5 btn-primary h-8 px-4 rounded-md text-xs font-semibold disabled:opacity-50"
          >
            {scanning
              ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Scanning…</>
              : <><Zap className="w-3.5 h-3.5" />Scan Now</>
            }
          </button>
        </div>

        {error && (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* ── MINI TREND CHART ─────────────────────────────────────────────── */}
      {positionTrend.length > 1 && (
        <div className="flex items-end gap-1.5 h-10 mb-5 pb-1 border-b border-neutral-100">
          {positionTrend.slice().reverse().map((point) => {
            const rate = point.total > 0 ? point.mentioned / point.total : 0
            const h = Math.max(20, Math.round(rate * 100))
            const color = rate >= 0.6 ? 'bg-emerald-400' : rate >= 0.3 ? 'bg-amber-400' : 'bg-red-300'
            return (
              <div key={point.scanId} className="flex flex-col items-center gap-0.5 flex-1 min-w-0" title={`${point.date.toLocaleDateString()} — ${Math.round(rate * 100)}%`}>
                <div className="w-full flex items-end justify-center" style={{ height: 32 }}>
                  <div className={`w-full rounded-t-sm ${color}`} style={{ height: `${h}%` }} />
                </div>
                <span className="text-[8px] text-neutral-300 truncate w-full text-center">
                  {point.date.toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {/* ── LIVE SCAN RESULTS ────────────────────────────────────────────── */}
      {singleScanResults && !scanning && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold text-neutral-900">Live Results</span>
            <span className="text-[10px] text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded-full">just now · not saved</span>
          </div>
          <div className="space-y-4">
            {singleScanResults.map((result) => (
              <ProviderStrip
                key={result.provider}
                provider={result.provider}
                mentioned={result.brand_mentioned}
                position={result.brand_position}
                response={result.raw_response}
                competitors={result.competitors_mentioned ?? []}
                highlightTerms={highlightTerms}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── SCAN HISTORY TIMELINE ────────────────────────────────────────── */}
      {history.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-900 mb-4">Scan History</p>

          <div className="space-y-px">
            {history.map((scan, idx) => {
              const rows = resultsByScan[scan.id] ?? []
              const isExpanded = expandedScanId === scan.id
              const isLatest = idx === 0
              const mentionedCount = rows.filter((r) => r.brand_mentioned).length
              const allMissing = rows.length > 0 && mentionedCount === 0

              return (
                <div key={scan.id} className={`rounded-lg overflow-hidden ${isLatest ? '' : ''}`}>
                  {/* Row header */}
                  <button
                    type="button"
                    className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
                      isExpanded ? 'bg-neutral-50' : 'hover:bg-neutral-50/60'
                    } ${idx > 0 ? 'border-t border-neutral-100' : ''}`}
                    onClick={() => setExpandedScanId(isExpanded ? null : scan.id)}
                  >
                    <div className="flex items-center gap-3">
                      {/* Timeline dot */}
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        allMissing ? 'bg-red-300' : mentionedCount > 0 ? 'bg-emerald-400' : 'bg-neutral-200'
                      }`} />

                      <span className="text-xs font-medium text-neutral-700">
                        {new Date(scan.started_at).toLocaleDateString('en', {
                          month: 'short', day: 'numeric', year: 'numeric',
                        })}
                      </span>

                      {isLatest && (
                        <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded">
                          Latest
                        </span>
                      )}

                      <span className={`text-[11px] font-medium ${mentionedCount > 0 ? 'text-emerald-600' : 'text-neutral-400'}`}>
                        {rows.length > 0
                          ? mentionedCount > 0
                            ? `Mentioned by ${mentionedCount} of ${rows.length} providers`
                            : `Not mentioned by any provider`
                          : 'No data'
                        }
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <Link
                        to={`/scans/${scan.id}`}
                        className="flex items-center gap-1 text-[10px] text-neutral-400 hover:text-neutral-700"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Full scan <ArrowUpRight className="w-3 h-3" />
                      </Link>
                      {isExpanded
                        ? <ChevronUp className="w-3.5 h-3.5 text-neutral-300" />
                        : <ChevronDown className="w-3.5 h-3.5 text-neutral-300" />
                      }
                    </div>
                  </button>

                  {/* Expanded provider strips */}
                  {isExpanded && (
                    <div className="px-7 pb-4 pt-1 space-y-4 bg-neutral-50/40">
                      {rows.length > 0 ? (
                        rows.map((row) => (
                          <ProviderStrip
                            key={`${scan.id}-${row.provider}`}
                            provider={row.provider}
                            mentioned={row.brand_mentioned}
                            position={row.brand_position}
                            response={row.raw_response}
                            competitors={row.competitors_mentioned ?? []}
                            highlightTerms={highlightTerms}
                          />
                        ))
                      ) : (
                        <p className="text-[11px] text-neutral-400 py-2">No results for this query in this scan.</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── EMPTY STATE ──────────────────────────────────────────────────── */}
      {history.length === 0 && !singleScanResults && !scanning && (
        <div className="py-16 text-center">
          <div className="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center mx-auto mb-3">
            <Zap className="w-5 h-5 text-neutral-300" />
          </div>
          <p className="text-sm font-medium text-neutral-700">No scan data yet</p>
          <p className="mt-1 text-xs text-neutral-400">Hit "Scan Now" to see what AI says for this query right now.</p>
        </div>
      )}

    </div>
  )
}

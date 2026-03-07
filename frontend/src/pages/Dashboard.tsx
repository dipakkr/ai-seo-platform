import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowUpRight, CheckCircle2, ChevronDown, ChevronUp,
  Circle, Loader2, RefreshCw, Settings, TrendingDown,
  TrendingUp, Zap,
} from 'lucide-react'
import {
  addQuery, deleteQuery, getProject, getProjectHistory,
  getScan, getScanRankings, getScanResults, triggerScan, updateQuery,
} from '../api'
import type { ProjectWithQueries, QueryRankings, Scan, ScanResult } from '../types'
import HighlightedText from '../components/HighlightedText'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge, { intentBadgeVariant, scanStatusVariant } from '../components/StatusBadge'
import { getIntegrationKeys } from '../integrations'
import type { IntegrationKeys } from '../integrations'

// ── Provider config ──────────────────────────────────────────────────────────
const PROVIDER_CONFIG = [
  { id: 'chatgpt',    label: 'ChatGPT',    sub: 'GPT-4o mini · OpenAI',          keyName: 'openai_api_key'      },
  { id: 'perplexity', label: 'Perplexity', sub: 'Sonar API · Perplexity AI',      keyName: 'perplexity_api_key'  },
  { id: 'gemini',     label: 'Gemini',     sub: 'Gemini 2.5 Flash · Google',      keyName: 'google_api_key'      },
  { id: 'claude',     label: 'Claude',     sub: 'Claude Sonnet · Anthropic',      keyName: 'anthropic_api_key'   },
  { id: 'grok',       label: 'Grok',       sub: 'Grok 3 Mini · xAI',             keyName: 'xai_api_key'         },
] as const

const ALL_PROVIDER_IDS = PROVIDER_CONFIG.map((p) => p.id)
const providerLabels: Record<string, string> = Object.fromEntries(PROVIDER_CONFIG.map((p) => [p.id, p.label]))

const INTENTS = ['discovery', 'comparison', 'problem', 'recommendation'] as const
type IntentFilter = 'all' | (typeof INTENTS)[number]

// ── Matrix cell ──────────────────────────────────────────────────────────────
function MatrixCell({ result }: { result: ScanResult | undefined }) {
  if (!result) return (
    <td className="px-3 py-2.5 text-center">
      <span className="inline-flex w-16 items-center justify-center rounded border border-neutral-100 bg-neutral-50 px-2 py-0.5 text-[11px] text-neutral-300">—</span>
    </td>
  )
  return (
    <td className="px-3 py-2.5 text-center">
      {result.brand_mentioned ? (
        <span className="inline-flex w-16 items-center justify-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
          <span className="text-[9px]">✓</span>
          {result.brand_position ? `#${result.brand_position}` : 'Yes'}
        </span>
      ) : (
        <span className="inline-flex w-16 items-center justify-center rounded border border-red-100 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-500">
          Miss
        </span>
      )}
    </td>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────
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
  const [scanProgress, setScanProgress] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [integrationKeys, setIntegrationKeys] = useState<IntegrationKeys>(getIntegrationKeys())
  const [selectedProviders, setSelectedProviders] = useState<string[]>([])

  const [expandedQueryId, setExpandedQueryId] = useState<number | null>(null)
  const [intentFilter, setIntentFilter] = useState<IntentFilter>('all')
  const [showQueryManager, setShowQueryManager] = useState(false)

  const [newQueryText, setNewQueryText] = useState('')
  const [newQueryIntent, setNewQueryIntent] = useState<(typeof INTENTS)[number]>('discovery')
  const [queryMutationLoading, setQueryMutationLoading] = useState(false)
  const [importingQueries, setImportingQueries] = useState(false)

  useEffect(() => { void loadProject() }, [id])

  // Refresh integration keys on storage change / window focus
  useEffect(() => {
    function refresh() {
      const keys = getIntegrationKeys()
      setIntegrationKeys(keys)
    }
    refresh()
    window.addEventListener('storage', refresh)
    window.addEventListener('focus', refresh)
    return () => { window.removeEventListener('storage', refresh); window.removeEventListener('focus', refresh) }
  }, [])

  // Auto-select configured providers
  useEffect(() => {
    const configured = PROVIDER_CONFIG
      .filter((p) => integrationKeys[p.keyName as keyof IntegrationKeys]?.trim())
      .map((p) => p.id)
    setSelectedProviders(configured)
  }, [integrationKeys])

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
        const [scanResults, scanRankings] = await Promise.all([getScanResults(completed.id), getScanRankings(completed.id)])
        setResults(scanResults)
        setRankings(scanRankings)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }

  async function runFullScan() {
    setScanning(true)
    setScanProgress('Starting…')
    setError(null)
    try {
      const resp = await triggerScan(projectId, selectedProviders)
      const scanId = resp.scan_id

      if (resp.status === 'completed') {
        const [scan, scanResults, scanRankings] = await Promise.all([
          getScan(scanId), getScanResults(scanId), getScanRankings(scanId),
        ])
        setLatestScan(scan); setResults(scanResults); setRankings(scanRankings)
        setScans((prev) => [scan, ...prev])
        return
      }

      let scan = await getScan(scanId)
      while (scan.status === 'pending' || scan.status === 'running') {
        setScanProgress(`${scan.completed_queries ?? 0} / ${scan.total_queries ?? '?'} queries`)
        await new Promise((r) => setTimeout(r, 2000))

        const [scanRes, partialResults, partialRankings] = await Promise.allSettled([
          getScan(scanId),
          getScanResults(scanId),
          getScanRankings(scanId),
        ])
        if (scanRes.status === 'fulfilled') scan = scanRes.value
        if (partialResults.status === 'fulfilled' && partialResults.value.length > 0) {
          setResults(partialResults.value)
        }
        if (partialRankings.status === 'fulfilled' && partialRankings.value.length > 0) {
          setRankings(partialRankings.value)
        }
      }

      setLatestScan(scan)
      if (scan.status === 'completed') {
        const [scanResults, scanRankings] = await Promise.all([getScanResults(scanId), getScanRankings(scanId)])
        setResults(scanResults); setRankings(scanRankings)
        setScans((prev) => [scan, ...prev])
      } else if (scan.status === 'failed') {
        setError(scan.error_message || 'Scan failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
    } finally {
      setScanning(false); setScanProgress('')
    }
  }

  async function handleAddQuery() {
    const text = newQueryText.trim()
    if (!text) return
    setQueryMutationLoading(true)
    try {
      await addQuery(projectId, text, newQueryIntent)
      setNewQueryText('')
      await loadProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add query')
    } finally { setQueryMutationLoading(false) }
  }

  async function handleDeleteQuery(queryId: number) {
    if (!window.confirm('Delete this query?')) return
    setQueryMutationLoading(true)
    try { await deleteQuery(queryId); await loadProject() }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to delete query') }
    finally { setQueryMutationLoading(false) }
  }

  async function handleToggleQuery(queryId: number, isActive: boolean) {
    setProject((prev) => {
      if (!prev) return prev
      return { ...prev, queries: prev.queries.map((q) => q.id === queryId ? { ...q, is_active: isActive } : q) }
    })
    try {
      await updateQuery(queryId, { is_active: isActive })
    } catch {
      setProject((prev) => {
        if (!prev) return prev
        return { ...prev, queries: prev.queries.map((q) => q.id === queryId ? { ...q, is_active: !isActive } : q) }
      })
    }
  }

  async function handleToggleAll(isActive: boolean) {
    if (!project) return
    const toChange = project.queries.filter((q) => q.is_active !== isActive)
    if (toChange.length === 0) return
    setProject((prev) => prev ? { ...prev, queries: prev.queries.map((q) => ({ ...q, is_active: isActive })) } : prev)
    try {
      await Promise.all(toChange.map((q) => updateQuery(q.id, { is_active: isActive })))
    } catch {
      const revertIds = new Set(toChange.map((q) => q.id))
      setProject((prev) => prev ? {
        ...prev,
        queries: prev.queries.map((q) => revertIds.has(q.id) ? { ...q, is_active: !isActive } : q),
      } : prev)
    }
  }

  async function handleImportQueries(file: File) {
    setImportingQueries(true)
    try {
      const text = await file.text()
      const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
      if (lines.length < 2) throw new Error('CSV must include a header and at least one row.')
      const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
      const queryIdx = headers.findIndex((h) => ['query', 'keyword', 'text'].includes(h))
      const volumeIdx = headers.findIndex((h) => ['search_volume', 'volume', 'sv'].includes(h))
      if (queryIdx === -1) throw new Error('CSV must contain a query column (query/keyword/text).')
      for (const row of lines.slice(1)) {
        const cols = row.split(',').map((c) => c.trim())
        const query = cols[queryIdx]
        if (!query) continue
        let volume: number | undefined
        if (volumeIdx >= 0 && cols[volumeIdx]) {
          const parsed = Number.parseInt(cols[volumeIdx], 10)
          if (!Number.isNaN(parsed)) volume = parsed
        }
        await addQuery(projectId, query, 'discovery', volume)
      }
      await loadProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import CSV')
    } finally { setImportingQueries(false) }
  }

  // ── Derived data ────────────────────────────────────────────────────────────
  const highlightTerms = useMemo(() => {
    if (!project) return []
    let domain = project.url
    try { domain = new URL(project.url).hostname.replace(/^www\./, '') } catch { /* */ }
    return [project.brand_name, domain, ...project.brand_aliases].filter(Boolean)
  }, [project])

  const activeProviders = useMemo(() => {
    const seen = new Set(results.map((r) => r.provider))
    return ALL_PROVIDER_IDS.filter((p) => seen.has(p))
  }, [results])

  const providerStats = useMemo(() => {
    const map: Record<string, { total: number; mentioned: number }> = {}
    for (const r of results) {
      if (!map[r.provider]) map[r.provider] = { total: 0, mentioned: 0 }
      map[r.provider].total++
      if (r.brand_mentioned) map[r.provider].mentioned++
    }
    return map
  }, [results])

  // Per-provider result counts (used for live progress during scan)
  const providerResultCounts = useMemo(() => {
    const map: Record<string, number> = {}
    for (const r of results) map[r.provider] = (map[r.provider] ?? 0) + 1
    return map
  }, [results])

  const resultsLookup = useMemo(() => {
    const map = new Map<string, ScanResult>()
    for (const r of results) map.set(`${r.query_id}:${r.provider}`, r)
    return map
  }, [results])

  const queryIntentMap = useMemo(() => {
    const map = new Map<number, string>()
    for (const q of project?.queries ?? []) map.set(q.id, q.intent_category)
    return map
  }, [project?.queries])

  const filteredRankings = useMemo(() => {
    if (intentFilter === 'all') return rankings
    return rankings.filter((r) => queryIntentMap.get(r.query_id) === intentFilter)
  }, [rankings, intentFilter, queryIntentMap])

  const sortedRankings = useMemo(() => {
    return [...filteredRankings].sort((a, b) => {
      const aMissing = activeProviders.filter((p) => !resultsLookup.get(`${a.query_id}:${p}`)?.brand_mentioned).length
      const bMissing = activeProviders.filter((p) => !resultsLookup.get(`${b.query_id}:${p}`)?.brand_mentioned).length
      return bMissing - aMissing
    })
  }, [filteredRankings, activeProviders, resultsLookup])

  const overallScore = useMemo(() => {
    if (latestScan?.visibility_score != null) return Math.round(latestScan.visibility_score)
    if (results.length === 0) return null
    return Math.round((results.filter((r) => r.brand_mentioned).length / results.length) * 100)
  }, [latestScan, results])

  const scoreDelta = useMemo(() => {
    if (scans.length < 2 || overallScore == null) return null
    const prev = scans.find((s) => s.id !== latestScan?.id && s.status === 'completed')
    if (!prev?.visibility_score) return null
    return overallScore - Math.round(prev.visibility_score)
  }, [scans, latestScan, overallScore])

  const blindSpots = useMemo(() => sortedRankings
    .filter((r) => activeProviders.some((p) => !resultsLookup.get(`${r.query_id}:${p}`)?.brand_mentioned))
    .slice(0, 3), [sortedRankings, activeProviders, resultsLookup])

  const topWins = useMemo(() => {
    if (activeProviders.length === 0) return []
    return [...rankings]
      .map((r) => ({
        ...r,
        mentionedIn: activeProviders.filter((p) => resultsLookup.get(`${r.query_id}:${p}`)?.brand_mentioned),
      }))
      .filter((r) => r.mentionedIn.length > 0)
      .sort((a, b) => b.mentionedIn.length - a.mentionedIn.length)
      .slice(0, 3)
  }, [rankings, activeProviders, resultsLookup])

  const topCompetitors = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const r of results) {
      for (const c of r.competitors_mentioned ?? []) counts[c] = (counts[c] ?? 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5)
  }, [results])

  const hasResults = results.length > 0
  const configuredCount = selectedProviders.length

  // Expected queries per provider (from scan metadata or project queries)
  const expectedPerProvider = latestScan?.total_queries && activeProviders.length > 0
    ? Math.ceil(latestScan.total_queries / Math.max(1, activeProviders.length))
    : 10

  if (loading) return <LoadingSpinner text="Loading workspace…" />
  if (!project) return <p className="text-sm text-neutral-500">Project not found.</p>

  return (
    <div className="max-w-7xl mx-auto space-y-4">

      {/* ── BRAND HEADER ──────────────────────────────────────────────────── */}
      <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 flex-shrink-0 rounded-lg bg-neutral-900 flex items-center justify-center text-white font-bold text-base">
              {project.brand_name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-neutral-900">{project.brand_name}</h1>
                {project.category && (
                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-500">
                    {project.category}
                  </span>
                )}
              </div>
              <a
                href={project.url} target="_blank" rel="noreferrer"
                className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 mt-0.5"
              >
                {project.url}
                <ArrowUpRight className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Score inline */}
          <div className="flex items-center gap-4 flex-shrink-0">
            {overallScore != null && (
              <div className="text-right">
                <div className="flex items-center gap-1.5 justify-end">
                  <span className={`text-2xl font-bold ${
                    overallScore >= 60 ? 'text-emerald-600' : overallScore >= 30 ? 'text-amber-600' : 'text-red-500'
                  }`}>{overallScore}</span>
                  <span className="text-sm text-neutral-400 font-medium">/ 100</span>
                  {scoreDelta != null && scoreDelta !== 0 && (
                    scoreDelta > 0
                      ? <TrendingUp className="w-4 h-4 text-emerald-500" />
                      : <TrendingDown className="w-4 h-4 text-red-400" />
                  )}
                </div>
                <p className="text-[10px] text-neutral-400 text-right">AI Visibility</p>
              </div>
            )}
            {hasResults && latestScan && (
              <Link
                to={`/scans/${latestScan.id}/opportunities`}
                className="flex items-center gap-1.5 rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
              >
                Opportunities
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            )}
          </div>
        </div>

        {project.description && (
          <p className="mt-2.5 text-xs text-neutral-500 leading-relaxed border-t border-neutral-100 pt-2.5 max-w-2xl">
            {project.description}
          </p>
        )}
        {error && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* ── PROVIDER SELECTION + SCAN TRIGGER ─────────────────────────────── */}
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold text-neutral-900">AI Providers</p>
            <p className="text-[11px] text-neutral-400 mt-0.5">
              Select which LLMs to scan — all run in parallel
            </p>
          </div>
          <div className="flex items-center gap-2">
            {configuredCount === 0 && (
              <Link to="/settings/integrations" className="flex items-center gap-1 text-xs text-amber-600 hover:underline">
                <Settings className="w-3 h-3" />
                Add API keys
              </Link>
            )}
            <button
              onClick={runFullScan}
              disabled={scanning || configuredCount === 0}
              type="button"
              className="flex items-center gap-2 btn-primary h-8 px-4 rounded-md text-xs font-semibold disabled:opacity-40"
            >
              {scanning ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" />{scanProgress || 'Scanning…'}</>
              ) : hasResults ? (
                <><RefreshCw className="w-3.5 h-3.5" />Re-run Scan</>
              ) : (
                <><Zap className="w-3.5 h-3.5" />Run Scan</>
              )}
            </button>
          </div>
        </div>

        {/* Provider cards */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-2">
          {PROVIDER_CONFIG.map((provider) => {
            const isConfigured = Boolean(integrationKeys[provider.keyName as keyof IntegrationKeys]?.trim())
            const isSelected = selectedProviders.includes(provider.id)
            const isDone = scanning && (providerResultCounts[provider.id] ?? 0) >= expectedPerProvider
            const isScanning = scanning && !isDone && isSelected

            return (
              <button
                key={provider.id}
                type="button"
                disabled={!isConfigured || scanning}
                onClick={() => {
                  if (!isConfigured) return
                  setSelectedProviders((prev) =>
                    prev.includes(provider.id)
                      ? prev.filter((p) => p !== provider.id)
                      : [...prev, provider.id]
                  )
                }}
                className={`relative text-left rounded-md border px-3 py-2.5 transition-all ${
                  !isConfigured
                    ? 'border-neutral-100 bg-neutral-50 opacity-60 cursor-not-allowed'
                    : isSelected
                      ? 'border-neutral-900 bg-neutral-900 text-white'
                      : 'border-neutral-200 bg-white hover:border-neutral-400'
                }`}
              >
                {/* Status indicator */}
                {scanning && isSelected ? (
                  isDone
                    ? <CheckCircle2 className="absolute top-2 right-2 w-3 h-3 text-emerald-400" />
                    : <Loader2 className="absolute top-2 right-2 w-3 h-3 animate-spin text-neutral-400" />
                ) : isConfigured ? (
                  isSelected
                    ? <CheckCircle2 className="absolute top-2 right-2 w-3 h-3 text-emerald-400" />
                    : <Circle className="absolute top-2 right-2 w-3 h-3 text-neutral-300" />
                ) : null}

                <p className={`text-[11px] font-semibold ${isSelected && !scanning ? 'text-white' : isSelected ? 'text-white/80' : 'text-neutral-900'}`}>
                  {provider.label}
                </p>
                <p className={`text-[10px] mt-0.5 ${isSelected && !scanning ? 'text-white/60' : 'text-neutral-400'}`}>
                  {isConfigured ? provider.sub : (
                    <Link
                      to="/settings/integrations"
                      className="hover:underline text-amber-500"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Add key →
                    </Link>
                  )}
                </p>

                {/* Scan progress bar */}
                {scanning && isSelected && (
                  <div className="mt-2 h-0.5 rounded-full bg-white/20 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${isDone ? 'bg-emerald-400' : 'bg-white/60'}`}
                      style={{ width: `${Math.min(100, ((providerResultCounts[provider.id] ?? 0) / expectedPerProvider) * 100)}%` }}
                    />
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {configuredCount > 0 && !scanning && (
          <p className="mt-2 text-[10px] text-neutral-400">
            {configuredCount} of {PROVIDER_CONFIG.length} providers selected · Click to toggle
          </p>
        )}
      </div>

      {/* ── EMPTY STATE ──────────────────────────────────────────────────────── */}
      {!hasResults && !scanning && (
        <div className="rounded-lg border border-neutral-200 bg-white px-6 py-12 text-center">
          <div className="mx-auto w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center mb-3">
            <Zap className="w-5 h-5 text-neutral-400" />
          </div>
          <h2 className="text-sm font-semibold text-neutral-900">No scan data yet</h2>
          <p className="mt-1 text-xs text-neutral-500 max-w-sm mx-auto leading-relaxed">
            Select your AI providers above and run a scan to see where {project.brand_name} appears across ChatGPT, Perplexity, Gemini, and more.
          </p>
        </div>
      )}

      {/* ── POST-SCAN INSIGHT HEADER ──────────────────────────────────────── */}
      {hasResults && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

          {/* Visibility stat */}
          <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Visibility</p>
            <div className="mt-1.5 flex items-end gap-2">
              <span className={`text-3xl font-bold ${
                overallScore != null && overallScore >= 60 ? 'text-emerald-600' : overallScore != null && overallScore >= 30 ? 'text-amber-600' : 'text-red-500'
              }`}>
                {results.filter((r) => r.brand_mentioned).length}
              </span>
              <span className="text-sm text-neutral-400 mb-0.5">/ {results.length} queries</span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">where AI mentions {project.brand_name}</p>
          </div>

          {/* Provider breakdown */}
          <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">By Provider</p>
            <div className="space-y-1.5">
              {[...activeProviders]
                .sort((a, b) => {
                  const rateA = providerStats[a] ? providerStats[a].mentioned / providerStats[a].total : 0
                  const rateB = providerStats[b] ? providerStats[b].mentioned / providerStats[b].total : 0
                  return rateB - rateA
                })
                .map((p) => {
                const s = providerStats[p]
                if (!s) return null
                const rate = Math.round((s.mentioned / s.total) * 100)
                return (
                  <div key={p} className="flex items-center gap-2">
                    <span className="text-[11px] w-16 text-neutral-600 font-medium">{providerLabels[p]}</span>
                    <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${rate >= 60 ? 'bg-emerald-500' : rate >= 30 ? 'bg-amber-400' : 'bg-red-400'}`}
                        style={{ width: `${rate}%` }}
                      />
                    </div>
                    <span className={`text-[11px] font-semibold w-8 text-right ${rate >= 60 ? 'text-emerald-600' : rate >= 30 ? 'text-amber-600' : 'text-red-500'}`}>
                      {rate}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Who AI recommends instead */}
          <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">AI Recommends Instead</p>
            {topCompetitors.length > 0 ? (
              <div className="space-y-1.5">
                {topCompetitors.map(([name, count]) => (
                  <div key={name} className="flex items-center justify-between">
                    <span className="text-[11px] text-neutral-700 font-medium truncate max-w-[120px]">{name}</span>
                    <span className="text-[10px] text-neutral-400">{count} mention{count !== 1 ? 's' : ''}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-neutral-400 mt-1">No competitors detected in responses.</p>
            )}
          </div>
        </div>
      )}

      {/* ── BLIND SPOTS ──────────────────────────────────────────────────────── */}
      {hasResults && blindSpots.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 px-1 mb-2">Top Blind Spots</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {blindSpots.map((row) => {
              const missing = activeProviders.filter((p) => !resultsLookup.get(`${row.query_id}:${p}`)?.brand_mentioned)
              const present = activeProviders.filter((p) => resultsLookup.get(`${row.query_id}:${p}`)?.brand_mentioned)
              const competitors = [...new Set(
                activeProviders.flatMap((p) => resultsLookup.get(`${row.query_id}:${p}`)?.competitors_mentioned ?? [])
              )].slice(0, 3)

              return (
                <div key={row.query_id} className="rounded-lg border border-red-100 bg-red-50 p-3.5">
                  <p className="text-[9px] font-bold uppercase tracking-wide text-red-400 mb-1">Blind Spot</p>
                  <p className="text-xs font-semibold text-neutral-900 leading-snug mb-2">"{row.query_text}"</p>
                  <div className="space-y-1">
                    {missing.length > 0 && (
                      <p className="text-[11px] text-red-600">
                        Missing from: {missing.map((p) => providerLabels[p]).join(', ')}
                      </p>
                    )}
                    {present.length > 0 && (
                      <p className="text-[11px] text-emerald-700">
                        Found in: {present.map((p) => providerLabels[p]).join(', ')}
                      </p>
                    )}
                    {competitors.length > 0 && (
                      <p className="text-[11px] text-neutral-500">
                        AI mentions: <span className="font-medium text-neutral-700">{competitors.join(', ')}</span>
                      </p>
                    )}
                  </div>
                  <Link
                    to={`/projects/${projectId}/queries/${row.query_id}`}
                    className="mt-2 inline-flex items-center gap-1 text-[11px] text-neutral-500 hover:text-neutral-900"
                  >
                    See history <ArrowUpRight className="w-3 h-3" />
                  </Link>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── TOP WINS ─────────────────────────────────────────────────────── */}
      {hasResults && topWins.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 px-1 mb-2">Top Wins</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {topWins.map((row) => {
              const allProviders = row.mentionedIn
              const bestPosition = allProviders.reduce<number | null>((best, p) => {
                const pos = resultsLookup.get(`${row.query_id}:${p}`)?.brand_position ?? null
                if (pos == null) return best
                return best == null || pos < best ? pos : best
              }, null)
              const missing = activeProviders.filter((p) => !resultsLookup.get(`${row.query_id}:${p}`)?.brand_mentioned)

              return (
                <div key={row.query_id} className="rounded-lg border border-emerald-100 bg-emerald-50 p-3.5">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[9px] font-bold uppercase tracking-wide text-emerald-500">Win</p>
                    {bestPosition != null && (
                      <span className="text-[10px] font-bold text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded">
                        #{bestPosition}
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-semibold text-neutral-900 leading-snug mb-2">"{row.query_text}"</p>
                  <div className="space-y-1">
                    <p className="text-[11px] text-emerald-700">
                      Mentioned in: {allProviders.map((p) => providerLabels[p]).join(', ')}
                    </p>
                    {missing.length > 0 && (
                      <p className="text-[11px] text-neutral-400">
                        Still missing: {missing.map((p) => providerLabels[p]).join(', ')}
                      </p>
                    )}
                  </div>
                  <Link
                    to={`/projects/${projectId}/queries/${row.query_id}`}
                    className="mt-2 inline-flex items-center gap-1 text-[11px] text-neutral-500 hover:text-neutral-900"
                  >
                    See history <ArrowUpRight className="w-3 h-3" />
                  </Link>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── VISIBILITY MATRIX ─────────────────────────────────────────────── */}
      {hasResults && latestScan && (
        <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
            <div>
              <p className="text-xs font-semibold text-neutral-900">Visibility Matrix</p>
              <p className="text-[10px] text-neutral-400 mt-0.5">Most invisible queries first · click any row to see AI responses</p>
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {(['all', ...INTENTS] as const).map((intent) => (
                <button
                  key={intent}
                  onClick={() => setIntentFilter(intent)}
                  type="button"
                  className={`h-6 px-2.5 rounded-full text-[10px] font-semibold border transition-colors ${
                    intentFilter === intent
                      ? 'bg-neutral-900 text-white border-neutral-900'
                      : 'bg-white text-neutral-500 border-neutral-200 hover:border-neutral-400'
                  }`}
                >
                  {intent === 'all' ? 'All' : intent}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-100 bg-neutral-50/50">
                  <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Query</th>
                  {activeProviders.map((p) => (
                    <th key={p} className="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-400 min-w-[90px]">
                      {providerLabels[p]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-50">
                {sortedRankings.map((row) => {
                  const intent = queryIntentMap.get(row.query_id)
                  const isExpanded = expandedQueryId === row.query_id
                  const allMissing = activeProviders.every((p) => !resultsLookup.get(`${row.query_id}:${p}`)?.brand_mentioned)

                  return (
                    <Fragment key={row.query_id}>
                      <tr
                        className={`cursor-pointer transition-colors ${isExpanded ? 'bg-neutral-50' : 'hover:bg-neutral-50/60'}`}
                        onClick={() => setExpandedQueryId(isExpanded ? null : row.query_id)}
                      >
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            {intent && (
                              <span className={`flex-shrink-0 text-[9px] font-bold uppercase tracking-wide rounded px-1.5 py-0.5 ${
                                allMissing ? 'bg-red-100 text-red-500' : 'bg-neutral-100 text-neutral-400'
                              }`}>{intent}</span>
                            )}
                            <span className="text-xs text-neutral-800 leading-snug">{row.query_text}</span>
                          </div>
                        </td>
                        {activeProviders.map((p) => (
                          <MatrixCell key={p} result={resultsLookup.get(`${row.query_id}:${p}`)} />
                        ))}
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={1 + activeProviders.length} className="bg-neutral-50 border-t border-neutral-100 px-4 py-4">
                            <div className="flex items-center justify-between mb-3">
                              <p className="text-xs font-semibold text-neutral-700">"{row.query_text}"</p>
                              <Link
                                to={`/projects/${projectId}/queries/${row.query_id}`}
                                className="flex items-center gap-1 text-[11px] text-neutral-400 hover:text-neutral-900"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Full history <ArrowUpRight className="w-3 h-3" />
                              </Link>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {activeProviders.map((provider) => {
                                const result = resultsLookup.get(`${row.query_id}:${provider}`)
                                if (!result) return null
                                return (
                                  <div key={provider} className={`rounded-md border p-3 bg-white ${result.brand_mentioned ? 'border-emerald-100' : 'border-red-100'}`}>
                                    <div className="flex items-center justify-between mb-2">
                                      <p className="text-[11px] font-bold text-neutral-700">{providerLabels[provider]}</p>
                                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                        result.brand_mentioned ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-500'
                                      }`}>
                                        {result.brand_mentioned
                                          ? (result.brand_position ? `#${result.brand_position}` : 'Mentioned')
                                          : 'Not mentioned'}
                                      </span>
                                    </div>
                                    {result.competitors_mentioned.length > 0 && (
                                      <p className="text-[10px] text-neutral-400 mb-2">
                                        Mentions: <span className="text-neutral-600 font-medium">{result.competitors_mentioned.slice(0, 4).join(', ')}</span>
                                      </p>
                                    )}
                                    {result.raw_response && (
                                      <HighlightedText
                                        className="text-[11px] text-neutral-500 leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto block"
                                        text={result.raw_response}
                                        terms={highlightTerms}
                                      />
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

          <div className="px-4 py-2 border-t border-neutral-100 bg-neutral-50/50">
            <p className="text-[10px] text-neutral-400">
              {sortedRankings.length} queries · Scan #{latestScan.id} · {new Date(latestScan.started_at).toLocaleString()}
              {latestScan.providers_used && ` · ${latestScan.providers_used}`}
            </p>
          </div>
        </div>
      )}

      {/* ── SCAN HISTORY ──────────────────────────────────────────────────── */}
      {scans.length > 0 && (
        <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold text-neutral-900 mb-3">Scan History</p>
          <div className="flex flex-wrap gap-2">
            {scans.map((scan) => {
              const score = scan.visibility_score != null ? Math.round(scan.visibility_score) : null
              const isLatest = scan.id === latestScan?.id
              const scoreColor = score == null ? 'text-neutral-400'
                : score >= 60 ? 'text-emerald-600'
                : score >= 30 ? 'text-amber-600'
                : 'text-red-500'

              const Inner = (
                <div className={`flex items-center gap-3 rounded-md border px-3 py-2 ${
                  isLatest ? 'border-neutral-900 bg-neutral-900' : 'border-neutral-200 hover:border-neutral-400'
                }`}>
                  <div>
                    <p className={`text-xl font-bold ${isLatest ? 'text-white' : scoreColor}`}>{score ?? '--'}</p>
                    <p className={`text-[10px] mt-0.5 ${isLatest ? 'text-neutral-400' : 'text-neutral-400'}`}>
                      {new Date(scan.started_at).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                    </p>
                  </div>
                  {isLatest && <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-400">Latest</span>}
                </div>
              )

              return scan.status === 'completed' ? (
                <Link key={scan.id} to={`/scans/${scan.id}`} className="transition-opacity hover:opacity-80">
                  {Inner}
                </Link>
              ) : (
                <div key={scan.id}>
                  <div className={`flex items-center gap-2 rounded-md border border-neutral-200 px-3 py-2`}>
                    <span className={`text-xl font-bold text-neutral-400`}>--</span>
                    <div>
                      <StatusBadge label={scan.status} variant={scanStatusVariant(scan.status)} />
                      <p className="text-[10px] text-neutral-400 mt-0.5">
                        {new Date(scan.started_at).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── QUERY MANAGER ─────────────────────────────────────────────────── */}
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <button
          type="button"
          onClick={() => setShowQueryManager(!showQueryManager)}
          className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-neutral-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold text-neutral-900">Manage Queries</p>
            <span className="text-[10px] text-neutral-400">
              {project.queries.filter((q) => q.is_active).length} active · {project.queries.length} total
            </span>
          </div>
          {showQueryManager
            ? <ChevronUp className="w-4 h-4 text-neutral-400" />
            : <ChevronDown className="w-4 h-4 text-neutral-400" />
          }
        </button>

        {showQueryManager && (
          <div className="border-t border-neutral-100 px-4 pb-4 pt-3">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_160px_72px] gap-2 mb-3">
              <input
                value={newQueryText}
                onChange={(e) => setNewQueryText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void handleAddQuery() }}
                placeholder="Add a query, e.g. best email marketing tools"
                className="h-9 rounded-md border border-neutral-200 px-3 text-xs outline-none focus:border-neutral-900 transition-colors"
              />
              <select
                value={newQueryIntent}
                onChange={(e) => setNewQueryIntent(e.target.value as (typeof INTENTS)[number])}
                className="h-9 rounded-md border border-neutral-200 px-3 text-xs outline-none focus:border-neutral-900"
              >
                {INTENTS.map((i) => <option key={i} value={i}>{i}</option>)}
              </select>
              <button
                onClick={handleAddQuery}
                disabled={queryMutationLoading || !newQueryText.trim()}
                className="btn-secondary h-9 px-3 rounded-md text-xs font-medium disabled:opacity-40"
                type="button"
              >Add</button>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <label className="cursor-pointer">
                <span className="btn-secondary px-2.5 py-1.5 rounded-md text-xs font-medium">Import CSV</span>
                <input type="file" accept=".csv" className="hidden" onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) { void handleImportQueries(file); e.currentTarget.value = '' }
                }} />
              </label>
              <span className="text-[10px] text-neutral-400">
                Columns: <code className="bg-neutral-100 px-1 rounded">query</code> + optional{' '}
                <code className="bg-neutral-100 px-1 rounded">search_volume</code>
              </span>
              {importingQueries && <span className="text-[10px] text-neutral-500 animate-pulse">Importing…</span>}
            </div>

            <div className="overflow-x-auto border border-neutral-100 rounded-md">
              <table className="w-full">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Query</th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Intent</th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Volume</th>
                    <th className="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                      <div className="flex flex-col items-center gap-0.5">
                        <span>Active</span>
                        <div className="flex gap-1">
                          <button type="button" onClick={() => void handleToggleAll(true)} className="text-[9px] text-neutral-500 hover:text-neutral-900 underline">All</button>
                          <span className="text-neutral-300">·</span>
                          <button type="button" onClick={() => void handleToggleAll(false)} className="text-[9px] text-neutral-500 hover:text-neutral-900 underline">None</button>
                        </div>
                      </div>
                    </th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-50">
                  {project.queries.map((query) => (
                    <tr key={query.id} className="hover:bg-neutral-50">
                      <td className="px-3 py-2 text-xs text-neutral-800 max-w-xs truncate">{query.text}</td>
                      <td className="px-3 py-2">
                        <StatusBadge label={query.intent_category} variant={intentBadgeVariant(query.intent_category)} />
                      </td>
                      <td className="px-3 py-2 text-xs text-neutral-400">{query.search_volume?.toLocaleString() ?? '—'}</td>
                      <td className="px-3 py-2 text-center">
                        <button
                          type="button"
                          role="switch"
                          aria-checked={query.is_active}
                          onClick={() => void handleToggleQuery(query.id, !query.is_active)}
                          className={`relative inline-flex h-4 w-7 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${query.is_active ? 'bg-neutral-900' : 'bg-neutral-200'}`}
                        >
                          <span className={`inline-block h-3 w-3 rounded-full bg-white shadow transform transition-transform duration-200 ${query.is_active ? 'translate-x-3' : 'translate-x-0'}`} />
                        </button>
                      </td>
                      <td className="px-3 py-2 text-right space-x-1">
                        <Link
                          to={`/projects/${projectId}/queries/${query.id}`}
                          className="inline-flex items-center h-6 px-2 rounded border border-neutral-200 text-[10px] text-neutral-600 hover:bg-neutral-50"
                        >
                          History
                        </Link>
                        <button
                          onClick={() => void handleDeleteQuery(query.id)}
                          disabled={queryMutationLoading}
                          type="button"
                          className="inline-flex items-center h-6 px-2 rounded border border-red-100 text-[10px] text-red-400 hover:bg-red-50 disabled:opacity-40"
                        >✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}

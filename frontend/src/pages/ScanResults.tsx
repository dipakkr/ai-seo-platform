import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProject, getProjectHistory, getScan, getScanResults } from '../api'
import type { Scan, ScanResult } from '../types'
import HighlightedText from '../components/HighlightedText'
import LoadingSpinner from '../components/LoadingSpinner'

const PROVIDERS = ['chatgpt', 'perplexity', 'gemini', 'claude', 'grok'] as const
const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
  grok: 'Grok',
}

type ProviderFilter = string | 'all'

export default function ScanResults() {
  const { id } = useParams<{ id: string }>()
  const scanId = Number(id)

  const [scan, setScan] = useState<Scan | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [projectBrandTerms, setProjectBrandTerms] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>('all')
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  const [history, setHistory] = useState<Scan[]>([])
  const [compareScanId, setCompareScanId] = useState<number | null>(null)
  const [compareResults, setCompareResults] = useState<ScanResult[]>([])

  useEffect(() => {
    async function load() {
      try {
        const [scanData, scanResults] = await Promise.all([getScan(scanId), getScanResults(scanId)])
        setScan(scanData)
        setResults(scanResults)

        const [project, projectHistory] = await Promise.all([
          getProject(scanData.project_id),
          getProjectHistory(scanData.project_id),
        ])
        setHistory(projectHistory)

        let domain = project.url
        try {
          domain = new URL(project.url).hostname.replace(/^www\./, '')
        } catch {
          // keep url fallback
        }
        setProjectBrandTerms([project.brand_name, domain, ...project.brand_aliases])

        const previous = projectHistory.find((s) => s.id !== scanId && s.status === 'completed')
        if (previous) {
          setCompareScanId(previous.id)
        }
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [id])

  useEffect(() => {
    async function loadCompare() {
      if (!compareScanId) {
        setCompareResults([])
        return
      }
      try {
        const data = await getScanResults(compareScanId)
        setCompareResults(data)
      } catch {
        setCompareResults([])
      }
    }

    void loadCompare()
  }, [compareScanId])

  const compareMap = useMemo(() => {
    const map = new Map<string, ScanResult>()
    for (const r of compareResults) {
      map.set(`${r.query_id}:${r.provider}`, r)
    }
    return map
  }, [compareResults])

  const grouped = useMemo(() => {
    const map = new Map<number, { text: string; providers: Map<string, ScanResult> }>()

    for (const result of results) {
      if (!map.has(result.query_id)) {
        map.set(result.query_id, {
          text: result.query_text ?? `Query #${result.query_id}`,
          providers: new Map(),
        })
      }
      map.get(result.query_id)!.providers.set(result.provider, result)
    }

    return [...map.entries()]
  }, [results])

  if (loading) return <LoadingSpinner text="Loading scan results..." />
  if (!scan) return <p className="text-sm text-neutral-500">Scan not found.</p>

  const activeProviders = PROVIDERS.filter((provider) => results.some((r) => r.provider === provider))
  const filteredRows = grouped.filter(([, row]) => providerFilter === 'all' || row.providers.has(providerFilter))

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <section className="surface p-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-neutral-400 font-semibold">Scan Overview</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">Ranked Result Matrix</h1>
            <p className="text-sm text-neutral-500 mt-1">
              {new Date(scan.started_at).toLocaleDateString()} · {scan.completed_queries}/{scan.total_queries} checks
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link to={`/scans/${scan.id}/opportunities`} className="btn-secondary h-10 px-4 rounded-md text-sm font-medium">
              Opportunities
            </Link>
            <Link to={`/projects/${scan.project_id}`} className="btn-primary h-10 px-4 rounded-md text-sm font-medium">
              Back to Project
            </Link>
          </div>
        </div>
      </section>

      <section className="surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          {/* Provider pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {(['all', ...activeProviders] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setProviderFilter(p)}
                className={`h-7 px-3 rounded-full text-xs font-medium border transition-colors ${
                  providerFilter === p
                    ? 'bg-neutral-900 text-white border-neutral-900'
                    : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400'
                }`}
              >
                {p === 'all' ? 'All Providers' : providerLabels[p] ?? p}
              </button>
            ))}
            <span className="text-[10px] text-neutral-400 ml-1">{filteredRows.length} queries</span>
          </div>

          {/* Compare select — keep as select, less critical */}
          {history.filter((s) => s.id !== scanId && s.status === 'completed').length > 0 && (
            <select
              value={compareScanId ?? ''}
              onChange={(e) => setCompareScanId(e.target.value ? Number(e.target.value) : null)}
              className="h-7 rounded-md border border-neutral-200 px-2 text-xs outline-none focus:border-neutral-900 text-neutral-600"
            >
              <option value="">Compare with…</option>
              {history
                .filter((s) => s.id !== scanId && s.status === 'completed')
                .map((s) => (
                  <option key={s.id} value={s.id}>Scan #{s.id}</option>
                ))}
            </select>
          )}
        </div>

        <div className="mt-4 overflow-x-auto border border-neutral-200 rounded-md">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-neutral-500 text-xs uppercase">
              <tr>
                <th className="px-3 py-2 text-left">Query</th>
                {activeProviders.map((provider) => (
                  <th key={provider} className="px-3 py-2 text-left">{providerLabels[provider]}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {filteredRows.map(([queryId, row]) => (
                <Fragment key={queryId}>
                  <tr
                    className="hover:bg-neutral-50 cursor-pointer"
                    onClick={() => setExpandedRow(expandedRow === queryId ? null : queryId)}
                  >
                    <td className="px-3 py-2.5 text-neutral-800 max-w-sm truncate">{row.text}</td>
                    {activeProviders.map((provider) => {
                      const result = row.providers.get(provider)
                      if (!result) {
                        return <td key={provider} className="px-3 py-2.5 text-neutral-300">--</td>
                      }

                      const topThree = result.brands_ranked
                        .filter((brand) => brand.position != null)
                        .sort((a, b) => (a.position ?? 999) - (b.position ?? 999))
                        .slice(0, 3)

                      const previous = compareMap.get(`${queryId}:${provider}`)
                      let deltaText = ''
                      if (previous && result.brand_position && previous.brand_position) {
                        const delta = previous.brand_position - result.brand_position
                        if (delta > 0) deltaText = `+${delta}`
                        if (delta < 0) deltaText = `${delta}`
                      }

                      return (
                        <td key={provider} className="px-3 py-2.5 align-top">
                          {topThree.length > 0 ? (
                            <div className="space-y-1">
                              {topThree.map((brand) => (
                                <div
                                  key={brand.name}
                                  className={`text-xs ${brand.is_your_brand ? 'inline-block rounded bg-neutral-900 px-1.5 py-0.5 text-white' : 'text-neutral-700'}`}
                                >
                                  {brand.position}. {brand.name}
                                </div>
                              ))}
                              {deltaText && (
                                <div className={`text-[10px] ${deltaText.startsWith('+') ? 'text-emerald-700' : 'text-red-700'}`}>
                                  vs previous: {deltaText}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${
                              result.brand_mentioned
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-red-50 text-red-500'
                            }`}>
                              {result.brand_mentioned ? 'Mentioned' : 'Not mentioned'}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>

                  {expandedRow === queryId && (
                    <tr>
                      <td colSpan={1 + activeProviders.length} className="bg-neutral-50 px-3 py-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {activeProviders.map((provider) => {
                            const result = row.providers.get(provider)
                            if (!result) return null

                            const previous = compareMap.get(`${queryId}:${provider}`)

                            return (
                              <div key={provider} className="surface-muted p-3">
                                <p className="text-xs font-semibold text-neutral-700">{providerLabels[provider]}</p>
                                {previous && (
                                  <p className="text-[11px] text-neutral-500 mt-1">
                                    Previous position: {previous.brand_position ? `#${previous.brand_position}` : 'missing'}
                                  </p>
                                )}
                                <p className="text-xs text-neutral-600 mt-1 leading-relaxed">
                                  {result.brands_ranked.map((brand) => (
                                    <span
                                      key={brand.name}
                                      className={brand.is_your_brand ? 'mr-1 rounded bg-neutral-900 px-1 text-white' : 'mr-1'}
                                    >
                                      {brand.position ? `${brand.position}. ` : ''}{brand.name}
                                    </span>
                                  ))}
                                </p>

                                {result.raw_response && (
                                  <div className="mt-2 rounded-md bg-neutral-50 border border-neutral-100 p-2.5 max-h-44 overflow-y-auto">
                                    <HighlightedText
                                      className="text-xs text-neutral-600 whitespace-pre-wrap leading-relaxed block"
                                      text={result.raw_response}
                                      terms={projectBrandTerms}
                                    />
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

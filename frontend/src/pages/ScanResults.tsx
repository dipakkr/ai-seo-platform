import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getScan, getScanResults } from '../api'
import type { Scan, ScanResult } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'

const PROVIDERS = ['chatgpt', 'perplexity', 'gemini', 'claude'] as const
const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

type ProviderFilter = string | 'all'

export default function ScanResults() {
  const { id } = useParams<{ id: string }>()
  const scanId = Number(id)

  const [scan, setScan] = useState<Scan | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>('all')
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [scanData, scanResults] = await Promise.all([getScan(scanId), getScanResults(scanId)])
        setScan(scanData)
        setResults(scanResults)
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [id])

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
        <div className="flex items-center gap-2">
          <select
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="h-9 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-900"
          >
            <option value="all">All Providers</option>
            {activeProviders.map((provider) => (
              <option key={provider} value={provider}>{providerLabels[provider]}</option>
            ))}
          </select>
          <span className="text-xs text-neutral-400">{filteredRows.length} queries</span>
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
                            </div>
                          ) : (
                            <span className="text-xs text-neutral-400">No parsed ranking</span>
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

                            return (
                              <div key={provider} className="surface-muted p-3">
                                <p className="text-xs font-semibold text-neutral-700">{providerLabels[provider]}</p>
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
                                  <details className="mt-2">
                                    <summary className="text-xs text-neutral-500 cursor-pointer">Full response</summary>
                                    <p className="text-xs text-neutral-600 mt-1 whitespace-pre-wrap max-h-40 overflow-y-auto">
                                      {result.raw_response}
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
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, ChevronDown, ChevronUp } from 'lucide-react'
import { getScan, getScanOpportunities } from '../api'
import type { Opportunity, Scan } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'

// ── Type config (minimal — just colors and labels) ───────────────────────────
const TYPE_CONFIG = {
  invisible: {
    label: 'Invisible',
    description: 'Not mentioned by any AI',
    dot: 'bg-red-400',
    badge: 'bg-red-50 text-red-600',
    bar: 'bg-red-400',
  },
  competitor_dominated: {
    label: 'Competitor Dominated',
    description: 'Rivals rank above you',
    dot: 'bg-orange-400',
    badge: 'bg-orange-50 text-orange-600',
    bar: 'bg-orange-400',
  },
  partial_visibility: {
    label: 'Partial Visibility',
    description: 'Some LLMs miss you',
    dot: 'bg-amber-400',
    badge: 'bg-amber-50 text-amber-600',
    bar: 'bg-amber-400',
  },
  negative_sentiment: {
    label: 'Negative Sentiment',
    description: 'Mentioned unfavorably',
    dot: 'bg-purple-400',
    badge: 'bg-purple-50 text-purple-600',
    bar: 'bg-purple-400',
  },
} as const

type OpportunityType = keyof typeof TYPE_CONFIG

const PROVIDER_LABELS: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
  grok: 'Grok',
}

// ── Single opportunity row ───────────────────────────────────────────────────
function OpportunityRow({ opportunity, rank }: { opportunity: Opportunity; rank: number }) {
  const [expanded, setExpanded] = useState(rank <= 3) // auto-expand top 3
  const type = opportunity.opportunity_type as OpportunityType
  const cfg = TYPE_CONFIG[type] ?? TYPE_CONFIG.invisible

  const impactLabel = opportunity.impact_score >= 5000 ? 'High' : opportunity.impact_score >= 1000 ? 'Medium' : 'Low'
  const gapPct = Math.round(opportunity.visibility_gap * 100)

  const queryLabel = opportunity.query_text ?? `Query #${opportunity.query_id}`

  return (
    <div className={`border-t border-neutral-100 ${rank === 1 ? 'border-t-0' : ''}`}>
      {/* Row header — always visible */}
      <button
        type="button"
        className="w-full text-left px-4 py-3.5 hover:bg-neutral-50/60 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-start gap-3">
          {/* Rank */}
          <span className="flex-shrink-0 text-xs font-bold text-neutral-300 w-5 pt-0.5 text-right">
            {rank}
          </span>

          {/* Type dot */}
          <span className={`flex-shrink-0 w-1.5 h-1.5 rounded-full mt-1.5 ${cfg.dot}`} />

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium text-neutral-900 leading-snug">
                {queryLabel}
              </p>
              <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${cfg.badge}`}>
                  {cfg.label}
                </span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                  impactLabel === 'High' ? 'text-red-500 bg-red-50'
                  : impactLabel === 'Medium' ? 'text-amber-600 bg-amber-50'
                  : 'text-neutral-400 bg-neutral-100'
                }`}>
                  {impactLabel}
                </span>
                {expanded
                  ? <ChevronUp className="w-3.5 h-3.5 text-neutral-300" />
                  : <ChevronDown className="w-3.5 h-3.5 text-neutral-300" />
                }
              </div>
            </div>

            {/* Compact meta row — always visible */}
            <div className="mt-1.5 flex items-center gap-3 flex-wrap">
              {/* Visibility gap bar */}
              <div className="flex items-center gap-1.5">
                <div className="w-16 h-1 bg-neutral-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${gapPct}%` }} />
                </div>
                <span className="text-[10px] text-neutral-400">{gapPct}% gap</span>
              </div>

              {/* Competitors (inline preview) */}
              {opportunity.competitors_visible.length > 0 && (
                <span className="text-[10px] text-neutral-400">
                  AI mentions: <span className="text-neutral-600 font-medium">
                    {opportunity.competitors_visible.slice(0, 3).join(', ')}
                  </span>
                </span>
              )}

              {/* Missing providers (inline preview) */}
              {opportunity.providers_missing.length > 0 && (
                <span className="text-[10px] text-neutral-400">
                  Missing from: <span className="text-neutral-600 font-medium">
                    {opportunity.providers_missing.map((p) => PROVIDER_LABELS[p] ?? p).join(', ')}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Expanded recommendation */}
      {expanded && opportunity.recommendation && (
        <div className="pl-12 pr-4 pb-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1.5">
            Recommended action
          </p>
          <p className="text-xs text-neutral-600 leading-relaxed">
            {opportunity.recommendation}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Opportunities() {
  const { id } = useParams<{ id: string }>()
  const scanId = Number(id)

  const [scan, setScan] = useState<Scan | null>(null)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<OpportunityType | 'all'>('all')

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
    return opportunities.filter((o) => o.opportunity_type === typeFilter)
  }, [typeFilter, opportunities])

  const typeCounts = useMemo(() => {
    const counts: Partial<Record<OpportunityType, number>> = {}
    for (const o of opportunities) {
      const t = o.opportunity_type as OpportunityType
      counts[t] = (counts[t] ?? 0) + 1
    }
    return counts
  }, [opportunities])

  if (loading) return <LoadingSpinner text="Loading opportunities…" />
  if (!scan) return <p className="text-sm text-neutral-500">Scan not found.</p>

  return (
    <div className="max-w-3xl mx-auto space-y-4">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-neutral-400 mb-2">
            <Link
              to={`/projects/${scan.project_id}`}
              className="flex items-center gap-1 hover:text-neutral-700 transition-colors"
            >
              <ArrowLeft className="w-3 h-3" />
              Project
            </Link>
            <span>/</span>
            <Link
              to={`/scans/${scanId}`}
              className="flex items-center gap-1 hover:text-neutral-700 transition-colors"
            >
              Result Matrix
              <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
          <h1 className="text-lg font-semibold text-neutral-900">Recommended Next Moves</h1>
          <p className="text-xs text-neutral-400 mt-0.5">
            {opportunities.length} opportunities · ranked by impact ·{' '}
            {new Date(scan.started_at).toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
      </div>

      {/* ── Type summary + filter pills ───────────────────────────────────── */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          type="button"
          onClick={() => setTypeFilter('all')}
          className={`h-7 px-3 rounded-full text-xs font-medium border transition-colors ${
            typeFilter === 'all'
              ? 'bg-neutral-900 text-white border-neutral-900'
              : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400'
          }`}
        >
          All ({opportunities.length})
        </button>
        {(Object.entries(TYPE_CONFIG) as [OpportunityType, typeof TYPE_CONFIG[OpportunityType]][]).map(([type, cfg]) => {
          const count = typeCounts[type] ?? 0
          if (count === 0) return null
          const isActive = typeFilter === type
          return (
            <button
              key={type}
              type="button"
              onClick={() => setTypeFilter(isActive ? 'all' : type)}
              className={`h-7 px-3 rounded-full text-xs font-medium border transition-colors flex items-center gap-1.5 ${
                isActive
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-white/60' : cfg.dot}`} />
              {cfg.label} ({count})
            </button>
          )
        })}
      </div>

      {/* ── Opportunity list ──────────────────────────────────────────────── */}
      {filtered.length > 0 ? (
        <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
          {filtered.map((opportunity, idx) => (
            <OpportunityRow key={opportunity.id} opportunity={opportunity} rank={idx + 1} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white px-6 py-14 text-center">
          <p className="text-2xl mb-2">✓</p>
          <p className="text-sm font-medium text-neutral-700">No opportunities in this category</p>
          <p className="text-xs text-neutral-400 mt-1">Try a different filter or run another scan.</p>
        </div>
      )}

    </div>
  )
}

import type { ScanResult } from '../types'

interface Props {
  results: ScanResult[]
}

const PROVIDERS = ['chatgpt', 'perplexity', 'gemini', 'claude'] as const

const providerLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

const providerColors: Record<string, string> = {
  chatgpt: 'bg-green-500',
  perplexity: 'bg-blue-500',
  gemini: 'bg-purple-500',
  claude: 'bg-orange-500',
}

function computeProviderScores(results: ScanResult[]): Record<string, number> {
  const scores: Record<string, number> = {}
  for (const provider of PROVIDERS) {
    const providerResults = results.filter((r) => r.provider === provider)
    if (providerResults.length === 0) {
      scores[provider] = 0
      continue
    }
    const mentioned = providerResults.filter((r) => r.brand_mentioned).length
    scores[provider] = Math.round((mentioned / providerResults.length) * 100)
  }
  return scores
}

export default function LLMBreakdown({ results }: Props) {
  const scores = computeProviderScores(results)

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">Per-LLM Visibility</h3>
      {PROVIDERS.map((provider) => {
        const score = scores[provider] ?? 0
        const hasData = results.some((r) => r.provider === provider)
        return (
          <div key={provider} className="flex items-center gap-3">
            <span className="text-sm text-gray-600 w-24">{providerLabels[provider]}</span>
            <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
              {hasData ? (
                <div
                  className={`h-full ${providerColors[provider]} rounded-full transition-all duration-500`}
                  style={{ width: `${score}%` }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-gray-400">
                  No data
                </div>
              )}
            </div>
            <span className="text-sm font-medium text-gray-700 w-10 text-right">
              {hasData ? `${score}%` : '--'}
            </span>
          </div>
        )
      })}
    </div>
  )
}

interface CategoryProps {
  results: ScanResult[]
  queries: { id: number; intent_category: string }[]
}

export function CategoryBreakdown({ results, queries }: CategoryProps) {
  const categories = ['discovery', 'comparison', 'problem', 'recommendation']
  const categoryLabels: Record<string, string> = {
    discovery: 'Discovery',
    comparison: 'Comparison',
    problem: 'Problem',
    recommendation: 'Recommendation',
  }

  const queryIdToCategory: Record<number, string> = {}
  for (const q of queries) {
    queryIdToCategory[q.id] = q.intent_category
  }

  const scores: Record<string, number> = {}
  for (const cat of categories) {
    const catResults = results.filter((r) => queryIdToCategory[r.query_id] === cat)
    if (catResults.length === 0) {
      scores[cat] = 0
      continue
    }
    const mentioned = catResults.filter((r) => r.brand_mentioned).length
    scores[cat] = Math.round((mentioned / catResults.length) * 100)
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">Per-Category Visibility</h3>
      {categories.map((cat) => {
        const score = scores[cat]
        return (
          <div key={cat} className="flex items-center gap-3">
            <span className="text-sm text-gray-600 w-24">{categoryLabels[cat]}</span>
            <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-sm font-medium text-gray-700 w-10 text-right">{score}%</span>
          </div>
        )
      })}
    </div>
  )
}

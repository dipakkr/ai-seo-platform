import type { Opportunity } from '../types'
import StatusBadge, { opportunityBadgeVariant } from './StatusBadge'

interface Props {
  opportunity: Opportunity
}

const typeLabels: Record<string, string> = {
  invisible: 'Invisible',
  competitor_dominated: 'Competitor Dominated',
  partial_visibility: 'Partial Visibility',
  negative_sentiment: 'Negative Sentiment',
}

export default function OpportunityCard({ opportunity }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="text-sm font-medium text-gray-900 flex-1">
          "{opportunity.query_text ?? `Query #${opportunity.query_id}`}"
        </h4>
        <StatusBadge
          label={typeLabels[opportunity.opportunity_type] ?? opportunity.opportunity_type}
          variant={opportunityBadgeVariant(opportunity.opportunity_type)}
        />
      </div>

      <div className="flex items-center gap-4 mb-3 text-xs text-gray-500">
        <span>
          Impact:{' '}
          <span className="font-semibold text-gray-900">{opportunity.impact_score.toFixed(1)}</span>
        </span>
        <span>
          Gap: <span className="font-semibold text-gray-900">{(opportunity.visibility_gap * 100).toFixed(0)}%</span>
        </span>
      </div>

      {opportunity.competitors_visible.length > 0 && (
        <div className="mb-2">
          <span className="text-xs text-gray-500">Competitors visible: </span>
          <span className="text-xs text-gray-700">
            {opportunity.competitors_visible.join(', ')}
          </span>
        </div>
      )}

      {opportunity.providers_missing.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500">Missing from: </span>
          <span className="text-xs text-gray-700">
            {opportunity.providers_missing.join(', ')}
          </span>
        </div>
      )}

      {opportunity.recommendation && (
        <p className="text-xs text-gray-600 bg-gray-50 rounded p-2 leading-relaxed">
          {opportunity.recommendation}
        </p>
      )}
    </div>
  )
}

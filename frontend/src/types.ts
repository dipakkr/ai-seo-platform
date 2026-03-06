export interface Project {
  id: number
  url: string
  brand_name: string
  brand_aliases: string[]
  description: string
  category: string
  competitors: string[]
  features: string[]
  target_audience: string
  created_at: string
  updated_at: string
}

export interface Query {
  id: number
  project_id: number
  text: string
  intent_category: 'discovery' | 'comparison' | 'problem' | 'recommendation'
  search_volume: number | null
  volume_source: string | null
  is_active: boolean
}

export interface Scan {
  id: number
  project_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  providers_used: string
  total_queries: number
  completed_queries: number
  visibility_score: number | null
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface ScanResult {
  id: number
  scan_id: number
  query_id: number
  query_text?: string
  provider: 'chatgpt' | 'perplexity' | 'gemini' | 'claude'
  raw_response: string
  brand_mentioned: boolean
  brand_position: number | null
  brand_sentiment: 'positive' | 'neutral' | 'negative' | null
  brand_context: string | null
  competitors_mentioned: string[]
  citations: string[]
  brand_cited: boolean
  response_tokens: number | null
  latency_ms: number | null
}

export interface Opportunity {
  id: number
  scan_id: number
  query_id: number
  query_text?: string
  opportunity_type: 'invisible' | 'competitor_dominated' | 'negative_sentiment' | 'partial_visibility'
  impact_score: number
  visibility_gap: number
  competitors_visible: string[]
  providers_missing: string[]
  recommendation: string
}

export interface ProjectWithQueries extends Project {
  queries: Query[]
}

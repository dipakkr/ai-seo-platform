import type {
  BrandRankingEntry,
  Project,
  ProjectWithQueries,
  Query,
  QueryRankings,
  Scan,
  ScanResult,
  Opportunity,
} from './types'
import { getIntegrationHeaders } from './integrations'

const BASE_URL = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...getIntegrationHeaders(),
      ...options?.headers,
    },
    ...options,
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }

  return res.json()
}

export async function listProjects(): Promise<Project[]> {
  return request('/api/v1/projects')
}

export async function createProject(url: string): Promise<ProjectWithQueries> {
  return request('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export async function updateProject(
  id: number,
  data: { brand_name?: string }
): Promise<ProjectWithQueries> {
  return request(`/api/v1/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function getProject(id: number): Promise<ProjectWithQueries> {
  return request(`/api/v1/projects/${id}`)
}

export async function triggerScan(
  projectId: number,
  providers?: string[],
): Promise<{ scan_id: number; status: string }> {
  return request(`/api/v1/projects/${projectId}/scan`, {
    method: 'POST',
    body: JSON.stringify(providers?.length ? { providers } : {}),
  })
}

export async function getScan(scanId: number): Promise<Scan> {
  return request(`/api/v1/scans/${scanId}`)
}

export async function getScanResults(
  scanId: number,
  options?: { queryId?: number }
): Promise<ScanResult[]> {
  const params = new URLSearchParams()
  if (options?.queryId != null) {
    params.set('query_id', String(options.queryId))
  }
  const query = params.toString()
  return request(`/api/v1/scans/${scanId}/results${query ? `?${query}` : ''}`)
}

export async function getScanRankings(scanId: number): Promise<QueryRankings[]> {
  return request(`/api/v1/scans/${scanId}/rankings`)
}

export async function getScanOpportunities(scanId: number): Promise<Opportunity[]> {
  return request(`/api/v1/scans/${scanId}/opportunities`)
}

export async function getProjectHistory(projectId: number): Promise<Scan[]> {
  return request(`/api/v1/projects/${projectId}/history`)
}

export interface SingleQueryResult {
  provider: string
  raw_response: string
  brand_mentioned: boolean
  brand_position: number | null
  brand_sentiment: string | null
  brand_context: string | null
  competitors_mentioned: string[]
  citations: string[]
  brand_cited: boolean
  brands_ranked: BrandRankingEntry[]
  latency_ms: number | null
  error: boolean
}

export interface SingleQueryScanResponse {
  query_id: number
  query_text: string
  results: SingleQueryResult[]
}

export async function scanSingleQuery(queryId: number): Promise<SingleQueryScanResponse> {
  return request(`/api/v1/queries/${queryId}/scan`, {
    method: 'POST',
  })
}

export async function addQuery(
  projectId: number,
  text: string,
  intentCategory: string,
  searchVolume?: number
): Promise<Query> {
  return request(`/api/v1/projects/${projectId}/queries`, {
    method: 'POST',
    body: JSON.stringify({
      text,
      intent_category: intentCategory,
      search_volume: searchVolume ?? null,
    }),
  })
}

export async function updateQuery(
  queryId: number,
  data: { text?: string; intent_category?: string; is_active?: boolean; search_volume?: number }
): Promise<Query> {
  return request(`/api/v1/queries/${queryId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteQuery(queryId: number): Promise<void> {
  const url = `${BASE_URL}/api/v1/queries/${queryId}`
  const res = await fetch(url, {
    method: 'DELETE',
    headers: {
      ...getIntegrationHeaders(),
    },
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
}

export interface IntegrationTestResult {
  provider: string
  configured: boolean
  success: boolean
  model: string | null
  latency_ms: number | null
  error: string | null
}

export async function testIntegration(provider: string): Promise<IntegrationTestResult> {
  return request('/api/v1/integrations/test', {
    method: 'POST',
    body: JSON.stringify({ provider }),
  })
}

import type {
  Project,
  ProjectWithQueries,
  Scan,
  ScanResult,
  Opportunity,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
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

export async function getProject(id: number): Promise<ProjectWithQueries> {
  return request(`/api/v1/projects/${id}`)
}

export async function triggerScan(projectId: number): Promise<{ scan_id: number; status: string }> {
  return request(`/api/v1/projects/${projectId}/scan`, {
    method: 'POST',
  })
}

export async function getScan(scanId: number): Promise<Scan> {
  return request(`/api/v1/scans/${scanId}`)
}

export async function getScanResults(scanId: number): Promise<ScanResult[]> {
  return request(`/api/v1/scans/${scanId}/results`)
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

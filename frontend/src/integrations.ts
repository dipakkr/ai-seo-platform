export type IntegrationKeys = {
  openai_api_key: string
  anthropic_api_key: string
  google_api_key: string
  perplexity_api_key: string
  xai_api_key: string
}

const STORAGE_KEY = 'aiseo_integration_keys'

const EMPTY_KEYS: IntegrationKeys = {
  openai_api_key: '',
  anthropic_api_key: '',
  google_api_key: '',
  perplexity_api_key: '',
  xai_api_key: '',
}

export function getIntegrationKeys(): IntegrationKeys {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return { ...EMPTY_KEYS }

  try {
    const parsed = JSON.parse(raw) as Partial<IntegrationKeys>
    return {
      openai_api_key: parsed.openai_api_key ?? '',
      anthropic_api_key: parsed.anthropic_api_key ?? '',
      google_api_key: parsed.google_api_key ?? '',
      perplexity_api_key: parsed.perplexity_api_key ?? '',
      xai_api_key: parsed.xai_api_key ?? '',
    }
  } catch {
    return { ...EMPTY_KEYS }
  }
}

export function saveIntegrationKeys(keys: IntegrationKeys): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys))
}

export function getIntegrationHeaders(): Record<string, string> {
  const keys = getIntegrationKeys()
  const headers: Record<string, string> = {}

  if (keys.openai_api_key.trim()) {
    headers['X-OpenAI-Api-Key'] = keys.openai_api_key.trim()
  }
  if (keys.anthropic_api_key.trim()) {
    headers['X-Anthropic-Api-Key'] = keys.anthropic_api_key.trim()
  }
  if (keys.google_api_key.trim()) {
    headers['X-Google-Api-Key'] = keys.google_api_key.trim()
  }
  if (keys.perplexity_api_key.trim()) {
    headers['X-Perplexity-Api-Key'] = keys.perplexity_api_key.trim()
  }
  if (keys.xai_api_key.trim()) {
    headers['X-XAI-Api-Key'] = keys.xai_api_key.trim()
  }

  return headers
}

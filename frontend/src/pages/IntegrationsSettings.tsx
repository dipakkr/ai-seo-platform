import { useMemo, useState } from 'react'
import { testIntegration, type IntegrationTestResult } from '../api'
import {
  getIntegrationKeys,
  saveIntegrationKeys,
  type IntegrationKeys,
} from '../integrations'

type ProviderKey = keyof IntegrationKeys

type SettingsSection = {
  id: string
  label: string
  description: string
  enabled: boolean
}

const SETTINGS_SECTIONS: SettingsSection[] = [
  { id: 'integrations', label: 'Integrations', description: 'Provider keys and status', enabled: true },
  { id: 'workspace', label: 'Workspace', description: 'Defaults and limits', enabled: false },
  { id: 'notifications', label: 'Notifications', description: 'Digest and alerts', enabled: false },
  { id: 'security', label: 'Security', description: 'Policies and roles', enabled: false },
]

const PROVIDERS: Array<{ key: ProviderKey; label: string; apiProvider: string; hint: string }> = [
  {
    key: 'openai_api_key',
    label: 'OpenAI',
    apiProvider: 'chatgpt',
    hint: 'Used by ChatGPT provider and extraction fallback.',
  },
  {
    key: 'anthropic_api_key',
    label: 'Anthropic',
    apiProvider: 'claude',
    hint: 'Used by Claude provider and extraction fallback.',
  },
  {
    key: 'google_api_key',
    label: 'Google',
    apiProvider: 'gemini',
    hint: 'Used by Gemini provider and extraction fallback.',
  },
  {
    key: 'perplexity_api_key',
    label: 'Perplexity',
    apiProvider: 'perplexity',
    hint: 'Used by Perplexity provider for ranking scans.',
  },
  {
    key: 'xai_api_key',
    label: 'xAI (Grok)',
    apiProvider: 'grok',
    hint: 'Used by Grok provider (xAI API). Get key at console.x.ai.',
  },
]

export default function IntegrationsSettings() {
  const [keys, setKeys] = useState<IntegrationKeys>(getIntegrationKeys())
  const [saved, setSaved] = useState(false)
  const [testing, setTesting] = useState<Record<string, boolean>>({})
  const [results, setResults] = useState<Record<string, IntegrationTestResult>>({})

  const anyKey = useMemo(() => Object.values(keys).some((value) => value.trim()), [keys])

  function onKeyChange(field: ProviderKey, value: string) {
    const updated = { ...keys, [field]: value }
    setKeys(updated)
    // Persist immediately so headers are sent on next request (including Test)
    saveIntegrationKeys(updated)
    setSaved(true)
    setTimeout(() => setSaved(false), 1200)
  }

  function onSave() {
    saveIntegrationKeys(keys)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  function onClear() {
    const cleared: IntegrationKeys = {
      openai_api_key: '',
      anthropic_api_key: '',
      google_api_key: '',
      perplexity_api_key: '',
      xai_api_key: '',
    }
    setKeys(cleared)
    saveIntegrationKeys(cleared)
    setResults({})
  }

  async function onTest(provider: string) {
    setTesting((prev) => ({ ...prev, [provider]: true }))
    try {
      const result = await testIntegration(provider)
      setResults((prev) => ({ ...prev, [provider]: result }))
    } finally {
      setTesting((prev) => ({ ...prev, [provider]: false }))
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">Settings</h1>
        <p className="text-sm text-neutral-500 mt-1">Manage platform-level configuration</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        <aside className="surface p-3 h-fit">
          <p className="px-2 pb-2 text-[11px] uppercase tracking-wide text-neutral-400 font-semibold">Sections</p>
          <div className="space-y-1">
            {SETTINGS_SECTIONS.map((section) => (
              <button
                key={section.id}
                type="button"
                disabled={!section.enabled}
                className={`w-full text-left rounded-md border px-2.5 py-2 ${
                  section.enabled
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-transparent text-neutral-500 hover:bg-neutral-50'
                }`}
              >
                <p className="text-sm font-medium">{section.label}</p>
                <p className={`text-xs mt-0.5 ${section.enabled ? 'text-neutral-300' : 'text-neutral-400'}`}>
                  {section.description}
                </p>
              </button>
            ))}
          </div>
        </aside>

        <section className="lg:col-span-3 surface p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">Integrations</h2>
              <p className="text-sm text-neutral-500 mt-1">
                Keys are stored in browser local storage and passed to API through request headers.
              </p>
            </div>
            {saved && (
              <span className="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-md">
                Saved
              </span>
            )}
          </div>

          {PROVIDERS.map((provider) => {
            const result = results[provider.apiProvider]
            const hasKey = keys[provider.key].trim().length > 0

            return (
              <div key={provider.key} className="surface-muted p-4">
                <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-medium text-neutral-900">{provider.label} API Key</p>
                    <p className="text-xs text-neutral-500 mt-1">{provider.hint}</p>
                  </div>
                  <button
                    onClick={() => onTest(provider.apiProvider)}
                    disabled={testing[provider.apiProvider] || !hasKey}
                    className="btn-secondary h-9 px-3 rounded-md text-xs font-medium disabled:opacity-40"
                  >
                    {testing[provider.apiProvider] ? 'Testing...' : 'Test Connection'}
                  </button>
                </div>

                <input
                  type="password"
                  value={keys[provider.key]}
                  onChange={(e) => onKeyChange(provider.key, e.target.value)}
                  placeholder="sk-..."
                  className="mt-3 w-full h-10 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-900"
                />

                {result && (
                  <p className={`text-xs mt-2 ${result.success ? 'text-emerald-700' : 'text-red-700'}`}>
                    {result.success
                      ? `Connected${result.model ? ` (${result.model})` : ''}${result.latency_ms != null ? ` in ${result.latency_ms}ms` : ''}`
                      : result.error || 'Connection failed'}
                  </p>
                )}
              </div>
            )
          })}

          <div className="flex items-center justify-between pt-2">
            <button onClick={onClear} className="btn-secondary h-10 px-4 rounded-md text-sm font-medium">
              Clear All
            </button>
            <button
              onClick={onSave}
              disabled={!anyKey}
              className="btn-primary h-10 px-4 rounded-md text-sm font-medium disabled:opacity-40"
            >
              Save Changes
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

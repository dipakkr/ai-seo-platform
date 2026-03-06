import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ProjectSetup() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)

    try {
      const project = await createProject(url.trim())
      navigate(`/projects/${project.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI Visibility Scanner
        </h1>
        <p className="text-gray-500">
          Paste your website URL to see how visible your brand is across ChatGPT, Perplexity, Gemini, and Claude.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
          Website URL
        </label>
        <div className="flex gap-3">
          <input
            id="url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourproduct.com"
            required
            disabled={loading}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Analyzing...' : 'Scan'}
          </button>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}

        {loading && (
          <div className="mt-6">
            <LoadingSpinner text="Extracting brand profile and generating queries..." />
          </div>
        )}
      </form>

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { title: 'Auto-detect brand', desc: 'Extracts name, category, competitors, and features from your site.' },
          { title: 'Generate queries', desc: 'Creates buyer-intent queries people ask AI search engines.' },
          { title: 'Scan & score', desc: 'Checks visibility across 4 LLMs and ranks opportunities.' },
        ].map((step, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="w-7 h-7 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold mb-2">
              {i + 1}
            </div>
            <h3 className="text-sm font-semibold text-gray-900 mb-1">{step.title}</h3>
            <p className="text-xs text-gray-500 leading-relaxed">{step.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

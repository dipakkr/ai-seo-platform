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
    <div className="max-w-4xl mx-auto space-y-6">
      <section className="surface p-8">
        <p className="text-xs uppercase tracking-wider text-neutral-400 font-semibold">Get Started</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-neutral-900">
          Create Your First Visibility Project
        </h1>
        <p className="mt-2 text-sm text-neutral-500 max-w-2xl">
          GEOkit profiles your product, generates AI-search queries, then scans ChatGPT, Perplexity,
          Gemini, and Claude to map your brand rank against competitors.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label htmlFor="url" className="block text-sm font-medium text-neutral-700">
            Product URL
          </label>
          <div className="flex flex-col md:flex-row gap-3">
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://yourproduct.com"
              required
              disabled={loading}
              className="flex-1 h-11 rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-900"
            />
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="btn-primary h-11 px-5 rounded-md text-sm font-medium disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>

          {error && <p className="text-sm text-red-700">{error}</p>}

          {loading && (
            <div className="surface-muted mt-4">
              <LoadingSpinner text="Extracting profile and building initial query set..." />
            </div>
          )}
        </form>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard
          title="Brand Modeling"
          body="Extracts brand narrative, category, features, and competitor set from your site."
        />
        <FeatureCard
          title="Query Intelligence"
          body="Generates discovery, comparison, problem, and recommendation prompts to track."
        />
        <FeatureCard
          title="Rank Monitoring"
          body="Tracks multi-provider ranking positions and visibility gaps over time."
        />
      </section>
    </div>
  )
}

function FeatureCard({ title, body }: { title: string; body: string }) {
  return (
    <article className="surface p-4">
      <h2 className="text-sm font-semibold text-neutral-900">{title}</h2>
      <p className="mt-2 text-sm text-neutral-500 leading-relaxed">{body}</p>
    </article>
  )
}

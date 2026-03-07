import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject, updateProject } from '../api'

const STEPS = [
  { label: 'Fetching your website…', icon: '🌐' },
  { label: 'Extracting brand profile…', icon: '🔍' },
  { label: 'Detecting competitors…', icon: '⚔️' },
  { label: 'Generating AI queries…', icon: '🤖' },
  { label: 'Setting up workspace…', icon: '✨' },
]

function LoadingSteps({ step }: { step: number }) {
  return (
    <div className="space-y-2">
      {STEPS.map((s, idx) => {
        const isDone = idx < step
        const isCurrent = idx === step
        return (
          <div
            key={idx}
            className={`flex items-center gap-3 rounded-lg px-4 py-2.5 transition-all ${
              isCurrent
                ? 'bg-neutral-900 text-white'
                : isDone
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-neutral-50 text-neutral-400'
            }`}
          >
            <span className="text-lg w-6 text-center">{isDone ? '✓' : s.icon}</span>
            <span className={`text-sm font-medium ${isCurrent ? 'animate-pulse' : ''}`}>
              {s.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function ProjectSetup() {
  const [url, setUrl] = useState('')
  const [brandName, setBrandName] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  // Animate through steps while loading
  useEffect(() => {
    if (!loading) { setLoadingStep(0); return }
    const timings = [800, 1800, 3000, 4500] // ms to advance to next step
    const timers = timings.map((delay, idx) =>
      setTimeout(() => setLoadingStep(idx + 1), delay)
    )
    return () => { timers.forEach(clearTimeout) }
  }, [loading])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)

    try {
      let project = await createProject(url.trim())
      if (brandName.trim()) {
        project = await updateProject(project.id, { brand_name: brandName.trim() })
      }
      navigate(`/projects/${project.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Hero */}
      <div className="text-center pt-4 pb-2">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-neutral-900 text-white text-2xl mb-4">
          👁
        </div>
        <h1 className="text-3xl font-bold text-neutral-900">
          Where does AI mention your brand?
        </h1>
        <p className="mt-3 text-base text-neutral-500 max-w-xl mx-auto leading-relaxed">
          Paste your URL and we'll show you exactly how ChatGPT, Perplexity, Gemini, and Claude
          respond when buyers search for what you do.
        </p>
      </div>

      {!loading ? (
        <section className="surface p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="url" className="block text-sm font-semibold text-neutral-700 mb-1.5">
                Product URL
              </label>
              <input
                id="url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://yourproduct.com"
                required
                autoFocus
                className="w-full h-12 rounded-lg border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition-all"
              />
            </div>

            <div>
              <label htmlFor="brandName" className="block text-sm font-medium text-neutral-600 mb-1.5">
                Brand name <span className="text-neutral-400 font-normal">(optional — we'll auto-detect it)</span>
              </label>
              <input
                id="brandName"
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="Acme Corp"
                className="w-full h-11 rounded-lg border border-neutral-300 bg-white px-4 text-sm outline-none focus:border-neutral-900 transition-all"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!url.trim()}
              className="w-full btn-primary h-12 rounded-lg text-sm font-bold disabled:opacity-40 transition-all"
            >
              Analyze My AI Visibility →
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-neutral-400">
            We'll auto-generate queries and scan up to 10 in demo mode.
            No credit card required.
          </p>
        </section>
      ) : (
        <section className="surface p-8">
          <p className="text-center text-sm font-semibold text-neutral-700 mb-5">
            Analyzing <span className="text-neutral-900">{url}</span>
          </p>
          <LoadingSteps step={loadingStep} />
          <p className="mt-5 text-center text-xs text-neutral-400">
            This takes 10–20 seconds. We're reading your site and building your brand profile.
          </p>
        </section>
      )}

      {/* Feature grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            {
              icon: '🔍',
              title: 'Auto Brand Detection',
              body: 'We read your site and extract your brand name, category, features, and competitors.',
            },
            {
              icon: '🤖',
              title: 'AI Query Generation',
              body: 'We generate discovery, comparison, and buyer-intent queries that real people ask AI.',
            },
            {
              icon: '📊',
              title: 'Visibility Matrix',
              body: 'See exactly which queries mention you — and where competitors appear instead.',
            },
          ].map(({ icon, title, body }) => (
            <article key={title} className="surface p-4">
              <div className="text-2xl mb-2">{icon}</div>
              <h2 className="text-sm font-semibold text-neutral-900">{title}</h2>
              <p className="mt-1 text-xs text-neutral-500 leading-relaxed">{body}</p>
            </article>
          ))}
        </div>
      )}

    </div>
  )
}

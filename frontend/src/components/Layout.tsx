import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Github, Star } from 'lucide-react'
import { listProjects } from '../api'
import type { Project } from '../types'

const GITHUB_URL = 'https://github.com/yourusername/ai-seo-platform'

export default function Layout() {
  const [projects, setProjects] = useState<Project[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  useEffect(() => {
    listProjects().then(setProjects).catch(() => { })
  }, [location.pathname])

  return (
    <div className="flex h-screen">
      <aside
        className={`${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'} border-r border-neutral-200 bg-white transition-all duration-200`}
      >
        <div className="h-full flex flex-col">
          <div className="h-14 px-4 border-b border-neutral-200 flex items-center">
            <Link to="/" className="flex items-center gap-2.5">
              <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="flex-shrink-0">
                <rect width="32" height="32" rx="7" fill="#0f0f0f"/>
                <rect x="6" y="20" width="5" height="6" rx="1.5" fill="white" opacity="0.35"/>
                <rect x="13.5" y="15" width="5" height="11" rx="1.5" fill="white" opacity="0.65"/>
                <rect x="21" y="9" width="5" height="17" rx="1.5" fill="white"/>
                <path d="M5 12 C10 5 22 5 27 12" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.4"/>
              </svg>
              <div>
                <p className="text-sm font-semibold text-neutral-900 leading-none">AISEO</p>
                <p className="text-[11px] text-neutral-500 leading-none mt-1">Visibility Platform</p>
              </div>
            </Link>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-3">
            <div className="flex items-center justify-between px-2 mb-2">
              <p className="text-[11px] uppercase tracking-wide text-neutral-400 font-semibold">Projects</p>
              <Link
                to="/"
                title="New Project"
                className={`flex items-center justify-center w-6 h-6 rounded-md text-sm font-bold transition-colors ${location.pathname === '/' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900'}`}
              >
                +
              </Link>
            </div>

            <div className="space-y-1">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className={`block rounded-md px-3 py-2 text-sm truncate ${location.pathname === `/projects/${project.id}`
                      ? 'bg-neutral-100 text-neutral-900 font-medium'
                      : 'text-neutral-600 hover:bg-neutral-50'
                    }`}
                >
                  {project.brand_name || project.url}
                </Link>
              ))}
              {projects.length === 0 && (
                <Link
                  to="/"
                  className="flex items-center gap-2 rounded-md border border-dashed border-neutral-200 px-3 py-2 text-xs text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 transition-colors"
                >
                  <span className="text-base leading-none">+</span>
                  Add your first project
                </Link>
              )}
            </div>
          </div>

          <div className="border-t border-neutral-200 p-3 space-y-1">
            <Link
              to="/settings"
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${location.pathname.startsWith('/settings') ? 'bg-neutral-900 text-white' : 'text-neutral-700 hover:bg-neutral-100'}`}
            >
              <span className="w-5 h-5 rounded bg-neutral-200 text-[10px] text-neutral-700 grid place-items-center">S</span>
              Settings
            </Link>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 transition-colors"
            >
              <Github className="w-4 h-4" />
              GitHub
              <span className="ml-auto flex items-center gap-0.5 text-[10px] text-neutral-400">
                <Star className="w-3 h-3" />
                Star
              </span>
            </a>
          </div>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 px-5 border-b border-neutral-200 bg-white flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="text-neutral-500 hover:text-neutral-800"
            type="button"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <p className="text-sm text-neutral-500 flex-1">AI Visibility Intelligence</p>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            <Github className="w-3.5 h-3.5" />
            Star on GitHub
          </a>
        </header>

        <main className="flex-1 overflow-y-auto p-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

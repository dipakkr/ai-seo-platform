import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { listProjects } from '../api'
import type { Project } from '../types'

export default function Layout() {
  const [projects, setProjects] = useState<Project[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  useEffect(() => {
    listProjects().then(setProjects).catch(() => {})
  }, [location.pathname])

  return (
    <div className="flex h-screen">
      <aside
        className={`${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'} border-r border-neutral-200 bg-white transition-all duration-200`}
      >
        <div className="h-full flex flex-col">
          <div className="h-14 px-4 border-b border-neutral-200 flex items-center">
            <Link to="/" className="flex items-center gap-2.5">
              <span className="w-7 h-7 rounded-md bg-black text-white text-xs font-semibold grid place-items-center">G</span>
              <div>
                <p className="text-sm font-semibold text-neutral-900 leading-none">GEOkit</p>
                <p className="text-[11px] text-neutral-500 leading-none mt-1">Visibility Platform</p>
              </div>
            </Link>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-3">
            <Link
              to="/"
              className={`block rounded-md px-3 py-2 text-sm font-medium ${location.pathname === '/' ? 'bg-neutral-900 text-white' : 'text-neutral-700 hover:bg-neutral-100'}`}
            >
              New Project
            </Link>

            <div className="mt-4">
              <p className="px-2 text-[11px] uppercase tracking-wide text-neutral-400 font-semibold">Projects</p>
              <div className="mt-2 space-y-1">
                {projects.map((project) => (
                  <Link
                    key={project.id}
                    to={`/projects/${project.id}`}
                    className={`block rounded-md px-3 py-2 text-sm truncate ${
                      location.pathname === `/projects/${project.id}`
                        ? 'bg-neutral-100 text-neutral-900 font-medium'
                        : 'text-neutral-600 hover:bg-neutral-50'
                    }`}
                  >
                    {project.brand_name || project.url}
                  </Link>
                ))}
                {projects.length === 0 && (
                  <p className="px-3 py-2 text-xs text-neutral-400">No projects yet.</p>
                )}
              </div>
            </div>
          </div>

          <div className="border-t border-neutral-200 p-3">
            <Link
              to="/settings"
              className={`mb-2 flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${location.pathname.startsWith('/settings') ? 'bg-neutral-900 text-white' : 'text-neutral-700 hover:bg-neutral-100'}`}
            >
              <span className="w-5 h-5 rounded bg-neutral-200 text-[10px] text-neutral-700 grid place-items-center">S</span>
              Settings
            </Link>
            <div className="surface-muted px-3 py-2.5">
              <p className="text-sm font-medium text-neutral-900">Demo User</p>
              <p className="text-xs text-neutral-500 mt-0.5">demo@geokit.app</p>
            </div>
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
          <p className="text-sm text-neutral-500">AI Visibility Intelligence</p>
        </header>

        <main className="flex-1 overflow-y-auto p-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

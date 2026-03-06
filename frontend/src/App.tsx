import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProjectSetup from './pages/ProjectSetup'
import Dashboard from './pages/Dashboard'
import ScanResults from './pages/ScanResults'
import Opportunities from './pages/Opportunities'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ProjectSetup />} />
        <Route path="/projects/:id" element={<Dashboard />} />
        <Route path="/scans/:id" element={<ScanResults />} />
        <Route path="/scans/:id/opportunities" element={<Opportunities />} />
      </Route>
    </Routes>
  )
}

export default App

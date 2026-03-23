import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Valuutat from './pages/Valuutat'
import Valuuttaparit from './pages/Valuuttaparit'
import Historia from './pages/Historia'
import TuoData from './pages/TuoData'
import Metodologia from './pages/Metodologia'
import BiasDashboard from './pages/BiasDashboard'
import Verifiointi from './pages/Verifiointi'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/bias', label: 'COT Bias' },
  { to: '/verifiointi', label: 'Verifiointi' },
  { to: '/valuutat', label: 'Valuutat' },
  { to: '/parit', label: 'Valuuttaparit' },
  { to: '/historia', label: 'Historia' },
  { to: '/tuo-dataa', label: 'Tuo dataa' },
  { to: '/metodologia', label: 'Metodologia' },
]

function Layout({ children }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        background: '#0a0e1a',
        borderBottom: '1px solid #1e293b',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '32px', height: '56px' }}>
          <span style={{ fontWeight: 800, fontSize: '1rem', color: '#e2e8f0', whiteSpace: 'nowrap' }}>
            📈 COT Analyzer
          </span>
          <nav style={{ display: 'flex', gap: '4px', overflowX: 'auto' }}>
            {NAV.map(n => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === '/'}
                style={({ isActive }) => ({
                  padding: '6px 14px',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? '#fff' : '#64748b',
                  background: isActive ? '#1e3a5f' : 'transparent',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s',
                })}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main style={{ flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '28px 24px' }}>
        {children}
      </main>

      <footer style={{ borderTop: '1px solid #1e293b', padding: '12px 24px', textAlign: 'center', color: '#334155', fontSize: '0.75rem' }}>
        COT Currency Strength Bias Analyzer – Perustuu CFTC:n julkiseen dataan. Ei kaupankäyntineuvoja.
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/bias" element={<BiasDashboard />} />
          <Route path="/verifiointi" element={<Verifiointi />} />
          <Route path="/valuutat" element={<Valuutat />} />
          <Route path="/parit" element={<Valuuttaparit />} />
          <Route path="/historia" element={<Historia />} />
          <Route path="/tuo-dataa" element={<TuoData />} />
          <Route path="/metodologia" element={<Metodologia />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

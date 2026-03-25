import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Overview     from './pages/Overview'
import Currency     from './pages/Currency'
import Pairs        from './pages/Pairs'
import PairDetail   from './pages/PairDetail'
import DataManagement from './pages/DataManagement'

const NAV = [
  { to: '/',        label: 'Overview', end: true },
  { to: '/pairs',   label: 'Pairs' },
  { to: '/data',    label: 'Data' },
]

function Layout({ children }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#060d1a' }}>
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
            COT Dashboard
          </span>
          <nav style={{ display: 'flex', gap: '4px' }}>
            {NAV.map(n => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
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

      <footer style={{ borderTop: '1px solid #1e293b', padding: '12px 24px', textAlign: 'center',
        color: '#334155', fontSize: '0.75rem' }}>
        COT Dashboard — Based on CFTC public data. Not financial advice.
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"              element={<Overview />} />
          <Route path="/currency/:symbol" element={<Currency />} />
          <Route path="/pairs"         element={<Pairs />} />
          <Route path="/pair/:pair"    element={<PairDetail />} />
          <Route path="/data"          element={<DataManagement />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

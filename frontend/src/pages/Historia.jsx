import { useEffect, useState } from 'react'
import { getCurrencyHistory, getPairHistory } from '../api/client'
import TrendChart from '../components/TrendChart'

const CURRENCIES = ['EUR', 'GBP', 'JPY', 'CAD', 'CHF', 'AUD', 'NZD', 'USD']
const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'USDCHF', 'AUDUSD', 'NZDUSD',
  'EURJPY', 'EURGBP', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'EURCAD', 'EURCHF']

export default function Historia() {
  const [mode, setMode] = useState('currency')
  const [selection, setSelection] = useState('EUR')
  const [weeks, setWeeks] = useState(52)
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setMode('currency')
    setSelection('EUR')
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    const fetcher = mode === 'currency'
      ? getCurrencyHistory(selection, weeks)
      : getPairHistory(selection, weeks)

    fetcher
      .then(r => setData(r.data))
      .catch(e => { setError(e.response?.data?.detail || e.message); setData([]) })
      .finally(() => setLoading(false))
  }, [mode, selection, weeks])

  return (
    <div>
      <h1 style={h1}>Historia</h1>

      {/* Valinnat */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', borderRadius: '6px', overflow: 'hidden', border: '1px solid #334155' }}>
          {['currency', 'pair'].map(m => (
            <button key={m} onClick={() => { setMode(m); setSelection(m === 'currency' ? 'EUR' : 'EURUSD') }}
              style={{ padding: '7px 16px', border: 'none', cursor: 'pointer', background: mode === m ? '#3b82f6' : '#1e293b', color: mode === m ? '#fff' : '#94a3b8', fontWeight: mode === m ? 700 : 400, fontSize: '0.85rem' }}>
              {m === 'currency' ? 'Valuutta' : 'Valuuttapari'}
            </button>
          ))}
        </div>

        <select value={selection} onChange={e => setSelection(e.target.value)} style={selectStyle}>
          {(mode === 'currency' ? CURRENCIES : PAIRS).map(v => <option key={v} value={v}>{v}</option>)}
        </select>

        <select value={weeks} onChange={e => setWeeks(Number(e.target.value))} style={selectStyle}>
          <option value={26}>26 viikkoa</option>
          <option value={52}>52 viikkoa</option>
          <option value={104}>2 vuotta</option>
          <option value={156}>3 vuotta</option>
          <option value={260}>5 vuotta</option>
        </select>
      </div>

      {loading && <div style={{ color: '#64748b', padding: '24px 0' }}>Ladataan...</div>}
      {error && <div style={{ color: '#ef4444', padding: '16px 0' }}>{error}</div>}

      {!loading && !error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Score-kuvaaja */}
          <div style={card}>
            <TrendChart
              data={data}
              fields={mode === 'currency' ? ['currency_score'] : ['pair_score']}
              title={`${selection} – ${mode === 'currency' ? 'CurrencyScore' : 'PairScore'}`}
            />
          </div>

          {/* Percentile-kuvaaja */}
          <div style={card}>
            <TrendChart
              data={data}
              fields={mode === 'currency' ? ['percentile_52w'] : ['pair_percentile_52w']}
              title={`${selection} – 52vk Percentile`}
            />
          </div>

          {/* Komponenttien hajotelma (vain valuutta) */}
          {mode === 'currency' && (
            <div style={card}>
              <TrendChart
                data={data}
                fields={['z_current', 'z_delta_1w', 'z_delta_4w', 'z_oi_delta']}
                title={`${selection} – Komponentit A / B / C / D`}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '20px' }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '7px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer' }
const card = { background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }

import { useEffect, useState } from 'react'
import { getVerification, getVerificationStats, getAvailableDates } from '../api/client'
import BiasLabel from '../components/BiasLabel'
import MiniCandleChart from '../components/MiniCandleChart'
import { fmt2, scoreColor, fmtDateWithDay } from '../utils/formatters'

export default function Verifiointi() {
  const [data, setData] = useState(null)
  const [stats, setStats] = useState(null)
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [expandedPair, setExpandedPair] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAvailableDates().then(r => setDates(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true); setError(null); setExpandedPair(null)
    getVerification(selectedDate)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [selectedDate])

  // Kokonaisstatistiikka (lataa kerran)
  useEffect(() => {
    setStatsLoading(true)
    getVerificationStats(52)
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setStatsLoading(false))
  }, [])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>Verifiointi</h1>
        {dates.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Positiot mitattu:</label>
            <select value={selectedDate || ''} onChange={e => setSelectedDate(e.target.value || null)} style={selectStyle}>
              <option value="">Uusin</option>
              {dates.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        )}
      </div>

      {loading ? <div style={loadingStyle}>Ladataan hintadataa (voi kestää hetken ensimmäisellä kerralla)...</div>
       : error ? <div style={errorStyle}>Virhe: {error}</div>
       : data && (
        <>
          {/* Otsikkorivi: päivämäärät + osumisprosentit */}
          <div style={{ ...card, marginBottom: '20px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'center' }}>
              {data.report_date && (
                <div>
                  <span style={labelStyle}>Positiot mitattu:</span>{' '}
                  <strong style={{ color: '#e2e8f0' }}>{fmtDateWithDay(data.report_date)}</strong>
                </div>
              )}
              {data.publish_date && (
                <div>
                  <span style={labelStyle}>Julkaistu:</span>{' '}
                  <span style={{ color: '#94a3b8' }}>{fmtDateWithDay(data.publish_date)}</span>
                </div>
              )}
              {data.verification_start && (
                <div>
                  <span style={labelStyle}>Verifiointiviikko:</span>{' '}
                  <span style={{ color: '#60a5fa' }}>
                    {fmtDateWithDay(data.verification_start)} – {fmtDateWithDay(data.verification_end)}
                  </span>
                </div>
              )}
            </div>

            {/* Hit rate badges */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '16px' }}>
              <HitBadge label="Viikko-osuma" rate={data.hit_rate_week} count={data.total_evaluated} />
              <HitBadge label="Päiväosuma" rate={data.hit_rate_daily} />
              <HitBadge label="Vahva bias" rate={data.hit_rate_strong} />
              <HitBadge label="Lievä bias" rate={data.hit_rate_mild} />
              <div style={{ ...badgeStyle('#1e293b', '#64748b'), }}>
                Neutraalit: {data.total_neutral}
              </div>
            </div>
          </div>

          {/* Kokonaisstatistiikka */}
          {stats && stats.weeks_analyzed > 0 && (
            <div style={{ ...card, marginBottom: '20px' }}>
              <h3 style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '10px' }}>
                Pitkäaikainen osumisprosentti ({stats.weeks_analyzed} viikkoa)
              </h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                <HitBadge label="Viikko" rate={stats.week_hit_rate} />
                <HitBadge label="Päivä" rate={stats.daily_hit_rate} />
                <HitBadge label="Vahva" rate={stats.strong_bias_hit_rate} />
                <HitBadge label="Lievä" rate={stats.mild_bias_hit_rate} />
              </div>
            </div>
          )}

          {/* Paritaulukko */}
          <div style={card}>
            <PairTable
              pairs={data.pairs}
              expandedPair={expandedPair}
              onToggle={p => setExpandedPair(expandedPair === p ? null : p)}
            />
          </div>
        </>
      )}
    </div>
  )
}

function HitBadge({ label, rate, count }) {
  if (rate == null) return null
  const pct = Math.round(rate * 100)
  const color = pct >= 60 ? '#22c55e' : pct >= 45 ? '#eab308' : '#ef4444'
  return (
    <div style={badgeStyle(color + '18', color)}>
      {label}: <strong>{pct}%</strong>{count != null && ` (${count})`}
    </div>
  )
}

function PairTable({ pairs, expandedPair, onToggle }) {
  if (!pairs || pairs.length === 0) return <div style={{ color: '#475569', textAlign: 'center', padding: '48px' }}>Ei dataa</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
        <thead>
          <tr>
            {['', 'Pari', 'Bias', 'Score', 'Kynttilät', 'Ma', 'Ti', 'Ke', 'To', 'Pe', 'Vko %', ''].map((h, i) => (
              <th key={i} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pairs.map(p => (
            <PairRow key={p.pair} pair={p} expanded={expandedPair === p.pair} onToggle={() => onToggle(p.pair)} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PairRow({ pair: p, expanded, onToggle }) {
  const icon = p.week_bias_correct === true ? '✅' : p.week_bias_correct === false ? '❌' : '➖'
  const candles = p.candles || []
  const closes = candles.map(c => c.close)

  return (
    <>
      <tr onClick={onToggle} style={{ cursor: 'pointer', background: expanded ? '#1e293b' : 'transparent' }}>
        <td style={tdStyle}>{icon}</td>
        <td style={{ ...tdStyle, fontWeight: 700, color: scoreColor(p.pair_score) }}>{p.pair}</td>
        <td style={tdStyle}><BiasLabel label={p.bias_label} /></td>
        <td style={{ ...tdStyle, color: scoreColor(p.pair_score), fontWeight: 600 }}>{fmt2(p.pair_score)}</td>
        <td style={tdStyle}><MiniCandleChart candles={candles} /></td>
        {/* Ma–Pe close */}
        {[0,1,2,3,4].map(i => {
          const c = candles[i]
          const prevClose = i === 0 ? (c ? c.open : null) : (candles[i-1] ? candles[i-1].close : null)
          const change = c && prevClose ? ((c.close - prevClose) / prevClose * 100) : null
          const color = change == null ? '#475569' : change > 0 ? '#4ade80' : change < 0 ? '#f87171' : '#94a3b8'
          return (
            <td key={i} style={{ ...tdStyle, color, fontSize: '0.78rem', textAlign: 'right' }}>
              {c ? c.close.toFixed(c.close > 10 ? 3 : 5) : '–'}
              {change != null && (
                <div style={{ fontSize: '0.65rem', opacity: 0.7 }}>{change > 0 ? '+' : ''}{change.toFixed(2)}%</div>
              )}
            </td>
          )
        })}
        <td style={{ ...tdStyle, fontWeight: 700, color: p.week_change_pct > 0 ? '#4ade80' : p.week_change_pct < 0 ? '#f87171' : '#94a3b8', textAlign: 'right' }}>
          {p.week_change_pct != null ? `${p.week_change_pct > 0 ? '+' : ''}${p.week_change_pct.toFixed(2)}%` : '–'}
        </td>
        <td style={{ ...tdStyle, color: '#475569', fontSize: '0.7rem' }}>{expanded ? '▲' : '▼'}</td>
      </tr>

      {/* Laajennettu päiväkohtainen näkymä */}
      {expanded && (
        <tr>
          <td colSpan={12} style={{ padding: 0, background: '#0a0e1a' }}>
            <ExpandedView pair={p} />
          </td>
        </tr>
      )}
    </>
  )
}

function ExpandedView({ pair: p }) {
  const candles = p.candles || []
  const days = ['Ma', 'Ti', 'Ke', 'To', 'Pe']

  const dailyCorrect = p.daily_bias_correct || []
  const dailyChanges = p.daily_changes_pct || []

  return (
    <div style={{ padding: '16px 24px' }}>
      <h3 style={{ color: '#e2e8f0', fontSize: '0.9rem', marginBottom: '12px' }}>
        {p.pair} – Päiväkohtainen verifiointi: {p.bias_label} ({fmt2(p.pair_score)})
      </h3>

      <table style={{ width: '100%', maxWidth: '600px', borderCollapse: 'collapse', fontSize: '0.82rem', marginBottom: '16px' }}>
        <thead>
          <tr>
            {['Päivä', 'Open', 'High', 'Low', 'Close', 'Muutos', ''].map((h, i) => (
              <th key={i} style={{ ...thStyle, fontSize: '0.72rem' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {candles.map((c, i) => {
            const change = dailyChanges[i]
            const correct = dailyCorrect[i]
            const icon = correct === true ? '▲' : correct === false ? '▼' : '–'
            const color = change == null ? '#94a3b8' : change > 0 ? '#4ade80' : change < 0 ? '#f87171' : '#94a3b8'
            const dec = c.close > 10 ? 3 : 5
            return (
              <tr key={i}>
                <td style={tdStyle}>{days[i] || c.date}</td>
                <td style={tdStyle}>{c.open.toFixed(dec)}</td>
                <td style={tdStyle}>{c.high.toFixed(dec)}</td>
                <td style={tdStyle}>{c.low.toFixed(dec)}</td>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{c.close.toFixed(dec)}</td>
                <td style={{ ...tdStyle, color }}>{change != null ? `${change > 0 ? '+' : ''}${change.toFixed(3)}%` : '–'}</td>
                <td style={{ ...tdStyle, color }}>{correct === true ? '✅' : correct === false ? '❌' : '➖'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', fontSize: '0.85rem' }}>
        <div style={{ color: '#94a3b8' }}>
          Open (ma) → Close (pe):{' '}
          <strong style={{ color: '#e2e8f0' }}>
            {p.week_open?.toFixed(p.week_open > 10 ? 3 : 5)} → {p.week_close?.toFixed(p.week_close > 10 ? 3 : 5)}
          </strong>
          {' = '}
          <strong style={{ color: p.week_change_pct > 0 ? '#4ade80' : '#f87171' }}>
            {p.week_change_pct != null ? `${p.week_change_pct > 0 ? '+' : ''}${p.week_change_pct.toFixed(3)}%` : '–'}
          </strong>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Viikko-osuma:</span>{' '}
          <strong style={{ color: p.week_bias_correct ? '#4ade80' : '#f87171' }}>
            {p.week_bias_correct === true ? '✅ OSUI' : p.week_bias_correct === false ? '❌ EI OSUNUT' : '➖'}
          </strong>
        </div>
        {p.daily_hit_rate != null && (
          <div>
            <span style={{ color: '#94a3b8' }}>Päiväosuma:</span>{' '}
            <strong style={{ color: p.daily_hit_rate >= 0.6 ? '#4ade80' : '#f87171' }}>
              {Math.round(p.daily_hit_rate * 100)}%
            </strong>
          </div>
        )}
      </div>
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const card = { background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }
const labelStyle = { color: '#64748b', fontSize: '0.82rem' }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer' }
const loadingStyle = { textAlign: 'center', padding: '64px', color: '#64748b' }
const errorStyle = { textAlign: 'center', padding: '64px', color: '#ef4444' }
const thStyle = { padding: '8px 10px', color: '#64748b', fontWeight: 600, borderBottom: '1px solid #1e293b', textAlign: 'left', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap' }
const tdStyle = { padding: '8px 10px', borderBottom: '1px solid #0f172a', color: '#cbd5e1', verticalAlign: 'middle' }

const badgeStyle = (bg, color) => ({
  display: 'inline-block', padding: '4px 12px', borderRadius: '6px',
  background: bg, color, fontSize: '0.82rem', fontWeight: 600,
})
